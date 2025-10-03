"""Pytest configuration and shared fixtures"""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from app.config.settings import Settings, SensorConfig


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_config_dir():
    """Create temporary directory for test configurations"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_sensor_configs():
    """Create test sensor configurations"""
    pressure_transducers = [
        SensorConfig(
            name="Test Pressure 1",
            id="pt1",
            color="#ff0000",
            min_value=0.0,
            max_value=1000.0,
            warning_threshold=800.0,
            danger_threshold=950.0,
            unit="psi",
            calibration_enabled=True,
            temperature_compensation=False
        ),
        SensorConfig(
            name="Test Pressure 2", 
            id="pt2",
            color="#00ff00",
            min_value=0.0,
            max_value=500.0,
            warning_threshold=400.0,
            danger_threshold=480.0,
            unit="psi",
            calibration_enabled=True,
            temperature_compensation=False
        )
    ]
    
    thermocouples = [
        SensorConfig(
            name="Test Thermocouple",
            id="tc1",
            color="#0000ff",
            min_value=-40.0,
            max_value=1200.0,
            warning_threshold=1000.0,
            danger_threshold=1150.0,
            unit="celsius",
            calibration_enabled=True,
            temperature_compensation=False
        )
    ]
    
    load_cells = [
        SensorConfig(
            name="Test Load Cell",
            id="lc1",
            color="#ffff00",
            min_value=0.0,
            max_value=5000.0,
            warning_threshold=4000.0,
            danger_threshold=4800.0,
            unit="lbs",
            calibration_enabled=True,
            temperature_compensation=True
        )
    ]
    
    return {
        "pressure_transducers": pressure_transducers,
        "thermocouples": thermocouples,
        "load_cells": load_cells
    }


@pytest.fixture
def mock_telemetry_data():
    """Create mock telemetry data for testing"""
    from app.models.sensors import TelemetryPacket, SensorReading
    
    return TelemetryPacket(
        pressure_transducers=[
            SensorReading(sensor_id="pt1", value=123.45, unit="psi", calibrated=True),
            SensorReading(sensor_id="pt2", value=67.89, unit="psi", calibrated=False)
        ],
        thermocouples=[
            SensorReading(sensor_id="tc1", value=25.6, unit="celsius", calibrated=True)
        ],
        load_cells=[
            SensorReading(sensor_id="lc1", value=1234.5, unit="lbs", calibrated=True)
        ],
        valve_states={"fcv1": True, "fcv2": False}
    )


@pytest.fixture
def mock_calibration_result():
    """Create mock calibration result for testing"""
    from app.models.calibration import CalibrationResult, CalibrationType
    
    return CalibrationResult(
        sensor_id="pt1",
        calibration_type=CalibrationType.AUTO_ZERO,
        success=True,
        timestamp="2024-01-01T12:00:00Z",
        measurement_count=50,
        new_offset=2.345,
        accuracy_percent=99.9,
        measurement_std_dev=0.01
    )


@pytest.fixture
def mock_data_source():
    """Create mock data source for testing"""
    mock = AsyncMock()
    mock.start.return_value = True
    mock.stop.return_value = None
    mock.is_running = True
    mock.read_sensors.return_value = AsyncMock()
    mock.health_check.return_value = {
        "running": True,
        "error_count": 0,
        "last_reading_time": "2024-01-01T12:00:00Z"
    }
    return mock


@pytest.fixture
def mock_calibration_service():
    """Create mock calibration service for testing"""
    from app.services.calibration import CalibrationService
    from app.models.calibration import CalibrationResult, CalibrationType
    
    mock = Mock(spec=CalibrationService)
    
    # Mock successful auto-zero calibration
    async def mock_auto_zero(sensor_id, data_source, **kwargs):
        return CalibrationResult(
            sensor_id=sensor_id,
            calibration_type=CalibrationType.AUTO_ZERO,
            success=True,
            measurement_count=50,
            new_offset=1.234,
            accuracy_percent=99.8
        )
    
    # Mock successful span calibration  
    async def mock_span(sensor_id, reference_value, measured_value):
        span_multiplier = reference_value / measured_value
        return CalibrationResult(
            sensor_id=sensor_id,
            calibration_type=CalibrationType.SPAN,
            success=True,
            measurement_count=1,
            new_span=span_multiplier,
            accuracy_percent=99.5
        )
    
    mock.auto_zero_calibration = mock_auto_zero
    mock.span_calibration = mock_span
    mock.get_calibration_state.return_value = None
    
    return mock


@pytest.fixture
def performance_settings():
    """Create settings optimized for performance testing"""
    settings = Settings()
    settings.telemetry_interval_ms = 10  # Very fast for performance testing
    settings.debug = False
    return settings


@pytest.fixture
def realistic_settings(test_sensor_configs):
    """Create realistic settings for integration testing"""
    settings = Settings()
    settings.data_source = "simulator"
    settings.telemetry_interval_ms = 100
    settings.pressure_transducers = test_sensor_configs["pressure_transducers"]
    settings.thermocouples = test_sensor_configs["thermocouples"] 
    settings.load_cells = test_sensor_configs["load_cells"]
    return settings


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests"""
    # This ensures clean state between tests
    yield
    
    # Clean up any global state that might persist
    # (Add cleanup code here if needed)


@pytest.fixture
def async_mock_websocket():
    """Create async mock WebSocket for testing"""
    mock = AsyncMock()
    mock.accept.return_value = None
    mock.send_text.return_value = None
    mock.close.return_value = None
    return mock


# Performance test markers
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# Async test configuration
@pytest.fixture(scope="function")
def anyio_backend():
    """Configure anyio backend for async tests"""
    return "asyncio"


# Test data cleanup
@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Clean up test data after each test"""
    yield
    
    # Add any necessary cleanup here
    # For example, clearing temporary files, resetting global state, etc.
    pass