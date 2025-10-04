from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml


@dataclass
class Settings:
    # Data source settings
    DATA_SOURCE: str
    SERIAL_PORT: str
    SERIAL_BAUDRATE: int

    # Sensor definitions
    PRESSURE_TRANSDUCERS: List[Dict[str, Any]]
    NUM_PRESSURE_TRANSDUCERS: int
    THERMOCOUPLES: List[Dict[str, Any]]
    NUM_THERMOCOUPLES: int
    LOAD_CELLS: List[Dict[str, Any]]
    NUM_LOAD_CELLS: int
    FLOW_CONTROL_VALVES: List[Dict[str, Any]]
    NUM_FLOW_CONTROL_VALVES: int

    # Boundaries
    TEMPERATURE_BOUNDARIES: Dict[str, List[float]]
    PRESSURE_BOUNDARIES: Dict[str, List[float]]
    LOAD_CELL_BOUNDARIES: Dict[str, List[float]]


def _require_key(obj: Dict[str, Any], key: str) -> Any:
    if key not in obj:
        print(f"FATAL: missing key '{key}' in config.yaml", file=sys.stderr)
        raise SystemExit(1)
    return obj[key]


def load_settings(path: Path) -> Settings:
    try:
        with path.open("r") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"FATAL: missing config at {path}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as e:
        print(f"FATAL: invalid config at {path}: {e}", file=sys.stderr)
        raise SystemExit(1)

    # Core
    data_source = _require_key(data, "data_source")
    serial_port = _require_key(data, "serial_port")
    serial_baudrate = _require_key(data, "serial_baudrate")

    # Subpages
    sp1 = _require_key(data, "subpage1")
    sp2 = _require_key(data, "subpage2")
    sp3 = _require_key(data, "subpage3")

    pts = _require_key(sp1, "pressure_transducers")
    tcs = _require_key(sp2, "thermocouples")
    lcs = _require_key(sp2, "load_cells")
    fcvs = _require_key(sp3, "flow_control_valves")

    # Boundaries (replicate legacy constants)
    temperature_boundaries = {
        "safe": [0, 600],
        "warning": [600, 800],
        "danger": [800, 1000],
    }
    pressure_boundaries = {
        "safe": [0, 500],
        "warning": [500, 750],
        "danger": [750, 1000],
    }
    load_cell_boundaries = {
        "safe": [0, 250],
        "warning": [250, 400],
        "danger": [400, 500],
    }

    settings = Settings(
        DATA_SOURCE=str(data_source),
        SERIAL_PORT=str(serial_port),
        SERIAL_BAUDRATE=int(serial_baudrate),
        PRESSURE_TRANSDUCERS=list(pts),
        NUM_PRESSURE_TRANSDUCERS=len(pts),
        THERMOCOUPLES=list(tcs),
        NUM_THERMOCOUPLES=len(tcs),
        LOAD_CELLS=list(lcs),
        NUM_LOAD_CELLS=len(lcs),
        FLOW_CONTROL_VALVES=list(fcvs),
        NUM_FLOW_CONTROL_VALVES=len(fcvs),
        TEMPERATURE_BOUNDARIES=temperature_boundaries,
        PRESSURE_BOUNDARIES=pressure_boundaries,
        LOAD_CELL_BOUNDARIES=load_cell_boundaries,
    )
    return settings

