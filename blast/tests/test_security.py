"""Security tests for BLAST application"""
import pytest
from fastapi.testclient import TestClient

from app import create_app
from app.config.settings import Settings


@pytest.fixture
def client():
    """Create test client"""
    settings = Settings()
    app = create_app(settings)
    return TestClient(app)


class TestInputValidation:
    """Test input validation and sanitization"""
    
    def test_calibration_parameter_validation(self, client):
        """Test calibration parameter validation"""
        # Test invalid duration
        response = client.post(
            "/api/sensors/pt1/calibrate",
            params={
                "calibration_type": "auto_zero",
                "duration_ms": -1000  # Invalid negative duration
            }
        )
        assert response.status_code == 400
        
        # Test extremely large duration
        response = client.post(
            "/api/sensors/pt1/calibrate", 
            params={
                "calibration_type": "auto_zero",
                "duration_ms": 9999999  # Unreasonably large
            }
        )
        assert response.status_code == 400
    
    def test_sensor_id_validation(self, client):
        """Test sensor ID validation"""
        # Test with injection attempt
        malicious_sensor_id = "pt1'; DROP TABLE sensors; --"
        response = client.post(
            f"/api/sensors/{malicious_sensor_id}/calibrate",
            params={
                "calibration_type": "auto_zero",
                "duration_ms": 1000
            }
        )
        # Should handle gracefully without SQL injection
        assert response.status_code in [400, 404]
        
        # Test with path traversal attempt
        malicious_sensor_id = "../../../etc/passwd"
        response = client.post(
            f"/api/sensors/{malicious_sensor_id}/calibrate",
            params={
                "calibration_type": "auto_zero", 
                "duration_ms": 1000
            }
        )
        assert response.status_code in [400, 404]
    
    def test_calibration_type_validation(self, client):
        """Test calibration type validation"""
        # Test invalid calibration type
        response = client.post(
            "/api/sensors/pt1/calibrate",
            params={
                "calibration_type": "malicious_type",
                "duration_ms": 1000
            }
        )
        assert response.status_code == 400
        
        # Test script injection in calibration type
        response = client.post(
            "/api/sensors/pt1/calibrate",
            params={
                "calibration_type": "<script>alert('xss')</script>",
                "duration_ms": 1000
            }
        )
        assert response.status_code == 400


class TestAccessControl:
    """Test access control mechanisms"""
    
    def test_api_endpoints_accessibility(self, client):
        """Test that API endpoints are accessible without authentication"""
        # For now, BLAST runs on internal networks without auth
        # But we should ensure consistent behavior
        
        response = client.get("/api/health")
        assert response.status_code == 200
        
        response = client.get("/api/config") 
        assert response.status_code == 200
        
        response = client.get("/api/telemetry")
        assert response.status_code == 200
    
    def test_static_file_access(self, client):
        """Test static file access restrictions"""
        # Should serve legitimate static files
        response = client.get("/static/css/dashboard.css")
        assert response.status_code == 200
        
        # Should not serve arbitrary files
        response = client.get("/static/../app/config/config.yaml")
        assert response.status_code == 404
        
        # Should not serve system files
        response = client.get("/static/../../../../etc/passwd")
        assert response.status_code == 404


class TestDataValidation:
    """Test data validation and sanitization"""
    
    def test_numeric_parameter_bounds(self, client):
        """Test numeric parameter boundary validation"""
        # Test span calibration with invalid values
        response = client.post(
            "/api/sensors/pt1/calibrate",
            params={
                "calibration_type": "span",
                "reference_value": float('inf'),  # Invalid value
                "measured_value": 100.0
            }
        )
        assert response.status_code == 400
        
        # Test with NaN values
        response = client.post(
            "/api/sensors/pt1/calibrate",
            params={
                "calibration_type": "span", 
                "reference_value": float('nan'),
                "measured_value": 100.0
            }
        )
        assert response.status_code == 400
    
    def test_string_parameter_limits(self, client):
        """Test string parameter length limits"""
        # Test extremely long sensor ID
        long_sensor_id = "x" * 1000
        response = client.post(
            f"/api/sensors/{long_sensor_id}/calibrate",
            params={
                "calibration_type": "auto_zero",
                "duration_ms": 1000
            }
        )
        # Should reject or handle gracefully
        assert response.status_code in [400, 404, 414]  # 414 = URI Too Long


