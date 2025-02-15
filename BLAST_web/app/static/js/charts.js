// Add at the start of the file
console.log('Charts.js loading...');
console.log('Config:', Config);

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing charts...');
    
    // Common layout settings
    const commonLayout = {
        margin: { t: 25, r: 50, l: 50, b: 25 },
        autosize: true,
        width: null,
        height: null,
        showlegend: true,
        legend: {
            orientation: 'h',
            y: -0.2
        },
        xaxis: {
            fixedrange: false,
            rangeslider: {
                visible: false
            },
            dtick: 1,
            tickformat: '.0f',
            // ticksuffix: 's'
        },
        font: {
            size: 10
        }
    };

    // Update the gauge layout
    const gaugeLayout = {
        margin: { t: 15, b: 0, l: 0, r: 0 },
        height: 80
    };

    // Create thermocouple chart
    let tcChart = Plotly.newPlot('tc-chart', [
        // Background shapes for zones
        {
            type: 'scatter',
            x: [0, 0],  // Will be updated in updateCharts
            y: [0, Config.TEMPERATURE_BOUNDARIES.safe[1]],
            fill: 'tozeroy',
            fillcolor: 'rgba(0, 255, 0, 0.2)',
            line: { width: 0 },
            name: 'Safe Zone',
            showlegend: false,
            yaxis: 'y2'
        },
        {
            type: 'scatter',
            x: [0, 0],  // Will be updated in updateCharts
            y: [Config.TEMPERATURE_BOUNDARIES.safe[1], Config.TEMPERATURE_BOUNDARIES.warning[1]],
            fill: 'tonexty',
            fillcolor: 'rgba(255, 165, 0, 0.2)',
            line: { width: 0 },
            name: 'Warning Zone',
            showlegend: false,
            yaxis: 'y2'
        },
        {
            type: 'scatter',
            x: [0, 0],  // Will be updated in updateCharts
            y: [Config.TEMPERATURE_BOUNDARIES.warning[1], Config.TEMPERATURE_BOUNDARIES.danger[1]],
            fill: 'tonexty',
            fillcolor: 'rgba(255, 0, 0, 0.2)',
            line: { width: 0 },
            name: 'Danger Zone',
            showlegend: false,
            yaxis: 'y2'
        },
        // Thermocouple traces
        ...Array(Config.NUM_THERMOCOUPLES).fill().map((_, i) => ({
            y: [],
            type: 'line',
            name: `TC${i + 1}`
        }))
    ], {
        ...commonLayout,
        title: 'Thermocouples',
        yaxis: {
            range: [0, 1000],
            title: 'Temperature',
            fixedrange: true
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

    // Create pressure transducer chart
    let ptChart = Plotly.newPlot('pt-chart', [
        // Background shapes for zones
        {
            type: 'scatter',
            x: [0, 0],  // Will be updated in updateCharts
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
            x: [0, 0],  // Will be updated in updateCharts
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
            x: [0, 0],  // Will be updated in updateCharts
            y: [Config.PRESSURE_BOUNDARIES.warning[1], Config.PRESSURE_BOUNDARIES.danger[1]],
            fill: 'tonexty',
            fillcolor: 'rgba(255, 0, 0, 0.2)',
            line: { width: 0 },
            name: 'Danger Zone',
            showlegend: false,
            yaxis: 'y2'
        },
        // Pressure transducer traces
        ...Array(Config.NUM_PRESSURE_TRANSDUCERS).fill().map((_, i) => ({
            y: [],
            type: 'line',
            name: `PT${i + 1}`
        }))
    ], {
        ...commonLayout,
        title: 'Pressure Transducers',
        yaxis: {
            range: [0, 1000],
            title: 'Pressure',
            fixedrange: true
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

    // Create valve indicators
    const flowIndicators = [];
    for (let i = 1; i <= 6; i++) {
        flowIndicators.push(
            Plotly.newPlot(`flow${i}`, [{
                type: 'indicator',
                mode: 'gauge',
                value: 0,
                title: { text: `V${i}`, font: { size: 12 } },
                gauge: {
                    shape: 'angular',
                    axis: { range: [0, 1], visible: false },
                    bar: { color: 'red' },
                    bgcolor: 'red',
                    borderwidth: 2,
                    bordercolor: '#ccc'
                }
            }], gaugeLayout)
        );
    }

    // Data arrays for each sensor type
    let sensorData = {
        x: [],
        tc: Array(Config.NUM_THERMOCOUPLES).fill().map(() => []),
        pt: Array(Config.NUM_PRESSURE_TRANSDUCERS).fill().map(() => [])
    };

    const startTime = Date.now();

    function updateCharts() {
        const currentTime = (Date.now() - startTime) / 1000;
        const xrange = [Math.max(0, currentTime - 30), currentTime];
        
        fetch('/data')
            .then(response => response.json())
            .then(data => {
                if (data.value && data.value.tc) {
                    // Update sensor data arrays
                    sensorData.x.push(currentTime);
                    data.value.tc.forEach((val, i) => {
                        sensorData.tc[i].push(val);
                    });
                    data.value.pt.forEach((val, i) => {
                        sensorData.pt[i].push(val);
                    });

                    // Update TC chart with zones
                    Plotly.update('tc-chart', {
                        x: [
                            [xrange[0], xrange[1]],  // Safe zone
                            [xrange[0], xrange[1]],  // Warning zone
                            [xrange[0], xrange[1]],  // Danger zone
                            ...Array(Config.NUM_THERMOCOUPLES).fill(sensorData.x)
                        ],
                        y: [
                            [Config.TEMPERATURE_BOUNDARIES.safe[1], Config.TEMPERATURE_BOUNDARIES.safe[1]],  // Safe zone
                            [Config.TEMPERATURE_BOUNDARIES.warning[1], Config.TEMPERATURE_BOUNDARIES.warning[1]],  // Warning zone
                            [Config.TEMPERATURE_BOUNDARIES.danger[1], Config.TEMPERATURE_BOUNDARIES.danger[1]],  // Danger zone
                            ...sensorData.tc
                        ]
                    }, {
                        xaxis: {
                            range: xrange,
                            dtick: 1,
                            tickformat: '.0f'
                        }
                    });

                    // Update PT chart with zones
                    Plotly.update('pt-chart', {
                        x: [
                            [xrange[0], xrange[1]],  // Safe zone
                            [xrange[0], xrange[1]],  // Warning zone
                            [xrange[0], xrange[1]],  // Danger zone
                            ...Array(Config.NUM_PRESSURE_TRANSDUCERS).fill(sensorData.x)
                        ],
                        y: [
                            [Config.PRESSURE_BOUNDARIES.safe[1], Config.PRESSURE_BOUNDARIES.safe[1]],  // Safe zone
                            [Config.PRESSURE_BOUNDARIES.warning[1], Config.PRESSURE_BOUNDARIES.warning[1]],  // Warning zone
                            [Config.PRESSURE_BOUNDARIES.danger[1], Config.PRESSURE_BOUNDARIES.danger[1]],  // Danger zone
                            ...sensorData.pt
                        ]
                    }, {
                        xaxis: {
                            range: xrange,
                            dtick: 1,
                            tickformat: '.0f'
                        }
                    });

                    // Keep only last 300 points
                    if (sensorData.x.length > 300) {
                        sensorData.x.shift();
                        sensorData.tc.forEach(arr => arr.shift());
                        sensorData.pt.forEach(arr => arr.shift());
                    }

                    // Update valve indicators
                    data.value.fcv.forEach((state, i) => {
                        Plotly.update(`flow${i + 1}`, {
                            value: state ? 1 : 0,
                            'gauge.bar.color': state ? 'green' : 'red',
                            'gauge.bgcolor': state ? '#f8f8f8' : 'red'
                        });
                    });
                }
            })
            .catch(error => {
                console.error('Error fetching data:', error);
            });
    }

    // Update at fixed 100ms intervals (10 Hz)
    setInterval(updateCharts, 100);

    // Make plots responsive
    window.addEventListener('resize', function() {
        Plotly.Plots.resize('tc-chart');
        Plotly.Plots.resize('pt-chart');
        for (let i = 1; i <= 6; i++) {
            Plotly.Plots.resize(`flow${i}`);
        }
    });

    // Handle valve button clicks
    async function handleValveClick(valveNumber) {
        try {
            const response = await fetch('/toggle_valve', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ valve: valveNumber })
            });
            const data = await response.json();
            if (data.success) {
                console.log(`Valve ${valveNumber} toggled successfully`);
            } else {
                console.error(`Failed to toggle valve ${valveNumber}:`, data.error);
            }
        } catch (error) {
            console.error('Error:', error);
        }
    }

    // Add after chart creation
    console.log('TC Chart:', tcChart);
    console.log('PT Chart:', ptChart);
}); 