from __future__ import annotations

import re
import sys
import time
import json
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Protocol, Tuple, Union
import random

try:
    import serial  # pyserial
except Exception:  # pragma: no cover
    serial = None  # type: ignore

from ..config.loader import Settings


class DataSource(Protocol):
    def initialize(self) -> None: ...
    def read_once(self) -> Tuple[Dict[str, Union[List[float], List[bool]]], float]: ...
    def shutdown(self) -> None: ...


@dataclass
class SimulatorSource:
    settings: Settings
    update_interval_s: float = 0.1

    def initialize(self) -> None:
        # Anchor time for deterministic waveforms
        self._t0 = time.time()
        return None

    def _rand_in_range(self, min_v: float, max_v: float) -> float:
        r = random.random()
        if r < 0.02:
            return random.uniform(max_v * 0.8, max_v * 0.95)
        if r < 0.05:
            return random.uniform(max_v * 0.5, max_v * 0.7)
        return random.uniform(min_v + max_v * 0.1, max_v * 0.4)

    def read_once(self) -> Tuple[Dict[str, Union[List[float], List[bool]]], float]:
        now = time.time()
        # Pressure transducers: special behavior for GN2 (sine wave + noise)
        pt: List[float] = []
        for i, ptc in enumerate(self.settings.PRESSURE_TRANSDUCERS):
            name = str(ptc.get("name", "")).strip().upper()
            if name == "GN2":
                # Sine with 60s period between -30 and 5000 plus noise
                period = 25.0
                t = (now - getattr(self, "_t0", now)) / period
                min_v = -30.0
                max_v = 5000.0
                mid = (max_v + min_v) / 2.0
                amp = (max_v - min_v) / 2.0
                noise = random.uniform(-50.0, 50.0)
                val = mid + amp * math.sin(2.0 * math.pi * t) + noise
                # clamp within the intended range
                val = max(min_v, min(max_v, val))
                pt.append(val)
            else:
                pt.append(
                    self._rand_in_range(
                        float(ptc.get("min_value", 0.0)), float(ptc.get("max_value", 1000.0))
                    )
                )
        tc = [
            self._rand_in_range(2 * tcc.get("min_value", 0.0), tcc.get("max_value", 1000.0))
            for tcc in self.settings.THERMOCOUPLES
        ]
        lc = [
            self._rand_in_range(lcc.get("min_value", 0.0), lcc.get("max_value", 1000.0))
            for lcc in self.settings.LOAD_CELLS
        ]
        fcv_actual = [False] * self.settings.NUM_FLOW_CONTROL_VALVES
        fcv_expected = [False] * self.settings.NUM_FLOW_CONTROL_VALVES

        value = {
            "tc": tc,
            "pt": pt,
            "fcv_actual": fcv_actual,
            "fcv_expected": fcv_expected,
            "lc": lc,
            "timestamp": now,
        }
        return value, now

    def shutdown(self) -> None:
        return None


