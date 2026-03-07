from __future__ import annotations

import time
import random
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol, Tuple, Union, Optional

try:
    import serial  # pyserial
except Exception:
    serial = None

from ..config.loader import Settings
from .protocol_parser import TelemetryParser

# Logger setup
logger = logging.getLogger("blast.datasource")

# ==========================================
#  DATA SOURCE INTERFACE
# ==========================================

class DataSource(Protocol):
    def initialize(self) -> None: ...
    def read_once(self) -> Tuple[Dict[str, Union[List[float], List[bool]]], float]: ...
    def shutdown(self) -> None: ...

# ==========================================
#  SIMULATOR (Updated to New Struct Layout)
# ==========================================

@dataclass
class SimulatorSource:
    settings: Settings
    update_interval_s: float = 0.05

    def initialize(self) -> None:
        self._t0 = time.time()

    def read_once(self) -> Tuple[Dict[str, Union[List[float], List[bool]]], float]:
        now = time.time()
        
        # Simulate 7 PTs (Pressure)
        # Just some sine waves and noise for visual variance
        pt_values = []
        for i in range(7):
            val = 275.0 + 150.0 * math.sin(time.time()* random.random())
            if i == 0: # GN2 (sine wave)
                val = 2500.0 + 500.0 * math.sin(time.time())
            pt_values.append(val)

        # Simulate 3 LCs (Load Cells)
        lc_values = [random.uniform(0, 10) for _ in range(3)]

        # Simulate 5 TCs (Thermocouples)
        tc_values = [random.uniform(20, 30) for _ in range(5)]

        # FCVs are not in the packet, filling with 0s to satisfy frontend contract
        num_fcv = self.settings.NUM_FLOW_CONTROL_VALVES
        fcv_actual = [False] * num_fcv
        fcv_expected = [False] * num_fcv

        value = {
            "pt": pt_values,
            "tc": tc_values,
            "lc": lc_values,
            "fcv_actual": fcv_actual,
            "fcv_expected": fcv_expected,
            "timestamp": now,
        }
        return value, now

    def shutdown(self) -> None:
        pass

import math # late import for simulator logic

# ==========================================
#  SERIAL SOURCE (Implements Handshake & Protocol)
# ==========================================

@dataclass
class SerialSource:
    settings: Settings
    update_interval_s: float = 0.001 

    def __post_init__(self) -> None:
        self._port = self.settings.SERIAL_PORT
        self._baud = self.settings.SERIAL_BAUDRATE
        self._ser: Optional[serial.Serial] = None
        self._parser = TelemetryParser()
        
        # Internal state cache
        self._last_pt = [0.0] * 7
        self._last_lc = [0.0] * 3
        self._last_tc = [0.0] * 5
        self._last_fcv_actual = [False] * self.settings.NUM_FLOW_CONTROL_VALVES
        self._last_fcv_expected = [False] * self.settings.NUM_FLOW_CONTROL_VALVES

    def initialize(self) -> None:
        if serial is None:
            raise RuntimeError("pyserial not installed.")
        
                # Get serial logger if available
        self._serial_logger = getattr(self.settings, '_serial_logger', None)
        
        if self._serial_logger:
            self._serial_logger.log_connection_attempt(self._port, self._baud)
            
        try:
            # Opening port typically resets Arduino (DTR toggle)
            self._ser = serial.Serial(port=self._port, baudrate=self._baud, timeout=1.0)
            if self._serial_logger:
                self._serial_logger.log_connection_success(self._port, self._baud)
            
            # --- HANDSHAKE PROTOCOL ---

            self._perform_handshake()
            
            # Switch to non-blocking or short timeout for data loop
            self._ser.timeout = 0.01

        except Exception as e:  # pragma: no cover
            if self._serial_logger:
                self._serial_logger.log_connection_failure(self._port, self._baud, str(e))
            raise RuntimeError(f"Failed to open serial port {self._port}: {e}")

    def _perform_handshake(self) -> None:
        """
        Waits for 'HANDSHAKE_INIT' from Arduino, then sends 'HANDSHAKE_ACK'.
        """
        max_retries = 50 # 50 seconds roughly if timeout is 1s
        
        for i in range(max_retries):
            # Read line (blocking with timeout)
            try:
                line = self._ser.readline().decode('ascii', errors='ignore').strip()
            except Exception:
                continue

            if line == "HANDSHAKE_INIT":
                self._serial_logger.log_handshake_received(self._port,self._baud)
                time.sleep(0.1) # Brief pause to ensure Arduino is listening
                self._ser.write(b"HANDSHAKE_ACK\n")
                self._ser.flush()
                #Handshake achnoledge sent
                self._serial_logger.log_handshake_attempt(self._port, self._baud, i, True)
                return
            
            #Handshake not recieved yet
            self._serial_logger.log_handshake_attempt(self._port, self._baud, i, False)

        self._serial_logger.log_handshake_failed(self._port, self._baud)
        raise TimeoutError("Timed out waiting for HANDSHAKE_INIT from Arduino.")

    def read_once(self) -> Tuple[Dict[str, Union[List[float], List[bool]]], float]:
        if self._ser is None:
            raise RuntimeError("Serial not initialized")
        
        try:
            # Read all available bytes
            if self._ser.in_waiting > 0:
                raw_chunk = self._ser.read(self._ser.in_waiting)  

                if (raw_chunk):
                    self._serial_logger.log_data_read(raw_chunk, self._port,True)
                else:
                    self._serial_logger.log_data_read(raw_chunk, self._port, False)



                # Feed to parser
                packets = self._parser.feed(raw_chunk)
                
                if(len(packets) == 0):
                    self._serial_logger.log_data_parse(raw_chunk, packets,True)
                else:
                    self._serial_logger.log_data_parse(raw_chunk, packets,False)

                    
                # Process all valid packets, keeping the latest one
                for pkt in packets:
                    self._last_pt = pkt['pt']
                    self._last_lc = pkt['lc']
                    self._last_tc = pkt['tc']
            
            # Heartbeat
            if hasattr(self.settings, '_freeze_detector'):
                self.settings._freeze_detector.heartbeat('serial_communication')
                
        except Exception as e:  # pragma: no cover
            if self._serial_logger:
                self._serial_logger.log_data_read('', self._port, False, str(e))
            # Keep last values on transient errors
            pass
            
        now = time.time()
        
        # Return state
        value = {
            "pt": list(self._last_pt),
            "tc": list(self._last_tc),
            "lc": list(self._last_lc),
            "fcv_actual": list(self._last_fcv_actual),
            "fcv_expected": list(self._last_fcv_expected),
            "timestamp": now,
        }
        return value, now

    def shutdown(self) -> None:
        try:
            if self._ser and self._ser.is_open:
                self._ser.close()
        except Exception:
            pass