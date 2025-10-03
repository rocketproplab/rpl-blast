/**
 * Calibration Manager for sensor calibration controls
 */
class CalibrationManager {
    constructor() {
        this.calibrationStates = new Map();
        this.activeCalibrations = new Set();
        this.init();
    }

    init() {
        // Listen for WebSocket events
        if (window.wsManager) {
            window.wsManager.on('calibration_complete', (data) => {
                this.handleCalibrationComplete(data);
            });
            
            window.wsManager.on('calibration_error', (data) => {
                this.handleCalibrationError(data);
            });
            
            window.wsManager.on('calibration_update', (data) => {
                this.handleCalibrationUpdate(data);
            });
        }
    }

    async performAutoZero(sensorId, durationMs = 5000) {
        if (this.activeCalibrations.has(sensorId)) {
            this.showError(sensorId, 'Calibration already in progress for this sensor');
            return;
        }

        this.startCalibrationProgress(sensorId, 'auto-zero', durationMs);
        
        try {
            if (window.wsManager) {
                window.wsManager.startCalibration(sensorId, 'auto_zero', {
                    duration_ms: durationMs
                });
            } else {
                // Fallback to REST API
                await this.performCalibrationREST(sensorId, 'auto_zero', { duration_ms: durationMs });
            }
        } catch (error) {
            this.handleCalibrationError({ sensor_id: sensorId, error: error.message });
        }
    }

    async performSpanCalibration(sensorId, referenceValue, measuredValue) {
        if (this.activeCalibrations.has(sensorId)) {
            this.showError(sensorId, 'Calibration already in progress for this sensor');
            return;
        }

        if (!referenceValue || !measuredValue) {
            this.showError(sensorId, 'Reference and measured values are required for span calibration');
            return;
        }

        this.startCalibrationProgress(sensorId, 'span');
        
        try {
            if (window.wsManager) {
                window.wsManager.startCalibration(sensorId, 'span', {
                    reference_value: parseFloat(referenceValue),
                    measured_value: parseFloat(measuredValue)
                });
            } else {
                // Fallback to REST API
                await this.performCalibrationREST(sensorId, 'span', {
                    reference_value: parseFloat(referenceValue),
                    measured_value: parseFloat(measuredValue)
                });
            }
        } catch (error) {
            this.handleCalibrationError({ sensor_id: sensorId, error: error.message });
        }
    }

