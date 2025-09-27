# BLAST Logging System - Log Analysis Guide

## Overview

The BLAST logging system creates timestamped directories for each run with organized log files. This guide explains how to read, interpret, and troubleshoot using these logs.

## Log Directory Structure

```
logs/
├── latest/                      → Symlink to current run
└── run_20250927_130611/         → Timestamped run directory
    ├── app.log                  → Main application log
    ├── data/
    │   └── blast_data_*.csv    → Sensor data recordings
    ├── errors/
    │   └── errors.log           → Error and exception logs
    ├── events/
    │   └── events.log           → Structured event logs (JSON)
    ├── performance/
    │   └── perf.log             → Performance metrics (JSON)
    ├── serial/
    │   └── serial.log           → Serial communication logs
    └── freeze_dump_*.json       → Freeze diagnostics (if freeze detected)
```

---

## 1. Main Application Log (`app.log`)

### Purpose
General application flow, startup/shutdown, and high-level operations.

### What to Look For

**Successful Startup:**
```
2025-09-27 13:06:11 [INFO] blast.app: ============================================================
2025-09-27 13:06:11 [INFO] blast.app: New logging session started: 20250927_130611
2025-09-27 13:06:11 [INFO] blast.app: Log directory: logs/run_20250927_130611
2025-09-27 13:06:11 [INFO] blast.app: ============================================================
2025-09-27 13:06:11 [INFO] blast.app: BLAST Application Starting
2025-09-27 13:06:11 [INFO] blast.app: Flask app created successfully
```

**Serial Connection:**
```
2025-09-27 13:06:12 [INFO] blast.app: Using serial data source on /dev/tty.usbserial-12345
2025-09-27 13:06:12 [INFO] blast.serial: Serial port opened successfully
2025-09-27 13:06:12 [INFO] blast.serial: Connected to /dev/tty.usbserial-12345 at 115200 baud
```

**Warning Signs:**
```
2025-09-27 13:06:15 [WARNING] blast.app: Heartbeat gap detected: 3.2s
2025-09-27 13:06:16 [WARNING] blast.app: High memory usage: 512.3MB
2025-09-27 13:06:17 [WARNING] blast.app: Browser throttling detected: 5 missed heartbeats
```

### Quick Commands
```bash
# Watch live
tail -f logs/latest/app.log

# Find warnings
grep WARNING logs/latest/app.log

# Check startup sequence
head -50 logs/latest/app.log

# Find freezes
grep -i freeze logs/latest/app.log
```

---

## 2. Error Log (`errors/errors.log`)

### Purpose
Captures all errors, exceptions, and stack traces.

### What to Look For

**Connection Errors:**
```
2025-09-27 13:07:23 [ERROR] blast.serial: Failed to read from serial port
Traceback (most recent call last):
  File "serial_reader.py", line 145, in read_data
    raw_data = self.ser.readline()
SerialException: device disconnected
```

**Parse Errors:**
```
2025-09-27 13:07:24 [ERROR] blast.serial: Failed to parse JSON: {"value": {"pt": [123, 45
ValueError: Expecting ',' delimiter: line 1 column 35
```

**Critical Errors:**
```
2025-09-27 13:07:25 [CRITICAL] blast.errors: FREEZE DETECTED! No heartbeat for 5.2s (freeze #1)
```

### Analyzing Stack Traces
```python
# Look for the actual error line (usually last in traceback)
File "serial_reader.py", line 145, in read_data
    raw_data = self.ser.readline()
SerialException: device disconnected  ← The actual error

# Check the call chain to understand flow
Traceback (most recent call last):  ← Start here
  File "routes/main.py", line 95     ← Web request handler
  File "data_sources/serial_reader.py", line 120  ← Data reading
  File "serial_reader.py", line 145  ← Where it failed
```

### Quick Commands
```bash
# Watch for errors
tail -f logs/latest/errors/errors.log

# Count error types
grep ERROR logs/latest/errors/errors.log | cut -d']' -f3 | sort | uniq -c

# Find critical issues
grep CRITICAL logs/latest/errors/errors.log

# Get last 10 errors with context
grep -A 5 ERROR logs/latest/errors/errors.log | tail -50
```

---

## 3. Event Log (`events/events.log`)

### Purpose
Structured JSON events for tracking state changes and important operations.

### Event Types
- `SERIAL_CONNECT` / `SERIAL_DISCONNECT` - Connection events
- `THRESHOLD_WARNING` / `THRESHOLD_DANGER` - Sensor alerts
- `VALVE_OPEN` / `VALVE_CLOSE` - Valve operations
- `CLIENT_THROTTLED` / `CLIENT_RECOVERED` - Browser issues
- `FREEZE_DETECTED` / `FREEZE_RECOVERED` - System freezes

### Reading JSON Events
```json
{
  "timestamp": "2025-09-27T13:07:30.123456",
  "event_type": "threshold_warning",
  "severity": "WARNING",
  "details": {
    "sensor_id": "pt1",
    "sensor_name": "Pressure 1",
    "value": 485.2,
    "threshold": 450,
    "unit": "PSI",
    "state_change": "normal -> warning"
  }
}
```

