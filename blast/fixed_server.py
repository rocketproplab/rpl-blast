#!/usr/bin/env python3
"""
BLAST FastAPI Server - Fixed to match original Flask design
"""
import sys
from pathlib import Path
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from app.config.settings import Settings

# Global services
settings = None
data_source = None
data_source_type = "unknown"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global settings, data_source, data_source_type
    print("🚀 Starting BLAST FastAPI Server...")
    
    # Initialize settings - bypass complex pydantic loading and read YAML directly
    import yaml
    from pathlib import Path
    
    config_path = Path("app/config/config.yaml")
    if config_path.exists():
        with open(config_path, 'r') as f:
            yaml_config = yaml.safe_load(f)
        data_source_type = yaml_config.get('data_source', 'serial')
        print(f"✅ Configuration loaded from YAML - Data source: {data_source_type}")
    else:
        data_source_type = 'serial'
        print(f"⚠️  No config file found, using default: {data_source_type}")
    
    # Try to create settings object but don't rely on it
    try:
        settings = Settings()
    except:
        settings = None
    
    # Initialize data source similar to original Flask
    if data_source_type == "simulator":
        # Use simple simulator matching original Flask behavior
        try:
            import time
            import numpy as np
            from datetime import datetime
            
            class SimpleSimulator:
                def __init__(self):
                    self.last_update = 0
                    self.update_interval = 0.1
                    self.fcv_actual_states = np.array([False, True, False, False, True, False, True])
                    self.fcv_expected_states = np.array([False, True, False, False, True, False, True])
                    self.rng = np.random.default_rng()
                
                def read_data(self):
                    current_time = time.time()
                    if current_time - self.last_update >= self.update_interval:
                        self.last_update = current_time
                        
                        # Generate PT data (5 sensors)
                        pt_data = []
                        for i in range(5):
                            rand = self.rng.random()
                            if rand < 0.02:  # Danger level
                                value = self.rng.uniform(320, 380)
                            elif rand < 0.05:  # Warning level
                                value = self.rng.uniform(200, 240)
                            else:  # Normal range
                                value = self.rng.uniform(10, 200)
                            pt_data.append(round(value, 1))
                        
                        # Generate TC data (3 sensors)
                        tc_data = [round(self.rng.uniform(20, 100), 1) for _ in range(3)]
                        
                        # Generate LC data (3 sensors)
                        lc_data = [round(self.rng.uniform(50, 300), 1) for _ in range(3)]
                        
                        # Occasionally change valve states
                        if self.rng.random() < 0.20:
                            valve_to_toggle = self.rng.integers(0, len(self.fcv_actual_states))
                            self.fcv_actual_states[valve_to_toggle] = not self.fcv_actual_states[valve_to_toggle]
                        
                        return {
                            'pt': pt_data,
                            'tc': tc_data,
                            'lc': lc_data,
                            'fcv_actual': self.fcv_actual_states.tolist(),
                            'fcv_expected': self.fcv_expected_states.tolist(),
                            'timestamp': datetime.now().isoformat()
                        }
                    return None
                
                async def stop(self):
                    """Dummy stop method for compatibility"""
                    pass
            
            data_source = SimpleSimulator()
            print("✅ Simple simulator started (matches original Flask)")
        except Exception as e:
            print(f"⚠️  Failed to start simulator: {e}")
            data_source = None
    else:
        try:
            from app.data_sources.serial_reader import AsyncSerialReader
            config = {
                'pressure_transducers': [pt.dict() for pt in settings.pressure_transducers],
                'thermocouples': [tc.dict() for tc in settings.thermocouples],
                'load_cells': [lc.dict() for lc in settings.load_cells],
                'flow_control_valves': settings.flow_control_valves,
                'serial_port': settings.serial_port,
                'serial_baudrate': settings.serial_baudrate
            }
            data_source = AsyncSerialReader(config)
            result = await data_source.start()
            if result:
                print("✅ Serial data source started")
            else:
                print("⚠️  Serial data source failed to start")
        except Exception as e:
            print(f"⚠️  Failed to start serial: {e}")
            data_source = None
    
    print("🎯 Server ready!")
    
    yield
    
    # Shutdown
    if data_source and hasattr(data_source, 'stop'):
        await data_source.stop()
    print("👋 Server shutdown complete")

# Create FastAPI app
app = FastAPI(title="BLAST - Big Launch Analysis & Stats Terminal", lifespan=lifespan)

