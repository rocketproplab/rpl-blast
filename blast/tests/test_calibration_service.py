"""Tests for calibration service implementation"""
import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta

from app.services.calibration import CalibrationService
from app.models.calibration import CalibrationState, CalibrationType
from app.models.sensors import SensorReading, TelemetryPacket
from app.data_sources.simulator import SensorSimulator


@pytest.fixture
def temp_calibration_file():
    """Create temporary file for calibration state persistence"""
    fd, path = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
async def calibration_service(temp_calibration_file):
    """Create calibration service with temporary storage"""
    service = CalibrationService(config_path=temp_calibration_file)
    await asyncio.sleep(0.1)  # Allow initialization to complete
    return service


@pytest.fixture
def mock_data_source():
    """Create mock data source for testing"""
    mock_source = AsyncMock()
    
    # Create consistent sensor reading
    reading = SensorReading(
        sensor_id="pt1",
        value=250.0,
        raw_value=2.5,
        unit="psi"
    )
    
    telemetry = TelemetryPacket(pressure_transducers=[reading])
    mock_source.read_sensors.return_value = telemetry
    
    return mock_source


@pytest.fixture
def sample_config():
    """Sample sensor configuration"""
    return {
        'pressure_transducers': [
            {'id': 'pt1', 'name': 'GN2', 'unit': 'psi'},
            {'id': 'pt2', 'name': 'LOX', 'unit': 'psi'}
        ],
        'noise_enabled': True,
        'drift_enabled': True
    }


