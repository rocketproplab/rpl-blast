# BLAST Logging System - Testing Guide

## 1. Test with Actual Serial Hardware

### Setup
1. **Connect your serial device** to the computer
2. **Find the serial port**:
   ```bash
   # On macOS:
   ls /dev/tty.* | grep -i usb
   
   # On Linux:
   ls /dev/ttyUSB* /dev/ttyACM*
   
   # On Windows:
   # Check Device Manager for COM ports
   ```

3. **Update configuration** in `app/config.py`:
   ```python
   DATA_SOURCE = 'serial'  # Change from 'simulator'
   SERIAL_PORT = '/dev/tty.usbserial-XXXXX'  # Your actual port
   SERIAL_BAUDRATE = 115200  # Match your device baudrate
   ```

4. **Run the application**:
   ```bash
   cd "/Users/andrewyang/Library/CloudStorage/OneDrive-UCSanDiego Real/Stuff/UCSD_School_Documents/RPL/rpl-blast/BLAST_web plotly subplot"
   python run.py
   ```

5. **Monitor the logs**:
   ```bash
   # Watch the main app log
   tail -f logs/latest/app.log
   
   # Watch serial communication log
   tail -f logs/latest/serial/serial.log
   
   # Watch for errors
   tail -f logs/latest/errors/errors.log
   ```

### What to Check:
- ✅ Serial connection establishes without errors
- ✅ Data is being received and parsed correctly
- ✅ No timeout errors in logs
- ✅ SerialLogger shows hex dumps of communication
- ✅ CSV data file is being populated in `logs/latest/data/`
- ✅ Error recovery works on disconnect/reconnect

### Test Disconnect/Reconnect:
1. While running, unplug the serial device
2. Check logs for disconnect detection and recovery attempts
3. Plug device back in
4. Verify automatic reconnection

---

## 2. Load Testing - Performance Under Heavy Load

### Purpose
Verify the logging system doesn't degrade performance under heavy load.

### Run the Test:
```bash
python test_load.py
```

### What It Tests:
- **High-rate sensor data** (100Hz for 10 seconds)
- **Concurrent operations** (20 threads logging simultaneously)
- **Error storms** (50 errors/second)
- **Memory pressure** (large log messages)

### Expected Results:
- ✅ Memory increase < 50MB
- ✅ Average response time < 10ms
- ✅ Log queue size < 100 messages
- ✅ No crashes or exceptions

### Interpreting Results:
```
Load Test Summary
============================================================
Duration: 45.2 seconds
Total messages logged: 4250
Messages per second: 94.0
Response times:
   Min: 0.12ms
   Avg: 2.34ms     ← Should be < 10ms
   Max: 15.23ms
   P95: 8.67ms
Results:
✅ Memory usage: PASS
✅ Log queue: PASS
✅ Performance: PASS
```

---

## 3. Long-Running Test - Memory Leaks & File Handles

### Purpose
Detect memory leaks and file handle leaks over extended periods.

### Run the Test:
```bash
# Run for 30 minutes (default)
python test_long_running.py

# Run for 2 hours
python test_long_running.py --minutes 120

# Run overnight (8 hours)
python test_long_running.py --minutes 480
```

### What It Monitors:
- Memory usage over time
- File descriptor count
- Log queue backlog
- Thread count
- CPU usage

### Expected Results:
- ✅ Memory growth < 0.5MB/minute
- ✅ File descriptors remain constant (±5)
- ✅ No queue backlog buildup
- ✅ Stable thread count

### Example Output:
```
Memory Analysis:
  Initial: 125.3MB
  Final: 138.7MB
  Growth: 13.4MB
  Growth rate: 0.45MB/min
  ✅ No memory leak detected

File Descriptor Analysis:
  Initial: 23
  Final: 24
  Growth: 1
  ✅ No file descriptor leak detected
```

---

## 4. Browser Throttling Test

### Purpose
Verify the browser monitor detects tab suspension and throttling.

### Manual Test Steps:

1. **Start the application**:
   ```bash
   python run.py
   ```

2. **Open the web interface**:
   - Navigate to http://localhost:5000
   - Open browser DevTools (F12)
   - Go to Console tab

3. **Test visibility changes**:
   - Switch to a different tab for 10+ seconds
   - Return to the BLAST tab
   - Check console for: `[BrowserMonitor] Page resumed`
   - Check logs: `grep "browser_event" logs/latest/events/events.log`

4. **Test throttling detection**:
   - Minimize the browser window
   - Wait 30 seconds
   - Restore the window
   - Check for throttling warnings in console
   - Verify in logs: `grep "throttled" logs/latest/app.log`

5. **Test performance monitoring**:
   - Open DevTools → Performance tab
   - Start recording
   - Use the application normally
   - Look for frame drops or long tasks
   - Check if browser monitor detected them

### Automated Browser Test:
```javascript
// Paste this in browser console to simulate throttling
setInterval(() => {
    // Simulate heavy computation
    let start = Date.now();
    while(Date.now() - start < 3000) {
        // Block for 3 seconds
    }
}, 5000);

// Check browserMonitor status
console.log(window.browserMonitor.getStatus());
```

### Expected Browser Monitor Output:
```javascript
{
  lastHeartbeat: 1732749123456,
  missedHeartbeats: 0,
  isThrottled: false,
  isVisible: true,
  frameDrops: 0,
  memoryUsage: {
    used: 45234176,
    total: 67108864,
    limit: 4294967296,
    percentage: "1.1%"
  }
}
```

### Server-side Verification:
```bash
# Check browser events in event log
grep "CLIENT_" logs/latest/events/events.log | tail -20

# Check for throttling detections
grep "browser_throttle" logs/latest/performance/perf.log

# Check heartbeat metrics
grep "browser_heartbeat" logs/latest/app.log | tail -10
```

---

## Test Summary Checklist

### Before Production:
- [ ] Serial hardware test passed
- [ ] Load test shows < 10ms average response
- [ ] 30-minute long-running test shows no leaks
- [ ] Browser throttling detection verified
- [ ] Error recovery tested (disconnect/reconnect)
- [ ] Log rotation working (files < 100MB)
- [ ] Timestamped directories created correctly
- [ ] All log streams writing data

### Known Limits:
- Log queue max: 10,000 messages
- File rotation: 100MB per file, 7 backups
- Freeze detection timeout: 5 seconds
- Browser heartbeat: 1 second intervals

### If Tests Fail:
1. Check `logs/latest/errors/errors.log` for exceptions
2. Verify system resources (disk space, memory)
3. Ensure no other instances running
4. Check file permissions on logs directory
5. Verify Python dependencies installed