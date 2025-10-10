"""
BLAST Logger Manager - Central coordination for all logging activities
"""

import logging
import logging.config
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class LoggerManager:
    """Central coordinator for BLAST logging system"""
    
    def __init__(self, log_dir: Path, config_path: Optional[Path] = None):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped log files to avoid overwriting
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.data_log = self.log_dir / f"data_{timestamp}.jsonl"
        self.events_log = self.log_dir / f"events_{timestamp}.jsonl"
        self.serial_log = self.log_dir / f"serial_{timestamp}.jsonl"
        self.performance_log = self.log_dir / f"performance_{timestamp}.jsonl"
        self.errors_log = self.log_dir / f"errors_{timestamp}.jsonl"
        self.system_log = self.log_dir / f"system_{timestamp}.log"
        
        # Create "latest" symlinks for easy access
        self._create_latest_symlinks()
        
        # Setup Python logging
        self._setup_logging(config_path)
        
        # Statistics
        self.stats = {
            'data_writes': 0,
            'event_writes': 0,
            'serial_writes': 0,
            'performance_writes': 0,
            'error_writes': 0,
            'start_time': time.time()
        }
        
        self.logger = logging.getLogger('blast.manager')
        self.logger.info("BLAST Logger Manager initialized")
    
    def _create_latest_symlinks(self):
        """Create 'latest' symlinks for easy access to current log files"""
        try:
            symlinks = {
                'data_latest.jsonl': self.data_log,
                'events_latest.jsonl': self.events_log,
                'serial_latest.jsonl': self.serial_log,
                'performance_latest.jsonl': self.performance_log,
                'errors_latest.jsonl': self.errors_log,
                'system_latest.log': self.system_log
            }
            
            for symlink_name, target in symlinks.items():
                symlink_path = self.log_dir / symlink_name
                # Remove existing symlink if it exists
                if symlink_path.exists() or symlink_path.is_symlink():
                    symlink_path.unlink()
                # Create new symlink
                symlink_path.symlink_to(target.name)
                
        except Exception as e:
            # Symlinks might not work on all systems, so just log the error
            logging.getLogger('blast.manager').warning(f"Could not create symlinks: {e}")
    
    def _setup_logging(self, config_path: Optional[Path]):
        """Setup Python logging configuration"""
        if config_path and config_path.exists():
            with open(config_path) as f:
                import yaml
                config = yaml.safe_load(f)
                logging.config.dictConfig(config)
        else:
            # Default configuration
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.StreamHandler(),
                    logging.FileHandler(self.system_log)
                ]
            )
    
    def log_data(self, timestamp: float, raw: Dict, adjusted: Dict, offsets: Dict):
        """Log sensor data to data.jsonl"""
        try:
            entry = {
                'ts': timestamp,
                'raw': raw,
                'adjusted': adjusted,
                'offsets': offsets,
                'logged_at': time.time()
            }
            with open(self.data_log, 'a') as f:
                f.write(json.dumps(entry) + '\n')
            self.stats['data_writes'] += 1
        except Exception as e:
            self.logger.error(f"Failed to log data: {e}")
    
    def log_event(self, event_type: str, message: str, data: Optional[Dict] = None):
        """Log application events to events.jsonl"""
        try:
            entry = {
                'timestamp': time.time(),
                'event_type': event_type,
                'message': message,
                'data': data or {},
                'iso_time': datetime.now().isoformat()
            }
            with open(self.events_log, 'a') as f:
                f.write(json.dumps(entry) + '\n')
            self.stats['event_writes'] += 1
        except Exception as e:
            self.logger.error(f"Failed to log event: {e}")
    
    def log_serial(self, direction: str, data: str, port: str, success: bool = True, error: Optional[str] = None):
        """Log serial communication to serial.jsonl"""
        try:
            entry = {
                'timestamp': time.time(),
                'direction': direction,  # 'read' or 'write'
                'port': port,
                'data': data,
                'success': success,
                'error': error,
                'data_length': len(data) if data else 0
            }
            with open(self.serial_log, 'a') as f:
                f.write(json.dumps(entry) + '\n')
            self.stats['serial_writes'] += 1
        except Exception as e:
            self.logger.error(f"Failed to log serial: {e}")
    
    def log_performance(self, metric_type: str, value: float, unit: str, context: Optional[Dict] = None):
        """Log performance metrics to performance.jsonl"""
        try:
            entry = {
                'timestamp': time.time(),
                'metric_type': metric_type,
                'value': value,
                'unit': unit,
                'context': context or {}
            }
            with open(self.performance_log, 'a') as f:
                f.write(json.dumps(entry) + '\n')
            self.stats['performance_writes'] += 1
        except Exception as e:
            self.logger.error(f"Failed to log performance: {e}")
    
    def log_error(self, error_type: str, message: str, exception: Optional[Exception] = None, context: Optional[Dict] = None):
        """Log errors to errors.jsonl"""
        try:
            entry = {
                'timestamp': time.time(),
                'error_type': error_type,
                'message': message,
                'exception': str(exception) if exception else None,
                'exception_type': type(exception).__name__ if exception else None,
                'context': context or {},
                'iso_time': datetime.now().isoformat()
            }
            with open(self.errors_log, 'a') as f:
                f.write(json.dumps(entry) + '\n')
            self.stats['error_writes'] += 1
        except Exception as e:
            self.logger.error(f"Failed to log error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get logging statistics"""
        uptime = time.time() - self.stats['start_time']
        return {
            **self.stats,
            'uptime_seconds': uptime,
            'uptime_formatted': f"{uptime/3600:.1f}h",
            'log_files': {
                'data': str(self.data_log),
                'events': str(self.events_log),
                'serial': str(self.serial_log),
                'performance': str(self.performance_log),
                'errors': str(self.errors_log),
                'system': str(self.system_log)
            }
        }
    
    def cleanup_old_logs(self, days: int = 7):
        """Clean up log files older than specified days"""
        cutoff = time.time() - (days * 24 * 3600)
        cleaned = 0
        
        for log_file in self.log_dir.glob("*.jsonl"):
            if log_file.stat().st_mtime < cutoff:
                try:
                    # Archive instead of delete
                    archive_name = f"{log_file.stem}_{int(log_file.stat().st_mtime)}.archived"
                    log_file.rename(self.log_dir / archive_name)
                    cleaned += 1
                except Exception as e:
                    self.logger.error(f"Failed to archive {log_file}: {e}")
        
        self.log_event('system', f'Log cleanup completed, archived {cleaned} files')
        return cleaned