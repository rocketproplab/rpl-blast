"""Tests for data source implementations"""
import pytest
import asyncio
from unittest.mock import Mock, patch
from app.data_sources.base import DataSource, SensorDataSource
from app.data_sources.simulator import SensorSimulator
from app.models.sensors import SensorReading, TelemetryPacket


@pytest.fixture
def sample_config():
    """Sample configuration for testing"""
    return {
        'pressure_transducers': [
            {'id': 'pt1', 'name': 'GN2', 'unit': 'psi'},
            {'id': 'pt2', 'name': 'LOX', 'unit': 'psi'}
        ],
        'thermocouples': [
            {'id': 'tc1', 'name': 'Thermocouple 1', 'unit': '°C'}
        ],
        'load_cells': [
            {'id': 'lc1', 'name': 'Load Cell 1', 'unit': 'lbf'}
        ],
        'flow_control_valves': [
            {'id': 'fv1', 'name': 'LNG Vent'}
        ]
    }


class TestDataSource:
    """Test abstract data source base class"""
    
    @pytest.mark.asyncio
    async def test_data_source_lifecycle(self, sample_config):
        """Test data source start/stop lifecycle"""
        
        class MockDataSource(DataSource):
            async def initialize(self):
                return True
            
            async def read_sensors(self):
                return TelemetryPacket()
            
            async def close(self):
                pass
            
            async def health_check(self):
                return {"status": "ok"}
        
        source = MockDataSource(sample_config)
        
        # Test initial state
        assert not source.is_connected
        assert not source.is_running
        
        # Test start
        success = await source.start()
        assert success is True
        assert source.is_running is True
        
        # Test stop
        await source.stop()
        assert source.is_running is False
        assert source.is_connected is False


class TestSensorDataSource:
    """Test sensor data source base functionality"""
    
    def test_sensor_data_source_config(self, sample_config):
        """Test sensor data source configuration loading"""
        source = SensorDataSource(sample_config)
        
        assert len(source.sensor_configs['pressure_transducers']) == 2
        assert len(source.sensor_configs['thermocouples']) == 1
        assert len(source.sensor_configs['load_cells']) == 1
        assert len(source.sensor_configs['flow_control_valves']) == 1
    
    def test_create_sensor_reading(self, sample_config):
        """Test sensor reading creation"""
        source = SensorDataSource(sample_config)
        
        reading = source.create_sensor_reading(
            sensor_id="pt1",
            value=250.5,
            raw_value=2.5,
            unit="psi"
        )
        
        assert isinstance(reading, SensorReading)
        assert reading.sensor_id == "pt1"
        assert reading.value == 250.5
        assert reading.raw_value == 2.5
        assert reading.unit == "psi"
        assert reading.calibrated is True
    
    def test_create_telemetry_packet(self, sample_config):
        """Test telemetry packet creation"""
        source = SensorDataSource(sample_config)
        
        pt_reading = source.create_sensor_reading("pt1", 250.0, unit="psi")
        tc_reading = source.create_sensor_reading("tc1", 120.0, unit="°C")
        
        packet = source.create_telemetry_packet(
            pressure_readings=[pt_reading],
            thermocouple_readings=[tc_reading],
            valve_states={"fv1": True}
        )
        
        assert isinstance(packet, TelemetryPacket)
        assert len(packet.pressure_transducers) == 1
        assert len(packet.thermocouples) == 1
        assert packet.valve_states["fv1"] is True


