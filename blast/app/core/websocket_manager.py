"""WebSocket connection manager for real-time telemetry streaming"""
import asyncio
import json
import logging
from typing import Dict, Set, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

from app.models.sensors import TelemetryPacket
from app.services.data_acquisition import DataAcquisitionService

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time data streaming"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = {
            "telemetry": set(),
            "calibration": set(),
            "health": set()
        }
        self._streaming_task: Optional[asyncio.Task] = None
        self._data_service: Optional[DataAcquisitionService] = None
        
    async def connect(self, websocket: WebSocket, client_id: str, subscription_type: str = "telemetry"):
        """Accept new WebSocket connection and add to subscriptions"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        
        if subscription_type in self.subscriptions:
            self.subscriptions[subscription_type].add(client_id)
            logger.info(f"Client {client_id} connected and subscribed to {subscription_type}")
        else:
            logger.warning(f"Unknown subscription type: {subscription_type}")
            
    def disconnect(self, client_id: str):
        """Remove client from all subscriptions and connections"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            
        # Remove from all subscriptions
        for subscription_set in self.subscriptions.values():
            subscription_set.discard(client_id)
            
        logger.info(f"Client {client_id} disconnected")
    
    async def send_personal_message(self, message: dict, client_id: str):
        """Send message to specific client"""
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast_to_subscription(self, message: dict, subscription_type: str):
        """Broadcast message to all clients subscribed to a type"""
        if subscription_type not in self.subscriptions:
            logger.warning(f"Unknown subscription type: {subscription_type}")
            return
            
        disconnected_clients = []
        
        for client_id in self.subscriptions[subscription_type].copy():
            try:
                if client_id in self.active_connections:
                    websocket = self.active_connections[client_id]
                    await websocket.send_text(json.dumps(message))
            except WebSocketDisconnect:
                disconnected_clients.append(client_id)
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    def set_data_service(self, data_service: DataAcquisitionService):
        """Set the data acquisition service for streaming"""
        self._data_service = data_service
        
    async def start_telemetry_streaming(self, interval_ms: int = 100):
        """Start background task for streaming telemetry data"""
        if self._streaming_task and not self._streaming_task.done():
            logger.warning("Telemetry streaming already running")
            return
            
        self._streaming_task = asyncio.create_task(
            self._telemetry_streaming_loop(interval_ms)
        )
        logger.info(f"Started telemetry streaming with {interval_ms}ms interval")
        
    async def stop_telemetry_streaming(self):
        """Stop the telemetry streaming task"""
        if self._streaming_task and not self._streaming_task.done():
            self._streaming_task.cancel()
            try:
                await self._streaming_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped telemetry streaming")
    
    async def _telemetry_streaming_loop(self, interval_ms: int):
        """Background loop for streaming telemetry data"""
        interval_seconds = interval_ms / 1000.0
        
        while True:
            try:
                if not self._data_service or not self._data_service.is_running:
                    await asyncio.sleep(interval_seconds)
                    continue
                
                # Only stream if we have subscribers
                if not self.subscriptions["telemetry"]:
                    await asyncio.sleep(interval_seconds)
                    continue
                
                # Get latest telemetry data
                telemetry = await self._data_service.get_calibrated_reading()
                
                # Prepare message for streaming
                message = {
                    "type": "telemetry_update",
                    "timestamp": datetime.now().isoformat(),
                    "data": telemetry.dict()
                }
                
                # Broadcast to all telemetry subscribers
                await self.broadcast_to_subscription(message, "telemetry")
                
            except Exception as e:
                logger.error(f"Error in telemetry streaming loop: {e}")
                
            await asyncio.sleep(interval_seconds)
    
    async def broadcast_calibration_update(self, sensor_id: str, calibration_result: dict):
        """Broadcast calibration completion to subscribers"""
        message = {
            "type": "calibration_update",
            "timestamp": datetime.now().isoformat(),
            "sensor_id": sensor_id,
            "data": calibration_result
        }
        await self.broadcast_to_subscription(message, "calibration")
    
    async def broadcast_health_update(self, health_data: dict):
        """Broadcast system health updates to subscribers"""
        message = {
            "type": "health_update",
            "timestamp": datetime.now().isoformat(),
            "data": health_data
        }
        await self.broadcast_to_subscription(message, "health")
    
    def get_connection_stats(self) -> dict:
        """Get statistics about current connections"""
        return {
            "total_connections": len(self.active_connections),
            "subscriptions": {
                sub_type: len(clients) 
                for sub_type, clients in self.subscriptions.items()
            },
            "streaming_active": self._streaming_task and not self._streaming_task.done(),
            "connected_clients": list(self.active_connections.keys())
        }


# Global connection manager instance
connection_manager = ConnectionManager()