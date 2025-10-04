from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException, Request


router = APIRouter()


@router.get("/api/offsets")
def get_offsets(request: Request) -> Dict[str, Dict[str, float]]:
    calib = request.app.state.calibration
    return {"offsets": calib.get()}


@router.put("/api/offsets")
def put_offsets(request: Request, body: Dict[str, Any] = Body(...)) -> Dict[str, Dict[str, float]]:
    calib = request.app.state.calibration
    try:
        merged = calib.set({k: float(v) for k, v in body.items()})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"offsets": merged}


@router.post("/api/zero/{sensor_id}")
def post_zero_sensor(sensor_id: str, request: Request) -> Dict[str, Any]:
    snap = request.app.state.cache.get_full()
    if not snap:
        raise HTTPException(status_code=503, detail="no live data")
    raw = snap.get("raw") or {}

    # Determine latest raw value for the sensor id across pt/tc/lc
    settings = request.app.state.settings
    value = _lookup_raw_by_id(raw, sensor_id, settings)
    if value is None:
        raise HTTPException(status_code=404, detail="unknown sensor")
    try:
        offset = request.app.state.calibration.zero(sensor_id, float(value))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": sensor_id, "offset": offset}


@router.post("/api/zero_all")
def post_zero_all(request: Request) -> Dict[str, Dict[str, float]]:
    snap = request.app.state.cache.get_full()
    if not snap:
        raise HTTPException(status_code=503, detail="no live data")
    raw = snap.get("raw") or {}
    settings = request.app.state.settings
    raw_by_id = _flatten_raw_by_id(raw, settings)
    merged = request.app.state.calibration.zero_all(raw_by_id)
    return {"offsets": merged}


@router.post("/api/reset_offsets")
def post_reset_offsets(request: Request) -> Dict[str, Dict[str, float]]:
    try:
        merged = request.app.state.calibration.reset()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"offsets": merged}


def _lookup_raw_by_id(raw: Dict[str, Any], sid: str, settings) -> float | None:
    # Search pt, tc, lc for matching id
    for series_key, ids in (
        ("pt", [pt.get("id") for pt in settings.PRESSURE_TRANSDUCERS]),
        ("tc", [tc.get("id") for tc in settings.THERMOCOUPLES]),
        ("lc", [lc.get("id") for lc in settings.LOAD_CELLS]),
    ):
        values = raw.get(series_key) or []
        for i, vid in enumerate(ids):
            if vid == sid and i < len(values):
                try:
                    return float(values[i])
                except Exception:
                    return None
    return None


def _flatten_raw_by_id(raw: Dict[str, Any], settings) -> Dict[str, float]:
    out: Dict[str, float] = {}
    mapping = (
        ("pt", [pt.get("id") for pt in settings.PRESSURE_TRANSDUCERS]),
        ("tc", [tc.get("id") for tc in settings.THERMOCOUPLES]),
        ("lc", [lc.get("id") for lc in settings.LOAD_CELLS]),
    )
    for key, ids in mapping:
        values = raw.get(key) or []
        for i, sid in enumerate(ids):
            if sid is None or i >= len(values):
                continue
            try:
                out[sid] = float(values[i])
            except Exception:
                pass
    return out
