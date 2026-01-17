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
#  PROTOCOL DEFINITIONS
# ==========================================

# 2-Bit Sensor Type Definitions
# Maps to the top 2 bits of the header (Bits 14-15 of the packet)
TYPE_PT  = 0  # Binary 00
TYPE_TC  = 1  # Binary 01
TYPE_LC  = 2  # Binary 10
TYPE_FCV = 3  # Binary 11

# ==========================================
#  ROCKET CONFIGURATION
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

# Order matches the "Index" sent by the rocket (0 to 6)
PT_CONFIGS: List[PTSensorConfig] = [
    PTSensorConfig("GN2",            "A0", 5000.0, 0.5, 4.5), # Index 0
    PTSensorConfig("LOX-UPSTREAM",   "A1", 1000.0, 1.0, 5.0), # Index 1
    PTSensorConfig("LNG-UPSTREAM",   "A2", 1000.0, 1.0, 5.0), # Index 2
    PTSensorConfig("LOX-DOWNSTREAM", "A3", 1000.0, 1.0, 5.0), # Index 3
    PTSensorConfig("LNG-DOWNSTREAM", "A4", 1000.0, 1.0, 5.0), # Index 4
    PTSensorConfig("LOX-DOME",       "A7", 1500.0, 0.5, 4.5), # Index 5
    PTSensorConfig("LNG-DOME",       "A6", 1500.0, 0.5, 4.5), # Index 6
]

# ==========================================
#  CONVERSION LOGIC
# ==========================================

def convert_raw_pt_to_psi(raw_val: int, config: PTSensorConfig) -> float:
    """Converts raw 0-1023 ADC value to PSI."""
    v = (raw_val / config.analog_range) * config.voltage_ref
    denom = (config.voltage_max - config.voltage_min)
    if denom <= 0.0: return 0.0
    pres = (v - config.voltage_min) / denom * config.pressure_range
    return max(0.0, min(config.pressure_range, pres))

def convert_raw_generic(raw_val: int, min_val: float, max_val: float) -> float:
    """Simple linear map for TC/LC if they just send 0-1023 scaled values."""
    ratio = raw_val / 1023.0
    return min_val + (ratio * (max_val - min_val))

def convert_raw_voltage(raw_val: int) -> float:
    """Converts raw 0-1023 ADC value to 0-5V."""
    return (raw_val / 1023.0) * 5.0

# ==========================================
#  DATA SOURCE INTERFACE
# ==========================================

class DataSource(Protocol):
    def initialize(self) -> None: ...
    def read_once(self) -> Tuple[Dict[str, Union[List[float], List[bool]]], float]: ...
    def shutdown(self) -> None: ...

# ==========================================
#  SIMULATOR (Byte-Level Simulation)
# ==========================================

