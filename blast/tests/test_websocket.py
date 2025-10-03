"""Tests for WebSocket functionality"""
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, Mock
from fastapi.testclient import TestClient
from fastapi import WebSocket

from app import create_app
from app.config.settings import Settings
from app.core.websocket_manager import ConnectionManager
from app.models.sensors import TelemetryPacket, SensorReading


@pytest.fixture
def test_settings():
    """Create test settings"""
    return Settings()


@pytest.fixture
def test_app(test_settings):
    """Create test FastAPI app"""
    return create_app(test_settings)


@pytest.fixture
def connection_manager():
    """Create fresh connection manager for testing"""
    return ConnectionManager()


@pytest.fixture
def mock_data_service():
    """Create mock data acquisition service"""
    mock_service = AsyncMock()
    mock_service.is_running = True
    
    # Mock telemetry data
    mock_telemetry = TelemetryPacket(
        pressure_transducers=[
            SensorReading(sensor_id="pt1", value=100.5, unit="psi", calibrated=True),
            SensorReading(sensor_id="pt2", value=200.3, unit="psi", calibrated=True)
        ],
        thermocouples=[
            SensorReading(sensor_id="tc1", value=25.4, unit="celsius", calibrated=True)
        ],
        load_cells=[
            SensorReading(sensor_id="lc1", value=1500.0, unit="lbs", calibrated=True)
        ],
        valve_states={"fcv1": True, "fcv2": False}
    )
    
    mock_service.get_calibrated_reading.return_value = mock_telemetry
    mock_service.health_check.return_value = {
        "running": True,
        "data_source_type": "simulator",
        "error_count": 0
    }
    
    return mock_service


class TestConnectionManager:
    """Test WebSocket connection management"""
    
    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self, connection_manager):
        """Test basic connection and disconnection"""
        mock_websocket = AsyncMock()
        client_id = "test_client_1"
        
        # Test connection
        await connection_manager.connect(mock_websocket, client_id, "telemetry")
        
        assert client_id in connection_manager.active_connections
        assert client_id in connection_manager.subscriptions["telemetry"]
        mock_websocket.accept.assert_called_once()
        
        # Test disconnection
        connection_manager.disconnect(client_id)
        
        assert client_id not in connection_manager.active_connections
        assert client_id not in connection_manager.subscriptions["telemetry"]
    
    @pytest.mark.asyncio
    async def test_send_personal_message(self, connection_manager):
        """Test sending message to specific client"""
        mock_websocket = AsyncMock()
        client_id = "test_client_1"
        
        await connection_manager.connect(mock_websocket, client_id)
        
        message = {"type": "test", "data": "hello"}
        await connection_manager.send_personal_message(message, client_id)
        
        mock_websocket.send_text.assert_called_once_with(json.dumps(message))
    
    @pytest.mark.asyncio
    async def test_broadcast_to_subscription(self, connection_manager):
        """Test broadcasting to subscription groups"""
        # Connect multiple clients
        clients = []
        for i in range(3):
            mock_websocket = AsyncMock()
            client_id = f"client_{i}"
            await connection_manager.connect(mock_websocket, client_id, "telemetry")
            clients.append((client_id, mock_websocket))
        
        # Broadcast message
        message = {"type": "broadcast", "data": "all clients"}
        await connection_manager.broadcast_to_subscription(message, "telemetry")
        
        # Verify all clients received the message
        for client_id, mock_websocket in clients:
            mock_websocket.send_text.assert_called_with(json.dumps(message))
    
    @pytest.mark.asyncio
    async def test_telemetry_streaming_loop(self, connection_manager, mock_data_service):
        """Test telemetry streaming background task"""
        connection_manager.set_data_service(mock_data_service)
        
        # Connect a client
        mock_websocket = AsyncMock()
        await connection_manager.connect(mock_websocket, "client_1", "telemetry")
        
        # Start streaming with short interval for testing
        await connection_manager.start_telemetry_streaming(50)  # 50ms
        
        # Let it run for a bit
        await asyncio.sleep(0.2)  # 200ms should allow 3-4 iterations
        
        # Stop streaming
        await connection_manager.stop_telemetry_streaming()
        
        # Verify data service was called
        assert mock_data_service.get_calibrated_reading.call_count >= 2
        assert mock_websocket.send_text.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_calibration_broadcast(self, connection_manager):
        """Test calibration update broadcasting"""
        # Connect calibration subscribers
        clients = []
        for i in range(2):
            mock_websocket = AsyncMock()
            client_id = f"cal_client_{i}"
            await connection_manager.connect(mock_websocket, client_id, "calibration")
            clients.append((client_id, mock_websocket))
        
        # Broadcast calibration update
        sensor_id = "pt1"
        result_data = {"success": True, "new_offset": 10.5}
        
        await connection_manager.broadcast_calibration_update(sensor_id, result_data)
        
        # Verify all calibration clients received the update
        for client_id, mock_websocket in clients:
            mock_websocket.send_text.assert_called()
            call_args = mock_websocket.send_text.call_args[0][0]
            message = json.loads(call_args)
            
            assert message["type"] == "calibration_update"
            assert message["sensor_id"] == sensor_id
            assert message["data"] == result_data
    
    def test_connection_stats(self, connection_manager):
        """Test connection statistics"""
        stats = connection_manager.get_connection_stats()
        
        assert "total_connections" in stats
        assert "subscriptions" in stats
        assert "streaming_active" in stats
        assert "connected_clients" in stats
        
        assert stats["total_connections"] == 0
        assert stats["subscriptions"]["telemetry"] == 0


