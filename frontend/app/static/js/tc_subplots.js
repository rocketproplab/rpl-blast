document.addEventListener('DOMContentLoaded', function() {
    const WINDOW_SIZE = 5; // Size of the time window in seconds, should match tc_agg.js

    const tcSensorData = {
        x: [],
        y: Array(Config.NUM_THERMOCOUPLES).fill().map(() => [])
        // Add y_avg and history here if rolling averages are needed later for TCs
    };

    const container = document.getElementById('tc-subplots-container');
    if (!container) {
        console.error('TC Subplots container not found');
        return;
    }
    const plotDiv = document.getElementById('tc-subplots-plot');
    if (!plotDiv) {
        console.error('TC Subplots plot div not found');
        return;
    }

    const traces = [];
    for (let i = 0; i < Config.NUM_THERMOCOUPLES; i++) {
        const tcConfig = Config.THERMOCOUPLES[i];
        traces.push({
            x: [],
            y: [],
            ...PT_PLOT_CONFIG.trace,
            name: tcConfig.name,
            xaxis: (i === 0 ? 'x' : `x${i + 1}`),
            yaxis: (i === 0 ? 'y' : `y${i + 1}`),
            line: { ...PT_PLOT_CONFIG.trace.line, color: tcConfig.color } 
        });
        // Add rolling average traces here if needed later
    }

    const layout = {
        ...PT_PLOT_CONFIG.layout,
        grid: {
            rows: Config.NUM_THERMOCOUPLES,
            columns: 1,
            pattern: 'independent',
            rowgap: 0.10 // Adjust as needed
        },
        showlegend: false,
        title: {
            ...PT_PLOT_CONFIG.title,
            text: 'Thermocouple Readings'
        }
        // height and width will be set by responsive relayout
    };

    for (let i = 0; i < Config.NUM_THERMOCOUPLES; i++) {
        const xAxisNameKey = i === 0 ? 'xaxis' : `xaxis${i + 1}`;
        layout[xAxisNameKey] = {
            ...PT_PLOT_CONFIG.axis,
            title: {
                ...PT_PLOT_CONFIG.axis.title,
                text: i === Config.NUM_THERMOCOUPLES - 1 ? 'Time' : ''
            },
            range: [0, WINDOW_SIZE]
        };
        const yAxisNameKey = i === 0 ? 'yaxis' : `yaxis${i + 1}`;
        layout[yAxisNameKey] = {
            ...PT_PLOT_CONFIG.axis,
            title: {
                text: Config.THERMOCOUPLES[i].name,
                font: { 
                    color: Config.THERMOCOUPLES[i].color
                }
            },
            showline: true,
            linecolor: Config.THERMOCOUPLES[i].color,
            linewidth: 2,
            range: [Config.THERMOCOUPLES[i].min_value, Config.THERMOCOUPLES[i].max_value],
            tickvals: generateTickVals(Config.THERMOCOUPLES[i].min_value, Config.THERMOCOUPLES[i].max_value),
            ticktext: generateTickVals(Config.THERMOCOUPLES[i].min_value, Config.THERMOCOUPLES[i].max_value).map(String)
        };
    }

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


    window.updateAllTCSubPlots = function(currentTimeFromAgg, tcDataFromAgg) {
        const windowStart = Math.max(0, currentTimeFromAgg - WINDOW_SIZE);
        const windowEnd = currentTimeFromAgg;

        if (tcDataFromAgg) {
            tcSensorData.x.push(currentTimeFromAgg);
            tcDataFromAgg.forEach((value, i) => {
                tcSensorData.y[i].push(value);
                // Handle rolling average data update here if added
            });

            while (tcSensorData.x.length > 0 && tcSensorData.x[0] < windowStart) {
                tcSensorData.x.shift();
                tcSensorData.y.forEach(arr => arr.shift());
                // Shift rolling average data here if added
            }

            // const newShapes = []; 
            // if (Config.TEMPERATURE_BOUNDARIES) {
            //     for (let i = 0; i < Config.NUM_THERMOCOUPLES; i++) {
            //         const currentXAxisRefZone = i === 0 ? 'x' : `x${i + 1}`;
            //         const currentYAxisRefZone = i === 0 ? 'y' : `y${i + 1}`;
            //         // Green Zone (Safe)
            //         newShapes.push({
            //             type: 'rect', xref: currentXAxisRefZone, yref: currentYAxisRefZone,
            //             x0: windowStart, x1: windowEnd, 
            //             y0: Config.TEMPERATURE_BOUNDARIES.safe[0], y1: Config.TEMPERATURE_BOUNDARIES.safe[1], 
            //             fillcolor: 'rgba(0, 255, 0, 0.2)', line: { width: 0 }, layer: 'below'
            //         });
            //         // Orange Zone (Warning)
            //         newShapes.push({
            //             type: 'rect', xref: currentXAxisRefZone, yref: currentYAxisRefZone,
            //             x0: windowStart, x1: windowEnd, 
            //             y0: Config.TEMPERATURE_BOUNDARIES.warning[0], y1: Config.TEMPERATURE_BOUNDARIES.warning[1], 
            //             fillcolor: 'rgba(255, 165, 0, 0.2)', line: { width: 0 }, layer: 'below'
            //         });
            //         // Red Zone (Danger)
            //         newShapes.push({
            //             type: 'rect', xref: currentXAxisRefZone, yref: currentYAxisRefZone,
            //             x0: windowStart, x1: windowEnd, 
            //             y0: Config.TEMPERATURE_BOUNDARIES.danger[0], y1: Config.TEMPERATURE_BOUNDARIES.danger[1], 
            //             fillcolor: 'rgba(255, 0, 0, 0.2)', line: { width: 0 }, layer: 'below'
            //         });
            //     }
            // }

            const xaxisUpdates = {};
            for (let i = 0; i < Config.NUM_THERMOCOUPLES; i++) {
                const axisKey = i === 0 ? 'xaxis.range' : `xaxis${i + 1}.range`;
                xaxisUpdates[axisKey] = [windowStart, windowEnd];
            }
            
            const updateData = {
                x: Array(Config.NUM_THERMOCOUPLES).fill().map(() => [...tcSensorData.x]),
                y: tcSensorData.y
                // Add y_avg to updateData if rolling averages are implemented
            };

            Plotly.update(plotDiv, updateData, {
                // shapes: newShapes, // Add if R/Y/G zones are implemented
                ...xaxisUpdates
            });
        }
    };
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