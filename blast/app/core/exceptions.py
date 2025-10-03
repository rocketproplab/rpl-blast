"""Custom exception handling"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from datetime import datetime


class BLASTException(Exception):
    """Base exception for BLAST application"""
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class SensorException(BLASTException):
    """Sensor-related errors"""
    pass


class CalibrationException(BLASTException):
    """Calibration procedure errors"""
    pass


class DataAcquisitionException(BLASTException):
    """Data source communication errors"""
    pass


class ConfigurationException(BLASTException):
    """Configuration validation errors"""
    pass


def add_exception_handlers(app: FastAPI):
    """Add global exception handlers to FastAPI app"""
    
    @app.exception_handler(BLASTException)
    async def blast_exception_handler(request: Request, exc: BLASTException):
        return JSONResponse(
            status_code=422,
            content={
                "error": exc.__class__.__name__,
                "message": exc.message,
                "error_code": exc.error_code,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred",
                "timestamp": datetime.now().isoformat()
            }
        )