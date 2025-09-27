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
        
        # Initialize logging if available
        try:
            from app.logging.logger_manager import get_logger_manager
            from app.logging.performance_monitor import get_performance_monitor
            from app.logging.event_logger import get_event_logger
            
            self.logger = get_logger_manager().get_logger('app')
            self.perf_monitor = get_performance_monitor()
            self.event_logger = get_event_logger()
            self.logger.info("Simulator initialized with logging")
        except ImportError:
            self.logger = None
            self.perf_monitor = None
            self.event_logger = None
        
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
            
            # Time data generation
            start_time = time.perf_counter()
            
            # Generate sensor data with occasional threshold violations for testing
            pt_data = []
            for conf in self.pt_configs:
                # 5% chance to generate warning level, 2% chance for danger level
                rand = self.rng.random()
                if rand < 0.02:  # Danger level
                    value = self.rng.uniform(conf['max'] * 0.8, conf['max'] * 0.95)
                elif rand < 0.05:  # Warning level
                    value = self.rng.uniform(conf['max'] * 0.5, conf['max'] * 0.7)
                else:  # Normal range
                    value = self.rng.uniform(conf['min'] + conf['max'] * 0.1, conf['max'] * 0.4)
                pt_data.append(value)
            
            tc_data = [self.rng.uniform(conf['min'] + conf['max'] * 0.3, conf['max'] * 0.7) for conf in self.tc_configs]
            lc_data = [self.rng.uniform(conf['min'] + conf['max'] * 0.3, conf['max'] * 0.7) for conf in self.lc_configs]
            
            # Log valve state changes
            if self.rng.random() < 0.20:  # 20% chance each update
                if self.config.NUM_FLOW_CONTROL_VALVES > 0: # Ensure there are valves to toggle
                    valve_to_toggle = self.rng.integers(0, self.config.NUM_FLOW_CONTROL_VALVES)
                    old_state = self.fcv_actual_states[valve_to_toggle]
                    self.fcv_actual_states[valve_to_toggle] = not old_state
                    
                    # Log valve change
                    if self.event_logger:
                        valve = self.config.FLOW_CONTROL_VALVES[valve_to_toggle]
                        self.event_logger.log_valve_operation(
                            valve['id'], valve['name'],
                            self.fcv_actual_states[valve_to_toggle],
                            'simulator', True
                        )
            
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
            
            # Log timing
            duration_ms = (time.perf_counter() - start_time) * 1000
            if self.perf_monitor:
                self.perf_monitor.record_metric('simulator_generate', duration_ms, 'ms')
            
            # Check thresholds
            if self.event_logger:
                self.event_logger.check_sensor_thresholds(sensor_data, self.config)
            
            return sensor_data
            
        return None
    
    def close(self):
        pass