document.addEventListener('DOMContentLoaded', function() {
    // Default window size, can be overridden by global window.plotWindowSize
    const DEFAULT_WINDOW_SIZE = 30; // Size of the time window in seconds
    
    // Get window size from global variable or use default
    function getWindowSize() {
        return window.plotWindowSize || DEFAULT_WINDOW_SIZE;
    }
    const UPDATE_INTERVAL = 100; // ms

    const lcSensorData = {
        x: [],
        y: Array(Config.NUM_LOAD_CELLS).fill().map(() => [])
    };
    let totalDataDuration = 0; // Store total duration of loaded data
    
    // Function to clear plot data (called when switching to analysis mode)
    window.clearLCPlotData = function() {
        lcSensorData.x = [];
        lcSensorData.y = Array(Config.NUM_LOAD_CELLS).fill().map(() => []);
    };
    
    // Function to load all analysis data at once
    window.loadAllLCAnalysisData = function(allDataEntries) {
        // Clear existing data
        lcSensorData.x = [];
        lcSensorData.y = Array(Config.NUM_LOAD_CELLS).fill().map(() => []);
        
        // Load all data points
        allDataEntries.forEach(entry => {
            const t = entry.t_seconds || 0;
            const adjusted = entry.adjusted || {};
            const lcValues = adjusted.lc || [];
            
            lcSensorData.x.push(t);
            lcValues.forEach((value, i) => {
                if (i < lcSensorData.y.length) {
                    lcSensorData.y[i].push(value);
                }
            });
        });
        
        // Store total duration
        if (lcSensorData.x.length > 0) {
            totalDataDuration = lcSensorData.x[lcSensorData.x.length - 1];
        }
        
        // Update plot with all data
        const updateData = {
            x: lcSensorData.y.map(() => lcSensorData.x),
            y: lcSensorData.y
        };
        
        // Note: Color bars for LC would go here if LOAD_CELL_BOUNDARIES is configured
        Plotly.update('lc-agg-plot', updateData, {});
    };
    
    // Function to update plot window based on playback position
    window.updateLCPlotWindow = function(currentPosition) {
        const WINDOW_SIZE = getWindowSize();
        const windowStart = Math.max(0, currentPosition - WINDOW_SIZE);
        const windowEnd = currentPosition;
        
        Plotly.relayout('lc-agg-plot', {
            'xaxis.range': [windowStart, windowEnd]
        });
    };

    const container = document.getElementById('lc-agg-container');
    if (!container) { console.error('LC Aggregate plot container not found'); return; }
    const plotDiv = document.getElementById('lc-agg-plot');
    if (!plotDiv) { console.error('LC Aggregate plot div not found'); return; }

    const traces = Config.LOAD_CELLS.map((lc, index) => ({
        x: [], y: [],
        ...PT_PLOT_CONFIG.trace,
        name: lc.name,
        line: { ...PT_PLOT_CONFIG.trace.line, color: lc.color }
    }));

    let overallMinY = Infinity, overallMaxY = -Infinity;
    Config.LOAD_CELLS.forEach(lc => {
        if (lc.min_value < overallMinY) overallMinY = lc.min_value;
        if (lc.max_value > overallMaxY) overallMaxY = lc.max_value;
    });
    // No padding for agg plot range, as per user preference from PT/TC plots

    const layout = {
        ...PT_PLOT_CONFIG.layout,
        title: { ...PT_PLOT_CONFIG.title, text: 'Composite Load Cell Readings' },
        xaxis: { ...PT_PLOT_CONFIG.axis, title: { ...PT_PLOT_CONFIG.axis.title, text: 'Time' }, range: [0, getWindowSize()] },
        yaxis: { ...PT_PLOT_CONFIG.axis, title: { ...PT_PLOT_CONFIG.axis.title, text: 'Load (Units)' }, range: [overallMinY, overallMaxY] },
        showlegend: true,
        legend: { ...PT_PLOT_CONFIG.legend, x: 1, xanchor: 'right', y: 1, orientation: 'v' }
    };
    Plotly.newPlot(plotDiv, traces, layout, { responsive: true, ...PT_PLOT_CONFIG.hover });

    function updateChartDimensions() {
        const rect = container.getBoundingClientRect();
        const cs = window.getComputedStyle(container);
        const padX = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight);
        const padY = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom);
        Plotly.relayout(plotDiv, { width: rect.width - padX, height: rect.height - padY });
    }
    updateChartDimensions();
    window.addEventListener('resize', updateChartDimensions);

    // const startTime = Date.now(); // Removed, currentTime is passed by get_data.js

    // This function will be called by get_data.js
    window.updateLCPlotsAndStats = function(currentTime, lcDataValues) { // Renamed and params changed
        const isAnalysisMode = window.analysisController && window.analysisController.currentMode === 'analysis';
        const windowStart = Math.max(0, currentTime - WINDOW_SIZE);
        const windowEnd = currentTime;

        if (lcDataValues) {
            const newLCValues = lcDataValues;

            if (isAnalysisMode) {
                // In analysis mode: all data is already loaded, just update the window
                // Update the x-axis range to show window around current playback position
                Plotly.relayout('lc-agg-plot', {
                    'xaxis.range': [windowStart, windowEnd]
                });
                
                // Update stats with current data point
                if (typeof window.updateAllLCStats === 'function') {
                    window.updateAllLCStats(currentTime, newLCValues);
                }
            } else {
                // Live mode: original behavior
                lcSensorData.x.push(currentTime);
                newLCValues.forEach((value, i) => { lcSensorData.y[i].push(value); });

                while (lcSensorData.x.length > 0 && lcSensorData.x[0] < windowStart) {
                    lcSensorData.x.shift();
                    lcSensorData.y.forEach(arr => arr.shift());
                }
            }

            // let newShapes = [];
            // if (Config.LOAD_CELL_BOUNDARIES) {
            //     newShapes.push({ type: 'rect', xref:'x', yref:'y', x0:windowStart, x1:windowEnd, y0:Config.LOAD_CELL_BOUNDARIES.safe[0], y1:Config.LOAD_CELL_BOUNDARIES.safe[1], fillcolor:'rgba(0,255,0,0.2)', line:{width:0}, layer:'below' });
            //     newShapes.push({ type: 'rect', xref:'x', yref:'y', x0:windowStart, x1:windowEnd, y0:Config.LOAD_CELL_BOUNDARIES.warning[0], y1:Config.LOAD_CELL_BOUNDARIES.warning[1], fillcolor:'rgba(255,165,0,0.2)', line:{width:0}, layer:'below' });
            //     newShapes.push({ type: 'rect', xref:'x', yref:'y', x0:windowStart, x1:windowEnd, y0:Config.LOAD_CELL_BOUNDARIES.danger[0], y1:Config.LOAD_CELL_BOUNDARIES.danger[1], fillcolor:'rgba(255,0,0,0.2)', line:{width:0}, layer:'below' });
            // }

            // Create update data object with proper structure for each trace
            const updateData = {
                x: lcSensorData.y.map(() => lcSensorData.x),  // Reference same x array for all traces
                y: lcSensorData.y.map(yData => yData)  // Reference each y array directly
            };
            
            Plotly.update(plotDiv, updateData, { 
                'xaxis.range': [windowStart, windowEnd], 
                // shapes: newShapes 
            });

            if (typeof window.updateAllLCSubPlots === 'function') { window.updateAllLCSubPlots(currentTime, newLCValues); }
            if (typeof window.updateAllLCStats === 'function') { window.updateAllLCStats(currentTime, newLCValues); }
        }
        // })
        // .catch(error => console.error('Error fetching LC data for aggregate plot:', error)); // Removed
    };

    // Corrected generateTickVals function for LC plots (e.g. every 100 or 50 units based on range)
    function generateTickVals(axisMin, axisMax) {
        const ticks = [axisMin, axisMax];
        const interval = (axisMax - axisMin) > 500 ? 100 : 50; // Example dynamic interval
        let current = Math.ceil(axisMin / interval) * interval;
        while (current < axisMax) {
            if (current > axisMin) ticks.push(current);
            current += interval;
        }
        return Array.from(new Set(ticks)).filter(tick => tick >= axisMin && tick <= axisMax).sort((a, b) => a - b);
    }
    // Update yaxis with tickvals
    layout.yaxis.tickvals = generateTickVals(overallMinY, overallMaxY);
    layout.yaxis.ticktext = layout.yaxis.tickvals.map(t => Math.round(t).toString());
    Plotly.relayout(plotDiv, layout); // Apply new tick PgetNextToken

    // setInterval(fetchDataAndUpdateCharts, UPDATE_INTERVAL); // Removed
}); 