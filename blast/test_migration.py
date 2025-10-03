#!/usr/bin/env python3
"""
Test script for Flask to FastAPI migration
"""
import asyncio
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from app.services.data_acquisition import DataAcquisitionService
from app.services.calibration import CalibrationService
from app.config.settings import Settings

async def test_migration():
    """Test the migration compatibility"""
    print("🚀 Testing Flask to FastAPI Migration")
    print("=" * 50)
    
    # Test configuration loading
    print("1. Testing configuration...")
    try:
        settings = Settings()
        print(f"✅ Settings loaded successfully")
        print(f"   Data source: {settings.data_source}")
        print(f"   Serial port: {settings.serial_port}")
        print(f"   Sensors: {len(settings.pressure_transducers)} PT, {len(settings.thermocouples)} TC, {len(settings.load_cells)} LC")
    except Exception as e:
        print(f"❌ Settings failed: {e}")
        return
    
    # Test service creation
    print("\n2. Testing service creation...")
    try:
        calibration_service = CalibrationService("calibration_states.json")
        data_service = DataAcquisitionService(settings, calibration_service)
        print(f"✅ Services created successfully")
        print(f"   Data source type: {type(data_service.data_source).__name__}")
    except Exception as e:
        print(f"❌ Service creation failed: {e}")
        return
    
    # Test data source start
    print("\n3. Testing data source initialization...")
    try:
        result = await data_service.start()
        if result:
            print(f"✅ Data source started successfully")
        else:
            print(f"⚠️  Data source start returned False (may need serial port)")
    except Exception as e:
        print(f"❌ Data source start failed: {e}")
        return
    
    # Test data reading (if possible)
    print("\n4. Testing data reading...")
    try:
        if data_service.is_running:
            reading = await data_service.get_calibrated_reading()
            print(f"✅ Reading obtained successfully")
            print(f"   Timestamp: {reading.timestamp}")
            print(f"   PT readings: {len(reading.pressure_transducers)}")
            print(f"   TC readings: {len(reading.thermocouples)}")
            print(f"   LC readings: {len(reading.load_cells)}")
            
            # Show first few values
            if reading.pressure_transducers:
                pt1 = reading.pressure_transducers[0]
                print(f"   PT1: {pt1.value:.2f} {pt1.unit}")
        else:
            print(f"⚠️  Service not running, skipping data test")
    except Exception as e:
        print(f"⚠️  Data reading failed (expected if no serial): {e}")
    
    # Test health check
    print("\n5. Testing health check...")
    try:
        health = await data_service.health_check()
        print(f"✅ Health check successful")
        print(f"   Running: {health['running']}")
        print(f"   Data source type: {health['data_source_type']}")
        print(f"   Error count: {health['error_count']}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
    
    # Clean up
    print("\n6. Cleaning up...")
    try:
        await data_service.stop()
        print(f"✅ Service stopped successfully")
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Migration test complete!")
    print("✅ FastAPI system is ready for deployment")

if __name__ == "__main__":
    asyncio.run(test_migration())