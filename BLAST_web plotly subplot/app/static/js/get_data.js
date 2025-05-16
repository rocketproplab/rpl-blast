// app/static/js/get_data.js
document.addEventListener('DOMContentLoaded', function() {
    const UPDATE_INTERVAL = 100; // ms, data fetch frequency
    const startTime = Date.now();

    function fetchAllDataAndUpdate() {
        const currentTime = (Date.now() - startTime) / 1000; // seconds

        fetch('/data') 
            .then(response => {
                if (!response.ok) {
                    console.error('get_data.js: Network response was not ok', response.statusText);
                    throw new Error('Network response was not ok ' + response.statusText);
                }
                return response.json();
            })
            .then(data => {
                if (data && data.value) {
                    const allSensorData = data.value;

                    // Pressure Transducers
                    if (allSensorData.pt) {
                        if (typeof window.updatePTPlotsAndStats === 'function') {
                            window.updatePTPlotsAndStats(currentTime, allSensorData.pt);
                        }
                    }

                    // Thermocouples
                    if (allSensorData.tc) {
                        if (typeof window.updateTCPlotsAndStats === 'function') {
                            window.updateTCPlotsAndStats(currentTime, allSensorData.tc);
                        }
                    }

                    // Load Cells
                    if (allSensorData.lc) {
                        if (typeof window.updateLCPlotsAndStats === 'function') {
                            window.updateLCPlotsAndStats(currentTime, allSensorData.lc);
                        }
                    }

                    // Flow Control Valves
                    if (allSensorData.fcv_actual && allSensorData.fcv_expected) {
                        if (typeof window.updateValveDisplays === 'function') {
                            window.updateValveDisplays(allSensorData.fcv_actual, allSensorData.fcv_expected);
                        }
                    }
                }
            })
            .catch(error => console.error('get_data.js: Error in fetchAllDataAndUpdate:', error));
    }

    setInterval(fetchAllDataAndUpdate, UPDATE_INTERVAL);
}); 