"""Tests for configuration management"""
import pytest
from app.config.settings import Settings, SensorConfig, CalibrationSettings, DataSourceType


def test_settings_load_from_yaml():
    """Test that settings load correctly from YAML file"""
    settings = Settings()
    
    # Test basic settings
    assert settings.data_source == DataSourceType.SERIAL
    assert settings.serial_port == "/dev/cu.usbmodem1201"
    assert settings.serial_baudrate == 115200
    assert settings.telemetry_interval_ms == 100
    
    # Test calibration settings
    assert settings.calibration.auto_zero_enabled is True
    assert settings.calibration.drift_monitoring is True
    assert settings.calibration.calibration_interval_hours == 24


def test_sensor_config_validation():
    """Test sensor configuration validation"""
    # Valid sensor config
    sensor = SensorConfig(
        name="Test Sensor",
        id="test1",
        color="#FF0000",
        min_value=0,
        max_value=100,
        warning_threshold=80,
        danger_threshold=90,
        unit="psi"
    )
    assert sensor.name == "Test Sensor"
    assert sensor.color == "#FF0000"
    
    # Invalid color should raise validation error
    with pytest.raises(ValueError):
        SensorConfig(
            name="Bad Sensor",
            id="bad1",
            color="red",  # Invalid hex color
            min_value=0,
            max_value=100,
            warning_threshold=80,
            danger_threshold=90
        )


def test_pressure_transducers_loaded():
    """Test that pressure transducers are loaded from config"""
    settings = Settings()
    
    assert len(settings.pressure_transducers) == 5
    
    # Check first pressure transducer
    pt1 = settings.pressure_transducers[0]
    assert pt1.name == "GN2"
    assert pt1.id == "pt1"
    assert pt1.color == "#0072B2"
    assert pt1.calibration_enabled is True


def test_thermocouples_loaded():
    """Test that thermocouples are loaded from config"""
    settings = Settings()
    
    assert len(settings.thermocouples) == 3
    
    # Check first thermocouple
    tc1 = settings.thermocouples[0]
    assert tc1.name == "Thermocouple 1"
    assert tc1.id == "tc1"
    assert tc1.unit == "°C"


def test_load_cells_loaded():
    """Test that load cells are loaded from config"""
    settings = Settings()
    
    assert len(settings.load_cells) == 3
    
    # Check first load cell
    lc1 = settings.load_cells[0]
    assert lc1.name == "Load Cell 1"
    assert lc1.id == "lc1"
    assert lc1.unit == "lbf"


def test_flow_control_valves_loaded():
    """Test that flow control valves are loaded from config"""
    settings = Settings()
    
    assert len(settings.flow_control_valves) == 7
    
    # Check first valve
    fv1 = settings.flow_control_valves[0]
    assert fv1["name"] == "LNG Vent"
    assert fv1["id"] == "fv1"


def test_calibration_settings():
    """Test calibration settings configuration"""
    settings = Settings()
    
    cal = settings.calibration
    assert cal.auto_zero_enabled is True
    assert cal.drift_monitoring is True
    assert cal.calibration_interval_hours == 24
    assert cal.drift_threshold_percent == 2.0
    assert cal.measurement_duration_ms == 5000
    assert cal.noise_threshold == 0.1