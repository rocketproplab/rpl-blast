"""Tests for backend services integration"""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
from fastapi.testclient import TestClient

from app import create_app
from app.config.settings import Settings
from app.services.data_acquisition import DataAcquisitionService
from app.services.calibration import CalibrationService
from app.core.circuit_breaker import CircuitBreaker, CircuitState
from app.models.sensors import SensorReading, TelemetryPacket


@pytest.fixture
def test_settings():
    """Create test settings"""
    return Settings()


@pytest.fixture
async def data_acquisition_service(test_settings):
    """Create data acquisition service for testing"""
    calibration_service = CalibrationService()
    service = DataAcquisitionService(test_settings, calibration_service)
    yield service
    await service.stop()


@pytest.fixture
def test_client():
    """Create test client"""
    settings = Settings()
    app = create_app(settings)
    return TestClient(app)


class TestDataAcquisitionService:
    """Test data acquisition service functionality"""
    
    @pytest.mark.asyncio
    async def test_service_startup_success(self, data_acquisition_service):
        """Test successful service startup"""
        # Service should start successfully with simulator
        success = await data_acquisition_service.start()
        assert success is True
        assert data_acquisition_service.is_running is True
        assert data_acquisition_service.data_source is not None
    
    @pytest.mark.asyncio
    async def test_get_calibrated_reading(self, data_acquisition_service):
        """Test getting calibrated sensor readings"""
        await data_acquisition_service.start()
        
        # Get calibrated reading
        telemetry = await data_acquisition_service.get_calibrated_reading()
        
        assert isinstance(telemetry, TelemetryPacket)
        assert len(telemetry.pressure_transducers) > 0
        assert len(telemetry.thermocouples) > 0
        assert len(telemetry.load_cells) > 0
        
        # Check that readings are calibrated
        for reading in telemetry.pressure_transducers:
            assert isinstance(reading, SensorReading)
            assert reading.sensor_id.startswith("pt")
            assert reading.unit == "psi"
    
    @pytest.mark.asyncio
    async def test_sensor_calibration_integration(self, data_acquisition_service):
        """Test sensor calibration through data acquisition service"""
        await data_acquisition_service.start()
        
        # Perform auto-zero calibration
        result = await data_acquisition_service.perform_sensor_calibration(
            "pt1", "auto_zero", duration_ms=1000
        )
        
        assert result.success is True
        assert result.sensor_id == "pt1"
        assert result.calibration_type.value == "auto_zero"
        assert result.measurement_count >= 8
        
        # Check that calibration state was updated
        state = await data_acquisition_service.get_calibration_state("pt1")
        assert state is not None
        assert state.zero_offset == result.new_offset
    
    @pytest.mark.asyncio
    async def test_span_calibration_integration(self, data_acquisition_service):
        """Test span calibration integration"""
        await data_acquisition_service.start()
        
        # Perform span calibration
        result = await data_acquisition_service.perform_sensor_calibration(
            "pt1", "span", reference_value=100.0, measured_value=95.0
        )
        
        assert result.success is True
        assert result.sensor_id == "pt1"
        assert result.calibration_type.value == "span"
        assert result.new_span is not None
    
    @pytest.mark.asyncio
    async def test_health_check(self, data_acquisition_service):
        """Test service health check"""
        await data_acquisition_service.start()
        
        health = await data_acquisition_service.health_check()
        
        assert health["running"] is True
        assert health["data_source_type"] == "simulator"  # Default for testing
        assert health["error_count"] == 0
        assert "data_source" in health


class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state"""
        breaker = CircuitBreaker(failure_threshold=3)
        
        # Should execute function normally
        async def test_func():
            return "success"
        
        result = await breaker.call(test_func)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures"""
        breaker = CircuitBreaker(failure_threshold=3)
        
        async def failing_func():
            raise Exception("Test failure")
        
        # Trigger failures to open circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(failing_func)
        
        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 3
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_calls_when_open(self):
        """Test circuit breaker blocks calls when open"""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        
        # Trigger failure to open circuit
        async def failing_func():
            raise Exception("Test failure")
        
        with pytest.raises(Exception):
            await breaker.call(failing_func)
        
        assert breaker.state == CircuitState.OPEN
        
        # Should block subsequent calls
        from app.core.exceptions import SensorException
        with pytest.raises(SensorException, match="Circuit breaker is OPEN"):
            await breaker.call(failing_func)
    
    def test_circuit_breaker_status(self):
        """Test circuit breaker status reporting"""
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30)
        
        status = breaker.get_status()
        
        assert status["state"] == "closed"
        assert status["failure_count"] == 0
        assert status["failure_threshold"] == 5
        assert status["recovery_timeout"] == 30


