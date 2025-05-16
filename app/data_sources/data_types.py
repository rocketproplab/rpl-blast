from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List # Ensure List is imported

print("***** WTF LOADING LATEST app/data_sources/data_types.py *****") # ADDED FOR DEBUG

@dataclass
class SensorData:
    pt: List[float]
    tc: List[float]
    lc: List[float]
    fcv_actual: List[bool]   # New field for actual FCV states
    fcv_expected: List[bool] # New field for expected FCV states
    # fcv: List[bool]        # Old field, now removed
    timestamp: datetime

    @classmethod
    def create_empty(cls, num_pt: int, num_tc: int, num_lc: int, num_fcv: int) -> 'SensorData':
        """Creates an empty SensorData object with lists of appropriate lengths."""
        return cls(
            pt=[0.0] * num_pt,
            tc=[0.0] * num_tc,
            lc=[0.0] * num_lc,
            fcv_actual=[False] * num_fcv,    # Initialize new field
            fcv_expected=[False] * num_fcv,  # Initialize new field
            # fcv=[False] * num_fcv,         # Remove old field initialization
            timestamp=datetime.now()
        )

    def to_dict(self) -> dict:
        """Converts the SensorData object to a dictionary."""
        return {
            "pt": self.pt,
            "tc": self.tc,
            "lc": self.lc,
            "fcv_actual": self.fcv_actual,      # Add new field to dict
            "fcv_expected": self.fcv_expected,  # Add new field to dict
            # "fcv": self.fcv,                  # Remove old field from dict
            "timestamp": self.timestamp.isoformat()
        } 