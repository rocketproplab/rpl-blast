document.addEventListener('DOMContentLoaded', function() {
    // Default window size, can be overridden by global window.statsWindowSize
    const DEFAULT_WINDOW_SIZE = 30; // seconds, smoothing window for stats
    const RATE_SECONDS = 60; // scale rate as change per 60 seconds
    
    // Get window size from global variable or use default
    function getWindowSize() {
        return window.statsWindowSize || DEFAULT_WINDOW_SIZE;
    }

    // Store data history for each sensor: { sensorName: [{time: t, value: v}, ...], ... }
    const sensorHistories = {};
    // Store max pressure for each sensor: { sensorName: maxValue, ... }
    const sensorMaxValues = {};

    // Store all loaded analysis data for stats calculation
    let allAnalysisData = null;

    Config.PRESSURE_TRANSDUCERS.forEach(pt => {
        const sensorNameKey = pt.name.toLowerCase().replace(/ /g, '-');
        sensorHistories[sensorNameKey] = [];
        sensorMaxValues[sensorNameKey] = -Infinity;
    });
    
    // Function to load all analysis data for stats calculation
    window.loadAllPTStatsData = function(allDataEntries) {
        allAnalysisData = allDataEntries;
        // Reset max values when loading new data
        Config.PRESSURE_TRANSDUCERS.forEach(pt => {
            const sensorNameKey = pt.name.toLowerCase().replace(/ /g, '-');
            sensorMaxValues[sensorNameKey] = -Infinity;
        });
    };

    window.updateAllStats = function(currentTime, ptDataArray) {
        // Validate currentTime
        if (currentTime === undefined || currentTime === null || isNaN(currentTime)) {
            return;
        }
        
        const isAnalysisMode = window.analysisController && window.analysisController.currentMode === 'analysis';
        
        if (isAnalysisMode) {
            if (!allAnalysisData || allAnalysisData.length === 0) {
                return;
            }
            
            // In analysis mode: calculate stats from loaded data up to current playback position
            Config.PRESSURE_TRANSDUCERS.forEach((pt, index) => {
                const sensorNameKey = pt.name.toLowerCase().replace(/ /g, '-');
                
                // Filter data up to current playback position
                const WINDOW_SIZE = getWindowSize();
                const windowStartTime = Math.max(0, currentTime - WINDOW_SIZE);
                const relevantData = allAnalysisData.filter(entry => {
                    const t = entry.t_seconds || 0;
                    return t >= windowStartTime && t <= currentTime;
                });
                
                // If no data in window, try to get at least the current point
                let dataToUse = relevantData;
                if (dataToUse.length === 0) {
                    // Get the closest data point at or before currentTime
                    const closestData = allAnalysisData.filter(entry => {
                        const t = entry.t_seconds || 0;
                        return t <= currentTime;
                    });
                    if (closestData.length > 0) {
                        // Use the last point up to currentTime
                        dataToUse = [closestData[closestData.length - 1]];
                    } else {
                        // If no data at or before currentTime, use the first available data point
                        // This handles the case where data starts after time 0
                        if (allAnalysisData.length > 0) {
                            const firstDataPoint = allAnalysisData[0];
                            const firstTime = firstDataPoint.t_seconds || 0;
                            if (currentTime < firstTime) {
                                // We're before the first data point, use the first point
                                dataToUse = [firstDataPoint];
                            } else {
                                // No data at all, skip this sensor
                                return;
                            }
                        } else {
                            // No data at all, skip this sensor
                            return;
                        }
                    }
                }
                
                // Get values for this sensor
                const values = dataToUse.map(entry => {
                    const adjusted = entry.adjusted || {};
                    const ptValues = adjusted.pt || [];
                    return ptValues[index];
                }).filter(v => v !== undefined && v !== null);
                
                if (values.length === 0) {
                    // No valid values for this sensor, skip
                    return;
                }
                
                // Get latest value (at current playback position)
                const latestValue = values[values.length - 1];
                
                // Calculate average
                const sum = values.reduce((acc, v) => acc + v, 0);
                const averageValue = sum / values.length;
                
                // Calculate rate of change (from window start to current)
                let rateOfChange = 0;
                if (values.length > 1) {
                    const startValue = values[0];
                    const endValue = values[values.length - 1];
                    const firstEntry = dataToUse[0];
                    const lastEntry = dataToUse[dataToUse.length - 1];
                    const duration = (lastEntry.t_seconds || 0) - (firstEntry.t_seconds || 0);
                    if (duration > 0.1) {
                        rateOfChange = (endValue - startValue) / duration * RATE_SECONDS;
                    }
                }
                
                // Update max value (from all data up to current position)
                const allDataUpToNow = allAnalysisData.filter(entry => {
                    const t = entry.t_seconds || 0;
                    return t <= currentTime;
                });
                
                let maxValue = sensorMaxValues[sensorNameKey];
                allDataUpToNow.forEach(entry => {
                    const adjusted = entry.adjusted || {};
                    const ptValues = adjusted.pt || [];
                    const value = ptValues[index];
                    if (value !== undefined && value !== null && value > maxValue) {
                        maxValue = value;
                    }
                });
                sensorMaxValues[sensorNameKey] = maxValue;
                
                // Update DOM
                const statBlockId = `pt-stat-${sensorNameKey}`;
                const statBlock = document.getElementById(statBlockId);
                if (statBlock) {
                    const latestEl = statBlock.querySelector('.stat-latest');
                    const avgEl = statBlock.querySelector('.stat-avg');
                    const rateEl = statBlock.querySelector('.stat-rate');
                    const maxEl = statBlock.querySelector('.stat-max');
                    
                    if (latestEl) latestEl.textContent = latestValue.toFixed(2);
                    if (avgEl) avgEl.textContent = averageValue.toFixed(2);
                    if (rateEl) rateEl.textContent = rateOfChange.toFixed(2);
                    if (maxEl) maxEl.textContent = maxValue.toFixed(2);
                }
            });
            return; // Exit early in analysis mode
        } else {
            // Live mode: original behavior
            if (!ptDataArray || ptDataArray.length === 0) {
            return;
        }

        Config.PRESSURE_TRANSDUCERS.forEach((pt, index) => {
            const sensorNameKey = pt.name.toLowerCase().replace(/ /g, '-');
            const latestValue = ptDataArray[index];

            if (latestValue === undefined) return; // Skip if no data for this sensor

            // Update history
            const history = sensorHistories[sensorNameKey];
            history.push({ time: currentTime, value: latestValue });

            // Trim history to window size + a little buffer for rate calculation
            const WINDOW_SIZE = getWindowSize();
            const windowStartTime = currentTime - WINDOW_SIZE;
            while (history.length > 0 && history[0].time < windowStartTime - 1) { // Keep slightly more than WINDOW_SIZE for rate
                history.shift();
            }

            // Update Max Value
            if (latestValue > sensorMaxValues[sensorNameKey]) {
                sensorMaxValues[sensorNameKey] = latestValue;
            }

            // Calculate Stats
            let sumForAverage = 0;
            let countForAverage = 0;
            let valueAtWindowStart = null;

            // Iterate backwards from latest to find points within the window for average and rate
            for (let i = history.length - 1; i >= 0; i--) {
                const point = history[i];
                if (point.time >= windowStartTime) {
                    sumForAverage += point.value;
                    countForAverage++;
                    valueAtWindowStart = point.value; // Oldest point in/near window start
                } else {
                    // If point.time is older than windowStartTime, but no valueAtWindowStart found yet from strictly within window,
                    // use this as the closest point before window start for rate calculation if needed.
                    if (valueAtWindowStart === null) valueAtWindowStart = point.value;
                    break; // Stop once we are outside the window
                }
            }
            
            const averageValue = countForAverage > 0 ? sumForAverage / countForAverage : 0;
            
            let rateOfChange = 0;
            if (valueAtWindowStart !== null && history.length > 1) {
                // Find the actual start point for rate calculation (closest to currentTime - WINDOW_SIZE)
                let actualWindowStartPoint = history[0]; // Default to oldest point if no exact match
                for(let i = 0; i < history.length; i++){
                    if(history[i].time >= windowStartTime){
                        actualWindowStartPoint = history[i];
                        break;
                    }
                }
                if (currentTime - actualWindowStartPoint.time > 0) { // Avoid division by zero
                    // Rate based on change over the actual duration of available data in window, scaled to RATE_SECONDS
                    const duration = currentTime - actualWindowStartPoint.time;
                    if (duration > 0.1) { // only calc if duration is somewhat significant
                        rateOfChange = (latestValue - actualWindowStartPoint.value) / duration * RATE_SECONDS;
                    } else {
                        rateOfChange = 0; // or handle as N/A if duration is too short
                    }
                } else {
                    rateOfChange = 0;
                }
            } else if (history.length === 1){
                rateOfChange = 0; // Not enough data for rate
            }

            // Update DOM
            const statBlock = document.getElementById(`pt-stat-${sensorNameKey}`);
            if (statBlock) {
                statBlock.querySelector('.stat-latest').textContent = latestValue.toFixed(2);
                statBlock.querySelector('.stat-avg').textContent = averageValue.toFixed(2);
                statBlock.querySelector('.stat-rate').textContent = rateOfChange.toFixed(2);
                statBlock.querySelector('.stat-max').textContent = sensorMaxValues[sensorNameKey].toFixed(2);
            }
        });
        }
    };
});
