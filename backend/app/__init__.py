"""FastAPI application package for RPL‑BLAST.

Serves the same pages and `/data` endpoint as the prior Flask app,
now using the FastAPI backend under `backend/` and templates/static
from `frontend/app/`. The simulator is the default data source; serial
support is wired behind the same interface.
"""