class TestCalibrationService:
    """Test calibration service core functionality"""
    
    @pytest.mark.asyncio
    async def test_auto_zero_calibration_success(self, calibration_service, mock_data_source):
        """Test successful auto-zero calibration"""
        # Set up consistent readings for zero calibration
        reading = SensorReading(sensor_id="pt1", value=2.0, raw_value=2.0, unit="psi")
        telemetry = TelemetryPacket(pressure_transducers=[reading])
        mock_data_source.read_sensors.return_value = telemetry
        
        # Perform calibration
        result = await calibration_service.auto_zero_calibration("pt1", mock_data_source, 1000)
        
        assert result.success is True
        assert result.sensor_id == "pt1"
        assert result.calibration_type == CalibrationType.AUTO_ZERO
        assert result.new_offset is not None
        assert result.measurement_count >= 8  # Should have at least 8 readings (80% of 10)
        assert result.noise_level is not None
        assert result.noise_level < 0.1  # Should be low noise for consistent readings
        
        # Check that calibration state was updated
        state = await calibration_service.get_calibration_state("pt1")
        assert state is not None
        assert state.zero_offset == result.new_offset
        assert state.calibration_type == CalibrationType.AUTO_ZERO
    
    @pytest.mark.asyncio
    async def test_auto_zero_calibration_high_noise(self, calibration_service, mock_data_source):
        """Test auto-zero calibration failure due to high noise"""
        # Set up mock to return varying readings (high noise)
        readings = [
            SensorReading(sensor_id="pt1", value=i * 10, raw_value=i * 10, unit="psi")
            for i in range(10)
        ]
        
        call_count = 0
        async def varying_read():
            nonlocal call_count
            reading = readings[call_count % len(readings)]
            call_count += 1
            return TelemetryPacket(pressure_transducers=[reading])
        
        mock_data_source.read_sensors.side_effect = varying_read
        
        result = await calibration_service.auto_zero_calibration("pt1", mock_data_source, 1000)
        
        assert result.success is False
        assert "Excessive noise" in result.error
        assert result.noise_level > 0.1
    
    @pytest.mark.asyncio
    async def test_span_calibration_success(self, calibration_service):
        """Test successful span calibration"""
        # First set up a zero offset
        await calibration_service._update_calibration_state("pt1", zero_offset=5.0)
        
        # Perform span calibration
        reference_value = 100.0
        measured_value = 105.0  # Includes the 5.0 zero offset
        
        result = await calibration_service.span_calibration("pt1", reference_value, measured_value)
        
        assert result.success is True
        assert result.sensor_id == "pt1"
        assert result.calibration_type == CalibrationType.SPAN
        assert result.new_span is not None
        
        # Check calculation: (measured - zero) = 100.0, so span = 100/100 = 1.0
        expected_span = reference_value / (measured_value - 5.0)  # 100 / 100 = 1.0
        assert abs(result.new_span - expected_span) < 0.001
        
        # Check state was updated
        state = await calibration_service.get_calibration_state("pt1")
        assert state.span_multiplier == result.new_span
    
    @pytest.mark.asyncio
    async def test_span_calibration_invalid_range(self, calibration_service):
        """Test span calibration failure with invalid multiplier"""
        # Set up scenario that would result in invalid span multiplier
        reference_value = 1000.0
        measured_value = 10.0  # Would result in span multiplier of 100 (too high)
        
        result = await calibration_service.span_calibration("pt1", reference_value, measured_value)
        
        assert result.success is False
        assert "span multiplier out of range" in result.error
    
    @pytest.mark.asyncio
    async def test_temperature_compensation(self, calibration_service):
        """Test temperature compensation calculation"""
        # Set up calibration state with temperature coefficient
        await calibration_service._update_calibration_state(
            "pt1", 
            temperature_coefficient=0.1  # 0.1 units per degree C
        )
        
        # Test compensation at different temperatures
        base_reading = 100.0
        
        # At reference temperature (25°C), no compensation
        compensated = await calibration_service.temperature_compensation("pt1", base_reading, 25.0)
        assert compensated == base_reading
        
        # At 35°C, should add 1.0 (10 degrees * 0.1)
        compensated = await calibration_service.temperature_compensation("pt1", base_reading, 35.0)
        assert compensated == base_reading + 1.0
        
        # At 15°C, should subtract 1.0 (-10 degrees * 0.1)
        compensated = await calibration_service.temperature_compensation("pt1", base_reading, 15.0)
        assert compensated == base_reading - 1.0
    
    @pytest.mark.asyncio
    async def test_apply_full_calibration(self, calibration_service):
        """Test applying complete calibration to sensor reading"""
        # Set up calibration state with all corrections
        await calibration_service._update_calibration_state(
            "pt1",
            zero_offset=5.0,
            span_multiplier=1.1,
            temperature_coefficient=0.05
        )
        
        # Create test reading
        raw_reading = SensorReading(
            sensor_id="pt1",
            value=100.0,
            raw_value=100.0,
            unit="psi"
        )
        
        # Apply calibration with temperature
        calibrated = await calibration_service.apply_calibration(raw_reading, ambient_temperature=30.0)
        
        # Expected: (100 - 5) * 1.1 + 0.05 * (30 - 25) = 95 * 1.1 + 0.25 = 104.5 + 0.25 = 104.75
        expected_value = (100.0 - 5.0) * 1.1 + 0.05 * (30.0 - 25.0)
        
        assert calibrated.calibrated is True
        assert abs(calibrated.value - expected_value) < 0.001
        assert calibrated.sensor_id == "pt1"
        assert calibrated.raw_value == 100.0
    
    @pytest.mark.asyncio
    async def test_calibration_state_persistence(self, temp_calibration_file):
        """Test saving and loading calibration states"""
        # Create service and add calibration state
        service1 = CalibrationService(config_path=temp_calibration_file)
        await service1._update_calibration_state("pt1", zero_offset=10.0, span_multiplier=1.05)
        
        # Save and create new service instance
        await service1.save_calibration_states()
        service2 = CalibrationService(config_path=temp_calibration_file)
        await asyncio.sleep(0.1)  # Allow loading to complete
        
        # Check that state was loaded
        state = await service2.get_calibration_state("pt1")
        assert state is not None
        assert state.zero_offset == 10.0
        assert state.span_multiplier == 1.05
    
    @pytest.mark.asyncio
    async def test_drift_monitoring(self, calibration_service):
        """Test drift monitoring and alert generation"""
        # Set up calibration state with old calibration time
        old_time = datetime.now() - timedelta(hours=2)
        state = CalibrationState(
            sensor_id="pt1",
            zero_offset=5.0,
            last_calibrated=old_time,
            drift_rate=1.0  # 1 unit per hour
        )
        calibration_service.calibration_states["pt1"] = state
        
        # Add some history to enable drift monitoring
        from app.models.calibration import CalibrationHistory, CalibrationResult
        history = CalibrationHistory(sensor_id="pt1")
        history.calibration_events = [
            CalibrationResult(success=True, sensor_id="pt1", calibration_type=CalibrationType.AUTO_ZERO),
            CalibrationResult(success=True, sensor_id="pt1", calibration_type=CalibrationType.AUTO_ZERO)
        ]
        calibration_service.calibration_histories["pt1"] = history
        
        # Test with high drift reading
        high_drift_reading = 20.0  # Expected: 5.0 + 2*1.0 = 7.0, so drift is ~13 units
        alert = await calibration_service.monitor_drift("pt1", high_drift_reading)
        
        assert alert is not None
        assert alert.sensor_id == "pt1"
        assert alert.current_drift > calibration_service.drift_threshold_percent
        assert alert.severity in ["warning", "critical"]


