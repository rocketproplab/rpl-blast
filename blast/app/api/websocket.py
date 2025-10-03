"""WebSocket API endpoints for real-time communication"""
import asyncio
import json
import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from uuid import uuid4

from app.core.websocket_manager import connection_manager
from app.core.dependencies import get_data_service
from app.services.data_acquisition import DataAcquisitionService

logger = logging.getLogger(__name__)

websocket_router = APIRouter()


@websocket_router.websocket("/telemetry")
async def websocket_telemetry_endpoint(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None),
    data_service: DataAcquisitionService = Depends(get_data_service)
):
    """WebSocket endpoint for real-time telemetry streaming"""
    if not client_id:
        client_id = str(uuid4())
    
    await connection_manager.connect(websocket, client_id, "telemetry")
    
    try:
        # Send initial connection confirmation
        await connection_manager.send_personal_message({
            "type": "connection_established",
            "client_id": client_id,
            "subscription": "telemetry"
        }, client_id)
        
        # Send current telemetry data immediately
        try:
            current_telemetry = await data_service.get_calibrated_reading()
            await connection_manager.send_personal_message({
                "type": "telemetry_update",
                "data": current_telemetry.dict()
            }, client_id)
        except Exception as e:
            logger.error(f"Error sending initial telemetry to {client_id}: {e}")
        
        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client message (e.g., ping, commands)
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await connection_manager.send_personal_message({
                        "type": "pong",
                        "timestamp": message.get("timestamp")
                    }, client_id)
                elif message.get("type") == "request_current_data":
                    # Send latest telemetry on demand
                    telemetry = await data_service.get_calibrated_reading()
                    await connection_manager.send_personal_message({
                        "type": "telemetry_update",
                        "data": telemetry.dict()
                    }, client_id)
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message from {client_id}: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket connection error for {client_id}: {e}")
    finally:
        connection_manager.disconnect(client_id)


@websocket_router.websocket("/calibration")
async def websocket_calibration_endpoint(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None),
    data_service: DataAcquisitionService = Depends(get_data_service)
):
    """WebSocket endpoint for real-time calibration updates"""
    if not client_id:
        client_id = str(uuid4())
    
    await connection_manager.connect(websocket, client_id, "calibration")
    
    try:
        # Send initial connection confirmation
        await connection_manager.send_personal_message({
            "type": "connection_established",
            "client_id": client_id,
            "subscription": "calibration"
        }, client_id)
        
        # Keep connection alive and handle calibration commands
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "start_calibration":
                    # Handle real-time calibration request
                    sensor_id = message.get("sensor_id")
                    calibration_type = message.get("calibration_type")
                    kwargs = message.get("parameters", {})
                    
                    if not sensor_id or not calibration_type:
                        await connection_manager.send_personal_message({
                            "type": "error",
                            "message": "Missing sensor_id or calibration_type"
                        }, client_id)
                        continue
                    
                    try:
                        # Perform calibration
                        result = await data_service.perform_sensor_calibration(
                            sensor_id, calibration_type, **kwargs
                        )
                        
                        # Send result back to client
                        await connection_manager.send_personal_message({
                            "type": "calibration_complete",
                            "sensor_id": sensor_id,
                            "data": result.dict()
                        }, client_id)
                        
                        # Broadcast to all calibration subscribers
                        await connection_manager.broadcast_calibration_update(
                            sensor_id, result.dict()
                        )
                        
                    except Exception as e:
                        await connection_manager.send_personal_message({
                            "type": "calibration_error",
                            "sensor_id": sensor_id,
                            "error": str(e)
                        }, client_id)
                
                elif message.get("type") == "get_calibration_state":
                    sensor_id = message.get("sensor_id")
                    if sensor_id:
                        state = await data_service.get_calibration_state(sensor_id)
                        await connection_manager.send_personal_message({
                            "type": "calibration_state",
                            "sensor_id": sensor_id,
                            "data": state.dict() if state else None
                        }, client_id)
                        
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling calibration WebSocket message from {client_id}: {e}")
                break
                
    except Exception as e:
        logger.error(f"Calibration WebSocket connection error for {client_id}: {e}")
    finally:
        connection_manager.disconnect(client_id)


@websocket_router.websocket("/health")
async def websocket_health_endpoint(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None),
    data_service: DataAcquisitionService = Depends(get_data_service)
):
    """WebSocket endpoint for system health monitoring"""
    if not client_id:
        client_id = str(uuid4())
    
    await connection_manager.connect(websocket, client_id, "health")
    
    try:
        # Send initial connection confirmation
        await connection_manager.send_personal_message({
            "type": "connection_established",
            "client_id": client_id,
            "subscription": "health"
        }, client_id)
        
        # Send current health status
        health = await data_service.health_check()
        await connection_manager.send_personal_message({
            "type": "health_update",
            "data": health
        }, client_id)
        
        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "request_health_update":
                    # Send current health status on demand
                    health = await data_service.health_check()
                    await connection_manager.send_personal_message({
                        "type": "health_update",
                        "data": health
                    }, client_id)
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling health WebSocket message from {client_id}: {e}")
                break
                
    except Exception as e:
        logger.error(f"Health WebSocket connection error for {client_id}: {e}")
    finally:
        connection_manager.disconnect(client_id)


@websocket_router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    return connection_manager.get_connection_stats()