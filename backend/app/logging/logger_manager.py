"""
BLAST Logger Manager - Central coordination for all logging activities
"""

import logging
import logging.config
import json
import time
import csv
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class LoggerManager:
    """Central coordinator for BLAST logging system"""
    
    def __init__(self, log_dir: Path, config_path: Optional[Path] = None):
        self.base_log_dir = Path(log_dir)
        self.base_log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create run-specific directory with timestamp
        self.run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = self.base_log_dir / self.run_timestamp
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log files in the run directory (no timestamps needed in filenames)
        self.data_log = self.log_dir / "data.jsonl"
        self.events_log = self.log_dir / "events.jsonl"
        self.serial_log = self.log_dir / "serial.jsonl"
        self.performance_log = self.log_dir / "performance.jsonl"
        self.errors_log = self.log_dir / "errors.jsonl"
        self.system_log = self.log_dir / "system.log"
        self.data_csv_log = self.log_dir / "data.csv"
        
        # Create "latest" symlink to current run directory
        self._create_latest_symlink()
        
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
    
    def _create_latest_symlink(self):
        """Create 'latest' symlink to current run directory"""
        try:
            latest_symlink = self.base_log_dir / 'latest'
            # Remove existing symlink if it exists
            if latest_symlink.exists() or latest_symlink.is_symlink():
                latest_symlink.unlink()
            # Create symlink to current run directory
            latest_symlink.symlink_to(self.run_timestamp)
                
        except Exception as e:
            # Symlinks might not work on all systems, so just log the error
            logging.getLogger('blast.manager').warning(f"Could not create latest symlink: {e}")
    
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


    def log_data_csv(self, timestamp: float, raw: Dict, adjusted: Dict, offsets: Dict, settings):
        """Log sensor data to data.csv"""
        try:
            if not os.path.exists(self.data_csv_log):
                print("No header: i am writing the header")
                header =( 
                    ["ts"] +
                    [("raw_" + rawKeys) for rawKeys in raw] + 
                    [("adjusted_" + adjustedKeys) for adjustedKeys in adjusted] + 
                    # [("offset_" + offsetsKeys) for offsetsKeys in offsets] +
                    [("offset_" + pt.get("id")) for pt in settings.PRESSURE_TRANSDUCERS] +
                    [("offset_" + pt.get("id")) for pt in settings.THERMOCOUPLES] +
                    [("offset_" + pt.get("id")) for pt in settings.LOAD_CELLS] +
                    ["logged_at"]
                    )
                with open(self.data_csv_log, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(header)
                    
            #print("am i gonig in here")
            combined = (
                [timestamp] +
                [sensorValue for sensorType in (raw, adjusted) for sensorMeasurements in sensorType.values() for sensorValue in sensorMeasurements] +
                [offset for offset in offsets.values()] +
                [time.time()]
                )
            #print(combined)
            with open(self.data_csv_log, 'a', newline='') as f:
                #print("im lkahgdagkfdsjgkgdajhgagk")
                writer = csv.writer(f)
                writer.writerow(combined)
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
            'run_info': {
                'run_timestamp': self.run_timestamp,
                'run_directory': str(self.log_dir),
                'base_log_directory': str(self.base_log_dir)
            },
            'log_files': {
                'data': str(self.data_log),
                'events': str(self.events_log),
                'serial': str(self.serial_log),
                'performance': str(self.performance_log),
                'errors': str(self.errors_log),
                'system': str(self.system_log),
                'data-csv': str(self.data_csv_log)
            }
        }
    
    def cleanup_old_runs(self, days: int = 7):
        """Clean up old run directories older than specified days"""
        cutoff = time.time() - (days * 24 * 3600)
        cleaned = 0
        
        for run_dir in self.base_log_dir.glob("20*"):  # Directories starting with year
            if run_dir.is_dir() and run_dir.stat().st_mtime < cutoff:
                try:
                    # Archive instead of delete
                    archive_name = f"{run_dir.name}.archived"
                    archive_path = self.base_log_dir / archive_name
                    run_dir.rename(archive_path)
                    cleaned += 1
                except Exception as e:
                    self.logger.error(f"Failed to archive run directory {run_dir}: {e}")
        
        self.log_event('system', f'Log cleanup completed, archived {cleaned} run directories')
        return cleaned
    
    def create_run_summary(self):
        """Create a summary file for this run"""
        try:
            summary = {
                'run_timestamp': self.run_timestamp,
                'start_time': self.stats['start_time'],
                'end_time': time.time(),
                'duration_seconds': time.time() - self.stats['start_time'],
                'statistics': dict(self.stats),
                'log_files_created': list(self.log_files.keys()) if hasattr(self, 'log_files') else []
            }
            
            summary_file = self.log_dir / 'run_summary.json'
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to create run summary: {e}")