"""BLAST FastAPI Application Factory"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config.settings import Settings
from app.core.exceptions import add_exception_handlers
from app.core.middleware import add_middleware
from app.core.websocket_manager import connection_manager
from app.api.router import api_router
from app.api.websocket import websocket_router
from app.api.frontend import frontend_router
from app.services.calibration import CalibrationService
from app.services.data_acquisition import DataAcquisitionService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    settings = app.state.settings
    calibration_service = CalibrationService()
    data_service = DataAcquisitionService(settings, calibration_service)
    
    # Start data acquisition service
    await data_service.start()
    
    # Store services in app state
    app.state.calibration_service = calibration_service
    app.state.data_service = data_service
    
    # Configure WebSocket manager
    connection_manager.set_data_service(data_service)
    await connection_manager.start_telemetry_streaming(settings.telemetry_interval_ms)
    
    yield
    
    # Shutdown
    await connection_manager.stop_telemetry_streaming()
    await data_service.stop()


def create_app(settings: Settings = None) -> FastAPI:
    """Create and configure FastAPI application"""
    if settings is None:
        settings = Settings()
    
    app = FastAPI(
        title="BLAST Sensor Monitoring System",
        description="Real-time rocket sensor monitoring with calibration",
        version="2.0.0",
        lifespan=lifespan
    )
    
    # Add CORS middleware for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    add_middleware(app)
    
    # Add exception handlers
    add_exception_handlers(app)
    
    # Mount static files
    static_path = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    
    # Include API routers
    app.include_router(api_router, prefix="/api")
    app.include_router(websocket_router, prefix="/ws")
    app.include_router(frontend_router)
    
    # Store settings for dependency injection
    app.state.settings = settings
    
    return app