/**
 * WebSocket Manager for real-time telemetry and calibration updates
 */
class WebSocketManager {
    constructor() {
        this.connections = {};
        this.reconnectAttempts = {};
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.isConnected = false;
        this.listeners = {};
    }

    connect(endpoint, subscriptionType = 'telemetry') {
        const wsUrl = `ws://${window.location.host}/ws/${endpoint}`;
        const clientId = this.generateClientId();
        
        try {
            const ws = new WebSocket(`${wsUrl}?client_id=${clientId}`);
            
            ws.onopen = () => {
                console.log(`Connected to ${endpoint} WebSocket`);
                this.connections[endpoint] = ws;
                this.isConnected = true;
                this.reconnectAttempts[endpoint] = 0;
                this.emit('connected', { endpoint, clientId });
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(endpoint, data);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };

            ws.onclose = (event) => {
                console.log(`WebSocket ${endpoint} closed:`, event.code, event.reason);
                delete this.connections[endpoint];
                this.isConnected = Object.keys(this.connections).length > 0;
                
                if (!event.wasClean) {
                    this.attemptReconnect(endpoint, subscriptionType);
                }
                
                this.emit('disconnected', { endpoint, code: event.code });
            };

            ws.onerror = (error) => {
                console.error(`WebSocket ${endpoint} error:`, error);
                this.emit('error', { endpoint, error });
            };

        } catch (error) {
            console.error(`Failed to create WebSocket connection to ${endpoint}:`, error);
            this.emit('error', { endpoint, error });
        }
    }

    disconnect(endpoint) {
        if (this.connections[endpoint]) {
            this.connections[endpoint].close(1000, 'User disconnected');
            delete this.connections[endpoint];
        }
    }

    disconnectAll() {
        Object.keys(this.connections).forEach(endpoint => {
            this.disconnect(endpoint);
        });
        this.isConnected = false;
    }

    send(endpoint, message) {
        const ws = this.connections[endpoint];
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(message));
            return true;
        }
        console.warn(`Cannot send message to ${endpoint}: connection not available`);
        return false;
    }

    handleMessage(endpoint, data) {
        switch (data.type) {
            case 'telemetry_update':
                this.emit('telemetry', data.data);
                break;
            case 'calibration_update':
                this.emit('calibration_update', data);
                break;
            case 'calibration_complete':
                this.emit('calibration_complete', data);
                break;
            case 'calibration_error':
                this.emit('calibration_error', data);
                break;
            case 'health_update':
                this.emit('health', data.data);
                break;
            case 'connection_established':
                this.emit('connection_established', data);
                break;
            case 'pong':
                this.emit('pong', data);
                break;
            default:
                console.log(`Unknown message type: ${data.type}`, data);
        }
    }

    attemptReconnect(endpoint, subscriptionType) {
        const attempts = this.reconnectAttempts[endpoint] || 0;
        
        if (attempts < this.maxReconnectAttempts) {
            this.reconnectAttempts[endpoint] = attempts + 1;
            
            setTimeout(() => {
                console.log(`Attempting to reconnect to ${endpoint} (${attempts + 1}/${this.maxReconnectAttempts})`);
                this.connect(endpoint, subscriptionType);
            }, this.reconnectDelay * Math.pow(2, attempts)); // Exponential backoff
        } else {
            console.error(`Max reconnection attempts reached for ${endpoint}`);
            this.emit('reconnect_failed', { endpoint });
        }
    }

    requestCurrentData(endpoint = 'telemetry') {
        this.send(endpoint, {
            type: 'request_current_data',
            timestamp: new Date().toISOString()
        });
    }

    startCalibration(sensorId, calibrationType, parameters = {}) {
        this.send('calibration', {
            type: 'start_calibration',
            sensor_id: sensorId,
            calibration_type: calibrationType,
            parameters: parameters
        });
    }

    getCalibrationState(sensorId) {
        this.send('calibration', {
            type: 'get_calibration_state',
            sensor_id: sensorId
        });
    }

    ping(endpoint = 'telemetry') {
        this.send(endpoint, {
            type: 'ping',
            timestamp: new Date().toISOString()
        });
    }

    // Event system
    on(event, callback) {
        if (!this.listeners[event]) {
            this.listeners[event] = [];
        }
        this.listeners[event].push(callback);
    }

    off(event, callback) {
        if (!this.listeners[event]) return;
        
        const index = this.listeners[event].indexOf(callback);
        if (index > -1) {
            this.listeners[event].splice(index, 1);
        }
    }

    emit(event, data) {
        if (!this.listeners[event]) return;
        
        this.listeners[event].forEach(callback => {
            try {
                callback(data);
            } catch (error) {
                console.error(`Error in event listener for ${event}:`, error);
            }
        });
    }

    generateClientId() {
        return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    getConnectionStatus() {
        return {
            isConnected: this.isConnected,
            connections: Object.keys(this.connections),
            reconnectAttempts: this.reconnectAttempts
        };
    }

    // Heartbeat to maintain connection
    startHeartbeat(interval = 30000) {
        this.heartbeatInterval = setInterval(() => {
            Object.keys(this.connections).forEach(endpoint => {
                this.ping(endpoint);
            });
        }, interval);
    }

    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }
}

// Global WebSocket manager instance
window.wsManager = new WebSocketManager();

// Auto-connect when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Connect to telemetry by default
    window.wsManager.connect('telemetry');
    window.wsManager.connect('calibration');
    window.wsManager.connect('health');
    
    // Start heartbeat
    window.wsManager.startHeartbeat();
    
    // Clean up on page unload
    window.addEventListener('beforeunload', () => {
        window.wsManager.stopHeartbeat();
        window.wsManager.disconnectAll();
    });
});