from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict


class DataEnvelope(BaseModel):
    value: Optional[Dict[str, Any]]
    timestamp: Optional[float]
    raw: Optional[Dict[str, Any]] = None
    adjusted: Optional[Dict[str, Any]] = None
    offsets: Optional[Dict[str, float]] = None

    model_config = ConfigDict(extra="forbid")
