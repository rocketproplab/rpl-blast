"""
EventLogger: Log system events with structured data
Tracks sensor thresholds, valve operations, connection events
"""

import json
from enum import Enum
from datetime import datetime
from typing import Dict, Optional, Any
import time


class EventType(Enum):
    """Types of events that can be logged"""
    # Connection Events
    SERIAL_CONNECT = "serial_connect"
    SERIAL_DISCONNECT = "serial_disconnect"
    SERIAL_ERROR = "serial_error"
    SERIAL_RECONNECT = "serial_reconnect"
    
    # Sensor Events
    THRESHOLD_WARNING = "threshold_warning"
    THRESHOLD_DANGER = "threshold_danger"
    THRESHOLD_CRITICAL = "threshold_critical"
    SENSOR_NORMAL = "sensor_normal"  # Return to normal
    SENSOR_FAILURE = "sensor_failure"
    
    # Valve Events
    VALVE_OPEN = "valve_open"
    VALVE_CLOSE = "valve_close"
    VALVE_ERROR = "valve_error"
    VALVE_COMMAND = "valve_command"
    
    # System Events
    MODE_CHANGE = "mode_change"
    CONFIG_RELOAD = "config_reload"
    FREEZE_DETECTED = "freeze_detected"
    FREEZE_RECOVERED = "freeze_recovered"
    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    
    # Client Events
    CLIENT_CONNECT = "client_connect"
    CLIENT_DISCONNECT = "client_disconnect"
    CLIENT_THROTTLED = "client_throttled"
    CLIENT_RECOVERED = "client_recovered"