class TestWebSocketEndpoints:
    """Test WebSocket API endpoints"""
    
    def test_websocket_stats_endpoint(self, test_app):
        """Test WebSocket statistics endpoint"""
        with TestClient(test_app) as client:
            response = client.get("/ws/stats")
            assert response.status_code == 200
            
            data = response.json()
            assert "total_connections" in data
            assert "subscriptions" in data


class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality"""
    
    @pytest.mark.asyncio
    async def test_websocket_lifecycle_integration(self, connection_manager, mock_data_service):
        """Test complete WebSocket lifecycle with data service"""
        connection_manager.set_data_service(mock_data_service)
        
        # Simulate client connection
        mock_websocket = AsyncMock()
        client_id = "integration_client"
        
        await connection_manager.connect(mock_websocket, client_id, "telemetry")
        
        # Start streaming
        await connection_manager.start_telemetry_streaming(100)
        
        # Let it run briefly
        await asyncio.sleep(0.15)
        
        # Simulate calibration
        await connection_manager.broadcast_calibration_update("pt1", {
            "success": True,
            "calibration_type": "auto_zero",
            "new_offset": 5.2
        })
        
        # Stop streaming
        await connection_manager.stop_telemetry_streaming()
        
        # Verify service interactions
        assert mock_data_service.get_calibrated_reading.called
        assert mock_websocket.send_text.called
        
        # Disconnect
        connection_manager.disconnect(client_id)
        assert client_id not in connection_manager.active_connections
    
    @pytest.mark.asyncio
    async def test_error_handling_in_streaming(self, connection_manager):
        """Test error handling during streaming"""
        # Mock data service that raises errors
        mock_service = AsyncMock()
        mock_service.is_running = True
        mock_service.get_calibrated_reading.side_effect = Exception("Sensor error")
        
        connection_manager.set_data_service(mock_service)
        
        # Connect client
        mock_websocket = AsyncMock()
        await connection_manager.connect(mock_websocket, "error_client", "telemetry")
        
        # Start streaming (should handle errors gracefully)
        await connection_manager.start_telemetry_streaming(50)
        
        # Let it run with errors
        await asyncio.sleep(0.15)
        
        # Stop streaming
        await connection_manager.stop_telemetry_streaming()
        
        # Verify service was called despite errors
        assert mock_service.get_calibrated_reading.called
    
    @pytest.mark.asyncio
    async def test_concurrent_connections(self, connection_manager, mock_data_service):
        """Test handling multiple concurrent connections"""
        connection_manager.set_data_service(mock_data_service)
        
        # Connect multiple clients to different subscription types
        clients = []
        for i in range(5):
            mock_websocket = AsyncMock()
            client_id = f"concurrent_client_{i}"
            subscription = "telemetry" if i < 3 else "calibration"
            
            await connection_manager.connect(mock_websocket, client_id, subscription)
            clients.append((client_id, mock_websocket, subscription))
        
        # Start streaming
        await connection_manager.start_telemetry_streaming(50)
        await asyncio.sleep(0.1)
        
        # Broadcast to all subscription types
        await connection_manager.broadcast_calibration_update("pt1", {"test": "data"})
        
        # Stop streaming
        await connection_manager.stop_telemetry_streaming()
        
        # Verify proper distribution of messages
        telemetry_clients = [c for c in clients if c[2] == "telemetry"]
        calibration_clients = [c for c in clients if c[2] == "calibration"]
        
        assert len(telemetry_clients) == 3
        assert len(calibration_clients) == 2
        
        # All telemetry clients should have received streaming updates
        for client_id, mock_websocket, _ in telemetry_clients:
            assert mock_websocket.send_text.call_count >= 1
        
        # All calibration clients should have received the broadcast
        for client_id, mock_websocket, _ in calibration_clients:
            assert mock_websocket.send_text.called