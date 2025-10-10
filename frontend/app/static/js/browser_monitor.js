/**
 * Browser Activity Monitor
 * Detects browser throttling, visibility changes, and performance issues
 * Sends heartbeat to server to maintain connection awareness
 */

(function() {
    'use strict';

    class BrowserMonitor {
        constructor() {
            // Configuration
            this.config = {
                heartbeatInterval: 1000,  // 1 second
                throttleDetectionThreshold: 2000,  // 2 seconds indicates throttling
                serverHeartbeatEndpoint: '/api/browser_heartbeat',
                performanceCheckInterval: 5000,  // 5 seconds
                maxMissedHeartbeats: 5
            };

            // State tracking
            this.state = {
                lastHeartbeat: Date.now(),
                missedHeartbeats: 0,
                isThrottled: false,
                isVisible: !document.hidden,
                frameDrops: 0,
                lastFrameTime: performance.now(),
                performanceMetrics: []
            };

            // Bind methods
            this.handleVisibilityChange = this.handleVisibilityChange.bind(this);
            this.checkThrottling = this.checkThrottling.bind(this);
            this.sendHeartbeat = this.sendHeartbeat.bind(this);
            this.measurePerformance = this.measurePerformance.bind(this);
            this.checkFrameRate = this.checkFrameRate.bind(this);

            // Start monitoring
            this.init();
        }

        init() {
            console.log('[BrowserMonitor] Initializing browser monitoring');

            // Set up visibility change detection
            document.addEventListener('visibilitychange', this.handleVisibilityChange);
            
            // Set up page hide/show events (more reliable on mobile)
            window.addEventListener('pagehide', () => this.handlePageHide());
            window.addEventListener('pageshow', () => this.handlePageShow());

            // Set up focus/blur detection
            window.addEventListener('blur', () => this.handleWindowBlur());
            window.addEventListener('focus', () => this.handleWindowFocus());

            // Start heartbeat
            this.heartbeatTimer = setInterval(this.checkThrottling, this.config.heartbeatInterval);
            
            // Start performance monitoring
            this.performanceTimer = setInterval(this.measurePerformance, this.config.performanceCheckInterval);

            // Start frame rate monitoring
            this.startFrameRateMonitoring();

            // Send initial status
            this.sendStatus('initialized');
        }

        handleVisibilityChange() {
            const wasVisible = this.state.isVisible;
            this.state.isVisible = !document.hidden;

            console.log(`[BrowserMonitor] Visibility changed: ${wasVisible} -> ${this.state.isVisible}`);

            if (this.state.isVisible && !wasVisible) {
                // Page became visible
                this.sendStatus('page_visible');
                this.onPageResumed();
            } else if (!this.state.isVisible && wasVisible) {
                // Page became hidden
                this.sendStatus('page_hidden');
                this.onPageSuspended();
            }
        }

        handlePageHide() {
            console.log('[BrowserMonitor] Page hide event');
            this.sendStatus('page_hide');
            this.onPageSuspended();
        }

        handlePageShow() {
            console.log('[BrowserMonitor] Page show event');
            this.sendStatus('page_show');
            this.onPageResumed();
        }

        handleWindowBlur() {
            console.log('[BrowserMonitor] Window lost focus');
            this.sendStatus('window_blur');
        }

        handleWindowFocus() {
            console.log('[BrowserMonitor] Window gained focus');
            this.sendStatus('window_focus');
            
            // Check if we were throttled while unfocused
            if (this.state.isThrottled) {
                this.onPageResumed();
            }
        }

        checkThrottling() {
            const now = Date.now();
            const timeSinceLastHeartbeat = now - this.state.lastHeartbeat;

            // Check if we've been throttled
            if (timeSinceLastHeartbeat > this.config.throttleDetectionThreshold) {
                if (!this.state.isThrottled) {
                    this.state.isThrottled = true;
                    console.warn(`[BrowserMonitor] Throttling detected! Gap: ${timeSinceLastHeartbeat}ms`);
                    this.sendStatus('throttled', {
                        gap_ms: timeSinceLastHeartbeat,
                        visibility: document.visibilityState
                    });
                }
                this.state.missedHeartbeats++;
            } else if (this.state.isThrottled) {
                // Recovered from throttling
                this.state.isThrottled = false;
                this.state.missedHeartbeats = 0;
                console.log('[BrowserMonitor] Recovered from throttling');
                this.sendStatus('throttle_recovered');
            }

            this.state.lastHeartbeat = now;

            // Send heartbeat to server
            if (!this.state.isThrottled && this.state.isVisible) {
                this.sendHeartbeat();
            }
        }

        sendHeartbeat() {
            // Send lightweight heartbeat to server
            fetch(this.config.serverHeartbeatEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    timestamp: Date.now(),
                    visible: this.state.isVisible,
                    throttled: this.state.isThrottled,
                    missed_heartbeats: this.state.missedHeartbeats
                })
            }).catch(err => {
                console.error('[BrowserMonitor] Failed to send heartbeat:', err);
            });
        }

        measurePerformance() {
            if (!this.state.isVisible) return;

            // Use Performance API to measure
            if (window.performance && window.performance.memory) {
                const metrics = {
                    timestamp: Date.now(),
                    memory: {
                        used: window.performance.memory.usedJSHeapSize,
                        total: window.performance.memory.totalJSHeapSize,
                        limit: window.performance.memory.jsHeapSizeLimit
                    }
                };

                // Check for memory pressure
                const memoryUsage = metrics.memory.used / metrics.memory.limit;
                if (memoryUsage > 0.9) {
                    console.warn('[BrowserMonitor] High memory usage:', (memoryUsage * 100).toFixed(1) + '%');
                    this.sendStatus('high_memory', metrics);
                }

                // Store metrics
                this.state.performanceMetrics.push(metrics);
                if (this.state.performanceMetrics.length > 60) {
                    this.state.performanceMetrics.shift();
                }
            }

            // Check main thread responsiveness
            this.checkMainThreadResponsiveness();
        }

        checkMainThreadResponsiveness() {
            const start = performance.now();
            
            // Schedule a microtask to measure main thread delay
            Promise.resolve().then(() => {
                const delay = performance.now() - start;
                if (delay > 50) {  // Main thread blocked for >50ms
                    console.warn(`[BrowserMonitor] Main thread blocked for ${delay.toFixed(1)}ms`);
                    this.sendStatus('main_thread_blocked', { delay_ms: delay });
                }
            });
        }

        startFrameRateMonitoring() {
            const checkFrame = (timestamp) => {
                if (this.state.lastFrameTime) {
                    const frameDuration = timestamp - this.state.lastFrameTime;
                    
                    // Check for dropped frames (>33ms for 30fps, >16ms for 60fps)
                    if (frameDuration > 33) {
                        this.state.frameDrops++;
                        
                        if (this.state.frameDrops > 10) {
                            console.warn(`[BrowserMonitor] Multiple frame drops detected: ${this.state.frameDrops}`);
                            this.sendStatus('frame_drops', { 
                                count: this.state.frameDrops,
                                duration_ms: frameDuration 
                            });
                            this.state.frameDrops = 0;  // Reset counter
                        }
                    } else {
                        // Reset counter on good frames
                        this.state.frameDrops = Math.max(0, this.state.frameDrops - 1);
                    }
                }
                
                this.state.lastFrameTime = timestamp;
                
                // Continue monitoring if visible
                if (this.state.isVisible) {
                    requestAnimationFrame(checkFrame);
                }
            };

            // Start monitoring
            requestAnimationFrame(checkFrame);
        }

        checkFrameRate() {
            // Additional frame rate check using setTimeout comparison
            const expectedInterval = 16.67;  // 60fps
            let lastTime = performance.now();
            let frameCount = 0;
            let totalDeviation = 0;

            const measure = () => {
                const now = performance.now();
                const actualInterval = now - lastTime;
                const deviation = Math.abs(actualInterval - expectedInterval);
                
                totalDeviation += deviation;
                frameCount++;

                if (frameCount >= 60) {  // Check every 60 frames
                    const avgDeviation = totalDeviation / frameCount;
                    
                    if (avgDeviation > 5) {
                        console.warn(`[BrowserMonitor] Irregular frame timing: ${avgDeviation.toFixed(2)}ms average deviation`);
                        this.sendStatus('irregular_frames', { 
                            avg_deviation: avgDeviation,
                            frames_measured: frameCount 
                        });
                    }
                    
                    // Reset counters
                    frameCount = 0;
                    totalDeviation = 0;
                }

                lastTime = now;

                if (this.state.isVisible) {
                    setTimeout(measure, expectedInterval);
                }
            };

            measure();
        }

        onPageSuspended() {
            console.log('[BrowserMonitor] Page suspended - stopping intensive monitoring');
            
            // Clear performance timer to save resources
            if (this.performanceTimer) {
                clearInterval(this.performanceTimer);
                this.performanceTimer = null;
            }

            // Notify server
            this.sendStatus('suspended');
        }

        onPageResumed() {
            console.log('[BrowserMonitor] Page resumed - restarting monitoring');
            
            // Reset state
            this.state.isThrottled = false;
            this.state.missedHeartbeats = 0;
            this.state.lastHeartbeat = Date.now();

            // Restart performance monitoring if it was stopped
            if (!this.performanceTimer) {
                this.performanceTimer = setInterval(this.measurePerformance, this.config.performanceCheckInterval);
            }

            // Restart frame monitoring
            this.startFrameRateMonitoring();

            // Notify server
            this.sendStatus('resumed');

            // Force a data refresh
            if (window.refreshData) {
                console.log('[BrowserMonitor] Triggering data refresh after resume');
                window.refreshData();
            }
        }

        sendStatus(event, data = {}) {
            // Send status update to server
            fetch('/api/browser_status', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    event: event,
                    timestamp: Date.now(),
                    visible: this.state.isVisible,
                    throttled: this.state.isThrottled,
                    ...data
                })
            }).catch(err => {
                console.error('[BrowserMonitor] Failed to send status:', err);
            });
        }

        destroy() {
            // Clean up event listeners and timers
            document.removeEventListener('visibilitychange', this.handleVisibilityChange);
            window.removeEventListener('blur', this.handleWindowBlur);
            window.removeEventListener('focus', this.handleWindowFocus);
            window.removeEventListener('pagehide', this.handlePageHide);
            window.removeEventListener('pageshow', this.handlePageShow);

            if (this.heartbeatTimer) {
                clearInterval(this.heartbeatTimer);
            }
            
            if (this.performanceTimer) {
                clearInterval(this.performanceTimer);
            }

            console.log('[BrowserMonitor] Destroyed');
        }

        // Public API for debugging
        getStatus() {
            return {
                ...this.state,
                memoryUsage: window.performance?.memory ? {
                    used: window.performance.memory.usedJSHeapSize,
                    total: window.performance.memory.totalJSHeapSize,
                    limit: window.performance.memory.jsHeapSizeLimit,
                    percentage: (window.performance.memory.usedJSHeapSize / window.performance.memory.jsHeapSizeLimit * 100).toFixed(1) + '%'
                } : null
            };
        }
    }

    // Initialize and expose globally
    window.BrowserMonitor = BrowserMonitor;
    window.browserMonitor = new BrowserMonitor();

    console.log('[BrowserMonitor] Browser monitoring started');
    console.log('[BrowserMonitor] Use window.browserMonitor.getStatus() to check current status');

})();