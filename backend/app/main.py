from __future__ import annotations

import asyncio
import sys
from typing import Optional

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import json
import logging

# Import comprehensive logging system
from .logging import LoggerManager, EventLogger, SerialLogger, PerformanceMonitor, ErrorRecovery, FreezeDetector

from .config.paths import (
    FRONTEND_CONFIG_YAML,
    FRONTEND_STATIC,
    FRONTEND_TEMPLATES,
    assert_legacy_layout,
)
from .config.loader import load_settings
from .routers import data as data_router
from .routers import pages as pages_router
from .routers import calibration as calibration_router
from .services.data_source import SimulatorSource, SerialSource
from .services.calibration import CalibrationService, CalibrationStore
from .services.reading_cache import LatestReadingCache
from .version import get_version


def _apply_offsets(raw: dict, offsets: dict, settings) -> dict:
    # Build ID lists from settings
    pt_ids = [pt.get("id") for pt in settings.PRESSURE_TRANSDUCERS]
    tc_ids = [tc.get("id") for tc in settings.THERMOCOUPLES]
    lc_ids = [lc.get("id") for lc in settings.LOAD_CELLS]

    def adj_series(series: list, ids: list) -> list:
        out = []
        for i, val in enumerate(series):
            sid = ids[i] if i < len(ids) else None
            off = offsets.get(sid, 0.0) if sid else 0.0
            try:
                out.append(float(val) + float(off))
            except Exception:
                out.append(val)
        return out

    adjusted = {
        "pt": adj_series(raw.get("pt", []), pt_ids),
        "tc": adj_series(raw.get("tc", []), tc_ids),
        "lc": adj_series(raw.get("lc", []), lc_ids),
        # Booleans: pass through
        "fcv_actual": list(raw.get("fcv_actual", [])),
        "fcv_expected": list(raw.get("fcv_expected", [])),
    }
    return adjusted


def _get_logs_path() -> Path:
    # Write logs alongside the legacy logs directory
    legacy_logs = FRONTEND_TEMPLATES.parent.parent / "logs"
    legacy_logs.mkdir(parents=True, exist_ok=True)
    return legacy_logs / "data.jsonl"

