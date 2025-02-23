from abc import ABC, abstractmethod
from .data_types import SensorData
from typing import Optional

class DataSource(ABC):
    @abstractmethod
    def initialize(self):
        pass

    @abstractmethod
    def read_data(self) -> Optional[SensorData]:
        """Should return a SensorData object or None if no new data"""
        pass

    @abstractmethod
    def close(self):
        pass 