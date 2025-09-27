"""
LoggerManager: Centralized logging configuration and management
Fail-fast approach with comprehensive validation
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Optional, Any
from queue import Queue, Full
import threading
import json
from datetime import datetime
import sys
import traceback


class LoggerManager:
    """Centralized logging configuration with fail-fast validation"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern to ensure one logging manager"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize logging manager with fail-fast checks"""
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        self.loggers: Dict[str, logging.Logger] = {}
        self.log_queue = Queue(maxsize=10000)
        self.writer_thread = None
        self.shutdown_flag = threading.Event()
        self.context = {}
        self._is_initialized = False
        
        # Create timestamp for this run
        self.run_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Validate log directory can be created
        self.log_dir = Path("logs")
        try:
            # Create main log directory
            self.log_dir.mkdir(exist_ok=True)
            
            # Create timestamped run directory
            self.run_dir = self.log_dir / f"run_{self.run_timestamp}"
            self.run_dir.mkdir(exist_ok=True)
            
            # Create subdirectories for this run
            (self.run_dir / "events").mkdir(exist_ok=True)
            (self.run_dir / "errors").mkdir(exist_ok=True)
            (self.run_dir / "performance").mkdir(exist_ok=True)
            (self.run_dir / "serial").mkdir(exist_ok=True)
            (self.run_dir / "data").mkdir(exist_ok=True)
            
            # Create symlink to latest run for convenience
            latest_link = self.log_dir / "latest"
            if latest_link.exists() or latest_link.is_symlink():
                latest_link.unlink()
            latest_link.symlink_to(self.run_dir.name)
            
        except Exception as e:
            print(f"FATAL: Cannot create log directories: {e}", file=sys.stderr)
            raise
        
        # Initialize core loggers
        self._setup_loggers()
        self._is_initialized = True
        
        # Log the run information
        app_logger = self.get_logger('app')
        app_logger.info(f"="*60)
        app_logger.info(f"New logging session started: {self.run_timestamp}")
        app_logger.info(f"Log directory: {self.run_dir}")
        app_logger.info(f"="*60)
    
    def _setup_loggers(self):
        """Set up logger instances with appropriate handlers"""
        # Root logger configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # Remove default handlers
        root_logger.handlers.clear()
        
        # Console handler for immediate feedback
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        root_logger.addHandler(console_handler)
        
        # Create specialized loggers
        self._create_logger('events', 'events/events.log', level=logging.INFO, json_format=True)
        self._create_logger('errors', 'errors/errors.log', level=logging.ERROR, detailed=True)
        self._create_logger('performance', 'performance/perf.log', level=logging.DEBUG, json_format=True)
        self._create_logger('serial', 'serial/serial.log', level=logging.DEBUG)
        self._create_logger('app', 'app.log', level=logging.DEBUG)
    
    def _create_logger(self, name: str, filename: str, level: int = logging.INFO, 
                      json_format: bool = False, detailed: bool = False):
        """Create a logger with rotating file handler"""
        logger = logging.getLogger(f"blast.{name}")
        logger.setLevel(level)
        logger.propagate = False  # Don't propagate to root logger
        
        # Create rotating file handler - use run_dir for timestamped logs
        file_path = self.run_dir / filename
        try:
            handler = logging.handlers.RotatingFileHandler(
                file_path,
                maxBytes=100 * 1024 * 1024,  # 100MB
                backupCount=7,
                encoding='utf-8'
            )
        except Exception as e:
            print(f"FATAL: Cannot create log file {file_path}: {e}", file=sys.stderr)
            raise
        
        handler.setLevel(level)
        
        # Set formatter based on type
        if json_format:
            handler.setFormatter(JsonFormatter())
        elif detailed:
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s [%(filename)s:%(lineno)d]\n'
                '%(message)s\n'
                '---Stack Trace---\n%(exc_info)s\n---End Trace---\n',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
        else:
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        self.loggers[name] = logger
        
        # Test write to ensure it works
        logger.info(f"Logger '{name}' initialized successfully")
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger instance"""
        if name in self.loggers:
            return self.loggers[name]
        
        # Create a new logger if it doesn't exist
        logger = logging.getLogger(f"blast.{name}")
        self.loggers[name] = logger
        return logger
    
    def add_context(self, **kwargs):
        """Add context that will be included in all log messages"""
        self.context.update(kwargs)
    
    def clear_context(self):
        """Clear the logging context"""
        self.context.clear()
    
    def start_async_writer(self):
        """Start background thread for async logging"""
        if self.writer_thread and self.writer_thread.is_alive():
            return
        
        self.writer_thread = threading.Thread(target=self._async_writer, daemon=True)
        self.writer_thread.start()
        self.get_logger('app').info("Async log writer started")
    
    def _async_writer(self):
        """Background thread that writes log messages from queue"""
        while not self.shutdown_flag.is_set():
            try:
                # Get message from queue with timeout
                log_record = self.log_queue.get(timeout=0.1)
                
                if log_record is None:  # Shutdown signal
                    break
                
                # Write the log record
                logger_name, record = log_record
                if logger_name in self.loggers:
                    self.loggers[logger_name].handle(record)
                
            except Exception as e:
                # Queue.get timeout is normal - just continue
                if "Empty" not in str(type(e).__name__):
                    print(f"ERROR in async writer: {e}", file=sys.stderr)
    
    def stop_async_writer(self):
        """Stop the async writer thread gracefully"""
        if not self.writer_thread:
            return
        
        self.shutdown_flag.set()
        self.log_queue.put(None)  # Signal shutdown
        
        self.writer_thread.join(timeout=2)
        if self.writer_thread.is_alive():
            self.get_logger('app').error("Async writer thread did not stop cleanly")
        else:
            self.get_logger('app').info("Async writer stopped")
    
    def log_async(self, logger_name: str, level: int, msg: str, **kwargs):
        """Queue a log message for async writing"""
        try:
            record = logging.LogRecord(
                name=f"blast.{logger_name}",
                level=level,
                pathname="",
                lineno=0,
                msg=msg,
                args=(),
                exc_info=None
            )
            
            # Add context to record
            for key, value in self.context.items():
                setattr(record, key, value)
            for key, value in kwargs.items():
                setattr(record, key, value)
            
            self.log_queue.put_nowait((logger_name, record))
            
        except Full:
            # Queue is full - fail fast
            self.get_logger('errors').error(f"Log queue full! Dropping message: {msg}")
            raise RuntimeError("Log queue is full - system may be overloaded")
    
    @property
    def is_initialized(self) -> bool:
        """Check if logger manager is initialized"""
        return self._is_initialized


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        """Format log record as JSON"""
        log_obj = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add any extra attributes
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'message', 'pathname', 'process', 'processName', 'relativeCreated',
                          'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info']:
                try:
                    # Ensure value is JSON serializable
                    json.dumps(value)
                    log_obj[key] = value
                except (TypeError, ValueError):
                    log_obj[key] = str(value)
        
        # Add exception info if present
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_obj)


# Module-level function for easy access
_manager = None

def get_logger_manager() -> LoggerManager:
    """Get the singleton logger manager instance"""
    global _manager
    if _manager is None:
        _manager = LoggerManager()
    return _manager