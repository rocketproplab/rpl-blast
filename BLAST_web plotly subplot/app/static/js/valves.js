document.addEventListener('DOMContentLoaded', function() {
    // console.log('valves.js: Loaded and DOM ready.');
    // console.log('valves.js: Config.FLOW_CONTROL_VALVES:', Config.FLOW_CONTROL_VALVES);

    window.updateValveDisplays = function(fcvActualData, fcvExpectedData) {
        // console.log('valves.js: updateValveDisplays called with:', fcvActualData, fcvExpectedData);

        if (!Config.FLOW_CONTROL_VALVES || !Array.isArray(Config.FLOW_CONTROL_VALVES)) {
            console.error('valves.js: Config.FLOW_CONTROL_VALVES is not defined or not an array.');
            return;
        }

        if (!fcvActualData || !Array.isArray(fcvActualData)) {
            // console.warn('valves.js: Actual FCV data is missing or not an array.');
            // return; // Allow partial update if expected is present, or handle as needed
        }
        if (!fcvExpectedData || !Array.isArray(fcvExpectedData)) {
            // console.warn('valves.js: Expected FCV data is missing or not an array.');
            // return; // Allow partial update if actual is present
        }

        Config.FLOW_CONTROL_VALVES.forEach((valve, index) => {
            if (!valve || typeof valve.id === 'undefined') {
                console.warn('valves.js: Valve config is invalid or missing id at index:', index);
                return; // Skip this valve
            }

            const actualStateElement = document.getElementById(`valve-${valve.id}-actual`);
            const expectedStateElement = document.getElementById(`valve-${valve.id}-expected`);

            // Update Actual State Block
            if (actualStateElement) {
                if (fcvActualData && typeof fcvActualData[index] !== 'undefined') {
                    actualStateElement.classList.remove('on', 'off');
                    actualStateElement.classList.add(fcvActualData[index] ? 'on' : 'off');
                } else {
                    // console.warn(`valves.js: No actual data for valve ${valve.id} (index ${index})`);
                    // Optionally set to a default/unknown state, e.g., grey
                    actualStateElement.classList.remove('on');
                    actualStateElement.classList.add('off'); // Default to off if no data
                }
            } else {
                // console.warn('valves.js: Actual state element not found for valve id:', valve.id);
            }

            // Update Expected State Block
            if (expectedStateElement) {
                if (fcvExpectedData && typeof fcvExpectedData[index] !== 'undefined') {
                    expectedStateElement.classList.remove('on', 'off');
                    expectedStateElement.classList.add(fcvExpectedData[index] ? 'on' : 'off');
                } else {
                    // console.warn(`valves.js: No expected data for valve ${valve.id} (index ${index})`);
                    expectedStateElement.classList.remove('on');
                    expectedStateElement.classList.add('off'); // Default to off if no data
                }
            } else {
                // console.warn('valves.js: Expected state element not found for valve id:', valve.id);
            }
        });
    };

    // Initial call with empty data or default states if desired, 
    // otherwise it will wait for the first call from get_data.js
    // For example, to ensure all are initially set to 'off' visually if not already by CSS:
    // if (Config.FLOW_CONTROL_VALVES && Config.FLOW_CONTROL_VALVES.length > 0) {
    //     const initialStates = Array(Config.FLOW_CONTROL_VALVES.length).fill(false);
    //     window.updateValveDisplays(initialStates, initialStates);
    // }
}); 