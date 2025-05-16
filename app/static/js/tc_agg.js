Plotly.newPlot(plotDiv, traces, layout, { responsive: true, ...PT_PLOT_CONFIG.hover });

function updateChartDimensions() {
    const rect = container.getBoundingClientRect();
    // ... existing code ...
}

updateChartDimensions();
window.addEventListener('resize', updateChartDimensions);

// const startTime = Date.now(); // Removed, handled by get_data.js

// This function will be called by get_data.js
window.updateTCPlotsAndStats = function(currentTime, tcDataValues) { // Renamed and params changed
    const windowStart = Math.max(0, currentTime - WINDOW_SIZE);
    const windowEnd = currentTime;

    // fetch('/data?type=tc') // Removed
    //     .then(response => response.json())
    //     .then(data => { // tcDataValues is now passed directly
    if (tcDataValues) { // data.value && data.value.tc changed to tcDataValues
        const newTCValues = tcDataValues;
        tcSensorData.x.push(currentTime);
    // ... existing code ...
        Plotly.update(plotDiv, {
            x: Array(Config.NUM_THERMOCOUPLES).fill().map(() => [...tcSensorData.x]),
            y: tcSensorData.y
        }, { 'xaxis.range': [windowStart, windowEnd], shapes: newShapes });

        if (typeof window.updateAllTCSubPlots === 'function') { window.updateAllTCSubPlots(currentTime, newTCValues); }
        if (typeof window.updateAllTCStats === 'function') { window.updateAllTCStats(currentTime, newTCValues); }
    }
    // })
    // .catch(error => console.error('Error fetching TC data for aggregate plot:', error)); // Removed
};

// Update yaxis with tickvals
// ... existing code ...
Plotly.relayout(plotDiv, layout); // Apply new tick values

// setInterval(fetchDataAndUpdateCharts, UPDATE_INTERVAL); // Removed
}); 