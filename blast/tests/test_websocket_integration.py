"""WebSocket integration and real-time communication tests"""
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, Mock
import websockets
from fastapi.testclient import TestClient

from app import create_app
from app.config.settings import Settings
from app.core.websocket_manager import ConnectionManager


@pytest.fixture
def test_settings():
    """Create test settings"""
    return Settings()


@pytest.fixture
def test_app(test_settings):
    """Create test application"""
    return create_app(test_settings)


@pytest.fixture
def connection_manager():
    """Create fresh connection manager"""
    return ConnectionManager()


class TestWebSocketConnections:
    """Test WebSocket connection management"""
    
    @pytest.mark.asyncio
    async def test_websocket_connection_lifecycle(self, connection_manager):
        """Test WebSocket connection and disconnection"""
        mock_websocket = AsyncMock()
        client_id = "test_client"
        
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
    async def test_multiple_subscription_types(self, connection_manager):
        """Test connections to different subscription types"""
        mock_websockets = {
            "telemetry": AsyncMock(),
            "calibration": AsyncMock(),
            "health": AsyncMock()
        }
        
        client_ids = {
            "telemetry": "client_tel",
            "calibration": "client_cal", 
            "health": "client_health"
        }
        
        # Connect to different subscription types
        for sub_type, client_id in client_ids.items():
            await connection_manager.connect(
                mock_websockets[sub_type], 
                client_id, 
                sub_type
            )
        
        # Verify all connections
        for sub_type, client_id in client_ids.items():
            assert client_id in connection_manager.subscriptions[sub_type]
        
        # Test broadcasting to specific subscription
        await connection_manager.broadcast_to_subscription(
            {"type": "test", "data": "telemetry_test"}, 
            "telemetry"
        )
        
        # Only telemetry client should receive message
        mock_websockets["telemetry"].send_text.assert_called_once()
        mock_websockets["calibration"].send_text.assert_not_called()
        mock_websockets["health"].send_text.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self, connection_manager):
        """Test error handling in WebSocket connections"""
        mock_websocket = AsyncMock()
        mock_websocket.send_text.side_effect = Exception("Connection lost")
        
        client_id = "error_client"
        await connection_manager.connect(mock_websocket, client_id, "telemetry")
        
        # Sending message should handle error gracefully
        await connection_manager.send_personal_message(
            {"type": "test"}, 
            client_id
        )
        
        # Client should be disconnected after error
        assert client_id not in connection_manager.active_connections


class TestRealTimeDataStreaming:
    """Test real-time data streaming functionality"""
    
    @pytest.mark.asyncio
    async def test_telemetry_streaming_loop(self, connection_manager):
        """Test telemetry streaming background task"""
        # Mock data service
        mock_data_service = AsyncMock()
        mock_telemetry = Mock()
        mock_telemetry.dict.return_value = {
            "pressure_transducers": [{"sensor_id": "pt1", "value": 100.5}],
            "timestamp": "2024-01-01T12:00:00"
        }
        mock_data_service.get_calibrated_reading.return_value = mock_telemetry
        mock_data_service.is_running = True
        
        connection_manager.set_data_service(mock_data_service)
        
        # Connect a test client
        mock_websocket = AsyncMock()
        await connection_manager.connect(mock_websocket, "test_client", "telemetry")
        
        # Start streaming for a short time
        await connection_manager.start_telemetry_streaming(100)  # 100ms interval
        await asyncio.sleep(0.25)  # Let it run for 250ms
        await connection_manager.stop_telemetry_streaming()
        
        # Should have made multiple calls to get telemetry
        assert mock_data_service.get_calibrated_reading.call_count >= 2
        
        # Should have sent messages to client
        assert mock_websocket.send_text.call_count >= 2
    
    @pytest.mark.asyncio 
    async def test_calibration_updates(self, connection_manager):
        """Test calibration update broadcasting"""
        # Connect calibration subscribers
        clients = []
        for i in range(3):
            mock_websocket = AsyncMock()
            client_id = f"cal_client_{i}"
            await connection_manager.connect(mock_websocket, client_id, "calibration")
            clients.append((client_id, mock_websocket))
        
        # Broadcast calibration update
        calibration_result = {
            "success": True,
            "calibration_type": "auto_zero",
            "new_offset": 5.2
        }
        
        await connection_manager.broadcast_calibration_update("pt1", calibration_result)
        
        # All calibration clients should receive the update
        for client_id, mock_websocket in clients:
            mock_websocket.send_text.assert_called()
            
            # Verify message content
            call_args = mock_websocket.send_text.call_args[0][0]
            message = json.loads(call_args)
            
            assert message["type"] == "calibration_update"
            assert message["sensor_id"] == "pt1"
            assert message["data"] == calibration_result
    
    @pytest.mark.asyncio
    async def test_health_monitoring(self, connection_manager):
        """Test health monitoring updates"""
        mock_websocket = AsyncMock()
        await connection_manager.connect(mock_websocket, "health_client", "health")
        
        health_data = {
            "running": True,
            "data_source_type": "simulator",
            "error_count": 0
        }
        
        await connection_manager.broadcast_health_update(health_data)
        
        mock_websocket.send_text.assert_called()
        call_args = mock_websocket.send_text.call_args[0][0]
        message = json.loads(call_args)
        
        assert message["type"] == "health_update"
        assert message["data"] == health_data


