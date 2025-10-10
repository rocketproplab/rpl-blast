"""
BLAST Performance Monitor - System performance tracking and alerting
"""

import logging
import time
import psutil
import threading
from typing import Dict, Any, Optional, List
from collections import deque
from dataclasses import dataclass


@dataclass
class PerformanceThresholds:
    """Performance alert thresholds"""
    cpu_percent_warning: float = 80.0
    cpu_percent_critical: float = 95.0
    memory_percent_warning: float = 85.0
    memory_percent_critical: float = 95.0
    data_lag_warning_ms: float = 1000.0
    data_lag_critical_ms: float = 5000.0
    api_response_warning_ms: float = 500.0
    api_response_critical_ms: float = 2000.0


class PerformanceMonitor:
    """Monitors system performance and logs metrics"""
    
    def __init__(self, logger_manager, thresholds: Optional[PerformanceThresholds] = None):
        self.logger_manager = logger_manager
        self.logger = logging.getLogger('blast.performance')
        self.thresholds = thresholds or PerformanceThresholds()
        
        # Performance history
        self.cpu_history = deque(maxlen=100)
        self.memory_history = deque(maxlen=100)
        self.response_times = deque(maxlen=100)
        self.data_lag_history = deque(maxlen=100)
        
        # Timing contexts
        self.active_timers = {}
        
        # Statistics
        self.stats = {
            'alerts_sent': 0,
            'monitoring_start': time.time(),
            'last_system_check': 0,
            'total_api_calls': 0,
            'slow_api_calls': 0
        }
        
        # Monitoring thread
        self._monitoring = False
        self._monitor_thread = None
        
        self.start_monitoring()
    
    def start_monitoring(self):
        """Start background performance monitoring"""
        if not self._monitoring:
            self._monitoring = True
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()
            self.logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop background performance monitoring"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        self.logger.info("Performance monitoring stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self._monitoring:
            try:
                self._check_system_performance()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self.logger.error(f"Error in performance monitoring: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _check_system_performance(self):
        """Check system CPU, memory, and other metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.cpu_history.append({'timestamp': time.time(), 'value': cpu_percent})
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            self.memory_history.append({'timestamp': time.time(), 'value': memory_percent})
            
            # Log metrics
            self.logger_manager.log_performance('cpu_percent', cpu_percent, 'percent')
            self.logger_manager.log_performance('memory_percent', memory_percent, 'percent')
            self.logger_manager.log_performance('memory_used_gb', memory.used / (1024**3), 'GB')
            self.logger_manager.log_performance('memory_available_gb', memory.available / (1024**3), 'GB')
            
            # Check thresholds
            self._check_cpu_threshold(cpu_percent)
            self._check_memory_threshold(memory_percent)
            
            self.stats['last_system_check'] = time.time()
            
        except Exception as e:
            self.logger.error(f"Failed to check system performance: {e}")
    
    def _check_cpu_threshold(self, cpu_percent: float):
        """Check CPU usage against thresholds"""
        if cpu_percent >= self.thresholds.cpu_percent_critical:
            self._send_alert('cpu_critical', f"Critical CPU usage: {cpu_percent:.1f}%", 'critical')
        elif cpu_percent >= self.thresholds.cpu_percent_warning:
            self._send_alert('cpu_warning', f"High CPU usage: {cpu_percent:.1f}%", 'warning')
    
    def _check_memory_threshold(self, memory_percent: float):
        """Check memory usage against thresholds"""
        if memory_percent >= self.thresholds.memory_percent_critical:
            self._send_alert('memory_critical', f"Critical memory usage: {memory_percent:.1f}%", 'critical')
        elif memory_percent >= self.thresholds.memory_percent_warning:
            self._send_alert('memory_warning', f"High memory usage: {memory_percent:.1f}%", 'warning')
    
    def start_timer(self, operation: str) -> str:
        """Start timing an operation"""
        timer_id = f"{operation}_{time.time()}"
        self.active_timers[timer_id] = {
            'operation': operation,
            'start_time': time.time()
        }
        return timer_id
    
    def end_timer(self, timer_id: str) -> Optional[float]:
        """End timing and log the duration"""
        if timer_id not in self.active_timers:
            return None
        
        timer = self.active_timers.pop(timer_id)
        duration = time.time() - timer['start_time']
        duration_ms = duration * 1000
        
        operation = timer['operation']
        
        # Log the performance metric
        self.logger_manager.log_performance(f'{operation}_duration_ms', duration_ms, 'milliseconds')
        
        # Check for slow operations
        if operation.startswith('api_') and duration_ms > self.thresholds.api_response_warning_ms:
            self.stats['slow_api_calls'] += 1
            if duration_ms > self.thresholds.api_response_critical_ms:
                self._send_alert('api_slow_critical', f"Critical API response time: {duration_ms:.1f}ms for {operation}", 'critical')
            else:
                self._send_alert('api_slow_warning', f"Slow API response: {duration_ms:.1f}ms for {operation}", 'warning')
        
        # Track response times
        if operation.startswith('api_'):
            self.response_times.append({'timestamp': time.time(), 'operation': operation, 'duration_ms': duration_ms})
            self.stats['total_api_calls'] += 1
        
        return duration
    
    def log_data_lag(self, lag_ms: float):
        """Log data acquisition lag"""
        self.data_lag_history.append({'timestamp': time.time(), 'lag_ms': lag_ms})
        self.logger_manager.log_performance('data_lag_ms', lag_ms, 'milliseconds')
        
        # Check lag thresholds
        if lag_ms >= self.thresholds.data_lag_critical_ms:
            self._send_alert('data_lag_critical', f"Critical data lag: {lag_ms:.1f}ms", 'critical')
        elif lag_ms >= self.thresholds.data_lag_warning_ms:
            self._send_alert('data_lag_warning', f"High data lag: {lag_ms:.1f}ms", 'warning')
    
    def log_custom_metric(self, metric_name: str, value: float, unit: str, context: Dict = None):
        """Log custom performance metric"""
        self.logger_manager.log_performance(metric_name, value, unit, context)
    
    def _send_alert(self, alert_type: str, message: str, severity: str):
        """Send performance alert"""
        self.stats['alerts_sent'] += 1
        
        # Log to event logger if available
        if hasattr(self.logger_manager, 'event_logger'):
            self.logger_manager.event_logger.log_performance_alert(alert_type, 0, 0, severity)
        
        # Log to performance log
        self.logger_manager.log_performance(f'alert_{alert_type}', 1, 'count', {'message': message, 'severity': severity})
        
        # Log to Python logger
        if severity == 'critical':
            self.logger.critical(f"PERFORMANCE ALERT: {message}")
        else:
            self.logger.warning(f"Performance Alert: {message}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        uptime = time.time() - self.stats['monitoring_start']
        
        # Calculate averages
        recent_cpu = [item['value'] for item in list(self.cpu_history)[-10:]]
        recent_memory = [item['value'] for item in list(self.memory_history)[-10:]]
        recent_responses = [item['duration_ms'] for item in list(self.response_times)[-10:]]
        recent_lag = [item['lag_ms'] for item in list(self.data_lag_history)[-10:]]
        
        return {
            **self.stats,
            'uptime_seconds': uptime,
            'uptime_formatted': f"{uptime/3600:.1f}h",
            'current_metrics': {
                'avg_cpu_percent_recent': sum(recent_cpu) / len(recent_cpu) if recent_cpu else 0,
                'avg_memory_percent_recent': sum(recent_memory) / len(recent_memory) if recent_memory else 0,
                'avg_response_time_ms_recent': sum(recent_responses) / len(recent_responses) if recent_responses else 0,
                'avg_data_lag_ms_recent': sum(recent_lag) / len(recent_lag) if recent_lag else 0
            },
            'history_counts': {
                'cpu_samples': len(self.cpu_history),
                'memory_samples': len(self.memory_history),
                'response_samples': len(self.response_times),
                'lag_samples': len(self.data_lag_history)
            },
            'api_performance': {
                'total_calls': self.stats['total_api_calls'],
                'slow_calls': self.stats['slow_api_calls'],
                'slow_call_rate': self.stats['slow_api_calls'] / max(1, self.stats['total_api_calls'])
            }
        }
    
    def get_recent_history(self, metric: str, limit: int = 50) -> List[Dict]:
        """Get recent history for a specific metric"""
        histories = {
            'cpu': self.cpu_history,
            'memory': self.memory_history,
            'response_times': self.response_times,
            'data_lag': self.data_lag_history
        }
        
        if metric in histories:
            return list(histories[metric])[-limit:]
        else:
            return []
    
    def health_check(self) -> Dict[str, Any]:
        """Get performance health status"""
        stats = self.get_stats()
        
        # Determine health status
        issues = []
        current = stats['current_metrics']
        
        if current['avg_cpu_percent_recent'] > self.thresholds.cpu_percent_warning:
            issues.append(f"High CPU: {current['avg_cpu_percent_recent']:.1f}%")
        
        if current['avg_memory_percent_recent'] > self.thresholds.memory_percent_warning:
            issues.append(f"High Memory: {current['avg_memory_percent_recent']:.1f}%")
        
        if current['avg_response_time_ms_recent'] > self.thresholds.api_response_warning_ms:
            issues.append(f"Slow API: {current['avg_response_time_ms_recent']:.1f}ms")
        
        if current['avg_data_lag_ms_recent'] > self.thresholds.data_lag_warning_ms:
            issues.append(f"Data Lag: {current['avg_data_lag_ms_recent']:.1f}ms")
        
        return {
            'healthy': len(issues) == 0,
            'status': 'healthy' if len(issues) == 0 else 'degraded',
            'issues': issues,
            'metrics': current,
            'alerts_sent': self.stats['alerts_sent']
        }