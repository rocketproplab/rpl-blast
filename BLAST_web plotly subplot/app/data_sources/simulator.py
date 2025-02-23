import time
import random
from .base import DataSource
from .data_types import SensorData
from app.config import Config
from datetime import datetime
from typing import Optional

class Simulator(DataSource):
    def __init__(self):
        config = Config()  # Create instance
        self.last_update = 0
        self.update_interval = 0.1
        self.fcv_states = [False] * config.NUM_FLOW_CONTROL_VALVES
        self.min_value = config.SIMULATOR_MIN_VALUE
        self.max_value = config.SIMULATOR_MAX_VALUE
        self.config = config  # Store the config instance

    def initialize(self):
        pass
    
    def read_data(self) -> Optional[SensorData]:
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.last_update = current_time
            
            # Generate random data for each sensor type
            tc_data = [
                random.uniform(self.min_value, self.max_value)
                for _ in range(self.config.NUM_THERMOCOUPLES)
            ]
            
            pt_data = [
                random.uniform(self.min_value, self.max_value)
                for _ in range(self.config.NUM_PRESSURE_TRANSDUCERS)
            ]
            
            # Occasionally toggle random valve states
            if random.random() < 0.20:  # 20% chance each update
                valve_to_toggle = random.randint(0, self.config.NUM_FLOW_CONTROL_VALVES - 1)
                self.fcv_states[valve_to_toggle] = not self.fcv_states[valve_to_toggle]
            
            return SensorData(
                tc=tc_data,
                pt=pt_data,
                fcv=self.fcv_states.copy(),
                timestamp=datetime.now()
            )
            
        return None
    
    def close(self):
        pass