### Quick Commands
```bash
# Pretty print events
cat logs/latest/events/events.log | jq '.'

# Find all threshold violations
grep threshold logs/latest/events/events.log | jq '.details'

# Track valve operations
grep -E "valve_open|valve_close" logs/latest/events/events.log

# Browser events
grep CLIENT_ logs/latest/events/events.log | jq '{time:.timestamp, event:.event_type}'
```

---

## 4. Performance Log (`performance/perf.log`)

### Purpose
Tracks operation timings and system metrics.

### Metrics Structure
```json
{
  "timestamp": "2025-09-27T13:07:35",
  "metrics": {
    "data_source_read_time": {
      "name": "data_source_read_time",
      "count": 523,
      "average": 2.341,
      "min": 0.125,
      "max": 15.234,
      "last": 1.892
    },
    "memory_mb": {
      "count": 120,
      "average": 156.3,
      "min": 125.1,
      "max": 189.5
    }
  }
}
```

### Performance Indicators

**Good Performance:**
- `data_source_read_time`: < 10ms average
- `web_request_time`: < 50ms average
- `memory_mb`: stable (not growing)
- `cpu_percent`: < 50%

**Performance Issues:**
- Times > 100ms indicate blocking operations
- Growing memory suggests a leak
- High CPU may cause freezes

### Quick Commands
```bash
# Get average response times
cat logs/latest/performance/perf.log | jq '.metrics.data_source_read_time.average'

# Track memory over time
cat logs/latest/performance/perf.log | jq '{time:.timestamp, mem:.metrics.memory_mb.last}'

# Find slow operations
cat logs/latest/performance/perf.log | jq '.metrics | to_entries[] | select(.value.max > 100)'
```

---

## 5. Serial Communication Log (`serial/serial.log`)

### Purpose
Detailed serial port communication including hex dumps and protocol analysis.

### Log Format
```
2025-09-27 13:07:40 [DEBUG] Serial TX [12 bytes]: READ_SENSORS
    48 45 58: 0000  52 45 41 44 5f 53 45 4e 53 4f 52 53  READ_SENSORS
    
2025-09-27 13:07:40 [DEBUG] Serial RX [156 bytes]:
    48 45 58: 0000  7b 22 76 61 6c 75 65 22 3a 20 7b 22 70 74 22 3a  {"value": {"pt":
    48 45 58: 0010  20 5b 31 32 33 2c 20 34 35 36 2c 20 37 38 39 5d   [123, 456, 789]
    41 53 43: [Valid JSON detected]
    50 41 52: {"value": {"pt": [123, 456, 789], "tc": [25.5, 30.2]}}
```

### Troubleshooting Serial Issues

**Good Communication:**
- Regular TX/RX pairs
- Valid JSON in responses
- No timeout messages
- Consistent timing

**Problem Signs:**
- `[ERROR] Serial timeout after 0.5s`
- `[ERROR] Invalid JSON: unexpected end of data`
- `[WARNING] Framing error detected`
- Hex dumps showing garbage data

### Protocol Analysis
```bash
# Check data rate
grep "Serial RX" logs/latest/serial/serial.log | wc -l

# Find timeouts
grep -i timeout logs/latest/serial/serial.log

# Check for reconnections
grep -E "Connected|Disconnected|Reconnecting" logs/latest/serial/serial.log

# Analyze protocol errors
grep "protocol_error" logs/latest/serial/serial.log
```

---

## 6. Data Files (`data/blast_data_*.csv`)

### Purpose
Sensor readings saved for analysis and replay.

### CSV Format
```csv
serial_timestamp,system_timestamp,pt1,pt2,pt3,pt4,pt5,pt6,pt7,pt8,tc1,tc2,tc3,tc4,tc5,tc6,tc7,tc8,lc1,lc2,lc3,lc4,fcv1,fcv2,fcv3,fcv4,fcv5,fcv6,fcv7,fcv8
1234567890,2025-09-27 13:07:45.123,123.4,456.7,234.5,345.6,234.5,123.4,234.5,345.6,25.5,30.2,28.7,29.1,31.5,27.8,26.3,29.4,500.2,234.5,123.4,345.6,1,0,1,1,0,1,0,1
```

### Quick Analysis
```bash
# Count data points
wc -l logs/latest/data/*.csv

# Check for gaps (timestamps should increment smoothly)
awk -F',' '{print $2}' logs/latest/data/*.csv | head -20

# Find max pressure values
awk -F',' '{print $3}' logs/latest/data/*.csv | sort -n | tail -1

# Plot with gnuplot (if installed)
gnuplot -e "set datafile separator ','; plot 'logs/latest/data/blast_data_*.csv' using 2:3 with lines"
```

---

## 7. Freeze Dumps (`freeze_dump_*.json`)

### Purpose
Comprehensive diagnostics when a freeze is detected.

