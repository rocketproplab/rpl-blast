"""Main API router"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from app.core.dependencies import get_settings, get_data_service, get_calibration_service
from app.config.settings import Settings
from app.services.data_acquisition import DataAcquisitionService
from app.services.calibration import CalibrationService

# Create main API router
api_router = APIRouter()

@api_router.get("/health")
async def health_check(data_service: DataAcquisitionService = Depends(get_data_service)):
    """Health check endpoint with service status"""
    health = await data_service.health_check()
    return {
        "status": "healthy" if health["running"] else "degraded",
        "service": "BLAST",
        "data_acquisition": health
    }

@api_router.get("/config")
async def get_config(settings: Settings = Depends(get_settings)):
    """Get current configuration"""
    return {
        "data_source": settings.data_source,
        "telemetry_interval_ms": settings.telemetry_interval_ms,
        "pressure_transducers": [pt.dict() for pt in settings.pressure_transducers],
        "thermocouples": [tc.dict() for tc in settings.thermocouples],
        "load_cells": [lc.dict() for lc in settings.load_cells],
        "calibration": settings.calibration.dict()
    }

@api_router.get("/telemetry")
async def get_telemetry(data_service: DataAcquisitionService = Depends(get_data_service)):
    """Get current sensor telemetry data"""
    try:
        telemetry = await data_service.get_calibrated_reading()
        return telemetry.dict()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to read telemetry: {str(e)}")

@api_router.post("/sensors/{sensor_id}/calibrate")
async def calibrate_sensor(
    sensor_id: str,
    calibration_type: str,
    reference_value: Optional[float] = None,
    measured_value: Optional[float] = None,
    duration_ms: Optional[int] = None,
    data_service: DataAcquisitionService = Depends(get_data_service)
):
    """Perform sensor calibration"""
    try:
        kwargs = {}
        if reference_value is not None:
            kwargs['reference_value'] = reference_value
        if measured_value is not None:
            kwargs['measured_value'] = measured_value
        if duration_ms is not None:
            kwargs['duration_ms'] = duration_ms
        
        result = await data_service.perform_sensor_calibration(sensor_id, calibration_type, **kwargs)
        return result.dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Calibration failed: {str(e)}")

@api_router.get("/sensors/{sensor_id}/calibration")
async def get_sensor_calibration(
    sensor_id: str,
    data_service: DataAcquisitionService = Depends(get_data_service)
):
    """Get current calibration state for a sensor"""
    try:
        state = await data_service.get_calibration_state(sensor_id)
        if state:
            return state.dict()
        else:
            raise HTTPException(status_code=404, detail=f"No calibration state found for sensor {sensor_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get calibration state: {str(e)}")