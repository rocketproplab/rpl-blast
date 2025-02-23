import time
import random
from .base import DataSource
from .data_types import SensorData
from app.config import Config
from datetime import datetime
from typing import Optional

class Simulator(DataSource):
    def __init__(self):
        self.last_update = 0
        self.update_interval = 0.1
        self.fcv_states = [False] * Config.NUM_FLOW_CONTROL_VALVES

    def initialize(self):
        pass
    
    def read_data(self) -> Optional[SensorData]:
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.last_update = current_time
            
            # Generate random data for each sensor type
            tc_data = [
                random.uniform(Config.SIMULATOR_MIN_VALUE, Config.SIMULATOR_MAX_VALUE)
                for _ in range(Config.NUM_THERMOCOUPLES)
            ]
            
            pt_data = [
                random.uniform(Config.SIMULATOR_MIN_VALUE, Config.SIMULATOR_MAX_VALUE)
                for _ in range(Config.NUM_PRESSURE_TRANSDUCERS)
            ]
            
            # Occasionally toggle random valve states
            if random.random() < 0.20:  # 20% chance each update
                valve_to_toggle = random.randint(0, Config.NUM_FLOW_CONTROL_VALVES - 1)
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