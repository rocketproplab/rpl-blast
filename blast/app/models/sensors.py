"""Sensor data models with Pydantic validation"""
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum


class SensorQuality(str, Enum):
    """Sensor reading quality indicators"""
    GOOD = "good"
    WARNING = "warning"
    DANGER = "danger"
    ERROR = "error"
    UNCALIBRATED = "uncalibrated"


class SensorReading(BaseModel):
    """Individual sensor reading with validation"""
    sensor_id: str = Field(..., description="Unique sensor identifier")
    value: float = Field(..., description="Calibrated sensor value")
    raw_value: Optional[float] = Field(None, description="Raw uncalibrated value")
    unit: str = Field(..., description="Unit of measurement")
    timestamp: datetime = Field(default_factory=datetime.now)
    quality: SensorQuality = Field(default=SensorQuality.GOOD)
    calibrated: bool = Field(default=False, description="Whether calibration has been applied")
    
    @validator('value', 'raw_value')
    def validate_sensor_value(cls, v):
        """Validate sensor values are reasonable"""
        if v is not None and not isinstance(v, (int, float)):
            raise ValueError('Sensor value must be numeric')
        if v is not None and not (-1e6 <= v <= 1e6):
            raise ValueError('Sensor value must be within reasonable range')
        return v
    
    @validator('sensor_id')
    def validate_sensor_id(cls, v):
        """Validate sensor ID format"""
        if not v or not isinstance(v, str):
            raise ValueError('Sensor ID must be a non-empty string')
        if len(v) > 50:
            raise ValueError('Sensor ID must be 50 characters or less')
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TelemetryPacket(BaseModel):
    """Complete telemetry data packet"""
    timestamp: datetime = Field(default_factory=datetime.now)
    pressure_transducers: List[SensorReading] = Field(default_factory=list)
    thermocouples: List[SensorReading] = Field(default_factory=list)
    load_cells: List[SensorReading] = Field(default_factory=list)
    valve_states: Dict[str, bool] = Field(default_factory=dict)
    system_status: str = Field(default="operational")
    
    @validator('pressure_transducers', 'thermocouples', 'load_cells')
    def validate_sensor_lists(cls, v):
        """Validate sensor reading lists"""
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError('Sensor readings must be a list')
        return v
    
    @validator('valve_states')
    def validate_valve_states(cls, v):
        """Validate valve states dictionary"""
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError('Valve states must be a dictionary')
        for valve_id, state in v.items():
            if not isinstance(state, bool):
                raise ValueError(f'Valve state for {valve_id} must be boolean')
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SensorStats(BaseModel):
    """Statistical information about sensor readings"""
    sensor_id: str
    latest_value: Optional[float] = None
    average_10s: Optional[float] = None
    rate_change: Optional[float] = None
    max_recorded: Optional[float] = None
    min_recorded: Optional[float] = None
    sample_count: int = 0
    last_updated: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }