#!/usr/bin/env python3
"""
Simple FastAPI server for testing the migration
"""
import sys
from pathlib import Path
import asyncio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from app.services.data_acquisition import DataAcquisitionService
from app.services.calibration import CalibrationService
from app.config.settings import Settings

# Create FastAPI app
app = FastAPI(title="BLAST Migration Test")

# Global services
data_service = None
settings = None

# Mount static files FIRST (before any routes that might use them)
from pathlib import Path
static_dir = Path("app/static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    print("✅ Static files mounted")
else:
    print(f"⚠️  Static directory not found: {static_dir}")

# Templates
templates = None
template_dir = Path("app/templates")
if template_dir.exists():
    templates = Jinja2Templates(directory="app/templates")
    print("✅ Templates loaded")
else:
    print(f"⚠️  Template directory not found: {template_dir}")

@app.on_event("startup")
async def startup_event():
    global data_service, settings
    print("🚀 Starting BLAST FastAPI Migration Server...")
    
    # Initialize services
    settings = Settings()
    calibration_service = CalibrationService("calibration_states.json")
    data_service = DataAcquisitionService(settings, calibration_service)
    
    # Start data acquisition
    result = await data_service.start()
    if result:
        print("✅ Data acquisition started successfully")
    else:
        print("⚠️  Data acquisition failed to start (likely no serial device)")
    
    print("🎯 Server ready!")

@app.on_event("shutdown")
async def shutdown_event():
    global data_service
    if data_service:
        await data_service.stop()
    print("👋 Server shutdown complete")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page"""
    if templates:
        return templates.TemplateResponse("pressure.html", {
            "request": request,
            "pressure_transducers": settings.pressure_transducers if settings else []
        })
    else:
        return HTMLResponse("""
        <html>
            <head><title>BLAST Migration Test</title></head>
            <body>
                <h1>🚀 BLAST FastAPI Migration Test</h1>
                <p>✅ FastAPI server is running!</p>
                <p>⚠️  Templates not available - using basic HTML</p>
                <div>
                    <h2>API Endpoints:</h2>
                    <ul>
                        <li><a href="/health">/health</a> - Health check</li>
                        <li><a href="/data">/data</a> - Get sensor data</li>
                        <li><a href="/api/calibration/states">/api/calibration/states</a> - Calibration states</li>
                    </ul>
                </div>
            </body>
        </html>
        """)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if data_service:
        health = await data_service.health_check()
        return {
            "status": "ok",
            "migration": "active", 
            "data_acquisition": health
        }
    else:
        return {
            "status": "error",
            "message": "Data service not initialized"
        }

@app.get("/data")
async def get_data():
    """Get current sensor data"""
    if not data_service or not data_service.is_running:
        # Return simulated data for testing
        return {
            "timestamp": "2025-01-02T00:00:00",
            "pressure_transducers": [
                {"sensor_id": "pt1", "value": 12.5, "unit": "psi", "calibrated": False},
                {"sensor_id": "pt2", "value": 15.2, "unit": "psi", "calibrated": False}
            ],
            "thermocouples": [
                {"sensor_id": "tc1", "value": 22.5, "unit": "celsius", "calibrated": False}
            ],
            "load_cells": [
                {"sensor_id": "lc1", "value": 125.0, "unit": "lbs", "calibrated": False}
            ],
            "valve_states": {"fcv1": False, "fcv2": True},
            "system_status": {"status": "simulation", "message": "No serial device connected"}
        }
    
    try:
        reading = await data_service.get_calibrated_reading()
        return reading.dict()
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": "2025-01-02T00:00:00",
            "pressure_transducers": [],
            "thermocouples": [],
            "load_cells": [],
            "valve_states": {},
            "system_status": {"status": "error", "message": str(e)}
        }

@app.get("/api/calibration/states")
async def get_calibration_states():
    """Get all calibration states"""
    if data_service and data_service.calibration_service:
        return {
            "states": {
                sensor_id: state.dict() 
                for sensor_id, state in data_service.calibration_service.calibration_states.items()
            }
        }
    return {"states": {}}

if __name__ == "__main__":
    import uvicorn
    print("🌟 Starting BLAST Migration Test Server")
    print("📍 http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")