    async performCalibrationREST(sensorId, calibrationType, parameters) {
        const url = `/api/sensors/${sensorId}/calibrate`;
        const params = new URLSearchParams({
            calibration_type: calibrationType,
            ...parameters
        });

        const response = await fetch(`${url}?${params}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Calibration failed');
        }

        const result = await response.json();
        this.handleCalibrationComplete({ sensor_id: sensorId, data: result });
        return result;
    }

    startCalibrationProgress(sensorId, type, durationMs = null) {
        this.activeCalibrations.add(sensorId);
        
        const progressElement = document.querySelector(`[data-sensor="${sensorId}"] .calibration-progress`);
        const button = document.querySelector(`[data-sensor="${sensorId}"] [data-action="${type}"]`);
        
        if (progressElement) {
            progressElement.classList.add('active');
            progressElement.querySelector('.progress-message').textContent = 
                `Performing ${type} calibration...`;
        }
        
        if (button) {
            button.disabled = true;
            button.classList.add('calibrating');
        }

        // If we have a duration, show progress bar
        if (durationMs && progressElement) {
            const progressBar = progressElement.querySelector('.progress-fill');
            let progress = 0;
            const interval = 100; // Update every 100ms
            const increment = (interval / durationMs) * 100;
            
            const progressTimer = setInterval(() => {
                progress += increment;
                if (progressBar) {
                    progressBar.style.width = `${Math.min(progress, 100)}%`;
                }
                
                if (progress >= 100) {
                    clearInterval(progressTimer);
                }
            }, interval);
            
            // Store timer reference to clear if needed
            this.progressTimers = this.progressTimers || new Map();
            this.progressTimers.set(sensorId, progressTimer);
        }
    }

    handleCalibrationComplete(data) {
        const sensorId = data.sensor_id;
        const result = data.data;
        
        this.activeCalibrations.delete(sensorId);
        this.calibrationStates.set(sensorId, result);
        
        // Clear progress timer if exists
        if (this.progressTimers && this.progressTimers.has(sensorId)) {
            clearInterval(this.progressTimers.get(sensorId));
            this.progressTimers.delete(sensorId);
        }
        
        this.hideProgress(sensorId);
        this.showSuccess(sensorId, result);
        this.updateCalibrationDisplay(sensorId, result);
        this.enableButtons(sensorId);
        
        // Request updated calibration state
        this.refreshCalibrationState(sensorId);
    }

    handleCalibrationError(data) {
        const sensorId = data.sensor_id;
        const error = data.error;
        
        this.activeCalibrations.delete(sensorId);
        
        // Clear progress timer if exists
        if (this.progressTimers && this.progressTimers.has(sensorId)) {
            clearInterval(this.progressTimers.get(sensorId));
            this.progressTimers.delete(sensorId);
        }
        
        this.hideProgress(sensorId);
        this.showError(sensorId, error);
        this.enableButtons(sensorId);
    }

    handleCalibrationUpdate(data) {
        const sensorId = data.sensor_id;
        const updateData = data.data;
        
        // Update any in-progress indicators
        const progressElement = document.querySelector(`[data-sensor="${sensorId}"] .calibration-progress`);
        if (progressElement && updateData.progress) {
            const progressBar = progressElement.querySelector('.progress-fill');
            if (progressBar) {
                progressBar.style.width = `${updateData.progress}%`;
            }
        }
    }

    hideProgress(sensorId) {
        const progressElement = document.querySelector(`[data-sensor="${sensorId}"] .calibration-progress`);
        if (progressElement) {
            progressElement.classList.remove('active');
        }
    }

    showSuccess(sensorId, result) {
        const resultsElement = document.querySelector(`[data-sensor="${sensorId}"] .calibration-results`);
        if (resultsElement) {
            resultsElement.className = 'calibration-results success';
            resultsElement.innerHTML = `
                <strong>Calibration completed successfully!</strong><br>
                Type: ${result.calibration_type}<br>
                ${result.new_offset !== undefined ? `New offset: ${result.new_offset.toFixed(3)}` : ''}
                ${result.new_span !== undefined ? `New span: ${result.new_span.toFixed(3)}` : ''}
            `;
            
            setTimeout(() => {
                resultsElement.style.display = 'none';
            }, 5000);
        }
    }

    showError(sensorId, error) {
        const resultsElement = document.querySelector(`[data-sensor="${sensorId}"] .calibration-results`);
        if (resultsElement) {
            resultsElement.className = 'calibration-results error';
            resultsElement.innerHTML = `<strong>Calibration failed:</strong><br>${error}`;
            
            setTimeout(() => {
                resultsElement.style.display = 'none';
            }, 8000);
        }
    }

    enableButtons(sensorId) {
        const buttons = document.querySelectorAll(`[data-sensor="${sensorId}"] .calibration-button`);
        buttons.forEach(button => {
            button.disabled = false;
            button.classList.remove('calibrating');
        });
    }

    updateCalibrationDisplay(sensorId, state) {
        const statusIndicator = document.querySelector(`[data-sensor="${sensorId}"] .status-indicator`);
        if (statusIndicator) {
            statusIndicator.className = 'status-indicator';
            if (state.success) {
                // Calibrated successfully
            } else {
                statusIndicator.classList.add('error');
            }
        }

        // Update calibration info
        const infoContainer = document.querySelector(`[data-sensor="${sensorId}"] .calibration-info`);
        if (infoContainer && state) {
            this.updateInfoValue(infoContainer, 'zero-offset', state.new_offset?.toFixed(3) || 'N/A');
            this.updateInfoValue(infoContainer, 'span-multiplier', state.new_span?.toFixed(3) || 'N/A');
            this.updateInfoValue(infoContainer, 'last-calibrated', 
                state.last_calibrated ? new Date(state.last_calibrated).toLocaleString() : 'Never');
        }
    }

    updateInfoValue(container, key, value) {
        const element = container.querySelector(`[data-info="${key}"] .info-value`);
        if (element) {
            element.textContent = value;
        }
    }

    async refreshCalibrationState(sensorId) {
        try {
            if (window.wsManager) {
                window.wsManager.getCalibrationState(sensorId);
            } else {
                // Fallback to REST API
                const response = await fetch(`/api/sensors/${sensorId}/calibration`);
                if (response.ok) {
                    const state = await response.json();
                    this.updateCalibrationDisplay(sensorId, state);
                }
            }
        } catch (error) {
            console.error(`Failed to refresh calibration state for ${sensorId}:`, error);
        }
    }

    // Initialize calibration controls for a sensor
    initializeSensorControls(sensorId) {
        const sensorElement = document.querySelector(`[data-sensor="${sensorId}"]`);
        if (!sensorElement) return;

        // Auto-zero button
        const autoZeroBtn = sensorElement.querySelector('[data-action="auto-zero"]');
        if (autoZeroBtn) {
            autoZeroBtn.addEventListener('click', () => {
                const duration = sensorElement.querySelector('[data-input="duration"]')?.value || 5000;
                this.performAutoZero(sensorId, parseInt(duration));
            });
        }

        // Span calibration button
        const spanBtn = sensorElement.querySelector('[data-action="span"]');
        if (spanBtn) {
            spanBtn.addEventListener('click', () => {
                const refValue = sensorElement.querySelector('[data-input="reference"]')?.value;
                const measValue = sensorElement.querySelector('[data-input="measured"]')?.value;
                this.performSpanCalibration(sensorId, refValue, measValue);
            });
        }

        // Refresh state button
        const refreshBtn = sensorElement.querySelector('[data-action="refresh"]');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.refreshCalibrationState(sensorId);
            });
        }

        // Load initial calibration state
        this.refreshCalibrationState(sensorId);
    }
}

// Global calibration manager instance
window.calibrationManager = new CalibrationManager();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Find all sensor calibration elements and initialize them
    const sensorElements = document.querySelectorAll('[data-sensor]');
    sensorElements.forEach(element => {
        const sensorId = element.getAttribute('data-sensor');
        window.calibrationManager.initializeSensorControls(sensorId);
    });
});