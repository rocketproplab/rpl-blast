#!/usr/bin/env python
"""
Test script to verify logging system is working
Makes requests to the app and checks log output
"""

import requests
import time
import subprocess
import signal
import threading
import json

def start_app():
    """Start the Flask app in background"""
    print("Starting Flask app...")
    proc = subprocess.Popen(
        ['python', 'run.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    # Wait for app to start
    time.sleep(3)
    return proc

def make_requests():
    """Make some test requests to generate logs"""
    base_url = "http://127.0.0.1:5000"
    
    print("\nMaking test requests...")
    
    # Test main page
    try:
        resp = requests.get(base_url, timeout=2)
        print(f"GET / - Status: {resp.status_code}")
    except Exception as e:
        print(f"Error accessing main page: {e}")
    
    # Test data endpoint multiple times
    for i in range(5):
        try:
            resp = requests.get(f"{base_url}/data", timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                if 'value' in data and data['value']:
                    print(f"Request {i+1}: Got sensor data")
                else:
                    print(f"Request {i+1}: No data available")
            else:
                print(f"Request {i+1}: Status {resp.status_code}")
        except Exception as e:
            print(f"Request {i+1} error: {e}")
        
        time.sleep(0.5)
    
    # Test concurrent requests
    print("\nTesting concurrent requests...")
    threads = []
    for i in range(3):
        t = threading.Thread(target=lambda idx=i: make_concurrent_request(base_url, idx))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()

def make_concurrent_request(base_url, idx):
    """Make a request for concurrent testing"""
    try:
        resp = requests.get(f"{base_url}/data", timeout=2)
        print(f"Concurrent request {idx}: Status {resp.status_code}")
    except Exception as e:
        print(f"Concurrent request {idx} error: {e}")

def check_logs():
    """Check log files for expected content"""
    print("\n" + "="*50)
    print("CHECKING LOG FILES")
    print("="*50)
    
    # Check app log
    print("\n--- App Log (last 10 lines) ---")
    with open('logs/app.log', 'r') as f:
        lines = f.readlines()
        for line in lines[-10:]:
            print(line.strip())
    
    # Check events log
    print("\n--- Events Log (last 5 entries) ---")
    try:
        with open('logs/events/events.log', 'r') as f:
            lines = f.readlines()
            for line in lines[-5:]:
                if line.strip():
                    try:
                        event = json.loads(line)
                        print(f"Event: {event.get('event_type')} - {event.get('details', {})}")
                    except:
                        print(line.strip())
    except FileNotFoundError:
        print("No events logged yet")
    
    # Check performance log
    print("\n--- Performance Metrics ---")
    try:
        with open('logs/performance/perf.log', 'r') as f:
            lines = f.readlines()
            if lines:
                # Get last metrics entry
                for line in reversed(lines):
                    if 'metrics' in line:
                        try:
                            data = json.loads(line)
                            metrics = data.get('metrics', {})
                            for name, stats in metrics.items():
                                if isinstance(stats, dict):
                                    avg = stats.get('average', 0)
                                    count = stats.get('count', 0)
                                    print(f"  {name}: avg={avg:.2f}, count={count}")
                            break
                        except:
                            continue
    except FileNotFoundError:
        print("No performance metrics yet")
    
    # Check for errors
    print("\n--- Errors ---")
    try:
        with open('logs/errors/errors.log', 'r') as f:
            content = f.read()
            if content:
                print("ERRORS FOUND:")
                print(content[:500])
            else:
                print("No errors logged")
    except FileNotFoundError:
        print("No error log file")

def main():
    """Main test function"""
    print("BLAST Logging System Test")
    print("="*50)
    
    # Start the app
    proc = start_app()
    
    try:
        # Make test requests
        make_requests()
        
        # Wait a bit for logs to be written
        time.sleep(2)
        
        # Check logs
        check_logs()
        
    finally:
        # Stop the app
        print("\n\nStopping Flask app...")
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=5)
        print("Test complete!")

if __name__ == "__main__":
    main()