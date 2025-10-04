from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Protocol, Tuple, Union
import random

from ..config.loader import Settings


class DataSource(Protocol):
    def initialize(self) -> None: ...
    def read_once(self) -> Tuple[Dict[str, Union[List[float], List[bool]]], float]: ...
    def shutdown(self) -> None: ...


@dataclass
class SimulatorSource:
    settings: Settings
    update_interval_s: float = 0.1

    def initialize(self) -> None:
        return None

    def _rand_in_range(self, min_v: float, max_v: float) -> float:
        # Bias toward normal range, occasionally spike
        r = random.random()
        if r < 0.02:
            return random.uniform(max_v * 0.8, max_v * 0.95)
        if r < 0.05:
            return random.uniform(max_v * 0.5, max_v * 0.7)
        return random.uniform(min_v + max_v * 0.1, max_v * 0.4)

    def read_once(self) -> Tuple[Dict[str, Union[List[float], List[bool]]], float]:
        now = time.time()
        # Build values consistent with legacy SensorData.to_dict()
        pt = [
            self._rand_in_range(ptc.get("min_value", 0.0), ptc.get("max_value", 1000.0))
            for ptc in self.settings.PRESSURE_TRANSDUCERS
        ]
        tc = [
            self._rand_in_range(tcc.get("min_value", 0.0), tcc.get("max_value", 1000.0))
            for tcc in self.settings.THERMOCOUPLES
        ]
        lc = [
            self._rand_in_range(lcc.get("min_value", 0.0), lcc.get("max_value", 1000.0))
            for lcc in self.settings.LOAD_CELLS
        ]
        fcv_actual = [False] * self.settings.NUM_FLOW_CONTROL_VALVES
        fcv_expected = [False] * self.settings.NUM_FLOW_CONTROL_VALVES

        value = {
            "tc": tc,
            "pt": pt,
            "fcv_actual": fcv_actual,
            "fcv_expected": fcv_expected,
            "lc": lc,
            "timestamp": now,
        }
        return value, now

    def shutdown(self) -> None:
        return None


@dataclass
class SerialSource:
    settings: Settings

    def initialize(self) -> None:
        # Placeholder: serial connection setup would occur here.
        # Intentionally unimplemented for simulator-only bringup.
        return None

    def read_once(self) -> Tuple[Dict[str, Union[List[float], List[bool]]], float]:
        # Placeholder: implement parsing and mapping to legacy dict shape.
        raise NotImplementedError("SerialSource.read_once is not implemented in simulator-only mode")

    def shutdown(self) -> None:
        return None
