"""
ErrorRecovery: Implement retry strategies and error handling
Uses strategy pattern for different error types with exponential backoff
"""

import time
import random
from typing import Dict, Callable, Optional, Any
from enum import Enum
from dataclasses import dataclass


class ErrorType(Enum):
    """Types of errors that can be recovered"""
    SERIAL_TIMEOUT = "serial_timeout"
    SERIAL_DISCONNECT = "serial_disconnect"
    FILE_WRITE = "file_write"
    NETWORK = "network"
    MEMORY = "memory"
    GENERIC = "generic"


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    initial_delay: float = 0.1
    max_delay: float = 10.0
    exponential_base: float = 2.0
    jitter: bool = True


class ErrorRecovery:
    """Handle errors with configurable recovery strategies"""
    
    def __init__(self):
        """Initialize error recovery system"""
        # Get logger
        from app.logging.logger_manager import get_logger_manager
        from app.logging.event_logger import get_event_logger
        
        self.logger = get_logger_manager().get_logger('app')
        self.error_logger = get_logger_manager().get_logger('errors')
        self.event_logger = get_event_logger()
        
        # Define recovery strategies
        self.strategies: Dict[ErrorType, Callable] = {
            ErrorType.SERIAL_TIMEOUT: self._handle_serial_timeout,
            ErrorType.SERIAL_DISCONNECT: self._handle_serial_disconnect,
            ErrorType.FILE_WRITE: self._handle_file_write,
            ErrorType.NETWORK: self._handle_network_error,
            ErrorType.MEMORY: self._handle_memory_error,
            ErrorType.GENERIC: self._handle_generic_error
        }
        
        # Retry configurations per error type
        self.retry_configs: Dict[ErrorType, RetryConfig] = {
            ErrorType.SERIAL_TIMEOUT: RetryConfig(max_attempts=5, initial_delay=0.5),
            ErrorType.SERIAL_DISCONNECT: RetryConfig(max_attempts=3, initial_delay=1.0),
            ErrorType.FILE_WRITE: RetryConfig(max_attempts=3, initial_delay=0.1),
            ErrorType.NETWORK: RetryConfig(max_attempts=5, initial_delay=0.5),
            ErrorType.MEMORY: RetryConfig(max_attempts=2, initial_delay=2.0),
            ErrorType.GENERIC: RetryConfig(max_attempts=3, initial_delay=0.5)
        }
        
        # Track error counts for circuit breaker pattern
        self.error_counts: Dict[str, int] = {}
        self.circuit_open: Dict[str, bool] = {}
        self.circuit_open_until: Dict[str, float] = {}
        
        self.logger.info("ErrorRecovery system initialized")
    
    def recover(self, error: Exception, error_type: ErrorType = ErrorType.GENERIC, 
                context: Optional[Dict] = None) -> bool:
        """Attempt to recover from an error
        
        Args:
            error: The exception that occurred
            error_type: Type of error for strategy selection
            context: Additional context about the error
            
        Returns:
            True if recovery succeeded, False otherwise
        """
        # Check circuit breaker
        if self._is_circuit_open(error_type):
            self.logger.warning(f"Circuit breaker open for {error_type.value}")
            return False
        
        # Get recovery strategy
        strategy = self.strategies.get(error_type, self._handle_generic_error)
        
        # Log the error
        self.error_logger.error(
            f"Error occurred: {error_type.value} - {str(error)}",
            exc_info=True
        )
        
        # Execute recovery strategy
        try:
            success = strategy(error, context or {})
            
            if success:
                self._reset_error_count(error_type)
                self.logger.info(f"Successfully recovered from {error_type.value}")
            else:
                self._increment_error_count(error_type)
                
            return success
            
        except Exception as recovery_error:
            self.error_logger.error(
                f"Recovery failed for {error_type.value}: {recovery_error}",
                exc_info=True
            )
            self._increment_error_count(error_type)
            return False
    
    def retry_with_backoff(self, func: Callable, error_type: ErrorType = ErrorType.GENERIC,
                          *args, **kwargs) -> Optional[Any]:
        """Execute a function with retry and exponential backoff
        
        Args:
            func: Function to execute
            error_type: Type of error expected
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result from function or None if all retries failed
        """
        config = self.retry_configs[error_type]
        last_exception = None
        
        for attempt in range(config.max_attempts):
            try:
                # Try to execute the function
                result = func(*args, **kwargs)
                
                # Success - reset error count
                if attempt > 0:
                    self.logger.info(f"Succeeded on retry {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Log retry attempt
                self.logger.warning(
                    f"Attempt {attempt + 1}/{config.max_attempts} failed: {str(e)}"
                )
                
                # Check if we should retry
                if attempt < config.max_attempts - 1:
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.initial_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )
                    
                    # Add jitter if configured
                    if config.jitter:
                        delay *= (0.5 + random.random())
                    
                    self.logger.info(f"Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                else:
                    # Final attempt failed
                    self.error_logger.error(
                        f"All {config.max_attempts} attempts failed for {error_type.value}",
                        exc_info=True
                    )
        
        # All retries exhausted
        self.recover(last_exception, error_type)
        return None
    
    def _handle_serial_timeout(self, error: Exception, context: Dict) -> bool:
        """Handle serial timeout errors"""
        self.logger.info("Attempting to recover from serial timeout")
        
        # Log event
        self.event_logger.log_connection_event('error', {
            'error_type': 'timeout',
            'port': context.get('port', 'unknown'),
            'message': str(error)
        })
        
        # For timeouts, we typically just retry
        # The retry is handled by retry_with_backoff
        return True
    
    def _handle_serial_disconnect(self, error: Exception, context: Dict) -> bool:
        """Handle serial disconnection"""
        self.logger.warning("Serial device disconnected")
        
        # Log event
        self.event_logger.log_connection_event('disconnect', {
            'port': context.get('port', 'unknown'),
            'error': str(error)
        })
        
        # Try to reconnect
        if 'reconnect_func' in context:
            try:
                context['reconnect_func']()
                self.event_logger.log_connection_event('reconnect', {
                    'port': context.get('port', 'unknown')
                })
                return True
            except Exception as e:
                self.error_logger.error(f"Reconnection failed: {e}")
                
                # Fall back to simulator mode if available
                if 'fallback_func' in context:
                    context['fallback_func']()
                    self.event_logger.log_mode_change('serial', 'simulator', 
                                                      f"Serial error: {str(error)}")
                    return True
        
        return False
    
    def _handle_file_write(self, error: Exception, context: Dict) -> bool:
        """Handle file write errors"""
        self.logger.warning(f"File write error: {error}")
        
        # Check for disk space
        if "No space left" in str(error) or "ENOSPC" in str(error):
            self.error_logger.critical("Disk full - cannot write logs!")
            
            # Try to clean up old logs
            if 'cleanup_func' in context:
                try:
                    context['cleanup_func']()
                    return True
                except:
                    pass
            
            return False
        
        # For other file errors, buffer the data
        if 'buffer_func' in context:
            context['buffer_func'](context.get('data'))
            self.logger.info("Data buffered for later write")
            return True
        
        return False
    
    def _handle_network_error(self, error: Exception, context: Dict) -> bool:
        """Handle network-related errors"""
        self.logger.warning(f"Network error: {error}")
        
        # For network errors, exponential backoff is usually best
        # This is handled by retry_with_backoff
        return True
    
    def _handle_memory_error(self, error: Exception, context: Dict) -> bool:
        """Handle memory errors"""
        self.error_logger.critical(f"Memory error: {error}")
        
        # Try to free memory
        if 'cleanup_func' in context:
            try:
                context['cleanup_func']()
                
                # Force garbage collection
                import gc
                gc.collect()
                
                return True
            except:
                pass
        
        # Memory errors are usually fatal
        return False
    
    def _handle_generic_error(self, error: Exception, context: Dict) -> bool:
        """Handle generic errors"""
        self.logger.warning(f"Generic error recovery for: {error}")
        
        # For generic errors, we can only retry
        return False
    
    def _increment_error_count(self, error_type: ErrorType):
        """Increment error count for circuit breaker"""
        key = error_type.value
        self.error_counts[key] = self.error_counts.get(key, 0) + 1
        
        # Open circuit if too many errors
        if self.error_counts[key] >= 10:  # Threshold
            self.circuit_open[key] = True
            self.circuit_open_until[key] = time.time() + 60  # Open for 60 seconds
            self.logger.warning(f"Circuit breaker opened for {key}")
    
    def _reset_error_count(self, error_type: ErrorType):
        """Reset error count after successful recovery"""
        key = error_type.value
        self.error_counts[key] = 0
        self.circuit_open[key] = False
    
    def _is_circuit_open(self, error_type: ErrorType) -> bool:
        """Check if circuit breaker is open"""
        key = error_type.value
        
        if key in self.circuit_open and self.circuit_open[key]:
            # Check if circuit should be closed
            if time.time() >= self.circuit_open_until.get(key, 0):
                self.circuit_open[key] = False
                self.logger.info(f"Circuit breaker closed for {key}")
                return False
            return True
        
        return False


# Global instance
_recovery = None

def get_error_recovery() -> ErrorRecovery:
    """Get the global error recovery instance"""
    global _recovery
    if _recovery is None:
        _recovery = ErrorRecovery()
    return _recovery