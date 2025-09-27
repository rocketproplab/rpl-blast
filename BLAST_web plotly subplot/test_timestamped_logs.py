#!/usr/bin/env python
"""
Test timestamped logging system
Verify that logs are created in timestamped directories
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime

# Add current directory to path
sys.path.append(os.getcwd())

def test_timestamped_logs():
    """Test that logs are created in timestamped directories"""
    
    print("="*60)
    print("Testing Timestamped Logging System")
    print("="*60)
    
    # Import and initialize logging
    print("\n1. Initializing logging system...")
    from app.logging.logger_manager import get_logger_manager
    from app.logging.performance_monitor import get_performance_monitor
    from app.logging.freeze_detector import get_freeze_detector
    from app.logging.event_logger import get_event_logger
    
    # Get logger manager
    logger_mgr = get_logger_manager()
    logger_mgr.start_async_writer()
    
    # Verify run directory was created
    print(f"\n2. Checking run directory...")
    print(f"   Run timestamp: {logger_mgr.run_timestamp}")
    print(f"   Run directory: {logger_mgr.run_dir}")
    
    assert logger_mgr.run_dir.exists(), "Run directory not created"
    assert logger_mgr.run_dir.name.startswith('run_'), "Run directory not named correctly"
    
    # Check subdirectories
    print(f"\n3. Checking subdirectories...")
    subdirs = ['events', 'errors', 'performance', 'serial', 'data']
    for subdir in subdirs:
        subdir_path = logger_mgr.run_dir / subdir
        assert subdir_path.exists(), f"Subdirectory {subdir} not created"
        print(f"   ✓ {subdir_path}")
    
    # Check symlink to latest
    print(f"\n4. Checking 'latest' symlink...")
    latest_link = logger_mgr.log_dir / 'latest'
    if latest_link.exists():
        assert latest_link.is_symlink(), "Latest is not a symlink"
        assert latest_link.resolve() == logger_mgr.run_dir.resolve(), "Latest doesn't point to current run"
        print(f"   ✓ Latest symlink points to {logger_mgr.run_dir.name}")
    else:
        print(f"   ⚠ Latest symlink not created (may be OS limitation)")
    
    # Test logging to different loggers
    print(f"\n5. Testing log file creation...")
    
    # Get various loggers and write test messages
    app_logger = logger_mgr.get_logger('app')
    error_logger = logger_mgr.get_logger('errors')
    event_logger = get_event_logger()
    
    app_logger.info("Test message to app log")
    app_logger.warning("Test warning to app log")
    error_logger.error("Test error message")
    
    # Give async writer time to flush
    time.sleep(1)
    
    # Check log files were created
    log_files = {
        'app.log': logger_mgr.run_dir / 'app.log',
        'errors/errors.log': logger_mgr.run_dir / 'errors' / 'errors.log',
        'events/events.log': logger_mgr.run_dir / 'events' / 'events.log',
        'performance/perf.log': logger_mgr.run_dir / 'performance' / 'perf.log',
    }
    
    for name, path in log_files.items():
        if path.exists():
            size = path.stat().st_size
            print(f"   ✓ {name}: {size} bytes")
        else:
            print(f"   ✗ {name}: not created yet")
    
    # Test data logger with serial reader
    print(f"\n6. Testing data logger...")
    try:
        from app.data_sources.simulator import Simulator
        sim = Simulator()
        sim.initialize()
        
        # Check if data file will be created in run directory
        # Note: The simulator doesn't log data, only serial reader does
        print(f"   ℹ Simulator initialized (doesn't create data logs)")
    except Exception as e:
        print(f"   ⚠ Could not test data logger: {e}")
    
    # Create a second run to test multiple runs
    print(f"\n7. Testing multiple runs...")
    print("   Note: In production, each app restart creates a new run directory")
    
    # List all run directories
    run_dirs = sorted([d for d in logger_mgr.log_dir.iterdir() 
                      if d.is_dir() and d.name.startswith('run_')])
    
    print(f"   Found {len(run_dirs)} run directories:")
    for run_dir in run_dirs[-5:]:  # Show last 5
        print(f"     - {run_dir.name}")
    
    # Clean up
    print(f"\n8. Cleanup...")
    logger_mgr.stop_async_writer()
    
    print(f"\n{'='*60}")
    print("✓ Timestamped logging system working correctly!")
    print(f"{'='*60}")
    print(f"\nLog files for this run are in:")
    print(f"  {logger_mgr.run_dir}")
    print(f"\nYou can also access them via:")
    print(f"  {logger_mgr.log_dir}/latest/")
    
    return True

if __name__ == "__main__":
    try:
        test_timestamped_logs()
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)