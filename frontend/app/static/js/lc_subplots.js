document.addEventListener('DOMContentLoaded', function() {
    // Default window size, can be overridden by global window.plotWindowSize
    const DEFAULT_WINDOW_SIZE = 30; // Size of the time window in seconds
    
    // Get window size from global variable or use default
    function getWindowSize() {
        return window.plotWindowSize || DEFAULT_WINDOW_SIZE;
    }

    const lcSensorData = {
        x: [],
        y: Array(Config.NUM_LOAD_CELLS).fill().map(() => [])
    };
    
    // Function to clear plot data (called when switching to analysis mode)
    window.clearLCSubplotData = function() {
        lcSensorData.x = [];
        lcSensorData.y = Array(Config.NUM_LOAD_CELLS).fill().map(() => []);
    };
    
    // Function to load all analysis data at once
    window.loadAllLCSubplotAnalysisData = function(allDataEntries) {
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
        
        // Update plot with all data
        const updateData = {
            x: lcSensorData.y.map(() => lcSensorData.x),
            y: lcSensorData.y
        };
        
        Plotly.update('lc-subplots-plot', updateData, {});
    };
    
    // Function to update plot window based on playback position
    window.updateLCSubplotWindow = function(currentPosition) {
        const WINDOW_SIZE = getWindowSize();
        const windowStart = Math.max(0, currentPosition - WINDOW_SIZE);
        const windowEnd = currentPosition;
        
        const xaxisUpdates = {};
        for (let i = 0; i < Config.NUM_LOAD_CELLS; i++) {
            const axisKey = i === 0 ? 'xaxis.range' : `xaxis${i + 1}.range`;
            xaxisUpdates[axisKey] = [windowStart, windowEnd];
        }
        
        Plotly.relayout('lc-subplots-plot', xaxisUpdates);
    };

    const container = document.getElementById('lc-subplots-container');
    if (!container) { console.error('LC Subplots container not found'); return; }
    const plotDiv = document.getElementById('lc-subplots-plot');
    if (!plotDiv) { console.error('LC Subplots plot div not found'); return; }

    const traces = [];
    for (let i = 0; i < Config.NUM_LOAD_CELLS; i++) {
        traces.push({
            x: [], y: [],
            ...PT_PLOT_CONFIG.trace,
            name: Config.LOAD_CELLS[i].name,
            xaxis: (i === 0 ? 'x' : `x${i + 1}`),
            yaxis: (i === 0 ? 'y' : `y${i + 1}`),
            line: { ...PT_PLOT_CONFIG.trace.line, color: Config.LOAD_CELLS[i].color }
        });
    }

    const layout = {
        ...PT_PLOT_CONFIG.layout,
        grid: { rows: Config.NUM_LOAD_CELLS, columns: 1, pattern: 'independent', rowgap: 0.10 },
        showlegend: false,
        title: { ...PT_PLOT_CONFIG.title, text: 'Load Cell Readings' }
    };

    for (let i = 0; i < Config.NUM_LOAD_CELLS; i++) {
        const lcConfig = Config.LOAD_CELLS[i];
        const xAxisNameKey = i === 0 ? 'xaxis' : `xaxis${i + 1}`;
        layout[xAxisNameKey] = { ...PT_PLOT_CONFIG.axis, title:{...PT_PLOT_CONFIG.axis.title, text:i===Config.NUM_LOAD_CELLS-1?'Time':''}, range:[0, getWindowSize()] };
        const yAxisNameKey = i === 0 ? 'yaxis' : `yaxis${i + 1}`;
        layout[yAxisNameKey] = {
            ...PT_PLOT_CONFIG.axis,
            title: { text: lcConfig.name, font: { color: lcConfig.color } },
            showline: true, linecolor: lcConfig.color, linewidth: 2,
            range: [lcConfig.min_value, lcConfig.max_value]
        };
    }
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

    window.updateAllLCSubPlots = function(currentTimeFromAgg, lcDataFromAgg) {
        const isAnalysisMode = window.analysisController && window.analysisController.currentMode === 'analysis';
        const windowStart = Math.max(0, currentTimeFromAgg - WINDOW_SIZE);
        const windowEnd = currentTimeFromAgg;

        if (lcDataFromAgg) {
            if (isAnalysisMode) {
                // In analysis mode: all data is already loaded, just update the window
                // Update the x-axis range to show window around current playback position
                const xaxisUpdates = {};
                for (let i = 0; i < Config.NUM_LOAD_CELLS; i++) {
                    const axisKey = i === 0 ? 'xaxis.range' : `xaxis${i + 1}.range`;
                    xaxisUpdates[axisKey] = [windowStart, windowEnd];
                }
                Plotly.relayout('lc-subplots-plot', xaxisUpdates);
            } else {
                // Live mode: original behavior
                lcSensorData.x.push(currentTimeFromAgg);
                lcDataFromAgg.forEach((value, i) => { lcSensorData.y[i].push(value); });

                while (lcSensorData.x.length > 0 && lcSensorData.x[0] < windowStart) {
                    lcSensorData.x.shift();
                    lcSensorData.y.forEach(arr => arr.shift());
                }
            }

            // let newShapes = [];
            // if (Config.LOAD_CELL_BOUNDARIES) {
            //     for (let i = 0; i < Config.NUM_LOAD_CELLS; i++) {
            //         const xAxisRef = i === 0 ? 'x' : `x${i + 1}`;
            //         const yAxisRef = i === 0 ? 'y' : `y${i + 1}`;
            //         newShapes.push({ type:'rect', xref:xAxisRef, yref:yAxisRef, x0:windowStart, x1:windowEnd, y0:Config.LOAD_CELL_BOUNDARIES.safe[0], y1:Config.LOAD_CELL_BOUNDARIES.safe[1], fillcolor:'rgba(0,255,0,0.2)', line:{width:0}, layer:'below' });
            //         newShapes.push({ type:'rect', xref:xAxisRef, yref:yAxisRef, x0:windowStart, x1:windowEnd, y0:Config.LOAD_CELL_BOUNDARIES.warning[0], y1:Config.LOAD_CELL_BOUNDARIES.warning[1], fillcolor:'rgba(255,165,0,0.2)', line:{width:0}, layer:'below' });
            //         newShapes.push({ type:'rect', xref:xAxisRef, yref:yAxisRef, x0:windowStart, x1:windowEnd, y0:Config.LOAD_CELL_BOUNDARIES.danger[0], y1:Config.LOAD_CELL_BOUNDARIES.danger[1], fillcolor:'rgba(255,0,0,0.2)', line:{width:0}, layer:'below' });
            //     }
            // }

            const xaxisUpdates = {};
            for (let i = 0; i < Config.NUM_LOAD_CELLS; i++) {
                xaxisUpdates[i===0?'xaxis.range':`xaxis${i+1}.range`] = [windowStart, windowEnd];
            }
            
            // Create update data object with proper structure for each trace
            const updateData = {
                x: lcSensorData.y.map(() => lcSensorData.x),  // Reference same x array for all traces
                y: lcSensorData.y.map(yData => yData)  // Reference each y array directly
            };
            
            Plotly.update(plotDiv, updateData, { 
                // shapes: newShapes, 
                ...xaxisUpdates 
            });
        }
    };
    // Corrected generateTickVals function for LC plots
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
    // Update yaxes with tickvals
    for (let i = 0; i < Config.NUM_LOAD_CELLS; i++) {
        const yAxisNameKey = i === 0 ? 'yaxis' : `yaxis${i + 1}`;
        const lcConfig = Config.LOAD_CELLS[i];
        layout[yAxisNameKey].tickvals = generateTickVals(lcConfig.min_value, lcConfig.max_value);
        layout[yAxisNameKey].ticktext = layout[yAxisNameKey].tickvals.map(t => Math.round(t).toString());
    }
    Plotly.relayout(plotDiv, layout); // Apply new tick PgetNextToken
}); 