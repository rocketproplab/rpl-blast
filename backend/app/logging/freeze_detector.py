"""
BLAST Freeze Detector - Detects system freezes and unresponsive states
"""

import logging
import time
import threading
import asyncio
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from collections import deque


@dataclass
class WatchdogTimer:
    """Individual watchdog timer for monitoring specific components"""
    name: str
    timeout_seconds: float
    last_heartbeat: float
    callback: Optional[Callable] = None
    active: bool = True


class FreezeDetector:
    """Detects system freezes and unresponsive components"""
    
    def __init__(self, logger_manager):
        self.logger_manager = logger_manager
        self.logger = logging.getLogger('blast.freeze_detector')
        
        # Watchdog timers for different components
        self.watchdogs: Dict[str, WatchdogTimer] = {}
        
        # Detection history
        self.freeze_events = deque(maxlen=50)
        self.heartbeat_history = deque(maxlen=1000)
        
        # Statistics
        self.stats = {
            'freezes_detected': 0,
            'false_positives': 0,
            'total_heartbeats': 0,
            'missed_heartbeats': 0,
            'monitoring_start': time.time()
        }
        
        # Monitoring state
        self._monitoring = False
        self._monitor_thread = None
        self._freeze_callbacks = []
        
        # System responsiveness tracking
        self.last_system_heartbeat = time.time()
        self.system_response_times = deque(maxlen=100)
        
        # Setup default watchdogs
        self._setup_default_watchdogs()
        
        # Start monitoring
        self.start_monitoring()
    
    def _setup_default_watchdogs(self):
        """Setup default watchdog timers for critical components"""
        
        # Data acquisition watchdog - should heartbeat every few seconds
        self.register_watchdog(
            'data_acquisition',
            timeout_seconds=10.0,
            callback=self._handle_data_acquisition_freeze
        )
        
        # API response watchdog - should heartbeat on every request
        self.register_watchdog(
            'api_requests',
            timeout_seconds=30.0,
            callback=self._handle_api_freeze
        )
        
        # Serial communication watchdog
        self.register_watchdog(
            'serial_communication',
            timeout_seconds=15.0,
            callback=self._handle_serial_freeze
        )
        
        # Overall system watchdog
        self.register_watchdog(
            'system_health',
            timeout_seconds=60.0,
            callback=self._handle_system_freeze
        )
    
    def register_watchdog(self, name: str, timeout_seconds: float, callback: Optional[Callable] = None):
        """Register a new watchdog timer"""
        self.watchdogs[name] = WatchdogTimer(
            name=name,
            timeout_seconds=timeout_seconds,
            last_heartbeat=time.time(),
            callback=callback,
            active=True
        )
        
        self.logger.info(f"Registered watchdog '{name}' with {timeout_seconds}s timeout")
    
    def heartbeat(self, component: str):
        """Send heartbeat for a component"""
        if component in self.watchdogs:
            self.watchdogs[component].last_heartbeat = time.time()
            self.stats['total_heartbeats'] += 1
            
            # Record heartbeat
            self.heartbeat_history.append({
                'timestamp': time.time(),
                'component': component
            })
            
            # Update system heartbeat
            if component == 'system_health':
                self.last_system_heartbeat = time.time()
    
    def start_monitoring(self):
        """Start freeze detection monitoring"""
        if not self._monitoring:
            self._monitoring = True
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()
            self.logger.info("Freeze detection monitoring started")
    
    def stop_monitoring(self):
        """Stop freeze detection monitoring"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        self.logger.info("Freeze detection monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop to check for freezes"""
        while self._monitoring:
            try:
                self._check_all_watchdogs()
                time.sleep(5)  # Check every 5 seconds
            except Exception as e:
                self.logger.error(f"Error in freeze detection monitoring: {e}")
                time.sleep(10)  # Wait longer on error
    
    def _check_all_watchdogs(self):
        """Check all watchdog timers for timeouts"""
        current_time = time.time()
        
        for name, watchdog in self.watchdogs.items():
            if not watchdog.active:
                continue
                
            time_since_heartbeat = current_time - watchdog.last_heartbeat
            
            if time_since_heartbeat > watchdog.timeout_seconds:
                self._handle_freeze_detected(name, time_since_heartbeat, watchdog)
    
    def _handle_freeze_detected(self, component: str, freeze_duration: float, watchdog: WatchdogTimer):
        """Handle detected freeze"""
        self.stats['freezes_detected'] += 1
        self.stats['missed_heartbeats'] += 1
        
        freeze_event = {
            'timestamp': time.time(),
            'component': component,
            'freeze_duration': freeze_duration,
            'timeout_threshold': watchdog.timeout_seconds
        }
        
        self.freeze_events.append(freeze_event)
        
        # Log freeze detection
        self.logger.warning(f"FREEZE DETECTED: {component} unresponsive for {freeze_duration:.1f}s")
        
        self.logger_manager.log_error(
            error_type='system_freeze',
            message=f"Component {component} appears frozen",
            context={
                'component': component,
                'freeze_duration_seconds': freeze_duration,
                'timeout_threshold': watchdog.timeout_seconds,
                'last_heartbeat': watchdog.last_heartbeat
            }
        )
        
        # Log event
        self.logger_manager.log_event(
            'freeze_detected',
            f"Freeze detected in {component}",
            freeze_event
        )
        
        # Execute callback if available
        if watchdog.callback:
            try:
                watchdog.callback(component, freeze_duration)
            except Exception as e:
                self.logger.error(f"Freeze callback failed for {component}: {e}")
        
        # Notify registered callbacks
        for callback in self._freeze_callbacks:
            try:
                callback(component, freeze_duration)
            except Exception as e:
                self.logger.error(f"Freeze notification callback failed: {e}")
        
        # Reset heartbeat timer to avoid repeated alerts
        watchdog.last_heartbeat = time.time()
    
    def register_freeze_callback(self, callback: Callable):
        """Register a callback to be called when freeze is detected"""
        self._freeze_callbacks.append(callback)
    
    def measure_response_time(self, operation: str) -> 'ResponseTimer':
        """Context manager to measure system response time"""
        return ResponseTimer(self, operation)
    
    def log_response_time(self, operation: str, response_time: float):
        """Log system response time"""
        self.system_response_times.append({
            'timestamp': time.time(),
            'operation': operation,
            'response_time': response_time
        })
        
        # Check for slow responses that might indicate freezing
        slow_threshold = 5.0  # seconds
        if response_time > slow_threshold:
            self.logger.warning(f"Slow system response: {operation} took {response_time:.2f}s")
            
            self.logger_manager.log_performance(
                f'{operation}_slow_response',
                response_time,
                'seconds',
                {'threshold': slow_threshold}
            )
    
    # Default freeze handlers
    
    def _handle_data_acquisition_freeze(self, component: str, freeze_duration: float):
        """Handle data acquisition freeze"""
        self.logger.critical(f"Data acquisition frozen for {freeze_duration:.1f}s - Critical for rocket monitoring!")
        
        # This could trigger recovery actions like:
        # - Restart data reader
        # - Switch to backup data source
        # - Alert operators
    
    def _handle_api_freeze(self, component: str, freeze_duration: float):
        """Handle API freeze"""
        self.logger.error(f"API responses frozen for {freeze_duration:.1f}s")
        
        # This could trigger:
        # - Restart API server
        # - Check system load
        # - Clear request queues
    
    def _handle_serial_freeze(self, component: str, freeze_duration: float):
        """Handle serial communication freeze"""
        self.logger.error(f"Serial communication frozen for {freeze_duration:.1f}s")
        
        # This could trigger:
        # - Reconnect serial port
        # - Switch to simulator mode
        # - Check hardware connection
    
    def _handle_system_freeze(self, component: str, freeze_duration: float):
        """Handle overall system freeze"""
        self.logger.critical(f"System health check frozen for {freeze_duration:.1f}s - CRITICAL ALERT!")
        
        # This could trigger:
        # - Emergency shutdown procedures
        # - Alert all operators
        # - Switch to safe mode
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive freeze detection statistics"""
        current_time = time.time()
        uptime = current_time - self.stats['monitoring_start']
        
        # Calculate recent activity
        recent_heartbeats = len([h for h in self.heartbeat_history 
                               if current_time - h['timestamp'] < 300])  # Last 5 minutes
        
        recent_freezes = len([f for f in self.freeze_events 
                            if current_time - f['timestamp'] < 3600])  # Last hour
        
        return {
            **self.stats,
            'uptime_seconds': uptime,
            'uptime_formatted': f"{uptime/3600:.1f}h",
            'active_watchdogs': len([w for w in self.watchdogs.values() if w.active]),
            'total_watchdogs': len(self.watchdogs),
            'recent_heartbeats_5min': recent_heartbeats,
            'recent_freezes_1hour': recent_freezes,
            'heartbeat_rate': self.stats['total_heartbeats'] / max(1, uptime),
            'freeze_rate': self.stats['freezes_detected'] / max(1, uptime/3600),  # per hour
            'watchdog_status': {
                name: {
                    'active': wd.active,
                    'timeout_seconds': wd.timeout_seconds,
                    'seconds_since_heartbeat': current_time - wd.last_heartbeat,
                    'healthy': (current_time - wd.last_heartbeat) < wd.timeout_seconds
                }
                for name, wd in self.watchdogs.items()
            }
        }
    
    def get_recent_events(self, limit: int = 20) -> List[Dict]:
        """Get recent freeze events"""
        return list(self.freeze_events)[-limit:]
    
    def health_check(self) -> Dict[str, Any]:
        """Get freeze detector health status"""
        current_time = time.time()
        
        # Check if any watchdogs are currently triggered
        triggered_watchdogs = []
        for name, wd in self.watchdogs.items():
            if wd.active and (current_time - wd.last_heartbeat) > wd.timeout_seconds:
                triggered_watchdogs.append(name)
        
        # Check recent freeze rate
        recent_freezes = len([f for f in self.freeze_events 
                            if current_time - f['timestamp'] < 3600])  # Last hour
        
        healthy = (
            len(triggered_watchdogs) == 0 and
            recent_freezes < 10 and  # Less than 10 freezes per hour
            self._monitoring
        )
        
        return {
            'healthy': healthy,
            'status': 'healthy' if healthy else 'degraded',
            'monitoring_active': self._monitoring,
            'triggered_watchdogs': triggered_watchdogs,
            'recent_freezes_count': recent_freezes,
            'active_watchdogs': len([w for w in self.watchdogs.values() if w.active])
        }


class ResponseTimer:
    """Context manager for measuring response times"""
    
    def __init__(self, freeze_detector: FreezeDetector, operation: str):
        self.freeze_detector = freeze_detector
        self.operation = operation
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            response_time = time.time() - self.start_time
            self.freeze_detector.log_response_time(self.operation, response_time)