/**
 * Browser Performance Monitor for Multi-Window Support
 * Optimizes performance when running multiple BLAST windows
 */
class BrowserMonitor {
    constructor() {
        this.isVisible = true;
        this.isActive = true;
        this.performanceMode = 'normal';
        this.lastActivity = Date.now();
        
        this.init();
    }

    init() {
        this.setupVisibilityListener();
        this.setupActivityMonitoring();
        this.setupPerformanceOptimization();
        
        // Check if running in multiple windows
        this.detectMultipleWindows();
    }

    setupVisibilityListener() {
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            this.isVisible = !document.hidden;
            this.updatePerformanceMode();
            
            if (this.isVisible) {
                // Request fresh data when window becomes visible
                if (window.wsManager) {
                    window.wsManager.requestCurrentData();
                }
            }
        });

        // Handle window focus/blur
        window.addEventListener('focus', () => {
            this.isActive = true;
            this.updatePerformanceMode();
        });

        window.addEventListener('blur', () => {
            this.isActive = false;
            this.updatePerformanceMode();
        });
    }

    setupActivityMonitoring() {
        // Track user activity
        const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
        
        const updateActivity = () => {
            this.lastActivity = Date.now();
        };

        activityEvents.forEach(event => {
            document.addEventListener(event, updateActivity, { passive: true });
        });

        // Check for inactivity periodically
        setInterval(() => {
            const timeSinceActivity = Date.now() - this.lastActivity;
            const isInactive = timeSinceActivity > 30000; // 30 seconds
            
            if (isInactive !== !this.isActive) {
                this.isActive = !isInactive;
                this.updatePerformanceMode();
            }
        }, 5000);
    }

    setupPerformanceOptimization() {
        // Optimize animation frames when not active
        const originalRequestAnimationFrame = window.requestAnimationFrame;
        
        window.requestAnimationFrame = (callback) => {
            if (this.performanceMode === 'reduced') {
                // Reduce animation frame rate when not active
                setTimeout(callback, 250); // 4 FPS instead of 60
            } else {
                originalRequestAnimationFrame(callback);
            }
        };

        // Monitor memory usage
        if ('memory' in performance) {
            setInterval(() => {
                const memory = performance.memory;
                const memoryUsage = memory.usedJSHeapSize / memory.jsHeapSizeLimit;
                
                if (memoryUsage > 0.8) {
                    console.warn('High memory usage detected:', memoryUsage);
                    this.optimizeMemory();
                }
            }, 30000);
        }
    }

    updatePerformanceMode() {
        const previousMode = this.performanceMode;
        
        if (!this.isVisible || !this.isActive) {
            this.performanceMode = 'reduced';
        } else {
            this.performanceMode = 'normal';
        }

        if (previousMode !== this.performanceMode) {
            this.notifyPerformanceModeChange();
        }
    }

    notifyPerformanceModeChange() {
        console.log(`Performance mode changed to: ${this.performanceMode}`);
        
        // Notify other components about performance mode change
        document.dispatchEvent(new CustomEvent('performanceModeChange', {
            detail: { mode: this.performanceMode }
        }));

        // Adjust WebSocket update frequency
        if (window.wsManager) {
            if (this.performanceMode === 'reduced') {
                // Reduce update frequency when not active
                this.adjustWebSocketFrequency(1000); // 1 second intervals
            } else {
                // Normal frequency when active
                this.adjustWebSocketFrequency(100); // 100ms intervals
            }
        }
    }

    adjustWebSocketFrequency(intervalMs) {
        // This would need to be implemented in the WebSocket manager
        // For now, we'll just log the intended change
        console.log(`Adjusting WebSocket frequency to ${intervalMs}ms`);
    }

    detectMultipleWindows() {
        // Use localStorage to detect multiple BLAST windows
        const windowId = `blast_window_${Date.now()}_${Math.random()}`;
        const windowsKey = 'blast_active_windows';
        
        // Register this window
        const activeWindows = JSON.parse(localStorage.getItem(windowsKey) || '[]');
        activeWindows.push({
            id: windowId,
            timestamp: Date.now(),
            path: window.location.pathname
        });
        
        // Clean up old windows (older than 10 seconds)
        const recentWindows = activeWindows.filter(w => Date.now() - w.timestamp < 10000);
        localStorage.setItem(windowsKey, JSON.stringify(recentWindows));
        
        // Update window count periodically
        setInterval(() => {
            const windows = JSON.parse(localStorage.getItem(windowsKey) || '[]');
            const activeCount = windows.filter(w => Date.now() - w.timestamp < 10000).length;
            
            if (activeCount > 1) {
                console.log(`Multiple BLAST windows detected: ${activeCount}`);
                this.enableMultiWindowOptimizations();
            }
            
            // Update this window's timestamp
            const updatedWindows = windows.map(w => 
                w.id === windowId ? { ...w, timestamp: Date.now() } : w
            );
            localStorage.setItem(windowsKey, JSON.stringify(updatedWindows));
        }, 5000);

        // Clean up when window closes
        window.addEventListener('beforeunload', () => {
            const windows = JSON.parse(localStorage.getItem(windowsKey) || '[]');
            const filteredWindows = windows.filter(w => w.id !== windowId);
            localStorage.setItem(windowsKey, JSON.stringify(filteredWindows));
        });
    }

    enableMultiWindowOptimizations() {
        // Implement optimizations for multiple windows
        if (!this.multiWindowOptimizationsEnabled) {
            console.log('Enabling multi-window performance optimizations');
            
            // Reduce update frequency for background windows
            if (!this.isVisible || !this.isActive) {
                this.performanceMode = 'reduced';
                this.notifyPerformanceModeChange();
            }
            
            this.multiWindowOptimizationsEnabled = true;
        }
    }

    optimizeMemory() {
        // Force garbage collection if available
        if (window.gc) {
            window.gc();
        }
        
        // Limit stored data points in displays
        if (window.pressureDisplay && window.pressureDisplay.data) {
            window.pressureDisplay.data = window.pressureDisplay.data.slice(-500);
        }
        
        console.log('Memory optimization performed');
    }

    getPerformanceInfo() {
        return {
            isVisible: this.isVisible,
            isActive: this.isActive,
            performanceMode: this.performanceMode,
            timeSinceActivity: Date.now() - this.lastActivity,
            memory: performance.memory ? {
                used: performance.memory.usedJSHeapSize,
                total: performance.memory.totalJSHeapSize,
                limit: performance.memory.jsHeapSizeLimit
            } : null
        };
    }
}

// Initialize browser monitor
window.browserMonitor = new BrowserMonitor();

// Listen for performance mode changes in other components
document.addEventListener('performanceModeChange', (event) => {
    const mode = event.detail.mode;
    
    // Adjust plot update frequencies
    if (window.pressureDisplay) {
        if (mode === 'reduced') {
            // Reduce plot update frequency
            window.pressureDisplay.updateInterval = 1000;
        } else {
            // Normal update frequency
            window.pressureDisplay.updateInterval = 100;
        }
    }
});