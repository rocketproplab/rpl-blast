import yaml

class Config:
    def __init__(self):
        with open('app/config.yaml', 'r') as file:
            config = yaml.safe_load(file)
            
        # Data source config
        self.DATA_SOURCE = config['data_source']
        self.SERIAL_PORT = config['serial_port']
        self.SERIAL_BAUDRATE = config['serial_baudrate']
        
        # Pressure transducers
        self.PRESSURE_TRANSDUCERS = config['subpage1']['pressure_transducers']
        self.NUM_PRESSURE_TRANSDUCERS = len(self.PRESSURE_TRANSDUCERS)
        
        # Thermocouples and load cells
        self.THERMOCOUPLES = config['subpage2']['thermocouples']
        self.NUM_THERMOCOUPLES = len(self.THERMOCOUPLES)
        self.LOAD_CELLS = config['subpage2']['load_cells']
        self.NUM_LOAD_CELLS = len(self.LOAD_CELLS)
        
        # Flow control valves
        self.FLOW_CONTROL_VALVES = config['subpage3']['flow_control_valves']
        self.NUM_FLOW_CONTROL_VALVES = len(self.FLOW_CONTROL_VALVES)
        self.VALVE_GROUPS = config['subpage3']['flow_control_valve_groups']

    # Simulator configuration
    SIMULATOR_MIN_VALUE = 300
    SIMULATOR_MAX_VALUE = 700

    # Safety boundaries
    TEMPERATURE_BOUNDARIES = {
        'safe': [0, 600],
        'warning': [600, 800],
        'danger': [800, 1000]
    }
    
    PRESSURE_BOUNDARIES = {
        'safe': [0, 500],
        'warning': [500, 750],
        'danger': [750, 1000]
    }

    SECRET_KEY = 'your-secret-key' 