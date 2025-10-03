"""Abstract data source interfaces"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import asyncio
from app.models.sensors import SensorReading, TelemetryPacket


class DataSource(ABC):
    """Abstract base class for all data sources"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.is_connected = False
        self.is_running = False
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the data source connection"""
        pass
    
    @abstractmethod
    async def read_sensors(self) -> TelemetryPacket:
        """Read all sensor data and return telemetry packet"""
        pass
    
    @abstractmethod
    async def close(self):
        """Close the data source connection"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check data source health status"""
        pass
    
    async def start(self) -> bool:
        """Start the data source"""
        try:
            success = await self.initialize()
            if success:
                self.is_running = True
            return success
        except Exception as e:
            await self.handle_error(f"Failed to start data source: {e}")
            return False
    
    async def stop(self):
        """Stop the data source"""
        try:
            await self.close()
            self.is_running = False
            self.is_connected = False
        except Exception as e:
            await self.handle_error(f"Error stopping data source: {e}")
    
    async def handle_error(self, error_message: str):
        """Handle data source errors"""
        print(f"DataSource Error: {error_message}")
        # In production, this would log to the logging system


class SensorDataSource(DataSource):
    """Base class for sensor data sources with common functionality"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.sensor_configs = {
            'pressure_transducers': config.get('pressure_transducers', []),
            'thermocouples': config.get('thermocouples', []),
            'load_cells': config.get('load_cells', []),
            'flow_control_valves': config.get('flow_control_valves', [])
        }
    
    def create_sensor_reading(self, sensor_id: str, value: float, 
                            raw_value: Optional[float] = None, 
                            unit: str = "unknown") -> SensorReading:
        """Create a validated sensor reading"""
        return SensorReading(
            sensor_id=sensor_id,
            value=value,
            raw_value=raw_value,
            unit=unit,
            calibrated=raw_value is not None
        )
    
    def create_telemetry_packet(self, 
                               pressure_readings: List[SensorReading] = None,
                               thermocouple_readings: List[SensorReading] = None,
                               load_cell_readings: List[SensorReading] = None,
                               valve_states: Dict[str, bool] = None) -> TelemetryPacket:
        """Create a complete telemetry packet"""
        return TelemetryPacket(
            pressure_transducers=pressure_readings or [],
            thermocouples=thermocouple_readings or [],
            load_cells=load_cell_readings or [],
            valve_states=valve_states or {},
            system_status="operational"
        )