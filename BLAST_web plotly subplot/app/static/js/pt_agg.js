document.addEventListener('DOMContentLoaded', function() {
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
        type: 'scatter',
        name: pt.name,
        mode: 'lines',
        line: { width: 2 }
    }));

    // Create layout
    const layout = {
        showlegend: true,
        legend: {
            x: 1,
            xanchor: 'right',
            y: 1
        },
        width: rect.width - paddingX,
        height: rect.height - paddingY,
        margin: { t: 50, r: 70, b: 60, l: 70 },
        paper_bgcolor: 'white',
        plot_bgcolor: 'white',
        font: {
            family: 'Roboto, sans-serif'
        },
        title: {
            text: 'Composite Pressure Readings',
            font: { 
                size: 16,
                family: 'Roboto, sans-serif'
            }
        },
        xaxis: {
            title: {
                text: 'Time (s)',
                standoff: 20,
                font: { size: 12 },
            },
            showgrid: true,
            gridcolor: '#eee',
            range: [0, 30],
            fixedrange: true
        },
        yaxis: {
            title: {
                text: 'Pressure (psi)',
                standoff: 20,
                font: { size: 12 },
            },
            showgrid: true,
            gridcolor: '#eee',
            range: [0, 1000],
            fixedrange: true
        },
        shapes: [
            // Safe zone
            {
                type: 'rect',
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
                x0: 0,
                x1: 30,
                y0: Config.PRESSURE_BOUNDARIES.warning[1],
                y1: Config.PRESSURE_BOUNDARIES.danger[1],
                fillcolor: 'rgba(255, 0, 0, 0.2)',
                line: { width: 0 }
            }
        ]
    };

    // Initialize plot
    Plotly.newPlot('pt-agg-plot', traces, layout);

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

    // Start time for x-axis
    const startTime = Date.now();

    function updateChart() {
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

                    // Update plot with new data
                    Plotly.update('pt-agg-plot', {
                        x: sensorData.y.map(() => sensorData.x),
                        y: sensorData.y
                    }, {
                        shapes: [
                            {
                                x0: xrange[0],
                                x1: xrange[1],
                                y0: 0,
                                y1: Config.PRESSURE_BOUNDARIES.safe[1]
                            },
                            {
                                x0: xrange[0],
                                x1: xrange[1],
                                y0: Config.PRESSURE_BOUNDARIES.safe[1],
                                y1: Config.PRESSURE_BOUNDARIES.warning[1]
                            },
                            {
                                x0: xrange[0],
                                x1: xrange[1],
                                y0: Config.PRESSURE_BOUNDARIES.warning[1],
                                y1: Config.PRESSURE_BOUNDARIES.danger[1]
                            }
                        ],
                        'xaxis.range': xrange
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

    // Update chart every 100ms (10 Hz)
    setInterval(updateChart, 100);
});
