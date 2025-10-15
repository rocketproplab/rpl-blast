document.addEventListener('DOMContentLoaded', function() {
    const WINDOW_SIZE = 10; // Size of the time window in seconds
    const ROLLING_AVG_WINDOW_SIZE = 3; // Size of the rolling average window in seconds
    // Dynamic Y upper bound behavior
    const YPAD_RATIO = 0.10;        // 10% of current max
    const YPAD_MIN_ABS = 5;         // At least 5 units padding
    const sensorData = {
        x: [],
        y: Array(Config.NUM_PRESSURE_TRANSDUCERS).fill().map(() => []),
        y_avg: Array(Config.NUM_PRESSURE_TRANSDUCERS).fill().map(() => []), // For rolling average
        history: Array(Config.NUM_PRESSURE_TRANSDUCERS).fill().map(() => []) // For calculating rolling average
    };
    // const gn2Index = Config.PRESSURE_TRANSDUCERS.findIndex(pt => pt.name === 'GN2'); // For logging (commented out)

    // Get container dimensions
    const container = document.getElementById('pt-subplots');
    const rect = container.getBoundingClientRect();
    const computedStyle = window.getComputedStyle(container);
    const paddingX = parseFloat(computedStyle.paddingLeft) + parseFloat(computedStyle.paddingRight);
    const paddingY = parseFloat(computedStyle.paddingTop) + parseFloat(computedStyle.paddingBottom);

    // Create subplot traces (sensor data traces and rolling average traces)
    const traces = [];
    for (let i = 0; i < Config.NUM_PRESSURE_TRANSDUCERS; i++) {
        // Sensor data trace
        traces.push({
            x: [],
            y: [],
            ...PT_PLOT_CONFIG.trace,
            name: Config.PRESSURE_TRANSDUCERS[i].name,
            xaxis: (i === 0 ? 'x' : `x${i + 1}`),
            yaxis: (i === 0 ? 'y' : `y${i + 1}`),
            line: {
                ...PT_PLOT_CONFIG.trace.line,
                color: Config.PRESSURE_TRANSDUCERS[i].color
            }
        });
        // Rolling average trace
        traces.push({
            x: [],
            y: [],
            ...PT_PLOT_CONFIG.trace,
            name: `${Config.PRESSURE_TRANSDUCERS[i].name} Avg`,
            xaxis: (i === 0 ? 'x' : `x${i + 1}`),
            yaxis: (i === 0 ? 'y' : `y${i + 1}`),
            line: {
                ...PT_PLOT_CONFIG.trace.line,
                color: Config.PRESSURE_TRANSDUCERS[i].color, // Use same color but make it dashed or thinner
                dash: 'dash',
                width: (PT_PLOT_CONFIG.trace.line.width || 2) * 0.8 // Slightly thinner
            },
            visible: true // Initially hidden, can be toggled via legend
        });
    }

    // Compute dynamic row gap based on number of subplots (tighter when many)
    const ROWGAP = (function(n){
        // Slightly larger gaps to improve readability on small subplots
        if (n >= 6) return 0.06;
        if (n >= 4) return 0.08;
        return 0.12;
    })(Config.NUM_PRESSURE_TRANSDUCERS);

    // Create subplot layout with shapes for zones
    const layout = {
        ...PT_PLOT_CONFIG.layout,
        grid: {
            rows: Config.NUM_PRESSURE_TRANSDUCERS,
            columns: 1,
            pattern: 'independent',
            rowgap: ROWGAP
        },
        shapes: [], // Will be populated with zone rectangles
        showlegend: false,
        width: rect.width - paddingX,
        height: rect.height - paddingY,
        title: {
            ...PT_PLOT_CONFIG.title,
            text: 'Pressure Transducer Readings'
        }
    };

    // Add axis configurations for each subplot
    for (let i = 0; i < Config.NUM_PRESSURE_TRANSDUCERS; i++) {
        const xAxisNameKey = i === 0 ? 'xaxis' : `xaxis${i + 1}`;
        layout[xAxisNameKey] = {
            ...PT_PLOT_CONFIG.axis,
            title: {
                ...PT_PLOT_CONFIG.axis.title,
                text: i === Config.NUM_PRESSURE_TRANSDUCERS - 1 ? 'Time' : ''
            },
            range: [0, WINDOW_SIZE]
        };
        const yAxisNameKey = i === 0 ? 'yaxis' : `yaxis${i + 1}`; 
        layout[yAxisNameKey] = {
            ...PT_PLOT_CONFIG.axis,
            title: {
                text: Config.PRESSURE_TRANSDUCERS[i].name,
                font: {
                    color: Config.PRESSURE_TRANSDUCERS[i].color
                }
            },
            showline: true, // Show y-axis line
            linecolor: Config.PRESSURE_TRANSDUCERS[i].color, // Color y-axis line
            linewidth: 2,      // Set y-axis line width
            range: [Config.PRESSURE_TRANSDUCERS[i].min_value, Config.PRESSURE_TRANSDUCERS[i].max_value], // Initial Y-axis range
            tickvals: generateNiceTicks(Config.PRESSURE_TRANSDUCERS[i].min_value, Config.PRESSURE_TRANSDUCERS[i].max_value, 15),
            ticktext: generateNiceTicks(Config.PRESSURE_TRANSDUCERS[i].min_value, Config.PRESSURE_TRANSDUCERS[i].max_value, 15).map(String)
        };
    }

    // Initialize the plot
    Plotly.newPlot('pt-subplots', traces, layout, {
        responsive: true,
        ...PT_PLOT_CONFIG.hover
    });

    // Update chart size on window resize
    window.addEventListener('resize', () => {
        const newRect = container.getBoundingClientRect();
        const newComputedStyle = window.getComputedStyle(container);
        const newPaddingX = parseFloat(newComputedStyle.paddingLeft) + parseFloat(newComputedStyle.paddingRight);
        const newPaddingY = parseFloat(newComputedStyle.paddingTop) + parseFloat(newComputedStyle.paddingBottom);
        
        Plotly.relayout('pt-subplots', {
            width: newRect.width - newPaddingX,
            height: newRect.height - newPaddingY
        });
    });

    // This function will be called by pt_agg.js
    window.updateAllSubPlots = function(currentTimeFromAgg, ptDataFromAgg) {
        const windowStart = Math.max(0, currentTimeFromAgg - WINDOW_SIZE);
        const windowEnd = currentTimeFromAgg;

        if (ptDataFromAgg) {
            // if (gn2Index !== -1 && ptDataFromAgg.length > gn2Index) { // For logging (commented out)
            //     const gn2Value = ptDataFromAgg[gn2Index];
            //     // console.log(`SUB_PLOT (from AGG) GN2 - Time: ${currentTimeFromAgg.toFixed(3)}, Value: ${gn2Value !== undefined ? gn2Value.toFixed(3) : 'N/A'}`);
            // }

            sensorData.x.push(currentTimeFromAgg);
            ptDataFromAgg.forEach((value, i) => {
                sensorData.y[i].push(value);

                // Update history for rolling average
                sensorData.history[i].push({ time: currentTimeFromAgg, value: value });
                // Trim history to ROLLING_AVG_WINDOW_SIZE
                while (sensorData.history[i].length > 0 && sensorData.history[i][0].time < currentTimeFromAgg - ROLLING_AVG_WINDOW_SIZE) {
                    sensorData.history[i].shift();
                }

                // Calculate rolling average
                if (sensorData.history[i].length > 0) {
                    const sum = sensorData.history[i].reduce((acc, point) => acc + point.value, 0);
                    sensorData.y_avg[i].push(sum / sensorData.history[i].length);
                } else {
                    sensorData.y_avg[i].push(null); // Or undefined, or the value itself if no history
                }
            });

            while (sensorData.x.length > 0 && sensorData.x[0] < windowStart) {
                sensorData.x.shift();
                sensorData.y.forEach(arr => arr.shift());
                sensorData.y_avg.forEach(arr => arr.shift()); // Also shift rolling average data
            }

            const newShapes = [];

            const xaxisUpdates = {};
            const yaxisUpdates = {};
            const yTicksUpdates = {};
            const dynUpperByIndex = {};
            for (let i = 0; i < Config.NUM_PRESSURE_TRANSDUCERS; i++) {
                const axisKey = i === 0 ? 'xaxis.range' : `xaxis${i + 1}.range`;
                xaxisUpdates[axisKey] = [windowStart, windowEnd];

                // Compute dynamic Y upper bound per subplot
                const ptCfg = Config.PRESSURE_TRANSDUCERS[i];
                const minY = ptCfg.min_value;
                // Lower limit (floor) for the upper bound to avoid excessive shrinking
                const minUpperLimit = (typeof ptCfg.min_upper_limit === 'number') ? ptCfg.min_upper_limit : (ptCfg.max_value ?? 100);
                // Find current window max for this sensor
                const arr = sensorData.y[i].filter(v => Number.isFinite(v));
                const currentMax = arr.length ? Math.max(...arr) : minUpperLimit;
                const padding = Math.max(YPAD_MIN_ABS, currentMax * YPAD_RATIO);
                const dynUpper = Math.max(minUpperLimit, currentMax + padding);
                const yKey = i === 0 ? 'yaxis.range' : `yaxis${i + 1}.range`;
                yaxisUpdates[yKey] = [minY, dynUpper];
                dynUpperByIndex[i] = dynUpper;

                // Dynamic y ticks
                const ticks = generateNiceTicks(minY, dynUpper, 15);
                const yTickValsKey = i === 0 ? 'yaxis.tickvals' : `yaxis${i + 1}.tickvals`;
                const yTickTextKey = i === 0 ? 'yaxis.ticktext' : `yaxis${i + 1}.ticktext`;
                yTicksUpdates[yTickValsKey] = ticks;
                yTicksUpdates[yTickTextKey] = ticks.map(String);
            }

            const updateData = {
                x: [],
                y: []
            };

            for (let i = 0; i < Config.NUM_PRESSURE_TRANSDUCERS; i++) {
                updateData.x.push([...sensorData.x]); // For sensor data trace
                updateData.y.push([...sensorData.y[i]]);

                updateData.x.push([...sensorData.x]); // For rolling average trace
                updateData.y.push([...sensorData.y_avg[i]]);
            }

            // Build zone shapes extended to dynamic upper
            for (let i = 0; i < Config.NUM_PRESSURE_TRANSDUCERS; i++) {
                const ptConfig = Config.PRESSURE_TRANSDUCERS[i];
                const currentXAxisRefZone = i === 0 ? 'x' : `x${i + 1}`;
                const currentYAxisRefZone = i === 0 ? 'y' : `y${i + 1}`;
                const dynUpper = dynUpperByIndex[i] ?? ptConfig.max_value;
                newShapes.push({ type: 'rect', xref: currentXAxisRefZone, yref: currentYAxisRefZone,
                    x0: windowStart, x1: windowEnd,
                    y0: ptConfig.min_value, y1: ptConfig.warning_value,
                    fillcolor: 'rgba(0, 255, 0, 0.2)', line: { width: 0 } });
                newShapes.push({ type: 'rect', xref: currentXAxisRefZone, yref: currentYAxisRefZone,
                    x0: windowStart, x1: windowEnd,
                    y0: ptConfig.warning_value, y1: ptConfig.danger_value,
                    fillcolor: 'rgba(255, 165, 0, 0.2)', line: { width: 0 } });
                newShapes.push({ type: 'rect', xref: currentXAxisRefZone, yref: currentYAxisRefZone,
                    x0: windowStart, x1: windowEnd,
                    y0: ptConfig.danger_value, y1: dynUpper,
                    fillcolor: 'rgba(255, 0, 0, 0.2)', line: { width: 0 } });
            }

            Plotly.update('pt-subplots', {
                x: updateData.x,
                y: updateData.y
            }, {
                shapes: newShapes,
                ...xaxisUpdates,
                ...yaxisUpdates,
                ...yTicksUpdates
            });
        }
    };
});

