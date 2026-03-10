document.addEventListener('DOMContentLoaded', function () {
    var serialBtn = document.getElementById('serial-btn');
    var slot = document.getElementById('serial-monitor-slot');

    if (!serialBtn || !slot) return;

    // Pad a number string to a fixed width for column alignment
    function padVal(val, width) {
        var s = String(val);
        while (s.length < width) s = ' ' + s;
        return s;
    }

    // Format a raw JSON packet with fixed-width numbers for alignment
    function formatPacket(raw) {
        try {
            var obj = JSON.parse(raw);
            var v = obj.value || obj;

            // Pad each number to fixed width inside the arrays
            function fmtArr(arr, w) {
                return '[' + arr.map(function (n) {
                    var s = (typeof n === 'number') ? n.toFixed(2) : String(n);
                    while (s.length < w) s = ' ' + s;
                    return s;
                }).join(', ') + ']';
            }

            var parts = [];
            if (v.pt)  parts.push('"pt": '  + fmtArr(v.pt, 8));
            if (v.tc)  parts.push('"tc": '  + fmtArr(v.tc, 7));
            if (v.lc)  parts.push('"lc": '  + fmtArr(v.lc, 7));
            if (v.fcv) parts.push('"fcv": ' + JSON.stringify(v.fcv));

            return '{"value": {' + parts.join(', ') + '}}';
        } catch (e) {
            return raw;
        }
    }

    // Build the serial monitor HTML
    var paneHTML =
        '<div id="serial-pane" class="serial-pane">' +
        '<div class="serial-pane-header">' +
        '<h2>Serial Monitor</h2>' +
        '</div>' +
        '<div class="serial-pane-body">' +
        '<textarea id="serial-console" readonly></textarea>' +
        '</div>' +
        '</div>';

    var pollTimer = null;
    var nextIndex = -1; // Start by getting all buffered lines

    function startPolling() {
        if (pollTimer) return; // Already polling

        pollTimer = setInterval(function () {
            fetch('/api/serial/logs?after=' + nextIndex)
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    if (!data.lines || data.lines.length === 0) return;

                    var console_el = document.getElementById('serial-console');
                    if (!console_el) return;

                    var newText = '';
                    for (var i = 0; i < data.lines.length; i++) {
                        var line = data.lines[i];
                        newText += line.timestamp + '  ' + formatPacket(line.raw) + '\n';
                    }

                    console_el.value += newText;

                    // Auto-scroll to bottom (like Arduino IDE)
                    console_el.scrollTop = console_el.scrollHeight;

                    // Update index for next incremental fetch
                    nextIndex = data.next_index - 1;
                })
                .catch(function () { /* silently retry on next tick */ });
        }, 100); // Poll every 100ms for near-real-time display
    }

    function stopPolling() {
        if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
        }
    }

    // Check localStorage for persisted state
    var isOpen = localStorage.getItem('serialMonitorOpen') === 'true';

    if (isOpen) {
        slot.innerHTML = paneHTML;
        serialBtn.textContent = 'Close Serial Monitor';
        startPolling();
    }

    serialBtn.addEventListener('click', function () {
        var pane = document.getElementById('serial-pane');

        if (pane) {
            // Currently open — close it
            stopPolling();
            slot.innerHTML = '';
            serialBtn.textContent = 'Serial Monitor';
            localStorage.setItem('serialMonitorOpen', 'false');
        } else {
            // Currently closed — open it
            slot.innerHTML = paneHTML;
            serialBtn.textContent = 'Close Serial Monitor';
            nextIndex = -1; // Get recent history when opening
            localStorage.setItem('serialMonitorOpen', 'true');
            startPolling();
        }
    });
});
