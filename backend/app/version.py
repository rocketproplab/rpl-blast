from __future__ import annotations

from pathlib import Path


def get_version() -> str:
    ver_file = Path(__file__).resolve().parents[0] / "VERSION"
    try:
        return ver_file.read_text().strip()
    except Exception:
        return "0.0.0"

