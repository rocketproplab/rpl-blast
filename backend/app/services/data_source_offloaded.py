from __future__ import annotations

import time
import struct
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol, Tuple, Union, Optional
import random

try:
    import serial  # pyserial
except Exception:  # pragma: no cover
    serial = None  # type: ignore

from ..config.loader import Settings

# ==========================================
#  ROCKET CONFIGURATION & PROTOCOL MAP
# ==========================================

@dataclass
class PTSensorConfig:
    name: str
    pin_id: str 
    pressure_range: float
    voltage_min: float
    voltage_max: float
    analog_range: float = 1023.0
    voltage_ref: float = 5.0

# Order matches pt.cpp
PT_CONFIGS: List[PTSensorConfig] = [
    PTSensorConfig("GN2",            "A0", 5000.0, 0.5, 4.5),
    PTSensorConfig("LOX-UPSTREAM",   "A1", 1000.0, 1.0, 5.0),
    PTSensorConfig("LNG-UPSTREAM",   "A2", 1000.0, 1.0, 5.0),
    PTSensorConfig("LOX-DOWNSTREAM", "A3", 1000.0, 1.0, 5.0),
    PTSensorConfig("LNG-DOWNSTREAM", "A4", 1000.0, 1.0, 5.0),
    PTSensorConfig("LOX-DOME",       "A7", 1500.0, 0.5, 4.5),
    PTSensorConfig("LNG-DOME",       "A6", 1500.0, 0.5, 4.5),
]

# [PROTOCOL AGREEMENT]
# Map the 6-bit Sensor ID (0-63) to the internal data arrays.
# Format: ID: ("type", index)
# Types: "pt" (Pressure), "tc" (Thermocouple), "lc" (Load Cell), "fcv" (Valve)
SENSOR_ID_MAP = {
    # Pressure Transducers (Matches PT_CONFIGS order)
    0: ("pt", 0),
    1: ("pt", 1),
    2: ("pt", 2),
    3: ("pt", 3),
    4: ("pt", 4),
    5: ("pt", 5),
    6: ("pt", 6),

    # Thermocouples (Arbitrary IDs assigned - Update to match Firmware)
    10: ("tc", 0),
    11: ("tc", 1),
    12: ("tc", 2),
    13: ("tc", 3),
    
    # Load Cells
    20: ("lc", 0),
    21: ("lc", 1),

    # Valves (FCV)
    30: ("fcv", 0),
    31: ("fcv", 1),
    32: ("fcv", 2),
}

# ==========================================
#  CONVERSION LOGIC
# ==========================================

def convert_raw_pt_to_psi(raw_val: int, config: PTSensorConfig) -> float:
    """Converts raw 0-1023 ADC value to PSI."""
    v = (raw_val / config.analog_range) * config.voltage_ref
    denom = (config.voltage_max - config.voltage_min)
    if denom <= 0.0: return 0.0
    pres = (v - config.voltage_min) / denom * config.pressure_range
    # Clamp
    return max(0.0, min(config.pressure_range, pres))

def convert_raw_generic(raw_val: int, min_val: float, max_val: float) -> float:
    """Simple linear map for TC/LC if they just send 0-1023 scaled values."""
    # Assuming 0-1023 maps to min_val-max_val
    ratio = raw_val / 1023.0
    return min_val + (ratio * (max_val - min_val))

# ==========================================
#  DATA SOURCE INTERFACE
# ==========================================

class DataSource(Protocol):
    def initialize(self) -> None: ...
    def read_once(self) -> Tuple[Dict[str, Union[List[float], List[bool]]], float]: ...
    def shutdown(self) -> None: ...

# ==========================================
#  SIMULATOR (Generates Clean Data)
# ==========================================

@dataclass
class SimulatorSource:
    settings: Settings
    update_interval_s: float = 0.1

    def initialize(self) -> None:
        self._t0 = time.time()

    def _generate_raw_sine_wave(self, now: float, config: PTSensorConfig) -> int:
        period = 25.0
        t = (now - getattr(self, "_t0", now)) / period
        mid_psi = config.pressure_range / 2.0
        amp_psi = config.pressure_range / 2.0
        noise = random.uniform(-50.0, 50.0)
        target_psi = mid_psi + amp_psi * math.sin(2.0 * math.pi * t) + noise
        
        # Reverse Math: PSI -> ADC
        denom = config.voltage_max - config.voltage_min
        target_volts = (target_psi * denom / config.pressure_range) + config.voltage_min
        raw = int((target_volts * config.analog_range) / config.voltage_ref)
        return max(0, min(1023, raw))

    def read_once(self) -> Tuple[Dict[str, Union[List[float], List[bool]]], float]:
        # The Simulator behaves as the "Perfect Source", bypassing the binary 
        # packing to ensure the UI always has valid data to display.
        now = time.time()
        
        # 1. Simulate PTs (Raw -> Converted)
        pt_values: List[float] = []
        for i, config in enumerate(PT_CONFIGS):
            raw_val = 0
            if config.name == "GN2":
                raw_val = self._generate_raw_sine_wave(now, config)
            else:
                raw_val = random.randint(102, 300) # Steady state noise
            pt_values.append(convert_raw_pt_to_psi(raw_val, config))

        # 2. Simulate others
        tc = [random.uniform(20.0, 30.0) for _ in self.settings.THERMOCOUPLES]
        lc = [random.uniform(0.0, 10.0) for _ in self.settings.LOAD_CELLS]
        fcv_actual = [False] * self.settings.NUM_FLOW_CONTROL_VALVES
        fcv_expected = [False] * self.settings.NUM_FLOW_CONTROL_VALVES

        value = {
            "pt": pt_values,
            "tc": tc,
            "lc": lc,
            "fcv_actual": fcv_actual,
            "fcv_expected": fcv_expected,
            "timestamp": now,
        }
        return value, now

    def shutdown(self) -> None:
        pass

