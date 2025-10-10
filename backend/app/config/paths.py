from __future__ import annotations

from pathlib import Path
import sys


# Resolve repository root from this file location
REPO_ROOT = Path(__file__).resolve().parents[3]

# Use the current frontend structure
FRONTEND_TEMPLATES = REPO_ROOT / "frontend" / "app" / "templates"
FRONTEND_CONFIG_YAML = REPO_ROOT / "frontend" / "app" / "config.yaml"
FRONTEND_STATIC = REPO_ROOT / "frontend" / "app" / "static"


def assert_legacy_layout() -> None:
    """Fail fast if expected legacy layout is not found."""
    missing = []
    if not FRONTEND_TEMPLATES.exists():
        missing.append(str(FRONTEND_TEMPLATES))
    if not FRONTEND_STATIC.exists():
        missing.append(str(FRONTEND_STATIC))
    if not FRONTEND_CONFIG_YAML.exists():
        missing.append(str(FRONTEND_CONFIG_YAML))
    if missing:
        msg = "FATAL: missing required frontend paths: " + ", ".join(missing)
        print(msg, file=sys.stderr)
        raise SystemExit(1)
