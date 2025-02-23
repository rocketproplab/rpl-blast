document.addEventListener('DOMContentLoaded', function() {
    // Create line charts for each pressure transducer
    const ptLineCharts = [];
    const sensorData = {
        x: [],
        y: Array(Config.NUM_PRESSURE_TRANSDUCERS).fill().map(() => [])
    };

    // Initialize each line chart
    const lineChartElements = document.querySelectorAll('.pt-line-chart');
    lineChartElements.forEach((element, index) => {
        // Get container dimensions accounting for padding
        const rect = element.getBoundingClientRect();
        const computedStyle = window.getComputedStyle(element);
        const paddingX = parseFloat(computedStyle.paddingLeft) + parseFloat(computedStyle.paddingRight);
        const paddingY = parseFloat(computedStyle.paddingTop) + parseFloat(computedStyle.paddingBottom);
        
        const sensorName = Config.PRESSURE_TRANSDUCERS[index];
        
        const chart = Plotly.newPlot(element, [
            // Background shapes for zones
            {
                type: 'scatter',
                x: [0, 0],
                y: [0, Config.PRESSURE_BOUNDARIES.safe[1]],
                fill: 'tozeroy',
                fillcolor: 'rgba(0, 255, 0, 0.2)',
                line: { width: 0 },
                name: 'Safe Zone',
                showlegend: false,
                yaxis: 'y2'
            },
            {
                type: 'scatter',
                x: [0, 0],
                y: [Config.PRESSURE_BOUNDARIES.safe[1], Config.PRESSURE_BOUNDARIES.warning[1]],
                fill: 'tonexty',
                fillcolor: 'rgba(255, 165, 0, 0.2)',
                line: { width: 0 },
                name: 'Warning Zone',
                showlegend: false,
                yaxis: 'y2'
            },
            {
                type: 'scatter',
                x: [0, 0],
                y: [Config.PRESSURE_BOUNDARIES.warning[1], Config.PRESSURE_BOUNDARIES.danger[1]],
                fill: 'tonexty',
                fillcolor: 'rgba(255, 0, 0, 0.2)',
                line: { width: 0 },
                name: 'Danger Zone',
                showlegend: false,
                yaxis: 'y2'
            },
            // Pressure transducer trace
            {
                x: [],
                y: [],
                type: 'scatter',
                name: sensorName,
                line: { color: '#000' }
            }
        ], {
            title: {
                text: sensorName,
                font: { size: 12 }
            },
            showlegend: false,
            margin: { t: 30, r: 10, b: 30, l: 40 },
            width: rect.width - paddingX,
            height: rect.height - paddingY,
            xaxis: {
                showgrid: true,
                zeroline: false,
                range: [0, 30],
                fixedrange: true,
                tickfont: { size: 8 },
                title: {
                    text: 'Time (s)',
                    font: { size: 10 }
                }
            },
            yaxis: {
                range: [0, 1000],
                fixedrange: true,
                tickfont: { size: 8 },
                title: {
                    text: 'Pressure',
                    font: { size: 10 }
                },
            },
            yaxis2: {
                range: [0, 1000],
                overlaying: 'y',
                showgrid: false,
                zeroline: false,
                showline: false,
                showticklabels: false,
                fixedrange: true
            }
        });
        ptLineCharts.push(chart);

        // Update chart size on window resize
        window.addEventListener('resize', () => {
            const newRect = element.getBoundingClientRect();
            const newComputedStyle = window.getComputedStyle(element);
            const newPaddingX = parseFloat(newComputedStyle.paddingLeft) + parseFloat(newComputedStyle.paddingRight);
            const newPaddingY = parseFloat(newComputedStyle.paddingTop) + parseFloat(newComputedStyle.paddingBottom);
            
            Plotly.relayout(element, {
                width: newRect.width - newPaddingX,
                height: newRect.height - newPaddingY
            });
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

                    // Update each line chart
                    lineChartElements.forEach((element, index) => {
                        Plotly.update(element, {
                            x: [
                                [xrange[0], xrange[1]], // Safe zone
                                [xrange[0], xrange[1]], // Warning zone
                                [xrange[0], xrange[1]], // Danger zone
                                sensorData.x // Sensor data
                            ],
                            y: [
                                [Config.PRESSURE_BOUNDARIES.safe[1], Config.PRESSURE_BOUNDARIES.safe[1]],
                                [Config.PRESSURE_BOUNDARIES.warning[1], Config.PRESSURE_BOUNDARIES.warning[1]],
                                [Config.PRESSURE_BOUNDARIES.danger[1], Config.PRESSURE_BOUNDARIES.danger[1]],
                                sensorData.y[index]
                            ]
                        }, {
                            xaxis: {
                                range: xrange
                            }
                        });
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