@dataclass
class SimulatorSource:
    settings: Settings
    update_interval_s: float = 0.1

    def __post_init__(self) -> None:
        # Internal state storage (Same as SerialSource)
        self._pt = [0.0] * len(PT_CONFIGS)
        self._tc = [0.0] * self.settings.NUM_THERMOCOUPLES
        self._lc = [0.0] * self.settings.NUM_LOAD_CELLS
        self._fcv_actual = [0.0] * self.settings.NUM_FLOW_CONTROL_VALVES
        self._fcv_expected = [0.0] * self.settings.NUM_FLOW_CONTROL_VALVES

    def initialize(self) -> None:
        self._t0 = time.time()

    def _generate_raw_pt(self, now: float, i: int, config: PTSensorConfig) -> int:
        """Generates a raw 0-1023 integer mimicking sensor reading."""
        if config.name == "GN2":
            # Sine wave simulation logic
            period = 25.0
            t = (now - getattr(self, "_t0", now)) / period
            mid_psi = config.pressure_range / 2.0
            amp_psi = config.pressure_range / 2.0
            noise = random.uniform(-50.0, 50.0)
            target_psi = mid_psi + amp_psi * math.sin(2.0 * math.pi * t) + noise
            
            # Reverse: PSI -> Voltage -> ADC
            denom = config.voltage_max - config.voltage_min
            target_volts = (target_psi * denom / config.pressure_range) + config.voltage_min
            raw = int((target_volts * config.analog_range) / config.voltage_ref)
        else:
            # Steady state random noise
            raw = random.randint(300, 450) # Approx 1.5V-2.2V
            
        return max(0, min(1023, raw))

    def _process_packet(self, sensor_type: int, index: int, raw_value: int) -> None:
        """
        EXACT COPY of SerialSource._process_packet.
        Decodes the values and updates internal state.
        """
        if sensor_type == TYPE_PT:
            if index < len(self._pt):
                config = PT_CONFIGS[index]
                self._pt[index] = convert_raw_pt_to_psi(raw_value, config)
        
        elif sensor_type == TYPE_TC:
            if index < len(self._tc):
                self._tc[index] = convert_raw_generic(raw_value, 0.0, 1000.0)

        elif sensor_type == TYPE_LC:
            if index < len(self._lc):
                self._lc[index] = convert_raw_generic(raw_value, 0.0, 5000.0)

        elif sensor_type == TYPE_FCV:
            if index < len(self._fcv_actual):
                val = convert_raw_voltage(raw_value)
                self._fcv_actual[index] = val
                self._fcv_expected[index] = val

    def read_once(self) -> Tuple[Dict[str, Union[List[float], List[bool]]], float]:
        now = time.time()
        
        # 1. GENERATE BINARY STREAM (Simulate Flight Computer)
        tx_buffer = bytearray()

        # Helper to pack 16-bit packet (Little Endian)
        def pack_packet(s_type, s_idx, s_val):
            # Packet: [2 bits Type] [4 bits Index] [10 bits Value]
            packet_int = (s_type << 14) | (s_idx << 10) | (s_val & 0x3FF)
            # Little Endian: Low Byte, High Byte
            tx_buffer.append(packet_int & 0xFF)
            tx_buffer.append((packet_int >> 8) & 0xFF)

        # -- Pack PTs --
        for i, config in enumerate(PT_CONFIGS):
            raw = self._generate_raw_pt(now, i, config)
            pack_packet(TYPE_PT, i, raw)

        # -- Pack TCs (Target ~25C) --
        for i in range(self.settings.NUM_THERMOCOUPLES):
            # Reverse generic: (25 / 1000) * 1023 ~= 25
            raw = int((random.uniform(20.0, 30.0) / 1000.0) * 1023.0)
            pack_packet(TYPE_TC, i, raw)

        # -- Pack LCs (Target ~5N) --
        for i in range(self.settings.NUM_LOAD_CELLS):
            raw = int((random.uniform(0.0, 10.0) / 5000.0) * 1023.0)
            pack_packet(TYPE_LC, i, raw)

        # -- Pack FCVs (Target Random Voltage) --
        for i in range(self.settings.NUM_FLOW_CONTROL_VALVES):
            raw = int((random.uniform(0.0, 5.0) / 5.0) * 1023.0)
            pack_packet(TYPE_FCV, i, raw)


        # 2. DECODE BINARY STREAM (Simulate Ground Station)
        # We iterate through the buffer exactly like SerialSource
        ptr = 0
        while ptr < len(tx_buffer):
            # Need at least 2 bytes
            if ptr + 1 >= len(tx_buffer):
                break
                
            b1 = tx_buffer[ptr]
            b2 = tx_buffer[ptr+1]
            
            # Reconstruction (Little Endian)
            packet = b1 | (b2 << 8)
            
            # Decoding
            raw_value = packet & 0x03FF
            header = (packet >> 10) & 0x3F
            index = header & 0x0F
            sensor_type = (header >> 4)

            self._process_packet(sensor_type, index, raw_value)
            
            ptr += 2

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
        pass

