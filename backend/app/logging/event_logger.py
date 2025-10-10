"""
BLAST Event Logger - Application lifecycle and state change logging
"""

import logging
import time
from typing import Dict, Any, Optional
from enum import Enum


class EventType(Enum):
    """Standard event types for BLAST system"""
    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    DATA_SOURCE_CHANGE = "data_source_change"
    CALIBRATION_UPDATE = "calibration_update"
    ERROR_RECOVERY = "error_recovery"
    USER_ACTION = "user_action"
    SYSTEM_STATE = "system_state"
    SENSOR_ALERT = "sensor_alert"
    CONNECTION_STATE = "connection_state"
    PERFORMANCE_ALERT = "performance_alert"


class EventLogger:
    """Handles application lifecycle and state change events"""
    
    def __init__(self, logger_manager):
        self.logger_manager = logger_manager
        self.logger = logging.getLogger('blast.events')
        self.session_id = int(time.time())
        
        # Track event counts by type
        self.event_counts = {event_type.value: 0 for event_type in EventType}
        
        self.log_startup()
    
    def log_startup(self):
        """Log application startup"""
        self._log_event(
            EventType.STARTUP,
            "BLAST FastAPI application started",
            {
                'session_id': self.session_id,
                'version': 'FastAPI Migration',
                'startup_time': time.time()
            }
        )
    
    def log_shutdown(self):
        """Log application shutdown"""
        uptime = time.time() - self.session_id
        self._log_event(
            EventType.SHUTDOWN,
            "BLAST FastAPI application shutdown",
            {
                'session_id': self.session_id,
                'uptime_seconds': uptime,
                'uptime_formatted': f"{uptime/3600:.1f}h",
                'event_summary': dict(self.event_counts)
            }
        )
    
    def log_data_source_change(self, old_source: str, new_source: str, reason: str = ""):
        """Log data source changes (serial <-> simulator)"""
        self._log_event(
            EventType.DATA_SOURCE_CHANGE,
            f"Data source changed from {old_source} to {new_source}",
            {
                'old_source': old_source,
                'new_source': new_source,
                'reason': reason
            }
        )
    
    def log_calibration_update(self, sensor_id: str, old_offset: float, new_offset: float, user_action: bool = True):
        """Log calibration offset changes"""
        self._log_event(
            EventType.CALIBRATION_UPDATE,
            f"Calibration updated for {sensor_id}",
            {
                'sensor_id': sensor_id,
                'old_offset': old_offset,
                'new_offset': new_offset,
                'delta': new_offset - old_offset,
                'user_action': user_action
            }
        )
    
    def log_sensor_alert(self, sensor_id: str, alert_type: str, value: float, threshold: float):
        """Log sensor threshold alerts (warning/danger)"""
        self._log_event(
            EventType.SENSOR_ALERT,
            f"Sensor alert: {sensor_id} {alert_type}",
            {
                'sensor_id': sensor_id,
                'alert_type': alert_type,  # 'warning' or 'danger'
                'current_value': value,
                'threshold': threshold,
                'severity': 'high' if alert_type == 'danger' else 'medium'
            }
        )
    
    def log_connection_state(self, connection_type: str, state: str, details: Dict = None):
        """Log connection state changes (serial, websocket, etc.)"""
        self._log_event(
            EventType.CONNECTION_STATE,
            f"{connection_type} connection {state}",
            {
                'connection_type': connection_type,
                'state': state,  # 'connected', 'disconnected', 'error'
                'details': details or {}
            }
        )
    
    def log_user_action(self, action: str, user_id: str = "unknown", data: Dict = None):
        """Log user interactions"""
        self._log_event(
            EventType.USER_ACTION,
            f"User action: {action}",
            {
                'action': action,
                'user_id': user_id,
                'data': data or {}
            }
        )
    
    def log_system_state(self, state: str, healthy: bool, metrics: Dict = None):
        """Log system health and state changes"""
        self._log_event(
            EventType.SYSTEM_STATE,
            f"System state: {state}",
            {
                'state': state,
                'healthy': healthy,
                'metrics': metrics or {}
            }
        )
    
    def log_error_recovery(self, error_type: str, recovery_action: str, success: bool):
        """Log error recovery attempts"""
        self._log_event(
            EventType.ERROR_RECOVERY,
            f"Error recovery: {error_type}",
            {
                'error_type': error_type,
                'recovery_action': recovery_action,
                'success': success
            }
        )
    
    def log_performance_alert(self, metric: str, value: float, threshold: float, severity: str):
        """Log performance-related alerts"""
        self._log_event(
            EventType.PERFORMANCE_ALERT,
            f"Performance alert: {metric}",
            {
                'metric': metric,
                'current_value': value,
                'threshold': threshold,
                'severity': severity
            }
        )
    
    def _log_event(self, event_type: EventType, message: str, data: Dict[str, Any]):
        """Internal method to log events"""
        self.event_counts[event_type.value] += 1
        
        # Add session tracking
        data['session_id'] = self.session_id
        data['event_sequence'] = self.event_counts[event_type.value]
        
        # Log to manager
        self.logger_manager.log_event(event_type.value, message, data)
        
        # Also log to Python logger for console/file output
        level = self._get_log_level(event_type)
        self.logger.log(level, f"[{event_type.value.upper()}] {message}")
    
    def _get_log_level(self, event_type: EventType) -> int:
        """Map event types to Python logging levels"""
        critical_events = [EventType.SHUTDOWN, EventType.SENSOR_ALERT, EventType.ERROR_RECOVERY]
        warning_events = [EventType.DATA_SOURCE_CHANGE, EventType.CONNECTION_STATE, EventType.PERFORMANCE_ALERT]
        
        if event_type in critical_events:
            return logging.WARNING
        elif event_type in warning_events:
            return logging.INFO
        else:
            return logging.DEBUG
    
    def get_event_summary(self) -> Dict[str, Any]:
        """Get summary of events logged in this session"""
        return {
            'session_id': self.session_id,
            'session_duration': time.time() - self.session_id,
            'event_counts': dict(self.event_counts),
            'total_events': sum(self.event_counts.values())
        }