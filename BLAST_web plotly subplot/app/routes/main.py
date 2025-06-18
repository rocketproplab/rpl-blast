from flask import Blueprint, render_template, jsonify, request
from app.config import Config
from app.data_sources.simulator import Simulator
from app.data_sources.serial_reader import SerialReader
import time
import os
from functools import lru_cache

main_bp = Blueprint('main', __name__)
config = Config()  # Create instance

# Initialize data source based on configuration
if not hasattr(main_bp, 'data_source'):
    if config.DATA_SOURCE == 'simulator':
        main_bp.data_source = Simulator()
    else:
        main_bp.data_source = SerialReader(config.SERIAL_PORT, config.SERIAL_BAUDRATE)
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        main_bp.data_source.initialize()

# Remove the cache decorator
def get_cached_sensor_data():
    return main_bp.data_source.read_data()

@main_bp.route('/')
def index():
    """Landing page with links to each sensor type"""
    return render_template('index.html', config=config)

@main_bp.route('/thermocouples')
def thermocouples():
    """Thermocouple monitoring page"""
    return render_template('thermocouples.html', config=config)

@main_bp.route('/pressure')
def pressure():
    """Pressure transducer monitoring page"""
    return render_template('pressure.html', config=config)

@main_bp.route('/valves')
def valves():
    """Flow control valve monitoring page"""
    return render_template('valves.html', config=config)

@main_bp.route('/data')
def get_data():
    sensor_type = request.args.get('type', 'all')
    sensor_data = main_bp.data_source.read_data()
    
    # print(f"--- DEBUG: routes.py /data: sensor_data object is: {sensor_data}, type: {type(sensor_data)} ---")
    if sensor_data:
    #     print(f"--- DEBUG: routes.py /data: sensor_data object dir(): {dir(sensor_data)} ---")
    #     if hasattr(sensor_data, 'fcv_actual'):
    #         print(f"--- DEBUG: sensor_data HAS fcv_actual: {getattr(sensor_data, 'fcv_actual')} ---")
    #     else:
    #         print(f"--- DEBUG: sensor_data DOES NOT HAVE fcv_actual ---")
    #     if hasattr(sensor_data, 'fcv_expected'):
    #         print(f"--- DEBUG: sensor_data HAS fcv_expected: {getattr(sensor_data, 'fcv_expected')} ---")
    #     else:
    #         print(f"--- DEBUG: sensor_data DOES NOT HAVE fcv_expected ---")
    #     if hasattr(sensor_data, 'fcv'): # Check for the old attribute
    #         print(f"--- DEBUG: sensor_data HAS OLD fcv: {getattr(sensor_data, 'fcv')} ---")
    #     else:
    #         print(f"--- DEBUG: sensor_data DOES NOT HAVE OLD fcv ---")
            
        data_dict = sensor_data.to_dict()
        # print(f"--- DEBUG: routes.py /data: data_dict from to_dict(): {data_dict} ---") # Optional: log the dict

        if sensor_type != 'all':
            return jsonify({
                'value': {sensor_type: data_dict.get(sensor_type, 'KEY_NOT_FOUND')}, # Added .get for safety
                'timestamp': data_dict['timestamp']
            })
        return jsonify({
            'value': data_dict,
            'timestamp': data_dict['timestamp']
        })
    
    print("!!! routes.py /data is returning {'value': None} because sensor_data was Falsy !!!")
    return jsonify({'value': None})

@main_bp.route('/toggle_valve', methods=['POST'])
def toggle_valve():
    if isinstance(main_bp.data_source, SerialReader):
        try:
            data = request.get_json()
            valve = data.get('valve', 0)
            success = main_bp.data_source.toggle_valve(valve)
            return jsonify({'success': success})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    return jsonify({'success': False, 'error': 'Not using serial connection'}) 
        