class TestWebSocketEndpoints:
    """Test WebSocket API endpoints"""
    
    def test_websocket_stats_endpoint(self, test_app):
        """Test WebSocket statistics endpoint"""
        client = TestClient(test_app)
        response = client.get("/ws/stats")
        
        assert response.status_code == 200
        stats = response.json()
        
        assert "total_connections" in stats
        assert "subscriptions" in stats
        assert "streaming_active" in stats
        assert "connected_clients" in stats
        
        # Initially should have no connections
        assert stats["total_connections"] == 0
        assert all(count == 0 for count in stats["subscriptions"].values())


class TestWebSocketPerformance:
    """Test WebSocket performance characteristics"""
    
    @pytest.mark.asyncio
    async def test_message_throughput(self, connection_manager):
        """Test WebSocket message throughput"""
        mock_websocket = AsyncMock()
        await connection_manager.connect(mock_websocket, "perf_client", "telemetry")
        
        # Send many messages rapidly
        message_count = 100
        start_time = asyncio.get_event_loop().time()
        
        for i in range(message_count):
            await connection_manager.send_personal_message(
                {"type": "test", "index": i}, 
                "perf_client"
            )
        
        end_time = asyncio.get_event_loop().time()
        
        # Should handle messages efficiently
        total_time = end_time - start_time
        messages_per_second = message_count / total_time
        
        # Should handle at least 1000 messages per second
        assert messages_per_second > 1000, f"Message throughput too low: {messages_per_second:.1f} msg/s"
        
        # All messages should be sent
        assert mock_websocket.send_text.call_count == message_count
    
    @pytest.mark.asyncio
    async def test_concurrent_connections(self, connection_manager):
        """Test many concurrent WebSocket connections"""
        clients = []
        connection_count = 50
        
        # Create many concurrent connections
        for i in range(connection_count):
            mock_websocket = AsyncMock()
            client_id = f"client_{i}"
            await connection_manager.connect(mock_websocket, client_id, "telemetry")
            clients.append((client_id, mock_websocket))
        
        # Broadcast to all clients
        await connection_manager.broadcast_to_subscription(
            {"type": "load_test", "data": "concurrent_test"}, 
            "telemetry"
        )
        
        # All clients should receive the message
        for client_id, mock_websocket in clients:
            mock_websocket.send_text.assert_called()
        
        # Verify connection stats
        stats = connection_manager.get_connection_stats()
        assert stats["total_connections"] == connection_count
        assert stats["subscriptions"]["telemetry"] == connection_count


class TestWebSocketResilience:
    """Test WebSocket resilience and error recovery"""
    
    @pytest.mark.asyncio
    async def test_streaming_with_data_service_errors(self, connection_manager):
        """Test streaming continues despite data service errors"""
        # Mock data service that sometimes fails
        mock_data_service = AsyncMock()
        call_count = 0
        
        def get_reading_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:  # Fail every 3rd call
                raise Exception("Simulated data service error")
            
            mock_telemetry = Mock()
            mock_telemetry.dict.return_value = {"test": "data"}
            return mock_telemetry
        
        mock_data_service.get_calibrated_reading.side_effect = get_reading_side_effect
        mock_data_service.is_running = True
        
        connection_manager.set_data_service(mock_data_service)
        
        # Connect client
        mock_websocket = AsyncMock()
        await connection_manager.connect(mock_websocket, "resilience_client", "telemetry")
        
        # Start streaming
        await connection_manager.start_telemetry_streaming(50)  # 50ms interval
        await asyncio.sleep(0.2)  # Run for 200ms
        await connection_manager.stop_telemetry_streaming()
        
        # Should have attempted multiple reads despite errors
        assert mock_data_service.get_calibrated_reading.call_count >= 3
        
        # Should have sent successful messages (not all calls fail)
        assert mock_websocket.send_text.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_connection_cleanup_on_errors(self, connection_manager):
        """Test that connections are cleaned up properly on errors"""
        mock_websockets = []
        
        # Create connections where some will fail
        for i in range(5):
            mock_websocket = AsyncMock()
            if i % 2 == 0:  # Make every other websocket fail
                mock_websocket.send_text.side_effect = Exception("Connection lost")
            
            client_id = f"cleanup_client_{i}"
            await connection_manager.connect(mock_websocket, client_id, "telemetry")
            mock_websockets.append((client_id, mock_websocket))
        
        initial_count = connection_manager.get_connection_stats()["total_connections"]
        assert initial_count == 5
        
        # Broadcast message (will trigger cleanup of failed connections)
        await connection_manager.broadcast_to_subscription(
            {"type": "cleanup_test"}, 
            "telemetry"
        )
        
        # Failed connections should be cleaned up
        final_count = connection_manager.get_connection_stats()["total_connections"]
        assert final_count < initial_count  # Some connections should be removed
    
    @pytest.mark.asyncio
    async def test_data_service_unavailable(self, connection_manager):
        """Test behavior when data service is unavailable"""
        # No data service set
        mock_websocket = AsyncMock()
        await connection_manager.connect(mock_websocket, "no_data_client", "telemetry")
        
        # Start streaming without data service
        await connection_manager.start_telemetry_streaming(100)
        await asyncio.sleep(0.15)  # Let it try to run
        await connection_manager.stop_telemetry_streaming()
        
        # Should not crash, but also shouldn't send telemetry data
        # (This tests the graceful handling of missing data service)
        assert True  # Test passes if no exception is raised