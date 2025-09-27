"""
SerialLogger: Log serial communication with hex dumps and protocol analysis
Provides detailed logging for debugging serial protocol issues
"""

import time
import json
from collections import deque
from datetime import datetime
from typing import Optional, Dict, Any
import binascii


class SerialLogger:
    """Log all serial communication for debugging"""
    
    def __init__(self, buffer_size: int = 1000):
        """Initialize serial logger
        
        Args:
            buffer_size: Number of entries to keep in circular buffer
        """
        # Get logger
        from app.logging.logger_manager import get_logger_manager
        self.logger = get_logger_manager().get_logger('serial')
        self.debug_logger = get_logger_manager().get_logger('app')
        
        # Circular buffer for recent communications
        self.tx_buffer = deque(maxlen=buffer_size)
        self.rx_buffer = deque(maxlen=buffer_size)
        
        # Message sequence tracking
        self.tx_sequence = 0
        self.rx_sequence = 0
        
        # Timing tracking
        self.last_tx_time = None
        self.last_rx_time = None
        
        # Protocol statistics
        self.stats = {
            'total_tx': 0,
            'total_rx': 0,
            'json_parse_errors': 0,
            'malformed_messages': 0,
            'checksum_errors': 0,
            'timeouts': 0
        }
        
        self.logger.info(f"SerialLogger initialized with buffer size {buffer_size}")
    
    def log_sent(self, data: bytes, command: Optional[str] = None):
        """Log data sent to serial device
        
        Args:
            data: Raw bytes sent
            command: Optional command description
        """
        self.tx_sequence += 1
        self.stats['total_tx'] += 1
        
        entry = {
            'sequence': self.tx_sequence,
            'timestamp': datetime.utcnow().isoformat(),
            'time_since_last': self._time_since_last_tx(),
            'command': command,
            'data_hex': binascii.hexlify(data).decode('ascii'),
            'data_ascii': self._safe_ascii(data),
            'length': len(data)
        }
        
        # Add to buffer
        self.tx_buffer.append(entry)
        
        # Log to file
        log_msg = (
            f"TX[{self.tx_sequence}] "
            f"{command or 'DATA'} "
            f"({len(data)} bytes): "
            f"HEX={entry['data_hex'][:100]} "  # First 100 chars of hex
            f"ASCII={entry['data_ascii'][:50]}"  # First 50 chars of ASCII
        )
        
        self.logger.info(log_msg)
        
        # Update timing
        self.last_tx_time = time.time()
    
    def log_received(self, data: bytes, parsed: Optional[Dict] = None):
        """Log data received from serial device
        
        Args:
            data: Raw bytes received
            parsed: Optional parsed data structure
        """
        self.rx_sequence += 1
        self.stats['total_rx'] += 1
        
        # Calculate timing
        response_time = None
        if self.last_tx_time:
            response_time = (time.time() - self.last_tx_time) * 1000  # ms
        
        entry = {
            'sequence': self.rx_sequence,
            'timestamp': datetime.utcnow().isoformat(),
            'time_since_last': self._time_since_last_rx(),
            'response_time_ms': response_time,
            'data_hex': binascii.hexlify(data).decode('ascii'),
            'data_ascii': self._safe_ascii(data),
            'length': len(data),
            'parsed': parsed,
            'valid': parsed is not None
        }
        
        # Add to buffer
        self.rx_buffer.append(entry)
        
        # Log to file
        log_msg = (
            f"RX[{self.rx_sequence}] "
            f"({len(data)} bytes"
        )
        
        if response_time:
            log_msg += f", RT={response_time:.1f}ms"
        
        log_msg += f"): HEX={entry['data_hex'][:100]}"
        
        if parsed:
            log_msg += f" PARSED=OK"
        else:
            log_msg += f" PARSED=FAIL"
        
        self.logger.info(log_msg)
        
        # Log parsed data at debug level
        if parsed:
            self.logger.debug(f"RX[{self.rx_sequence}] parsed: {json.dumps(parsed, default=str)[:200]}")
        
        # Update timing
        self.last_rx_time = time.time()
    
    def log_timeout(self, duration: float, context: Optional[str] = None):
        """Log a timeout event
        
        Args:
            duration: Timeout duration in seconds
            context: Optional context about what timed out
        """
        self.stats['timeouts'] += 1
        
        log_msg = f"TIMEOUT after {duration:.1f}s"
        if context:
            log_msg += f": {context}"
        
        self.logger.warning(log_msg)
    
    def log_reconnection(self, attempts: int, success: bool):
        """Log reconnection attempt
        
        Args:
            attempts: Number of attempts made
            success: Whether reconnection succeeded
        """
        if success:
            self.logger.info(f"RECONNECTED after {attempts} attempts")
        else:
            self.logger.error(f"RECONNECTION FAILED after {attempts} attempts")
    
    def log_protocol_error(self, error_type: str, data: bytes, error: Exception):
        """Log protocol-level errors
        
        Args:
            error_type: Type of error (json_parse, checksum, etc)
            data: Raw data that caused the error
            error: The exception
        """
        if error_type == 'json_parse':
            self.stats['json_parse_errors'] += 1
        elif error_type == 'malformed':
            self.stats['malformed_messages'] += 1
        elif error_type == 'checksum':
            self.stats['checksum_errors'] += 1
        
        self.logger.error(
            f"PROTOCOL ERROR [{error_type}]: {str(error)} | "
            f"Data: {self._safe_ascii(data)[:100]}"
        )
    
    def analyze_protocol(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Analyze raw data for protocol patterns
        
        Args:
            data: Raw data to analyze
            
        Returns:
            Analysis results or None if no patterns found
        """
        analysis = {
            'length': len(data),
            'starts_with': data[:4].hex() if len(data) >= 4 else data.hex(),
            'ends_with': data[-4:].hex() if len(data) >= 4 else data.hex(),
            'contains_json': False,
            'line_endings': None,
            'potential_format': 'unknown'
        }
        
        # Check for JSON
        try:
            decoded = data.decode('utf-8', errors='ignore')
            if '{' in decoded and '}' in decoded:
                analysis['contains_json'] = True
                analysis['potential_format'] = 'json'
                
                # Try to parse JSON
                start = decoded.index('{')
                end = decoded.rindex('}') + 1
                json_str = decoded[start:end]
                parsed = json.loads(json_str)
                analysis['parsed_json'] = parsed
        except:
            pass
        
        # Check line endings
        if b'\r\n' in data:
            analysis['line_endings'] = 'CRLF'
        elif b'\n' in data:
            analysis['line_endings'] = 'LF'
        elif b'\r' in data:
            analysis['line_endings'] = 'CR'
        
        # Check for common protocols
        if data.startswith(b'$'):
            analysis['potential_format'] = 'NMEA'
        elif data.startswith(b'AT'):
            analysis['potential_format'] = 'AT_COMMAND'
        elif b'\x02' in data and b'\x03' in data:
            analysis['potential_format'] = 'STX_ETX'
        
        return analysis
    
    def get_recent_communications(self, count: int = 10) -> Dict[str, Any]:
        """Get recent TX/RX communications
        
        Args:
            count: Number of recent entries to return
            
        Returns:
            Dictionary with recent TX and RX entries
        """
        return {
            'tx': list(self.tx_buffer)[-count:],
            'rx': list(self.rx_buffer)[-count:],
            'stats': self.stats
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get communication statistics
        
        Returns:
            Dictionary with statistics
        """
        stats = self.stats.copy()
        
        # Calculate error rate
        if stats['total_rx'] > 0:
            error_count = (
                stats['json_parse_errors'] + 
                stats['malformed_messages'] + 
                stats['checksum_errors']
            )
            stats['error_rate'] = (error_count / stats['total_rx']) * 100
        else:
            stats['error_rate'] = 0.0
        
        # Add timing stats
        if self.rx_buffer:
            response_times = [
                entry.get('response_time_ms', 0) 
                for entry in self.rx_buffer 
                if entry.get('response_time_ms')
            ]
            if response_times:
                stats['avg_response_time_ms'] = sum(response_times) / len(response_times)
                stats['max_response_time_ms'] = max(response_times)
                stats['min_response_time_ms'] = min(response_times)
        
        return stats
    
    def dump_to_file(self, filename: str):
        """Dump recent communications to a file for analysis
        
        Args:
            filename: Output filename
        """
        try:
            data = {
                'timestamp': datetime.utcnow().isoformat(),
                'tx_buffer': list(self.tx_buffer),
                'rx_buffer': list(self.rx_buffer),
                'statistics': self.get_statistics()
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            self.debug_logger.info(f"Serial communications dumped to {filename}")
            
        except Exception as e:
            self.debug_logger.error(f"Failed to dump serial data: {e}")
    
    def _safe_ascii(self, data: bytes) -> str:
        """Convert bytes to safe ASCII representation
        
        Args:
            data: Raw bytes
            
        Returns:
            ASCII string with non-printable chars replaced
        """
        result = []
        for byte in data:
            if 32 <= byte <= 126:  # Printable ASCII
                result.append(chr(byte))
            else:
                result.append(f'\\x{byte:02x}')
        return ''.join(result)
    
    def _time_since_last_tx(self) -> Optional[float]:
        """Calculate time since last TX in ms"""
        if self.last_tx_time:
            return (time.time() - self.last_tx_time) * 1000
        return None
    
    def _time_since_last_rx(self) -> Optional[float]:
        """Calculate time since last RX in ms"""
        if self.last_rx_time:
            return (time.time() - self.last_rx_time) * 1000
        return None


# Global instance
_serial_logger = None

def get_serial_logger() -> SerialLogger:
    """Get the global serial logger instance"""
    global _serial_logger
    if _serial_logger is None:
        _serial_logger = SerialLogger()
    return _serial_logger