class Config:
    # Data source configuration
    DATA_SOURCE = 'simulator'  # Options: 'simulator' or 'serial'
    
    # Serial configuration
    SERIAL_PORT = '/dev/cu.usbmodem1201'  # Change this to match your system
    SERIAL_BAUDRATE = 9600
    
    # Simulator configuration
    SIMULATOR_MIN_VALUE = 300
    SIMULATOR_MAX_VALUE = 700

    # Sensor configuration
    NUM_THERMOCOUPLES = 3
    NUM_PRESSURE_TRANSDUCERS = 3
    NUM_FLOW_CONTROL_VALVES = 6

    SECRET_KEY = 'your-secret-key' 