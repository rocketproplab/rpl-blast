import time
import numpy as np
from .base import DataSource
from .data_types import SensorData
from app.config import Config
from datetime import datetime
from typing import Optional

# print("$$$$$ LOADING LATEST app/data_sources/simulator.py $$$$$")

class Simulator(DataSource):
    def __init__(self):
        config = Config()
        self.fcv_actual_states = [False] * config.NUM_FLOW_CONTROL_VALVES
        self.fcv_expected_states = [False] * config.NUM_FLOW_CONTROL_VALVES
        self.config = config
        
        # Store min/max for each sensor type from config
        self.pt_configs = [{'min': pt['min_value'], 'max': pt['max_value']} for pt in config.PRESSURE_TRANSDUCERS]
        self.tc_configs = [{'min': tc['min_value'], 'max': tc['max_value']} for tc in config.THERMOCOUPLES]
        self.lc_configs = [{'min': lc['min_value'], 'max': lc['max_value']} for lc in config.LOAD_CELLS]
        
        self.rng = np.random.default_rng()
        # print("Simulator initialized (from latest file if $$$$$ appeared).")
        # print(f"Number of pressure transducers: {config.NUM_PRESSURE_TRANSDUCERS}")
        # print(f"Number of thermocouples: {config.NUM_THERMOCOUPLES}")
        # print(f"Number of load cells: {config.NUM_LOAD_CELLS}")
        # print(f"Number of flow control valves: {config.NUM_FLOW_CONTROL_VALVES}")

    def initialize(self):
        pass
    
    def read_data(self) -> SensorData:
        pt_data = [self.rng.uniform(conf['min'], conf['max']) for conf in self.pt_configs]
        tc_data = [self.rng.uniform(conf['min'], conf['max']) for conf in self.tc_configs]
        lc_data = [self.rng.uniform(conf['min'], conf['max']) for conf in self.lc_configs]
        
        if self.config.NUM_FLOW_CONTROL_VALVES > 0:
            for i in range(self.config.NUM_FLOW_CONTROL_VALVES):
                if self.rng.random() < 0.10: 
                    self.fcv_actual_states[i] = not self.fcv_actual_states[i]
                if self.rng.random() < 0.05: 
                    self.fcv_expected_states[i] = not self.fcv_expected_states[i]
        
        sensor_data_obj = SensorData(
            pt=pt_data,
            tc=tc_data,
            lc=lc_data,
            fcv_actual=list(self.fcv_actual_states),
            fcv_expected=list(self.fcv_expected_states),
            timestamp=datetime.now()
        )
        # print(f"Simulator.read_data is returning: {sensor_data_obj.to_dict()}") # For debugging in Flask console
        return sensor_data_obj
    
    def close(self):
        pass 