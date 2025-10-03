"""Tests for sensor data models"""
import pytest
from datetime import datetime
from app.models.sensors import SensorReading, SensorQuality, TelemetryPacket, SensorStats


def test_sensor_reading_valid():
    """Test valid sensor reading creation"""
    reading = SensorReading(
        sensor_id="pt1",
        value=245.5,
        raw_value=2.45,
        unit="psi",
        quality=SensorQuality.GOOD,
        calibrated=True
    )
    
    assert reading.sensor_id == "pt1"
    assert reading.value == 245.5
    assert reading.raw_value == 2.45
    assert reading.unit == "psi"
    assert reading.quality == SensorQuality.GOOD
    assert reading.calibrated is True
    assert isinstance(reading.timestamp, datetime)


def test_sensor_reading_validation():
    """Test sensor reading validation"""
    # Test invalid sensor value
    with pytest.raises(ValueError, match="Sensor value must be within reasonable range"):
        SensorReading(
            sensor_id="pt1",
            value=1e7,  # Too large
            unit="psi"
        )
    
    # Test invalid sensor ID
    with pytest.raises(ValueError, match="Sensor ID must be a non-empty string"):
        SensorReading(
            sensor_id="",  # Empty string
            value=100.0,
            unit="psi"
        )
    
    # Test sensor ID too long
    with pytest.raises(ValueError, match="Sensor ID must be 50 characters or less"):
        SensorReading(
            sensor_id="a" * 51,  # Too long
            value=100.0,
            unit="psi"
        )


def test_sensor_reading_serialization():
    """Test sensor reading JSON serialization"""
    reading = SensorReading(
        sensor_id="tc1",
        value=125.5,
        unit="°C"
    )
    
    json_data = reading.dict()
    assert json_data["sensor_id"] == "tc1"
    assert json_data["value"] == 125.5
    assert json_data["unit"] == "°C"
    assert "timestamp" in json_data


def test_telemetry_packet_valid():
    """Test valid telemetry packet creation"""
    pt_reading = SensorReading(sensor_id="pt1", value=250.0, unit="psi")
    tc_reading = SensorReading(sensor_id="tc1", value=120.0, unit="°C")
    lc_reading = SensorReading(sensor_id="lc1", value=50.0, unit="lbf")
    
    packet = TelemetryPacket(
        pressure_transducers=[pt_reading],
        thermocouples=[tc_reading],
        load_cells=[lc_reading],
        valve_states={"fv1": True, "fv2": False},
        system_status="operational"
    )
    
    assert len(packet.pressure_transducers) == 1
    assert len(packet.thermocouples) == 1
    assert len(packet.load_cells) == 1
    assert packet.valve_states["fv1"] is True
    assert packet.valve_states["fv2"] is False
    assert packet.system_status == "operational"


def test_telemetry_packet_validation():
    """Test telemetry packet validation"""
    # Test invalid valve states
    with pytest.raises(ValueError, match="Valve states must be a dictionary"):
        TelemetryPacket(valve_states="invalid")
    
    # Test invalid valve state values
    with pytest.raises(ValueError, match="Valve state for fv1 must be boolean"):
        TelemetryPacket(valve_states={"fv1": "on"})


def test_telemetry_packet_empty():
    """Test empty telemetry packet"""
    packet = TelemetryPacket()
    
    assert packet.pressure_transducers == []
    assert packet.thermocouples == []
    assert packet.load_cells == []
    assert packet.valve_states == {}
    assert packet.system_status == "operational"
    assert isinstance(packet.timestamp, datetime)


def test_sensor_stats_valid():
    """Test sensor stats creation"""
    stats = SensorStats(
        sensor_id="pt1",
        latest_value=245.5,
        average_10s=240.0,
        rate_change=2.5,
        max_recorded=300.0,
        min_recorded=200.0,
        sample_count=1000
    )
    
    assert stats.sensor_id == "pt1"
    assert stats.latest_value == 245.5
    assert stats.average_10s == 240.0
    assert stats.rate_change == 2.5
    assert stats.max_recorded == 300.0
    assert stats.min_recorded == 200.0
    assert stats.sample_count == 1000
    assert isinstance(stats.last_updated, datetime)


def test_sensor_quality_enum():
    """Test sensor quality enumeration"""
    assert SensorQuality.GOOD == "good"
    assert SensorQuality.WARNING == "warning"
    assert SensorQuality.DANGER == "danger"
    assert SensorQuality.ERROR == "error"
    assert SensorQuality.UNCALIBRATED == "uncalibrated"


def test_sensor_reading_edge_cases():
    """Test sensor reading edge cases"""
    # Test with None raw_value
    reading = SensorReading(
        sensor_id="pt1",
        value=100.0,
        raw_value=None,
        unit="psi"
    )
    assert reading.raw_value is None
    
    # Test with extreme but valid values
    reading = SensorReading(
        sensor_id="pt2",
        value=-999999.0,
        unit="psi"
    )
    assert reading.value == -999999.0