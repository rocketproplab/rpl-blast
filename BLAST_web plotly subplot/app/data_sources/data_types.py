from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from app.config import Config

# Create a config instance
config = Config()

@dataclass
class SensorData:
    """Data structure for sensor readings with specific sensor types:
    tc: Thermocouple readings
    pt: Pressure transducer readings
    fcv_actual: Actual flow control valve states
    fcv_expected: Expected flow control valve states
    lc: Load cell readings
    """
    tc: List[float]
    pt: List[float]
    fcv_actual: List[bool]
    fcv_expected: List[bool]
    lc: List[float]
    timestamp: datetime

    def __post_init__(self):
        """Validate the lengths of sensor arrays"""
        if len(self.tc) != config.NUM_THERMOCOUPLES:
            raise ValueError(f"Expected {config.NUM_THERMOCOUPLES} thermocouples, got {len(self.tc)}")
        if len(self.pt) != config.NUM_PRESSURE_TRANSDUCERS:
            raise ValueError(f"Expected {config.NUM_PRESSURE_TRANSDUCERS} pressure transducers, got {len(self.pt)}")
        if len(self.fcv_actual) != config.NUM_FLOW_CONTROL_VALVES:
            raise ValueError(f"Expected {config.NUM_FLOW_CONTROL_VALVES} flow control valves, got {len(self.fcv_actual)}")
        if len(self.fcv_expected) != config.NUM_FLOW_CONTROL_VALVES:
            raise ValueError(f"Expected {config.NUM_FLOW_CONTROL_VALVES} flow control valves, got {len(self.fcv_expected)}")
        if len(self.lc) != config.NUM_LOAD_CELLS:
            raise ValueError(f"Expected {config.NUM_LOAD_CELLS} load cells, got {len(self.lc)}")

    @classmethod
    def create_empty(cls) -> 'SensorData':
        """Create a new SensorData instance with zero values"""
        return cls(
            tc=[0.0] * config.NUM_THERMOCOUPLES,
            pt=[0.0] * config.NUM_PRESSURE_TRANSDUCERS,
            fcv_actual=[False] * config.NUM_FLOW_CONTROL_VALVES,
            fcv_expected=[False] * config.NUM_FLOW_CONTROL_VALVES,
            lc=[0.0] * config.NUM_LOAD_CELLS,
            timestamp=datetime.now()
        )

    def to_dict(self) -> dict:
        """Convert the data to a dictionary format for JSON serialization"""
        return {
            'tc': self.tc,
            'pt': self.pt,
            'fcv_actual': self.fcv_actual,
            'fcv_expected': self.fcv_expected,
            'lc': self.lc,
            'timestamp': self.timestamp.timestamp()
        } 