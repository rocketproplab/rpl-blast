# RPL‑BLAST Onboarding (What it does)

This document states plainly what BLAST does today and how to use it.

## Objectives
- Provide a small web app that reads telemetry from either a built‑in simulator or a serial port and serves it to browser dashboards.
- Let users apply simple calibration offsets server‑side (zero or set values) and persist them.
- Write run‑scoped JSONL logs of data and basic events for later inspection.

## Audience & Prerequisites
- Audience: firmware (frames over serial), backend (API/service work), data/analysis, and DevOps for CI.
- Requirements: Python 3.9, Conda/micromamba, Git. Serial testing requires hardware access and OS permissions.

## System Context
```
Sensors → Avionics FW → USB/UART → BLAST on laptop → Browser dashboards
                                        ↳ JSONL logs on disk
```
- Inputs come from firmware (serial JSON lines) or the simulator. BLAST does not control hardware.

## Architecture & Modules
- Backend (`backend/app`):
  - Routers: `/data` (telemetry JSON), calibration endpoints, simple page routes.
  - Services: data sources (`SimulatorSource`, `SerialSource`), calibration store (`calibration_offsets.yaml`), in‑memory cache.
  - Logging: writes JSONL files for data/events/performance/errors; also a `system.log`.
- Frontend (`frontend/app`):
  - Jinja templates and Plotly assets; reads `/data`; calls calibration APIs.
- Not included: mission state machine, GNC, uplink/downlink; BLAST is ground‑side display/logging only.

## Tech Stack & Repo Layout
- Python 3.9, FastAPI, Plotly, PySerial, PyYAML, pytest.
- Entrypoint: `uvicorn backend.app.main:app --reload`.
- Key paths: `backend/app/*`, `frontend/app/*`, `frontend/logs/`, `frontend/app/config.yaml`.

## Setup & Running
Option A — One‑click (no global install)
```bash
# macOS (double‑click from Finder)
scripts/Setup Mac.command   # one‑time env setup (micromamba)
scripts/Start App.command   # starts uvicorn with the local env

# Windows (PowerShell; double‑click)
scripts\setup_win.bat       # one‑time env setup (micromamba)
scripts\start_win.bat       # starts uvicorn with the local env
```

Option B — Command line
```bash
conda env create -f environment.yaml
conda activate RPL
uvicorn backend.app.main:app --reload
# Open http://127.0.0.1:8000
```
- Simulator vs serial and `serial_port` are set in `frontend/app/config.yaml`.
- Port discovery: `python serial_test.py`.

## Interfaces & Data
- `GET /data?type=all|pt|tc|lc|...`
  - Returns: `value` (adjusted data with `timestamp`), top‑level `timestamp`, plus `raw`, `adjusted`, and `offsets` maps.
  - Compatibility: `value == adjusted`; `value.timestamp` is kept for existing JS.
- Calibration:
  - `GET /api/offsets` → `{ offsets }`
  - `PUT /api/offsets` with `{ id: float }` (partial) → merged `{ offsets }`
  - `POST /api/zero/{sensor_id}`, `POST /api/zero_all`, `POST /api/reset_offsets`
- Sensor IDs and series order come from `frontend/app/config.yaml`.
- SerialSource expects one JSON line per frame with a `{"value": {"pt": [...], "tc": [...], "lc": [...], "fcv": [...]}}` shape. Confirm with firmware.

- Health & logging status:
  - `GET /healthz` → overall health, last data timestamp, lag_ms, version.
  - `GET /api/logging/status` → JSON summary of logging/performance/freeze detector statistics.

## CI and Tests
- CI: GitHub Actions installs deps, runs a smoke script, then runs pytest (`.github/workflows/ci.yml`).
- Tests: a small basic pytest suite exists under `backend/tests`; it’s minimal and not comprehensive (no lint/coverage gates).

## Reliability Notes
- Reader loop runs at a fixed interval and updates an in‑memory snapshot.
- Logging manager creates a new directory per run and attempts a `latest` symlink (may be unsupported on some systems).
- Health/performance metrics are recorded to logs; they do not enforce safety.

## Operations (Typical Use)
- Edit `frontend/app/config.yaml` (choose data source and serial port).
- Start the app, open the site, verify `/data` responds, and use zero/offset controls.
- Logs are written under `frontend/logs/<timestamp>/`.

## Short Roadmap
- Lock down serial frame schema/units with firmware
  - Define a simple ICD (keys, types, units, sample rate, timestamp semantics) and version it. Update `SerialSource._parse_and_update` to match, and add a small shape check so malformed frames are ignored without crashing.
- Move some sensor processing from Arduino to the laptop
  - Shift lightweight conversions from ADC voltage to engineering units (e.g., PT volts → PSI, TC volts → °C, LC volts → force/mass) and offset math into BLAST. Centralizing these curves/tables on the laptop reduces MCU load and lets us update conversion parameters without reflashing firmware.
- Explore Rust or C for serial I/O or other hot paths
  - Prototype a tiny reader (line parsing + ring buffer) exposed to Python via FFI or a local socket. Benchmark at expected rates and only adopt if we see real CPU/latency gains over the current Python path.
- Exercise serial on bench hardware and document permissions/rates
  - Validate sustained read rates (baseline ~10 Hz via `update_interval_s`), OS permissions (e.g., macOS `/dev/cu.*`, Windows COM ports), and failure behavior (disconnects, partial frames). Capture a short “serial setup” note in docs.
- Add focused tests around calibration math and serial parsing
  - Unit tests: zero/zero_all arithmetic, partial updates, invalid payload handling. Parser tests: drop bad lines, keep last good snapshot, and confirm boolean FCV handling.

Have something else or see an issue? Add your item here and open a PR.

- Wire and test remaining sensor pages
  - Ensure each page/template and its JS binds to the right `/data` keys (e.g., load cells, valve states). Verify live updates, resizing, and navigation links. Add any missing routes as needed.

- Add an accelerator page (if/when data exists)
  - If accelerometer data is available from firmware/config, add a simple page and JS module to plot it (e.g., magnitude and per‑axis traces). If not yet available, leave a stub and simulator support for later.

- Page style improvements (incremental)
  - Make layout and typography more consistent, improve spacing and responsiveness, and unify Plotly configs (fonts, colors). Keep changes minimal and avoid blocking functional work.

## Onboarding (First Week)
- Get access to the repo/CI; create the Conda env and run with the simulator.
- Inspect `/data`, change an offset via API/UI, and watch values change.
- If hardware is available, switch to serial and confirm frames parse; otherwise, stay on simulator.



## Quick Links
- Run: `uvicorn backend.app.main:app --reload` → http://127.0.0.1:8000
- Config: `frontend/app/config.yaml`
- Key files: `backend/app/main.py`, `backend/app/routers/{data,calibration,pages}.py`, `backend/app/services/*`
- Logs: `frontend/logs/`
- CI: `.github/workflows/ci.yml`