# Mount static files
static_dir = Path("app/static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    print("✅ Static files mounted")

# Templates
templates = None
template_dir = Path("app/templates")
if template_dir.exists():
    templates = Jinja2Templates(directory="app/templates")
    print("✅ Templates loaded")

# Routes matching original Flask structure

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Landing page with links to each sensor type - matches original Flask"""
    if templates and settings:
        # Create a config object matching original Flask structure
        config = {
            'pressure_transducers': [pt.dict() for pt in settings.pressure_transducers],
            'thermocouples': [tc.dict() for tc in settings.thermocouples],
            'load_cells': [lc.dict() for lc in settings.load_cells],
            'flow_control_valves': [fv.dict() for fv in settings.flow_control_valves]
        }
        return templates.TemplateResponse("index.html", {
            "request": request,
            "config": config
        })
    else:
        return HTMLResponse("""
        <html>
            <head><title>BLAST | Big Launch Analysis & Stats Terminal</title></head>
            <body>
                <h1>🚀 BLAST - Big Launch Analysis & Stats Terminal</h1>
                <div style="margin: 20px;">
                    <h2>Sensor Groups:</h2>
                    <ul>
                        <li><a href="/thermocouples">Thermocouples & Load Cells</a></li>
                        <li><a href="/pressure">Pressure Transducers</a></li>
                        <li><a href="/valves">Flow Control Valves</a></li>
                    </ul>
                </div>
            </body>
        </html>
        """)

@app.get("/thermocouples", response_class=HTMLResponse)
async def thermocouples(request: Request):
    """Thermocouple monitoring page - matches original Flask"""
    if templates and settings:
        config = {
            'thermocouples': [tc.dict() for tc in settings.thermocouples],
            'load_cells': [lc.dict() for lc in settings.load_cells],
            'temperature_boundaries': {},  # Add if needed
            'load_cell_boundaries': {}     # Add if needed
        }
        return templates.TemplateResponse("thermocouples.html", {
            "request": request,
            "config": config
        })
    else:
        return HTMLResponse("<h1>Thermocouples & Load Cells</h1><p>Templates not available</p>")

@app.get("/pressure", response_class=HTMLResponse)
async def pressure(request: Request):
    """Pressure transducer monitoring page - matches original Flask"""
    if templates and settings:
        config = {
            'pressure_transducers': [pt.dict() for pt in settings.pressure_transducers],
            'pressure_boundaries': {}  # Add if needed
        }
        return templates.TemplateResponse("pressure.html", {
            "request": request,
            "config": config
        })
    else:
        return HTMLResponse("<h1>Pressure Transducers</h1><p>Templates not available</p>")

@app.get("/valves", response_class=HTMLResponse)
async def valves(request: Request):
    """Flow control valve monitoring page - matches original Flask"""
    if templates and settings:
        config = {
            'flow_control_valves': [fv.dict() for fv in settings.flow_control_valves]
        }
        return templates.TemplateResponse("valves.html", {
            "request": request,
            "config": config
        })
    else:
        return HTMLResponse("<h1>Flow Control Valves</h1><p>Templates not available</p>")

@app.get("/data")
async def get_data(sensor_type: str = "all"):
    """Get sensor data - matches original Flask API structure"""
    global data_source
    
    # Initialize data source if not already done (for testing)
    if not data_source:
        try:
            import time
            import numpy as np
            from datetime import datetime
            
            class SimpleSimulator:
                def __init__(self):
                    self.last_update = 0
                    self.update_interval = 0.1
                    self.fcv_actual_states = np.array([False, True, False, False, True, False, True])
                    self.fcv_expected_states = np.array([False, True, False, False, True, False, True])
                    self.rng = np.random.default_rng()
                
                def read_data(self):
                    current_time = time.time()
                    if current_time - self.last_update >= self.update_interval:
                        self.last_update = current_time
                        
                        # Generate PT data (5 sensors)
                        pt_data = []
                        for i in range(5):
                            rand = self.rng.random()
                            if rand < 0.02:  # Danger level
                                value = self.rng.uniform(320, 380)
                            elif rand < 0.05:  # Warning level
                                value = self.rng.uniform(200, 240)
                            else:  # Normal range
                                value = self.rng.uniform(10, 200)
                            pt_data.append(round(value, 1))
                        
                        # Generate TC data (3 sensors)
                        tc_data = [round(self.rng.uniform(20, 100), 1) for _ in range(3)]
                        
                        # Generate LC data (3 sensors)
                        lc_data = [round(self.rng.uniform(50, 300), 1) for _ in range(3)]
                        
                        # Occasionally change valve states
                        if self.rng.random() < 0.20:
                            valve_to_toggle = self.rng.integers(0, len(self.fcv_actual_states))
                            self.fcv_actual_states[valve_to_toggle] = not self.fcv_actual_states[valve_to_toggle]
                        
                        return {
                            'pt': pt_data,
                            'tc': tc_data,
                            'lc': lc_data,
                            'fcv_actual': self.fcv_actual_states.tolist(),
                            'fcv_expected': self.fcv_expected_states.tolist(),
                            'timestamp': datetime.now().isoformat()
                        }
                    return None
                
                async def stop(self):
                    """Dummy stop method for compatibility"""
                    pass
            
            data_source = SimpleSimulator()
            print("⚡ Simulator initialized for API call")
        except Exception:
            pass
    
    try:
        # Get data from simple simulator (matches Flask format)
        reading = data_source.read_data()
        if not reading:
            return JSONResponse({'value': None})
        
        # Data is already in Flask format from simple simulator
        data_dict = reading
        
        if sensor_type != 'all':
            return JSONResponse({
                'value': {sensor_type: data_dict.get(sensor_type, 'KEY_NOT_FOUND')},
                'timestamp': data_dict['timestamp']
            })
        else:
            return JSONResponse({
                'value': data_dict,
                'timestamp': data_dict['timestamp']
            })
            
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)

@app.get("/health")
async def health_check():
    """System health check"""
    global data_source_type
    return {
        "status": "ok",
        "system": "BLAST - Big Launch Analysis & Stats Terminal",
        "data_source": data_source_type,
        "data_source_running": data_source is not None,
        "serial_port": settings.serial_port if settings else "unknown"
    }

if __name__ == "__main__":
    import uvicorn
    print("🌟 Starting BLAST Server (Original Design)")
    print("📍 http://127.0.0.1:8000")
    print("🎯 Three sensor groups available!")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")