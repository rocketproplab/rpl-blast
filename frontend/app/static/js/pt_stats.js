document.addEventListener('DOMContentLoaded', function() {
    const WINDOW_SIZE = 10; // seconds, smoothing window for stats
    const RATE_SECONDS = 60; // scale rate as change per 60 seconds

    // Store data history for each sensor: { sensorName: [{time: t, value: v}, ...], ... }
    const sensorHistories = {};
    // Store max pressure for each sensor: { sensorName: maxValue, ... }
    const sensorMaxValues = {};

    Config.PRESSURE_TRANSDUCERS.forEach(pt => {
        const sensorNameKey = pt.name.toLowerCase().replace(/ /g, '-');
        sensorHistories[sensorNameKey] = [];
        sensorMaxValues[sensorNameKey] = -Infinity;
    });

    window.updateAllStats = function(currentTime, ptDataArray) {
        if (!ptDataArray || ptDataArray.length === 0) {
            return;
        }

        Config.PRESSURE_TRANSDUCERS.forEach((pt, index) => {
            const sensorNameKey = pt.name.toLowerCase().replace(/ /g, '-');
            const latestValue = ptDataArray[index];

            if (latestValue === undefined) return; // Skip if no data for this sensor

            // Update history
            const history = sensorHistories[sensorNameKey];
            history.push({ time: currentTime, value: latestValue });

            // Trim history to window size + a little buffer for rate calculation
            const windowStartTime = currentTime - WINDOW_SIZE;
            while (history.length > 0 && history[0].time < windowStartTime - 1) { // Keep slightly more than WINDOW_SIZE for rate
                history.shift();
            }

            // Update Max Value
            if (latestValue > sensorMaxValues[sensorNameKey]) {
                sensorMaxValues[sensorNameKey] = latestValue;
            }

            // Calculate Stats
            let sumForAverage = 0;
            let countForAverage = 0;
            let valueAtWindowStart = null;

            // Iterate backwards from latest to find points within the window for average and rate
            for (let i = history.length - 1; i >= 0; i--) {
                const point = history[i];
                if (point.time >= windowStartTime) {
                    sumForAverage += point.value;
                    countForAverage++;
                    valueAtWindowStart = point.value; // Oldest point in/near window start
                } else {
                    // If point.time is older than windowStartTime, but no valueAtWindowStart found yet from strictly within window,
                    // use this as the closest point before window start for rate calculation if needed.
                    if (valueAtWindowStart === null) valueAtWindowStart = point.value;
                    break; // Stop once we are outside the window
                }
            }
            
            const averageValue = countForAverage > 0 ? sumForAverage / countForAverage : 0;
            
            let rateOfChange = 0;
            if (valueAtWindowStart !== null && history.length > 1) {
                // Find the actual start point for rate calculation (closest to currentTime - WINDOW_SIZE)
                let actualWindowStartPoint = history[0]; // Default to oldest point if no exact match
                for(let i = 0; i < history.length; i++){
                    if(history[i].time >= windowStartTime){
                        actualWindowStartPoint = history[i];
                        break;
                    }
                }
                if (currentTime - actualWindowStartPoint.time > 0) { // Avoid division by zero
                    // Rate based on change over the actual duration of available data in window, scaled to RATE_SECONDS
                    const duration = currentTime - actualWindowStartPoint.time;
                    if (duration > 0.1) { // only calc if duration is somewhat significant
                        rateOfChange = (latestValue - actualWindowStartPoint.value) / duration * RATE_SECONDS;
                    } else {
                        rateOfChange = 0; // or handle as N/A if duration is too short
                    }
                } else {
                    rateOfChange = 0;
                }
            } else if (history.length === 1){
                rateOfChange = 0; // Not enough data for rate
            }


            // Update DOM
            const statBlock = document.getElementById(`pt-stat-${sensorNameKey}`);
            if (statBlock) {
                statBlock.querySelector('.stat-latest').textContent = latestValue.toFixed(2);
                statBlock.querySelector('.stat-avg').textContent = averageValue.toFixed(2);
                statBlock.querySelector('.stat-rate').textContent = rateOfChange.toFixed(2);
                statBlock.querySelector('.stat-max').textContent = sensorMaxValues[sensorNameKey].toFixed(2);
            }
        });
    };
});
