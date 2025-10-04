from __future__ import annotations

import json
import math
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict

import yaml


def _is_finite_number(x: float) -> bool:
    try:
        xf = float(x)
    except Exception:
        return False
    return math.isfinite(xf)


@dataclass
class CalibrationStore:
    path: Path

    def load(self) -> Dict[str, float]:
        if not self.path.exists():
            return {}
        with self.path.open("r") as f:
            data = yaml.safe_load(f) or {}
            if not isinstance(data, dict):
                raise ValueError("calibration file must be a mapping of id -> float")
            out: Dict[str, float] = {}
            for k, v in data.items():
                if not _is_finite_number(v):
                    raise ValueError(f"invalid offset for {k}")
                out[str(k)] = float(v)
            return out

    def save(self, offsets: Dict[str, float]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Prefer atomic write; fall back to direct write if temp files are restricted (e.g., OneDrive)
        try:
            with NamedTemporaryFile("w", delete=False, dir=str(self.path.parent)) as tmp:
                yaml.safe_dump(offsets, tmp)
                tmp_path = Path(tmp.name)
            os.replace(tmp_path, self.path)
        except Exception:
            # Fallback: direct write
            with self.path.open("w") as f:
                yaml.safe_dump(offsets, f)


@dataclass
class CalibrationService:
    store: CalibrationStore
    _offsets: Dict[str, float] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def initialize(self) -> None:
        with self._lock:
            self._offsets = self.store.load()

    def get(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._offsets)

    def set(self, partial: Dict[str, float]) -> Dict[str, float]:
        for k, v in partial.items():
            if not _is_finite_number(v):
                raise ValueError(f"invalid offset for {k}")
        with self._lock:
            new_map = dict(self._offsets)
            new_map.update({k: float(v) for k, v in partial.items()})
            self.store.save(new_map)
            self._offsets = new_map
            return dict(new_map)

    def zero(self, sensor_id: str, raw_value: float) -> float:
        if not _is_finite_number(raw_value):
            raise ValueError("raw value must be finite")
        offset = -float(raw_value)
        with self._lock:
            new_map = dict(self._offsets)
            new_map[sensor_id] = offset
            self.store.save(new_map)
            self._offsets = new_map
            return offset

    def zero_all(self, raw_map: Dict[str, float]) -> Dict[str, float]:
        # Only apply numeric entries
        new_offsets: Dict[str, float] = {}
        for sid, val in raw_map.items():
            if _is_finite_number(val):
                new_offsets[sid] = -float(val)
        with self._lock:
            new_map = dict(self._offsets)
            new_map.update(new_offsets)
            self.store.save(new_map)
            self._offsets = new_map
            return dict(new_map)

    def reset(self) -> Dict[str, float]:
        """Clear all offsets (equivalent to setting every offset to 0.0)."""
        with self._lock:
            new_map: Dict[str, float] = {}
            self.store.save(new_map)
            self._offsets = new_map
            return dict(new_map)
