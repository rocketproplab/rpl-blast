"""
PerformanceMonitor: Track and log performance metrics with timing measurements
"""

import time
import threading
from contextlib import contextmanager
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import json
from datetime import datetime
import psutil
import sys


@dataclass
class MetricStats:
    """Statistics for a performance metric"""
    name: str
    count: int = 0
    total: float = 0.0
    min_value: float = float('inf')
    max_value: float = float('-inf')
    last_value: float = 0.0
    
    def add_sample(self, value: float):
        """Add a sample to the statistics"""
        self.count += 1
        self.total += value
        self.min_value = min(self.min_value, value)
        self.max_value = max(self.max_value, value)
        self.last_value = value
    
    @property
    def average(self) -> float:
        """Calculate average value"""
        return self.total / self.count if self.count > 0 else 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'name': self.name,
            'count': self.count,
            'average': round(self.average, 3),
            'min': round(self.min_value, 3) if self.min_value != float('inf') else None,
            'max': round(self.max_value, 3) if self.max_value != float('-inf') else None,
            'last': round(self.last_value, 3)
        }


class PerformanceMonitor:
    """Monitor and log performance metrics"""
    
    def __init__(self, sample_interval: float = 1.0, log_interval: float = 60.0):
        """Initialize performance monitor
        
        Args:
            sample_interval: How often to sample metrics (seconds)
            log_interval: How often to log aggregated metrics (seconds)
        """
        self.sample_interval = sample_interval
        self.log_interval = log_interval
        self.metrics: Dict[str, MetricStats] = {}
        self.metrics_lock = threading.Lock()
        
        # Get logger
        from app.logging.logger_manager import get_logger_manager
        self.logger = get_logger_manager().get_logger('performance')
        
        # System metrics
        self.process = psutil.Process()
        self.last_log_time = time.time()
        
        # Monitoring thread
        self.monitor_thread = None
        self.stop_flag = threading.Event()
        
        # Operation timings
        self.active_timings: Dict[str, float] = {}
        
        # Fail-fast validation
        if sample_interval <= 0 or log_interval <= 0:
            raise ValueError("Sample and log intervals must be positive")
        
        self.logger.info(f"PerformanceMonitor initialized (sample={sample_interval}s, log={log_interval}s)")
    
    @contextmanager
    def measure(self, operation: str):
        """Context manager to measure operation timing
        
        Usage:
            with perf_monitor.measure('database_query'):
                # do something
        """
        start_time = time.perf_counter()
        
        # Store start time for nested operations
        thread_id = threading.get_ident()
        key = f"{thread_id}:{operation}"
        self.active_timings[key] = start_time
        
        try:
            yield
        finally:
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Remove from active timings
            self.active_timings.pop(key, None)
            
            # Record metric
            self.record_metric(f"{operation}_time", duration_ms, "ms")
            
            # Log if slow operation
            if duration_ms > 500:  # More than 500ms
                self.logger.warning(f"Slow operation: {operation} took {duration_ms:.1f}ms")
    
    def record_metric(self, name: str, value: float, unit: str = ""):
        """Record a performance metric
        
        Args:
            name: Metric name
            value: Metric value
            unit: Optional unit (ms, MB, etc)
        """
        with self.metrics_lock:
            if name not in self.metrics:
                self.metrics[name] = MetricStats(name)
            
            self.metrics[name].add_sample(value)
            
            # Check if it's time to log
            current_time = time.time()
            if current_time - self.last_log_time >= self.log_interval:
                self._log_metrics()
                self.last_log_time = current_time
    
    def start_monitoring(self):
        """Start the monitoring thread"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.logger.warning("Monitor thread already running")
            return
        
        self.stop_flag.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop the monitoring thread"""
        if not self.monitor_thread:
            return
        
        self.stop_flag.set()
        self.monitor_thread.join(timeout=2)
        
        if self.monitor_thread.is_alive():
            self.logger.error("Monitor thread did not stop cleanly")
        else:
            self.logger.info("Performance monitoring stopped")
    
    def _monitor_loop(self):
        """Background thread that samples system metrics"""
        while not self.stop_flag.is_set():
            try:
                # Sample system metrics
                self._sample_system_metrics()
                
                # Sleep for sample interval
                time.sleep(self.sample_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}")
    
    def _sample_system_metrics(self):
        """Sample current system metrics"""
        try:
            # Memory usage
            mem_info = self.process.memory_info()
            mem_mb = mem_info.rss / 1024 / 1024
            self.record_metric("memory_mb", mem_mb, "MB")
            
            # CPU percent
            cpu_percent = self.process.cpu_percent()
            if cpu_percent > 0:  # Skip first call which returns 0
                self.record_metric("cpu_percent", cpu_percent, "%")
            
            # Thread count
            num_threads = threading.active_count()
            self.record_metric("thread_count", num_threads, "threads")
            
            # Check for memory threshold
            if mem_mb > 500:  # Configurable threshold
                self.logger.warning(f"High memory usage: {mem_mb:.1f}MB")
            
        except Exception as e:
            self.logger.error(f"Error sampling system metrics: {e}")
    
    def _log_metrics(self):
        """Log aggregated metrics"""
        with self.metrics_lock:
            if not self.metrics:
                return
            
            # Create summary
            summary = {
                'timestamp': datetime.utcnow().isoformat(),
                'metrics': {}
            }
            
            for name, stats in self.metrics.items():
                summary['metrics'][name] = stats.to_dict()
            
            # Log as JSON
            self.logger.info(json.dumps(summary))
            
            # Reset non-system metrics
            metrics_to_reset = [name for name in self.metrics.keys() 
                              if not name.startswith(('memory_', 'cpu_', 'thread_'))]
            
            for name in metrics_to_reset:
                self.metrics[name] = MetricStats(name)
    
    def get_statistics(self) -> dict:
        """Get current statistics for all metrics"""
        with self.metrics_lock:
            return {name: stats.to_dict() for name, stats in self.metrics.items()}
    
    def get_metrics(self) -> dict:
        """Get all collected metrics (alias for get_statistics for compatibility)"""
        return self.get_statistics()
    
    def check_health(self) -> dict:
        """Check system health and return status"""
        try:
            mem_info = self.process.memory_info()
            mem_mb = mem_info.rss / 1024 / 1024
            
            health = {
                'healthy': True,
                'memory_mb': round(mem_mb, 1),
                'cpu_percent': self.process.cpu_percent(),
                'thread_count': threading.active_count(),
                'active_operations': len(self.active_timings),
                'metrics_tracked': len(self.metrics)
            }
            
            # Check thresholds
            if mem_mb > 500:
                health['healthy'] = False
                health['issues'] = health.get('issues', []) + ['High memory usage']
            
            if health['thread_count'] > 50:
                health['healthy'] = False
                health['issues'] = health.get('issues', []) + ['Too many threads']
            
            return health
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }


# Decorator for easy function timing
def measure_time(operation_name: Optional[str] = None):
    """Decorator to measure function execution time
    
    Usage:
        @measure_time()
        def my_function():
            pass
            
        @measure_time("custom_operation")
        def another_function():
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get or create monitor instance
            from app.logging.logger_manager import get_logger_manager
            
            # Use function name if operation name not provided
            op_name = operation_name or func.__name__
            
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000
                
                # Log directly if no monitor available
                logger = get_logger_manager().get_logger('performance')
                if duration_ms > 100:  # Log slow operations
                    logger.info(f"{op_name} took {duration_ms:.1f}ms")
        
        return wrapper
    return decorator


# Global instance for convenience
_monitor = None

def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor()
        _monitor.start_monitoring()
    return _monitor