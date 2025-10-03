"""Data acquisition service coordination"""
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from app.data_sources.base import DataSource
from app.data_sources.serial_reader import AsyncSerialReader
from app.data_sources.simulator import SensorSimulator
from app.services.calibration import CalibrationService
from app.models.sensors import TelemetryPacket
from app.core.exceptions import DataAcquisitionException
from app.config.settings import Settings, DataSourceType
from app.migration.flask_compatibility import create_flask_compatible_data_source


class DataAcquisitionService:
    """Coordinates data sources and calibration for real-time sensor data"""
    
    def __init__(self, settings: Settings, calibration_service: CalibrationService = None):
        self.settings = settings
        self.calibration_service = calibration_service or CalibrationService("calibration_states.json")
        self.data_source: Optional[DataSource] = None
        self.is_running = False
        self.last_reading_time: Optional[datetime] = None
        self.error_count = 0
        self.max_errors = 10
        
        # Create appropriate data source based on configuration
        self._create_data_source()
    
    def _create_data_source(self):
        """Create data source based on configuration"""
        # Try Flask compatibility layer first (for migration)
        try:
            self.data_source = create_flask_compatible_data_source(self.settings)
            print("✅ Using Flask compatibility layer for data source")
            return
        except Exception as e:
            print(f"Flask compatibility not available, using native sources: {e}")
        
        # Fallback to native FastAPI data sources
        config = {
            'pressure_transducers': [pt.dict() for pt in self.settings.pressure_transducers],
            'thermocouples': [tc.dict() for tc in self.settings.thermocouples],
            'load_cells': [lc.dict() for lc in self.settings.load_cells],
            'flow_control_valves': self.settings.flow_control_valves,
            'serial_port': self.settings.serial_port,
            'serial_baudrate': self.settings.serial_baudrate,
            'noise_enabled': True,
            'drift_enabled': True
        }
        
        if self.settings.data_source == DataSourceType.SERIAL:
            self.data_source = AsyncSerialReader(config)
        else:
            self.data_source = SensorSimulator(config)
    
    async def start(self) -> bool:
        """Start data acquisition service"""
        if self.is_running:
            return True
        
        try:
            if not self.data_source:
                raise DataAcquisitionException("Data source not initialized")
            
            # Initialize data source
            success = await self.data_source.start()
            if not success:
                raise DataAcquisitionException("Failed to start data source")
            
            self.is_running = True
            self.error_count = 0
            return True
            
        except Exception as e:
            await self._handle_error(f"Failed to start data acquisition: {e}")
            return False
    
    async def stop(self):
        """Stop data acquisition service"""
        if self.data_source:
            await self.data_source.stop()
        self.is_running = False
    
    async def get_calibrated_reading(self) -> TelemetryPacket:
        """Get sensor reading with applied calibrations"""
        if not self.is_running or not self.data_source:
            raise DataAcquisitionException("Data acquisition service not running")
        
        try:
            # Read raw sensor data
            raw_telemetry = await self.data_source.read_sensors()
            
            # Apply calibrations to all sensor readings
            calibrated_telemetry = await self._apply_calibrations(raw_telemetry)
            
            # Update last reading time
            self.last_reading_time = datetime.now()
            
            # Reset error count on successful reading
            if self.error_count > 0:
                self.error_count = 0
            
            return calibrated_telemetry
            
        except Exception as e:
            await self._handle_error(f"Error reading sensors: {e}")
            raise DataAcquisitionException(f"Failed to get calibrated reading: {e}")
    
    async def _apply_calibrations(self, raw_telemetry: TelemetryPacket) -> TelemetryPacket:
        """Apply calibrations to all sensor readings in telemetry packet"""
        calibrated_pt = []
        calibrated_tc = []
        calibrated_lc = []
        
        # Calibrate pressure transducers
        for reading in raw_telemetry.pressure_transducers:
            calibrated = await self.calibration_service.apply_calibration(reading)
            calibrated_pt.append(calibrated)
        
        # Calibrate thermocouples
        for reading in raw_telemetry.thermocouples:
            calibrated = await self.calibration_service.apply_calibration(reading)
            calibrated_tc.append(calibrated)
        
        # Calibrate load cells
        for reading in raw_telemetry.load_cells:
            calibrated = await self.calibration_service.apply_calibration(reading)
            calibrated_lc.append(calibrated)
        
        # Create calibrated telemetry packet
        return TelemetryPacket(
            timestamp=raw_telemetry.timestamp,
            pressure_transducers=calibrated_pt,
            thermocouples=calibrated_tc,
            load_cells=calibrated_lc,
            valve_states=raw_telemetry.valve_states,
            system_status=raw_telemetry.system_status
        )
    
    async def _handle_error(self, error_message: str):
        """Handle data acquisition errors"""
        self.error_count += 1
        print(f"DataAcquisition Error ({self.error_count}/{self.max_errors}): {error_message}")
        
        # If too many errors, stop the service
        if self.error_count >= self.max_errors:
            print("Maximum errors reached, stopping data acquisition")
            await self.stop()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check data acquisition service health"""
        data_source_health = {}
        if self.data_source:
            data_source_health = await self.data_source.health_check()
        
        return {
            "running": self.is_running,
            "data_source_type": self.settings.data_source.value,
            "last_reading": self.last_reading_time.isoformat() if self.last_reading_time else None,
            "error_count": self.error_count,
            "max_errors": self.max_errors,
            "data_source": data_source_health
        }
    
    async def perform_sensor_calibration(self, sensor_id: str, calibration_type: str, **kwargs):
        """Perform sensor calibration using the data acquisition service"""
        if not self.is_running:
            raise DataAcquisitionException("Data acquisition service not running")
        
        if calibration_type == "auto_zero":
            duration_ms = kwargs.get('duration_ms', 5000)
            return await self.calibration_service.auto_zero_calibration(
                sensor_id, self.data_source, duration_ms
            )
        elif calibration_type == "span":
            reference_value = kwargs.get('reference_value')
            measured_value = kwargs.get('measured_value')
            if reference_value is None or measured_value is None:
                raise DataAcquisitionException("Span calibration requires reference_value and measured_value")
            return await self.calibration_service.span_calibration(
                sensor_id, reference_value, measured_value
            )
        else:
            raise DataAcquisitionException(f"Unknown calibration type: {calibration_type}")
    
    async def get_calibration_state(self, sensor_id: str):
        """Get current calibration state for a sensor"""
        return await self.calibration_service.get_calibration_state(sensor_id)
    
    async def monitor_sensor_drift(self, sensor_id: str, current_reading: float):
        """Monitor sensor for drift and return alert if needed"""
        return await self.calibration_service.monitor_drift(sensor_id, current_reading)