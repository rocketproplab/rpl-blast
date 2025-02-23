document.addEventListener('DOMContentLoaded', function() {
    const sensorData = {
        x: [],
        y: Array(Config.NUM_PRESSURE_TRANSDUCERS).fill().map(() => [])
    };

    // Get container dimensions
    const container = document.getElementById('pt-subplots');
    const rect = container.getBoundingClientRect();
    const computedStyle = window.getComputedStyle(container);
    const paddingX = parseFloat(computedStyle.paddingLeft) + parseFloat(computedStyle.paddingRight);
    const paddingY = parseFloat(computedStyle.paddingTop) + parseFloat(computedStyle.paddingBottom);

    // Create subplot traces (only sensor data traces)
    const traces = [];
    for (let i = 0; i < Config.NUM_PRESSURE_TRANSDUCERS; i++) {
        traces.push({
            x: [],
            y: [],
            type: 'scatter',
            name: Config.PRESSURE_TRANSDUCERS[i].name,
            line: { color: '#000' },
            xaxis: `x${i + 1}`,
            yaxis: `y${i + 1}`
        });
    }

    // Create subplot layout with shapes for zones
    const layout = {
        grid: {
            rows: Config.NUM_PRESSURE_TRANSDUCERS,
            columns: 1,
            pattern: 'independent',
            rowgap: 0.15
        },
        shapes: [], // Will be populated with zone rectangles
        showlegend: false,
        width: rect.width - paddingX,
        height: rect.height - paddingY,
        margin: { t: 50, r: 20, b: 40, l: 50 },
        paper_bgcolor: 'white',
        plot_bgcolor: 'white',
        font: {
            family: 'Roboto, sans-serif'  // Set default font for all text
        },
        title: {
            text: 'Pressure Transducer Readings',
            font: { 
                size: 16,
                family: 'Roboto, sans-serif'
            },
            y: 1.1
        },
        annotations: [{
            text: 'Pressure (psi)',
            textangle: -90,
            font: { 
                size: 12,
                family: 'Roboto, sans-serif'
            },
            showarrow: false,
            x: -0.17,
            xref: 'paper',
            y: 0.5,
            yref: 'paper'
        }, {
            text: 'Time (s)',
            font: { 
                size: 12,
                family: 'Roboto, sans-serif'
            },
            showarrow: false,
            x: 0.5,
            xref: 'paper',
            y: -0.05,
            yref: 'paper'
        }]
    };

    // Add axis properties and zone shapes for each subplot
    for (let i = 0; i < Config.NUM_PRESSURE_TRANSDUCERS; i++) {
        // Add subplot title
        layout.annotations.push({
            text: Config.PRESSURE_TRANSDUCERS[i].name,
            font: { 
                size: 12,
                family: 'Roboto, sans-serif'
            },
            showarrow: false,
            x: 0.5,
            xref: `x${i + 1} domain`,
            y: 1.2,
            yref: `y${i + 1} domain`
        });

        // Add axis properties
        layout[`xaxis${i + 1}`] = {
            showgrid: true,
            zeroline: false,
            range: [0, 30],
            fixedrange: true,
            tickfont: { 
                size: 8,
                family: 'Roboto, sans-serif'
            },
            showticklabels: i === Config.NUM_PRESSURE_TRANSDUCERS - 1,
            showline: true,
            linewidth: 1,
            gridcolor: '#eee',
            domain: [0, 1]
        };
        
        layout[`yaxis${i + 1}`] = {
            range: [0, 1000],
            fixedrange: true,
            tickfont: { 
                size: 8,
                family: 'Roboto, sans-serif'
            },
            showline: true,
            linewidth: 1,
            linecolor: '#ddd',
            gridcolor: '#eee',
            showticklabels: true
        };

        // Add zone shapes for this subplot
        layout.shapes.push(
            // Safe zone
            {
                type: 'rect',
                xref: `x${i + 1}`,
                yref: `y${i + 1}`,
                x0: 0,
                x1: 30,
                y0: 0,
                y1: Config.PRESSURE_BOUNDARIES.safe[1],
                fillcolor: 'rgba(0, 255, 0, 0.2)',
                line: { width: 0 }
            },
            // Warning zone
            {
                type: 'rect',
                xref: `x${i + 1}`,
                yref: `y${i + 1}`,
                x0: 0,
                x1: 30,
                y0: Config.PRESSURE_BOUNDARIES.safe[1],
                y1: Config.PRESSURE_BOUNDARIES.warning[1],
                fillcolor: 'rgba(255, 165, 0, 0.2)',
                line: { width: 0 }
            },
            // Danger zone
            {
                type: 'rect',
                xref: `x${i + 1}`,
                yref: `y${i + 1}`,
                x0: 0,
                x1: 30,
                y0: Config.PRESSURE_BOUNDARIES.warning[1],
                y1: Config.PRESSURE_BOUNDARIES.danger[1],
                fillcolor: 'rgba(255, 0, 0, 0.2)',
                line: { width: 0 }
            }
        );
    }

    const chart = Plotly.newPlot('pt-subplots', traces, layout);

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

    const startTime = Date.now();

    function updateCharts() {
        const currentTime = (Date.now() - startTime) / 1000;
        const xrange = [Math.max(0, currentTime - 30), currentTime];

        fetch('/data?type=pt')
            .then(response => response.json())
            .then(data => {
                if (data.value && data.value.pt) {
                    // Add new data point
                    sensorData.x.push(currentTime);
                    data.value.pt.forEach((value, i) => {
                        sensorData.y[i].push(value);
                    });

                    // Update shapes for the moving time window
                    const newShapes = [];
                    for (let i = 0; i < Config.NUM_PRESSURE_TRANSDUCERS; i++) {
                        newShapes.push(
                            // Safe zone
                            {
                                type: 'rect',
                                xref: `x${i + 1}`,
                                yref: `y${i + 1}`,
                                x0: xrange[0],
                                x1: xrange[1],
                                y0: 0,
                                y1: Config.PRESSURE_BOUNDARIES.safe[1],
                                fillcolor: 'rgba(0, 255, 0, 0.2)',
                                line: { width: 0 }
                            },
                            // Warning zone
                            {
                                type: 'rect',
                                xref: `x${i + 1}`,
                                yref: `y${i + 1}`,
                                x0: xrange[0],
                                x1: xrange[1],
                                y0: Config.PRESSURE_BOUNDARIES.safe[1],
                                y1: Config.PRESSURE_BOUNDARIES.warning[1],
                                fillcolor: 'rgba(255, 165, 0, 0.2)',
                                line: { width: 0 }
                            },
                            // Danger zone
                            {
                                type: 'rect',
                                xref: `x${i + 1}`,
                                yref: `y${i + 1}`,
                                x0: xrange[0],
                                x1: xrange[1],
                                y0: Config.PRESSURE_BOUNDARIES.warning[1],
                                y1: Config.PRESSURE_BOUNDARIES.danger[1],
                                fillcolor: 'rgba(255, 0, 0, 0.2)',
                                line: { width: 0 }
                            }
                        );
                    }

                    // Update the plot with new data and shapes
                    Plotly.update('pt-subplots', {
                        x: sensorData.y.map(() => sensorData.x),
                        y: sensorData.y
                    }, {
                        shapes: newShapes,
                        xaxis: { range: xrange }
                    });

                    // Keep only last 300 points
                    if (sensorData.x.length > 300) {
                        sensorData.x.shift();
                        sensorData.y.forEach(arr => arr.shift());
                    }
                }
            })
            .catch(error => console.error('Error fetching data:', error));
    }

    // Update charts every 100ms (10 Hz)
    setInterval(updateCharts, 100);
});