class TestFastAPIIntegration:
    """Test FastAPI application integration"""
    
    def test_health_endpoint(self, test_client):
        """Test health check endpoint"""
        response = test_client.get("/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["service"] == "BLAST"
        assert "data_acquisition" in data
    
    def test_config_endpoint(self, test_client):
        """Test configuration endpoint"""
        response = test_client.get("/api/config")
        assert response.status_code == 200
        
        data = response.json()
        assert "data_source" in data
        assert "pressure_transducers" in data
        assert "thermocouples" in data
        assert "load_cells" in data
        assert "calibration" in data
    
    def test_telemetry_endpoint(self, test_client):
        """Test telemetry data endpoint"""
        response = test_client.get("/api/telemetry")
        assert response.status_code == 200
        
        data = response.json()
        assert "timestamp" in data
        assert "pressure_transducers" in data
        assert "thermocouples" in data
        assert "load_cells" in data
        assert "valve_states" in data
    
    def test_calibration_endpoint(self, test_client):
        """Test sensor calibration endpoint"""
        # Test auto-zero calibration
        response = test_client.post(
            "/api/sensors/pt1/calibrate",
            params={
                "calibration_type": "auto_zero",
                "duration_ms": 1000
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["sensor_id"] == "pt1"
        assert data["calibration_type"] == "auto_zero"
    
    def test_get_calibration_state_endpoint(self, test_client):
        """Test get calibration state endpoint"""
        # First perform calibration
        test_client.post(
            "/api/sensors/pt1/calibrate",
            params={"calibration_type": "auto_zero", "duration_ms": 500}
        )
        
        # Then get calibration state
        response = test_client.get("/api/sensors/pt1/calibration")
        assert response.status_code == 200
        
        data = response.json()
        assert data["sensor_id"] == "pt1"
        assert "zero_offset" in data
        assert "last_calibrated" in data
    
    def test_span_calibration_endpoint(self, test_client):
        """Test span calibration endpoint"""
        response = test_client.post(
            "/api/sensors/pt1/calibrate",
            params={
                "calibration_type": "span",
                "reference_value": 100.0,
                "measured_value": 95.0
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["calibration_type"] == "span"
        assert data["new_span"] is not None


class TestServiceIntegration:
    """Test integration between all services"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_calibration_workflow(self, data_acquisition_service):
        """Test complete calibration workflow"""
        await data_acquisition_service.start()
        
        # Step 1: Get baseline reading
        baseline_telemetry = await data_acquisition_service.get_calibrated_reading()
        baseline_reading = baseline_telemetry.pressure_transducers[0]
        
        # Step 2: Perform auto-zero calibration
        zero_result = await data_acquisition_service.perform_sensor_calibration(
            "pt1", "auto_zero", duration_ms=1000
        )
        assert zero_result.success is True
        
        # Step 3: Perform span calibration
        span_result = await data_acquisition_service.perform_sensor_calibration(
            "pt1", "span", reference_value=500.0, measured_value=baseline_reading.value
        )
        assert span_result.success is True
        
        # Step 4: Get calibrated reading
        calibrated_telemetry = await data_acquisition_service.get_calibrated_reading()
        calibrated_reading = calibrated_telemetry.pressure_transducers[0]
        
        # Verify calibration was applied
        assert calibrated_reading.calibrated is True
        assert calibrated_reading.sensor_id == "pt1"
        
        # Step 5: Check calibration state persistence
        state = await data_acquisition_service.get_calibration_state("pt1")
        assert state.zero_offset == zero_result.new_offset
        assert state.span_multiplier == span_result.new_span
    
    @pytest.mark.asyncio
    async def test_service_error_handling(self, test_settings):
        """Test service error handling and recovery"""
        # Create service with mock data source that fails
        calibration_service = CalibrationService()
        service = DataAcquisitionService(test_settings, calibration_service)
        
        # Mock data source to fail initialization
        mock_source = AsyncMock()
        mock_source.start.return_value = False
        service.data_source = mock_source
        
        # Service startup should fail gracefully
        success = await service.start()
        assert success is False
        assert service.is_running is False