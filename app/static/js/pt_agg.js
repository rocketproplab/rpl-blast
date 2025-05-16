const traces = Config.PRESSURE_TRANSDUCERS.map((pt, index) => ({
    x: [],
    y: [],
}));

Plotly.newPlot('pt-agg-plot', traces, layout, {
    responsive: true,
    ...PT_PLOT_CONFIG.hover
});

// Update chart size on window resize
window.addEventListener('resize', () => {
    const newRect = container.getBoundingClientRect();
    // ... existing code ...
});

// const startTime = Date.now(); // Removed, handled by get_data.js

// This function will be called by get_data.js
window.updatePTPlotsAndStats = function(currentTime, ptDataValues) {
    const windowStart = Math.max(0, currentTime - WINDOW_SIZE);
    const windowEnd = currentTime;

    // fetch('/data?type=pt') // Removed, data is passed in
    //     .then(response => response.json())
    //     .then(data => { // Data is now ptDataValues directly
    if (ptDataValues) { // data.value && data.value.pt changed to ptDataValues
        // Add new data point
        sensorData.x.push(currentTime);
        ptDataValues.forEach((value, i) => { // data.value.pt changed to ptDataValues
            sensorData.y[i].push(value);
        });

        // ... existing code ...
        // Update the plot with new data and ranges
        Plotly.update('pt-agg-plot', {
            x: Array(Config.NUM_PRESSURE_TRANSDUCERS).fill().map(() => [...sensorData.x]),
            y: sensorData.y
            // ... existing code ...
        });

        // Now, call the function in pt_line.js to update subplots with the SAME data
        if (typeof window.updateAllSubPlots === 'function') {
            window.updateAllSubPlots(currentTime, ptDataValues); // data.value.pt changed to ptDataValues
        }

        // Also, call the function in pt_stats.js to update stats with the SAME data
        if (typeof window.updateAllStats === 'function') {
            window.updateAllStats(currentTime, ptDataValues); // data.value.pt changed to ptDataValues
        }
    }
    // })
    // .catch(error => console.error('Error fetching data:', error)); // Removed
};

// Update chart every 100ms (10 Hz) // Removed
// setInterval(updateChart, 100); // Removed

function generateTickVals(axisMin, axisMax) {
    // ... existing code ...
} 