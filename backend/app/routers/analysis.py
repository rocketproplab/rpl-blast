from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

from fastapi import APIRouter, Body, HTTPException, Request

from ..config.paths import FRONTEND_TEMPLATES
from ..services.analysis_source import AnalysisSource


router = APIRouter()


def _get_logs_directory() -> Path:
    """Get the logs directory path."""
    return FRONTEND_TEMPLATES.parent.parent / "logs"


def _get_run_directory(run_id: str) -> Path:
    """Get the directory path for a specific run."""
    logs_dir = _get_logs_directory()
    run_dir = logs_dir / run_id
    return run_dir


def _parse_run_id(run_id: str) -> Optional[datetime]:
    """Parse run_id (YYYYMMDD_HHMMSS) to datetime, or None if invalid."""
    try:
        return datetime.strptime(run_id, "%Y%m%d_%H%M%S")
    except ValueError:
        return None


@router.get("/api/analysis/runs")
def list_runs(request: Request) -> Dict[str, Any]:
    """List all available analysis runs."""
    logs_dir = _get_logs_directory()
    
    if not logs_dir.exists():
        return {"runs": []}
    
    runs = []
    
    for run_dir in sorted(logs_dir.iterdir(), reverse=True):
        if not run_dir.is_dir():
            continue
        
        run_id = run_dir.name
        
        # Skip special directories
        if run_id in ('latest',):
            continue
        
        # Validate run_id format
        dt = _parse_run_id(run_id)
        if dt is None:
            continue
        
        # Check if data.jsonl exists
        data_file = run_dir / "data.jsonl"
        if not data_file.exists():
            continue
        
        # Try to get run summary if available
        summary_file = run_dir / "run_summary.json"
        summary = None
        if summary_file.exists():
            try:
                with open(summary_file, 'r') as f:
                    summary = json.load(f)
            except Exception:
                pass
        
        # Count entries in data.jsonl (approximate)
        entry_count = 0
        try:
            with open(data_file, 'r') as f:
                entry_count = sum(1 for line in f if line.strip())
        except Exception:
            pass
        
        # Get duration from summary or calculate from first/last entry
        duration_seconds = 0.0
        start_time = None
        end_time = None
        
        if summary:
            duration_seconds = summary.get('duration_seconds', 0.0)
            start_time = summary.get('start_time')
            end_time = summary.get('end_time')
        else:
            # Try to get from first and last entry
            try:
                with open(data_file, 'r') as f:
                    first_line = None
                    last_line = None
                    for line in f:
                        line = line.strip()
                        if line:
                            if first_line is None:
                                first_line = line
                            last_line = line
                    
                    if first_line and last_line:
                        first_entry = json.loads(first_line)
                        last_entry = json.loads(last_line)
                        start_time = first_entry.get('recieved_at')
                        end_time = last_entry.get('recieved_at')
                        if start_time and end_time:
                            duration_seconds = end_time - start_time
            except Exception:
                pass
        
        runs.append({
            "run_id": run_id,
            "timestamp": dt.isoformat(),
            "duration_seconds": duration_seconds,
            "data_points": entry_count,
            "start_time": start_time,
            "end_time": end_time,
        })
    
    return {"runs": runs}


