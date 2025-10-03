"""Enhanced simulator for testing and calibration scenarios"""
import asyncio
import random
import math
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from app.data_sources.base import SensorDataSource
from app.models.sensors import SensorReading, TelemetryPacket


class SensorSimulator(SensorDataSource):
    """Enhanced simulator with noise, drift, and calibration testing support"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.simulation_time = 0.0
        self.base_values = {}
        self.drift_rates = {}
        self.noise_levels = {}
        self.calibration_offsets = {}
        self.is_simulating = False
        
        # Simulation parameters
        self.noise_enabled = config.get('noise_enabled', True)
        self.drift_enabled = config.get('drift_enabled', True)
        self.min_value = config.get('simulator_min_value', 300)
        self.max_value = config.get('simulator_max_value', 700)
        
        self._initialize_sensor_parameters()
    
    def _initialize_sensor_parameters(self):
        """Initialize simulation parameters for each sensor"""
        # Initialize pressure transducers
        for sensor in self.sensor_configs['pressure_transducers']:
            sensor_id = sensor['id']
            self.base_values[sensor_id] = random.uniform(self.min_value, self.max_value)
            self.drift_rates[sensor_id] = random.uniform(-0.1, 0.1)  # PSI per hour
            self.noise_levels[sensor_id] = random.uniform(0.5, 2.0)  # PSI noise
            self.calibration_offsets[sensor_id] = 0.0
        
        # Initialize thermocouples
        for sensor in self.sensor_configs['thermocouples']:
            sensor_id = sensor['id']
            self.base_values[sensor_id] = random.uniform(20, 200)  # Temperature range
            self.drift_rates[sensor_id] = random.uniform(-0.05, 0.05)  # °C per hour
            self.noise_levels[sensor_id] = random.uniform(0.2, 1.0)  # °C noise
            self.calibration_offsets[sensor_id] = 0.0
        
        # Initialize load cells
        for sensor in self.sensor_configs['load_cells']:
            sensor_id = sensor['id']
            self.base_values[sensor_id] = random.uniform(50, 300)  # Force range
            self.drift_rates[sensor_id] = random.uniform(-0.02, 0.02)  # lbf per hour
            self.noise_levels[sensor_id] = random.uniform(0.1, 0.5)  # lbf noise
            self.calibration_offsets[sensor_id] = 0.0
    
    async def initialize(self) -> bool:
        """Initialize the simulator"""
        try:
            self.is_simulating = True
            self.is_connected = True
            await asyncio.sleep(0.1)  # Simulate initialization delay
            return True
        except Exception as e:
            await self.handle_error(f"Simulator initialization failed: {e}")
            return False
    
    async def read_sensors(self) -> TelemetryPacket:
        """Generate simulated sensor data"""
        if not self.is_simulating:
            raise Exception("Simulator not initialized")
        
        # Advance simulation time
        self.simulation_time += 0.1  # 100ms intervals
        
        pressure_readings = await self._generate_pressure_readings()
        thermocouple_readings = await self._generate_thermocouple_readings()
        load_cell_readings = await self._generate_load_cell_readings()
        valve_states = await self._generate_valve_states()
        
        return self.create_telemetry_packet(
            pressure_readings=pressure_readings,
            thermocouple_readings=thermocouple_readings,
            load_cell_readings=load_cell_readings,
            valve_states=valve_states
        )
    
    async def _generate_pressure_readings(self) -> List[SensorReading]:
        """Generate simulated pressure transducer readings"""
        readings = []
        
        for sensor in self.sensor_configs['pressure_transducers']:
            sensor_id = sensor['id']
            
            # Base value with sinusoidal variation
            base_value = self.base_values[sensor_id]
            variation = 20 * math.sin(self.simulation_time * 0.1)  # Slow variation
            
            # Add drift over time
            if self.drift_enabled:
                drift = self.drift_rates[sensor_id] * (self.simulation_time / 3600)  # Convert to hours
                base_value += drift
            
            # Add noise
            noise = 0
            if self.noise_enabled:
                noise = random.gauss(0, self.noise_levels[sensor_id])
            
            # Add calibration offset
            calibration_offset = self.calibration_offsets[sensor_id]
            
            # Calculate final value
            final_value = base_value + variation + noise + calibration_offset
            
            # Generate raw voltage (for testing calibration)
            raw_voltage = self._psi_to_voltage(final_value, sensor['name'])
            
            reading = self.create_sensor_reading(
                sensor_id=sensor_id,
                value=final_value,
                raw_value=raw_voltage,
                unit="psi"
            )
            readings.append(reading)
        
        return readings
    
    async def _generate_thermocouple_readings(self) -> List[SensorReading]:
        """Generate simulated thermocouple readings"""
        readings = []
        
        for sensor in self.sensor_configs['thermocouples']:
            sensor_id = sensor['id']
            
            # Base temperature with variation
            base_temp = self.base_values[sensor_id]
            variation = 10 * math.sin(self.simulation_time * 0.05)
            
            # Add drift
            if self.drift_enabled:
                drift = self.drift_rates[sensor_id] * (self.simulation_time / 3600)
                base_temp += drift
            
            # Add noise
            noise = 0
            if self.noise_enabled:
                noise = random.gauss(0, self.noise_levels[sensor_id])
            
            # Add calibration offset
            calibration_offset = self.calibration_offsets[sensor_id]
            
            final_temp = base_temp + variation + noise + calibration_offset
            
            reading = self.create_sensor_reading(
                sensor_id=sensor_id,
                value=final_temp,
                unit="°C"
            )
            readings.append(reading)
        
        return readings
    
    async def _generate_load_cell_readings(self) -> List[SensorReading]:
        """Generate simulated load cell readings"""
        readings = []
        
        for sensor in self.sensor_configs['load_cells']:
            sensor_id = sensor['id']
            
            # Base force with variation
            base_force = self.base_values[sensor_id]
            variation = 5 * math.sin(self.simulation_time * 0.2)
            
            # Add drift
            if self.drift_enabled:
                drift = self.drift_rates[sensor_id] * (self.simulation_time / 3600)
                base_force += drift
            
            # Add noise
            noise = 0
            if self.noise_enabled:
                noise = random.gauss(0, self.noise_levels[sensor_id])
            
            # Add calibration offset
            calibration_offset = self.calibration_offsets[sensor_id]
            
            final_force = base_force + variation + noise + calibration_offset
            
            reading = self.create_sensor_reading(
                sensor_id=sensor_id,
                value=final_force,
                unit="lbf"
            )
            readings.append(reading)
        
        return readings
    
    async def _generate_valve_states(self) -> Dict[str, bool]:
        """Generate simulated valve states"""
        valve_states = {}
        
        for valve in self.sensor_configs['flow_control_valves']:
            valve_id = valve['id']
            # Simple cycling pattern for demo
            cycle_time = 10.0  # 10 second cycle
            is_open = (self.simulation_time % cycle_time) < (cycle_time / 2)
            valve_states[valve_id] = is_open
        
        return valve_states
    
    def _psi_to_voltage(self, psi_value: float, sensor_name: str) -> float:
        """Convert PSI back to voltage (inverse of serial reader conversion)"""
        # Use same conversion parameters as serial reader
        if 'GN2' in sensor_name:
            conversion = {
                'min_voltage': 0.5,
                'max_voltage': 4.5,
                'max_psi': 5000,
                'offset': -23.55,
            }
        else:
            conversion = {
                'min_voltage': 1.0,
                'max_voltage': 5.0,
                'max_psi': 1000,
                'offset': -8.55,
            }
        
        # Inverse conversion: PSI -> voltage
        voltage_normalized = (psi_value - conversion['offset']) / conversion['max_psi']
        voltage = voltage_normalized * (conversion['max_voltage'] - conversion['min_voltage']) + conversion['min_voltage']
        
        return round(voltage, 3)
    
    async def inject_calibration_offset(self, sensor_id: str, offset: float):
        """Inject calibration offset for testing calibration algorithms"""
        if sensor_id in self.calibration_offsets:
            self.calibration_offsets[sensor_id] = offset
    
    async def set_sensor_drift_rate(self, sensor_id: str, drift_rate: float):
        """Set drift rate for testing drift detection"""
        if sensor_id in self.drift_rates:
            self.drift_rates[sensor_id] = drift_rate
    
    async def set_sensor_noise_level(self, sensor_id: str, noise_level: float):
        """Set noise level for testing calibration under different conditions"""
        if sensor_id in self.noise_levels:
            self.noise_levels[sensor_id] = noise_level
    
    async def reset_sensor(self, sensor_id: str):
        """Reset sensor to initial state"""
        if sensor_id in self.calibration_offsets:
            self.calibration_offsets[sensor_id] = 0.0
            self.drift_rates[sensor_id] = random.uniform(-0.1, 0.1)
            self.noise_levels[sensor_id] = random.uniform(0.5, 2.0)
    
    async def close(self):
        """Close the simulator"""
        self.is_simulating = False
        self.is_connected = False
    
    async def health_check(self) -> Dict[str, Any]:
        """Check simulator health"""
        return {
            "connected": self.is_connected,
            "simulating": self.is_simulating,
            "simulation_time": self.simulation_time,
            "noise_enabled": self.noise_enabled,
            "drift_enabled": self.drift_enabled,
            "sensor_count": len(self.base_values)
        }