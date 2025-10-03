"""Tests for calibration data models"""
import pytest
from datetime import datetime
from app.models.calibration import (
    CalibrationState, CalibrationResult, CalibrationHistory, 
    DriftAlert, CalibrationType
)


def test_calibration_state_valid():
    """Test valid calibration state creation"""
    state = CalibrationState(
        sensor_id="pt1",
        zero_offset=-2.5,
        span_multiplier=1.02,
        temperature_coefficient=0.001,
        calibration_type=CalibrationType.AUTO_ZERO,
        calibration_quality=0.95
    )
    
    assert state.sensor_id == "pt1"
    assert state.zero_offset == -2.5
    assert state.span_multiplier == 1.02
    assert state.temperature_coefficient == 0.001
    assert state.calibration_type == CalibrationType.AUTO_ZERO
    assert state.calibration_quality == 0.95
    assert state.is_valid is True


def test_calibration_state_validation():
    """Test calibration state validation"""
    # Test invalid span multiplier (negative)
    with pytest.raises(ValueError, match="Span multiplier must be positive"):
        CalibrationState(
            sensor_id="pt1",
            span_multiplier=-1.0
        )
    
    # Test invalid span multiplier (too large)
    with pytest.raises(ValueError, match="Span multiplier must be between 0.1 and 10.0"):
        CalibrationState(
            sensor_id="pt1",
            span_multiplier=15.0
        )
    
    # Test invalid calibration quality
    with pytest.raises(ValueError, match="Calibration quality must be between 0.0 and 1.0"):
        CalibrationState(
            sensor_id="pt1",
            calibration_quality=1.5
        )


def test_calibration_result_success():
    """Test successful calibration result"""
    result = CalibrationResult(
        success=True,
        sensor_id="pt1",
        calibration_type=CalibrationType.AUTO_ZERO,
        previous_offset=-1.0,
        new_offset=-2.5,
        accuracy_improvement=15.0,
        measurement_count=50,
        noise_level=0.05
    )
    
    assert result.success is True
    assert result.sensor_id == "pt1"
    assert result.calibration_type == CalibrationType.AUTO_ZERO
    assert result.previous_offset == -1.0
    assert result.new_offset == -2.5
    assert result.accuracy_improvement == 15.0
    assert result.measurement_count == 50
    assert result.noise_level == 0.05
    assert isinstance(result.timestamp, datetime)
    assert result.error is None


def test_calibration_result_failure():
    """Test failed calibration result"""
    result = CalibrationResult(
        success=False,
        sensor_id="pt1",
        calibration_type=CalibrationType.SPAN,
        error="Excessive noise during calibration"
    )
    
    assert result.success is False
    assert result.sensor_id == "pt1"
    assert result.error == "Excessive noise during calibration"


def test_calibration_result_validation():
    """Test calibration result validation"""
    # Test invalid accuracy improvement
    with pytest.raises(ValueError, match="Accuracy improvement must be between -100% and 100%"):
        CalibrationResult(
            success=True,
            sensor_id="pt1",
            calibration_type=CalibrationType.AUTO_ZERO,
            accuracy_improvement=150.0  # Too high
        )


def test_calibration_history():
    """Test calibration history functionality"""
    history = CalibrationHistory(sensor_id="pt1")
    
    assert history.sensor_id == "pt1"
    assert history.calibration_events == []
    assert history.total_calibrations == 0
    
    # Add calibration event
    result = CalibrationResult(
        success=True,
        sensor_id="pt1",
        calibration_type=CalibrationType.AUTO_ZERO
    )
    
    history.add_calibration_event(result)
    
    assert len(history.calibration_events) == 1
    assert history.total_calibrations == 1
    assert history.calibration_events[0] == result


def test_calibration_history_limit():
    """Test calibration history size limit"""
    history = CalibrationHistory(sensor_id="pt1")
    
    # Add 105 events (more than the 100 limit)
    for i in range(105):
        result = CalibrationResult(
            success=True,
            sensor_id="pt1",
            calibration_type=CalibrationType.AUTO_ZERO
        )
        history.add_calibration_event(result)
    
    # Should only keep the last 100 events
    assert len(history.calibration_events) == 100
    assert history.total_calibrations == 105


def test_drift_alert():
    """Test drift alert creation"""
    alert = DriftAlert(
        sensor_id="pt1",
        current_drift=3.5,
        threshold=2.0,
        recommended_action="Perform zero calibration",
        severity="warning"
    )
    
    assert alert.sensor_id == "pt1"
    assert alert.current_drift == 3.5
    assert alert.threshold == 2.0
    assert alert.recommended_action == "Perform zero calibration"
    assert alert.severity == "warning"
    assert isinstance(alert.timestamp, datetime)


def test_drift_alert_validation():
    """Test drift alert validation"""
    # Test invalid severity
    with pytest.raises(ValueError, match="Severity must be one of"):
        DriftAlert(
            sensor_id="pt1",
            current_drift=3.5,
            threshold=2.0,
            recommended_action="Recalibrate",
            severity="invalid"
        )


def test_calibration_type_enum():
    """Test calibration type enumeration"""
    assert CalibrationType.AUTO_ZERO == "auto_zero"
    assert CalibrationType.MANUAL_ZERO == "manual_zero"
    assert CalibrationType.SPAN == "span"
    assert CalibrationType.MULTIPOINT == "multipoint"
    assert CalibrationType.TEMPERATURE_COMPENSATION == "temperature_compensation"


def test_calibration_state_defaults():
    """Test calibration state default values"""
    state = CalibrationState(sensor_id="pt1")
    
    assert state.sensor_id == "pt1"
    assert state.zero_offset == 0.0
    assert state.span_multiplier == 1.0
    assert state.temperature_coefficient == 0.0
    assert state.last_calibrated is None
    assert state.calibration_type == CalibrationType.AUTO_ZERO
    assert state.drift_rate is None
    assert state.calibration_quality == 1.0
    assert state.is_valid is True