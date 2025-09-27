#!/usr/bin/env python
"""
Load Testing Script for BLAST Logging System
Tests logging performance under heavy load
"""

import sys
import os
import time
import threading
import random
import psutil
import statistics
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

sys.path.append(os.getcwd())

from app.logging.logger_manager import get_logger_manager
from app.logging.performance_monitor import get_performance_monitor
from app.logging.event_logger import get_event_logger, EventType
from app.logging.freeze_detector import get_freeze_detector

class LoadTester:
    def __init__(self):
        # Initialize logging
        self.logger_mgr = get_logger_manager()
        self.logger_mgr.start_async_writer()
        self.perf_monitor = get_performance_monitor()
        self.event_logger = get_event_logger()
        self.freeze_detector = get_freeze_detector()
        self.freeze_detector.start()
        
        self.app_logger = self.logger_mgr.get_logger('app')
        
        # Performance tracking
        self.start_time = time.time()
        self.message_count = 0
        self.error_count = 0
        self.response_times = []
        
        # System metrics before test
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024
        self.initial_handles = len(self.process.open_files())
        
    def simulate_sensor_data_burst(self, duration=10, rate_hz=100):
        """Simulate high-rate sensor data logging"""
        print(f"\n📊 Simulating sensor data at {rate_hz}Hz for {duration}s...")
        
        interval = 1.0 / rate_hz
        end_time = time.time() + duration
        burst_count = 0
        
        while time.time() < end_time:
            start = time.perf_counter()
            
            # Simulate sensor readings
            with self.perf_monitor.measure('sensor_read'):
                data = {
                    'pt': [random.uniform(0, 500) for _ in range(8)],
                    'tc': [random.uniform(20, 100) for _ in range(8)],
                    'lc': [random.uniform(0, 1000) for _ in range(4)],
                    'fcv': [random.choice([True, False]) for _ in range(8)]
                }
            
            # Log the data
            self.app_logger.debug(f"Sensor data: {data}")
            
            # Check thresholds (generates events)
            if data['pt'][0] > 450:
                self.event_logger.log_sensor_threshold(
                    'pt1', 'Pressure 1', data['pt'][0], 450, 'warning', 'PSI'
                )
            
            # Track performance
            elapsed = time.perf_counter() - start
            self.response_times.append(elapsed * 1000)
            burst_count += 1
            self.message_count += 1
            
            # Heartbeat
            self.freeze_detector.heartbeat()
            
            # Maintain rate
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        print(f"   ✓ Generated {burst_count} sensor readings")
        print(f"   Average processing time: {statistics.mean(self.response_times):.2f}ms")
    
    def simulate_concurrent_operations(self, num_threads=10, operations_per_thread=100):
        """Simulate multiple concurrent logging operations"""
        print(f"\n🔄 Simulating {num_threads} concurrent threads...")
        
        def worker(thread_id):
            logger = self.logger_mgr.get_logger('app')
            for i in range(operations_per_thread):
                # Mix of different log levels
                if i % 10 == 0:
                    logger.error(f"Thread {thread_id}: Simulated error {i}")
                    self.error_count += 1
                elif i % 5 == 0:
                    logger.warning(f"Thread {thread_id}: Warning {i}")
                else:
                    logger.info(f"Thread {thread_id}: Operation {i}")
                
                self.message_count += 1
                
                # Simulate some processing
                time.sleep(random.uniform(0.001, 0.01))
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]
            for future in futures:
                future.result()
        
        print(f"   ✓ Completed {num_threads * operations_per_thread} operations")
    
    def simulate_error_storm(self, duration=5, errors_per_second=50):
        """Simulate rapid error generation"""
        print(f"\n⚠️  Simulating error storm at {errors_per_second} errors/sec for {duration}s...")
        
        interval = 1.0 / errors_per_second
        end_time = time.time() + duration
        storm_count = 0
        
        while time.time() < end_time:
            try:
                # Generate various types of errors
                error_type = random.choice(['timeout', 'parse', 'connection', 'validation'])
                
                if error_type == 'timeout':
                    raise TimeoutError("Simulated timeout")
                elif error_type == 'parse':
                    raise ValueError("Simulated parse error")
                elif error_type == 'connection':
                    raise ConnectionError("Simulated connection error")
                else:
                    raise RuntimeError("Simulated runtime error")
                    
            except Exception as e:
                self.logger_mgr.get_logger('errors').error(
                    f"Error storm: {e}", 
                    exc_info=True
                )
                storm_count += 1
                self.error_count += 1
            
            time.sleep(interval)
        
        print(f"   ✓ Generated {storm_count} errors")
    
    def simulate_memory_pressure(self):
        """Generate large log messages to test memory handling"""
        print(f"\n💾 Testing memory pressure with large messages...")
        
        # Generate increasingly large messages
        for size_kb in [1, 10, 100, 500]:
            large_data = 'X' * (size_kb * 1024)
            self.app_logger.info(f"Large message test: {size_kb}KB - {large_data[:100]}...")
            time.sleep(0.5)
            
            # Check memory
            current_memory = self.process.memory_info().rss / 1024 / 1024
            print(f"   Memory after {size_kb}KB: {current_memory:.1f}MB")
    
    def check_system_health(self):
        """Check system health during/after load test"""
        print(f"\n🔍 System Health Check:")
        
        # Memory usage
        current_memory = self.process.memory_info().rss / 1024 / 1024
        memory_increase = current_memory - self.initial_memory
        print(f"   Memory: {current_memory:.1f}MB (Δ{memory_increase:+.1f}MB)")
        
        # CPU usage
        cpu_percent = self.process.cpu_percent(interval=1)
        print(f"   CPU: {cpu_percent:.1f}%")
        
        # Thread count
        thread_count = threading.active_count()
        print(f"   Threads: {thread_count}")
        
        # File handles
        try:
            current_handles = len(self.process.open_files())
            handle_increase = current_handles - self.initial_handles
            print(f"   File handles: {current_handles} (Δ{handle_increase:+d})")
        except:
            print(f"   File handles: Unable to count")
        
        # Log queue status
        queue_size = self.logger_mgr.log_queue.qsize()
        print(f"   Log queue: {queue_size} messages pending")
        
        # Check for memory leaks
        if memory_increase > 100:  # More than 100MB increase
            print(f"   ⚠️  WARNING: Significant memory increase detected!")
        
        # Check for handle leaks
        if current_handles - self.initial_handles > 20:
            print(f"   ⚠️  WARNING: Possible file handle leak!")
        
        return {
            'memory_mb': current_memory,
            'memory_increase_mb': memory_increase,
            'cpu_percent': cpu_percent,
            'thread_count': thread_count,
            'queue_size': queue_size
        }
    
    def run_full_test(self):
        """Run complete load test suite"""
        print("="*60)
        print("BLAST Logging System - Load Test")
        print("="*60)
        print(f"Started at: {datetime.now().isoformat()}")
        print(f"Initial memory: {self.initial_memory:.1f}MB")
        print(f"Initial handles: {self.initial_handles}")
        
        # Test 1: High-rate sensor data
        self.simulate_sensor_data_burst(duration=10, rate_hz=100)
        self.check_system_health()
        
        # Test 2: Concurrent operations
        self.simulate_concurrent_operations(num_threads=20, operations_per_thread=50)
        self.check_system_health()
        
        # Test 3: Error storm
        self.simulate_error_storm(duration=5, errors_per_second=50)
        self.check_system_health()
        
        # Test 4: Memory pressure
        self.simulate_memory_pressure()
        final_health = self.check_system_health()
        
        # Summary
        duration = time.time() - self.start_time
        print("\n" + "="*60)
        print("Load Test Summary")
        print("="*60)
        print(f"Duration: {duration:.1f} seconds")
        print(f"Total messages logged: {self.message_count}")
        print(f"Messages per second: {self.message_count/duration:.1f}")
        print(f"Total errors logged: {self.error_count}")
        
        if self.response_times:
            print(f"Response times:")
            print(f"   Min: {min(self.response_times):.2f}ms")
            print(f"   Avg: {statistics.mean(self.response_times):.2f}ms")
            print(f"   Max: {max(self.response_times):.2f}ms")
            print(f"   P95: {statistics.quantiles(self.response_times, n=20)[18]:.2f}ms")
        
        # Pass/Fail
        print("\nResults:")
        if final_health['memory_increase_mb'] < 50:
            print("✅ Memory usage: PASS")
        else:
            print("❌ Memory usage: FAIL (possible leak)")
        
        if final_health['queue_size'] < 100:
            print("✅ Log queue: PASS")
        else:
            print("❌ Log queue: FAIL (backlog detected)")
        
        if self.response_times and statistics.mean(self.response_times) < 10:
            print("✅ Performance: PASS")
        else:
            print("❌ Performance: FAIL (slow response times)")
        
        # Cleanup
        self.freeze_detector.stop()
        self.logger_mgr.stop_async_writer()
        
        print(f"\nLog files saved to: logs/latest/")

if __name__ == "__main__":
    tester = LoadTester()
    tester.run_full_test()