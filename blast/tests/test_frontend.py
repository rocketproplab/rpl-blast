"""Tests for frontend components and routes"""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from app import create_app
from app.config.settings import Settings


@pytest.fixture
def test_settings():
    """Create test settings"""
    return Settings()


@pytest.fixture
def client(test_settings):
    """Create test client"""
    app = create_app(test_settings)
    return TestClient(app)


class TestFrontendRoutes:
    """Test frontend page routes"""
    
    def test_dashboard_page(self, client):
        """Test main dashboard page"""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        content = response.content.decode()
        assert "BLAST" in content
        assert "Dashboard" in content
        assert "Pressure Transducers" in content
        assert "Thermocouples" in content
        assert "Flow Control Valves" in content
    
    def test_pressure_page(self, client):
        """Test pressure transducers page"""
        response = client.get("/pressure")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        content = response.content.decode()
        assert "Pressure Transducers" in content
        assert "calibration-panel" in content
        assert "Auto-Zero Calibration" in content
        assert "Span Calibration" in content
    
    def test_thermocouples_page(self, client):
        """Test thermocouples page"""
        response = client.get("/thermocouples")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        content = response.content.decode()
        assert "Thermocouples" in content or "Load Cells" in content
    
    def test_valves_page(self, client):
        """Test valves page"""
        response = client.get("/valves")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        content = response.content.decode()
        assert "Flow Control" in content or "Valves" in content


class TestStaticAssets:
    """Test static asset serving"""
    
    def test_css_files(self, client):
        """Test CSS file serving"""
        response = client.get("/static/css/dashboard.css")
        assert response.status_code == 200
        assert "text/css" in response.headers["content-type"]
        
        response = client.get("/static/css/calibration.css")
        assert response.status_code == 200
        assert "text/css" in response.headers["content-type"]
    
    def test_javascript_files(self, client):
        """Test JavaScript file serving"""
        js_files = [
            "websocket-manager.js",
            "calibration-manager.js", 
            "pressure-display.js",
            "browser-monitor.js"
        ]
        
        for js_file in js_files:
            response = client.get(f"/static/js/{js_file}")
            assert response.status_code == 200
            assert any(ct in response.headers["content-type"] for ct in ["javascript", "text/plain"])
    
    def test_nonexistent_static_file(self, client):
        """Test handling of nonexistent static files"""
        response = client.get("/static/nonexistent.js")
        assert response.status_code == 404


class TestTemplateRendering:
    """Test template rendering with data"""
    
    def test_pressure_page_with_sensors(self, client, test_settings):
        """Test that pressure page renders sensor data correctly"""
        response = client.get("/pressure")
        assert response.status_code == 200
        
        content = response.content.decode()
        
        # Should contain sensor configurations
        for pt in test_settings.pressure_transducers:
            assert pt.name in content
            assert pt.id in content
            assert pt.color in content
            assert pt.unit in content
    
    def test_dashboard_with_system_info(self, client, test_settings):
        """Test that dashboard shows system information"""
        response = client.get("/")
        assert response.status_code == 200
        
        content = response.content.decode()
        
        # Should show data source info
        assert test_settings.data_source.value in content
        
        # Should show update rate
        assert str(test_settings.telemetry_interval_ms) in content
        
        # Should show sensor counts
        assert str(len(test_settings.pressure_transducers)) in content
    
    def test_template_includes_required_scripts(self, client):
        """Test that templates include required JavaScript"""
        response = client.get("/pressure")
        assert response.status_code == 200
        
        content = response.content.decode()
        
        # Should include required scripts
        assert "websocket-manager.js" in content
        assert "calibration-manager.js" in content
        assert "pressure-display.js" in content
        assert "plotly-latest.min.js" in content


class TestResponsiveDesign:
    """Test responsive design elements"""
    
    def test_viewport_meta_tag(self, client):
        """Test that pages include viewport meta tag"""
        response = client.get("/")
        assert response.status_code == 200
        
        content = response.content.decode()
        assert 'viewport' in content
        assert 'width=device-width' in content
    
    def test_css_grid_classes(self, client):
        """Test that pages use responsive CSS classes"""
        response = client.get("/pressure")
        assert response.status_code == 200
        
        content = response.content.decode()
        
        # Should use responsive grid classes
        assert "sensor-grid" in content
        assert "pt-grid" in content
        assert "dashboard-grid" in content or "calibration-controls" in content


class TestAccessibility:
    """Test basic accessibility features"""
    
    def test_semantic_html(self, client):
        """Test that pages use semantic HTML"""
        response = client.get("/")
        assert response.status_code == 200
        
        content = response.content.decode()
        
        # Should use semantic tags
        assert "<header>" in content
        assert "<main>" in content
        assert "<nav>" in content or "nav" in content
    
    def test_form_labels(self, client):
        """Test that form inputs have labels"""
        response = client.get("/pressure")
        assert response.status_code == 200
        
        content = response.content.decode()
        
        # Calibration inputs should have labels
        assert "<label>" in content
        assert "Duration:" in content
        assert "Reference:" in content
    
    def test_button_accessibility(self, client):
        """Test that buttons have appropriate attributes"""
        response = client.get("/pressure")
        assert response.status_code == 200
        
        content = response.content.decode()
        
        # Buttons should have descriptive text
        assert "Zero Sensor" in content
        assert "Calibrate Span" in content
        assert "Refresh State" in content


class TestErrorPages:
    """Test error page handling"""
    
    def test_404_handling(self, client):
        """Test 404 page handling"""
        response = client.get("/nonexistent-page")
        assert response.status_code == 404
    
    def test_invalid_sensor_page(self, client):
        """Test handling of invalid sensor routes"""
        # This might not exist yet, but testing the concept
        response = client.get("/sensors/invalid-sensor")
        assert response.status_code == 404


class TestSecurityHeaders:
    """Test security-related headers"""
    
    def test_content_type_headers(self, client):
        """Test that responses have proper content-type headers"""
        # HTML pages
        response = client.get("/")
        assert "text/html" in response.headers["content-type"]
        
        # CSS files
        response = client.get("/static/css/dashboard.css")
        assert "text/css" in response.headers["content-type"]
    
    def test_no_sensitive_info_in_headers(self, client):
        """Test that sensitive information is not exposed in headers"""
        response = client.get("/")
        
        # Should not expose server details
        server_header = response.headers.get("server", "").lower()
        assert "version" not in server_header


class TestPerformanceOptimization:
    """Test frontend performance optimizations"""
    
    def test_static_file_caching(self, client):
        """Test that static files can be cached"""
        response = client.get("/static/css/dashboard.css")
        assert response.status_code == 200
        
        # Should not have no-cache headers for static assets
        cache_control = response.headers.get("cache-control", "")
        assert "no-cache" not in cache_control
    
    def test_javascript_loading(self, client):
        """Test JavaScript file loading"""
        response = client.get("/pressure")
        content = response.content.decode()
        
        # Scripts should be loaded efficiently
        # Check that heavy scripts like Plotly are loaded from CDN
        assert "cdn.plot.ly" in content
        
        # Local scripts should be at bottom of page for performance
        script_positions = []
        for script in ["websocket-manager.js", "calibration-manager.js"]:
            pos = content.find(script)
            if pos > 0:
                script_positions.append(pos)
        
        # Scripts should be towards the end of the document
        if script_positions:
            body_end = content.rfind("</body>")
            assert all(pos < body_end for pos in script_positions)