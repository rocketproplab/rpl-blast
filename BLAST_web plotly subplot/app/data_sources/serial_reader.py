import serial
import time
from .base import DataSource
from app.config import Config
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

ENCODING = 'ascii'

class SerialReader(DataSource):
    def __init__(self, port, baudrate):
        config = Config()  # Create instance
        self.fcv_states = [False] * config.NUM_FLOW_CONTROL_VALVES
        self.serial = None
        self.last_value = 200  # Default to released state
        self.led_state = False

    def initialize(self):
        self.serial = serial.Serial(
            port=Config.SERIAL_PORT,
            baudrate=Config.SERIAL_BAUDRATE,
            timeout=0.1
        )
        time.sleep(2)

    def read_data(self):
        if self.serial and self.serial.in_waiting > 0:
            raw_data = self.serial.readline().decode(ENCODING).strip()

            if raw_data.startswith("SENSOR:"):
                sensor_data = raw_data[7:]
                if sensor_data == "Button Pressed":
                    logger.info("Button state: PRESSED")
                    self.last_value = 800
                elif sensor_data == "Button Released":
                    logger.info("Button state: RELEASED")
                    self.last_value = 200
            
            return self.last_value
        
    def close(self):
        if self.serial:
            self.serial.close()
                    
                