class TestCalibrationServiceIntegration:
    """Integration tests with real simulator"""
    
    @pytest.mark.asyncio
    async def test_auto_zero_with_simulator(self, sample_config, temp_calibration_file):
        """Test auto-zero calibration with real simulator"""
        # Create simulator and calibration service
        simulator = SensorSimulator(sample_config)
        await simulator.initialize()
        
        calibration_service = CalibrationService(config_path=temp_calibration_file)
        
        # Inject known offset for testing
        test_offset = 25.0
        await simulator.inject_calibration_offset("pt1", test_offset)
        
        # Perform calibration (should detect and correct the offset)
        result = await calibration_service.auto_zero_calibration("pt1", simulator, 1000)
        
        assert result.success is True
        assert result.measurement_count >= 8
        
        # The new offset should be close to the injected offset
        assert abs(result.new_offset - test_offset) < 5.0  # Allow for some noise
    
    @pytest.mark.asyncio
    async def test_span_calibration_accuracy(self, sample_config, temp_calibration_file):
        """Test span calibration accuracy with known reference"""
        # Create simulator and calibration service
        simulator = SensorSimulator(sample_config)
        await simulator.initialize()
        
        calibration_service = CalibrationService(config_path=temp_calibration_file)
        
        # Read current value from simulator
        telemetry = await simulator.read_sensors()
        current_reading = telemetry.pressure_transducers[0]
        
        # Use current reading as "measured" and set a known reference
        measured_value = current_reading.value
        reference_value = 500.0  # Known reference pressure
        
        # Perform span calibration
        result = await calibration_service.span_calibration("pt1", reference_value, measured_value)
        
        assert result.success is True
        
        # Apply calibration to a new reading
        new_telemetry = await simulator.read_sensors()
        new_reading = new_telemetry.pressure_transducers[0]
        calibrated_reading = await calibration_service.apply_calibration(new_reading)
        
        # The calibrated reading should be closer to the expected range
        assert calibrated_reading.calibrated is True
        assert calibrated_reading.value != new_reading.value  # Should be different after calibration
    
    @pytest.mark.asyncio
    async def test_calibration_checkpoint_accuracy(self, sample_config, temp_calibration_file):
        """Test that calibration meets the ±0.1% accuracy checkpoint"""
        simulator = SensorSimulator(sample_config)
        await simulator.initialize()
        
        calibration_service = CalibrationService(config_path=temp_calibration_file)
        
        # Set low noise for accurate testing
        await simulator.set_sensor_noise_level("pt1", 0.01)
        
        # Inject small, known offset
        known_offset = 5.0
        await simulator.inject_calibration_offset("pt1", known_offset)
        
        # Perform calibration
        result = await calibration_service.auto_zero_calibration("pt1", simulator, 2000)
        
        assert result.success is True
        
        # Check accuracy: detected offset should be within ±0.1% of known offset
        accuracy_error = abs(result.new_offset - known_offset) / known_offset * 100
        assert accuracy_error < 0.1, f"Calibration accuracy error: {accuracy_error:.3f}% > 0.1%"
        
        # Verify low noise level
        assert result.noise_level < 0.1, f"Noise level too high: {result.noise_level}"