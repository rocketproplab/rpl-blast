"""Integration tests for the complete BLAST system"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app import create_app
from app.config.settings import Settings


@pytest.fixture
def test_settings():
    """Create test settings with realistic sensor configurations"""
    return Settings()


@pytest.fixture
def test_app(test_settings):
    """Create test application"""
    return create_app(test_settings)


@pytest.fixture
def client(test_app):
    """Create test client"""
    return TestClient(test_app)


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows"""
    
    def test_application_startup(self, client):
        """Test that application starts correctly"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "BLAST"
        assert "data_acquisition" in data
    
    def test_config_retrieval(self, client):
        """Test configuration endpoint returns valid data"""
        response = client.get("/api/config")
        assert response.status_code == 200
        
        config = response.json()
        assert "data_source" in config
        assert "pressure_transducers" in config
        assert "calibration" in config
        assert len(config["pressure_transducers"]) > 0
    
    def test_telemetry_data_flow(self, client):
        """Test telemetry data retrieval"""
        response = client.get("/api/telemetry")
        assert response.status_code == 200
        
        telemetry = response.json()
        assert "timestamp" in telemetry
        assert "pressure_transducers" in telemetry
        assert "thermocouples" in telemetry
        assert "load_cells" in telemetry
        assert "valve_states" in telemetry
    
    def test_calibration_workflow(self, client):
        """Test complete calibration workflow"""
        sensor_id = "pt1"
        
        # Test auto-zero calibration
        response = client.post(
            f"/api/sensors/{sensor_id}/calibrate",
            params={
                "calibration_type": "auto_zero",
                "duration_ms": 1000
            }
        )
        assert response.status_code == 200
        
        result = response.json()
        assert result["success"] is True
        assert result["sensor_id"] == sensor_id
        assert result["calibration_type"] == "auto_zero"
        assert "new_offset" in result
        
        # Test getting calibration state
        response = client.get(f"/api/sensors/{sensor_id}/calibration")
        assert response.status_code == 200
        
        state = response.json()
        assert state["sensor_id"] == sensor_id
        assert "zero_offset" in state
        assert "last_calibrated" in state
    
    def test_span_calibration_workflow(self, client):
        """Test span calibration workflow"""
        sensor_id = "pt2"
        
        response = client.post(
            f"/api/sensors/{sensor_id}/calibrate",
            params={
                "calibration_type": "span",
                "reference_value": 100.0,
                "measured_value": 95.0
            }
        )
        assert response.status_code == 200
        
        result = response.json()
        assert result["success"] is True
        assert result["calibration_type"] == "span"
        assert "new_span" in result
    
    def test_frontend_pages(self, client):
        """Test that frontend pages load correctly"""
        # Dashboard
        response = client.get("/")
        assert response.status_code == 200
        assert b"BLAST" in response.content
        
        # Pressure page
        response = client.get("/pressure")
        assert response.status_code == 200
        assert b"Pressure Transducers" in response.content
        
        # Check for calibration controls
        assert b"calibration-panel" in response.content
        assert b"auto-zero" in response.content
    
    def test_websocket_stats(self, client):
        """Test WebSocket statistics endpoint"""
        response = client.get("/ws/stats")
        assert response.status_code == 200
        
        stats = response.json()
        assert "total_connections" in stats
        assert "subscriptions" in stats
        assert "streaming_active" in stats


class TestErrorHandling:
    """Test error handling across the system"""
    
    def test_invalid_sensor_id(self, client):
        """Test calibration with invalid sensor ID"""
        response = client.post(
            "/api/sensors/invalid_sensor/calibrate",
            params={
                "calibration_type": "auto_zero",
                "duration_ms": 1000
            }
        )
        # Should not crash, might return error or handle gracefully
        assert response.status_code in [400, 404, 200]
    
    def test_invalid_calibration_type(self, client):
        """Test invalid calibration type"""
        response = client.post(
            "/api/sensors/pt1/calibrate",
            params={
                "calibration_type": "invalid_type",
                "duration_ms": 1000
            }
        )
        assert response.status_code == 400
    
    def test_missing_span_parameters(self, client):
        """Test span calibration without required parameters"""
        response = client.post(
            "/api/sensors/pt1/calibrate",
            params={
                "calibration_type": "span"
                # Missing reference_value and measured_value
            }
        )
        assert response.status_code == 400
    
    def test_nonexistent_calibration_state(self, client):
        """Test getting calibration state for uncalibrated sensor"""
        response = client.get("/api/sensors/nonexistent/calibration")
        assert response.status_code in [404, 500]


class TestPerformance:
    """Test system performance characteristics"""
    
    def test_concurrent_calibrations(self, client):
        """Test multiple concurrent calibration requests"""
        import threading
        import time
        
        results = []
        
        def calibrate_sensor(sensor_id):
            response = client.post(
                f"/api/sensors/{sensor_id}/calibrate",
                params={
                    "calibration_type": "auto_zero",
                    "duration_ms": 500
                }
            )
            results.append(response.status_code)
        
        # Start multiple calibrations concurrently
        threads = []
        sensor_ids = ["pt1", "pt2", "pt3"]
        
        for sensor_id in sensor_ids:
            thread = threading.Thread(target=calibrate_sensor, args=(sensor_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        # All should succeed
        assert all(status == 200 for status in results)
        assert len(results) == len(sensor_ids)
    
    def test_rapid_telemetry_requests(self, client):
        """Test rapid telemetry data requests"""
        import time
        
        start_time = time.time()
        responses = []
        
        # Make 10 rapid requests
        for _ in range(10):
            response = client.get("/api/telemetry")
            responses.append(response.status_code)
        
        end_time = time.time()
        
        # All should succeed
        assert all(status == 200 for status in responses)
        
        # Should complete reasonably quickly (within 2 seconds)
        assert (end_time - start_time) < 2.0


class TestDataConsistency:
    """Test data consistency across the system"""
    
    def test_calibration_persistence(self, client):
        """Test that calibration data persists correctly"""
        sensor_id = "pt1"
        
        # Perform calibration
        calibration_response = client.post(
            f"/api/sensors/{sensor_id}/calibrate",
            params={
                "calibration_type": "auto_zero",
                "duration_ms": 1000
            }
        )
        assert calibration_response.status_code == 200
        
        calibration_result = calibration_response.json()
        new_offset = calibration_result["new_offset"]
        
        # Get calibration state
        state_response = client.get(f"/api/sensors/{sensor_id}/calibration")
        assert state_response.status_code == 200
        
        state = state_response.json()
        
        # Offset should match
        assert abs(state["zero_offset"] - new_offset) < 0.001
    
    def test_telemetry_calibration_integration(self, client):
        """Test that telemetry reflects calibration status"""
        sensor_id = "pt1"
        
        # Get initial telemetry
        initial_response = client.get("/api/telemetry")
        assert initial_response.status_code == 200
        
        # Perform calibration
        client.post(
            f"/api/sensors/{sensor_id}/calibrate",
            params={
                "calibration_type": "auto_zero",
                "duration_ms": 1000
            }
        )
        
        # Get updated telemetry
        updated_response = client.get("/api/telemetry")
        assert updated_response.status_code == 200
        
        updated_telemetry = updated_response.json()
        
        # Find the calibrated sensor in telemetry
        pt_sensor = None
        for sensor in updated_telemetry["pressure_transducers"]:
            if sensor["sensor_id"] == sensor_id:
                pt_sensor = sensor
                break
        
        assert pt_sensor is not None
        assert pt_sensor["calibrated"] is True


class TestSystemResilience:
    """Test system resilience and recovery"""
    
    @patch('app.services.data_acquisition.DataAcquisitionService.get_calibrated_reading')
    def test_telemetry_service_failure(self, mock_get_reading, client):
        """Test behavior when telemetry service fails"""
        # Mock service failure
        mock_get_reading.side_effect = Exception("Service unavailable")
        
        response = client.get("/api/telemetry")
        assert response.status_code == 503
        
        error_detail = response.json()
        assert "Failed to read telemetry" in error_detail["detail"]
    
    def test_configuration_validation(self, test_settings):
        """Test that configuration is properly validated"""
        # Test with valid settings
        app = create_app(test_settings)
        assert app is not None
        
        # Configuration should have required sensor configurations
        assert len(test_settings.pressure_transducers) > 0
        assert test_settings.telemetry_interval_ms > 0
        assert test_settings.calibration is not None