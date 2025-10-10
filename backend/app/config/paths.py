from __future__ import annotations

from pathlib import Path
import sys


# Resolve repository root from this file location
REPO_ROOT = Path(__file__).resolve().parents[3]

LEGACY_APP_DIR = REPO_ROOT / "BLAST_web plotly subplot" / "app"

# Prefer new frontend/app for templates and config when present
FRONTEND_TEMPLATES = REPO_ROOT / "frontend" / "app" / "templates"
if not FRONTEND_TEMPLATES.exists():
    FRONTEND_TEMPLATES = LEGACY_APP_DIR / "templates"

FRONTEND_CONFIG_YAML = REPO_ROOT / "frontend" / "app" / "config.yaml"
if not FRONTEND_CONFIG_YAML.exists():
    FRONTEND_CONFIG_YAML = LEGACY_APP_DIR / "config.yaml"

# Static: use new path only when migration sentinel exists; else serve legacy static
FRONTEND_STATIC = REPO_ROOT / "frontend" / "app" / "static"
if (not FRONTEND_STATIC.exists()) or (not (FRONTEND_STATIC / ".migrated").exists()):
    FRONTEND_STATIC = LEGACY_APP_DIR / "static"


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