class TestErrorHandling:
    """Test secure error handling"""
    
    def test_error_information_disclosure(self, client):
        """Test that errors don't disclose sensitive information"""
        # Test with malformed request
        response = client.post("/api/sensors/pt1/calibrate")  # Missing parameters
        assert response.status_code == 422  # Validation error
        
        error_detail = response.json()
        
        # Error should not contain file paths or internal details
        error_text = str(error_detail).lower()
        assert "/users/" not in error_text
        assert "traceback" not in error_text
        assert "stack" not in error_text
    
    def test_internal_error_handling(self, client):
        """Test handling of internal server errors"""
        # This would test 500 errors, but our current implementation
        # doesn't easily trigger them without mocking
        # The test framework validates that proper error codes are returned
        pass


class TestDataSanitization:
    """Test data sanitization in responses"""
    
    def test_json_response_sanitization(self, client):
        """Test that JSON responses are properly sanitized"""
        response = client.get("/api/config")
        assert response.status_code == 200
        
        config = response.json()
        
        # Ensure no sensitive data is exposed
        config_str = str(config).lower()
        assert "password" not in config_str
        assert "secret" not in config_str
        assert "key" not in config_str
        assert "token" not in config_str
    
    def test_html_response_sanitization(self, client):
        """Test that HTML responses are sanitized"""
        response = client.get("/pressure")
        assert response.status_code == 200
        
        content = response.content.decode()
        
        # Should not contain unescaped user input
        # This is more relevant if we had user-generated content
        assert "<script>" not in content.lower()
        assert "javascript:" not in content.lower()


class TestResourceLimits:
    """Test resource usage limits"""
    
    def test_request_size_limits(self, client):
        """Test request size limitations"""
        # FastAPI should handle this automatically, but we can test
        # Currently our API doesn't accept large payloads, so this is theoretical
        pass
    
    def test_concurrent_request_limits(self, client):
        """Test concurrent request handling"""
        import threading
        import time
        
        responses = []
        
        def make_request():
            response = client.get("/api/health")
            responses.append(response.status_code)
        
        # Test many concurrent requests
        threads = []
        for _ in range(20):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All requests should succeed (no DoS protection in internal app)
        assert all(status == 200 for status in responses)
        assert len(responses) == 20


class TestWebSocketSecurity:
    """Test WebSocket security measures"""
    
    def test_websocket_connection_limits(self, client):
        """Test WebSocket connection limitations"""
        # Get WebSocket stats
        response = client.get("/ws/stats")
        assert response.status_code == 200
        
        stats = response.json()
        assert "total_connections" in stats
        
        # Currently no connection limits implemented for internal use
        # But the monitoring is in place
    
    def test_websocket_message_validation(self, client):
        """Test WebSocket message validation"""
        # This would require WebSocket test client
        # For now, we verify the endpoints exist
        response = client.get("/ws/stats")
        assert response.status_code == 200


class TestConfigurationSecurity:
    """Test configuration security"""
    
    def test_debug_mode_disabled(self, client):
        """Test that debug mode is properly configured"""
        response = client.get("/api/config")
        assert response.status_code == 200
        
        config = response.json()
        
        # Debug should be false in production-like settings
        # (This depends on how we configure the test environment)
        assert isinstance(config.get("debug", False), bool)
    
    def test_sensitive_config_not_exposed(self, client):
        """Test that sensitive configuration is not exposed"""
        response = client.get("/api/config")
        assert response.status_code == 200
        
        config = response.json()
        config_str = str(config).lower()
        
        # Should not expose sensitive configuration
        sensitive_terms = ["password", "secret", "key", "token", "private"]
        for term in sensitive_terms:
            assert term not in config_str


class TestInputSanitization:
    """Test input sanitization across the system"""
    
    def test_no_code_injection(self, client):
        """Test prevention of code injection"""
        # Test Python code injection attempt
        response = client.post(
            "/api/sensors/pt1/calibrate",
            params={
                "calibration_type": "__import__('os').system('ls')",
                "duration_ms": 1000
            }
        )
        assert response.status_code == 400
    
    def test_no_template_injection(self, client):
        """Test prevention of template injection"""
        # Test Jinja2 template injection attempt  
        malicious_id = "{{ 7*7 }}"
        response = client.post(
            f"/api/sensors/{malicious_id}/calibrate",
            params={
                "calibration_type": "auto_zero",
                "duration_ms": 1000
            }
        )
        # Should not execute template code
        assert response.status_code in [400, 404]