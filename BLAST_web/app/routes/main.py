from flask import Blueprint, render_template, jsonify, request
from app.config import Config
from app.data_sources.simulator import Simulator
from app.data_sources.serial_reader import SerialReader
import time

main_bp = Blueprint('main', __name__)

# Initialize data source based on configuration
if not hasattr(main_bp, 'data_source'):
    if Config.DATA_SOURCE == 'simulator':
        main_bp.data_source = Simulator()
    elif Config.DATA_SOURCE == 'serial':
        main_bp.data_source = SerialReader()
    else:
        raise ValueError(f"Invalid DATA_SOURCE in config: {Config.DATA_SOURCE}")
    
    main_bp.data_source.initialize()

@main_bp.route('/')
def index():
    return render_template('dashboard.html', config=Config)

@main_bp.route('/data')
def get_data():
    sensor_data = main_bp.data_source.read_data()
    if sensor_data:
        return jsonify({'value': sensor_data.to_dict()})
    return jsonify({'value': None})

@main_bp.route('/toggle_led', methods=['POST'])
def toggle_led():
    if isinstance(main_bp.data_source, SerialReader):
        try:
            data = request.get_json()
            valve = data.get('valve', 0)
            success = main_bp.data_source.toggle_led(valve)
            return jsonify({'success': success})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    return jsonify({'success': False, 'error': 'Not using serial connection'}) 
        