# ==========================================
#  SERIAL SOURCE (New Protocol)
# ==========================================

@dataclass
class SerialSource:
    settings: Settings
    update_interval_s: float = 0.001 

    _buffer: bytearray = field(default_factory=bytearray)

    def __post_init__(self) -> None:
        self._port = self.settings.SERIAL_PORT
        self._baud = self.settings.SERIAL_BAUDRATE
        self._ser = None
        
        # Initialize State Vectors
        self._pt = [0.0] * len(PT_CONFIGS)
        self._tc = [0.0] * self.settings.NUM_THERMOCOUPLES
        self._lc = [0.0] * self.settings.NUM_LOAD_CELLS
        self._fcv_actual = [0.0] * self.settings.NUM_FLOW_CONTROL_VALVES
        self._fcv_expected = [0.0] * self.settings.NUM_FLOW_CONTROL_VALVES

    def initialize(self) -> None:
        if serial is None:
            raise RuntimeError("pyserial not available.")
            
        try:
            self._ser = serial.Serial(port=self._port, baudrate=self._baud, timeout=0.01)
            time.sleep(0.5)
        except Exception as e:
            raise RuntimeError(f"Failed to open serial port {self._port}: {e}")

    def _process_packet(self, sensor_type: int, index: int, raw_value: int) -> None:
        """
        Updates internal state based on Type (2 bits) and Index (4 bits).
        """
        
        # --- TYPE 0: Pressure Transducers ---
        if sensor_type == TYPE_PT:
            if index < len(self._pt):
                # Retrieve config for this specific index
                config = PT_CONFIGS[index]
                self._pt[index] = convert_raw_pt_to_psi(raw_value, config)
        
        # --- TYPE 1: Thermocouples ---
        elif sensor_type == TYPE_TC:
            if index < len(self._tc):
                # Map 0-1023 -> 0-1000 C (Example)
                self._tc[index] = convert_raw_generic(raw_value, 0.0, 1000.0)

        # --- TYPE 2: Load Cells ---
        elif sensor_type == TYPE_LC:
            if index < len(self._lc):
                # Map 0-1023 -> 0-5000 N (Example)
                self._lc[index] = convert_raw_generic(raw_value, 0.0, 5000.0)

        # --- TYPE 3: Valves (FCV) ---
        elif sensor_type == TYPE_FCV:
            if index < len(self._fcv_actual):
                # Map 0-1023 -> 0-5V
                val = convert_raw_voltage(raw_value)
                self._fcv_actual[index] = val
                self._fcv_expected[index] = val

    def read_once(self) -> Tuple[Dict[str, Union[List[float], List[bool]]], float]:
        if self._ser is None:
            raise RuntimeError("Serial not initialized")
        
        try:
            if self._ser.in_waiting > 0:
                new_data = self._ser.read(self._ser.in_waiting)
                self._buffer.extend(new_data)

            # Process 2-byte chunks
            while len(self._buffer) >= 2:
                # Little Endian Reconstruction (Low Byte, High Byte)
                b1 = self._buffer[0]
                b2 = self._buffer[1]
                packet = b1 | (b2 << 8) 

                # --- NEW DECODING LOGIC ---
                # Bits 0-9:   Value (10 bits)
                # Bits 10-13: Index (4 bits)
                # Bits 14-15: Type  (2 bits)
                
                raw_value = packet & 0x03FF
                
                header = (packet >> 10) & 0x3F  # Get top 6 bits
                index = header & 0x0F           # Bottom 4 bits of header
                sensor_type = (header >> 4)     # Top 2 bits of header

                self._process_packet(sensor_type, index, raw_value)
                del self._buffer[:2]
            
            if hasattr(self.settings, '_freeze_detector'):
                self.settings._freeze_detector.heartbeat('serial_communication')
                
        except Exception:
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