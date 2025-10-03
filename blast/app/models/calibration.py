"""Calibration data models with Pydantic validation"""
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum


class CalibrationType(str, Enum):
    """Types of calibration procedures"""
    AUTO_ZERO = "auto_zero"
    MANUAL_ZERO = "manual_zero"
    SPAN = "span"
    MULTIPOINT = "multipoint"
    TEMPERATURE_COMPENSATION = "temperature_compensation"


class CalibrationState(BaseModel):
    """Current calibration state for a sensor"""
    sensor_id: str = Field(..., description="Sensor identifier")
    zero_offset: float = Field(default=0.0, description="Zero point offset correction")
    span_multiplier: float = Field(default=1.0, description="Span correction multiplier")
    temperature_coefficient: float = Field(default=0.0, description="Temperature compensation coefficient")
    last_calibrated: Optional[datetime] = Field(None, description="Last calibration timestamp")
    calibration_type: CalibrationType = Field(default=CalibrationType.AUTO_ZERO)
    drift_rate: Optional[float] = Field(None, description="Measured drift rate per day")
    calibration_quality: float = Field(default=1.0, description="Calibration quality score 0-1")
    is_valid: bool = Field(default=True, description="Whether calibration is still valid")
    
    @validator('zero_offset', 'span_multiplier', 'temperature_coefficient')
    def validate_calibration_values(cls, v):
        """Validate calibration parameters are reasonable"""
        if not isinstance(v, (int, float)):
            raise ValueError('Calibration values must be numeric')
        return v
    
    @validator('span_multiplier')
    def validate_span_multiplier(cls, v):
        """Validate span multiplier is positive and reasonable"""
        if v <= 0:
            raise ValueError('Span multiplier must be positive')
        if not (0.1 <= v <= 10.0):
            raise ValueError('Span multiplier must be between 0.1 and 10.0')
        return v
    
    @validator('calibration_quality')
    def validate_quality_score(cls, v):
        """Validate quality score is between 0 and 1"""
        if not (0.0 <= v <= 1.0):
            raise ValueError('Calibration quality must be between 0.0 and 1.0')
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class CalibrationResult(BaseModel):
    """Result of a calibration procedure"""
    success: bool = Field(..., description="Whether calibration succeeded")
    sensor_id: str = Field(..., description="Sensor that was calibrated")
    calibration_type: CalibrationType = Field(..., description="Type of calibration performed")
    previous_offset: Optional[float] = Field(None, description="Previous zero offset")
    new_offset: Optional[float] = Field(None, description="New zero offset")
    previous_span: Optional[float] = Field(None, description="Previous span multiplier")
    new_span: Optional[float] = Field(None, description="New span multiplier")
    accuracy_improvement: Optional[float] = Field(None, description="Accuracy improvement percentage")
    measurement_count: Optional[int] = Field(None, description="Number of measurements used")
    noise_level: Optional[float] = Field(None, description="Measured noise during calibration")
    timestamp: datetime = Field(default_factory=datetime.now)
    error: Optional[str] = Field(None, description="Error message if calibration failed")
    
    @validator('accuracy_improvement')
    def validate_accuracy_improvement(cls, v):
        """Validate accuracy improvement percentage"""
        if v is not None and not (-100.0 <= v <= 100.0):
            raise ValueError('Accuracy improvement must be between -100% and 100%')
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CalibrationHistory(BaseModel):
    """Historical calibration data for a sensor"""
    sensor_id: str = Field(..., description="Sensor identifier")
    calibration_events: List[CalibrationResult] = Field(default_factory=list)
    drift_analysis: Dict[str, float] = Field(default_factory=dict)
    last_drift_check: Optional[datetime] = Field(None, description="Last drift monitoring check")
    total_calibrations: int = Field(default=0, description="Total number of calibrations")
    
    @validator('calibration_events')
    def validate_calibration_events(cls, v):
        """Validate calibration events list"""
        if not isinstance(v, list):
            raise ValueError('Calibration events must be a list')
        return v
    
    def add_calibration_event(self, result: CalibrationResult):
        """Add a new calibration event to history"""
        self.calibration_events.append(result)
        self.total_calibrations += 1
        # Keep only last 100 events to prevent memory issues
        if len(self.calibration_events) > 100:
            self.calibration_events = self.calibration_events[-100:]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class DriftAlert(BaseModel):
    """Alert for sensor drift detection"""
    sensor_id: str = Field(..., description="Sensor showing drift")
    current_drift: float = Field(..., description="Current drift percentage")
    threshold: float = Field(..., description="Drift threshold that was exceeded")
    last_calibration: Optional[datetime] = Field(None, description="Last calibration timestamp")
    recommended_action: str = Field(..., description="Recommended corrective action")
    severity: str = Field(default="warning", description="Alert severity level")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    @validator('severity')
    def validate_severity(cls, v):
        """Validate alert severity"""
        valid_severities = ["info", "warning", "critical"]
        if v not in valid_severities:
            raise ValueError(f'Severity must be one of {valid_severities}')
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }