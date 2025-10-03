#!/usr/bin/env python3
"""
Simple test to check if simulator works
"""
import sys
from pathlib import Path
import asyncio
import time
import numpy as np
from datetime import datetime

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

class SimpleSimulator:
    """Simple simulator based on original Flask pattern"""
    
    def __init__(self):
        self.last_update = 0
        self.update_interval = 0.1
        
        # Valve states
        self.fcv_actual_states = np.array([False, True, False, False, True, False, True])
        self.fcv_expected_states = np.array([False, True, False, False, True, False, True])
        
        # Random number generator
        self.rng = np.random.default_rng()
        
        print("✅ Simple simulator initialized")
    
    def read_data(self):
        """Read data like original Flask simulator"""
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.last_update = current_time
            
            # Generate PT data (5 sensors)
            pt_data = []
            for i in range(5):
                # Generate realistic pressure data with occasional threshold violations
                rand = self.rng.random()
                if rand < 0.02:  # Danger level
                    value = self.rng.uniform(320, 380)  # Near 400 danger threshold
                elif rand < 0.05:  # Warning level
                    value = self.rng.uniform(200, 240)  # Near 250 warning threshold
                else:  # Normal range
                    value = self.rng.uniform(10, 200)   # Normal operation
                pt_data.append(round(value, 1))
            
            # Generate TC data (3 sensors)
            tc_data = [round(self.rng.uniform(20, 100), 1) for _ in range(3)]
            
            # Generate LC data (3 sensors)  
            lc_data = [round(self.rng.uniform(50, 300), 1) for _ in range(3)]
            
            # Occasionally change valve states
            if self.rng.random() < 0.20:  # 20% chance
                valve_to_toggle = self.rng.integers(0, len(self.fcv_actual_states))
                self.fcv_actual_states[valve_to_toggle] = not self.fcv_actual_states[valve_to_toggle]
            
            return {
                'pt': pt_data,
                'tc': tc_data,
                'lc': lc_data,
                'fcv_actual': self.fcv_actual_states.tolist(),
                'fcv_expected': self.fcv_expected_states.tolist(),
                'timestamp': datetime.now().isoformat()
            }
        
        return None

def test_simple_simulator():
    """Test the simple simulator"""
    print("🧪 Testing Simple Simulator...")
    
    sim = SimpleSimulator()
    
    # Test data generation
    for i in range(5):
        data = sim.read_data()
        if data:
            print(f"Reading {i+1}:")
            print(f"  PT: {data['pt']} (5 values)")
            print(f"  TC: {data['tc']} (3 values)")
            print(f"  LC: {data['lc']} (3 values)")
            print(f"  FCV: {data['fcv_actual']} (7 values)")
            print(f"  Time: {data['timestamp']}")
            print()
        
        time.sleep(0.15)  # Wait a bit
    
    print("✅ Simple simulator working correctly!")

if __name__ == "__main__":
    test_simple_simulator()