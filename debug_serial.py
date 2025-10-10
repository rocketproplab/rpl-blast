#!/usr/bin/env python3
"""Debug script to see raw serial data from hardware"""

import serial
import time

port = "/dev/cu.usbmodem21301"  # Your port from config
baudrate = 115200

try:
    ser = serial.Serial(port=port, baudrate=baudrate, timeout=1.0)
    print(f"Connected to {port}")
    print("Raw data from hardware (press Ctrl+C to stop):")
    print("-" * 50)
    
    for i in range(20):  # Show 20 lines then stop
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('ascii', errors='ignore').strip()
                if line:
                    print(f"[{i:2d}] {line}")
        except KeyboardInterrupt:
            break
        time.sleep(0.1)
    
    ser.close()
    print("\nDone!")
    
except Exception as e:
    print(f"Error: {e}")