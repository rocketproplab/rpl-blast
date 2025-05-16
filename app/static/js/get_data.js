// app/static/js/get_data.js
document.addEventListener('DOMContentLoaded', function() {
    const UPDATE_INTERVAL = 100; // ms, data fetch frequency
    const startTime = Date.now();

    function fetchAllDataAndUpdate() {
        const currentTime = (Date.now() - startTime) / 1000; // seconds

        fetch('/data') // Fetches all data: { pt: [...], tc: [...], lc: [...], fcv: [...], timestamp: "..." }
            .then(response => response.json())
            .then(data => {
                if (data && data.value) {
                    const allSensorData = data.value;

                    // Pressure Transducers
                    if (allSensorData.pt && typeof window.updatePTPlotsAndStats === 'function') {
                        window.updatePTPlotsAndStats(currentTime, allSensorData.pt);
                    }

                    // Thermocouples
                    if (allSensorData.tc && typeof window.updateTCPlotsAndStats === 'function') {
                        window.updateTCPlotsAndStats(currentTime, allSensorData.tc);
                    }

                    // Load Cells
                    if (allSensorData.lc && typeof window.updateLCPlotsAndStats === 'function') {
                        window.updateLCPlotsAndStats(currentTime, allSensorData.lc);
                    } else {
                        // console.warn('get_data.js: No LC data in response');
                    }
                    
                    // Flow Control Valves
                    if (allSensorData.fcv_actual && allSensorData.fcv_expected && typeof window.updateValveDisplays === 'function') {
                        // console.log('get_data.js: Calling updateValveDisplays');
                        window.updateValveDisplays(allSensorData.fcv_actual, allSensorData.fcv_expected);
                    } else {
                        // if (typeof window.updateValveDisplays !== 'function') {
                        //     console.warn('get_data.js: updateValveDisplays function not found');
                        // } else {
                        //     console.warn('get_data.js: No FCV actual/expected data in response');
                        // }
                    }

                } else {
                    console.error('get_data.js: Received empty or invalid data object from /data endpoint:', data);
                }
            })
            .catch(error => console.error('Error fetching all sensor data:', error));
    }

    // Start the master data fetch loop
    setInterval(fetchAllDataAndUpdate, UPDATE_INTERVAL);
}); 