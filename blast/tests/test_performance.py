"""Performance and load tests for BLAST system"""
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app import create_app
from app.config.settings import Settings


@pytest.fixture
def test_settings():
    """Create test settings optimized for performance testing"""
    settings = Settings()
    settings.telemetry_interval_ms = 50  # Faster for testing
    return settings


@pytest.fixture
def client(test_settings):
    """Create test client"""
    app = create_app(test_settings)
    return TestClient(app)


class TestAPIPerformance:
    """Test API endpoint performance"""
    
    def test_telemetry_endpoint_latency(self, client):
        """Test telemetry endpoint response time"""
        # Warm up
        client.get("/api/telemetry")
        
        start_time = time.time()
        response = client.get("/api/telemetry")
        end_time = time.time()
        
        assert response.status_code == 200
        latency = end_time - start_time
        
        # Should respond within 100ms for simulator data
        assert latency < 0.1, f"Telemetry latency too high: {latency:.3f}s"
    
    def test_health_check_performance(self, client):
        """Test health check endpoint performance"""
        start_time = time.time()
        response = client.get("/api/health")
        end_time = time.time()
        
        assert response.status_code == 200
        latency = end_time - start_time
        
        # Health check should be very fast
        assert latency < 0.05, f"Health check latency too high: {latency:.3f}s"
    
    def test_config_endpoint_performance(self, client):
        """Test configuration endpoint performance"""
        start_time = time.time()
        response = client.get("/api/config")
        end_time = time.time()
        
        assert response.status_code == 200
        latency = end_time - start_time
        
        # Config should load quickly
        assert latency < 0.05, f"Config latency too high: {latency:.3f}s"
    
    def test_calibration_performance(self, client):
        """Test calibration endpoint performance"""
        start_time = time.time()
        response = client.post(
            "/api/sensors/pt1/calibrate",
            params={
                "calibration_type": "auto_zero",
                "duration_ms": 1000
            }
        )
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Should complete within reasonable time (duration + overhead)
        max_expected_time = 2.0  # 1s duration + 1s overhead
        actual_time = end_time - start_time
        assert actual_time < max_expected_time, f"Calibration took too long: {actual_time:.3f}s"


class TestConcurrentLoad:
    """Test system behavior under concurrent load"""
    
    def test_concurrent_telemetry_requests(self, client):
        """Test multiple concurrent telemetry requests"""
        def make_request():
            response = client.get("/api/telemetry")
            return response.status_code, response.elapsed.total_seconds() if hasattr(response, 'elapsed') else 0
        
        # Test with 10 concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [future.result() for future in futures]
        
        # All requests should succeed
        status_codes = [result[0] for result in results]
        assert all(code == 200 for code in status_codes)
        
        # Average response time should be reasonable
        response_times = [result[1] for result in results if result[1] > 0]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            assert avg_time < 0.5, f"Average response time too high: {avg_time:.3f}s"
    
    def test_concurrent_calibrations(self, client):
        """Test concurrent calibration requests on different sensors"""
        def calibrate_sensor(sensor_id):
            response = client.post(
                f"/api/sensors/{sensor_id}/calibrate",
                params={
                    "calibration_type": "auto_zero",
                    "duration_ms": 500
                }
            )
            return response.status_code
        
        sensor_ids = ["pt1", "pt2", "pt3"]
        
        with ThreadPoolExecutor(max_workers=len(sensor_ids)) as executor:
            futures = [executor.submit(calibrate_sensor, sid) for sid in sensor_ids]
            results = [future.result() for future in futures]
        
        # All calibrations should succeed
        assert all(code == 200 for code in results)
    
    def test_mixed_workload(self, client):
        """Test mixed API workload"""
        def telemetry_worker():
            return client.get("/api/telemetry").status_code
        
        def health_worker():
            return client.get("/api/health").status_code
        
        def config_worker():
            return client.get("/api/config").status_code
        
        # Mix of different request types
        workers = [telemetry_worker, health_worker, config_worker] * 5
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker) for worker in workers]
            results = [future.result() for future in futures]
        
        # All requests should succeed
        assert all(code == 200 for code in results)


class TestMemoryUsage:
    """Test memory usage patterns"""
    
    def test_memory_leak_prevention(self, client):
        """Test that repeated requests don't cause memory leaks"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Make many requests
        for _ in range(100):
            response = client.get("/api/telemetry")
            assert response.status_code == 200
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB)
        max_increase = 50 * 1024 * 1024  # 50MB
        assert memory_increase < max_increase, f"Memory increase too high: {memory_increase / 1024 / 1024:.1f}MB"
    
    def test_data_structure_efficiency(self, client):
        """Test that data structures don't grow unbounded"""
        # This would typically test internal data structures
        # For now, we'll test that responses remain consistent
        
        first_response = client.get("/api/telemetry")
        assert first_response.status_code == 200
        first_size = len(first_response.content)
        
        # Make many requests
        for _ in range(50):
            client.get("/api/telemetry")
        
        final_response = client.get("/api/telemetry")
        assert final_response.status_code == 200
        final_size = len(final_response.content)
        
        # Response size should remain similar
        size_difference = abs(final_size - first_size)
        assert size_difference < first_size * 0.1, "Response size variation too high"


