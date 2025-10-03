"""Dependency injection for FastAPI"""
from fastapi import Depends, Request
from app.config.settings import Settings
from app.services.calibration import CalibrationService
from app.services.data_acquisition import DataAcquisitionService


def get_settings(request: Request) -> Settings:
    """Get application settings from app state"""
    return request.app.state.settings


def get_calibration_service(request: Request) -> CalibrationService:
    """Get calibration service from app state"""
    return request.app.state.calibration_service


def get_data_service(request: Request) -> DataAcquisitionService:
    """Get data acquisition service from app state"""
    return request.app.state.data_service