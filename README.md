# RPL‑BLAST

**Big Launch Analysis & Stats Terminal** — a ground‑side web application for real‑time rocket sensor telemetry display, logging, and calibration.

BLAST reads data from either a built‑in simulator or a serial‑connected flight computer, applies calibration offsets, and serves live dashboards in the browser using Plotly charts. All data is logged to disk in JSONL and CSV formats for post‑run analysis.

> New to the project? Start with the onboarding guide: [ONBOARDING.md](ONBOARDING.md).

---

## Quick Start

### Option A — One‑Click Scripts (No Python Required)

The scripts in `scripts/` use [micromamba](https://mamba.readthedocs.io/en/latest/user_guide/micromamba.html) to install a project‑scoped Python environment at `.venv`. No global changes are made.

**macOS**
```bash
# One‑time setup (downloads micromamba + creates .venv + installs deps)
scripts/Setup Mac.command

# Start the app
scripts/Start App.command
```
> If macOS blocks the scripts, run `bash scripts/fix_permissions_mac.sh` first.

**Windows**
```powershell
# One‑time setup
scripts\setup_win.bat

# Start the app
scripts\start_win.bat
```

**Uninstall** (removes `.venv` and the local micromamba — nothing global)
- macOS: `scripts/Uninstall Mac.command`
- Windows: `scripts\uninstall_win.bat`

### Option B — Manual Setup (Conda / pip)

```bash
# Create and activate a Conda environment
conda env create -f environment.yaml
conda activate RPL

# Or use pip directly in a venv
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate    # macOS / Linux
pip install -r requirements.txt
```

### Running the App

```bash
uvicorn backend.app.main:app --reload
```
Open **http://127.0.0.1:8000** in your browser.

You can customize the host and port via environment variables `HOST` and `PORT` when using the one‑click scripts.

---

## Dashboard Pages

| Route               | Page                      | Description |
|----------------------|---------------------------|-------------|
| `/`                  | Home / Dashboard          | Navigation hub with cards linking to each sensor page. |
| `/pressure`          | Pressure Transducers      | Live line plots (per‑sensor subplots), an aggregate overlay plot, and stats cards (latest, avg, rate, max). Includes calibration controls. |
| `/thermocouples`     | Thermocouples & Load Cells| Subplots and aggregate views for TCs and LCs, with stats and calibration. |
| `/valves`            | Flow Control Valves       | Grid of valve actual/expected state indicators (on/off). |

Every page includes a **Serial Monitor** toggle button that opens an in‑page console showing raw data packets as they arrive.

---

## Configuration

BLAST uses a **layered configuration system**:

1. **`frontend/app/config.base.yaml`** — Base / shared settings (checked into git). Defines all sensor names, IDs, colors, value ranges, warning/danger thresholds, serial port defaults, and valve definitions.
2. **`frontend/app/config.user.yaml`** — User overrides (git‑ignored). Create this by copying `config.user.yaml.example`. Any keys here are deep‑merged on top of the base config.
3. **`frontend/app/config.ci.yaml`** — CI fallback config used by GitHub Actions.

### Key Config Fields

```yaml
data_source: "simulator"          # "simulator" or "serial"
serial_port: "COM4"               # e.g., "/dev/cu.usbmodem1301" on Mac
serial_baudrate: 115200

subpage1:
  pressure_transducers:           # List of {name, id, color, min_value, max_value, warning_value, danger_value}
subpage2:
  thermocouples: [...]
  load_cells: [...]
subpage3:
  flow_control_valves: [...]      # List of {name, id}
```

### Switching Data Sources

1. Create or edit `frontend/app/config.user.yaml`
2. Set `data_source: "simulator"` for testing or `data_source: "serial"` for real hardware
3. For serial mode, set the correct `serial_port` for your OS

---

## API Reference

### Telemetry Data
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/data` | Returns the latest sensor snapshot. Accepts `?type=all\|pt\|tc\|lc\|fcv_actual\|fcv_expected` to filter. |
| `GET`  | `/data?type=pt` | Returns only pressure transducer values. |

**Response shape:**
```json
{
  "value": { "pt": [...], "tc": [...], "lc": [...], "fcv_actual": [...], "fcv_expected": [...], "timestamp": 1234567890.0 },
  "timestamp": 1234567890.0,
  "raw": { ... },
  "adjusted": { ... },
  "offsets": { "pt1": 0.0, ... }
}
```
- `value` and `adjusted` are identical (kept for legacy JS compatibility).
- `raw` contains pre‑offset sensor values.

### Calibration
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/offsets` | Returns `{ "offsets": { sensor_id: float } }` |
| `PUT`  | `/api/offsets` | Partial update — body is `{ sensor_id: value }`, merged with existing offsets. |
| `POST` | `/api/zero/{sensor_id}` | Sets offset to negate the current raw reading (zeroes the sensor). |
| `POST` | `/api/zero_all` | Zeroes all sensors using their current raw values. |
| `POST` | `/api/reset_offsets` | Resets all offsets to `0.0`. |

### Serial Monitor
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/serial/logs?after=-1` | Returns buffered raw serial lines. Pass `after=<index>` for incremental polling. |

### Browser Telemetry
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/browser_heartbeat` | Receives heartbeat pings from the browser monitor script. |
| `POST` | `/api/browser_status` | Receives browser tab status updates. |

### Health & Diagnostics
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/healthz` | Overall health, data lag, version, log error count. |
| `GET`  | `/api/logging/status` | Detailed stats from the logging subsystem (performance, freeze detection, error recovery). |

---

## Project Structure

```
rpl-blast/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app factory, startup/shutdown, reader loop, healthz
│   │   ├── VERSION                  # Semantic version string (currently 0.1.0)
│   │   ├── version.py               # Version helper
│   │   ├── config/
│   │   │   ├── loader.py            # Layered YAML config loading + Settings dataclass
│   │   │   └── paths.py             # Resolved filesystem paths (templates, static, configs)
│   │   ├── routers/
│   │   │   ├── data.py              # /data, /api/serial/logs, browser heartbeat endpoints
│   │   │   ├── calibration.py       # /api/offsets, /api/zero/*, /api/reset_offsets
│   │   │   └── pages.py             # HTML page routes (/, /pressure, /thermocouples, /valves)
│   │   ├── schemas/
│   │   │   └── data.py              # Pydantic DataEnvelope model
│   │   ├── services/
│   │   │   ├── data_source.py       # SimulatorSource + SerialSource (DataSource protocol)
│   │   │   ├── calibration.py       # CalibrationStore (YAML persistence) + CalibrationService
│   │   │   ├── reading_cache.py     # Thread-safe LatestReadingCache
│   │   │   └── serial_monitor.py    # SerialMonitorBuffer (ring buffer for raw packets)
│   │   ├── logging/
│   │   │   ├── logger_manager.py    # Orchestrates all log writers (JSONL, CSV, run dirs)
│   │   │   ├── event_logger.py      # Structured event logging (startup, shutdown, source changes)
│   │   │   ├── serial_logger.py     # Serial connection & data read logging
│   │   │   ├── performance_monitor.py # Timer-based latency & throughput tracking
│   │   │   ├── error_recovery.py    # Error tracking with health checks
│   │   │   └── freeze_detector.py   # Heartbeat-based stall detection
│   │   └── state/                   # (gitignored runtime state)
│   ├── state/
│   │   └── calibration_offsets.yaml # Persisted calibration offsets
│   └── tests/
│       ├── test_app_basic.py        # Health, pages, /data shape, type filtering
│       └── test_calibration_api.py  # Offset CRUD, zero, reset
│
├── frontend/
│   ├── app/
│   │   ├── config.base.yaml         # Base configuration (sensors, serial, boundaries)
│   │   ├── config.ci.yaml           # CI-specific config
│   │   ├── config.user.yaml.example # Template for local overrides
│   │   ├── logging_config.yaml      # Python logging handler config
│   │   ├── templates/
│   │   │   ├── base.html            # Jinja2 base layout (header, nav, serial monitor btn)
│   │   │   ├── index.html           # Dashboard home with nav cards
│   │   │   ├── pressure.html        # PT subplots, aggregate, stats, calibration
│   │   │   ├── thermocouples.html   # TC/LC subplots, aggregate, stats, calibration
│   │   │   └── valves.html          # Valve state grid
│   │   └── static/
│   │       ├── css/
│   │       │   └── dashboard.css    # All page styles
│   │       ├── js/
│   │       │   ├── get_data.js      # Shared /data polling helper
│   │       │   ├── pt_config.js     # PT Plotly layout config
│   │       │   ├── pt_line.js       # PT per-sensor subplot charts
│   │       │   ├── pt_agg.js        # PT aggregate overlay chart
│   │       │   ├── pt_stats.js      # PT stats card updater
│   │       │   ├── tc_agg.js        # TC aggregate chart
│   │       │   ├── tc_subplots.js   # TC per-sensor subplots
│   │       │   ├── tc_stats.js      # TC stats updater
│   │       │   ├── lc_agg.js        # LC aggregate chart
│   │       │   ├── lc_subplots.js   # LC per-sensor subplots
│   │       │   ├── lc_stats.js      # LC stats updater
│   │       │   ├── calibration.js   # Calibration UI controls
│   │       │   ├── valves.js        # Valve state rendering
│   │       │   ├── serial_monitor.js# Serial Monitor panel (toggle, auto-scroll, polling)
│   │       │   ├── browser_monitor.js# Browser heartbeat/status reporter
│   │       │   └── charts.js        # (Minimal chart utilities)
│   │       └── fonts/               # Custom fonts
│   └── logs/                        # Runtime logs (per-run dirs, data.jsonl, CSV, offsets)
│
├── scripts/                         # One-click setup/start/uninstall for macOS & Windows
├── tools/
│   └── smoke_test_fastapi.py        # CI smoke test (exercises /healthz, /data, calibration)
├── .github/workflows/ci.yml         # GitHub Actions CI (Python 3.9, smoke test + pytest)
├── requirements.txt                 # Python dependencies
├── LICENSE                          # MIT License
└── ONBOARDING.md                    # In-depth onboarding guide
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend framework | [FastAPI](https://fastapi.tiangolo.com/) 0.115 + [Uvicorn](https://www.uvicorn.org/) |
| Data validation | [Pydantic](https://docs.pydantic.dev/) v2 |
| Templating | [Jinja2](https://jinja.palletsprojects.com/) (served by FastAPI) |
| Charting | [Plotly.js](https://plotly.com/javascript/) (CDN) |
| Serial I/O | [PySerial](https://pyserial.readthedocs.io/) |
| Config | [PyYAML](https://pyyaml.org/) (layered base + user) |
| System monitoring | [psutil](https://github.com/giampaolo/psutil) |
| Testing | [pytest](https://docs.pytest.org/) + FastAPI `TestClient` |
| CI | GitHub Actions |
| License | MIT |

---

## CI / Testing

CI runs on every push/PR to `main` via `.github/workflows/ci.yml`:

1. **Install** — Python 3.9, pip deps from `requirements.txt` (cached)
2. **Smoke test** — `python tools/smoke_test_fastapi.py` (forces simulator mode via `FORCE_SIMULATOR_MODE=1`, exercises healthz, /data, calibration endpoints)
3. **Pytest** — `pytest -q backend/tests` (health, page routes, data shape, calibration CRUD)

### Running Tests Locally

```bash
# Smoke test
python tools/smoke_test_fastapi.py

# Unit tests
pytest -q backend/tests
```

---

## Logging System

BLAST has a comprehensive logging subsystem under `backend/app/logging/`:

- **LoggerManager** — Creates a timestamped run directory under `frontend/logs/`, writes JSONL data logs and CSV data logs, and produces a run summary on shutdown.
- **EventLogger** — Structured logging for system events (startup, shutdown, data source changes, state transitions).
- **SerialLogger** — Logs serial connection attempts, successes, failures, and per‑read results.
- **PerformanceMonitor** — Timer‑based latency measurement for data reads and API calls; tracks data lag.
- **ErrorRecovery** — Counts and categorizes errors; exposes a health check.
- **FreezeDetector** — Heartbeat‑based watchdog that detects stalled loops (data acquisition, serial communication, API requests).

All diagnostics are queryable at runtime via `GET /api/logging/status`.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Serial port not found | Check `serial_port` in your `config.user.yaml`. On Mac, look for `/dev/cu.usbmodem*`; on Windows, check Device Manager for the COM port. |
| macOS blocks scripts | Run `bash scripts/fix_permissions_mac.sh` |
| `FATAL: missing key` on startup | Your config file is missing a required section. Compare against `config.base.yaml`. |
| Data shows all zeros | You may be in serial mode with no hardware connected. Switch to `data_source: "simulator"`. |
| Calibration file write errors | Check filesystem permissions on `frontend/logs/`. OneDrive‑synced folders can cause atomic‑write failures (the app falls back to direct writes). |

---

## License

MIT — see [LICENSE](LICENSE).
