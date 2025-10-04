from __future__ import annotations

from pathlib import Path
import sys


# Resolve repository root from this file location
REPO_ROOT = Path(__file__).resolve().parents[3]

# Legacy frontend app directory (keep as-is; includes spaces)
LEGACY_APP_DIRNAME = "BLAST_web plotly subplot"
LEGACY_APP_DIR = REPO_ROOT / LEGACY_APP_DIRNAME / "app"

FRONTEND_TEMPLATES = LEGACY_APP_DIR / "templates"
FRONTEND_STATIC = LEGACY_APP_DIR / "static"
FRONTEND_CONFIG_YAML = LEGACY_APP_DIR / "config.yaml"


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
        msg = "FATAL: missing required legacy paths: " + ", ".join(missing)
        print(msg, file=sys.stderr)
        raise SystemExit(1)

