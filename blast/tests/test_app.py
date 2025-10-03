"""Tests for FastAPI application"""
import pytest
from fastapi.testclient import TestClient
from app import create_app
from app.config.settings import Settings


@pytest.fixture
def client():
    """Create test client with test settings"""
    test_settings = Settings()
    app = create_app(test_settings)
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "BLAST"}


def test_config_endpoint(client):
    """Test config endpoint placeholder"""
    response = client.get("/api/config")
    assert response.status_code == 200
    assert "message" in response.json()


def test_app_creation():
    """Test that app can be created with settings"""
    settings = Settings()
    app = create_app(settings)
    
    assert app.title == "BLAST Sensor Monitoring System"
    assert app.version == "2.0.0"
    assert app.state.settings == settings