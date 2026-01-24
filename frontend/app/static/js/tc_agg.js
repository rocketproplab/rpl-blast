document.addEventListener('DOMContentLoaded', function() {
    // Default window size, can be overridden by global window.plotWindowSize
    const DEFAULT_WINDOW_SIZE = 30; // Size of the time window in seconds
    
    // Get window size from global variable or use default
    function getWindowSize() {
        return window.plotWindowSize || DEFAULT_WINDOW_SIZE;
    }
    const UPDATE_INTERVAL = 100; // ms, for fetching data (consistent with PT plots)

    const tcSensorData = {
        x: [],
        y: Array(Config.NUM_THERMOCOUPLES).fill().map(() => [])
    };
    let totalDataDuration = 0; // Store total duration of loaded data
    
    // Function to clear plot data (called when switching to analysis mode)
    window.clearTCPlotData = function() {
        tcSensorData.x = [];
        tcSensorData.y = Array(Config.NUM_THERMOCOUPLES).fill().map(() => []);
    };
    
    // Function to load all analysis data at once
    window.loadAllTCAnalysisData = function(allDataEntries) {
        // Clear existing data
        tcSensorData.x = [];
        tcSensorData.y = Array(Config.NUM_THERMOCOUPLES).fill().map(() => []);
        
        // Load all data points
        allDataEntries.forEach(entry => {
            const t = entry.t_seconds || 0;
            const adjusted = entry.adjusted || {};
            const tcValues = adjusted.tc || [];
            
            tcSensorData.x.push(t);
            tcValues.forEach((value, i) => {
                if (i < tcSensorData.y.length) {
                    tcSensorData.y[i].push(value);
                }
            });
        });
        
        // Store total duration
        if (tcSensorData.x.length > 0) {
            totalDataDuration = tcSensorData.x[tcSensorData.x.length - 1];
        }
        
        // Update plot with all data
        const updateData = {
            x: tcSensorData.y.map(() => tcSensorData.x),
            y: tcSensorData.y
        };
        
        // Note: Color bars for TC would go here if TEMPERATURE_BOUNDARIES is configured
        Plotly.update('tc-agg-plot', updateData, {});
    };
    
    // Function to update plot window based on playback position
    window.updateTCPlotWindow = function(currentPosition) {
        const WINDOW_SIZE = getWindowSize();
        const windowStart = Math.max(0, currentPosition - WINDOW_SIZE);
        const windowEnd = currentPosition;
        
        Plotly.relayout('tc-agg-plot', {
            'xaxis.range': [windowStart, windowEnd]
        });
    };

    const container = document.getElementById('tc-agg-container'); // Container for this plot
    if (!container) {
        console.error('TC Aggregate plot container not found');
        return;
    }
    const plotDiv = document.getElementById('tc-agg-plot');
    if (!plotDiv) {
        console.error('TC Aggregate plot div not found');
        return;
    }

    // Create traces for each thermocouple
    const traces = Config.THERMOCOUPLES.map((tc, index) => {
        return {
            x: [],
            y: [],
            ...PT_PLOT_CONFIG.trace, // Using PT_PLOT_CONFIG for styling consistency
            name: tc.name,
            line: { ...PT_PLOT_CONFIG.trace.line, color: tc.color } // Assuming TCs have a color in config
            // If TCs don't have a color in config, Plotly will assign default colors.
            // Let's check config for TC colors. If not present, we remove the line or use defaults.
        };
    });

    // Determine overall min and max for Y-axis range from all TCs
    let overallMinY = Infinity;
    let overallMaxY = -Infinity;
    Config.THERMOCOUPLES.forEach(tc => {
        if (tc.min_value < overallMinY) overallMinY = tc.min_value;
        if (tc.max_value > overallMaxY) overallMaxY = tc.max_value;
    });

    const layout = {
        ...PT_PLOT_CONFIG.layout,
        title: {
            ...PT_PLOT_CONFIG.title,
            text: 'Composite Thermocouple Readings'
        },
        xaxis: {
            ...PT_PLOT_CONFIG.axis,
            title: { ...PT_PLOT_CONFIG.axis.title, text: 'Time' },
            range: [0, getWindowSize()]
        },
        yaxis: {
            ...PT_PLOT_CONFIG.axis,
            title: { ...PT_PLOT_CONFIG.axis.title, text: 'Temperature (°C)' },
            range: [overallMinY, overallMaxY], // Set Y-axis range
            tickvals: generateTickVals(overallMinY, overallMaxY),
            ticktext: generateTickVals(overallMinY, overallMaxY).map(t => Math.round(t).toString())
        },
        showlegend: true,
        legend: {
            ...PT_PLOT_CONFIG.legend,
            x: 1, xanchor: 'right', y: 1, orientation: 'v'
        }
        // height and width will be set by responsive relayout
    };

    Plotly.newPlot(plotDiv, traces, layout, { 
        responsive: true, 
        ...PT_PLOT_CONFIG.hover 
    });

    function updateChartDimensions() {
        const rect = container.getBoundingClientRect();
        const computedStyle = window.getComputedStyle(container);
        const paddingX = parseFloat(computedStyle.paddingLeft) + parseFloat(computedStyle.paddingRight);
        const paddingY = parseFloat(computedStyle.paddingTop) + parseFloat(computedStyle.paddingBottom);
        Plotly.relayout(plotDiv, {
            width: rect.width - paddingX,
            height: rect.height - paddingY
        });
    }
    updateChartDimensions(); // Initial call
    window.addEventListener('resize', updateChartDimensions);

    // const startTime = Date.now(); // Removed, currentTime is passed by get_data.js

    // This function will be called by get_data.js
    window.updateTCPlotsAndStats = function(currentTime, tcDataValues) { // Renamed and params changed
        const isAnalysisMode = window.analysisController && window.analysisController.currentMode === 'analysis';
        const windowStart = Math.max(0, currentTime - WINDOW_SIZE);
        const windowEnd = currentTime;

        if (tcDataValues) {
            const newTCValues = tcDataValues;

            if (isAnalysisMode) {
                // In analysis mode: all data is already loaded, just update the window
                // Update the x-axis range to show window around current playback position
                Plotly.relayout('tc-agg-plot', {
                    'xaxis.range': [windowStart, windowEnd]
                });
                
                // Update stats with current data point
                if (typeof window.updateAllTCStats === 'function') {
                    window.updateAllTCStats(currentTime, newTCValues);
                }
            } else {
                // Live mode: original behavior
                tcSensorData.x.push(currentTime);
                newTCValues.forEach((value, i) => {
                    tcSensorData.y[i].push(value);
                });

                // Trim data outside the window
                while (tcSensorData.x.length > 0 && tcSensorData.x[0] < windowStart) {
                    tcSensorData.x.shift();
                    tcSensorData.y.forEach(arr => arr.shift());
                }
            }

            // let newShapes = [];
            // if (Config.TEMPERATURE_BOUNDARIES) {
            //     // Green Zone (Safe)
            //     newShapes.push({
            //         type: 'rect', xref: 'x', yref: 'y',
            //         x0: windowStart, x1: windowEnd, 
            //         y0: Config.TEMPERATURE_BOUNDARIES.safe[0], y1: Config.TEMPERATURE_BOUNDARIES.safe[1], 
            //         fillcolor: 'rgba(0, 255, 0, 0.2)', line: { width: 0 }, layer: 'below'
            //     });
            //     // Orange Zone (Warning)
            //     newShapes.push({
            //         type: 'rect', xref: 'x', yref: 'y',
            //         x0: windowStart, x1: windowEnd, 
            //         y0: Config.TEMPERATURE_BOUNDARIES.warning[0], y1: Config.TEMPERATURE_BOUNDARIES.warning[1], 
            //         fillcolor: 'rgba(255, 165, 0, 0.2)', line: { width: 0 }, layer: 'below'
            //     });
            //     // Red Zone (Danger)
            //     newShapes.push({
            //         type: 'rect', xref: 'x', yref: 'y',
            //         x0: windowStart, x1: windowEnd, 
            //         y0: Config.TEMPERATURE_BOUNDARIES.danger[0], y1: Config.TEMPERATURE_BOUNDARIES.danger[1], 
            //         fillcolor: 'rgba(255, 0, 0, 0.2)', line: { width: 0 }, layer: 'below'
            //     });
            // }

            // Create update data object with proper structure for each trace
            const updateData = {
                x: tcSensorData.y.map(() => tcSensorData.x),  // Reference same x array for all traces
                y: tcSensorData.y.map(yData => yData)  // Reference each y array directly
            };
            
            Plotly.update(plotDiv, updateData, {
                'xaxis.range': [windowStart, windowEnd],
                // shapes: newShapes
            });

            // Call update for subplots (if the function exists)
            if (typeof window.updateAllTCSubPlots === 'function') {
                window.updateAllTCSubPlots(currentTime, newTCValues);
            }

            // Call update for stats (if the function exists)
            if (typeof window.updateAllTCStats === 'function') {
                window.updateAllTCStats(currentTime, newTCValues);
            }
        }
        // }) // Removed
        // .catch(error => console.error('Error fetching TC data for aggregate plot:', error)); // Removed
    };

    // setInterval(fetchDataAndUpdateCharts, UPDATE_INTERVAL); // Removed
});

function generateTickVals(axisMin, axisMax) {
    const ticks = [axisMin, axisMax];
    let current = Math.ceil(axisMin / 200) * 200;
    while (current < axisMax) {
        if (current > axisMin) {
            ticks.push(current);
        }
        current += 200;
    }
    return Array.from(new Set(ticks)).filter(tick => tick >= axisMin && tick <= axisMax).sort((a, b) => a - b);
} 