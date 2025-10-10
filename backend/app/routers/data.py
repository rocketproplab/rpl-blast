from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import time

from ..schemas.data import DataEnvelope


router = APIRouter()


@router.get("/data", name="data")
def get_data(request: Request, type: str = "all"):
    cache = request.app.state.cache
    snap = cache.get_full()
    if not snap:
        return JSONResponse({"value": None})

    ts = snap.get("timestamp")
    adjusted = snap.get("adjusted") or snap.get("value") or {}

    # Mirror Flask behavior: whole value dict, or a single key
    if type != "all":
        payload = {type: adjusted.get(type, "KEY_NOT_FOUND")}
    else:
        payload = dict(adjusted)

    env = DataEnvelope(
        value=payload,
        timestamp=ts,
        raw=snap.get("raw"),
        adjusted=snap.get("adjusted"),
        offsets=snap.get("offsets"),
    )
    return JSONResponse(env.model_dump())


@router.post("/api/browser_heartbeat")
async def browser_heartbeat(request: Request):
    """Receive browser heartbeat to monitor user activity"""
    try:
        data = await request.json()
        # Log or store heartbeat data if needed for monitoring
        return JSONResponse({"status": "ok", "timestamp": time.time()})
    except Exception:
        return JSONResponse({"status": "ok", "timestamp": time.time()})


@router.post("/api/browser_status") 
async def browser_status(request: Request):
    """Receive browser status updates"""
    try:
        data = await request.json()
        # Log or store status data if needed for monitoring
        return JSONResponse({"status": "ok", "timestamp": time.time()})
    except Exception:
        return JSONResponse({"status": "ok", "timestamp": time.time()})
