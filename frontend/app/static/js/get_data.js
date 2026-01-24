// app/static/js/get_data.js
document.addEventListener('DOMContentLoaded', function() {
    const UPDATE_INTERVAL = 100; // ms, data fetch frequency for live mode
    const ANALYSIS_UPDATE_INTERVAL = 16; // ms, ~60fps for smoother analysis mode playback
    const startTime = Date.now();
    let lastUpdateTime = 0;
    let lastPlaybackPosition = -1;
    let dataUpdateInterval = null;
    let animationFrameId = null;

    function getCurrentTime() {
        // Check if we're in analysis mode
        if (window.analysisController && window.analysisController.currentMode === 'analysis') {
            // In analysis mode, use calculated position for smoother updates
            if (typeof window.analysisController.getCurrentPosition === 'function') {
                return window.analysisController.getCurrentPosition();
            }
            // Fallback to stored position
            return window.analysisController.playbackState.position || 0;
        } else {
            // In live mode, use elapsed time
            return (Date.now() - startTime) / 1000;
        }
    }

    function shouldUpdate() {
        // In analysis mode, only update if playback position changed AND not paused (or if position changed while paused)
        if (window.analysisController && window.analysisController.currentMode === 'analysis') {
            const currentPos = window.analysisController.playbackState.position || 0;
            const isPaused = window.analysisController.playbackState.isPaused;
            
            // Update if position changed (including initial load when lastPlaybackPosition is -1)
            // This handles: initial load, seeking while paused, and playback advancing
            if (currentPos !== lastPlaybackPosition || lastPlaybackPosition === -1) {
                lastPlaybackPosition = currentPos;
                return true;
            }
            
            // If paused and position hasn't changed, don't update at all
            // This prevents the plot from updating when paused
            return false;
        } else {
            // In live mode, always update
            // Reset lastPlaybackPosition when switching to live mode
            if (lastPlaybackPosition !== -1) {
                lastPlaybackPosition = -1;
            }
            return true;
        }
    }

    function fetchAllDataAndUpdate() {
        if (!shouldUpdate()) {
            return;
        }

        const currentTime = getCurrentTime();
        lastUpdateTime = Date.now();

        fetch('/data') 
            .then(response => {
                if (!response.ok) {
                    console.error('get_data.js: Network response was not ok', response.statusText);
                    throw new Error('Network response was not ok ' + response.statusText);
                }
                return response.json();
            })
            .then(data => {
                if (data && data.value) {
                    const allSensorData = data.value;
                    const isAnalysisMode = window.analysisController && window.analysisController.currentMode === 'analysis';

                    // In analysis mode, just update the window position
                    if (isAnalysisMode) {
                        if (typeof window.analysisController !== 'undefined' && window.analysisController.updateAnalysisPlotWindow) {
                            window.analysisController.updateAnalysisPlotWindow(currentTime);
                        }
                        
                        // Update stats based on current playback position (using loaded data)
                        // Pass currentTime and dummy array - stats will use loaded data
                        // Pressure Transducers
                        if (typeof window.updateAllStats === 'function') {
                            window.updateAllStats(currentTime, allSensorData.pt || []);
                        } else {
                            console.warn('get_data.js: updateAllStats function not found');
                        }
                        
                        // Thermocouples
                        if (typeof window.updateAllTCStats === 'function') {
                            window.updateAllTCStats(currentTime, allSensorData.tc || []);
                        } else {
                            console.warn('get_data.js: updateAllTCStats function not found');
                        }
                        
                        // Load Cells
                        if (typeof window.updateAllLCStats === 'function') {
                            window.updateAllLCStats(currentTime, allSensorData.lc || []);
                        } else {
                            console.warn('get_data.js: updateAllLCStats function not found');
                        }
                    }

                    // Pressure Transducers
                    if (allSensorData.pt) {
                        if (typeof window.updatePTPlotsAndStats === 'function') {
                            window.updatePTPlotsAndStats(currentTime, allSensorData.pt);
                        }
                    }

                    // Thermocouples
                    if (allSensorData.tc) {
                        if (typeof window.updateTCPlotsAndStats === 'function') {
                            window.updateTCPlotsAndStats(currentTime, allSensorData.tc);
                        }
                    }

                    // Load Cells
                    if (allSensorData.lc) {
                        if (typeof window.updateLCPlotsAndStats === 'function') {
                            window.updateLCPlotsAndStats(currentTime, allSensorData.lc);
                        }
                    }

                    // Flow Control Valves
                    if (allSensorData.fcv_actual && allSensorData.fcv_expected) {
                        if (typeof window.updateValveDisplays === 'function') {
                            window.updateValveDisplays(allSensorData.fcv_actual, allSensorData.fcv_expected);
                        }
                    }
                }
            })
            .catch(error => console.error('get_data.js: Error in fetchAllDataAndUpdate:', error));
    }

    function startDataUpdates() {
        // Clear any existing intervals or animation frames
        if (dataUpdateInterval) {
            clearInterval(dataUpdateInterval);
            dataUpdateInterval = null;
        }
        if (animationFrameId) {
            cancelAnimationFrame(animationFrameId);
            animationFrameId = null;
        }
        
        const isAnalysisMode = window.analysisController && window.analysisController.currentMode === 'analysis';
        
        if (isAnalysisMode) {
            // In analysis mode, use requestAnimationFrame for smoother 60fps updates
            function animate() {
                fetchAllDataAndUpdate();
                animationFrameId = requestAnimationFrame(animate);
            }
            animationFrameId = requestAnimationFrame(animate);
        } else {
            // In live mode, use setInterval
            dataUpdateInterval = setInterval(fetchAllDataAndUpdate, UPDATE_INTERVAL);
        }
    }

    // Start initial updates
    startDataUpdates();

    // Listen for mode changes to adjust update interval
    // This will be called by analysis mode controller when mode changes
    window.restartDataUpdates = function() {
        startDataUpdates();
    };
    
    // Force an immediate data update (useful after loading analysis run)
    window.forceDataUpdate = function() {
        lastPlaybackPosition = -1; // Reset to force update
        fetchAllDataAndUpdate();
    };
}); 