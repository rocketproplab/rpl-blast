document.addEventListener('DOMContentLoaded', function () {
    var serialBtn = document.getElementById('serial-btn');
    var slot = document.getElementById('serial-monitor-slot');

    if (!serialBtn || !slot) return;

    // Build the serial monitor HTML
    var paneHTML =
        '<div id="serial-pane" class="serial-pane">' +
        '<div class="serial-pane-header">' +
        '<h2>Serial Monitor</h2>' +
        '</div>' +
        '<div class="serial-pane-body">' +
        '<textarea id="serial-console" readonly>To be implemented soon</textarea>' +
        '</div>' +
        '</div>';

    // Check localStorage for persisted state
    var isOpen = localStorage.getItem('serialMonitorOpen') === 'true';

    if (isOpen) {
        slot.innerHTML = paneHTML;
        serialBtn.textContent = 'Close Serial Monitor';
    }

    serialBtn.addEventListener('click', function () {
        var pane = document.getElementById('serial-pane');

        if (pane) {
            // Currently open — close it
            slot.innerHTML = '';
            serialBtn.textContent = 'Serial Monitor';
            localStorage.setItem('serialMonitorOpen', 'false');
        } else {
            // Currently closed — open it
            slot.innerHTML = paneHTML;
            serialBtn.textContent = 'Close Serial Monitor';
            localStorage.setItem('serialMonitorOpen', 'true');
        }
    });
});
