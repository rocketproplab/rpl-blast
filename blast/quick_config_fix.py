#!/usr/bin/env python3
"""
Quick fix to switch to simulator mode by directly editing the config
"""
import yaml
from pathlib import Path

def switch_to_simulator():
    """Switch config to simulator mode"""
    config_path = Path("app/config/config.yaml")
    
    if config_path.exists():
        # Read current config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Update data source
        config['data_source'] = 'simulator'
        
        # Write back
        with open(config_path, 'w') as f:
            yaml.safe_dump(config, f, default_flow_style=False)
        
        print("✅ Config updated to simulator mode")
        
        # Verify
        with open(config_path, 'r') as f:
            verify_config = yaml.safe_load(f)
        print(f"✅ Verified: data_source = {verify_config.get('data_source')}")
    else:
        print("❌ Config file not found")

if __name__ == "__main__":
    switch_to_simulator()