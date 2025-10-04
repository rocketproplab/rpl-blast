# Legacy Flask App (Deprecated during FastAPI migration)

This directory contains the original Flask application. The active server is now the FastAPI app under `backend/app/`.

What still lives here:
- `templates/` and `static/` are intentionally reused by FastAPI (do not remove).
- `config.yaml` remains the single source of truth for sensor definitions.

What is considered legacy and not used by FastAPI:
- `routes/` (Flask blueprints)
- `data_sources/` (legacy simulator/serial), superseded by `backend/app/services/data_source.py`
- `logging/` (custom stack) — FastAPI uses a minimal JSON log for sensor data; legacy log modules may be selectively reused later.

Cleanup guidance:
- Do not delete templates or static assets.
- When in doubt, keep files and mark them here; remove only after parity is confirmed and tests pass.

