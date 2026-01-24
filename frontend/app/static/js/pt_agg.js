document.addEventListener('DOMContentLoaded', function() {
    // Default window size, can be overridden by global window.plotWindowSize
    const DEFAULT_WINDOW_SIZE = 30; // Size of the time window in seconds
    
    // Get window size from global variable or use default
    function getWindowSize() {
        return window.plotWindowSize || DEFAULT_WINDOW_SIZE;
    }
    const sensorData = {
        x: [],
        y: Array(Config.NUM_PRESSURE_TRANSDUCERS).fill().map(() => [])
    };
    let totalDataDuration = 0; // Store total duration of loaded data
    
    // Function to clear plot data (called when switching to analysis mode)
    window.clearPTPlotData = function() {
        sensorData.x = [];
        sensorData.y = Array(Config.NUM_PRESSURE_TRANSDUCERS).fill().map(() => []);
    };
    
    // Function to load all analysis data at once
    window.loadAllPTAnalysisData = function(allDataEntries) {
        // Clear existing data
        sensorData.x = [];
        sensorData.y = Array(Config.NUM_PRESSURE_TRANSDUCERS).fill().map(() => []);
        
        // Load all data points
        allDataEntries.forEach(entry => {
            const t = entry.t_seconds || 0;
            const adjusted = entry.adjusted || {};
            const ptValues = adjusted.pt || [];
            
            sensorData.x.push(t);
            ptValues.forEach((value, i) => {
                if (i < sensorData.y.length) {
                    sensorData.y[i].push(value);
                }
            });
        });
        
        // Store total duration
        if (sensorData.x.length > 0) {
            totalDataDuration = sensorData.x[sensorData.x.length - 1];
        }
        
        // Create zone shapes that span the full data range
        let newShapes = [];
        if (Config.PRESSURE_TRANSDUCERS.length > 0 && totalDataDuration > 0) {
            const firstPTConfig = Config.PRESSURE_TRANSDUCERS[0];
            newShapes = [
                // Green Zone - spans full duration
                { type: 'rect', x0: 0, x1: totalDataDuration, 
                  y0: firstPTConfig.min_value, y1: firstPTConfig.warning_value, 
                  fillcolor: 'rgba(0, 255, 0, 0.2)', line: { width: 0 }, layer: 'below' },
                // Orange Zone - spans full duration
                { type: 'rect', x0: 0, x1: totalDataDuration, 
                  y0: firstPTConfig.warning_value, y1: firstPTConfig.danger_value, 
                  fillcolor: 'rgba(255, 165, 0, 0.2)', line: { width: 0 }, layer: 'below' },
                // Red Zone - spans full duration
                { type: 'rect', x0: 0, x1: totalDataDuration, 
                  y0: firstPTConfig.danger_value, y1: firstPTConfig.max_value, 
                  fillcolor: 'rgba(255, 0, 0, 0.2)', line: { width: 0 }, layer: 'below' }
            ];
        }
        
        // Update plot with all data and zone shapes
        const updateData = {
            x: sensorData.y.map(() => sensorData.x),
            y: sensorData.y
        };
        
        Plotly.update('pt-agg-plot', updateData, {
            shapes: newShapes
        });
    };
    
    // Function to update plot window based on playback position
    window.updatePTPlotWindow = function(currentPosition) {
        const WINDOW_SIZE = getWindowSize();
        const windowStart = Math.max(0, currentPosition - WINDOW_SIZE);
        const windowEnd = currentPosition;
        
        Plotly.relayout('pt-agg-plot', {
            'xaxis.range': [windowStart, windowEnd]
        });
    };

    // Get container dimensions
    const container = document.querySelector('.pt-agg-container');
    const rect = container.getBoundingClientRect();
    const computedStyle = window.getComputedStyle(container);
    const paddingX = parseFloat(computedStyle.paddingLeft) + parseFloat(computedStyle.paddingRight);
    const paddingY = parseFloat(computedStyle.paddingTop) + parseFloat(computedStyle.paddingBottom);

    // Create traces for each pressure transducer
    const traces = Config.PRESSURE_TRANSDUCERS.map((pt, index) => ({
        x: [],
        y: [],
        ...PT_PLOT_CONFIG.trace,
        name: pt.name,
        line: {
            ...PT_PLOT_CONFIG.trace.line,
            color: Config.PRESSURE_TRANSDUCERS[index].color
        }
    }));

    // Determine overall min for Y-axis range from all PTs
    let overallMinY = Infinity;
    let overallMaxCfg = -Infinity;
    Config.PRESSURE_TRANSDUCERS.forEach(pt => {
        if (pt.min_value < overallMinY) overallMinY = pt.min_value;
        if (pt.max_value > overallMaxCfg) overallMaxCfg = pt.max_value;
    });

    // Create layout
    const layout = {
        ...PT_PLOT_CONFIG.layout,
        showlegend: true,
        legend: {
            ...PT_PLOT_CONFIG.legend,
            x: 1,
            xanchor: 'right',
            y: 1,
            orientation: 'v'
        },
        width: rect.width - paddingX,
        height: rect.height - paddingY,
        title: {
            ...PT_PLOT_CONFIG.title,
            text: 'Composite Pressure Readings'
        },
        xaxis: {
            ...PT_PLOT_CONFIG.axis,
            title: {
                ...PT_PLOT_CONFIG.axis.title,
                text: 'Time'
            },
            showgrid: true,
            gridcolor: '#f0f0f0',
            zeroline: true,
            zerolinecolor: '#f0f0f0',
            range: [0, getWindowSize()] // Initialize with window size
        },
        yaxis: {
            ...PT_PLOT_CONFIG.axis,
            title: {
                ...PT_PLOT_CONFIG.axis.title,
                text: 'Pressure (psi)'
            },
            showgrid: true,
            gridcolor: '#f0f0f0',
            zeroline: true,
            zerolinecolor: '#f0f0f0',
            range: [overallMinY, overallMaxCfg], // Initialize; will be updated reactively
            tickvals: generateTickVals(overallMinY, overallMaxCfg),
            ticktext: generateTickVals(overallMinY, overallMaxCfg).map(t => Math.round(t).toString())
        },
        shapes: [] // Will be populated with zone rectangles
    };

    // Initialize the plot
    Plotly.newPlot('pt-agg-plot', traces, layout, {
        responsive: true,
        ...PT_PLOT_CONFIG.hover
    });

    // Update chart size on window resize
    window.addEventListener('resize', () => {
        const newRect = container.getBoundingClientRect();
        const newComputedStyle = window.getComputedStyle(container);
        const newPaddingX = parseFloat(newComputedStyle.paddingLeft) + parseFloat(newComputedStyle.paddingRight);
        const newPaddingY = parseFloat(newComputedStyle.paddingTop) + parseFloat(newComputedStyle.paddingBottom);
        
        Plotly.relayout('pt-agg-plot', {
            width: newRect.width - newPaddingX,
            height: newRect.height - newPaddingY
        });
    });

    const startTime = Date.now();
    let updateChartInterval = null;

    function updateChart() {
        // Skip if in analysis mode (get_data.js handles updates in analysis mode)
        if (window.analysisController && window.analysisController.currentMode === 'analysis') {
            return;
        }
        
        const currentTime = (Date.now() - startTime) / 1000;
        const WINDOW_SIZE = getWindowSize();
        const windowStart = Math.max(0, currentTime - WINDOW_SIZE);
        const windowEnd = currentTime;

        fetch('/data?type=pt')
            .then(response => response.json())
            .then(data => {
                if (data.value && data.value.pt) {
                    // Add new data point
                    sensorData.x.push(currentTime);
                    data.value.pt.forEach((value, i) => {
                        sensorData.y[i].push(value);
                    });

                    // Trim data outside the window
                    while (sensorData.x.length > 0 && sensorData.x[0] < windowStart) {
                        sensorData.x.shift();
                        sensorData.y.forEach(arr => arr.shift());
                    }

                    // Compute dynamic upper bound across all sensors in-window
                    const allVals = sensorData.y.flat().filter(v => Number.isFinite(v));
                    const currentMax = allVals.length ? Math.max(...allVals) : overallMaxCfg;
                    const pad = Math.max(5, currentMax * 0.10); // 10% padding or 5 units
                    const minUpperLimit = overallMaxCfg || 100;  // floor for upper bound
                    const dynUpper = Math.max(minUpperLimit, currentMax + pad);

                    // Update shapes for the moving time window using first PT's thresholds and dynamic upper
                    let newShapes = [];
                    if (Config.PRESSURE_TRANSDUCERS.length > 0) {
                        const firstPTConfig = Config.PRESSURE_TRANSDUCERS[0];
                        newShapes = [
                            // Green Zone
                            { type: 'rect', x0: windowStart, x1: windowEnd, 
                              y0: firstPTConfig.min_value, y1: firstPTConfig.warning_value, 
                              fillcolor: 'rgba(0, 255, 0, 0.2)', line: { width: 0 }, layer: 'below' },
                            // Orange Zone
                            { type: 'rect', x0: windowStart, x1: windowEnd, 
                              y0: firstPTConfig.warning_value, y1: firstPTConfig.danger_value, 
                              fillcolor: 'rgba(255, 165, 0, 0.2)', line: { width: 0 }, layer: 'below' },
                            // Red Zone extended to dynamic upper
                            { type: 'rect', x0: windowStart, x1: windowEnd, 
                              y0: firstPTConfig.danger_value, y1: dynUpper, 
                              fillcolor: 'rgba(255, 0, 0, 0.2)', line: { width: 0 }, layer: 'below' }
                        ];
                    }

                    // Update the plot with new data and ranges
                    // Create update data object with proper structure for each trace
                    const updateData = {
                        x: sensorData.y.map(() => sensorData.x),  // Reference same x array for all traces
                        y: sensorData.y.map(yData => yData)  // Reference each y array directly
                    };
                    
                    Plotly.update('pt-agg-plot', updateData, {
                        shapes: newShapes,
                        'xaxis.range': [windowStart, windowEnd],
                        'yaxis.range': [overallMinY, dynUpper],
                        'yaxis.tickvals': generateTickVals(overallMinY, dynUpper),
                        'yaxis.ticktext': generateTickVals(overallMinY, dynUpper).map(t => Math.round(t).toString())
                    });

                    // Now, call the function in pt_line.js to update subplots with the SAME data
                    if (typeof window.updateAllSubPlots === 'function') {
                        window.updateAllSubPlots(currentTime, data.value.pt);
                    }

                    // Also, call the function in pt_stats.js to update stats with the SAME data
                    if (typeof window.updateAllStats === 'function') {
                        window.updateAllStats(currentTime, data.value.pt);
                    }
                }
            })
            .catch(error => console.error('Error fetching data:', error));
    }

    // Update chart every 100ms (10 Hz) - only in live mode
    updateChartInterval = setInterval(updateChart, 100);

    // Global function to handle external data updates from get_data.js
    window.updatePTPlotsAndStats = function(currentTime, ptDataValues) {
        const isAnalysisMode = window.analysisController && window.analysisController.currentMode === 'analysis';
        
        if (isAnalysisMode) {
            // In analysis mode: all data is already loaded, just update the window
            // Update the x-axis range to show window around current playback position
            const WINDOW_SIZE = getWindowSize();
            const windowStart = Math.max(0, currentTime - WINDOW_SIZE);
            const windowEnd = currentTime;
            
            Plotly.relayout('pt-agg-plot', {
                'xaxis.range': [windowStart, windowEnd]
            });
            
            // Update stats with current data point
            if (typeof window.updateAllStats === 'function') {
                window.updateAllStats(currentTime, ptDataValues);
            }
        } else {
            // Live mode: original behavior - accumulate data continuously
            sensorData.x.push(currentTime);
            
            // Limit to window size
            const WINDOW_SIZE = getWindowSize();
            const windowStart = Math.max(0, currentTime - WINDOW_SIZE);
            
            // Filter data to window
            let startIndex = 0;
            while (startIndex < sensorData.x.length && sensorData.x[startIndex] < windowStart) {
                startIndex++;
            }
            
            if (startIndex > 0) {
                sensorData.x = sensorData.x.slice(startIndex);
                sensorData.y = sensorData.y.map(yData => yData.slice(startIndex));
            }
            
            // Add new PT values
            ptDataValues.forEach((value, i) => {
                if (i < sensorData.y.length) {
                    sensorData.y[i].push(value);
                }
            });
            
            // Update the plot
            const updateData = {
                x: sensorData.y.map(() => sensorData.x),
                y: sensorData.y.map(yData => yData)
            };
            
            Plotly.update('pt-agg-plot', updateData, {
                'xaxis.range': [windowStart, currentTime]
            });
        }
        
        // Update subplots and stats
        if (typeof window.updateAllSubPlots === 'function') {
            window.updateAllSubPlots(currentTime, ptDataValues);
        }
        if (typeof window.updateAllStats === 'function') {
            window.updateAllStats(currentTime, ptDataValues);
        }
    };
});

function generateTickVals(axisMin, axisMax) {
    const ticks = [axisMin, axisMax];
    let current = Math.ceil(axisMin / 100) * 100;
    while (current < axisMax) {
        if (current > axisMin) {
            ticks.push(current);
        }
        current += 100;
    }
    // Filter out ticks outside the explicit range, then sort.
    // Ensure axisMin and axisMax are part of the ticks if they are not multiples of 100
    // and fall within the generated tick sequence before being potentially filtered out.
    // The initial push of axisMin and axisMax handles this.
    return Array.from(new Set(ticks)).filter(tick => tick >= axisMin && tick <= axisMax).sort((a, b) => a - b);
}