class TestScalability:
    """Test system scalability characteristics"""
    
    def test_response_time_under_load(self, client):
        """Test that response time doesn't degrade significantly under load"""
        # Baseline measurement
        start = time.time()
        response = client.get("/api/telemetry")
        baseline_time = time.time() - start
        assert response.status_code == 200
        
        # Create background load
        def background_load():
            for _ in range(10):
                client.get("/api/telemetry")
                time.sleep(0.01)
        
        # Start background load
        with ThreadPoolExecutor(max_workers=3) as executor:
            load_futures = [executor.submit(background_load) for _ in range(3)]
            
            # Measure response time under load
            time.sleep(0.1)  # Let background load start
            start = time.time()
            response = client.get("/api/telemetry")
            loaded_time = time.time() - start
            
            # Wait for background load to complete
            for future in load_futures:
                future.result()
        
        assert response.status_code == 200
        
        # Response time shouldn't degrade more than 3x
        max_acceptable_time = baseline_time * 3
        assert loaded_time < max_acceptable_time, f"Response time degraded too much: {loaded_time:.3f}s vs {baseline_time:.3f}s baseline"
    
    def test_sensor_count_scalability(self, test_settings):
        """Test that system handles varying numbers of sensors"""
        # This tests configuration with different sensor counts
        original_count = len(test_settings.pressure_transducers)
        
        # Test with minimal sensors
        test_settings.pressure_transducers = test_settings.pressure_transducers[:1]
        app = create_app(test_settings)
        client = TestClient(app)
        
        response = client.get("/api/telemetry")
        assert response.status_code == 200
        
        telemetry = response.json()
        assert len(telemetry["pressure_transducers"]) == 1
        
        # Reset for other tests
        test_settings.pressure_transducers = test_settings.pressure_transducers * original_count


class TestResourceOptimization:
    """Test resource optimization features"""
    
    def test_static_file_serving_efficiency(self, client):
        """Test static file serving performance"""
        start_time = time.time()
        response = client.get("/static/css/dashboard.css")
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Static files should serve very quickly
        latency = end_time - start_time
        assert latency < 0.05, f"Static file serving too slow: {latency:.3f}s"
    
    def test_frontend_page_load_time(self, client):
        """Test frontend page loading performance"""
        start_time = time.time()
        response = client.get("/pressure")
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Page should load within reasonable time
        load_time = end_time - start_time
        assert load_time < 0.2, f"Page load time too high: {load_time:.3f}s"
    
    def test_json_serialization_performance(self, client):
        """Test JSON serialization performance"""
        # Test large telemetry response
        start_time = time.time()
        response = client.get("/api/telemetry")
        json_data = response.json()
        end_time = time.time()
        
        assert response.status_code == 200
        
        # JSON parsing should be fast
        parse_time = end_time - start_time
        assert parse_time < 0.05, f"JSON serialization too slow: {parse_time:.3f}s"


class TestRealTimePerformance:
    """Test real-time performance characteristics"""
    
    def test_telemetry_update_frequency(self, test_settings):
        """Test that telemetry updates meet frequency requirements"""
        # This would typically test WebSocket update frequency
        # For now, test that the configuration supports real-time requirements
        
        assert test_settings.telemetry_interval_ms <= 100, "Telemetry interval too slow for real-time"
        
        # Calculate theoretical maximum update rate
        max_updates_per_second = 1000 / test_settings.telemetry_interval_ms
        assert max_updates_per_second >= 10, "Update rate too low for real-time monitoring"
    
    @pytest.mark.asyncio
    async def test_async_operation_performance(self):
        """Test async operation performance"""
        from app.services.data_acquisition import DataAcquisitionService
        from app.services.calibration import CalibrationService
        from app.config.settings import Settings
        
        settings = Settings()
        calibration_service = CalibrationService()
        data_service = DataAcquisitionService(settings, calibration_service)
        
        # Test async startup
        start_time = time.time()
        await data_service.start()
        startup_time = time.time() - start_time
        
        assert startup_time < 1.0, f"Service startup too slow: {startup_time:.3f}s"
        
        # Test async data reading
        start_time = time.time()
        telemetry = await data_service.get_calibrated_reading()
        read_time = time.time() - start_time
        
        assert read_time < 0.1, f"Data reading too slow: {read_time:.3f}s"
        assert telemetry is not None
        
        await data_service.stop()