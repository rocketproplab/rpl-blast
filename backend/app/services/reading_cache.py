from __future__ import annotations

import threading
from typing import Any, Dict, Optional, Tuple


class LatestReadingCache:
    """Thread-safe snapshot of latest reading."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._snapshot: Optional[Dict[str, Any]] = None

    def set(self, value: Dict[str, Any], timestamp: float) -> None:
        with self._lock:
            self._snapshot = {"value": dict(value), "timestamp": float(timestamp)}

    def get(self) -> Tuple[Optional[Dict[str, Any]], Optional[float]]:
        with self._lock:
            if self._snapshot is None:
                return None, None
            return dict(self._snapshot["value"]), self._snapshot["timestamp"]

    def set_full(self, snapshot: Dict[str, Any]) -> None:
        with self._lock:
            self._snapshot = dict(snapshot)

    def get_full(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return None if self._snapshot is None else dict(self._snapshot)
