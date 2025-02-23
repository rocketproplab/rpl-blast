console.log('Thermocouples.js loading...');
console.log('Config:', Config);

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing thermocouple chart...');
    
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
            tickformat: '.0f'
        },
        font: {
            size: 10
        }
    };

    // Create thermocouple chart
    let tcChart = Plotly.newPlot('tc-chart', [
        // Background shapes for zones
        {
            type: 'scatter',
            x: [0, 0],
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
            x: [0, 0],
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
            x: [0, 0],
            y: [Config.TEMPERATURE_BOUNDARIES.warning[1], Config.TEMPERATURE_BOUNDARIES.danger[1]],
            fill: 'tonexty',
            fillcolor: 'rgba(255, 0, 0, 0.2)',
            line: { width: 0 },
            name: 'Danger Zone',
            showlegend: false,
            yaxis: 'y2'
        },
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

    // Data arrays for thermocouple data
    let sensorData = {
        x: [],
        tc: Array(Config.NUM_THERMOCOUPLES).fill().map(() => [])
    };

    const startTime = Date.now();

    function updateChart() {
        const currentTime = (Date.now() - startTime) / 1000;
        const xrange = [Math.max(0, currentTime - 30), currentTime];
        
        fetch('/data?type=tc')
            .then(response => response.json())
            .then(data => {
                if (data.value && data.value.tc) {
                    sensorData.x.push(currentTime);
                    data.value.tc.forEach((val, i) => {
                        sensorData.tc[i].push(val);
                    });

                    Plotly.update('tc-chart', {
                        x: [
                            [xrange[0], xrange[1]],
                            [xrange[0], xrange[1]],
                            [xrange[0], xrange[1]],
                            ...Array(Config.NUM_THERMOCOUPLES).fill(sensorData.x)
                        ],
                        y: [
                            [Config.TEMPERATURE_BOUNDARIES.safe[1], Config.TEMPERATURE_BOUNDARIES.safe[1]],
                            [Config.TEMPERATURE_BOUNDARIES.warning[1], Config.TEMPERATURE_BOUNDARIES.warning[1]],
                            [Config.TEMPERATURE_BOUNDARIES.danger[1], Config.TEMPERATURE_BOUNDARIES.danger[1]],
                            ...sensorData.tc
                        ]
                    }, {
                        xaxis: {
                            range: xrange,
                            dtick: 1,
                            tickformat: '.0f'
                        }
                    });

                    if (sensorData.x.length > 300) {
                        sensorData.x.shift();
                        sensorData.tc.forEach(arr => arr.shift());
                    }
                }
            })
            .catch(error => {
                console.error('Error fetching data:', error);
            });
    }

    setInterval(updateChart, 100);

    window.addEventListener('resize', function() {
        Plotly.Plots.resize('tc-chart');

    });
}); 