"""
BLAST Serial Logger - Serial communication monitoring and logging
"""

import logging
import time
import json
from typing import Dict, Any, Optional
from collections import deque


class SerialLogger:
    """Handles detailed logging of serial port communication"""
    
    def __init__(self, logger_manager):
        self.logger_manager = logger_manager
        self.logger = logging.getLogger('blast.serial')
        
        # Statistics tracking
        self.stats = {
            'bytes_read': 0,
            'bytes_written': 0,
            'successful_reads': 0,
            'failed_reads': 0,
            'successful_writes': 0,
            'failed_writes': 0,
            'connection_attempts': 0,
            'connection_failures': 0,
            'data_packets_parsed': 0,
            'parse_errors': 0
        }
        
        # Keep recent activity in memory for debugging
        self.recent_activity = deque(maxlen=100)
        self.current_port = None
        self.connection_start_time = None
    
    def log_connection_attempt(self, port: str, baudrate: int):
        """Log serial connection attempt"""
        self.current_port = port
        self.stats['connection_attempts'] += 1
        
        self.logger_manager.log_serial(
            direction='connection',
            data=f"Attempting connection to {port} at {baudrate} baud",
            port=port,
            success=True
        )
        
        self.recent_activity.append({
            'timestamp': time.time(),
            'action': 'connection_attempt',
            'port': port,
            'baudrate': baudrate
        })
    
    def log_connection_success(self, port: str, baudrate: int):
        """Log successful serial connection"""
        self.connection_start_time = time.time()
        
        self.logger_manager.log_serial(
            direction='connection',
            data=f"Successfully connected to {port} at {baudrate} baud",
            port=port,
            success=True
        )
        
        self.logger.info(f"Serial connection established: {port}@{baudrate}")
        
        self.recent_activity.append({
            'timestamp': time.time(),
            'action': 'connection_success',
            'port': port,
            'baudrate': baudrate
        })
    
    def log_connection_failure(self, port: str, baudrate: int, error: str):
        """Log failed serial connection"""
        self.stats['connection_failures'] += 1
        
        self.logger_manager.log_serial(
            direction='connection',
            data=f"Failed to connect to {port} at {baudrate} baud",
            port=port,
            success=False,
            error=error
        )
        
        self.logger.error(f"Serial connection failed: {port}@{baudrate} - {error}")
        
        self.recent_activity.append({
            'timestamp': time.time(),
            'action': 'connection_failure',
            'port': port,
            'baudrate': baudrate,
            'error': error
        })
    
    def log_data_read(self, raw_data: str, port: str, success: bool = True, error: Optional[str] = None):
        """Log data read from serial port"""
        if success:
            self.stats['successful_reads'] += 1
            self.stats['bytes_read'] += len(raw_data) if raw_data else 0
        else:
            self.stats['failed_reads'] += 1
        
        # Only log non-empty reads or errors
        if raw_data or error:
            self.logger_manager.log_serial(
                direction='read',
                data=raw_data or '',
                port=port,
                success=success,
                error=error
            )
        
        self.recent_activity.append({
            'timestamp': time.time(),
            'action': 'data_read',
            'data_length': len(raw_data) if raw_data else 0,
            'success': success,
            'error': error
        })
    
    def log_data_write(self, data: str, port: str, success: bool = True, error: Optional[str] = None):
        """Log data written to serial port"""
        if success:
            self.stats['successful_writes'] += 1
            self.stats['bytes_written'] += len(data)
        else:
            self.stats['failed_writes'] += 1
        
        self.logger_manager.log_serial(
            direction='write',
            data=data,
            port=port,
            success=success,
            error=error
        )
        
        self.logger.debug(f"Serial write: {len(data)} bytes {'successful' if success else 'failed'}")
        
        self.recent_activity.append({
            'timestamp': time.time(),
            'action': 'data_write',
            'data_length': len(data),
            'success': success,
            'error': error
        })
    
    def log_data_parse(self, raw_data: str, parsed_data: Dict, success: bool = True, error: Optional[str] = None):
        """Log data parsing results"""
        if success:
            self.stats['data_packets_parsed'] += 1
        else:
            self.stats['parse_errors'] += 1
        
        # Log parsing details for debugging
        parse_info = {
            'raw_length': len(raw_data),
            'parsed_keys': list(parsed_data.keys()) if parsed_data else [],
            'parse_time': time.time()
        }
        
        if success:
            self.logger.debug(f"Parsed data packet: {parse_info}")
        else:
            self.logger.warning(f"Failed to parse data: {raw_data[:100]}... Error: {error}")
        
        self.recent_activity.append({
            'timestamp': time.time(),
            'action': 'data_parse',
            'success': success,
            'error': error,
            **parse_info
        })
    
    def log_port_state(self, port: str, state: str, details: Dict = None):
        """Log serial port state changes"""
        self.logger_manager.log_serial(
            direction='state',
            data=f"Port state: {state}",
            port=port,
            success=True
        )
        
        self.logger.info(f"Serial port {port} state: {state}")
        
        self.recent_activity.append({
            'timestamp': time.time(),
            'action': 'port_state',
            'state': state,
            'details': details or {}
        })
    
    def log_disconnection(self, port: str, reason: str = "normal"):
        """Log serial disconnection"""
        uptime = None
        if self.connection_start_time:
            uptime = time.time() - self.connection_start_time
        
        self.logger_manager.log_serial(
            direction='disconnection',
            data=f"Disconnected from {port} - {reason}",
            port=port,
            success=True
        )
        
        self.logger.info(f"Serial disconnected: {port} ({reason}) - Uptime: {uptime:.1f}s" if uptime else f"Serial disconnected: {port} ({reason})")
        
        self.recent_activity.append({
            'timestamp': time.time(),
            'action': 'disconnection',
            'reason': reason,
            'uptime': uptime
        })
        
        self.connection_start_time = None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive serial communication statistics"""
        current_time = time.time()
        uptime = current_time - self.connection_start_time if self.connection_start_time else 0
        
        return {
            **self.stats,
            'current_port': self.current_port,
            'connection_uptime': uptime,
            'connection_uptime_formatted': f"{uptime/3600:.1f}h" if uptime > 0 else "Not connected",
            'bytes_per_second_read': self.stats['bytes_read'] / uptime if uptime > 0 else 0,
            'bytes_per_second_write': self.stats['bytes_written'] / uptime if uptime > 0 else 0,
            'read_success_rate': self.stats['successful_reads'] / max(1, self.stats['successful_reads'] + self.stats['failed_reads']),
            'write_success_rate': self.stats['successful_writes'] / max(1, self.stats['successful_writes'] + self.stats['failed_writes']),
            'parse_success_rate': self.stats['data_packets_parsed'] / max(1, self.stats['data_packets_parsed'] + self.stats['parse_errors'])
        }
    
    def get_recent_activity(self, limit: int = 50) -> list:
        """Get recent serial activity for debugging"""
        return list(self.recent_activity)[-limit:]
    
    def log_health_check(self):
        """Log periodic health check of serial communication"""
        stats = self.get_stats()
        
        # Check for potential issues
        issues = []
        if stats['parse_success_rate'] < 0.95:
            issues.append(f"Low parse success rate: {stats['parse_success_rate']:.2%}")
        if stats['read_success_rate'] < 0.98:
            issues.append(f"Low read success rate: {stats['read_success_rate']:.2%}")
        
        health_status = "healthy" if not issues else "degraded"
        
        self.logger_manager.log_serial(
            direction='health_check',
            data=f"Serial health: {health_status}",
            port=self.current_port or 'unknown',
            success=len(issues) == 0,
            error="; ".join(issues) if issues else None
        )
        
        if issues:
            self.logger.warning(f"Serial health issues detected: {'; '.join(issues)}")
        else:
            self.logger.debug("Serial health check: OK")