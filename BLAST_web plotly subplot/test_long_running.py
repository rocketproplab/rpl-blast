#!/usr/bin/env python
"""
Long-Running Test for BLAST Logging System
Tests for memory leaks and file handle issues over extended periods
"""

import sys
import os
import time
import threading
import psutil
import gc
from datetime import datetime, timedelta

sys.path.append(os.getcwd())

from app.logging.logger_manager import get_logger_manager
from app.logging.performance_monitor import get_performance_monitor
from app.logging.event_logger import get_event_logger
from app.logging.freeze_detector import get_freeze_detector

class LongRunningTest:
    def __init__(self, duration_minutes=30):
        self.duration_minutes = duration_minutes
        self.duration_seconds = duration_minutes * 60
        
        # Initialize logging
        self.logger_mgr = get_logger_manager()
        self.logger_mgr.start_async_writer()
        self.perf_monitor = get_performance_monitor()
        self.event_logger = get_event_logger()
        self.freeze_detector = get_freeze_detector()
        self.freeze_detector.start()
        
        self.logger = self.logger_mgr.get_logger('app')
        
        # Tracking
        self.process = psutil.Process()
        self.start_time = time.time()
        self.metrics_history = []
        self.running = True
        
    def collect_metrics(self):
        """Collect system metrics"""
        try:
            metrics = {
                'timestamp': time.time(),
                'elapsed_minutes': (time.time() - self.start_time) / 60,
                'memory_mb': self.process.memory_info().rss / 1024 / 1024,
                'cpu_percent': self.process.cpu_percent(),
                'thread_count': threading.active_count(),
                'num_fds': len(self.process.open_files()),
                'queue_size': self.logger_mgr.log_queue.qsize()
            }
            
            # Check for handle leaks by listing open files
            open_logs = [f for f in self.process.open_files() if 'log' in f.path]
            metrics['log_files_open'] = len(open_logs)
            
            return metrics
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
            return None
    
    def monitor_thread(self):
        """Background thread that monitors system health"""
        while self.running:
            metrics = self.collect_metrics()
            if metrics:
                self.metrics_history.append(metrics)
                
                # Log metrics every 5 minutes
                if len(self.metrics_history) % 5 == 0:
                    self.logger.info(
                        f"Health check at {metrics['elapsed_minutes']:.1f} min: "
                        f"Memory={metrics['memory_mb']:.1f}MB, "
                        f"FDs={metrics['num_fds']}, "
                        f"Queue={metrics['queue_size']}"
                    )
                
                # Alert on issues
                if metrics['memory_mb'] > 500:
                    self.logger.warning(f"High memory usage: {metrics['memory_mb']:.1f}MB")
                
                if metrics['num_fds'] > 100:
                    self.logger.warning(f"High file descriptor count: {metrics['num_fds']}")
                
                if metrics['queue_size'] > 1000:
                    self.logger.warning(f"Log queue backlog: {metrics['queue_size']} messages")
            
            time.sleep(60)  # Check every minute
    
    def simulate_normal_operations(self):
        """Simulate normal application operations"""
        operations_count = 0
        
        while self.running:
            # Simulate sensor reading (10Hz)
            for _ in range(10):
                self.logger.debug(f"Sensor reading {operations_count}")
                self.perf_monitor.record_metric('sensor_read', operations_count % 100, 'value')
                operations_count += 1
                time.sleep(0.1)
            
            # Periodic event
            if operations_count % 100 == 0:
                self.event_logger.log_valve_operation(
                    'fcv1', 'Test Valve', 
                    operations_count % 2 == 0,
                    'auto', True
                )
            
            # Heartbeat
            self.freeze_detector.heartbeat()
            
            # Occasional warning
            if operations_count % 500 == 0:
                self.logger.warning(f"Periodic check at operation {operations_count}")
            
            # Force garbage collection periodically
            if operations_count % 1000 == 0:
                gc.collect()
    
    def analyze_results(self):
        """Analyze metrics history for leaks"""
        if len(self.metrics_history) < 2:
            print("Not enough data to analyze")
            return
        
        print("\n" + "="*60)
        print("Long-Running Test Analysis")
        print("="*60)
        
        # Memory leak detection
        initial_memory = self.metrics_history[0]['memory_mb']
        final_memory = self.metrics_history[-1]['memory_mb']
        memory_growth = final_memory - initial_memory
        memory_growth_rate = memory_growth / (self.duration_minutes)
        
        print(f"\nMemory Analysis:")
        print(f"  Initial: {initial_memory:.1f}MB")
        print(f"  Final: {final_memory:.1f}MB")
        print(f"  Growth: {memory_growth:.1f}MB")
        print(f"  Growth rate: {memory_growth_rate:.2f}MB/min")
        
        if memory_growth_rate < 0.5:
            print("  ✅ No memory leak detected")
        elif memory_growth_rate < 1.0:
            print("  ⚠️  Possible minor memory leak")
        else:
            print("  ❌ Memory leak detected!")
        
        # File descriptor leak detection
        initial_fds = self.metrics_history[0]['num_fds']
        final_fds = self.metrics_history[-1]['num_fds']
        fd_growth = final_fds - initial_fds
        
        print(f"\nFile Descriptor Analysis:")
        print(f"  Initial: {initial_fds}")
        print(f"  Final: {final_fds}")
        print(f"  Growth: {fd_growth}")
        
        if fd_growth < 5:
            print("  ✅ No file descriptor leak detected")
        else:
            print("  ❌ File descriptor leak detected!")
        
        # Queue backlog detection
        max_queue = max(m['queue_size'] for m in self.metrics_history)
        avg_queue = sum(m['queue_size'] for m in self.metrics_history) / len(self.metrics_history)
        
        print(f"\nLog Queue Analysis:")
        print(f"  Max size: {max_queue}")
        print(f"  Avg size: {avg_queue:.1f}")
        
        if max_queue < 100:
            print("  ✅ No queue backlog issues")
        else:
            print("  ⚠️  Queue backlog detected")
        
        # Plot memory trend (simple ASCII)
        print(f"\nMemory Usage Over Time:")
        max_mem = max(m['memory_mb'] for m in self.metrics_history)
        min_mem = min(m['memory_mb'] for m in self.metrics_history)
        range_mem = max_mem - min_mem
        
        for i, m in enumerate(self.metrics_history[::len(self.metrics_history)//20 or 1]):
            bar_len = int((m['memory_mb'] - min_mem) / range_mem * 40) if range_mem > 0 else 0
            print(f"  {m['elapsed_minutes']:5.1f}min: {'█' * bar_len} {m['memory_mb']:.1f}MB")
    
    def run(self):
        """Run the long-running test"""
        print("="*60)
        print("BLAST Logging System - Long-Running Test")
        print("="*60)
        print(f"Duration: {self.duration_minutes} minutes")
        print(f"Started: {datetime.now().isoformat()}")
        print(f"Expected end: {(datetime.now() + timedelta(minutes=self.duration_minutes)).isoformat()}")
        print("\nPress Ctrl+C to stop early\n")
        
        # Collect initial metrics
        initial_metrics = self.collect_metrics()
        self.metrics_history.append(initial_metrics)
        print(f"Initial state:")
        print(f"  Memory: {initial_metrics['memory_mb']:.1f}MB")
        print(f"  File descriptors: {initial_metrics['num_fds']}")
        print(f"  Threads: {initial_metrics['thread_count']}")
        
        # Start monitoring thread
        monitor = threading.Thread(target=self.monitor_thread, daemon=True)
        monitor.start()
        
        try:
            # Run simulation
            end_time = time.time() + self.duration_seconds
            
            while time.time() < end_time:
                self.simulate_normal_operations()
                
                # Progress update
                elapsed = (time.time() - self.start_time) / 60
                remaining = self.duration_minutes - elapsed
                if int(elapsed) % 5 == 0:  # Every 5 minutes
                    print(f"Progress: {elapsed:.0f}/{self.duration_minutes} minutes ({remaining:.0f} remaining)")
            
        except KeyboardInterrupt:
            print("\nTest interrupted by user")
        finally:
            self.running = False
            time.sleep(2)  # Let monitor thread finish
            
            # Collect final metrics
            final_metrics = self.collect_metrics()
            if final_metrics:
                self.metrics_history.append(final_metrics)
            
            # Analyze results
            self.analyze_results()
            
            # Cleanup
            self.freeze_detector.stop()
            self.perf_monitor.stop_monitoring()
            self.logger_mgr.stop_async_writer()
            
            print(f"\nTest completed. Logs saved to: logs/latest/")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Long-running test for BLAST logging system')
    parser.add_argument('--minutes', type=int, default=30,
                       help='Duration of test in minutes (default: 30)')
    args = parser.parse_args()
    
    test = LongRunningTest(duration_minutes=args.minutes)
    test.run()