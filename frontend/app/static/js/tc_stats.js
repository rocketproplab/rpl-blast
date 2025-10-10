document.addEventListener('DOMContentLoaded', function() {
    const WINDOW_SIZE = 5; // seconds, MUST match tc_agg.js and tc_subplots.js

    const sensorHistories = {}; // { sensorNameKey: [{time: t, value: v}, ...], ... }
    const sensorMaxValues = {};   // { sensorNameKey: maxValue, ... }

    Config.THERMOCOUPLES.forEach(tc => {
        const sensorNameKey = tc.name.toLowerCase().replace(/ /g, '-');
        sensorHistories[sensorNameKey] = [];
        sensorMaxValues[sensorNameKey] = -Infinity;
    });

    window.updateAllTCStats = function(currentTime, tcDataArray) {
        if (!tcDataArray || tcDataArray.length === 0) {
            return;
        }

        Config.THERMOCOUPLES.forEach((tc, index) => {
            const sensorNameKey = tc.name.toLowerCase().replace(/ /g, '-');
            const latestValue = tcDataArray[index];

            if (latestValue === undefined) return;

            const history = sensorHistories[sensorNameKey];
            history.push({ time: currentTime, value: latestValue });

            const windowStartTime = currentTime - WINDOW_SIZE;
            while (history.length > 0 && history[0].time < windowStartTime - 1) { // Keep buffer for rate
                history.shift();
            }

            if (latestValue > sensorMaxValues[sensorNameKey]) {
                sensorMaxValues[sensorNameKey] = latestValue;
            }

            let sumForAverage = 0;
            let countForAverage = 0;
            let valueAtWindowStart = null;

            for (let i = history.length - 1; i >= 0; i--) {
                const point = history[i];
                if (point.time >= windowStartTime) {
                    sumForAverage += point.value;
                    countForAverage++;
                    valueAtWindowStart = point.value; 
                } else {
                    if (valueAtWindowStart === null) valueAtWindowStart = point.value;
                    break; 
                }
            }
            
            const averageValue = countForAverage > 0 ? sumForAverage / countForAverage : 0;
            
            let rateOfChange = 0;
            if (valueAtWindowStart !== null && history.length > 1) {
                let actualWindowStartPoint = history[0];
                for(let i = 0; i < history.length; i++){
                    if(history[i].time >= windowStartTime){
                        actualWindowStartPoint = history[i];
                        break;
                    }
                }
                const duration = currentTime - actualWindowStartPoint.time;
                if (duration > 0.1) { 
                    rateOfChange = (latestValue - actualWindowStartPoint.value) / duration * WINDOW_SIZE;
                } else {
                    rateOfChange = 0;
                }
            } else if (history.length === 1){
                rateOfChange = 0;
            }

            const statBlock = document.getElementById(`tc-stat-${sensorNameKey}`);
            if (statBlock) {
                statBlock.querySelector('.stat-latest').textContent = latestValue.toFixed(2);
                statBlock.querySelector('.stat-avg').textContent = averageValue.toFixed(2);
                statBlock.querySelector('.stat-rate').textContent = rateOfChange.toFixed(2);
                statBlock.querySelector('.stat-max').textContent = sensorMaxValues[sensorNameKey].toFixed(2);
            }
        });
    };
}); 