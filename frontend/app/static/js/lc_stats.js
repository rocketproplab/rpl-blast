document.addEventListener('DOMContentLoaded', function() {
    // Default window size, can be overridden by global window.statsWindowSize
    const DEFAULT_WINDOW_SIZE = 30; // seconds, smoothing window for stats
    
    // Get window size from global variable or use default
    function getWindowSize() {
        return window.statsWindowSize || DEFAULT_WINDOW_SIZE;
    }

    const sensorHistories = {};
    const sensorMaxValues = {};
    
    // Store all loaded analysis data for stats calculation
    let allAnalysisData = null;

    Config.LOAD_CELLS.forEach(lc => {
        const sensorNameKey = lc.name.toLowerCase().replace(/ /g, '-');
        sensorHistories[sensorNameKey] = [];
        sensorMaxValues[sensorNameKey] = -Infinity;
    });
    
    // Function to load all analysis data for stats calculation
    window.loadAllLCStatsData = function(allDataEntries) {
        allAnalysisData = allDataEntries;
        // Reset max values when loading new data
        Config.LOAD_CELLS.forEach(lc => {
            const sensorNameKey = lc.name.toLowerCase().replace(/ /g, '-');
            sensorMaxValues[sensorNameKey] = -Infinity;
        });
    };

    window.updateAllLCStats = function(currentTime, lcDataArray) {
        const isAnalysisMode = window.analysisController && window.analysisController.currentMode === 'analysis';
        
        if (isAnalysisMode && allAnalysisData && allAnalysisData.length > 0) {
            // In analysis mode: calculate stats from loaded data up to current playback position
            Config.LOAD_CELLS.forEach((lc, index) => {
                const sensorNameKey = lc.name.toLowerCase().replace(/ /g, '-');
                
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
                    const closestData = allAnalysisData.filter(entry => {
                        const t = entry.t_seconds || 0;
                        return t <= currentTime;
                    });
                    if (closestData.length > 0) {
                        dataToUse = [closestData[closestData.length - 1]];
                    } else {
                        // If no data at or before currentTime, use the first available data point
                        if (allAnalysisData.length > 0) {
                            const firstDataPoint = allAnalysisData[0];
                            const firstTime = firstDataPoint.t_seconds || 0;
                            if (currentTime < firstTime) {
                                dataToUse = [firstDataPoint];
                            } else {
                                return;
                            }
                        } else {
                            return;
                        }
                    }
                }
                
                // Get values for this sensor
                const values = dataToUse.map(entry => {
                    const adjusted = entry.adjusted || {};
                    const lcValues = adjusted.lc || [];
                    return lcValues[index];
                }).filter(v => v !== undefined && v !== null);
                
                if (values.length === 0) {
                    return; // No valid values
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
                        rateOfChange = (endValue - startValue) / duration * WINDOW_SIZE;
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
                    const lcValues = adjusted.lc || [];
                    const value = lcValues[index];
                    if (value !== undefined && value !== null && value > maxValue) {
                        maxValue = value;
                    }
                });
                sensorMaxValues[sensorNameKey] = maxValue;
                
                // Update DOM
                const statBlock = document.getElementById(`lc-stat-${sensorNameKey}`);
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
        } else {
            // Live mode: original behavior
            if (!lcDataArray || lcDataArray.length === 0) return;

            Config.LOAD_CELLS.forEach((lc, index) => {
                const sensorNameKey = lc.name.toLowerCase().replace(/ /g, '-');
                const latestValue = lcDataArray[index];
                if (latestValue === undefined) return;

                const history = sensorHistories[sensorNameKey];
                history.push({ time: currentTime, value: latestValue });

                const WINDOW_SIZE = getWindowSize();
                const windowStartTime = currentTime - WINDOW_SIZE;
                while (history.length > 0 && history[0].time < windowStartTime - 1) { history.shift(); }

                if (latestValue > sensorMaxValues[sensorNameKey]) {
                    sensorMaxValues[sensorNameKey] = latestValue;
                }

                let sumForAverage = 0, countForAverage = 0, valueAtWindowStart = null;
                for (let i = history.length - 1; i >= 0; i--) {
                    const point = history[i];
                    if (point.time >= windowStartTime) {
                        sumForAverage += point.value;
                        countForAverage++;
                        valueAtWindowStart = point.value;
                    } else {
                        if (valueAtWindowStart === null) valueAtWindowStart = point.value;
                        break;
                    }
                }
                const averageValue = countForAverage > 0 ? sumForAverage / countForAverage : 0;
                
                let rateOfChange = 0;
                if (valueAtWindowStart !== null && history.length > 1) {
                    let actualWindowStartPoint = history[0];
                    for(let i = 0; i < history.length; i++){
                        if(history[i].time >= windowStartTime){ actualWindowStartPoint = history[i]; break; }
                    }
                    const duration = currentTime - actualWindowStartPoint.time;
                    if (duration > 0.1) rateOfChange = (latestValue - actualWindowStartPoint.value) / duration * WINDOW_SIZE;
                }

                const statBlock = document.getElementById(`lc-stat-${sensorNameKey}`);
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