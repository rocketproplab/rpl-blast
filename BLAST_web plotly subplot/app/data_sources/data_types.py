from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from app.config import Config

@dataclass
class SensorData:
    """Data structure for sensor readings with specific sensor types:
    tc: Thermocouple readings
    pt: Pressure transducer readings
    fcv: Flow control valve states
    """
    tc: List[float]
    pt: List[float]
    fcv: List[bool]
    timestamp: datetime

    def __post_init__(self):
        """Validate the lengths of sensor arrays"""
        if len(self.tc) != Config.NUM_THERMOCOUPLES:
            raise ValueError(f"Expected {Config.NUM_THERMOCOUPLES} thermocouples, got {len(self.tc)}")
        if len(self.pt) != Config.NUM_PRESSURE_TRANSDUCERS:
            raise ValueError(f"Expected {Config.NUM_PRESSURE_TRANSDUCERS} pressure transducers, got {len(self.pt)}")
        if len(self.fcv) != Config.NUM_FLOW_CONTROL_VALVES:
            raise ValueError(f"Expected {Config.NUM_FLOW_CONTROL_VALVES} flow control valves, got {len(self.fcv)}")

    @classmethod
    def create_empty(cls) -> 'SensorData':
        """Create a new SensorData instance with zero values"""
        return cls(
            tc=[0.0] * Config.NUM_THERMOCOUPLES,
            pt=[0.0] * Config.NUM_PRESSURE_TRANSDUCERS,
            fcv=[False] * Config.NUM_FLOW_CONTROL_VALVES,
            timestamp=datetime.now()
        )

    def to_dict(self) -> dict:
        """Convert the data to a dictionary format for JSON serialization"""
        return {
            'tc': self.tc,
            'pt': self.pt,
            'fcv': self.fcv,
            'timestamp': self.timestamp.timestamp()
        } 