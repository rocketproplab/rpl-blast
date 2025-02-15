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
            }
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
        }
    });

    // Create pressure transducer chart
    let ptChart = Plotly.newPlot('pt-chart', [
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

                    // Update plots with sliding window
                    const xrange = [Math.max(0, currentTime - 30), currentTime];
                    
                    // Update TC chart
                    Plotly.update('tc-chart', {
                        x: Array(Config.NUM_THERMOCOUPLES).fill(sensorData.x),
                        y: sensorData.tc
                    }, {
                        xaxis: {range: xrange}
                    });

                    // Update PT chart
                    Plotly.update('pt-chart', {
                        x: Array(Config.NUM_PRESSURE_TRANSDUCERS).fill(sensorData.x),
                        y: sensorData.pt
                    }, {
                        xaxis: {range: xrange}
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