@dataclass
class SerialSource:
    settings: Settings
    update_interval_s: float = 0.1

    def __post_init__(self) -> None:
        self._port = self.settings.SERIAL_PORT
        self._baud = self.settings.SERIAL_BAUDRATE
        self._ser = None
        # Pre-size arrays
        self._pt = [0.0] * self.settings.NUM_PRESSURE_TRANSDUCERS
        self._tc = [0.0] * self.settings.NUM_THERMOCOUPLES
        self._lc = [0.0] * self.settings.NUM_LOAD_CELLS
        self._fcv_actual = [False] * self.settings.NUM_FLOW_CONTROL_VALVES
        self._fcv_expected = [False] * self.settings.NUM_FLOW_CONTROL_VALVES
        # Throttle NaN warnings per sensor (key -> last log time)
        self._nan_warn_last: Dict[Tuple[str, int], float] = {}
        self._nan_warn_interval_s: float = 5.0

    def initialize(self) -> None:
        if serial is None:
            raise RuntimeError("pyserial not available. Install 'pyserial' and retry.")
        
        # Get serial logger if available
        self._serial_logger = getattr(self.settings, '_serial_logger', None)
        
        if self._serial_logger:
            self._serial_logger.log_connection_attempt(self._port, self._baud)
            
        try:
            self._ser = serial.Serial(port=self._port, baudrate=self._baud, timeout=0.1)
            time.sleep(0.5)
            
            if self._serial_logger:
                self._serial_logger.log_connection_success(self._port, self._baud)
                
        except Exception as e:  # pragma: no cover
            if self._serial_logger:
                self._serial_logger.log_connection_failure(self._port, self._baud, str(e))
            raise RuntimeError(f"Failed to open serial port {self._port}: {e}")

    def _convert_pt_voltage_to_psi(self, value: float, pt_name: str) -> float:
        # Legacy conversion: value - offset (as seen in prior code)
        # If PT_CONVERSION doesn't exist, just pass through the value
        if not hasattr(self.settings, 'PT_CONVERSION'):
            return float(value)
        
        try:
            conv = self.settings.PT_CONVERSION['GN2'] if pt_name == 'GN2' else self.settings.PT_CONVERSION['other']
            return float(value) - float(conv.get('offset', 0.0))
        except Exception:
            return float(value)

    def _sanitize_sensor_value(
        self, value: float, sensor_type: str, sensor_id: str, index: int
    ) -> float:
        """Replace NaN/Inf with 0 and log to terminal (throttled per sensor)."""
        if value is not None and math.isfinite(value):
            return value
        key = (sensor_type, index)
        now = time.time()
        last = self._nan_warn_last.get(key, 0.0)
        if now - last >= self._nan_warn_interval_s:
            self._nan_warn_last[key] = now
            print(
                f"[Serial] {sensor_type} '{sensor_id}' (index {index}) returned "
                "non-finite value (NaN/Inf), using 0",
                file=sys.stderr,
            )
        return 0.0

    @staticmethod
    def _normalize_json_nan(raw_line: str) -> str:
        """Replace non-standard JSON literals (nan, NaN, inf, -inf) with null so json.loads succeeds."""
        return re.sub(
            r'(?<=[,[])\s*(?:nan|NaN|Infinity|-Infinity|inf|-inf)\s*(?=[,\]])',
            'null',
            raw_line,
            flags=re.IGNORECASE,
        )

    def _parse_and_update(self, raw_line: str) -> None:
        line = self._normalize_json_nan(raw_line)
        try:
            data = json.loads(line)
        except Exception:
            return
        if not isinstance(data, dict) or 'value' not in data:
            return
        value = data['value']
        def to_float(v: Any) -> float:
            if v is None:
                return math.nan
            try:
                return float(v)
            except (TypeError, ValueError):
                return math.nan

        # pt
        if 'pt' in value:
            for i, v in enumerate(value['pt']):
                if i < len(self._pt):
                    name = self.settings.PRESSURE_TRANSDUCERS[i].get('name', 'other')
                    raw_val = to_float(v)
                    converted = self._convert_pt_voltage_to_psi(raw_val, name) if math.isfinite(raw_val) else raw_val
                    self._pt[i] = self._sanitize_sensor_value(
                        converted, 'Pressure transducer', name, i
                    )
        # tc
        if 'tc' in value:
            for i, v in enumerate(value['tc']):
                if i < len(self._tc):
                    name = (
                        self.settings.THERMOCOUPLES[i].get('name', f'TC{i}')
                        if i < len(self.settings.THERMOCOUPLES)
                        else f'TC{i}'
                    )
                    self._tc[i] = self._sanitize_sensor_value(
                        to_float(v), 'Thermocouple', name, i
                    )
        # lc
        if 'lc' in value:
            for i, v in enumerate(value['lc']):
                if i < len(self._lc):
                    name = (
                        self.settings.LOAD_CELLS[i].get('name', f'LC{i}')
                        if i < len(self.settings.LOAD_CELLS)
                        else f'LC{i}'
                    )
                    self._lc[i] = self._sanitize_sensor_value(
                        to_float(v), 'Load cell', name, i
                    )
        # fcv
        if 'fcv' in value:
            for i, v in enumerate(value['fcv']):
                if i < len(self._fcv_actual):
                    state = bool(v)
                    self._fcv_actual[i] = state
                    self._fcv_expected[i] = state

    def read_once(self) -> Tuple[Dict[str, Union[List[float], List[bool]]], float]:
        if self._ser is None:
            raise RuntimeError("Serial not initialized")
        # Attempt to read a line; if none, return current snapshot
        try:
            if self._ser.in_waiting > 0:
                line = self._ser.readline().decode('ascii', errors='ignore').strip()
                if line:
                    if self._serial_logger:
                        self._serial_logger.log_data_read(line, self._port, True)
                    self._parse_and_update(line)
                elif self._serial_logger:
                    self._serial_logger.log_data_read('', self._port, True)
            
            # Send heartbeat to freeze detector when serial is active
            if hasattr(self.settings, '_freeze_detector'):
                self.settings._freeze_detector.heartbeat('serial_communication')
                
        except Exception as e:  # pragma: no cover
            if self._serial_logger:
                self._serial_logger.log_data_read('', self._port, False, str(e))
            # Keep last values on transient errors
            pass
        now = time.time()
        value = {
            "pt": list(self._pt),
            "tc": list(self._tc),
            "lc": list(self._lc),
            "fcv_actual": list(self._fcv_actual),
            "fcv_expected": list(self._fcv_expected),
            "timestamp": now,
        }
        return value, now

    def shutdown(self) -> None:
        try:
            if self._ser is not None and self._ser.is_open:
                self._ser.close()
        except Exception:
            pass
