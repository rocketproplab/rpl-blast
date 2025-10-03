"""
Compatibility layer for migrating Flask components to FastAPI
"""
import sys
import os
import importlib.util
from pathlib import Path
from typing import Dict, Any

# Get Flask app path
flask_app_path = Path(__file__).parent.parent.parent.parent / "BLAST_web plotly subplot"

def load_flask_module(module_path, module_name):
    """Dynamically load a module from Flask app"""
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

try:
    # Load Flask modules dynamically to avoid import conflicts
    simulator_path = flask_app_path / "app" / "data_sources" / "simulator.py"
    serial_reader_path = flask_app_path / "app" / "data_sources" / "serial_reader.py"
    data_types_path = flask_app_path / "app" / "data_sources" / "data_types.py"
    
    # Add Flask app to path temporarily for imports
    original_path = sys.path.copy()
    sys.path.insert(0, str(flask_app_path))
    
    # Load modules
    simulator_module = load_flask_module(simulator_path, "flask_simulator")
    serial_reader_module = load_flask_module(serial_reader_path, "flask_serial_reader")
    data_types_module = load_flask_module(data_types_path, "flask_data_types")
    
    # Extract classes
    FlaskSimulator = simulator_module.Simulator
    FlaskSerialReader = serial_reader_module.SerialReader
    FlaskSensorData = data_types_module.SensorData
    
    # Restore original path
    sys.path = original_path
    
    FLASK_IMPORTS_AVAILABLE = True
    print("✅ Flask imports successful for compatibility layer")
    
except Exception as e:
    print(f"Flask imports not available: {e}")
    FLASK_IMPORTS_AVAILABLE = False
    FlaskSimulator = None
    FlaskSerialReader = None
    FlaskSensorData = None


class FlaskDataSourceAdapter:
    """Adapter to use Flask data sources with FastAPI"""
    
    def __init__(self, settings):
        self.settings = settings
        self.flask_data_source = None
        self.is_running = False
        
    async def start(self) -> bool:
        """Start the Flask data source"""
        if not FLASK_IMPORTS_AVAILABLE:
            return False
            
        try:
            if self.settings.data_source.value == "simulator":
                self.flask_data_source = FlaskSimulator()
            else:
                self.flask_data_source = FlaskSerialReader(
                    self.settings.serial_port, 
                    self.settings.serial_baudrate
                )
            
            # Initialize the Flask data source
            self.flask_data_source.initialize()
            self.is_running = True
            return True
            
        except Exception as e:
            print(f"Failed to start Flask data source: {e}")
            return False
    
    async def stop(self):
        """Stop the Flask data source"""
        if self.flask_data_source:
            try:
                # Flask data sources don't have explicit stop methods
                pass
            except Exception as e:
                print(f"Error stopping Flask data source: {e}")
        self.is_running = False
    
    async def read_sensors(self):
        """Read sensor data from Flask data source and convert to FastAPI format"""
        if not self.flask_data_source or not self.is_running:
            return None
            
        try:
            # Get data from Flask source
            flask_data = self.flask_data_source.read_data()
            
            if not flask_data:
                return None
            
            # Convert Flask SensorData to FastAPI format
            return self._convert_flask_data_to_fastapi(flask_data)
            
        except Exception as e:
            print(f"Error reading from Flask data source: {e}")
            return None
    
    def _convert_flask_data_to_fastapi(self, flask_data):
        """Convert Flask SensorData to FastAPI TelemetryPacket format"""
        from app.models.sensors import TelemetryPacket, SensorReading
        
        # Convert to dict first
        data_dict = flask_data.to_dict()
        
        # Create FastAPI sensor readings
        pressure_transducers = []
        thermocouples = []
        load_cells = []
        valve_states = {}
        
        # Convert pressure transducers
        if 'pt' in data_dict:
            for i, value in enumerate(data_dict['pt']):
                sensor_id = f"pt{i+1}"
                pressure_transducers.append(SensorReading(
                    sensor_id=sensor_id,
                    value=float(value),
                    unit="psi",
                    calibrated=False  # Will be updated by calibration service
                ))
        
        # Convert thermocouples
        if 'tc' in data_dict:
            for i, value in enumerate(data_dict['tc']):
                sensor_id = f"tc{i+1}"
                thermocouples.append(SensorReading(
                    sensor_id=sensor_id,
                    value=float(value),
                    unit="celsius",
                    calibrated=False
                ))
        
        # Convert load cells
        if 'lc' in data_dict:
            for i, value in enumerate(data_dict['lc']):
                sensor_id = f"lc{i+1}"
                load_cells.append(SensorReading(
                    sensor_id=sensor_id,
                    value=float(value),
                    unit="lbs",
                    calibrated=False
                ))
        
        # Convert valve states
        if hasattr(flask_data, 'fcv_actual'):
            fcv_actual = getattr(flask_data, 'fcv_actual', [])
            for i, state in enumerate(fcv_actual):
                valve_states[f"fcv{i+1}"] = bool(state)
        elif 'fcv_actual' in data_dict:
            fcv_actual = data_dict['fcv_actual']
            for i, state in enumerate(fcv_actual):
                valve_states[f"fcv{i+1}"] = bool(state)
        
        # Create telemetry packet
        return TelemetryPacket(
            pressure_transducers=pressure_transducers,
            thermocouples=thermocouples,
            load_cells=load_cells,
            valve_states=valve_states
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for Flask data source"""
        return {
            "running": self.is_running,
            "data_source_type": "flask_adapter",
            "flask_available": FLASK_IMPORTS_AVAILABLE,
            "error_count": 0
        }


def create_flask_compatible_data_source(settings):
    """Factory function to create Flask-compatible data source"""
    return FlaskDataSourceAdapter(settings)