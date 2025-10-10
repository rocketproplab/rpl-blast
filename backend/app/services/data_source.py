from __future__ import annotations

import time
import json
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
        pt = [
            self._rand_in_range(ptc.get("min_value", 0.0), ptc.get("max_value", 1000.0))
            for ptc in self.settings.PRESSURE_TRANSDUCERS
        ]
        tc = [
            self._rand_in_range(tcc.get("min_value", 0.0), tcc.get("max_value", 1000.0))
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

    def _parse_and_update(self, raw_line: str) -> None:
        try:
            data = json.loads(raw_line)
        except Exception:
            return
        if not isinstance(data, dict) or 'value' not in data:
            return
        value = data['value']
        # pt
        if 'pt' in value:
            for i, v in enumerate(value['pt']):
                if i < len(self._pt):
                    name = self.settings.PRESSURE_TRANSDUCERS[i].get('name', 'other')
                    self._pt[i] = self._convert_pt_voltage_to_psi(float(v), name)
        # tc
        if 'tc' in value:
            for i, v in enumerate(value['tc']):
                if i < len(self._tc):
                    self._tc[i] = float(v)
        # lc
        if 'lc' in value:
            for i, v in enumerate(value['lc']):
                if i < len(self._lc):
                    self._lc[i] = float(v)
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