def create_app() -> FastAPI:
    assert_legacy_layout()

    settings = load_settings(FRONTEND_CONFIG_YAML)

    app = FastAPI()

    # Initialize comprehensive logging system
    logs_dir = FRONTEND_TEMPLATES.parent.parent / 'logs'
    config_path = FRONTEND_TEMPLATES.parent / 'logging_config.yaml'
    
    app.state.logger_manager = LoggerManager(logs_dir, config_path)
    app.state.event_logger = EventLogger(app.state.logger_manager)
    app.state.serial_logger = SerialLogger(app.state.logger_manager)
    app.state.performance_monitor = PerformanceMonitor(app.state.logger_manager)
    app.state.error_recovery = ErrorRecovery(app.state.logger_manager)
    app.state.freeze_detector = FreezeDetector(app.state.logger_manager)

    # Shared state
    app.state.settings = settings
    app.state.cache = LatestReadingCache()
    app.state.templates = Jinja2Templates(directory=str(FRONTEND_TEMPLATES))
    app.state.reader_task: Optional[asyncio.Task] = None
    app.state.healthy: bool = True
    app.state.health_error: Optional[str] = None
    app.state.data_log_path: Path = _get_logs_path()
    app.state.data_log_errors: int = 0
    # Health thresholds (customizable via env)
    import os as _os
    try:
        app.state.health_max_lag_ms = float(_os.environ.get("HEALTH_MAX_LAG_MS", "2000"))
    except Exception:
        app.state.health_max_lag_ms = 2000.0
    try:
        app.state.health_max_log_errors = int(_os.environ.get("HEALTH_MAX_LOG_ERRORS", "100"))
    except Exception:
        app.state.health_max_log_errors = 100
    app.state.app_version = get_version()

    # Mount static files under the same name Flask templates expect
    app.mount(
        "/static",
        StaticFiles(directory=str(FRONTEND_STATIC)),
        name="static",
    )

    # Include routers
    app.include_router(data_router.router)
    app.include_router(pages_router.router)
    app.include_router(calibration_router.router)

    @app.on_event("startup")
    async def _startup():
        # Initialize calibration service (fail early on invalid file)
        try:
            # Store offsets alongside legacy logs for better write permissions
            from pathlib import Path as _P
            logs_dir = FRONTEND_TEMPLATES.parent.parent / 'logs'
            logs_dir.mkdir(parents=True, exist_ok=True)
            calib_path = logs_dir / 'calibration_offsets.yaml'
            store = CalibrationStore(path=calib_path)
            calib = CalibrationService(store)
            calib.initialize()
            app.state.calibration = calib
        except Exception as e:
            app.state.healthy = False
            app.state.health_error = f"calibration: {e}"
            print(f"FATAL: failed to load calibration offsets: {e}", file=sys.stderr)
            raise SystemExit(1)
        # Choose data source (simulate serial existence but default to simulator)
        if settings.DATA_SOURCE == "serial":
            # Pass logging components to data source
            settings._serial_logger = app.state.serial_logger
            settings._freeze_detector = app.state.freeze_detector
            source = SerialSource(settings)
            app.state.event_logger.log_data_source_change('unknown', 'serial', 'startup configuration')
        else:
            source = SimulatorSource(settings)
            app.state.event_logger.log_data_source_change('unknown', 'simulator', 'startup configuration')

        try:
            source.initialize()
            # Initial read (fail early if cannot produce data)
            value, ts = source.read_once()
            # Build raw numeric map (exclude timestamp)
            raw = {
                k: v for k, v in value.items() if k in ("pt", "tc", "lc", "fcv_actual", "fcv_expected")
            }
            # Apply calibration offsets
            calib = app.state.calibration
            offsets = calib.get()
            adjusted = _apply_offsets(raw, offsets, app.state.settings)
            # Preserve legacy behavior: include timestamp inside 'value'
            value_adjusted = dict(adjusted)
            value_adjusted["timestamp"] = ts
            app.state.cache.set_full({
                "raw": raw,
                "adjusted": adjusted,
                "offsets": offsets,
                "timestamp": ts,
                "value": value_adjusted,
            })
            
            # Log data using comprehensive logging system
            app.state.logger_manager.log_data(ts, raw, adjusted, offsets)
            
            # Legacy logging fallback
            try:
                with app.state.data_log_path.open("a") as f:
                    f.write(json.dumps({
                        "ts": ts,
                        "raw": raw,
                        "adjusted": adjusted,
                        "offsets": offsets,
                    }) + "\n")
            except Exception as e:
                app.state.data_log_errors += 1
                app.state.logger_manager.log_error('file_write_error', f'Failed to write legacy log: {e}')
        except SystemExit:
            raise
        except Exception as e:
            app.state.healthy = False
            app.state.health_error = f"startup: {e}"
            print(f"FATAL: failed to start data source: {e}", file=sys.stderr)
            raise SystemExit(1)

        async def reader_loop():
            try:
                while True:
                    # Heartbeat for freeze detection
                    app.state.freeze_detector.heartbeat('data_acquisition')
                    
                    # Measure performance
                    timer_id = app.state.performance_monitor.start_timer('data_read')
                    
                    value, ts = source.read_once()
                    raw = {
                        k: v for k, v in value.items() if k in ("pt", "tc", "lc", "fcv_actual", "fcv_expected")
                    }
                    calib = app.state.calibration
                    offsets = calib.get()
                    adjusted = _apply_offsets(raw, offsets, app.state.settings)
                    value_adjusted = dict(adjusted)
                    value_adjusted["timestamp"] = ts
                    app.state.cache.set_full({
                        "raw": raw,
                        "adjusted": adjusted,
                        "offsets": offsets,
                        "timestamp": ts,
                        "value": value_adjusted,
                    })
                    
                    # Log data using comprehensive logging system
                    app.state.logger_manager.log_data(ts, raw, adjusted, offsets)
                    
                    # Legacy logging fallback
                    try:
                        with app.state.data_log_path.open("a") as f:
                            f.write(json.dumps({
                                "ts": ts,
                                "raw": raw,
                                "adjusted": adjusted,
                                "offsets": offsets,
                            }) + "\n")
                    except Exception as e:
                        app.state.data_log_errors += 1
                        app.state.logger_manager.log_error('file_write_error', f'Failed to write legacy log: {e}')
                    
                    # End performance measurement
                    app.state.performance_monitor.end_timer(timer_id)
                    
                    # Check data lag
                    import time as _t
                    lag_ms = (_t.time() - ts) * 1000 if ts else 0
                    app.state.performance_monitor.log_data_lag(lag_ms)
                    
                    # Pace the loop to avoid blocking the event loop
                    interval = getattr(source, "update_interval_s", 0.1)
                    await asyncio.sleep(interval)
            except asyncio.CancelledError:
                app.state.event_logger.log_system_state('data_reader_cancelled', True)
                # graceful shutdown
                source.shutdown()
            except Exception as e:
                app.state.healthy = False
                app.state.health_error = f"reader: {e}"
                app.state.logger_manager.log_error('data_reader_error', f'Data reader loop failed: {e}', e)
                app.state.event_logger.log_system_state('data_reader_error', False, {'error': str(e)})
                print(f"ERROR: reader loop stopped: {e}", file=sys.stderr)

        app.state.reader_task = asyncio.create_task(reader_loop())

    @app.on_event("shutdown")
    async def _shutdown():
        app.state.event_logger.log_shutdown()
        
        # Stop monitoring systems
        app.state.performance_monitor.stop_monitoring()
        app.state.freeze_detector.stop_monitoring()
        
        task = app.state.reader_task
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    @app.get("/healthz")
    async def healthz():
        calib = getattr(app.state, 'calibration', None)
        offsets = calib.get() if calib else {}
        snap = app.state.cache.get_full()
        last_ts = snap.get("timestamp") if snap else None
        import time as _t
        now = _t.time()
        lag_ms = None
        if isinstance(last_ts, (int, float)):
            lag_ms = max(0, (now - float(last_ts)) * 1000.0)
        # Derive health: base health AND lag under threshold
        lag_ok = (lag_ms is None) or (lag_ms < app.state.health_max_lag_ms)
        data_log_ok = getattr(app.state, 'data_log_errors', 0) < app.state.health_max_log_errors
        healthy = app.state.healthy and lag_ok and data_log_ok
        return {
            "status": "ok" if healthy else "error",
            "healthy": healthy,
            "error": app.state.health_error,
            "service": "fastapi",
            "data_log_errors": getattr(app.state, 'data_log_errors', 0),
            "offsets_count": len(offsets),
            "lag_ms": lag_ms,
            "last_ts": last_ts,
            "version": app.state.app_version,
        }

    @app.get("/api/logging/status")
    async def logging_status():
        """Get comprehensive logging system status"""
        # Heartbeat for API monitoring
        app.state.freeze_detector.heartbeat('api_requests')
        
        timer_id = app.state.performance_monitor.start_timer('api_logging_status')
        
        try:
            return {
                "logger_manager": app.state.logger_manager.get_stats(),
                "event_logger": app.state.event_logger.get_event_summary(),
                "serial_logger": app.state.serial_logger.get_stats(),
                "performance_monitor": app.state.performance_monitor.get_stats(),
                "error_recovery": app.state.error_recovery.get_recovery_stats(),
                "freeze_detector": app.state.freeze_detector.get_stats(),
                "health_checks": {
                    "performance": app.state.performance_monitor.health_check(),
                    "error_recovery": app.state.error_recovery.health_check(),
                    "freeze_detector": app.state.freeze_detector.health_check()
                }
            }
        finally:
            app.state.performance_monitor.end_timer(timer_id)

    return app


app = create_app()
