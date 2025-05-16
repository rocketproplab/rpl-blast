document.addEventListener('DOMContentLoaded', function() {
    const WINDOW_SIZE = 10; // Size of the time window in seconds
    const sensorData = {
        x: [],
        y: Array(Config.NUM_PRESSURE_TRANSDUCERS).fill().map(() => [])
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

    // Determine overall min and max for Y-axis range from all PTs
    let overallMinY = Infinity;
    let overallMaxY = -Infinity;
    Config.PRESSURE_TRANSDUCERS.forEach(pt => {
        if (pt.min_value < overallMinY) overallMinY = pt.min_value;
        if (pt.max_value > overallMaxY) overallMaxY = pt.max_value;
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
            range: [0, WINDOW_SIZE] // Initialize with window size
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
            range: [overallMinY, overallMaxY], // Explicitly set Y-axis range here
            tickvals: generateTickVals(overallMinY, overallMaxY),
            ticktext: generateTickVals(overallMinY, overallMaxY).map(String)
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

    function updateChart() {
        const currentTime = (Date.now() - startTime) / 1000;
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

                    // Update shapes for the moving time window using the first PT's config for zones
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
                            // Red Zone
                            { type: 'rect', x0: windowStart, x1: windowEnd, 
                              y0: firstPTConfig.danger_value, y1: firstPTConfig.max_value, 
                              fillcolor: 'rgba(255, 0, 0, 0.2)', line: { width: 0 }, layer: 'below' }
                    ];
                    }

                    // Update the plot with new data and ranges
                    Plotly.update('pt-agg-plot', {
                        x: Array(Config.NUM_PRESSURE_TRANSDUCERS).fill().map(() => [...sensorData.x]),
                        y: sensorData.y
                    }, {
                        shapes: newShapes,
                        'xaxis.range': [windowStart, windowEnd]
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

    // Update chart every 100ms (10 Hz)
    setInterval(updateChart, 100);
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
