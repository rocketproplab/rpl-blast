// Analysis Mode Controller
// Handles switching between live and analysis modes, run selection, and playback control

class AnalysisModeController {
    constructor() {
        this.currentMode = 'live';
        this.currentRun = null;
        this.userSelectedMode = 'live'; // Track user's mode selection (even if no run loaded yet)
        this.playbackState = {
            isPaused: false,
            speed: 1.0,
            position: 0.0,
            duration: 0.0,
            isAtEnd: false
        };
        this.availableRuns = [];
        this.statusPollInterval = null;
        this.updateInterval = 50; // Poll status every 50ms for smoother updates
        this.lastPositionUpdateTime = Date.now(); // Track when position was last updated
        this.lastKnownPosition = 0; // Track last known position for local calculation
        this.lastKnownSpeed = 1.0; // Track last known speed
        this.lastKnownIsPaused = true; // Track pause state
        
        this.init();
    }
    
    init() {
        // Check initial status
        this.updateStatus();
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Start status polling
        this.startStatusPolling();
    }
    
    setupEventListeners() {
        // Mode toggle buttons
        const liveBtn = document.getElementById('mode-live');
        const analysisBtn = document.getElementById('mode-analysis');
        
        if (liveBtn) {
            liveBtn.addEventListener('click', () => this.switchMode('live'));
        }
        if (analysisBtn) {
            analysisBtn.addEventListener('click', () => this.switchMode('analysis'));
        }
        
        // Run selection
        const runSelect = document.getElementById('run-select');
        const loadBtn = document.getElementById('load-run-btn');
        
        if (runSelect) {
            runSelect.addEventListener('change', (e) => {
                this.currentRun = e.target.value;
            });
        }
        
        if (loadBtn) {
            loadBtn.addEventListener('click', () => this.loadSelectedRun());
        }
        
        // Playback controls
        const playBtn = document.getElementById('playback-play');
        const pauseBtn = document.getElementById('playback-pause');
        const seekBar = document.getElementById('playback-seek');
        const speedSelect = document.getElementById('playback-speed');
        const timeInput = document.getElementById('playback-time-input');
        const rewindBtn = document.getElementById('playback-rewind');
        const forwardBtn = document.getElementById('playback-forward');
        const stepBackBtn = document.getElementById('playback-step-back');
        const stepForwardBtn = document.getElementById('playback-step-forward');
        
        if (playBtn) {
            playBtn.addEventListener('click', () => this.play());
        }
        if (pauseBtn) {
            pauseBtn.addEventListener('click', () => this.pause());
        }
        if (seekBar) {
            // Use both input and change events for better responsiveness
            seekBar.addEventListener('input', (e) => {
                const tSeconds = parseFloat(e.target.value);
                this.seek(tSeconds);
            });
            seekBar.addEventListener('change', (e) => {
                const tSeconds = parseFloat(e.target.value);
                this.seek(tSeconds);
            });
        }
        if (speedSelect) {
            speedSelect.addEventListener('change', (e) => {
                const speed = parseFloat(e.target.value);
                this.setSpeed(speed);
            });
        }
        if (timeInput) {
            timeInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.jumpToTime(e.target.value);
                }
            });
            timeInput.addEventListener('blur', (e) => {
                if (e.target.value) {
                    this.jumpToTime(e.target.value);
                }
            });
        }
        if (rewindBtn) {
            rewindBtn.addEventListener('click', () => this.stepBackward(10));
        }
        if (forwardBtn) {
            forwardBtn.addEventListener('click', () => this.stepForward(10));
        }
        if (stepBackBtn) {
            stepBackBtn.addEventListener('click', () => this.stepBackward(1));
        }
        if (stepForwardBtn) {
            stepForwardBtn.addEventListener('click', () => this.stepForward(1));
        }
        
        // Plot window size selector
        const plotWindowSizeSelect = document.getElementById('plot-window-size');
        if (plotWindowSizeSelect) {
            plotWindowSizeSelect.addEventListener('change', (e) => {
                const windowSize = parseFloat(e.target.value);
                this.setPlotWindowSize(windowSize);
            });
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Only handle if not typing in an input
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }
            
            if (e.code === 'Space') {
                e.preventDefault();
                if (this.playbackState.isPaused) {
                    this.play();
                } else {
                    this.pause();
                }
            } else if (e.code === 'ArrowLeft') {
                e.preventDefault();
                this.stepBackward(10);
            } else if (e.code === 'ArrowRight') {
                e.preventDefault();
                this.stepForward(10);
            }
        });
    }
    
    async switchMode(mode) {
        this.userSelectedMode = mode;
        if (mode === 'live') {
            await this.switchToLive();
        } else if (mode === 'analysis') {
            // Show the analysis UI and load available runs
            // Don't switch backend mode until a run is loaded
            this.currentMode = 'analysis';
            this.updateModeButtons();
            this.showAnalysisUI();
            await this.loadAvailableRuns();
        }
    }
    
    async switchToLive() {
        try {
            const response = await fetch('/api/analysis/switch_to_live', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (!response.ok) {
                throw new Error('Failed to switch to live mode');
            }
            
            this.currentMode = 'live';
            this.userSelectedMode = 'live';
            this.currentRun = null;
            this.hideAnalysisUI();
            this.updateModeButtons();
            
            // Restart data updates for live mode
            if (typeof window.restartDataUpdates === 'function') {
                window.restartDataUpdates();
            }
        } catch (error) {
            console.error('Error switching to live mode:', error);
            alert('Failed to switch to live mode: ' + error.message);
        }
    }
    
    async loadAvailableRuns() {
        try {
            const response = await fetch('/api/analysis/runs');
            if (!response.ok) {
                throw new Error('Failed to fetch runs');
            }
            
            const data = await response.json();
            this.availableRuns = data.runs || [];
            this.updateRunSelect();
            return this.availableRuns;
        } catch (error) {
            console.error('Error loading runs:', error);
            return [];
        }
    }
    
    updateRunSelect() {
        const runSelect = document.getElementById('run-select');
        if (!runSelect) return;
        
        // Clear existing options
        runSelect.innerHTML = '<option value="">Select a run...</option>';
        
        // Add runs
        this.availableRuns.forEach(run => {
            const option = document.createElement('option');
            option.value = run.run_id;
            option.textContent = `${run.run_id} (${this.formatDuration(run.duration_seconds)})`;
            runSelect.appendChild(option);
        });
    }
    
    async loadSelectedRun() {
        const runSelect = document.getElementById('run-select');
        if (!runSelect || !runSelect.value) {
            alert('Please select a run first');
            return;
        }
        
        const runId = runSelect.value;
        const speedSelect = document.getElementById('playback-speed');
        const speed = speedSelect ? parseFloat(speedSelect.value) : 1.0;
        
        try {
            // First, load all data from the run
            const dataResponse = await fetch(`/api/analysis/data/${runId}`);
            if (!dataResponse.ok) {
                const error = await dataResponse.json();
                throw new Error(error.detail || 'Failed to fetch run data');
            }
            const allData = await dataResponse.json();
            
            // Load all data into plots
            this.loadAllAnalysisData(allData.data || []);
            
            // Then switch backend to analysis mode
            const response = await fetch(`/api/analysis/load/${runId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    playback_speed: speed,
                    start_at_seconds: 0.0
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to load run');
            }
            
            const data = await response.json();
            this.currentRun = runId;
            this.currentMode = 'analysis';
            this.userSelectedMode = 'analysis';
            this.playbackState.duration = data.duration_seconds || 0;
            this.playbackState.position = data.start_at_seconds || 0;
            this.playbackState.isPaused = true;
            
            // Initialize plot window size from dropdown (default 30s)
            const plotWindowSizeSelect = document.getElementById('plot-window-size');
            if (plotWindowSizeSelect) {
                window.plotWindowSize = parseFloat(plotWindowSizeSelect.value) || 30;
            } else {
                window.plotWindowSize = 30; // Default fallback
            }
            
            this.updateModeButtons();
            this.showAnalysisUI();
            this.updatePlaybackControls();
            
            // Immediately update status to sync with backend
            await this.updateStatus();
            
            // Restart data updates for analysis mode
            if (typeof window.restartDataUpdates === 'function') {
                window.restartDataUpdates();
            }
            
            // Update plot window to show current position
            this.updateAnalysisPlotWindow(this.playbackState.position);
            
            // Force an immediate stats update at the current position
            const currentTime = this.playbackState.position || 0;
            if (typeof window.forceDataUpdate === 'function') {
                window.forceDataUpdate();
            }
            
            // Also directly update stats if we have data
            setTimeout(() => {
                // Get current data from backend to trigger stats update
                fetch('/data')
                    .then(response => response.json())
                    .then(data => {
                        if (data && data.value) {
                            if (data.value.pt && typeof window.updateAllStats === 'function') {
                                window.updateAllStats(currentTime, data.value.pt);
                            }
                            if (data.value.tc && typeof window.updateAllTCStats === 'function') {
                                window.updateAllTCStats(currentTime, data.value.tc);
                            }
                            if (data.value.lc && typeof window.updateAllLCStats === 'function') {
                                window.updateAllLCStats(currentTime, data.value.lc);
                            }
                        }
                    })
                    .catch(err => console.error('Error updating stats after load:', err));
            }, 200);
            
            console.log('Run loaded:', data);
            console.log('Analysis mode active. Playback state:', this.playbackState);
        } catch (error) {
            console.error('Error loading run:', error);
            alert('Failed to load run: ' + error.message);
        }
    }
    
    async play() {
        await this.controlPlayback('play');
    }
    
    async pause() {
        await this.controlPlayback('pause');
    }
    
    async seek(tSeconds) {
        // Clamp to valid range
        tSeconds = Math.max(0, Math.min(tSeconds, this.playbackState.duration || 0));
        await this.controlPlayback('seek', { t_seconds: tSeconds });
    }
    
    async setSpeed(speed) {
        await this.controlPlayback('set_speed', { speed: speed });
    }
    
    async stepBackward(seconds) {
        const newTime = Math.max(0, (this.playbackState.position || 0) - seconds);
        await this.seek(newTime);
    }
    
    async stepForward(seconds) {
        const newTime = Math.min(
            this.playbackState.duration || 0,
            (this.playbackState.position || 0) + seconds
        );
        await this.seek(newTime);
    }
    
    jumpToTime(timeString) {
        // Parse time string (MM:SS or HH:MM:SS)
        const parts = timeString.split(':').map(p => parseInt(p, 10));
        let seconds = 0;
        
        if (parts.length === 2) {
            // MM:SS format
            seconds = parts[0] * 60 + parts[1];
        } else if (parts.length === 3) {
            // HH:MM:SS format
            seconds = parts[0] * 3600 + parts[1] * 60 + parts[2];
        } else {
            // Try parsing as just seconds
            seconds = parseFloat(timeString) || 0;
        }
        
        this.seek(seconds);
    }
    
    async controlPlayback(action, params = {}) {
        try {
            const response = await fetch('/api/analysis/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action, ...params })
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to control playback');
            }
            
            const data = await response.json();
            // Always update position from backend response (it should have the correct paused position)
            if (data.current_position !== undefined && data.current_position !== null) {
                this.lastKnownPosition = data.current_position;
                this.lastPositionUpdateTime = Date.now();
                this.playbackState.position = data.current_position;
            }
            if (data.is_paused !== undefined) {
                this.lastKnownIsPaused = data.is_paused;
                this.playbackState.isPaused = data.is_paused;
            }
            if (data.playback_speed !== undefined) {
                this.lastKnownSpeed = data.playback_speed;
                this.playbackState.speed = data.playback_speed;
            }
            this.playbackState.isAtEnd = data.is_at_end !== undefined ? data.is_at_end : false;
            
            this.updatePlaybackControls();
        } catch (error) {
            console.error('Error controlling playback:', error);
            alert('Playback control error: ' + error.message);
        }
    }
    
    async updateStatus() {
        try {
            const response = await fetch('/api/analysis/status');
            if (!response.ok) {
                return;
            }
            
            const data = await response.json();
            
            // Only update currentMode from backend if a run is actually loaded
            // Otherwise, respect userSelectedMode (user clicked analysis but hasn't loaded a run yet)
            if (data.mode === 'analysis' && data.run_id) {
                this.currentMode = 'analysis';
                this.currentRun = data.run_id;
                
                // Update position and track for local calculation
                const newPosition = data.current_position || 0.0;
                this.lastKnownPosition = newPosition;
                this.lastKnownSpeed = data.playback_speed || 1.0;
                this.lastKnownIsPaused = data.is_paused || false;
                this.lastPositionUpdateTime = Date.now();
                
                this.playbackState.position = newPosition;
                this.playbackState.duration = data.total_duration || 0.0;
                this.playbackState.isPaused = this.lastKnownIsPaused;
                this.playbackState.speed = this.lastKnownSpeed;
                this.playbackState.isAtEnd = data.is_at_end || false;
                
                this.showAnalysisUI();
                this.updatePlaybackControls();
            } else if (data.mode === 'live') {
                // Only hide UI if user hasn't selected analysis mode
                if (this.userSelectedMode === 'live') {
                    this.currentMode = 'live';
                    this.currentRun = null;
                    this.hideAnalysisUI();
                }
            }
            
            // Update mode buttons based on user selection, not just backend state
            this.updateModeButtons();
        } catch (error) {
            console.error('Error updating status:', error);
        }
    }
    
    updateModeButtons() {
        const liveBtn = document.getElementById('mode-live');
        const analysisBtn = document.getElementById('mode-analysis');
        
        // Use userSelectedMode to determine which button is active
        if (liveBtn) {
            liveBtn.classList.toggle('active', this.userSelectedMode === 'live');
        }
        if (analysisBtn) {
            analysisBtn.classList.toggle('active', this.userSelectedMode === 'analysis');
        }
    }
    
    updatePlaybackControls() {
        // Update seek bar
        const seekBar = document.getElementById('playback-seek');
        if (seekBar) {
            const duration = this.playbackState.duration || 1;
            const position = this.playbackState.position || 0;
            seekBar.max = Math.max(1, duration);
            seekBar.value = position;
        }
        
        // Update time displays
        const timeInput = document.getElementById('playback-time-input');
        const timeTotal = document.getElementById('playback-time-total');
        
        if (timeInput) {
            const currentTime = this.formatTimeFull(this.playbackState.position || 0);
            // Only update if not focused (user might be typing)
            if (document.activeElement !== timeInput) {
                timeInput.value = currentTime;
            }
        }
        
        if (timeTotal) {
            timeTotal.textContent = this.formatTimeFull(this.playbackState.duration || 0);
        }
        
        // Update play/pause buttons visibility
        const playBtn = document.getElementById('playback-play');
        const pauseBtn = document.getElementById('playback-pause');
        
        if (playBtn && pauseBtn) {
            if (this.playbackState.isPaused || this.playbackState.isAtEnd) {
                playBtn.style.display = 'inline-flex';
                pauseBtn.style.display = 'none';
            } else {
                playBtn.style.display = 'none';
                pauseBtn.style.display = 'inline-flex';
            }
        }
        
        // Update speed select value
        const speedSelect = document.getElementById('playback-speed');
        if (speedSelect) {
            speedSelect.value = this.playbackState.speed;
        }
        
        // Update plot windows when position changes
        this.updatePlaybackPosition();
    }
    
    showAnalysisUI() {
        const analysisControls = document.getElementById('analysis-controls');
        if (analysisControls) {
            analysisControls.style.display = 'flex';
        }
        
        // Load available runs
        this.loadAvailableRuns();
    }
    
    hideAnalysisUI() {
        const analysisControls = document.getElementById('analysis-controls');
        if (analysisControls) {
            analysisControls.style.display = 'none';
        }
    }
    
    startStatusPolling() {
        if (this.statusPollInterval) {
            clearInterval(this.statusPollInterval);
            clearTimeout(this.statusPollInterval);
        }
        
        // Use faster polling for analysis mode
        this.statusPollInterval = setInterval(() => {
            this.updateStatus();
        }, this.updateInterval);
    }
    
    // Get current position with local calculation for smoother updates
    getCurrentPosition() {
        if (this.currentMode !== 'analysis') {
            return this.playbackState.position || 0;
        }
        
        // If paused, always return the exact position from backend (no interpolation)
        if (this.lastKnownIsPaused) {
            return this.playbackState.position || this.lastKnownPosition || 0;
        }
        
        // If playing, calculate position locally based on last known position, speed, and elapsed time
        const elapsed = (Date.now() - this.lastPositionUpdateTime) / 1000; // seconds
        const calculatedPosition = this.lastKnownPosition + (elapsed * this.lastKnownSpeed);
        
        // Clamp to duration
        const maxPosition = this.playbackState.duration || Infinity;
        return Math.min(calculatedPosition, maxPosition);
    }
    
    stopStatusPolling() {
        if (this.statusPollInterval) {
            clearInterval(this.statusPollInterval);
            clearTimeout(this.statusPollInterval);
            this.statusPollInterval = null;
        }
    }
    
    formatTime(seconds) {
        if (!seconds || seconds < 0) return '00:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }
    
    formatTimeFull(seconds) {
        if (!seconds || seconds < 0) return '00:00:00';
        const hours = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        if (hours > 0) {
            return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
        }
        return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }
    
    formatDuration(seconds) {
        if (!seconds) return '0s';
        if (seconds < 60) return `${Math.floor(seconds)}s`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
        return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
    }
    
    clearAllPlotData() {
        // Clear plot data by calling reset functions if they exist
        // This ensures plots start fresh when entering analysis mode
        if (typeof window.clearPTPlotData === 'function') {
            window.clearPTPlotData();
        }
        if (typeof window.clearTCPlotData === 'function') {
            window.clearTCPlotData();
        }
        if (typeof window.clearLCPlotData === 'function') {
            window.clearLCPlotData();
        }
        if (typeof window.clearPTSubplotData === 'function') {
            window.clearPTSubplotData();
        }
        if (typeof window.clearTCSubplotData === 'function') {
            window.clearTCSubplotData();
        }
        if (typeof window.clearLCSubplotData === 'function') {
            window.clearLCSubplotData();
        }
    }
    
    // Load all analysis data into plots
    loadAllAnalysisData(allDataEntries) {
        if (typeof window.loadAllPTAnalysisData === 'function') {
            window.loadAllPTAnalysisData(allDataEntries);
        }
        if (typeof window.loadAllTCAnalysisData === 'function') {
            window.loadAllTCAnalysisData(allDataEntries);
        }
        if (typeof window.loadAllLCAnalysisData === 'function') {
            window.loadAllLCAnalysisData(allDataEntries);
        }
        if (typeof window.loadAllPTSubplotAnalysisData === 'function') {
            window.loadAllPTSubplotAnalysisData(allDataEntries);
        }
        if (typeof window.loadAllTCSubplotAnalysisData === 'function') {
            window.loadAllTCSubplotAnalysisData(allDataEntries);
        }
        if (typeof window.loadAllLCSubplotAnalysisData === 'function') {
            window.loadAllLCSubplotAnalysisData(allDataEntries);
        }
        // Load data for stats calculation
        if (typeof window.loadAllPTStatsData === 'function') {
            window.loadAllPTStatsData(allDataEntries);
        }
        if (typeof window.loadAllTCStatsData === 'function') {
            window.loadAllTCStatsData(allDataEntries);
        }
        if (typeof window.loadAllLCStatsData === 'function') {
            window.loadAllLCStatsData(allDataEntries);
        }
    }
    
    // Update plot windows based on playback position
    updateAnalysisPlotWindow(position) {
        // Use requestAnimationFrame for smooth updates
        if (this._updateAnimationFrame) {
            cancelAnimationFrame(this._updateAnimationFrame);
        }
        
        this._updateAnimationFrame = requestAnimationFrame(() => {
            if (typeof window.updatePTPlotWindow === 'function') {
                window.updatePTPlotWindow(position);
            }
            if (typeof window.updateTCPlotWindow === 'function') {
                window.updateTCPlotWindow(position);
            }
            if (typeof window.updateLCPlotWindow === 'function') {
                window.updateLCPlotWindow(position);
            }
            if (typeof window.updatePTSubplotWindow === 'function') {
                window.updatePTSubplotWindow(position);
            }
            if (typeof window.updateTCSubplotWindow === 'function') {
                window.updateTCSubplotWindow(position);
            }
            if (typeof window.updateLCSubplotWindow === 'function') {
                window.updateLCSubplotWindow(position);
            }
            this._updateAnimationFrame = null;
        });
    }
    
    // Update plot windows when playback position changes
    updatePlaybackPosition() {
        if (this.currentMode === 'analysis' && this.playbackState) {
            const currentTime = this.playbackState.position || 0;
            this.updateAnalysisPlotWindow(currentTime);
            
            // Also update stats whenever position changes
            // Force stats update by calling the update functions directly
            if (typeof window.updateAllStats === 'function') {
                window.updateAllStats(currentTime, []);
            }
            if (typeof window.updateAllTCStats === 'function') {
                window.updateAllTCStats(currentTime, []);
            }
            if (typeof window.updateAllLCStats === 'function') {
                window.updateAllLCStats(currentTime, []);
            }
        }
    }
    
    setPlotWindowSize(windowSizeSeconds) {
        // Store window size globally so plot files can access it
        window.plotWindowSize = windowSizeSeconds;
        
        // Trigger plot window update with new size
        if (this.currentMode === 'analysis' && this.playbackState) {
            const currentTime = this.playbackState.position || 0;
            this.updateAnalysisPlotWindow(currentTime);
        }
    }
}

// Initialize when DOM is ready
let analysisController = null;
document.addEventListener('DOMContentLoaded', function() {
    analysisController = new AnalysisModeController();
    window.analysisController = analysisController; // Make globally accessible
    
    // Initialize default plot window size (30s)
    const plotWindowSizeSelect = document.getElementById('plot-window-size');
    if (plotWindowSizeSelect) {
        window.plotWindowSize = parseFloat(plotWindowSizeSelect.value) || 30;
    } else {
        window.plotWindowSize = 30; // Default fallback
    }
    
    // Restart data updates when mode changes
    if (typeof window.restartDataUpdates === 'function') {
        window.restartDataUpdates();
    }
});

