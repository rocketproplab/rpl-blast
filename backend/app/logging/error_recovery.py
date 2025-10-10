"""
BLAST Error Recovery - Automatic error detection and recovery mechanisms
"""

import logging
import time
import asyncio
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict


class ErrorType(Enum):
    """Types of errors that can be recovered from"""
    SERIAL_CONNECTION = "serial_connection"
    DATA_PARSING = "data_parsing"
    API_TIMEOUT = "api_timeout"
    MEMORY_LIMIT = "memory_limit"
    DATA_STALE = "data_stale"
    CALIBRATION_ERROR = "calibration_error"
    FILE_WRITE_ERROR = "file_write_error"


@dataclass
class RecoveryAction:
    """Defines a recovery action for a specific error type"""
    error_type: ErrorType
    action_name: str
    action_func: Callable
    max_attempts: int = 3
    cooldown_seconds: int = 30
    escalation_func: Optional[Callable] = None


class ErrorRecovery:
    """Handles automatic error detection and recovery"""
    
    def __init__(self, logger_manager):
        self.logger_manager = logger_manager
        self.logger = logging.getLogger('blast.error_recovery')
        
        # Recovery tracking
        self.recovery_attempts = defaultdict(list)  # error_type -> [timestamps]
        self.successful_recoveries = defaultdict(int)
        self.failed_recoveries = defaultdict(int)
        self.escalated_errors = defaultdict(int)
        
        # Recovery actions registry
        self.recovery_actions: Dict[ErrorType, RecoveryAction] = {}
        
        # System state for recovery decisions
        self.system_healthy = True
        self.last_data_timestamp = time.time()
        self.critical_errors_count = 0
        
        # Setup default recovery actions
        self._setup_default_recovery_actions()
    
    def _setup_default_recovery_actions(self):
        """Setup default recovery actions for common error types"""
        
        # Serial connection recovery
        self.register_recovery_action(
            ErrorType.SERIAL_CONNECTION,
            "reconnect_serial",
            self._recover_serial_connection,
            max_attempts=5,
            cooldown_seconds=10
        )
        
        # Data parsing recovery
        self.register_recovery_action(
            ErrorType.DATA_PARSING,
            "reset_parser",
            self._recover_data_parsing,
            max_attempts=3,
            cooldown_seconds=5
        )
        
        # API timeout recovery
        self.register_recovery_action(
            ErrorType.API_TIMEOUT,
            "restart_reader",
            self._recover_api_timeout,
            max_attempts=2,
            cooldown_seconds=15
        )
        
        # File write error recovery
        self.register_recovery_action(
            ErrorType.FILE_WRITE_ERROR,
            "check_disk_space",
            self._recover_file_write,
            max_attempts=2,
            cooldown_seconds=30
        )
    
    def register_recovery_action(self, error_type: ErrorType, action_name: str, 
                                action_func: Callable, max_attempts: int = 3, 
                                cooldown_seconds: int = 30, escalation_func: Optional[Callable] = None):
        """Register a recovery action for an error type"""
        self.recovery_actions[error_type] = RecoveryAction(
            error_type=error_type,
            action_name=action_name,
            action_func=action_func,
            max_attempts=max_attempts,
            cooldown_seconds=cooldown_seconds,
            escalation_func=escalation_func
        )
        
        self.logger.info(f"Registered recovery action '{action_name}' for {error_type.value}")
    
    async def handle_error(self, error_type: ErrorType, error_message: str, 
                          context: Optional[Dict] = None) -> bool:
        """Handle an error with automatic recovery"""
        
        self.logger.warning(f"Error detected: {error_type.value} - {error_message}")
        
        # Log the error
        self.logger_manager.log_error(
            error_type=error_type.value,
            message=error_message,
            context=context
        )
        
        # Check if we have a recovery action
        if error_type not in self.recovery_actions:
            self.logger.error(f"No recovery action registered for {error_type.value}")
            return False
        
        recovery_action = self.recovery_actions[error_type]
        
        # Check cooldown and attempt limits
        if not self._can_attempt_recovery(error_type, recovery_action):
            self.logger.warning(f"Recovery attempt blocked due to cooldown or max attempts for {error_type.value}")
            return False
        
        # Record recovery attempt
        self.recovery_attempts[error_type].append(time.time())
        
        # Attempt recovery
        try:
            self.logger.info(f"Attempting recovery: {recovery_action.action_name} for {error_type.value}")
            
            success = await self._execute_recovery_action(recovery_action, context)
            
            if success:
                self.successful_recoveries[error_type] += 1
                self.logger.info(f"Recovery successful: {recovery_action.action_name}")
                
                # Log successful recovery event
                self.logger_manager.log_event(
                    'error_recovery',
                    f"Successfully recovered from {error_type.value}",
                    {
                        'error_type': error_type.value,
                        'recovery_action': recovery_action.action_name,
                        'attempt_number': len(self.recovery_attempts[error_type])
                    }
                )
                
                return True
            else:
                self.failed_recoveries[error_type] += 1
                self.logger.error(f"Recovery failed: {recovery_action.action_name}")
                
                # Check if we should escalate
                if self._should_escalate(error_type, recovery_action):
                    await self._escalate_error(error_type, error_message, recovery_action)
                
                return False
                
        except Exception as e:
            self.failed_recoveries[error_type] += 1
            self.logger.error(f"Recovery action failed with exception: {e}")
            return False
    
    def _can_attempt_recovery(self, error_type: ErrorType, recovery_action: RecoveryAction) -> bool:
        """Check if recovery can be attempted based on limits and cooldown"""
        
        attempts = self.recovery_attempts[error_type]
        
        # Check max attempts
        if len(attempts) >= recovery_action.max_attempts:
            # Check if cooldown period has passed since last attempt
            if attempts and (time.time() - attempts[-1]) < recovery_action.cooldown_seconds:
                return False
            
            # Reset attempts if cooldown has passed
            if attempts and (time.time() - attempts[-1]) >= recovery_action.cooldown_seconds:
                self.recovery_attempts[error_type] = []
                return True
                
            return False
        
        # Check cooldown since last attempt
        if attempts and (time.time() - attempts[-1]) < recovery_action.cooldown_seconds:
            return False
        
        return True
    
    async def _execute_recovery_action(self, recovery_action: RecoveryAction, context: Optional[Dict]) -> bool:
        """Execute a recovery action"""
        try:
            if asyncio.iscoroutinefunction(recovery_action.action_func):
                return await recovery_action.action_func(context)
            else:
                return recovery_action.action_func(context)
        except Exception as e:
            self.logger.error(f"Recovery action execution failed: {e}")
            return False
    
    def _should_escalate(self, error_type: ErrorType, recovery_action: RecoveryAction) -> bool:
        """Determine if error should be escalated"""
        attempts = len(self.recovery_attempts[error_type])
        return attempts >= recovery_action.max_attempts and recovery_action.escalation_func is not None
    
    async def _escalate_error(self, error_type: ErrorType, error_message: str, recovery_action: RecoveryAction):
        """Escalate error when recovery fails"""
        self.escalated_errors[error_type] += 1
        self.critical_errors_count += 1
        
        self.logger.critical(f"ESCALATED ERROR: {error_type.value} - {error_message}")
        
        # Log escalation event
        self.logger_manager.log_event(
            'error_escalation',
            f"Error escalated: {error_type.value}",
            {
                'error_type': error_type.value,
                'original_message': error_message,
                'failed_recovery_attempts': len(self.recovery_attempts[error_type])
            }
        )
        
        # Execute escalation action if available
        if recovery_action.escalation_func:
            try:
                if asyncio.iscoroutinefunction(recovery_action.escalation_func):
                    await recovery_action.escalation_func(error_type, error_message)
                else:
                    recovery_action.escalation_func(error_type, error_message)
            except Exception as e:
                self.logger.error(f"Escalation action failed: {e}")
    
    # Default recovery action implementations
    
    async def _recover_serial_connection(self, context: Optional[Dict]) -> bool:
        """Attempt to recover serial connection"""
        self.logger.info("Attempting serial connection recovery")
        
        # This would typically:
        # 1. Close existing connection
        # 2. Wait a moment
        # 3. Attempt to reconnect
        # For now, we'll simulate this
        
        await asyncio.sleep(2)  # Simulate reconnection delay
        
        # In real implementation, this would call the actual serial reconnection code
        # return await serial_source.reconnect()
        
        # Simulate success/failure
        import random
        success = random.random() > 0.3  # 70% success rate
        
        if success:
            self.logger.info("Serial connection recovery successful")
        else:
            self.logger.warning("Serial connection recovery failed")
            
        return success
    
    async def _recover_data_parsing(self, context: Optional[Dict]) -> bool:
        """Attempt to recover from data parsing errors"""
        self.logger.info("Attempting data parsing recovery")
        
        # This would typically:
        # 1. Clear parser buffers
        # 2. Reset parsing state
        # 3. Skip malformed data
        
        await asyncio.sleep(1)
        
        # Simulate parser reset
        success = True  # Parsing recovery usually succeeds
        
        if success:
            self.logger.info("Data parsing recovery successful")
        
        return success
    
    async def _recover_api_timeout(self, context: Optional[Dict]) -> bool:
        """Attempt to recover from API timeouts"""
        self.logger.info("Attempting API timeout recovery")
        
        # This would typically:
        # 1. Cancel pending requests
        # 2. Restart data reader task
        # 3. Check system load
        
        await asyncio.sleep(1)
        
        # Simulate timeout recovery
        import random
        success = random.random() > 0.2  # 80% success rate
        
        if success:
            self.logger.info("API timeout recovery successful")
        
        return success
    
    async def _recover_file_write(self, context: Optional[Dict]) -> bool:
        """Attempt to recover from file write errors"""
        self.logger.info("Attempting file write recovery")
        
        # This would typically:
        # 1. Check disk space
        # 2. Check file permissions
        # 3. Rotate logs if needed
        # 4. Try alternative log location
        
        await asyncio.sleep(1)
        
        # Simulate file recovery
        import random
        success = random.random() > 0.4  # 60% success rate
        
        if success:
            self.logger.info("File write recovery successful")
        
        return success
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get comprehensive recovery statistics"""
        total_attempts = sum(len(attempts) for attempts in self.recovery_attempts.values())
        total_successful = sum(self.successful_recoveries.values())
        total_failed = sum(self.failed_recoveries.values())
        total_escalated = sum(self.escalated_errors.values())
        
        return {
            'total_recovery_attempts': total_attempts,
            'successful_recoveries': total_successful,
            'failed_recoveries': total_failed,
            'escalated_errors': total_escalated,
            'recovery_success_rate': total_successful / max(1, total_attempts),
            'critical_errors_count': self.critical_errors_count,
            'system_healthy': self.system_healthy,
            'by_error_type': {
                error_type.value: {
                    'attempts': len(self.recovery_attempts[error_type]),
                    'successful': self.successful_recoveries[error_type],
                    'failed': self.failed_recoveries[error_type],
                    'escalated': self.escalated_errors[error_type]
                }
                for error_type in ErrorType
            },
            'registered_actions': [
                {
                    'error_type': action.error_type.value,
                    'action_name': action.action_name,
                    'max_attempts': action.max_attempts,
                    'cooldown_seconds': action.cooldown_seconds
                }
                for action in self.recovery_actions.values()
            ]
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Get error recovery system health status"""
        stats = self.get_recovery_stats()
        
        # Determine health
        recent_escalations = sum(1 for error_type in ErrorType 
                               if self.escalated_errors[error_type] > 0)
        
        healthy = (
            self.critical_errors_count < 5 and
            recent_escalations < 3 and
            stats['recovery_success_rate'] > 0.5
        )
        
        return {
            'healthy': healthy,
            'status': 'healthy' if healthy else 'degraded',
            'critical_errors': self.critical_errors_count,
            'recent_escalations': recent_escalations,
            'recovery_success_rate': stats['recovery_success_rate'],
            'registered_recovery_actions': len(self.recovery_actions)
        }