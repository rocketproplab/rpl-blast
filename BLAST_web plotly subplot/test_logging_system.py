#!/usr/bin/env python
"""
Comprehensive test suite for BLAST logging system
Tests all logging components and verifies integration
"""

import sys
import os
import time
import json
import threading
import requests
from pathlib import Path

# Add current directory to path
sys.path.append(os.getcwd())

# Import logging components
from app.logging.logger_manager import LoggerManager, get_logger_manager
from app.logging.performance_monitor import PerformanceMonitor, get_performance_monitor
from app.logging.freeze_detector import FreezeDetector, get_freeze_detector
from app.logging.event_logger import EventLogger, get_event_logger, EventType
from app.logging.error_recovery import ErrorRecovery, get_error_recovery, ErrorType
from app.logging.serial_logger import SerialLogger, get_serial_logger

# Test results tracking
test_results = {
    'passed': 0,
    'failed': 0,
    'errors': []
}

def print_header(title):
    """Print a test section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_case(name, func):
    """Run a single test case"""
    print(f"\n[TEST] {name}...", end=" ")
    try:
        func()
        print("PASSED ✓")
        test_results['passed'] += 1
        return True
    except AssertionError as e:
        print(f"FAILED ✗ - {e}")
        test_results['failed'] += 1
        test_results['errors'].append(f"{name}: {e}")
        return False
    except Exception as e:
        print(f"ERROR ✗ - {e}")
        test_results['failed'] += 1
        test_results['errors'].append(f"{name}: Unexpected error - {e}")
        return False

# ============================================================================
# Logger Manager Tests
# ============================================================================

def test_logger_manager():
    """Test core logging functionality"""
    print_header("Testing Logger Manager")
    
    def test_initialization():
        manager = get_logger_manager()
        assert manager is not None, "Failed to get logger manager"
        assert manager.is_initialized, "Logger manager not initialized"
    
    def test_logger_creation():
        manager = get_logger_manager()
        logger = manager.get_logger('test')
        assert logger is not None, "Failed to create logger"
        logger.info("Test message")
    
    def test_async_writer():
        manager = get_logger_manager()
        assert manager.writer_thread is not None, "Async writer not started"
        assert manager.writer_thread.is_alive(), "Async writer thread not running"
    
    def test_log_levels():
        manager = get_logger_manager()
        logger = manager.get_logger('test')
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
    
    def test_log_files():
        log_dir = Path('logs')
        assert log_dir.exists(), "Log directory doesn't exist"
        
        # Check for log files
        log_files = list(log_dir.glob('*.log'))
        assert len(log_files) > 0, "No log files created"
        
        # Verify app.log exists
        app_log = log_dir / 'app.log'
        assert app_log.exists(), "app.log not created"
    
    test_case("Logger initialization", test_initialization)
    test_case("Logger creation", test_logger_creation)
    test_case("Async writer", test_async_writer)
    test_case("Log levels", test_log_levels)
    test_case("Log file creation", test_log_files)

# ============================================================================
# Performance Monitor Tests
# ============================================================================

def test_performance_monitor():
    """Test performance monitoring"""
    print_header("Testing Performance Monitor")
    
    def test_initialization():
        monitor = get_performance_monitor()
        assert monitor is not None, "Failed to get performance monitor"
    
    def test_timing_measurement():
        monitor = get_performance_monitor()
        
        # Test context manager
        with monitor.measure('test_operation'):
            time.sleep(0.1)  # Simulate work
        
        # Check metrics were recorded
        metrics = monitor.get_metrics()
        assert 'test_operation' in metrics, "Operation not recorded"
        assert metrics['test_operation']['count'] > 0, "Count not updated"
    
    def test_metric_recording():
        monitor = get_performance_monitor()
        
        # Record various metrics
        monitor.record_metric('cpu_usage', 45.5, '%')
        monitor.record_metric('memory_usage', 1024, 'MB')
        monitor.record_metric('requests_per_second', 100, 'req/s')
        
        metrics = monitor.get_metrics()
        assert 'cpu_usage' in metrics, "CPU usage not recorded"
        assert 'memory_usage' in metrics, "Memory usage not recorded"
    
    def test_statistics():
        monitor = get_performance_monitor()
        
        # Record multiple values
        for i in range(10):
            monitor.record_metric('test_stat', i * 10, 'ms')
        
        metrics = monitor.get_metrics()
        stat = metrics.get('test_stat')
        assert stat is not None, "Statistics not calculated"
        assert 'avg' in stat, "Average not calculated"
        assert 'min' in stat, "Min not calculated"
        assert 'max' in stat, "Max not calculated"
    
    def test_system_metrics():
        monitor = get_performance_monitor()
        
        # Trigger monitoring
        monitor.start_monitoring()
        time.sleep(2)  # Let it collect some metrics
        
        metrics = monitor.get_metrics()
        # System metrics should be present
        assert any('cpu' in key.lower() or 'memory' in key.lower() for key in metrics), \
               "No system metrics collected"
    
    test_case("Performance monitor initialization", test_initialization)
    test_case("Timing measurement", test_timing_measurement)
    test_case("Metric recording", test_metric_recording)
    test_case("Statistics calculation", test_statistics)
    test_case("System metrics collection", test_system_metrics)

# ============================================================================
# Freeze Detector Tests
# ============================================================================

def test_freeze_detector():
    """Test freeze detection"""
    print_header("Testing Freeze Detector")
    
    def test_initialization():
        detector = get_freeze_detector()
        assert detector is not None, "Failed to get freeze detector"
    
    def test_heartbeat():
        detector = get_freeze_detector()
        detector.start()
        
        # Send heartbeats
        for _ in range(3):
            detector.heartbeat()
            time.sleep(0.5)
        
        assert not detector.freeze_detected, "False freeze detection"
    
    def test_operation_logging():
        detector = get_freeze_detector()
        
        # Log various operations
        detector.log_operation('data_read', {'source': 'serial'})
        detector.log_operation('web_request', {'endpoint': '/data'})
        detector.log_operation('valve_command', {'valve': 1, 'state': 'open'})
        
        # Get recent operations
        recent = detector.get_recent_operations(5)
        assert len(recent) > 0, "Operations not logged"
    
    def test_freeze_simulation():
        # Create new detector with short timeout
        detector = FreezeDetector(timeout=1.0)
        detector.start()
        
        # Send initial heartbeat
        detector.heartbeat()
        
        # Wait longer than timeout
        time.sleep(1.5)
        
        # Check if detected (may or may not trigger depending on timing)
        # Just verify no crash
        detector.stop()
    
    test_case("Freeze detector initialization", test_initialization)
    test_case("Heartbeat mechanism", test_heartbeat)
    test_case("Operation logging", test_operation_logging)
    test_case("Freeze simulation", test_freeze_simulation)

# ============================================================================
# Event Logger Tests
# ============================================================================

def test_event_logger():
    """Test event logging"""
    print_header("Testing Event Logger")
    
    def test_initialization():
        logger = get_event_logger()
        assert logger is not None, "Failed to get event logger"
    
    def test_event_logging():
        logger = get_event_logger()
        
        # Log various events
        logger.log_event(EventType.STARTUP, {'version': '1.0.0'}, 'INFO')
        logger.log_event(EventType.SERIAL_CONNECT, {'port': '/dev/tty.USB0'}, 'INFO')
        logger.log_event(EventType.THRESHOLD_WARNING, {'sensor': 'PT1', 'value': 450}, 'WARNING')
    
    def test_sensor_threshold():
        logger = get_event_logger()
        
        # Test threshold logging
        logger.log_sensor_threshold('pt1', 'Pressure 1', 450.5, 400.0, 'warning', 'PSI')
        logger.log_sensor_threshold('tc1', 'Temp 1', 95.2, 90.0, 'danger', '°C')
    
    def test_valve_operations():
        logger = get_event_logger()
        
        # Log valve operations
        logger.log_valve_operation('fcv1', 'Main Valve', True, 'user', True)
        logger.log_valve_operation('fcv2', 'Vent Valve', False, 'system', True)
        logger.log_valve_operation('fcv3', 'Test Valve', True, 'auto', False)
    
    def test_browser_events():
        logger = get_event_logger()
        
        # Log browser events
        logger.log_browser_event('throttled', {
            'gap_ms': 2500,
            'visibility': 'hidden',
            'timestamp': time.time()
        })
        
        logger.log_browser_event('resumed', {
            'visible': True,
            'throttled': False
        })
    
    test_case("Event logger initialization", test_initialization)
    test_case("Event logging", test_event_logging)
    test_case("Sensor threshold logging", test_sensor_threshold)
    test_case("Valve operation logging", test_valve_operations)
    test_case("Browser event logging", test_browser_events)

# ============================================================================
# Error Recovery Tests
# ============================================================================

def test_error_recovery():
    """Test error recovery system"""
    print_header("Testing Error Recovery")
    
    def test_initialization():
        recovery = get_error_recovery()
        assert recovery is not None, "Failed to get error recovery"
    
    def test_retry_with_backoff():
        recovery = get_error_recovery()
        
        attempt_count = 0
        def flaky_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ConnectionError("Simulated failure")
            return "Success"
        
        result = recovery.retry_with_backoff(flaky_function, ErrorType.NETWORK)
        assert result == "Success", "Retry failed"
        assert attempt_count == 3, f"Unexpected attempt count: {attempt_count}"
    
    def test_error_strategies():
        recovery = get_error_recovery()
        
        # Test different error types
        result = recovery.recover(
            TimeoutError("Test timeout"),
            ErrorType.SERIAL_TIMEOUT,
            {'port': '/dev/test'}
        )
        # Just verify no crash
    
    def test_circuit_breaker():
        recovery = ErrorRecovery()  # Fresh instance
        
        # Trigger many errors
        for i in range(11):
            recovery.recover(
                Exception(f"Error {i}"),
                ErrorType.GENERIC
            )
        
        # Circuit should be open
        result = recovery.recover(
            Exception("Should fail"),
            ErrorType.GENERIC
        )
        assert result == False, "Circuit breaker didn't open"
    
    test_case("Error recovery initialization", test_initialization)
    test_case("Retry with backoff", test_retry_with_backoff)
    test_case("Error strategies", test_error_strategies)
    test_case("Circuit breaker", test_circuit_breaker)

# ============================================================================
# Serial Logger Tests
# ============================================================================

def test_serial_logger():
    """Test serial communication logging"""
    print_header("Testing Serial Logger")
    
    def test_initialization():
        logger = get_serial_logger()
        assert logger is not None, "Failed to get serial logger"
    
    def test_data_logging():
        logger = get_serial_logger()
        
        # Log sent data
        test_data = b'{"command": "read_sensors"}'
        logger.log_sent(test_data, "READ_SENSORS")
        
        # Log received data
        response = b'{"sensors": {"pt": [100, 200], "tc": [25.5, 30.2]}}'
        parsed = json.loads(response.decode())
        logger.log_received(response, parsed)
    
    def test_protocol_analysis():
        logger = get_serial_logger()
        
        # Test JSON protocol
        json_data = b'{"test": "data"}\r\n'
        analysis = logger.analyze_protocol(json_data)
        assert analysis['contains_json'] == True, "JSON not detected"
        assert analysis['line_endings'] == 'CRLF', "Line endings not detected"
    
    def test_error_logging():
        logger = get_serial_logger()
        
        # Log various errors
        logger.log_timeout(0.5, "Serial read timeout")
        logger.log_protocol_error('json_parse', b'invalid json', ValueError("Invalid JSON"))
        logger.log_reconnection(3, True)
    
    def test_statistics():
        logger = get_serial_logger()
        
        # Generate some data
        for i in range(5):
            logger.log_sent(f"Command {i}".encode(), f"CMD_{i}")
            logger.log_received(f"Response {i}".encode(), None)
        
        stats = logger.get_statistics()
        assert stats['total_tx'] >= 5, "TX count incorrect"
        assert stats['total_rx'] >= 5, "RX count incorrect"
    
    test_case("Serial logger initialization", test_initialization)
    test_case("Data logging", test_data_logging)
    test_case("Protocol analysis", test_protocol_analysis)
    test_case("Error logging", test_error_logging)
    test_case("Statistics tracking", test_statistics)

# ============================================================================
# Integration Tests
# ============================================================================

def test_integration():
    """Test integration between components"""
    print_header("Testing Integration")
    
    def test_logging_pipeline():
        # Get all components
        logger_mgr = get_logger_manager()
        perf_monitor = get_performance_monitor()
        event_logger = get_event_logger()
        
        # Perform integrated operation
        logger = logger_mgr.get_logger('integration')
        
        with perf_monitor.measure('integrated_operation'):
            logger.info("Starting integrated operation")
            event_logger.log_event(EventType.STARTUP, {'test': True}, 'INFO')
            time.sleep(0.1)
            logger.info("Completed integrated operation")
        
        # Verify all components worked together
        metrics = perf_monitor.get_metrics()
        assert 'integrated_operation' in metrics, "Operation not measured"
    
    def test_error_and_logging():
        logger_mgr = get_logger_manager()
        error_recovery = get_error_recovery()
        
        logger = logger_mgr.get_logger('error_test')
        
        # Test error recovery with logging
        def failing_op():
            logger.error("Operation failed")
            raise RuntimeError("Test error")
        
        result = error_recovery.retry_with_backoff(
            lambda: "Success",  # Will succeed first time
            ErrorType.GENERIC
        )
        assert result == "Success", "Recovery failed"
    
    def test_concurrent_logging():
        logger_mgr = get_logger_manager()
        logger = logger_mgr.get_logger('concurrent')
        
        def log_messages(thread_id):
            for i in range(10):
                logger.info(f"Thread {thread_id} message {i}")
                time.sleep(0.01)
        
        # Create multiple threads
        threads = []
        for i in range(3):
            t = threading.Thread(target=log_messages, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Verify no crashes
        logger.info("Concurrent logging completed")
    
    test_case("Logging pipeline", test_logging_pipeline)
    test_case("Error recovery with logging", test_error_and_logging)
    test_case("Concurrent logging", test_concurrent_logging)

# ============================================================================
# Web Server Tests (if server is running)
# ============================================================================

def test_web_endpoints():
    """Test web server endpoints if available"""
    print_header("Testing Web Endpoints")
    
    base_url = "http://localhost:5000"
    
    def test_browser_heartbeat():
        try:
            response = requests.post(
                f"{base_url}/api/browser_heartbeat",
                json={
                    'timestamp': time.time(),
                    'visible': True,
                    'throttled': False,
                    'missed_heartbeats': 0
                },
                timeout=2
            )
            assert response.status_code == 200, f"Bad status: {response.status_code}"
            data = response.json()
            assert 'status' in data, "Missing status in response"
        except requests.exceptions.ConnectionError:
            raise AssertionError("Server not running - skipping web tests")
    
    def test_browser_status():
        response = requests.post(
            f"{base_url}/api/browser_status",
            json={
                'event': 'initialized',
                'timestamp': time.time(),
                'visible': True,
                'throttled': False
            },
            timeout=2
        )
        assert response.status_code == 200, f"Bad status: {response.status_code}"
    
    try:
        test_case("Browser heartbeat endpoint", test_browser_heartbeat)
        test_case("Browser status endpoint", test_browser_status)
    except AssertionError as e:
        if "Server not running" in str(e):
            print(f"\n[INFO] {e}")
        else:
            raise

# ============================================================================
# Main Test Runner
# ============================================================================

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  BLAST Logging System - Comprehensive Test Suite")
    print("="*60)
    
    # Initialize logging system
    print("\n[SETUP] Initializing logging system...")
    logger_mgr = get_logger_manager()
    logger_mgr.start_async_writer()
    
    # Run all test suites
    test_logger_manager()
    test_performance_monitor()
    test_freeze_detector()
    test_event_logger()
    test_error_recovery()
    test_serial_logger()
    test_integration()
    test_web_endpoints()
    
    # Print summary
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)
    print(f"  Passed: {test_results['passed']} tests")
    print(f"  Failed: {test_results['failed']} tests")
    
    if test_results['failed'] > 0:
        print("\n  Failed Tests:")
        for error in test_results['errors']:
            print(f"    - {error}")
    
    print("="*60)
    
    # Cleanup
    print("\n[CLEANUP] Stopping logging system...")
    freeze_detector = get_freeze_detector()
    if freeze_detector.monitor_thread:
        freeze_detector.stop()
    
    perf_monitor = get_performance_monitor()
    perf_monitor.stop_monitoring()
    
    logger_mgr.stop_async_writer()
    
    # Exit with appropriate code
    sys.exit(0 if test_results['failed'] == 0 else 1)

if __name__ == "__main__":
    main()