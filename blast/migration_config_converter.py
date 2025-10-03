#!/usr/bin/env python3
"""
Migration script to convert Flask config to FastAPI config format
"""
import yaml
from pathlib import Path


def convert_flask_config_to_fastapi():
    """Convert the original Flask config to FastAPI format"""
    
    # Read the original Flask config
    flask_config_path = Path("../BLAST_web plotly subplot/app/config.yaml")
    
    if not flask_config_path.exists():
        print(f"Flask config not found at {flask_config_path}")
        return
    
    with open(flask_config_path, 'r') as f:
        flask_config = yaml.safe_load(f)
    
    # Convert to FastAPI format
    fastapi_config = {
        'data_source': flask_config['data_source'],
        'serial_port': flask_config['serial_port'],
        'serial_baudrate': flask_config['serial_baudrate'],
        
        # Convert pressure transducers
        'pressure_transducers': [],
        'thermocouples': [],
        'load_cells': [],
        'flow_control_valves': [],
        
        # Calibration settings
        'calibration': {
            'auto_zero_enabled': True,
            'drift_monitoring': True,
            'calibration_interval_hours': 24,
            'drift_threshold_percent': 2.0,
            'measurement_duration_ms': 5000,
            'noise_threshold': 0.1
        },
        
        # Performance settings
        'telemetry_interval_ms': 100,
        'max_websocket_connections': 50,
        'heartbeat_interval_ms': 30000,
        
        # Logging
        'log_level': 'INFO',
        'log_retention_days': 30,
        'log_max_size_mb': 100,
        
        # Application
        'debug': False,
        'host': '127.0.0.1',
        'port': 5000
    }
    
    # Convert pressure transducers
    for pt in flask_config['subpage1']['pressure_transducers']:
        fastapi_config['pressure_transducers'].append({
            'name': pt['name'],
            'id': pt['id'],
            'color': pt['color'],
            'min_value': pt['min_value'],
            'max_value': pt['max_value'],
            'warning_threshold': pt['warning_value'],
            'danger_threshold': pt['danger_value'],
            'unit': 'psi',
            'calibration_enabled': True,
            'temperature_compensation': False
        })
    
    # Convert thermocouples
    for tc in flask_config['subpage2']['thermocouples']:
        fastapi_config['thermocouples'].append({
            'name': tc['name'],
            'id': tc['id'],
            'color': tc['color'],
            'min_value': tc['min_value'],
            'max_value': tc['max_value'],
            'warning_threshold': tc['warning_value'],
            'danger_threshold': tc['danger_value'],
            'unit': 'celsius',
            'calibration_enabled': True,
            'temperature_compensation': False
        })
    
    # Convert load cells
    for lc in flask_config['subpage2']['load_cells']:
        fastapi_config['load_cells'].append({
            'name': lc['name'],
            'id': lc['id'],
            'color': lc['color'],
            'min_value': lc['min_value'],
            'max_value': lc['max_value'],
            'warning_threshold': lc['warning_value'],
            'danger_threshold': lc['danger_value'],
            'unit': 'lbs',
            'calibration_enabled': True,
            'temperature_compensation': True
        })
    
    # Convert flow control valves
    for fv in flask_config['subpage3']['flow_control_valves']:
        fastapi_config['flow_control_valves'].append({
            'name': fv['name'],
            'id': fv['id'],
            'type': 'binary'
        })
    
    # Write the converted config
    output_path = Path("app/config/config.yaml")
    with open(output_path, 'w') as f:
        yaml.dump(fastapi_config, f, default_flow_style=False, indent=2)
    
    print(f"✅ Converted Flask config to FastAPI format")
    print(f"📁 Output: {output_path}")
    print(f"📊 Converted: {len(fastapi_config['pressure_transducers'])} PT, {len(fastapi_config['thermocouples'])} TC, {len(fastapi_config['load_cells'])} LC, {len(fastapi_config['flow_control_valves'])} FCV")


if __name__ == "__main__":
    convert_flask_config_to_fastapi()