function generateNiceTicks(minV, maxV, maxTicks) {
    // Generate <= maxTicks "nice" tick positions from minV to maxV
    if (!isFinite(minV) || !isFinite(maxV)) return [minV, maxV];
    if (maxV < minV) [minV, maxV] = [maxV, minV];
    const span = maxV - minV;
    if (span <= 0) return [minV, maxV];
    const raw = span / Math.max(2, maxTicks);
    const pow10 = Math.pow(10, Math.floor(Math.log10(raw)));
    const candidates = [1, 2, 5, 10].map(m => m * pow10);
    let step = candidates[0];
    for (const s of candidates) {
        if (span / s <= maxTicks) { step = s; break; }
        step = s; // fallback to largest if none under maxTicks
    }
    const start = Math.ceil(minV / step) * step;
    const ticks = [];
    for (let v = start; v <= maxV + 1e-9; v += step) {
        ticks.push(Number(v.toFixed(6)));
        if (ticks.length > maxTicks + 2) break; // safety
    }
    if (ticks.length === 0 || ticks[0] > minV) ticks.unshift(minV);
    if (ticks[ticks.length - 1] < maxV) ticks.push(maxV);
    // Ensure uniqueness and ordering
    return Array.from(new Set(ticks)).sort((a,b)=>a-b);
}
