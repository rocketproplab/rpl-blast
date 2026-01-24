from __future__ import annotations

import time
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Union, Optional
import bisect

from ..config.loader import Settings


@dataclass
class AnalysisSource:
    """Data source that reads from historical log files for analysis mode."""
    
    settings: Settings
    run_directory: Path
    update_interval_s: float = 0.1
    
    def __post_init__(self) -> None:
        self.data_entries: List[Dict] = []
        self.current_index: int = 0
        self.playback_speed: float = 1.0  # 1.0 = real-time, 2.0 = 2x speed
        self.is_paused: bool = True  # Start paused by default
        self.playback_start_time: Optional[float] = None  # When playback started
        self.start_t_seconds: float = 0.0  # t_seconds value when playback started
        self.first_entry_t_seconds: float = 0.0  # First entry's t_seconds for reference
        
    def initialize(self) -> None:
        """Load data.jsonl and parse all entries."""
        data_file = self.run_directory / "data.jsonl"
        
        if not data_file.exists():
            raise FileNotFoundError(f"data.jsonl not found in {self.run_directory}")
        
        self.data_entries = []
        malformed_count = 0
        
        try:
            with open(data_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry = json.loads(line)
                        # Validate entry structure
                        if not isinstance(entry, dict):
                            malformed_count += 1
                            continue
                        
                        # Ensure required fields exist
                        if 'raw' not in entry or 'recieved_at' not in entry:
                            malformed_count += 1
                            continue
                        
                        # Store t_seconds for fast seeking
                        entry['_t_seconds'] = entry.get('t_seconds', 0.0)
                        self.data_entries.append(entry)
                        
                    except json.JSONDecodeError:
                        malformed_count += 1
                        continue
            
            if not self.data_entries:
                raise ValueError(f"No valid entries found in {data_file}")
            
            # Sort by t_seconds to ensure chronological order
            self.data_entries.sort(key=lambda e: e.get('_t_seconds', 0.0))
            
            # Store first entry's t_seconds for reference
            if self.data_entries:
                self.first_entry_t_seconds = self.data_entries[0].get('_t_seconds', 0.0)
            
            # Reset to start
            self.current_index = 0
            self.playback_start_time = None
            self.start_t_seconds = 0.0
            
        except Exception as e:
            raise RuntimeError(f"Failed to load analysis data from {data_file}: {e}")
    
    def _find_entry_at_time(self, target_t_seconds: float) -> int:
        """Binary search to find entry index closest to target_t_seconds."""
        if not self.data_entries:
            return 0
        
        # Create list of t_seconds for binary search
        t_values = [e.get('_t_seconds', 0.0) for e in self.data_entries]
        
        # Find insertion point
        idx = bisect.bisect_left(t_values, target_t_seconds)
        
        # Clamp to valid range
        if idx >= len(self.data_entries):
            return len(self.data_entries) - 1
        if idx > 0:
            # Check which entry is closer
            prev_diff = abs(t_values[idx - 1] - target_t_seconds)
            curr_diff = abs(t_values[idx] - target_t_seconds)
            if prev_diff < curr_diff:
                return idx - 1
        return idx
    
    def seek_to_time(self, t_seconds: float) -> None:
        """Jump to specific time in the log (t_seconds from start of run)."""
        if not self.data_entries:
            return
        
        # Clamp to valid range
        max_t = self.data_entries[-1].get('_t_seconds', 0.0)
        t_seconds = max(0.0, min(t_seconds, max_t))
        
        self.current_index = self._find_entry_at_time(t_seconds)
        self.playback_start_time = time.time()
        self.start_t_seconds = t_seconds
    
    def set_playback_speed(self, speed: float) -> None:
        """Set playback speed multiplier (1.0 = real-time, 2.0 = 2x speed)."""
        if speed <= 0:
            raise ValueError("Playback speed must be positive")
        
        # Adjust start time to maintain current position when changing speed
        if self.playback_start_time is not None and not self.is_paused:
            current_t = self._get_current_playback_time()
            self.playback_start_time = time.time()
            self.start_t_seconds = current_t
        
        self.playback_speed = speed
    
    def pause(self) -> None:
        """Pause playback."""
        if self.is_paused:
            return
        
        # Store current position before pausing
        current_t = self._get_current_playback_time()
        self.start_t_seconds = current_t
        
        # Update current_index to match the current position
        self.current_index = self._find_entry_at_time(current_t)
        
        self.is_paused = True
        self.playback_start_time = None
    
    def resume(self) -> None:
        """Resume playback."""
        if not self.is_paused:
            return
        
        self.is_paused = False
        # Resume from stored position
        self.playback_start_time = time.time()
    
    def _get_current_playback_time(self) -> float:
        """Get current t_seconds position in playback."""
        if self.is_paused or self.playback_start_time is None:
            return self.start_t_seconds
        
        elapsed = (time.time() - self.playback_start_time) * self.playback_speed
        return self.start_t_seconds + elapsed
    
    def _get_entry_for_current_time(self) -> Optional[Dict]:
        """Get the data entry that should be returned at current playback time."""
        if not self.data_entries:
            return None
        
        if self.is_paused:
            # Return entry at current position
            if self.current_index < len(self.data_entries):
                return self.data_entries[self.current_index]
            return self.data_entries[-1] if self.data_entries else None
        
        # Calculate target time
        target_t = self._get_current_playback_time()
        
        # Find entry at or before target time
        idx = self._find_entry_at_time(target_t)
        
        # Update current index
        self.current_index = idx
        
        if idx < len(self.data_entries):
            return self.data_entries[idx]
        
        # Reached end of data
        return self.data_entries[-1] if self.data_entries else None
    
    def read_once(self) -> Tuple[Dict[str, Union[List[float], List[bool]]], float]:
        """
        Return next data entry based on playback state.
        Returns data in the same format as other DataSource implementations.
        """
        entry = self._get_entry_for_current_time()
        
        if entry is None:
            # No data available, return empty structure
            return {
                "pt": [],
                "tc": [],
                "lc": [],
                "fcv_actual": [],
                "fcv_expected": [],
                "timestamp": time.time(),
            }, time.time()
        
        # Extract raw data from log entry
        raw = entry.get('raw', {})
        
        # Build value dict matching DataSource format
        value = {
            "pt": list(raw.get('pt', [])),
            "tc": list(raw.get('tc', [])),
            "lc": list(raw.get('lc', [])),
            "fcv_actual": list(raw.get('fcv_actual', [])),
            "fcv_expected": list(raw.get('fcv_expected', [])),
            "timestamp": entry.get('recieved_at', time.time()),
        }
        
        # Return the original timestamp from the log
        timestamp = entry.get('recieved_at', time.time())
        
        return value, timestamp
    
    def shutdown(self) -> None:
        """Clean up resources."""
        self.data_entries = []
        self.current_index = 0
        self.playback_start_time = None
        self.is_paused = False
    
    def get_status(self) -> Dict:
        """Get current playback status."""
        if not self.data_entries:
            return {
                "total_entries": 0,
                "current_index": 0,
                "current_t_seconds": 0.0,
                "total_duration": 0.0,
                "is_paused": True,
                "playback_speed": self.playback_speed,
                "is_at_end": True,
            }
        
        current_t = self._get_current_playback_time()
        max_t = self.data_entries[-1].get('_t_seconds', 0.0)
        is_at_end = self.current_index >= len(self.data_entries) - 1
        
        return {
            "total_entries": len(self.data_entries),
            "current_index": self.current_index,
            "current_t_seconds": current_t,
            "total_duration": max_t,
            "is_paused": self.is_paused,
            "playback_speed": self.playback_speed,
            "is_at_end": is_at_end,
        }