# ==========================================
#  SERIAL SOURCE (Binary Protocol Impl)
# ==========================================

@dataclass
class SerialSource:
    settings: Settings
    update_interval_s: float = 0.001 # Poll fast for binary data

    # Internal buffer for fragmented packets
    _buffer: bytearray = field(default_factory=bytearray)

    def __post_init__(self) -> None:
        self._port = self.settings.SERIAL_PORT
        self._baud = self.settings.SERIAL_BAUDRATE
        self._ser = None
        
        # Initialize State Vectors
        self._pt = [0.0] * len(PT_CONFIGS)
        self._tc = [0.0] * self.settings.NUM_THERMOCOUPLES
        self._lc = [0.0] * self.settings.NUM_LOAD_CELLS
        self._fcv_actual = [False] * self.settings.NUM_FLOW_CONTROL_VALVES
        self._fcv_expected = [False] * self.settings.NUM_FLOW_CONTROL_VALVES

    def initialize(self) -> None:
        if serial is None:
            raise RuntimeError("pyserial not available.")
        
        self._serial_logger = getattr(self.settings, '_serial_logger', None)
        if self._serial_logger:
            self._serial_logger.log_connection_attempt(self._port, self._baud)
            
        try:
            # Timeout is small so we don't block the main loop
            self._ser = serial.Serial(port=self._port, baudrate=self._baud, timeout=0.01)
            time.sleep(0.5)
            if self._serial_logger:
                self._serial_logger.log_connection_success(self._port, self._baud)
        except Exception as e:
            if self._serial_logger:
                self._serial_logger.log_connection_failure(self._port, self._baud, str(e))
            raise RuntimeError(f"Failed to open serial port {self._port}: {e}")

    def _process_packet(self, sensor_id: int, raw_value: int) -> None:
        """
        Maps a decoded ID/Value pair to the correct internal state array.
        """
        if sensor_id not in SENSOR_ID_MAP:
            return # Unknown ID, ignore

        s_type, s_index = SENSOR_ID_MAP[sensor_id]

        # 1. Pressure Transducers
        if s_type == "pt":
            if s_index < len(self._pt):
                # Retrieve config for this specific PT index
                config = PT_CONFIGS[s_index]
                self._pt[s_index] = convert_raw_pt_to_psi(raw_value, config)
        
        # 2. Thermocouples
        elif s_type == "tc":
            if s_index < len(self._tc):
                # Example conversion: map 0-1023 to 0-1000 deg C?
                # Adjust min/max based on your hardware spec
                self._tc[s_index] = convert_raw_generic(raw_value, 0.0, 1000.0)

        # 3. Load Cells
        elif s_type == "lc":
            if s_index < len(self._lc):
                self._lc[s_index] = convert_raw_generic(raw_value, 0.0, 5000.0)

        # 4. Valves (FCV)
        elif s_type == "fcv":
            if s_index < len(self._fcv_actual):
                # Threshold logic: > 512 is OPEN (True), < 512 is CLOSED (False)
                state = raw_value > 512
                self._fcv_actual[s_index] = state
                self._fcv_expected[s_index] = state

    def read_once(self) -> Tuple[Dict[str, Union[List[float], List[bool]]], float]:
        if self._ser is None:
            raise RuntimeError("Serial not initialized")
        
        try:
            # 1. Read all available bytes
            if self._ser.in_waiting > 0:
                new_data = self._ser.read(self._ser.in_waiting)
                self._buffer.extend(new_data)
                
                # Log raw bytes if logger is active (optional, can be noisy)
                if self._serial_logger:
                    self._serial_logger.log_data_read(new_data.hex(), self._port, True)

            # 2. Process 2-byte chunks [High Byte, Low Byte]
            # Protocol: 16 bits = [6 bit ID] [10 bit Value]
            
            while len(self._buffer) >= 2:
                # Pop 2 bytes
                b1 = self._buffer[0]
                b2 = self._buffer[1]
                
                packet = (b1 << 8) | b2 

                # Decode
                # Top 6 bits: ID
                sensor_id = (packet >> 10) & 0x3F
                # Bottom 10 bits: Value
                raw_value = packet & 0x03FF

                # Process
                self._process_packet(sensor_id, raw_value)

                # Remove used bytes
                del self._buffer[:2]
            
            # Heartbeat
            if hasattr(self.settings, '_freeze_detector'):
                self.settings._freeze_detector.heartbeat('serial_communication')
                
        except Exception as e:
            if self._serial_logger:
                self._serial_logger.log_data_read('', self._port, False, str(e))
            # On error, we don't crash, we just return the last known state
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