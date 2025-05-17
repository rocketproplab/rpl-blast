import serial
import time
import json
import csv
from datetime import datetime
from pathlib import Path
from .base import DataSource
from .data_types import SensorData
from app.config import Config
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

ENCODING = 'ascii'

class SerialReader(DataSource):
    def __init__(self, port, baudrate):
        config = Config()
        self.config = config
        # Initialize arrays for all sensor types
        self.pt_data = [0.0] * config.NUM_PRESSURE_TRANSDUCERS
        self.tc_data = [0.0] * config.NUM_THERMOCOUPLES
        self.lc_data = [0.0] * config.NUM_LOAD_CELLS
        self.fcv_actual = [False] * config.NUM_FLOW_CONTROL_VALVES
        self.fcv_expected = [False] * config.NUM_FLOW_CONTROL_VALVES
        self.serial = None
        self.last_update = 0
        self.update_interval = 0.1  # 100ms update interval to match simulator
        
        # Initialize data logger
        self._setup_data_logger()

    def _setup_data_logger(self):
        """Setup CSV data logger"""
        # Create logs directory if it doesn't exist
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = log_dir / f'blast_data_{timestamp}.csv'
        
        # Create CSV file with headers
        headers = [
            'serial_timestamp',  # Timestamp from serial device
            'computer_timestamp'  # Timestamp from computer
        ]
        # Add headers for each sensor
        headers.extend([f'pt_{i+1}' for i in range(self.config.NUM_PRESSURE_TRANSDUCERS)])
        headers.extend([f'tc_{i+1}' for i in range(self.config.NUM_THERMOCOUPLES)])
        headers.extend([f'lc_{i+1}' for i in range(self.config.NUM_LOAD_CELLS)])
        headers.extend([f'fcv_{i+1}' for i in range(self.config.NUM_FLOW_CONTROL_VALVES)])
        
        with open(self.log_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
        
        logger.info(f"Data logger initialized: {self.log_file}")

    def _log_data(self, sensor_data, serial_timestamp):
        """Log sensor data to CSV file"""
        try:
            row = [
                serial_timestamp,  # Timestamp from serial device
                sensor_data.timestamp.isoformat()  # Computer timestamp
            ]
            row.extend(sensor_data.pt)
            row.extend(sensor_data.tc)
            row.extend(sensor_data.lc)
            row.extend(sensor_data.fcv_actual)  # Using fcv_actual as the main FCV state
            
            with open(self.log_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row)
        except Exception as e:
            logger.error(f"Error logging data: {e}")

    def initialize(self):
        try:
            self.serial = serial.Serial(
                port=self.config.SERIAL_PORT,
                baudrate=self.config.SERIAL_BAUDRATE,
                timeout=0.1
            )
            time.sleep(2)  # Wait for serial connection to stabilize
            logger.info(f"Serial connection established on {self.config.SERIAL_PORT}")
        except Exception as e:
            logger.error(f"Failed to initialize serial connection: {e}")
            raise

    def read_data(self):
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return None

        self.last_update = current_time

        if not self.serial or not self.serial.is_open:
            logger.error("Serial port not open")
            return None

        try:
            if self.serial.in_waiting > 0:
                raw_data = self.serial.readline().decode(ENCODING).strip()
                serial_timestamp = self._parse_serial_data(raw_data)
                if serial_timestamp is None:
                    return None
        except Exception as e:
            logger.error(f"Error reading serial data: {e}")
            return None

        # Create SensorData object with current values
        sensor_data = SensorData(
            pt=self.pt_data,
            tc=self.tc_data,
            lc=self.lc_data,
            fcv_actual=self.fcv_actual,
            fcv_expected=self.fcv_expected,
            timestamp=datetime.now()
        )

        # Log the data with both timestamps
        self._log_data(sensor_data, serial_timestamp)

        return sensor_data

    def _parse_serial_data(self, raw_data):
        """Parse incoming JSON serial data and update sensor values"""
        try:
            # Parse JSON data
            data = json.loads(raw_data)
            
            if 'value' not in data:
                logger.error("Missing 'value' key in JSON data")
                return None
                
            value = data['value']
            
            # Get timestamp from serial data
            serial_timestamp = value.get('timestamp')
            if not serial_timestamp:
                logger.warning("No timestamp in serial data")
                serial_timestamp = datetime.now().isoformat()
            
            # Update pressure transducer data
            if 'pt' in value:
                for i, val in enumerate(value['pt']):
                    if i < self.config.NUM_PRESSURE_TRANSDUCERS:
                        self.pt_data[i] = float(val)

            # Update thermocouple data
            if 'tc' in value:
                for i, val in enumerate(value['tc']):
                    if i < self.config.NUM_THERMOCOUPLES:
                        self.tc_data[i] = float(val)

            # Update load cell data
            if 'lc' in value:
                for i, val in enumerate(value['lc']):
                    if i < self.config.NUM_LOAD_CELLS:
                        self.lc_data[i] = float(val)

            # Update flow control valve data
            if 'fcv' in value:
                for i, val in enumerate(value['fcv']):
                    if i < self.config.NUM_FLOW_CONTROL_VALVES:
                        state = bool(val)
                        self.fcv_actual[i] = state
                        self.fcv_expected[i] = state  # Using same value for both actual and expected

            return serial_timestamp

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON data: {raw_data}")
            return None
        except Exception as e:
            logger.error(f"Error parsing serial data: {e}")
            return None

    def close(self):
        if self.serial and self.serial.is_open:
            self.serial.close()
            logger.info("Serial connection closed")
                    
                