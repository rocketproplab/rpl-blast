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

ENCODING = 'ascii'

class SerialReader(DataSource):
    def __init__(self, port, baudrate):
        config = Config()
        self.config = config
        self.port = port
        self.baudrate = baudrate
        
        # Initialize arrays for all sensor types
        self.pt_data = [0.0] * config.NUM_PRESSURE_TRANSDUCERS
        self.tc_data = [0.0] * config.NUM_THERMOCOUPLES
        self.lc_data = [0.0] * config.NUM_LOAD_CELLS
        self.fcv_actual = [False] * config.NUM_FLOW_CONTROL_VALVES
        self.fcv_expected = [False] * config.NUM_FLOW_CONTROL_VALVES
        self.serial = None
        self.last_update = 0
        self.update_interval = 0.1  # 100ms update interval to match simulator
        
        # Initialize logging and error recovery
        self.ErrorType = None  # Initialize ErrorType reference
        try:
            from app.logging.logger_manager import get_logger_manager
            from app.logging.performance_monitor import get_performance_monitor
            from app.logging.event_logger import get_event_logger
            from app.logging.error_recovery import get_error_recovery, ErrorType
            from app.logging.serial_logger import get_serial_logger
            
            self.logger = get_logger_manager().get_logger('app')
            self.perf_monitor = get_performance_monitor()
            self.event_logger = get_event_logger()
            self.error_recovery = get_error_recovery()
            self.serial_comm_logger = get_serial_logger()
            self.ErrorType = ErrorType  # Store reference to ErrorType enum
            
            self.logger.info(f"SerialReader initialized for {port} @ {baudrate}")
        except ImportError:
            # Fallback to basic logging
            logging.basicConfig(level=logging.DEBUG)
            self.logger = logging.getLogger(__name__)
            self.perf_monitor = None
            self.event_logger = None
            self.error_recovery = None
            self.serial_comm_logger = None
        
        # Initialize data logger
        self._setup_data_logger()

    def _setup_data_logger(self):
        """Setup CSV data logger"""
        # Get the run directory from logger manager
        try:
            from app.logging.logger_manager import get_logger_manager
            logger_mgr = get_logger_manager()
            if hasattr(logger_mgr, 'run_dir'):
                log_dir = logger_mgr.run_dir / 'data'
            else:
                # Fallback to logs directory
                log_dir = Path('logs')
                log_dir.mkdir(exist_ok=True)
        except:
            # Fallback if logging not available
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
        
        self.logger.info(f"Data logger initialized: {self.log_file}")

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
            self.logger.error(f"Error logging data: {e}")

    def initialize(self):
        """Initialize serial connection with error recovery"""
        def connect():
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1
            )
            time.sleep(2)  # Wait for serial connection to stabilize
            self.logger.info(f"Serial connection established on {self.port}")
            
            # Log connection event
            if self.event_logger:
                self.event_logger.log_connection_event('connect', {
                    'port': self.port,
                    'baudrate': self.baudrate
                })
            return True  # Return True to indicate success
        
        # Try to connect with retry
        if self.error_recovery and self.ErrorType:
            result = self.error_recovery.retry_with_backoff(
                connect,
                self.ErrorType.SERIAL_DISCONNECT
            )
            if not result:
                self.logger.error(f"Failed to initialize serial connection on {self.port} after retries")
                raise serial.SerialException(f"Could not connect to {self.port}")
        else:
            try:
                connect()
            except Exception as e:
                self.logger.error(f"Failed to initialize serial connection: {e}")
                raise

    def read_data(self):
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return None

        self.last_update = current_time

        if not self.serial or not self.serial.is_open:
            self.logger.error("Serial port not open")
            # Try to reconnect
            if self.error_recovery:
                self.error_recovery.recover(
                    serial.SerialException("Port not open"),
                    self.ErrorType.SERIAL_DISCONNECT,
                    {'port': self.port, 'reconnect_func': self.initialize}
                )
            return None

        try:
            # Time the serial read operation
            start_time = time.perf_counter()
            
            if self.serial.in_waiting > 0:
                raw_data = self.serial.readline().decode(ENCODING).strip()
                
                # Log timing
                read_time_ms = (time.perf_counter() - start_time) * 1000
                if self.perf_monitor:
                    self.perf_monitor.record_metric('serial_read_time', read_time_ms, 'ms')
                
                # Log if slow
                if read_time_ms > 100:
                    self.logger.warning(f"Slow serial read: {read_time_ms:.1f}ms")
                
                # Log raw data with serial logger
                if self.serial_comm_logger and len(raw_data) > 0:
                    # Try to parse for logging
                    try:
                        parsed = json.loads(raw_data)
                        self.serial_comm_logger.log_received(raw_data.encode(ENCODING), parsed)
                    except:
                        self.serial_comm_logger.log_received(raw_data.encode(ENCODING), None)
                
                serial_timestamp = self._parse_serial_data(raw_data)
                if serial_timestamp is None:
                    return None
            else:
                # No data available yet
                return None
                
        except serial.SerialTimeoutException as e:
            # Log timeout
            if self.serial_comm_logger:
                self.serial_comm_logger.log_timeout(0.1, f"Serial read timeout on {self.port}")
            
            # Handle timeout with retry
            if self.error_recovery:
                self.error_recovery.recover(e, self.ErrorType.SERIAL_TIMEOUT, {'port': self.port})
            else:
                self.logger.error(f"Serial timeout: {e}")
            return None
            
        except Exception as e:
            # Handle other errors
            self.logger.error(f"Error reading serial data: {e}")
            if self.error_recovery:
                self.error_recovery.recover(e, self.ErrorType.SERIAL_DISCONNECT, 
                                           {'port': self.port, 'reconnect_func': self.initialize})
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
        
        # Check thresholds
        if self.event_logger:
            self.event_logger.check_sensor_thresholds(sensor_data, self.config)
        
        # Log performance metric
        if self.perf_monitor:
            self.perf_monitor.record_metric('serial_data_processed', 1, 'count')

        return sensor_data

    def _convert_pt_voltage_to_psi(self, value, pt_name):
        """Convert PT voltage reading to PSI"""
        if pt_name == "GN2":
            conv = self.config.PT_CONVERSION['GN2']
        else:
            conv = self.config.PT_CONVERSION['other']
            
        # return (((value/1023*5) - conv['min_voltage']) / 
                # (conv['max_voltage'] - conv['min_voltage'])) * conv['max_psi']
        return value - conv['offset']

    def _parse_serial_data(self, raw_data):
        """Parse incoming JSON serial data and update sensor values"""
        try:
            # Parse JSON data
            data = json.loads(raw_data)
            
            if 'value' not in data:
                self.logger.error("Missing 'value' key in JSON data")
                return None
                
            value = data['value']
            
            # Get timestamp from serial data
            serial_timestamp = value.get('timestamp')
            if not serial_timestamp:
                self.logger.warning("No timestamp in serial data")
                serial_timestamp = datetime.now().isoformat()
            
            # Update pressure transducer data
            if 'pt' in value:
                for i, voltage in enumerate(value['pt']):
                    if i < self.config.NUM_PRESSURE_TRANSDUCERS:
                        # Convert voltage to PSI based on PT type
                        pt_name = self.config.PRESSURE_TRANSDUCERS[i]['name']
                        self.pt_data[i] = self._convert_pt_voltage_to_psi(float(voltage), pt_name)

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
            self.logger.error(f"Invalid JSON data: {raw_data}")
            if self.serial_comm_logger:
                self.serial_comm_logger.log_protocol_error('json_parse', raw_data.encode(ENCODING), e)
            return None
        except Exception as e:
            self.logger.error(f"Error parsing serial data: {e}")
            if self.serial_comm_logger:
                self.serial_comm_logger.log_protocol_error('malformed', raw_data.encode(ENCODING), e)
            return None

    def close(self):
        if self.serial and self.serial.is_open:
            self.serial.close()
            self.logger.info("Serial connection closed")
                    
                