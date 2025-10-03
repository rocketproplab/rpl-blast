/**
 * Pressure Transducer Display with WebSocket Integration
 */
class PressureDisplay {
    constructor() {
        this.data = [];
        this.maxDataPoints = 1000;
        this.stats = new Map();
        this.plotsInitialized = false;
        this.lastUpdateTime = Date.now();
        
        this.init();
    }

    init() {
        // Wait for WebSocket manager to be ready
        if (window.wsManager) {
            this.setupWebSocketListeners();
        } else {
            setTimeout(() => this.init(), 100);
            return;
        }

        // Initialize plots when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initializePlots());
        } else {
            this.initializePlots();
        }
    }

    setupWebSocketListeners() {
        window.wsManager.on('telemetry', (data) => {
            this.updateData(data);
        });

        window.wsManager.on('connected', (info) => {
            console.log('Connected to telemetry stream');
            this.updateConnectionStatus(true);
        });

        window.wsManager.on('disconnected', (info) => {
            console.log('Disconnected from telemetry stream');
            this.updateConnectionStatus(false);
        });

        window.wsManager.on('calibration_complete', (data) => {
            this.updateCalibrationStatus(data.sensor_id, true);
        });
    }

    updateData(telemetryData) {
        if (!telemetryData || !telemetryData.pressure_transducers) return;

        const timestamp = new Date(telemetryData.timestamp);
        
        // Add new data point
        const dataPoint = {
            timestamp: timestamp,
            sensors: {}
        };

        telemetryData.pressure_transducers.forEach(reading => {
            dataPoint.sensors[reading.sensor_id] = {
                value: reading.value,
                calibrated: reading.calibrated,
                raw_value: reading.raw_value
            };
        });

        this.data.push(dataPoint);

        // Trim data if too long
        if (this.data.length > this.maxDataPoints) {
            this.data = this.data.slice(-this.maxDataPoints);
        }

        // Update displays
        this.updatePlots();
        this.updateStats();
        this.lastUpdateTime = Date.now();
    }

    initializePlots() {
        if (this.plotsInitialized) return;

        // Individual sensor plots
        this.initSubplots();
        
        // Aggregated plot
        this.initAggregatedPlot();
        
        this.plotsInitialized = true;
    }

    initSubplots() {
        const container = document.getElementById('pt-subplots');
        if (!container || !Config.PRESSURE_TRANSDUCERS) return;

        const traces = Config.PRESSURE_TRANSDUCERS.map(pt => ({
            x: [],
            y: [],
            type: 'scatter',
            mode: 'lines',
            name: pt.name,
            line: { color: pt.color, width: 2 },
            yaxis: `y${Config.PRESSURE_TRANSDUCERS.indexOf(pt) + 1}`
        }));

        const layout = {
            title: 'Pressure Transducers - Individual Readings',
            xaxis: { 
                title: 'Time',
                type: 'date'
            },
            grid: { 
                rows: Config.PRESSURE_TRANSDUCERS.length, 
                columns: 1, 
                pattern: 'independent',
                roworder: 'top to bottom'
            },
            height: 600,
            showlegend: true,
            margin: { l: 60, r: 20, t: 40, b: 40 }
        };

        // Add y-axes for each sensor
        Config.PRESSURE_TRANSDUCERS.forEach((pt, index) => {
            const yAxisKey = index === 0 ? 'yaxis' : `yaxis${index + 1}`;
            layout[yAxisKey] = {
                title: `${pt.name} (${pt.unit})`,
                anchor: 'x',
                domain: [
                    (Config.PRESSURE_TRANSDUCERS.length - index - 1) / Config.PRESSURE_TRANSDUCERS.length,
                    (Config.PRESSURE_TRANSDUCERS.length - index) / Config.PRESSURE_TRANSDUCERS.length
                ]
            };
        });

        Plotly.newPlot(container, traces, layout, {
            responsive: true,
            displayModeBar: false
        });
    }

    initAggregatedPlot() {
        const container = document.getElementById('pt-agg-plot');
        if (!container || !Config.PRESSURE_TRANSDUCERS) return;

        const traces = Config.PRESSURE_TRANSDUCERS.map(pt => ({
            x: [],
            y: [],
            type: 'scatter',
            mode: 'lines',
            name: pt.name,
            line: { color: pt.color, width: 2 }
        }));

        const layout = {
            title: 'All Pressure Transducers',
            xaxis: { 
                title: 'Time',
                type: 'date'
            },
            yaxis: { title: 'Pressure (psi)' },
            height: 400,
            showlegend: true,
            margin: { l: 60, r: 20, t: 40, b: 40 }
        };

        Plotly.newPlot(container, traces, layout, {
            responsive: true,
            displayModeBar: false
        });
    }

    updatePlots() {
        if (!this.plotsInitialized || this.data.length === 0) return;

        const recentData = this.data.slice(-500); // Show last 500 points
        
        // Update individual subplots
        this.updateSubplots(recentData);
        
        // Update aggregated plot
        this.updateAggregatedPlot(recentData);
    }

    updateSubplots(data) {
        const container = document.getElementById('pt-subplots');
        if (!container) return;

        const updates = {};
        
        Config.PRESSURE_TRANSDUCERS.forEach((pt, index) => {
            const sensorData = data.map(d => ({
                x: d.timestamp,
                y: d.sensors[pt.id]?.value || null
            })).filter(d => d.y !== null);

            updates[`x[${index}]`] = sensorData.map(d => d.x);
            updates[`y[${index}]`] = sensorData.map(d => d.y);
        });

        Plotly.restyle(container, updates);
    }

    updateAggregatedPlot(data) {
        const container = document.getElementById('pt-agg-plot');
        if (!container) return;

        const updates = {};
        
        Config.PRESSURE_TRANSDUCERS.forEach((pt, index) => {
            const sensorData = data.map(d => ({
                x: d.timestamp,
                y: d.sensors[pt.id]?.value || null
            })).filter(d => d.y !== null);

            updates[`x[${index}]`] = sensorData.map(d => d.x);
            updates[`y[${index}]`] = sensorData.map(d => d.y);
        });

        Plotly.restyle(container, updates);
    }

    updateStats() {
        if (this.data.length === 0) return;

        const recentData = this.data.slice(-100); // Last 10 seconds at 100ms intervals
        
        Config.PRESSURE_TRANSDUCERS.forEach(pt => {
            const sensorData = recentData
                .map(d => d.sensors[pt.id]?.value)
                .filter(v => v !== undefined && v !== null);

            if (sensorData.length === 0) return;

            const latest = sensorData[sensorData.length - 1];
            const avg = sensorData.reduce((a, b) => a + b, 0) / sensorData.length;
            const max = Math.max(...this.data.map(d => d.sensors[pt.id]?.value || 0));
            
            // Calculate rate (change over last 10 seconds)
            const rate = sensorData.length > 1 ? 
                ((latest - sensorData[0]) / (sensorData.length * 0.1)) : 0;

            // Get calibration status
            const isCalibrated = this.data[this.data.length - 1].sensors[pt.id]?.calibrated || false;

            this.updateStatDisplay(pt.id, {
                latest: latest.toFixed(2),
                avg: avg.toFixed(2),
                rate: rate.toFixed(2),
                max: max.toFixed(2),
                calibrated: isCalibrated ? 'Yes' : 'No'
            });
        });
    }

    updateStatDisplay(sensorId, stats) {
        const container = document.getElementById(`pt-stat-${sensorId}`);
        if (!container) return;

        const elements = {
            latest: container.querySelector('.stat-latest'),
            avg: container.querySelector('.stat-avg'),
            rate: container.querySelector('.stat-rate'),
            max: container.querySelector('.stat-max'),
            calibrated: container.querySelector('.stat-calibrated')
        };

        Object.entries(stats).forEach(([key, value]) => {
            if (elements[key]) {
                elements[key].textContent = value;
                
                // Add visual indication for calibration status
                if (key === 'calibrated') {
                    elements[key].style.color = value === 'Yes' ? '#28a745' : '#ffc107';
                    elements[key].style.fontWeight = 'bold';
                }
            }
        });
    }

    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('calibration-status');
        if (statusElement) {
            statusElement.className = connected ? 'status-indicator' : 'status-indicator error';
        }
        
        const statusText = statusElement?.nextElementSibling;
        if (statusText) {
            statusText.textContent = connected ? 'System Ready' : 'Disconnected';
        }
    }

    updateCalibrationStatus(sensorId, calibrated) {
        const sensorCard = document.querySelector(`[data-sensor="${sensorId}"]`);
        if (!sensorCard) return;

        const statusIndicator = sensorCard.querySelector('.status-indicator');
        const statusText = sensorCard.querySelector('.status-text');
        
        if (statusIndicator) {
            statusIndicator.className = calibrated ? 'status-indicator' : 'status-indicator uncalibrated';
        }
        
        if (statusText) {
            statusText.textContent = calibrated ? 'Calibrated' : 'Uncalibrated';
        }
    }

    // Manual data request (fallback)
    async requestData() {
        try {
            const response = await fetch('/api/telemetry');
            if (response.ok) {
                const data = await response.json();
                this.updateData(data);
            }
        } catch (error) {
            console.error('Failed to fetch telemetry data:', error);
        }
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.pressureDisplay = new PressureDisplay();
    
    // Fallback polling if WebSocket fails
    setInterval(() => {
        const timeSinceUpdate = Date.now() - (window.pressureDisplay?.lastUpdateTime || 0);
        if (timeSinceUpdate > 5000) { // No updates for 5 seconds
            window.pressureDisplay?.requestData();
        }
    }, 2000);
});