class EventLogger:
    """Log structured events for analysis and monitoring"""
    
    def __init__(self):
        """Initialize event logger"""
        # Get logger
        from app.logging.logger_manager import get_logger_manager
        self.logger = get_logger_manager().get_logger('events')
        self.error_logger = get_logger_manager().get_logger('errors')
        
        # Track sensor states for change detection
        self.sensor_states: Dict[str, str] = {}  # sensor_id -> state (normal/warning/danger)
        self.valve_states: Dict[str, bool] = {}  # valve_id -> open/closed
        
        self.logger.info("EventLogger initialized")
    
    def log_event(self, event_type: EventType, details: Dict[str, Any], 
                  severity: str = "INFO", context: Optional[Dict] = None):
        """Log a structured event
        
        Args:
            event_type: Type of event from EventType enum
            details: Event-specific details
            severity: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            context: Additional context (request_id, user, etc)
        """
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type.value,
            'severity': severity,
            'details': details
        }
        
        if context:
            event['context'] = context
        
        # Log at appropriate level
        log_message = json.dumps(event)
        
        if severity == "CRITICAL":
            self.error_logger.critical(log_message)
        elif severity == "ERROR":
            self.error_logger.error(log_message)
        elif severity == "WARNING":
            self.logger.warning(log_message)
        elif severity == "DEBUG":
            self.logger.debug(log_message)
        else:
            self.logger.info(log_message)
    
    def log_sensor_threshold(self, sensor_id: str, sensor_name: str, 
                           value: float, threshold: float, 
                           threshold_type: str, unit: str = ""):
        """Log sensor threshold violation
        
        Args:
            sensor_id: Unique sensor identifier (pt1, tc2, etc)
            sensor_name: Human-readable sensor name
            value: Current sensor value
            threshold: Threshold that was exceeded
            threshold_type: Type of threshold (warning/danger/critical)
            unit: Unit of measurement
        """
        # Determine event type and severity
        if threshold_type == "danger" or threshold_type == "critical":
            event_type = EventType.THRESHOLD_DANGER
            severity = "ERROR" if threshold_type == "critical" else "WARNING"
        elif threshold_type == "warning":
            event_type = EventType.THRESHOLD_WARNING
            severity = "WARNING"
        else:
            event_type = EventType.SENSOR_NORMAL
            severity = "INFO"
        
        # Check if this is a state change
        previous_state = self.sensor_states.get(sensor_id, "normal")
        current_state = threshold_type if threshold_type != "normal" else "normal"
        
        # Only log if state changed or it's critical
        if current_state != previous_state or threshold_type == "critical":
            self.sensor_states[sensor_id] = current_state
            
            details = {
                'sensor_id': sensor_id,
                'sensor_name': sensor_name,
                'value': round(value, 2),
                'threshold': threshold,
                'threshold_type': threshold_type,
                'unit': unit,
                'state_change': f"{previous_state} -> {current_state}"
            }
            
            self.log_event(event_type, details, severity)
            
            # Also log to console for critical events
            if threshold_type == "critical":
                print(f"CRITICAL: {sensor_name} at {value}{unit} exceeds critical threshold {threshold}{unit}")
    
    def log_valve_operation(self, valve_id: str, valve_name: str, 
                          new_state: bool, command_source: str = "system",
                          success: bool = True):
        """Log valve operation
        
        Args:
            valve_id: Unique valve identifier
            valve_name: Human-readable valve name
            new_state: True for open, False for closed
            command_source: Who initiated (system/user/auto)
            success: Whether operation succeeded
        """
        previous_state = self.valve_states.get(valve_id)
        
        event_type = EventType.VALVE_OPEN if new_state else EventType.VALVE_CLOSE
        if not success:
            event_type = EventType.VALVE_ERROR
        
        details = {
            'valve_id': valve_id,
            'valve_name': valve_name,
            'new_state': 'open' if new_state else 'closed',
            'previous_state': 'open' if previous_state else 'closed' if previous_state is not None else 'unknown',
            'command_source': command_source,
            'success': success
        }
        
        severity = "ERROR" if not success else "INFO"
        self.log_event(event_type, details, severity)
        
        if success:
            self.valve_states[valve_id] = new_state
    
    def log_connection_event(self, event_type: str, details: Dict):
        """Log connection-related events
        
        Args:
            event_type: Type of connection event
            details: Event details (port, error, etc)
        """
        # Map string to EventType
        event_map = {
            'connect': EventType.SERIAL_CONNECT,
            'disconnect': EventType.SERIAL_DISCONNECT,
            'error': EventType.SERIAL_ERROR,
            'reconnect': EventType.SERIAL_RECONNECT
        }
        
        event = event_map.get(event_type, EventType.SERIAL_ERROR)
        severity = "ERROR" if event_type == "error" else "INFO"
        
        self.log_event(event, details, severity)
    
    def log_mode_change(self, from_mode: str, to_mode: str, reason: str = ""):
        """Log mode change (serial/simulator)
        
        Args:
            from_mode: Previous mode
            to_mode: New mode
            reason: Reason for change
        """
        details = {
            'from_mode': from_mode,
            'to_mode': to_mode,
            'reason': reason,
            'timestamp': time.time()
        }
        
        self.log_event(EventType.MODE_CHANGE, details, "INFO")
    
    def log_client_event(self, client_id: str, event_type: str, details: Optional[Dict] = None):
        """Log client/browser events
        
        Args:
            client_id: Unique client identifier
            event_type: Type of client event
            details: Additional details
        """
        event_map = {
            'connect': EventType.CLIENT_CONNECT,
            'disconnect': EventType.CLIENT_DISCONNECT,
            'throttled': EventType.CLIENT_THROTTLED,
            'recovered': EventType.CLIENT_RECOVERED
        }
        
        event = event_map.get(event_type, EventType.CLIENT_DISCONNECT)
        
        event_details = {
            'client_id': client_id,
            'event': event_type
        }
        
        if details:
            event_details.update(details)
        
        severity = "WARNING" if event_type == "throttled" else "INFO"
        self.log_event(event, event_details, severity)
    
    def check_sensor_thresholds(self, sensor_data, config):
        """Check all sensors against configured thresholds
        
        Args:
            sensor_data: SensorData object with current readings
            config: Config object with threshold definitions
        """
        # Check pressure transducers
        for i, value in enumerate(sensor_data.pt):
            if i < len(config.PRESSURE_TRANSDUCERS):
                pt = config.PRESSURE_TRANSDUCERS[i]
                self._check_threshold(
                    pt['id'], pt['name'], value, 
                    pt.get('warning_value', float('inf')),
                    pt.get('danger_value', float('inf')),
                    "PSI"
                )
        
        # Check thermocouples
        for i, value in enumerate(sensor_data.tc):
            if i < len(config.THERMOCOUPLES):
                tc = config.THERMOCOUPLES[i]
                self._check_threshold(
                    tc['id'], tc['name'], value,
                    tc.get('warning_value', float('inf')),
                    tc.get('danger_value', float('inf')),
                    "°C"
                )
        
        # Check load cells
        for i, value in enumerate(sensor_data.lc):
            if i < len(config.LOAD_CELLS):
                lc = config.LOAD_CELLS[i]
                self._check_threshold(
                    lc['id'], lc['name'], value,
                    lc.get('warning_value', float('inf')),
                    lc.get('danger_value', float('inf')),
                    "lbs"
                )
    
    def _check_threshold(self, sensor_id: str, sensor_name: str, value: float,
                        warning_threshold: float, danger_threshold: float, unit: str):
        """Check a single sensor against thresholds"""
        if value >= danger_threshold:
            self.log_sensor_threshold(
                sensor_id, sensor_name, value, 
                danger_threshold, "danger", unit
            )
        elif value >= warning_threshold:
            self.log_sensor_threshold(
                sensor_id, sensor_name, value,
                warning_threshold, "warning", unit
            )
        else:
            # Check if returning to normal from warning/danger
            if sensor_id in self.sensor_states and self.sensor_states[sensor_id] != "normal":
                self.log_sensor_threshold(
                    sensor_id, sensor_name, value,
                    warning_threshold, "normal", unit
                )
    
    def log_browser_event(self, event: str, data: Dict[str, Any]):
        """Log browser-related events (throttling, visibility, performance)
        
        Args:
            event: Event type (throttled, suspended, resumed, etc)
            data: Event data from browser
        """
        # Map to appropriate EventType
        if event in ['throttled', 'frame_drops', 'main_thread_blocked']:
            event_type = EventType.CLIENT_THROTTLED
            severity = "WARNING"
        elif event == 'resumed' or event == 'throttle_recovered':
            event_type = EventType.CLIENT_RECOVERED
            severity = "INFO"
        elif event in ['suspended', 'page_hidden']:
            event_type = EventType.CLIENT_DISCONNECT
            severity = "INFO"
        elif event in ['initialized', 'page_visible']:
            event_type = EventType.CLIENT_CONNECT
            severity = "INFO"
        else:
            # Generic client event
            event_type = EventType.CLIENT_CONNECT
            severity = "INFO"
        
        details = {
            'browser_event': event,
            'timestamp': data.get('timestamp', time.time()),
            'visible': data.get('visible'),
            'throttled': data.get('throttled')
        }
        
        # Add event-specific details
        if event == 'throttled':
            details['gap_ms'] = data.get('gap_ms', 0)
            details['visibility'] = data.get('visibility')
        elif event == 'frame_drops':
            details['count'] = data.get('count', 0)
            details['duration_ms'] = data.get('duration_ms', 0)
        elif event == 'main_thread_blocked':
            details['delay_ms'] = data.get('delay_ms', 0)
        elif event == 'high_memory':
            if 'memory' in data:
                details['memory_used'] = data['memory']['used']
                details['memory_limit'] = data['memory']['limit']
                details['memory_usage_pct'] = (data['memory']['used'] / data['memory']['limit'] * 100)
        
        self.log_event(event_type, details, severity)


# Global instance
_event_logger = None

def get_event_logger() -> EventLogger:
    """Get the global event logger instance"""
    global _event_logger
    if _event_logger is None:
        _event_logger = EventLogger()
    return _event_logger