"""Industrial-grade calibration service with advanced algorithms"""
import asyncio
import statistics
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from app.models.calibration import (
    CalibrationState, CalibrationResult, CalibrationHistory, 
    DriftAlert, CalibrationType
)
from app.models.sensors import SensorReading
from app.core.exceptions import CalibrationException


class CalibrationService:
    """Industrial-grade sensor calibration service"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.calibration_states: Dict[str, CalibrationState] = {}
        self.calibration_histories: Dict[str, CalibrationHistory] = {}
        self.drift_monitoring_enabled = True
        self.config_path = config_path or "calibration_states.json"
        
        # Calibration parameters
        self.default_measurement_duration_ms = 5000
        self.default_noise_threshold = 0.1
        self.drift_check_interval_hours = 1.0
        self.drift_threshold_percent = 2.0
        
        # Load existing calibration states
        asyncio.create_task(self.load_calibration_states())
    
    async def auto_zero_calibration(self, 
                                  sensor_id: str,
                                  data_source,
                                  measurement_duration_ms: int = None) -> CalibrationResult:
        """
        Perform automatic zero calibration using industrial auto-zero technique.
        Averages multiple readings at zero pressure condition for statistical accuracy.
        """
        if measurement_duration_ms is None:
            measurement_duration_ms = self.default_measurement_duration_ms
        
        try:
            # Collect multiple readings for statistical accuracy
            readings = []
            measurement_count = measurement_duration_ms // 100  # 100ms intervals
            
            for i in range(measurement_count):
                try:
                    # Read sensor data
                    telemetry = await data_source.read_sensors()
                    sensor_reading = self._find_sensor_reading(telemetry, sensor_id)
                    
                    if sensor_reading:
                        # Use raw value if available, otherwise use calibrated value
                        value = sensor_reading.raw_value if sensor_reading.raw_value is not None else sensor_reading.value
                        readings.append(value)
                    
                    await asyncio.sleep(0.1)  # 100ms interval
                except Exception as e:
                    # Continue collecting readings even if some fail
                    continue
            
            if len(readings) < measurement_count * 0.8:  # Need at least 80% successful readings
                return CalibrationResult(
                    success=False,
                    sensor_id=sensor_id,
                    calibration_type=CalibrationType.AUTO_ZERO,
                    error=f"Insufficient readings collected: {len(readings)}/{measurement_count}"
                )
            
            # Calculate statistical parameters
            zero_offset = statistics.mean(readings)
            std_dev = statistics.stdev(readings) if len(readings) > 1 else 0
            
            # Validate calibration quality
            noise_threshold = self.default_noise_threshold
            if std_dev > noise_threshold:
                return CalibrationResult(
                    success=False,
                    sensor_id=sensor_id,
                    calibration_type=CalibrationType.AUTO_ZERO,
                    error=f"Excessive noise during calibration: {std_dev:.3f} > {noise_threshold}",
                    noise_level=std_dev,
                    measurement_count=len(readings)
                )
            
            # Get previous calibration state
            previous_state = self.calibration_states.get(sensor_id)
            previous_offset = previous_state.zero_offset if previous_state else 0.0
            
            # Calculate accuracy improvement
            accuracy_improvement = self._calculate_accuracy_improvement(
                previous_offset, zero_offset, std_dev
            )
            
            # Update calibration state
            await self._update_calibration_state(
                sensor_id=sensor_id,
                zero_offset=zero_offset,
                calibration_type=CalibrationType.AUTO_ZERO,
                quality=1.0 - (std_dev / noise_threshold)  # Quality inversely related to noise
            )
            
            # Create successful result
            result = CalibrationResult(
                success=True,
                sensor_id=sensor_id,
                calibration_type=CalibrationType.AUTO_ZERO,
                previous_offset=previous_offset,
                new_offset=zero_offset,
                accuracy_improvement=accuracy_improvement,
                measurement_count=len(readings),
                noise_level=std_dev
            )
            
            # Add to calibration history
            await self._add_calibration_event(sensor_id, result)
            
            return result
            
        except Exception as e:
            return CalibrationResult(
                success=False,
                sensor_id=sensor_id,
                calibration_type=CalibrationType.AUTO_ZERO,
                error=f"Calibration procedure failed: {str(e)}"
            )
    
    async def span_calibration(self, 
                              sensor_id: str,
                              reference_value: float,
                              measured_value: float) -> CalibrationResult:
        """
        Perform span calibration using known reference pressure/temperature.
        Adjusts the span multiplier for full-scale accuracy.
        """
        try:
            # Get current calibration state
            current_state = self.calibration_states.get(sensor_id)
            if not current_state:
                # Initialize with default state
                current_state = CalibrationState(sensor_id=sensor_id)
                self.calibration_states[sensor_id] = current_state
            
            # Apply zero offset correction first
            zero_corrected_value = measured_value - current_state.zero_offset
            
            # Calculate span multiplier
            if abs(zero_corrected_value) < 1e-6:  # Avoid division by zero
                return CalibrationResult(
                    success=False,
                    sensor_id=sensor_id,
                    calibration_type=CalibrationType.SPAN,
                    error="Measured value too close to zero after offset correction"
                )
            
            new_span_multiplier = reference_value / zero_corrected_value
            
            # Validate span multiplier is reasonable
            if not (0.1 <= new_span_multiplier <= 10.0):
                return CalibrationResult(
                    success=False,
                    sensor_id=sensor_id,
                    calibration_type=CalibrationType.SPAN,
                    error=f"Calculated span multiplier out of range: {new_span_multiplier:.3f}"
                )
            
            # Calculate accuracy improvement
            previous_span = current_state.span_multiplier
            accuracy_improvement = abs(1.0 - previous_span) - abs(1.0 - new_span_multiplier)
            accuracy_improvement = (accuracy_improvement / abs(1.0 - previous_span)) * 100 if previous_span != 1.0 else 0
            
            # Update calibration state
            await self._update_calibration_state(
                sensor_id=sensor_id,
                span_multiplier=new_span_multiplier,
                calibration_type=CalibrationType.SPAN
            )
            
            result = CalibrationResult(
                success=True,
                sensor_id=sensor_id,
                calibration_type=CalibrationType.SPAN,
                previous_span=previous_span,
                new_span=new_span_multiplier,
                accuracy_improvement=accuracy_improvement
            )
            
            await self._add_calibration_event(sensor_id, result)
            return result
            
        except Exception as e:
            return CalibrationResult(
                success=False,
                sensor_id=sensor_id,
                calibration_type=CalibrationType.SPAN,
                error=f"Span calibration failed: {str(e)}"
            )
    
    async def temperature_compensation(self, 
                                     sensor_id: str,
                                     sensor_reading: float,
                                     ambient_temperature: float) -> float:
        """
        Apply temperature coefficient compensation for temperature-sensitive sensors.
        """
        state = self.calibration_states.get(sensor_id)
        if not state or state.temperature_coefficient == 0.0:
            return sensor_reading
        
        # Apply temperature compensation: reading + coeff * (temp - 25°C)
        reference_temp = 25.0  # Reference temperature in Celsius
        temp_correction = state.temperature_coefficient * (ambient_temperature - reference_temp)
        compensated_reading = sensor_reading + temp_correction
        
        return compensated_reading
    
    async def apply_calibration(self, sensor_reading: SensorReading, 
                               ambient_temperature: Optional[float] = None) -> SensorReading:
        """Apply full calibration to a sensor reading"""
        sensor_id = sensor_reading.sensor_id
        state = self.calibration_states.get(sensor_id)
        
        if not state:
            # Return original reading if no calibration available
            return sensor_reading
        
        # Start with raw value if available, otherwise use current value
        base_value = sensor_reading.raw_value if sensor_reading.raw_value is not None else sensor_reading.value
        
        # Apply zero offset correction
        zero_corrected = base_value - state.zero_offset
        
        # Apply span correction
        span_corrected = zero_corrected * state.span_multiplier
        
        # Apply temperature compensation if available
        final_value = span_corrected
        if ambient_temperature is not None:
            final_value = await self.temperature_compensation(sensor_id, span_corrected, ambient_temperature)
        
        # Create calibrated reading
        calibrated_reading = SensorReading(
            sensor_id=sensor_reading.sensor_id,
            value=final_value,
            raw_value=sensor_reading.raw_value,
            unit=sensor_reading.unit,
            timestamp=sensor_reading.timestamp,
            quality=sensor_reading.quality,
            calibrated=True
        )
        
        return calibrated_reading
    
    async def monitor_drift(self, sensor_id: str, current_reading: float) -> Optional[DriftAlert]:
        """Monitor calibration drift over time and alert when thresholds exceeded"""
        if not self.drift_monitoring_enabled:
            return None
        
        state = self.calibration_states.get(sensor_id)
        if not state or not state.last_calibrated:
            return None
        
        # Check if enough time has passed for drift monitoring
        time_since_calibration = datetime.now() - state.last_calibrated
        if time_since_calibration < timedelta(hours=self.drift_check_interval_hours):
            return None
        
        # Calculate expected drift based on historical data
        history = self.calibration_histories.get(sensor_id)
        if not history or len(history.calibration_events) < 2:
            return None
        
        # Estimate current drift (simplified - would use more sophisticated analysis in production)
        hours_elapsed = time_since_calibration.total_seconds() / 3600
        estimated_drift = state.drift_rate * hours_elapsed if state.drift_rate else 0
        
        # Calculate actual drift from expected baseline
        baseline_value = state.zero_offset  # Simplified baseline
        actual_drift = abs(current_reading - baseline_value - estimated_drift)
        drift_percentage = (actual_drift / abs(baseline_value)) * 100 if baseline_value != 0 else 0
        
        # Check if drift exceeds threshold
        if drift_percentage > self.drift_threshold_percent:
            severity = "critical" if drift_percentage > self.drift_threshold_percent * 2 else "warning"
            
            return DriftAlert(
                sensor_id=sensor_id,
                current_drift=drift_percentage,
                threshold=self.drift_threshold_percent,
                last_calibration=state.last_calibrated,
                recommended_action="Perform auto-zero calibration" if severity == "warning" else "Immediate recalibration required",
                severity=severity
            )
        
        return None
    
    def _find_sensor_reading(self, telemetry, sensor_id: str) -> Optional[SensorReading]:
        """Find sensor reading by ID in telemetry packet"""
        all_readings = (telemetry.pressure_transducers + 
                       telemetry.thermocouples + 
                       telemetry.load_cells)
        
        for reading in all_readings:
            if reading.sensor_id == sensor_id:
                return reading
        
        return None
    
    def _calculate_accuracy_improvement(self, previous_offset: float, 
                                      new_offset: float, noise_level: float) -> float:
        """Calculate accuracy improvement percentage"""
        if abs(previous_offset) < 1e-6:  # No previous offset
            return 0.0
        
        # Simple improvement calculation based on offset reduction
        improvement = (abs(previous_offset) - abs(new_offset)) / abs(previous_offset) * 100
        
        # Penalize for high noise
        if noise_level > self.default_noise_threshold:
            improvement *= (1.0 - noise_level / self.default_noise_threshold)
        
        return round(improvement, 1)
    
    async def _update_calibration_state(self, sensor_id: str, 
                                       zero_offset: Optional[float] = None,
                                       span_multiplier: Optional[float] = None,
                                       temperature_coefficient: Optional[float] = None,
                                       calibration_type: CalibrationType = CalibrationType.AUTO_ZERO,
                                       quality: float = 1.0):
        """Update calibration state for a sensor"""
        if sensor_id not in self.calibration_states:
            self.calibration_states[sensor_id] = CalibrationState(sensor_id=sensor_id)
        
        state = self.calibration_states[sensor_id]
        
        if zero_offset is not None:
            state.zero_offset = zero_offset
        if span_multiplier is not None:
            state.span_multiplier = span_multiplier
        if temperature_coefficient is not None:
            state.temperature_coefficient = temperature_coefficient
        
        state.last_calibrated = datetime.now()
        state.calibration_type = calibration_type
        state.calibration_quality = quality
        state.is_valid = True
        
        # Save states to persistent storage
        await self.save_calibration_states()
    
    async def _add_calibration_event(self, sensor_id: str, result: CalibrationResult):
        """Add calibration event to history"""
        if sensor_id not in self.calibration_histories:
            self.calibration_histories[sensor_id] = CalibrationHistory(sensor_id=sensor_id)
        
        history = self.calibration_histories[sensor_id]
        history.add_calibration_event(result)
    
    async def save_calibration_states(self):
        """Save calibration states to persistent storage"""
        try:
            data = {
                "states": {
                    sensor_id: state.dict() for sensor_id, state in self.calibration_states.items()
                },
                "saved_at": datetime.now().isoformat()
            }
            
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
        except Exception as e:
            print(f"Failed to save calibration states: {e}")
    
    async def load_calibration_states(self):
        """Load calibration states from persistent storage"""
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                
                for sensor_id, state_data in data.get("states", {}).items():
                    # Convert datetime strings back to datetime objects
                    if "last_calibrated" in state_data and state_data["last_calibrated"]:
                        state_data["last_calibrated"] = datetime.fromisoformat(state_data["last_calibrated"])
                    
                    self.calibration_states[sensor_id] = CalibrationState(**state_data)
                    
        except Exception as e:
            print(f"Failed to load calibration states: {e}")
    
    async def get_calibration_state(self, sensor_id: str) -> Optional[CalibrationState]:
        """Get current calibration state for a sensor"""
        return self.calibration_states.get(sensor_id)
    
    async def get_calibration_history(self, sensor_id: str) -> Optional[CalibrationHistory]:
        """Get calibration history for a sensor"""
        return self.calibration_histories.get(sensor_id)