import time
import numpy as np
from .base import DataSource
from .data_types import SensorData
from app.config import Config
from datetime import datetime
from typing import Optional

class Simulator(DataSource):
    def __init__(self):
        config = Config()
        self.last_update = 0
        self.update_interval = 0.1
        self.fcv_actual_states = np.zeros(config.NUM_FLOW_CONTROL_VALVES, dtype=bool)
        self.fcv_expected_states = np.zeros(config.NUM_FLOW_CONTROL_VALVES, dtype=bool)
        self.config = config
        
        # Store min/max for each sensor type from config
        self.pt_configs = [{'min': pt['min_value'], 'max': pt['max_value']} for pt in config.PRESSURE_TRANSDUCERS]
        self.tc_configs = [{'min': tc['min_value'], 'max': tc['max_value']} for tc in config.THERMOCOUPLES]
        self.lc_configs = [{'min': lc['min_value'], 'max': lc['max_value']} for lc in config.LOAD_CELLS]
        
        self.rng = np.random.default_rng()

    def initialize(self):
        pass
    
    def read_data(self) -> Optional[SensorData]:
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.last_update = current_time
            
            pt_data = [self.rng.uniform(conf['min'], conf['max']) for conf in self.pt_configs]
            tc_data = [self.rng.uniform(conf['min'], conf['max']) for conf in self.tc_configs]
            lc_data = [self.rng.uniform(conf['min'], conf['max']) for conf in self.lc_configs]
            
            # Occasionally toggle random valve states
            if self.rng.random() < 0.20:  # 20% chance each update
                if self.config.NUM_FLOW_CONTROL_VALVES > 0: # Ensure there are valves to toggle
                    valve_to_toggle = self.rng.integers(0, self.config.NUM_FLOW_CONTROL_VALVES)
                    self.fcv_actual_states[valve_to_toggle] = not self.fcv_actual_states[valve_to_toggle]
            
            # Occasionally update expected states (less frequently than actual)
            if self.rng.random() < 0.05:  # 5% chance each update
                if self.config.NUM_FLOW_CONTROL_VALVES > 0:
                    valve_to_toggle = self.rng.integers(0, self.config.NUM_FLOW_CONTROL_VALVES)
                    self.fcv_expected_states[valve_to_toggle] = not self.fcv_expected_states[valve_to_toggle]
            
            sensor_data = SensorData(
                pt=pt_data,
                tc=tc_data,
                lc=lc_data,
                fcv_actual=self.fcv_actual_states.tolist(),
                fcv_expected=self.fcv_expected_states.tolist(),
                timestamp=datetime.now()
            )
            
            return sensor_data
            
        return None
    
    def close(self):
        pass