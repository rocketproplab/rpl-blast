from __future__ import annotations

from pathlib import Path
import sys


# Resolve repository root from this file location
REPO_ROOT = Path(__file__).resolve().parents[3]

# Use the current frontend structure
FRONTEND_TEMPLATES = REPO_ROOT / "frontend" / "app" / "templates"
FRONTEND_CONFIG_YAML = REPO_ROOT / "frontend" / "app" / "config.yaml"
FRONTEND_CONFIG_CI_YAML = REPO_ROOT / "frontend" / "app" / "config.ci.yaml"
FRONTEND_STATIC = REPO_ROOT / "frontend" / "app" / "static"


def assert_legacy_layout() -> None:
    """Fail fast if expected legacy layout is not found."""
    missing = []
    if not FRONTEND_TEMPLATES.exists():
        missing.append(str(FRONTEND_TEMPLATES))
    if not FRONTEND_STATIC.exists():
        missing.append(str(FRONTEND_STATIC))
    # For config, accept either the main config or CI config
    if not FRONTEND_CONFIG_YAML.exists() and not FRONTEND_CONFIG_CI_YAML.exists():
        missing.append(f"{FRONTEND_CONFIG_YAML} or {FRONTEND_CONFIG_CI_YAML}")
    if missing:
        msg = "FATAL: missing required frontend paths: " + ", ".join(missing)
        print(msg, file=sys.stderr)
        raise SystemExit(1)


def get_config_path() -> Path:
    """Get the appropriate config file path, preferring main config over CI config."""
    if FRONTEND_CONFIG_YAML.exists():
        return FRONTEND_CONFIG_YAML
    elif FRONTEND_CONFIG_CI_YAML.exists():
        return FRONTEND_CONFIG_CI_YAML
    else:
        raise SystemExit(f"FATAL: no config file found at {FRONTEND_CONFIG_YAML} or {FRONTEND_CONFIG_CI_YAML}")