@router.get("/api/analysis/runs/{run_id}")
def get_run_info(run_id: str, request: Request) -> Dict[str, Any]:
    """Get detailed information about a specific run."""
    run_dir = _get_run_directory(run_id)
    
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    data_file = run_dir / "data.jsonl"
    if not data_file.exists():
        raise HTTPException(status_code=404, detail=f"data.jsonl not found for run {run_id}")
    
    # Load run summary if available
    summary_file = run_dir / "run_summary.json"
    summary = None
    if summary_file.exists():
        try:
            with open(summary_file, 'r') as f:
                summary = json.load(f)
        except Exception:
            pass
    
    # Count entries
    entry_count = 0
    try:
        with open(data_file, 'r') as f:
            entry_count = sum(1 for line in f if line.strip())
    except Exception:
        pass
    
    # Get first and last entry for timing info
    first_entry = None
    last_entry = None
    try:
        with open(data_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    if first_entry is None:
                        first_entry = json.loads(line)
                    last_entry = json.loads(line)
    except Exception:
        pass
    
    dt = _parse_run_id(run_id)
    
    return {
        "run_id": run_id,
        "timestamp": dt.isoformat() if dt else None,
        "summary": summary,
        "data_file_exists": True,
        "total_entries": entry_count,
        "first_entry": first_entry,
        "last_entry": last_entry,
    }


@router.get("/api/analysis/data/{run_id}")
def get_all_run_data(run_id: str, request: Request) -> Dict[str, Any]:
    """Get all data entries from a run for frontend to pre-load."""
    run_dir = _get_run_directory(run_id)
    
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    data_file = run_dir / "data.jsonl"
    if not data_file.exists():
        raise HTTPException(status_code=404, detail=f"data.jsonl not found for run {run_id}")
    
    try:
        all_data = []
        with open(data_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    # Extract just what we need for plotting
                    all_data.append({
                        't_seconds': entry.get('t_seconds', 0.0),
                        'raw': entry.get('raw', {}),
                        'adjusted': entry.get('adjusted', {}),
                    })
                except json.JSONDecodeError:
                    continue
        
        return {
            "run_id": run_id,
            "data": all_data,
            "total_entries": len(all_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load run data: {str(e)}")


@router.post("/api/analysis/load/{run_id}")
def load_run(run_id: str, request: Request, body: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    """Switch to analysis mode and load a specific run."""
    run_dir = _get_run_directory(run_id)
    
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    data_file = run_dir / "data.jsonl"
    if not data_file.exists():
        raise HTTPException(status_code=404, detail=f"data.jsonl not found for run {run_id}")
    
    # Get playback parameters from request body
    playback_speed = float(body.get("playback_speed", 1.0))
    start_at_seconds = float(body.get("start_at_seconds", 0.0))
    
    if playback_speed <= 0:
        raise HTTPException(status_code=400, detail="playback_speed must be positive")
    
    try:
        # Create analysis source
        analysis_source = AnalysisSource(
            settings=request.app.state.settings,
            run_directory=run_dir
        )
        
        # Initialize (loads data)
        analysis_source.initialize()
        
        # Set playback speed
        analysis_source.set_playback_speed(playback_speed)
        
        # Seek to start position
        if start_at_seconds > 0:
            analysis_source.seek_to_time(start_at_seconds)
        
        # Store in app state
        request.app.state.analysis_source = analysis_source
        request.app.state.data_mode = "analysis"
        request.app.state.current_run_id = run_id
        
        # Get status for response
        status = analysis_source.get_status()
        
        return {
            "status": "loaded",
            "run_id": run_id,
            "total_entries": status["total_entries"],
            "duration_seconds": status["total_duration"],
            "playback_speed": playback_speed,
            "start_at_seconds": start_at_seconds,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load run: {str(e)}")


@router.post("/api/analysis/control")
def control_playback(request: Request, body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Control playback (play, pause, seek, set_speed)."""
    if request.app.state.data_mode != "analysis":
        raise HTTPException(status_code=400, detail="Not in analysis mode")
    
    analysis_source: Optional[AnalysisSource] = getattr(request.app.state, 'analysis_source', None)
    if analysis_source is None:
        raise HTTPException(status_code=400, detail="No analysis source loaded")
    
    action = body.get("action")
    
    if action == "play":
        analysis_source.resume()
    elif action == "pause":
        analysis_source.pause()
    elif action == "seek":
        t_seconds = float(body.get("t_seconds", 0.0))
        analysis_source.seek_to_time(t_seconds)
    elif action == "set_speed":
        speed = float(body.get("speed", 1.0))
        if speed <= 0:
            raise HTTPException(status_code=400, detail="speed must be positive")
        analysis_source.set_playback_speed(speed)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
    
    status = analysis_source.get_status()
    
    return {
        "status": "ok",
        "current_position": status["current_t_seconds"],
        "is_paused": status["is_paused"],
        "playback_speed": status["playback_speed"],
        "is_at_end": status["is_at_end"],
    }


@router.get("/api/analysis/status")
def get_analysis_status(request: Request) -> Dict[str, Any]:
    """Get current analysis mode status."""
    mode = getattr(request.app.state, 'data_mode', 'live')
    
    if mode != "analysis":
        return {
            "mode": "live",
            "run_id": None,
            "current_position": None,
            "total_duration": None,
            "is_paused": None,
            "playback_speed": None,
        }
    
    analysis_source: Optional[AnalysisSource] = getattr(request.app.state, 'analysis_source', None)
    if analysis_source is None:
        return {
            "mode": "analysis",
            "run_id": getattr(request.app.state, 'current_run_id', None),
            "current_position": None,
            "total_duration": None,
            "is_paused": None,
            "playback_speed": None,
        }
    
    status = analysis_source.get_status()
    run_id = getattr(request.app.state, 'current_run_id', None)
    
    return {
        "mode": "analysis",
        "run_id": run_id,
        "current_position": status["current_t_seconds"],
        "total_duration": status["total_duration"],
        "is_paused": status["is_paused"],
        "playback_speed": status["playback_speed"],
        "is_at_end": status["is_at_end"],
    }


@router.post("/api/analysis/switch_to_live")
def switch_to_live(request: Request) -> Dict[str, Any]:
    """Switch back to live mode."""
    # Shutdown analysis source if active
    analysis_source: Optional[AnalysisSource] = getattr(request.app.state, 'analysis_source', None)
    if analysis_source is not None:
        analysis_source.shutdown()
        request.app.state.analysis_source = None
    
    # Switch mode
    request.app.state.data_mode = "live"
    request.app.state.current_run_id = None
    
    return {
        "status": "switched",
        "mode": "live",
    }

