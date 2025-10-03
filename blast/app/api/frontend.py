"""Frontend routes for serving HTML templates"""
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.dependencies import get_settings
from app.config.settings import Settings

# Get the app directory path
app_dir = Path(__file__).parent.parent

# Initialize templates
templates = Jinja2Templates(directory=str(app_dir / "templates"))

# Create frontend router
frontend_router = APIRouter()

@frontend_router.get("/")
async def index(request: Request, settings: Settings = Depends(get_settings)):
    """Main dashboard page"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "settings": settings
    })

@frontend_router.get("/pressure")
async def pressure_page(request: Request, settings: Settings = Depends(get_settings)):
    """Pressure transducers page with calibration controls"""
    return templates.TemplateResponse("pressure.html", {
        "request": request,
        "pressure_transducers": settings.pressure_transducers,
        "settings": settings
    })

@frontend_router.get("/thermocouples")
async def thermocouples_page(request: Request, settings: Settings = Depends(get_settings)):
    """Thermocouples and load cells page"""
    return templates.TemplateResponse("thermocouples.html", {
        "request": request,
        "thermocouples": settings.thermocouples,
        "load_cells": settings.load_cells,
        "settings": settings
    })

@frontend_router.get("/valves")
async def valves_page(request: Request, settings: Settings = Depends(get_settings)):
    """Flow control valves page"""
    return templates.TemplateResponse("valves.html", {
        "request": request,
        "flow_control_valves": settings.flow_control_valves,
        "settings": settings
    })