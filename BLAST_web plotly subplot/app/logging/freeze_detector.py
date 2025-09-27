"""
FreezeDetector: Monitor application health and detect freezes
Uses watchdog pattern to detect when main thread stops responding
"""

import time
import threading
import json
import traceback
import sys
from datetime import datetime
from typing import List, Optional, Dict
from collections import deque
from pathlib import Path


class FreezeDetector:
    """Detect when application freezes using heartbeat/watchdog pattern"""
    
    def __init__(self, timeout: float = 5.0, heartbeat_interval: float = 1.0):
        """Initialize freeze detector
        
        Args:
            timeout: Seconds without heartbeat before declaring freeze
            heartbeat_interval: Expected heartbeat interval
        """
        # Validate parameters - fail fast
        if timeout <= 0 or heartbeat_interval <= 0:
            raise ValueError("Timeout and heartbeat interval must be positive")
        
        if timeout <= heartbeat_interval:
            raise ValueError("Timeout must be greater than heartbeat interval")
        
        self.timeout = timeout
        self.heartbeat_interval = heartbeat_interval
        self.last_heartbeat = time.time()
        self.watchdog_thread = None
        self.heartbeat_thread = None
        self.stop_flag = threading.Event()
        
        # Track recent operations for debugging
        self.recent_operations = deque(maxlen=100)
        self.operations_lock = threading.Lock()
        
        # Freeze detection state
        self.freeze_detected = False
        self.freeze_count = 0
        
        # Get logger
        from app.logging.logger_manager import get_logger_manager
        self.logger = get_logger_manager().get_logger('app')
        self.error_logger = get_logger_manager().get_logger('errors')
        
        self.logger.info(f"FreezeDetector initialized (timeout={timeout}s, interval={heartbeat_interval}s)")
    
    def start(self):
        """Start freeze detection threads"""
        if self.watchdog_thread and self.watchdog_thread.is_alive():
            self.logger.warning("Freeze detector already running")
            return
        
        self.stop_flag.clear()
        self.freeze_detected = False
        self.last_heartbeat = time.time()
        
        # Start watchdog thread
        self.watchdog_thread = threading.Thread(
            target=self._watchdog_loop,
            name="FreezeWatchdog",
            daemon=True
        )
        self.watchdog_thread.start()
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name="Heartbeat",
            daemon=True
        )
        self.heartbeat_thread.start()
        
        self.logger.info("Freeze detection started")
    
    def stop(self):
        """Stop freeze detection threads"""
        self.stop_flag.set()
        
        if self.watchdog_thread:
            self.watchdog_thread.join(timeout=2)
            if self.watchdog_thread.is_alive():
                self.logger.error("Watchdog thread did not stop cleanly")
        
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=2)
            if self.heartbeat_thread.is_alive():
                self.logger.error("Heartbeat thread did not stop cleanly")
        
        self.logger.info("Freeze detection stopped")
    
    def heartbeat(self):
        """Record a heartbeat from the main thread"""
        current_time = time.time()
        gap = current_time - self.last_heartbeat
        
        # Check for recovery from freeze
        if self.freeze_detected and gap < self.timeout:
            recovery_time = current_time - self.last_heartbeat
            self.logger.warning(f"Application recovered from freeze after {recovery_time:.1f}s")
            self.freeze_detected = False
        
        self.last_heartbeat = current_time
        
        # Log if there was a significant gap
        if gap > 2 * self.heartbeat_interval:
            self.logger.warning(f"Heartbeat gap detected: {gap:.1f}s")
    
    def log_operation(self, operation: str, details: Optional[Dict] = None):
        """Log an operation for debugging purposes"""
        with self.operations_lock:
            self.recent_operations.append({
                'timestamp': time.time(),
                'operation': operation,
                'details': details or {},
                'thread': threading.current_thread().name
            })
    
    def _watchdog_loop(self):
        """Watchdog thread that checks for freezes"""
        while not self.stop_flag.is_set():
            try:
                current_time = time.time()
                time_since_heartbeat = current_time - self.last_heartbeat
                
                if time_since_heartbeat > self.timeout:
                    if not self.freeze_detected:
                        self._handle_freeze_detected(time_since_heartbeat)
                    elif time_since_heartbeat > self.timeout * 2:
                        # Severe freeze - dump more info
                        self.error_logger.error(
                            f"SEVERE FREEZE: No heartbeat for {time_since_heartbeat:.1f}s"
                        )
                
                # Sleep briefly before next check
                time.sleep(0.5)
                
            except Exception as e:
                self.error_logger.error(f"Error in watchdog loop: {e}", exc_info=True)
    
    def _heartbeat_loop(self):
        """Generate heartbeats to detect main thread freezes"""
        while not self.stop_flag.is_set():
            try:
                # Log heartbeat
                self.logger.debug(f"Heartbeat at {datetime.now().isoformat()}")
                
                # Check if we should log a heartbeat gap
                gap = time.time() - self.last_heartbeat
                if gap > 2 * self.heartbeat_interval:
                    self.logger.warning(f"Heartbeat gap: {gap:.1f}s")
                
                # Sleep for interval
                time.sleep(self.heartbeat_interval)
                
            except Exception as e:
                self.error_logger.error(f"Error in heartbeat loop: {e}")
    
    def _handle_freeze_detected(self, duration: float):
        """Handle freeze detection"""
        self.freeze_detected = True
        self.freeze_count += 1
        
        # Log critical error
        self.error_logger.critical(
            f"FREEZE DETECTED! No heartbeat for {duration:.1f}s (freeze #{self.freeze_count})"
        )
        
        # Dump diagnostic information
        self._dump_diagnostics()
    
    def _dump_diagnostics(self):
        """Dump diagnostic information when freeze is detected"""
        try:
            diagnostics = {
                'timestamp': datetime.utcnow().isoformat(),
                'freeze_count': self.freeze_count,
                'time_since_heartbeat': time.time() - self.last_heartbeat,
                'thread_info': self._get_thread_info(),
                'recent_operations': list(self.recent_operations)[-50:],  # Last 50 operations
                'system_info': self._get_system_info()
            }
            
            # Write to freeze dump file in the run directory
            try:
                from app.logging.logger_manager import get_logger_manager
                logger_mgr = get_logger_manager()
                if hasattr(logger_mgr, 'run_dir'):
                    dump_dir = logger_mgr.run_dir
                else:
                    dump_dir = Path("logs")
            except:
                dump_dir = Path("logs")
                
            dump_file = dump_dir / f"freeze_dump_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(dump_file, 'w') as f:
                json.dump(diagnostics, f, indent=2, default=str)
            
            self.error_logger.critical(f"Freeze diagnostics dumped to {dump_file}")
            
            # Log key info to error log
            self.error_logger.critical(f"Active threads: {len(diagnostics['thread_info'])}")
            self.error_logger.critical(
                f"Last operations: {[op['operation'] for op in diagnostics['recent_operations'][-5:]]}"
            )
            
        except Exception as e:
            self.error_logger.error(f"Failed to dump diagnostics: {e}", exc_info=True)
    
    def _get_thread_info(self) -> List[Dict]:
        """Get information about all active threads"""
        thread_info = []
        
        for thread in threading.enumerate():
            try:
                # Get thread stack trace
                frame = sys._current_frames().get(thread.ident)
                if frame:
                    stack = traceback.format_stack(frame)
                    stack_str = ''.join(stack[-3:])  # Last 3 stack frames
                else:
                    stack_str = "No stack trace available"
                
                thread_info.append({
                    'name': thread.name,
                    'daemon': thread.daemon,
                    'alive': thread.is_alive(),
                    'stack_trace': stack_str
                })
            except Exception as e:
                thread_info.append({
                    'name': thread.name,
                    'error': str(e)
                })
        
        return thread_info
    
    def _get_system_info(self) -> Dict:
        """Get system information for diagnostics"""
        try:
            import psutil
            process = psutil.Process()
            
            return {
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'cpu_percent': process.cpu_percent(),
                'num_threads': process.num_threads(),
                'open_files': len(process.open_files()),
                'connections': len(process.connections())
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_recent_operations(self, count: int = 10) -> List[Dict]:
        """Get the most recent operations
        
        Args:
            count: Number of operations to return
            
        Returns:
            List of recent operations
        """
        with self.operations_lock:
            operations = list(self.recent_operations)
            return operations[-count:] if operations else []
    
    def check_health(self) -> Dict:
        """Check freeze detector health"""
        current_time = time.time()
        time_since_heartbeat = current_time - self.last_heartbeat
        
        return {
            'healthy': not self.freeze_detected,
            'time_since_heartbeat': round(time_since_heartbeat, 1),
            'freeze_detected': self.freeze_detected,
            'freeze_count': self.freeze_count,
            'watchdog_alive': self.watchdog_thread and self.watchdog_thread.is_alive(),
            'heartbeat_alive': self.heartbeat_thread and self.heartbeat_thread.is_alive()
        }


# Global instance
_detector = None

def get_freeze_detector() -> FreezeDetector:
    """Get the global freeze detector instance"""
    global _detector
    if _detector is None:
        _detector = FreezeDetector()
    return _detector