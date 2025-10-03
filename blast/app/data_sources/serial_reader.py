"""Async serial communication for sensor data"""
import asyncio
import json
import serial
import serial.tools.list_ports
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.data_sources.base import SensorDataSource
from app.models.sensors import SensorReading, TelemetryPacket
from app.core.exceptions import DataAcquisitionException


class AsyncSerialReader(SensorDataSource):
    """Async serial communication with hardware sensors"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.serial_port = config.get('serial_port', '/dev/cu.usbmodem1201')
        self.baudrate = config.get('serial_baudrate', 115200)
        self.timeout = config.get('serial_timeout', 1.0)
        self.serial_connection = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 2.0
        
        # PT conversion parameters from original config
        self.pt_conversion = {
            'GN2': {
                'min_voltage': 0.5,
                'max_voltage': 4.5,
                'max_psi': 5000,
                'offset': -23.55,
            },
            'other': {
                'min_voltage': 1.0,
                'max_voltage': 5.0,
                'max_psi': 1000,
                'offset': -8.55,
            }
        }
    
    async def initialize(self) -> bool:
        """Initialize serial connection"""
        try:
            # Check if port exists
            available_ports = [port.device for port in serial.tools.list_ports.comports()]
            if self.serial_port not in available_ports:
                await self.handle_error(f"Serial port {self.serial_port} not found. Available: {available_ports}")
                return False
            
            # Open serial connection
            self.serial_connection = serial.Serial(
                port=self.serial_port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=1.0
            )
            
            # Wait for Arduino initialization
            await asyncio.sleep(2.0)
            
            # Test connection with a simple read
            test_data = await self._read_serial_data()
            if test_data is None:
                await self.handle_error("No data received from serial port")
                return False
            
            self.is_connected = True
            self.reconnect_attempts = 0
            return True
            
        except Exception as e:
            await self.handle_error(f"Serial initialization failed: {e}")
            return False
    
    async def read_sensors(self) -> TelemetryPacket:
        """Read sensor data from serial port"""
        if not self.is_connected or not self.serial_connection:
            raise DataAcquisitionException("Serial connection not initialized")
        
        try:
            # Read raw data from serial
            raw_data = await self._read_serial_data()
            if raw_data is None:
                raise DataAcquisitionException("No data received from serial port")
            
            # Parse and convert sensor data
            return await self._parse_sensor_data(raw_data)
            
        except Exception as e:
            await self.handle_error(f"Error reading sensors: {e}")
            # Attempt reconnection
            if await self._attempt_reconnection():
                return await self.read_sensors()
            else:
                raise DataAcquisitionException(f"Failed to read sensors: {e}")
    
    async def _read_serial_data(self) -> Optional[Dict]:
        """Read and parse JSON data from serial port"""
        try:
            # Run serial read in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            line = await loop.run_in_executor(None, self._read_line)
            
            if not line:
                return None
            
            # Parse JSON data
            data = json.loads(line)
            return data.get('value', {})
            
        except json.JSONDecodeError as e:
            await self.handle_error(f"Invalid JSON received: {e}")
            return None
        except Exception as e:
            await self.handle_error(f"Serial read error: {e}")
            return None
    
    def _read_line(self) -> str:
        """Blocking serial read (runs in thread pool)"""
        if self.serial_connection and self.serial_connection.in_waiting > 0:
            line = self.serial_connection.readline().decode('utf-8').strip()
            return line
        return ""
    
    async def _parse_sensor_data(self, raw_data: Dict) -> TelemetryPacket:
        """Parse raw sensor data into calibrated readings"""
        pressure_readings = []
        thermocouple_readings = []
        load_cell_readings = []
        valve_states = {}
        
        # Parse pressure transducers
        pt_data = raw_data.get('pt', [])
        for i, voltage in enumerate(pt_data):
            if i < len(self.sensor_configs['pressure_transducers']):
                sensor_config = self.sensor_configs['pressure_transducers'][i]
                psi_value = self._convert_voltage_to_psi(voltage, sensor_config['name'])
                
                reading = self.create_sensor_reading(
                    sensor_id=sensor_config['id'],
                    value=psi_value,
                    raw_value=voltage,
                    unit="psi"
                )
                pressure_readings.append(reading)
        
        # Parse thermocouples
        tc_data = raw_data.get('tc', [])
        for i, temp_value in enumerate(tc_data):
            if i < len(self.sensor_configs['thermocouples']):
                sensor_config = self.sensor_configs['thermocouples'][i]
                
                reading = self.create_sensor_reading(
                    sensor_id=sensor_config['id'],
                    value=temp_value,
                    unit="°C"
                )
                thermocouple_readings.append(reading)
        
        # Parse load cells
        lc_data = raw_data.get('lc', [])
        for i, force_value in enumerate(lc_data):
            if i < len(self.sensor_configs['load_cells']):
                sensor_config = self.sensor_configs['load_cells'][i]
                
                reading = self.create_sensor_reading(
                    sensor_id=sensor_config['id'],
                    value=force_value,
                    unit="lbf"
                )
                load_cell_readings.append(reading)
        
        # Parse valve states
        fcv_actual = raw_data.get('fcv_actual', [])
        for i, state in enumerate(fcv_actual):
            if i < len(self.sensor_configs['flow_control_valves']):
                valve_config = self.sensor_configs['flow_control_valves'][i]
                valve_states[valve_config['id']] = bool(state)
        
        return self.create_telemetry_packet(
            pressure_readings=pressure_readings,
            thermocouple_readings=thermocouple_readings,
            load_cell_readings=load_cell_readings,
            valve_states=valve_states
        )
    
    def _convert_voltage_to_psi(self, voltage: float, sensor_name: str) -> float:
        """Convert voltage reading to PSI using calibration parameters"""
        # Use GN2 conversion for GN2 sensor, otherwise use 'other'
        conversion = self.pt_conversion['GN2'] if 'GN2' in sensor_name else self.pt_conversion['other']
        
        # Linear conversion from voltage to PSI
        voltage_range = conversion['max_voltage'] - conversion['min_voltage']
        voltage_normalized = (voltage - conversion['min_voltage']) / voltage_range
        psi_value = voltage_normalized * conversion['max_psi'] + conversion['offset']
        
        return round(psi_value, 2)
    
    async def _attempt_reconnection(self) -> bool:
        """Attempt to reconnect to serial port"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            return False
        
        self.reconnect_attempts += 1
        await self.handle_error(f"Attempting reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts}")
        
        try:
            if self.serial_connection:
                self.serial_connection.close()
            
            await asyncio.sleep(self.reconnect_delay)
            return await self.initialize()
            
        except Exception as e:
            await self.handle_error(f"Reconnection attempt failed: {e}")
            return False
    
    async def close(self):
        """Close serial connection"""
        if self.serial_connection:
            try:
                self.serial_connection.close()
            except Exception as e:
                await self.handle_error(f"Error closing serial connection: {e}")
            finally:
                self.serial_connection = None
                self.is_connected = False
    
    async def health_check(self) -> Dict[str, Any]:
        """Check serial connection health"""
        return {
            "connected": self.is_connected,
            "port": self.serial_port,
            "baudrate": self.baudrate,
            "reconnect_attempts": self.reconnect_attempts,
            "max_reconnect_attempts": self.max_reconnect_attempts
        }