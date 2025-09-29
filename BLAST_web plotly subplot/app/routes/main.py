from flask import Blueprint, render_template, jsonify, request
from app.config import Config
from app.data_sources.simulator import Simulator
from app.data_sources.serial_reader import SerialReader
import time
import os
import uuid
from functools import lru_cache

main_bp = Blueprint('main', __name__)
config = Config()  # Create instance

# Initialize logging
try:
    from app.logging.logger_manager import get_logger_manager
    from app.logging.performance_monitor import get_performance_monitor, measure_time
    from app.logging.freeze_detector import get_freeze_detector
    
    logger = get_logger_manager().get_logger('app')
    perf_monitor = get_performance_monitor()
    freeze_detector = get_freeze_detector()
    
    # Track concurrent requests
    concurrent_requests = 0
    
except ImportError:
    # Logging not available yet during initial import
    logger = None
    perf_monitor = None
    freeze_detector = None
    concurrent_requests = 0

# Initialize data source based on configuration
if not hasattr(main_bp, 'data_source'):
    if config.DATA_SOURCE == 'simulator':
        main_bp.data_source = Simulator()
        if logger:
            logger.info("Using simulator data source")
    else:
        main_bp.data_source = SerialReader(config.SERIAL_PORT, config.SERIAL_BAUDRATE)
        if logger:
            logger.info(f"Using serial data source on {config.SERIAL_PORT}")
    # Initialize data source (always, not just in debug mode)
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
    global concurrent_requests
    
    # Generate request ID for tracking
    request_id = str(uuid.uuid4())[:8]
    
    # Track concurrent requests
    concurrent_requests += 1
    
    # Log request start with timing
    start_time = time.perf_counter()
    if logger:
        logger.debug(f"Request {request_id} started (concurrent: {concurrent_requests})")
    
    try:
        # Heartbeat for freeze detection
        if freeze_detector:
            freeze_detector.heartbeat()
            freeze_detector.log_operation('web_request', {'endpoint': '/data', 'request_id': request_id})
        
        sensor_type = request.args.get('type', 'all')
        
        # Time the data read operation
        if perf_monitor:
            with perf_monitor.measure('data_source_read'):
                sensor_data = main_bp.data_source.read_data()
        else:
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
                response = jsonify({
                    'value': {sensor_type: data_dict.get(sensor_type, 'KEY_NOT_FOUND')}, # Added .get for safety
                    'timestamp': data_dict['timestamp']
                })
            else:
                response = jsonify({
                    'value': data_dict,
                    'timestamp': data_dict['timestamp']
                })
            
            # Log successful response
            duration_ms = (time.perf_counter() - start_time) * 1000
            if logger:
                if duration_ms > 500:
                    logger.warning(f"Slow request {request_id}: {duration_ms:.1f}ms")
                else:
                    logger.debug(f"Request {request_id} completed: {duration_ms:.1f}ms")
            
            if perf_monitor:
                perf_monitor.record_metric('request_duration', duration_ms, 'ms')
                perf_monitor.record_metric('concurrent_requests', concurrent_requests, 'requests')
            
            return response
        
        # No data available
        if logger:
            logger.warning(f"Request {request_id}: No sensor data available")
        return jsonify({'value': None})
        
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        if logger:
            logger.error(f"Request {request_id} failed after {duration_ms:.1f}ms: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
        
    finally:
        concurrent_requests -= 1

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

@main_bp.route('/api/browser_heartbeat', methods=['POST'])
def browser_heartbeat():
    """Handle browser heartbeat to detect client-side issues"""
    try:
        data = request.get_json()
        
        # Log heartbeat with performance monitor
        if perf_monitor:
            perf_monitor.record_metric('browser_heartbeat', 1, 'count')
            
            # Check for throttling
            if data.get('throttled'):
                perf_monitor.record_metric('browser_throttled', 1, 'count')
                if logger:
                    logger.warning(f"Browser throttling detected: {data.get('missed_heartbeats')} missed heartbeats")
        
        # Update freeze detector with browser status
        if freeze_detector:
            freeze_detector.log_operation('browser_heartbeat', {
                'visible': data.get('visible'),
                'throttled': data.get('throttled')
            })
        
        return jsonify({'status': 'ok', 'server_time': time.time()})
    except Exception as e:
        if logger:
            logger.error(f"Browser heartbeat error: {e}")
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/browser_status', methods=['POST'])
def browser_status():
    """Handle browser status updates (visibility changes, performance issues)"""
    try:
        data = request.get_json()
        event = data.get('event')
        
        # Log the event
        if logger:
            if event in ['throttled', 'frame_drops', 'main_thread_blocked', 'high_memory']:
                logger.warning(f"Browser issue: {event} - {data}")
            else:
                logger.info(f"Browser event: {event}")
        
        # Log with event logger if available
        try:
            from app.logging.event_logger import get_event_logger
            event_logger = get_event_logger()
            event_logger.log_browser_event(event, data)
        except:
            pass
        
        # Track metrics
        if perf_monitor:
            if event == 'throttled':
                perf_monitor.record_metric('browser_throttle_events', 1, 'count')
                perf_monitor.record_metric('browser_throttle_gap', data.get('gap_ms', 0), 'ms')
            elif event == 'frame_drops':
                perf_monitor.record_metric('browser_frame_drops', data.get('count', 0), 'count')
            elif event == 'main_thread_blocked':
                perf_monitor.record_metric('browser_main_thread_blocked', data.get('delay_ms', 0), 'ms')
            elif event == 'high_memory':
                if 'memory' in data:
                    memory_usage = data['memory']['used'] / data['memory']['limit'] * 100
                    perf_monitor.record_metric('browser_memory_usage', memory_usage, '%')
        
        # Handle specific events
        if event == 'suspended':
            # Browser tab was suspended
            if logger:
                logger.info("Browser tab suspended - client may miss updates")
        elif event == 'resumed':
            # Browser tab resumed
            if logger:
                logger.info("Browser tab resumed - client requesting refresh")
        
        return jsonify({'status': 'ok', 'received': event})
    except Exception as e:
        if logger:
            logger.error(f"Browser status error: {e}")
        return jsonify({'error': str(e)}), 500 
        