### Structure
```json
{
  "timestamp": "2025-09-27T13:07:50",
  "freeze_count": 1,
  "time_since_heartbeat": 5.234,
  "thread_info": [
    {
      "name": "MainThread",
      "daemon": false,
      "alive": true,
      "stack_trace": "..."
    }
  ],
  "recent_operations": [
    {
      "timestamp": 1234567890,
      "operation": "data_read",
      "details": {"source": "serial"},
      "thread": "MainThread"
    }
  ],
  "system_info": {
    "memory_mb": 234.5,
    "cpu_percent": 85.2,
    "num_threads": 12,
    "open_files": 45,
    "connections": 3
  }
}
```

### Analyzing Freezes
1. Check `time_since_heartbeat` - how long the freeze lasted
2. Look at `stack_trace` in threads - where code was stuck
3. Review `recent_operations` - what happened before freeze
4. Check `system_info` - resource exhaustion?

---

## Common Issues and Solutions

### Issue: Application Freezing

**Check these logs in order:**
1. `freeze_dump_*.json` - If exists, analyze thread stack traces
2. `errors/errors.log` - Look for CRITICAL messages before freeze
3. `performance/perf.log` - Check for increasing response times
4. `app.log` - Look for "Heartbeat gap" warnings

**Common Causes:**
- Serial blocking on disconnect
- Browser throttling
- Memory exhaustion
- Infinite loop in data processing

### Issue: Missing Data

**Check:**
1. `serial/serial.log` - Verify data is being received
2. `data/*.csv` - Check if CSV files are being written
3. `errors/errors.log` - Look for parse errors
4. `events/events.log` - Check for SERIAL_DISCONNECT events

### Issue: High Memory Usage

**Check:**
1. `performance/perf.log` - Track memory_mb over time
2. `app.log` - Look for "High memory usage" warnings
3. Count log file sizes: `du -sh logs/latest/*`
4. Check queue backlog in performance metrics

### Issue: Browser Not Updating

**Check:**
1. `app.log` - Look for "Browser throttling detected"
2. `events/events.log` - Check CLIENT_THROTTLED events
3. Browser console - Look for [BrowserMonitor] messages
4. Network tab in DevTools - Check if requests are failing

---

## Useful One-Liners

```bash
# Find all errors in the last hour
find logs/latest -name "*.log" -mmin -60 | xargs grep -h ERROR

# Get system health summary
echo "Errors: $(grep -c ERROR logs/latest/errors/errors.log)"
echo "Warnings: $(grep -c WARNING logs/latest/app.log)"
echo "Freezes: $(ls logs/latest/freeze_dump_* 2>/dev/null | wc -l)"

# Track request rate
grep "Request.*started" logs/latest/app.log | awk '{print $1" "$2}' | uniq -c

# Find memory leaks
grep memory_mb logs/latest/performance/perf.log | tail -10

# Check serial data rate
echo "Data points per minute:"
for file in logs/latest/data/*.csv; do
    lines=$(wc -l < "$file")
    echo "$(basename $file): $((lines * 60 / 300)) pts/min"
done

# Generate quick report
echo "=== BLAST Log Summary ==="
echo "Run: $(readlink logs/latest)"
echo "Duration: $(head -1 logs/latest/app.log | awk '{print $1" "$2}') to $(tail -1 logs/latest/app.log | awk '{print $1" "$2}')"
echo "Errors: $(grep -c ERROR logs/latest/errors/errors.log)"
echo "Warnings: $(grep -c WARNING logs/latest/app.log)"
echo "Data points: $(cat logs/latest/data/*.csv 2>/dev/null | wc -l)"
```

---

## Log Monitoring During Operations

### Terminal Setup (4 panes):
```bash
# Terminal 1: Main app log
tail -f logs/latest/app.log | grep -v DEBUG

# Terminal 2: Errors only
tail -f logs/latest/errors/errors.log

# Terminal 3: Performance metrics
watch -n 5 'tail -20 logs/latest/performance/perf.log | jq .metrics.memory_mb'

# Terminal 4: Serial communication
tail -f logs/latest/serial/serial.log | grep -E "RX|TX|ERROR"
```

### Critical Alerts to Watch For:
- `FREEZE DETECTED`
- `High memory usage`
- `Serial timeout`
- `Browser throttling detected`
- `Queue full`
- `CRITICAL`

---

## Best Practices

1. **Always check `logs/latest/` first** - it's the current run
2. **Start with `app.log`** for overview, then drill into specific logs
3. **Use `grep` and `jq`** for quick filtering of large logs
4. **Keep terminal windows open** with `tail -f` during testing
5. **Save important runs** by copying the run directory before next restart
6. **Check file sizes** - logs over 100MB will rotate
7. **Look for patterns** - repeated errors often indicate the root cause

## Getting Help

If you can't diagnose an issue:
1. Create a tarball of the problem run: `tar -czf blast_logs_issue.tar.gz logs/run_YYYYMMDD_HHMMSS/`
2. Note the exact time the issue occurred
3. Include browser console output if relevant
4. Check system resources at time of issue (memory, CPU, disk)