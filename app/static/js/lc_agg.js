Plotly.newPlot(plotDiv, traces, layout, { responsive: true, ...PT_PLOT_CONFIG.hover });

function updateChartDimensions() {
    const rect = container.getBoundingClientRect();
    // ... existing code ...
}

updateChartDimensions();
window.addEventListener('resize', updateChartDimensions);

// const startTime = Date.now(); // Removed

// This function will be called by get_data.js
window.updateLCPlotsAndStats = function(currentTime, lcDataValues) { // Renamed and params changed
    const windowStart = Math.max(0, currentTime - WINDOW_SIZE);
    const windowEnd = currentTime;

    // fetch('/data?type=lc') // Removed
    //     .then(response => response.json())
    //     .then(data => { // lcDataValues is passed directly
    if (lcDataValues) { // data.value && data.value.lc changed to lcDataValues
        const newLCValues = lcDataValues;
        lcSensorData.x.push(currentTime);
        // ... existing code ...
        Plotly.update(plotDiv, {
            x: Array(Config.NUM_LOAD_CELLS).fill().map(() => [...lcSensorData.x]),
            y: lcSensorData.y
        }, { 'xaxis.range': [windowStart, windowEnd], shapes: newShapes });

        if (typeof window.updateAllLCSubPlots === 'function') { window.updateAllLCSubPlots(currentTime, newLCValues); }
        if (typeof window.updateAllLCStats === 'function') { window.updateAllLCStats(currentTime, newLCValues); }
    }
    // })
    // .catch(error => console.error('Error fetching LC data for aggregate plot:', error)); // Removed
};
// Corrected generateTickVals function for LC plots (e.g. every 100 or 50 units based on range)
// ... existing code ...
layout.yaxis.ticktext = layout.yaxis.tickvals.map(String);
Plotly.relayout(plotDiv, layout); // Apply new tick PgetNextToken

// setInterval(fetchDataAndUpdateCharts, UPDATE_INTERVAL); // Removed
}); 