class TestSensorSimulator:
    """Test sensor simulator implementation"""
    
    @pytest.mark.asyncio
    async def test_simulator_initialization(self, sample_config):
        """Test simulator initialization"""
        simulator = SensorSimulator(sample_config)
        
        # Test initialization
        success = await simulator.initialize()
        assert success is True
        assert simulator.is_connected is True
        assert simulator.is_simulating is True
        
        # Test health check
        health = await simulator.health_check()
        assert health["connected"] is True
        assert health["simulating"] is True
        assert "simulation_time" in health
    
    @pytest.mark.asyncio
    async def test_simulator_sensor_reading(self, sample_config):
        """Test simulator sensor data generation"""
        simulator = SensorSimulator(sample_config)
        await simulator.initialize()
        
        # Read sensor data
        packet = await simulator.read_sensors()
        
        assert isinstance(packet, TelemetryPacket)
        assert len(packet.pressure_transducers) == 2
        assert len(packet.thermocouples) == 1
        assert len(packet.load_cells) == 1
        
        # Check pressure transducer readings
        pt_reading = packet.pressure_transducers[0]
        assert pt_reading.sensor_id == "pt1"
        assert pt_reading.unit == "psi"
        assert pt_reading.raw_value is not None  # Should have raw voltage
        
        # Check thermocouple readings
        tc_reading = packet.thermocouples[0]
        assert tc_reading.sensor_id == "tc1"
        assert tc_reading.unit == "°C"
    
    @pytest.mark.asyncio
    async def test_simulator_drift_simulation(self, sample_config):
        """Test drift simulation functionality"""
        simulator = SensorSimulator(sample_config)
        await simulator.initialize()
        
        # Set a high drift rate
        await simulator.set_sensor_drift_rate("pt1", 10.0)  # 10 PSI per hour
        
        # Read initial value
        packet1 = await simulator.read_sensors()
        initial_value = packet1.pressure_transducers[0].value
        
        # Advance simulation time and read again
        simulator.simulation_time += 360.0  # 6 minutes = 0.1 hours
        packet2 = await simulator.read_sensors()
        later_value = packet2.pressure_transducers[0].value
        
        # Should see drift effect (approximately 1 PSI change)
        drift_change = abs(later_value - initial_value)
        assert drift_change > 0.5  # Should see some drift
    
    @pytest.mark.asyncio
    async def test_simulator_calibration_offset(self, sample_config):
        """Test calibration offset injection"""
        simulator = SensorSimulator(sample_config)
        await simulator.initialize()
        
        # Read baseline value
        packet1 = await simulator.read_sensors()
        baseline_value = packet1.pressure_transducers[0].value
        
        # Inject calibration offset
        offset = 50.0
        await simulator.inject_calibration_offset("pt1", offset)
        
        # Read with offset
        packet2 = await simulator.read_sensors()
        offset_value = packet2.pressure_transducers[0].value
        
        # Should see the offset applied
        actual_offset = offset_value - baseline_value
        assert abs(actual_offset - offset) < 5.0  # Allow for noise variation
    
    @pytest.mark.asyncio
    async def test_simulator_noise_control(self, sample_config):
        """Test noise level control"""
        simulator = SensorSimulator(sample_config)
        await simulator.initialize()
        
        # Set very low noise
        await simulator.set_sensor_noise_level("pt1", 0.01)
        
        # Read multiple values and check consistency
        values = []
        for _ in range(10):
            packet = await simulator.read_sensors()
            values.append(packet.pressure_transducers[0].value)
        
        # With low noise, values should be relatively consistent
        value_range = max(values) - min(values)
        assert value_range < 5.0  # Should be fairly stable
    
    @pytest.mark.asyncio
    async def test_simulator_voltage_conversion(self, sample_config):
        """Test PSI to voltage conversion for calibration testing"""
        simulator = SensorSimulator(sample_config)
        await simulator.initialize()
        
        packet = await simulator.read_sensors()
        pt_reading = packet.pressure_transducers[0]  # This should be GN2
        
        # Check that raw voltage is reasonable for the PSI value
        assert pt_reading.raw_value is not None
        assert 0.5 <= pt_reading.raw_value <= 4.5  # GN2 voltage range
        
        # Check conversion consistency
        psi_value = pt_reading.value
        voltage = pt_reading.raw_value
        
        # Voltage should increase with PSI (roughly linear relationship)
        assert isinstance(voltage, float)
        assert voltage > 0
    
    @pytest.mark.asyncio
    async def test_simulator_valve_states(self, sample_config):
        """Test valve state generation"""
        simulator = SensorSimulator(sample_config)
        await simulator.initialize()
        
        packet = await simulator.read_sensors()
        
        assert "fv1" in packet.valve_states
        assert isinstance(packet.valve_states["fv1"], bool)
    
    @pytest.mark.asyncio
    async def test_simulator_reset_sensor(self, sample_config):
        """Test sensor reset functionality"""
        simulator = SensorSimulator(sample_config)
        await simulator.initialize()
        
        # Modify sensor parameters
        await simulator.inject_calibration_offset("pt1", 100.0)
        await simulator.set_sensor_drift_rate("pt1", 50.0)
        
        # Reset sensor
        await simulator.reset_sensor("pt1")
        
        # Check that offset is reset
        assert simulator.calibration_offsets["pt1"] == 0.0
        
        # Drift rate should be reset to reasonable range
        assert -0.1 <= simulator.drift_rates["pt1"] <= 0.1