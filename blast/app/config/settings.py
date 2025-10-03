"""Unified Configuration Management with Pydantic"""
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from typing import List, Dict, Optional
from enum import Enum
import yaml
from pathlib import Path


class DataSourceType(str, Enum):
    SERIAL = "serial"
    SIMULATOR = "simulator"


class SensorConfig(BaseSettings):
    name: str
    id: str
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    min_value: float
    max_value: float
    warning_threshold: float
    danger_threshold: float
    unit: str = "psi"
    calibration_enabled: bool = True
    temperature_compensation: bool = False


class CalibrationSettings(BaseSettings):
    auto_zero_enabled: bool = True
    drift_monitoring: bool = True
    calibration_interval_hours: int = 24
    drift_threshold_percent: float = 2.0
    measurement_duration_ms: int = 5000
    noise_threshold: float = 0.1


class Settings(BaseSettings):
    """Unified BLAST configuration settings"""
    
    # Data source configuration
    data_source: DataSourceType = DataSourceType.SERIAL
    serial_port: str = "/dev/cu.usbmodem1201"
    serial_baudrate: int = 115200
    
    # Sensor configurations
    pressure_transducers: List[SensorConfig] = []
    thermocouples: List[SensorConfig] = []
    load_cells: List[SensorConfig] = []
    flow_control_valves: List[Dict[str, str]] = []
    
    # Calibration settings
    calibration: CalibrationSettings = CalibrationSettings()
    
    # Performance settings
    telemetry_interval_ms: int = 100
    max_websocket_connections: int = 50
    heartbeat_interval_ms: int = 30000
    
    # Logging configuration
    log_level: str = "INFO"
    log_retention_days: int = 30
    log_max_size_mb: int = 100
    
    # Application settings
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000
    
    @validator('pressure_transducers', 'thermocouples', 'load_cells', pre=True)
    def parse_sensor_configs(cls, v):
        """Convert dict configs to SensorConfig objects"""
        if isinstance(v, list) and v and isinstance(v[0], dict):
            return [SensorConfig(**sensor) for sensor in v]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            """Load from YAML file first, then env, then init"""
            return (
                init_settings,
                yaml_settings_source,
                env_settings,
                file_secret_settings,
            )


def yaml_settings_source(settings: BaseSettings) -> Dict[str, any]:
    """Load settings from YAML configuration file"""
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f) or {}
    return {}