# RPL‑BLAST Onboarding Guide

Welcome to **BLAST** — the Big Launch Analysis & Stats Terminal. This document walks you through every layer of the system so you can get productive quickly, whether you're working on firmware integration, backend services, frontend dashboards, data analysis, or DevOps.

---

## Table of Contents

1. [What BLAST Does](#what-blast-does)
2. [System Context](#system-context)
3. [Prerequisites](#prerequisites)
4. [Setup & First Run](#setup--first-run)
5. [Architecture Overview](#architecture-overview)
6. [Configuration System](#configuration-system)
7. [Backend Deep Dive](#backend-deep-dive)
8. [Frontend Deep Dive](#frontend-deep-dive)
9. [Logging & Observability](#logging--observability)
10. [Serial Protocol & Firmware Interface](#serial-protocol--firmware-interface)
11. [Calibration System](#calibration-system)
12. [API Reference](#api-reference)
13. [CI & Testing](#ci--testing)
14. [First Week Checklist](#first-week-checklist)
15. [Short Roadmap](#short-roadmap)
16. [Quick Links](#quick-links)

---

## What BLAST Does

BLAST is a **ground‑side telemetry display and logging tool**. It:

- Reads sensor data from a flight computer over USB/UART serial, or generates simulated data for development.
- Applies user‑configurable calibration offsets server‑side (zero, set, reset).
- Serves real‑time browser dashboards with live Plotly charts for pressure transducers, thermocouples, load cells, and valve states.
- Provides a Serial Monitor panel on every page to inspect raw data packets.
- Writes structured JSONL and CSV logs partitioned by run for post‑test analysis.
- Exposes health, performance, and freeze‑detection diagnostics via API.

**What BLAST is not:** It does not control hardware, manage mission state, perform GNC, or handle uplink/downlink. It is read‑only ground‑side display and logging.

---

## System Context

```mermaid
flowchart LR
    A["Sensors"] --> B["Avionics Firmware"]
    B -->|USB / UART| C["BLAST\n(Python/FastAPI on laptop)"]
    C --> D["Browser Dashboards"]
    C --> E["JSONL + CSV logs on disk"]
    C --> F["/healthz & /api/logging/status"]

    classDef hardware fill:#e67e73,stroke:#b35a52,color:#fff
    classDef blast fill:#4a90d9,stroke:#2c5f8a,color:#fff
    classDef output fill:#50b86c,stroke:#2f7a42,color:#fff

    class A,B hardware
    class C blast
    class D,E,F output
```

- **Inputs:** JSON lines from firmware (one per frame) over a serial port, or internally generated simulator data.
- **Outputs:** HTML dashboards, REST API (JSON), disk logs.
- **Scope:** Passive observer — BLAST never sends commands to hardware.

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.9+ | Used by the backend (FastAPI + Uvicorn). |
| Git | For cloning the repo. |
| Conda or micromamba | The one‑click scripts use micromamba automatically; manual setup can use Conda. |
| Serial hardware (optional) | Only needed to test real serial data. Requires OS‑level port permissions. |
| Modern browser | Chrome, Firefox, or Edge for the dashboards. |

---

## Setup & First Run

### Option A — One‑Click Scripts (Recommended)

These scripts install micromamba locally, create a project‑scoped `.venv`, and install all Python deps from `requirements.txt`. No global changes.

**macOS:**
```bash
# One-time setup
scripts/Setup Mac.command       # double-click in Finder, or: bash scripts/setup_mac.sh

# Start the app
scripts/Start App.command       # or: bash scripts/start_mac.sh
```

If macOS Gatekeeper blocks execution:
```bash
bash scripts/fix_permissions_mac.sh
```

**Windows:**
```powershell
# One-time setup
scripts\setup_win.bat           # double-click, or: powershell scripts\setup_win.ps1

# Start the app
scripts\start_win.bat           # or: powershell scripts\start_win.ps1
```

**Uninstall** (removes `.venv` + local micromamba only):
- macOS: `scripts/Uninstall Mac.command`
- Windows: `scripts\uninstall_win.bat`

### Option B — Manual (Conda)

```bash
conda env create -f environment.yaml
conda activate RPL
uvicorn backend.app.main:app --reload
```

### Option C — Manual (pip + venv)

```bash
python -m venv .venv
# Activate:
#   Windows:  .venv\Scripts\activate
#   macOS:    source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

Once running, open **http://127.0.0.1:8000** in your browser.

---

## Architecture Overview

BLAST follows a clean **backend ↔ frontend** split, all served from a single FastAPI process.

```mermaid
flowchart TB
    subgraph APP["FastAPI App - main.py"]
        direction TB

        subgraph ROUTERS["Routers"]
            direction LR
            R1["data.py"]
            R2["calibration.py"]
            R3["pages.py"]
        end

        subgraph SERVICES["Services"]
            direction LR
            S1["DataSource"]
            S2["CalibrationService"]
            S3["ReadingCache"]
            S4["SerialMonitorBuffer"]
        end

        subgraph LOGGING["Logging Subsystem"]
            direction LR
            L1["LoggerManager"]
            L2["EventLogger"]
            L3["SerialLogger"]
            L4["PerfMonitor"]
            L5["ErrorRecovery"]
            L6["FreezeDetector"]
        end

        TEMPLATES["Jinja2 Templates + Plotly.js"]

        R1 --> S1
        R1 --> S3
        R2 --> S2
        R3 --> TEMPLATES
    end

    classDef router fill:#4a90d9,stroke:#2c5f8a,color:#fff
    classDef service fill:#50b86c,stroke:#2f7a42,color:#fff
    classDef logging fill:#9b59b6,stroke:#6c3483,color:#fff
    classDef ui fill:#e8a838,stroke:#b07c20,color:#fff

    class R1,R2,R3 router
    class S1,S2,S3,S4 service
    class L1,L2,L3,L4,L5,L6 logging
    class TEMPLATES ui
```

### Data Flow

1. **Startup:** `main.py` creates the FastAPI app, loads layered config, initializes calibration, selects the data source (simulator or serial), performs an initial read, and spawns an async `reader_loop` task.
2. **Reader Loop:** Runs at ~10 Hz (`update_interval_s = 0.1`). Each iteration:
   - Calls `source.read_once()` to get raw sensor values + timestamp.
   - Applies calibration offsets via `_apply_offsets()`.
   - Stores the full snapshot (raw, adjusted, offsets, timestamp, value) in `LatestReadingCache`.
   - Logs data to the comprehensive logging system (JSONL + CSV) and legacy JSONL.
   - Reports performance metrics and heartbeats to the freeze detector.
3. **Browser Polling:** Frontend JS polls `GET /data` at a regular interval, receives the latest cached snapshot, and updates Plotly charts + stats cards in place.
4. **Shutdown:** Cancels the reader task, stops monitoring systems, writes a run summary.

---

## Configuration System

BLAST uses a **layered YAML config** approach — a mandatory base file plus optional user overrides.

### Config Files

```mermaid
flowchart LR
    BASE["config.base.yaml\n✅ Git-tracked"] ---|deep merge| MERGED["Merged Settings"]
    USER["config.user.yaml\n❌ Git-ignored"] ---|overrides| MERGED
    CI["config.ci.yaml\n✅ Git-tracked"] -.->|CI fallback| MERGED

    classDef tracked fill:#50b86c,stroke:#2f7a42,color:#fff
    classDef local fill:#e8a838,stroke:#b07c20,color:#fff
    classDef result fill:#4a90d9,stroke:#2c5f8a,color:#fff

    class BASE,CI tracked
    class USER local
    class MERGED result
```

### How Loading Works (`backend/app/config/loader.py`)

1. Looks for `config.base.yaml`. If found, loads it as the base.
2. If `config.user.yaml` exists, deep‑merges it on top (user keys override base keys recursively).
3. If no base file exists, falls back to the legacy single `config.yaml`.
4. Parses the merged data into a `Settings` dataclass.

### `Settings` Dataclass Fields

```python
@dataclass
class Settings:
    DATA_SOURCE: str                    # "simulator" or "serial"
    SERIAL_PORT: str                    # e.g. "COM4", "/dev/cu.usbmodem1301"
    SERIAL_BAUDRATE: int                # e.g. 115200

    PRESSURE_TRANSDUCERS: List[Dict]    # [{name, id, color, min_value, max_value, ...}, ...]
    NUM_PRESSURE_TRANSDUCERS: int
    THERMOCOUPLES: List[Dict]
    NUM_THERMOCOUPLES: int
    LOAD_CELLS: List[Dict]
    NUM_LOAD_CELLS: int
    FLOW_CONTROL_VALVES: List[Dict]
    NUM_FLOW_CONTROL_VALVES: int

    TEMPERATURE_BOUNDARIES: Dict        # {safe: [lo, hi], warning: [...], danger: [...]}
    PRESSURE_BOUNDARIES: Dict
    LOAD_CELL_BOUNDARIES: Dict
```

### Currently Configured Sensors (in `config.base.yaml`)

**Pressure Transducers (7):** GN2, LOX, LNG, LNG Downstream, LOX Downstream, LOG DOME, LNG DOME

**Thermocouples (3):** Thermocouple 1, Thermocouple 2, Cryo Thermocouple (Cold Flow)

**Load Cells (3):** Load Cell 1, Load Cell 2, Load Cell 3

**Flow Control Valves (7):** LNG Vent, LOX Vent, GN2 Vent, LNG Flow, LOX Flow, GN2‑LNG Flow, GN2‑LOX Flow

---

## Backend Deep Dive

### Entry Point — `backend/app/main.py`

The `create_app()` factory:
1. Asserts the expected filesystem layout (`assert_legacy_layout()`).
2. Loads the layered config.
3. Creates the FastAPI app and initializes all logging components.
4. Mounts static files at `/static`.
5. Includes three routers: `data`, `pages`, `calibration`.
6. Registers `startup` / `shutdown` lifecycle events.

### Routers

#### `routers/data.py`
- **`GET /data`** — Returns the latest cached snapshot. Accepts `?type=` to filter to a single sensor group. Wraps the response in a `DataEnvelope` Pydantic model.
- **`POST /api/browser_heartbeat`** — Stub endpoint for browser activity monitoring.
- **`POST /api/browser_status`** — Stub endpoint for browser tab status.
- **`GET /api/serial/logs?after=-1`** — Returns raw serial lines from the `SerialMonitorBuffer` ring buffer. Supports incremental polling via the `after` index parameter.

#### `routers/calibration.py`
- **`GET /api/offsets`** — Returns the current offset map.
- **`PUT /api/offsets`** — Partial update (merge).
- **`POST /api/zero/{sensor_id}`** — Zeroes one sensor (offset = −raw).
- **`POST /api/zero_all`** — Zeroes all sensors.
- **`POST /api/reset_offsets`** — Resets all offsets to 0.0.

Internally uses `_lookup_raw_by_id` and `_flatten_raw_by_id` helpers to map sensor IDs (e.g., `pt1`, `tc2`) to their array positions using the settings.

#### `routers/pages.py`
- Serves Jinja2‑rendered HTML pages for `/`, `/pressure`, `/thermocouples`, `/valves`.
- Injects `config` (Settings) and a `url_for` shim that translates Flask‑style `url_for('static', filename=...)` to FastAPI's `request.url_for('static', path=...)`.

### Services

#### `services/data_source.py` — `DataSource` Protocol, `SimulatorSource`, `SerialSource`

**`DataSource` Protocol:**
```python
class DataSource(Protocol):
    def initialize(self) -> None: ...
    def read_once(self) -> Tuple[Dict, float]: ...
    def shutdown(self) -> None: ...
```

**`SimulatorSource`:**
- Generates random sensor values within configured min/max ranges.
- GN2 pressure transducer uses a 25‑second sine wave + noise for realistic demo behavior.
- Writes formatted JSON packets to the `SerialMonitorBuffer` so the Serial Monitor works even in simulator mode.

**`SerialSource`:**
- Opens a PySerial connection to the configured port/baud.
- `read_once()` reads one line if data is available, calls `_parse_and_update()`, and returns the latest snapshot. On transient errors, keeps the last‑known values.
- `_parse_and_update()` expects JSON lines of the form: `{"value": {"pt": [...], "tc": [...], "lc": [...], "fcv": [...]}}`.
- Supports an optional `_convert_pt_voltage_to_psi()` conversion if `PT_CONVERSION` is configured.
- Writes every raw line to the `SerialMonitorBuffer`.

#### `services/calibration.py` — `CalibrationStore`, `CalibrationService`

- **`CalibrationStore`** — YAML file persistence with atomic writes (temp file + `os.replace`), with a fallback to direct writes for restricted filesystems (e.g., OneDrive).
- **`CalibrationService`** — Thread‑safe in‑memory offset map with `get`, `set`, `zero`, `zero_all`, and `reset` operations.
- On startup, `initialize()` builds a fresh offset map with all sensor IDs set to `0.0` and saves it.

#### `services/reading_cache.py` — `LatestReadingCache`

Thread‑safe snapshot holder. The reader loop writes via `set_full()`, and the `/data` endpoint reads via `get_full()`. Stores only the latest reading — no history.

#### `services/serial_monitor.py` — `SerialMonitorBuffer`

A thread‑safe ring buffer (`collections.deque`, default maxlen=1000) that stores every raw data packet. Each entry has `{index, timestamp, raw, source}`. The frontend polls `GET /api/serial/logs?after=<last_index>` for incremental updates.

### Schemas

#### `schemas/data.py` — `DataEnvelope`

```python
class DataEnvelope(BaseModel):
    value: Optional[Dict[str, Any]]
    timestamp: Optional[float]
    raw: Optional[Dict[str, Any]] = None
    adjusted: Optional[Dict[str, Any]] = None
    offsets: Optional[Dict[str, float]] = None
```

Uses `model_config = ConfigDict(extra="forbid")` to reject unexpected fields.

---

## Frontend Deep Dive

### Templates (`frontend/app/templates/`)

All templates extend `base.html`, which provides:
- A header with the BLAST title, current page name, a Serial Monitor toggle button, and a "Back to Dashboard" nav link (shown on subpages).
- Loads `dashboard.css`, Plotly.js (CDN), `serial_monitor.js`, and `browser_monitor.js`.

```mermaid
flowchart LR
    subgraph PAGES["Page Templates"]
        direction TB
        IDX["index.html\n/ Dashboard home"]
        PR["pressure.html\n/pressure"]
        TC["thermocouples.html\n/thermocouples"]
        VL["valves.html\n/valves"]
    end

    IDX --> N1["Nav cards"]
    PR --> P1["pt_config, pt_line,\npt_agg, pt_stats,\ncalibration.js"]
    TC --> T1["tc_agg, tc_subplots,\ntc_stats, lc_agg,\nlc_subplots, lc_stats,\ncalibration.js"]
    VL --> V1["valves.js,\nget_data.js"]

    classDef page fill:#4a90d9,stroke:#2c5f8a,color:#fff
    classDef scripts fill:#50b86c,stroke:#2f7a42,color:#fff

    class IDX,PR,TC,VL page
    class N1,P1,T1,V1 scripts
```

All templates extend `base.html`, which loads `dashboard.css`, Plotly.js (CDN), `serial_monitor.js`, and `browser_monitor.js`.

### JavaScript Modules (`frontend/app/static/js/`)

```mermaid
flowchart TB
    subgraph SHARED["Shared"]
        direction LR
        GD["get_data.js\nPolling helper"]
        CAL["calibration.js\nUI controls"]
        SM["serial_monitor.js\nPanel + auto-scroll"]
        BM["browser_monitor.js\nHeartbeat reporter"]
        CH["charts.js\nUtilities"]
    end

    subgraph PT["Pressure Transducers"]
        direction LR
        PTC["pt_config.js"]
        PTL["pt_line.js"]
        PTA["pt_agg.js"]
        PTS["pt_stats.js"]
    end

    subgraph TCLC["Thermocouples & Load Cells"]
        direction LR
        TCA["tc_agg.js"]
        TCS["tc_subplots.js"]
        TCST["tc_stats.js"]
        LCA["lc_agg.js"]
        LCS["lc_subplots.js"]
        LCST["lc_stats.js"]
    end

    subgraph VLV["Valves"]
        VJS["valves.js"]
    end

    classDef shared fill:#34495e,stroke:#2c3e50,color:#fff
    classDef pt fill:#4a90d9,stroke:#2c5f8a,color:#fff
    classDef tc fill:#50b86c,stroke:#2f7a42,color:#fff
    classDef valve fill:#e8a838,stroke:#b07c20,color:#fff

    class GD,CAL,SM,BM,CH shared
    class PTC,PTL,PTA,PTS pt
    class TCA,TCS,TCST,LCA,LCS,LCST tc
    class VJS valve
```

### Styles (`frontend/app/static/css/dashboard.css`)

A single CSS file covering all pages — layout grids, header, nav cards, stat blocks, valve grid, serial monitor panel, Plotly container sizing, and responsive adjustments.

---

## Logging & Observability

### Subsystem Components (`backend/app/logging/`)

```mermaid
flowchart TB
    subgraph LOG["Logging Components"]
        direction LR
        LM["LoggerManager\nJSONL + CSV + run dirs"]
        EL["EventLogger\nSystem events"]
        SL["SerialLogger\nSerial I/O logs"]
    end

    subgraph MON["Monitoring"]
        direction LR
        PM["PerformanceMonitor\nLatency + data lag"]
        ER["ErrorRecovery\nError counts + health"]
        FD["FreezeDetector\nHeartbeat watchdog"]
    end

    classDef logger fill:#9b59b6,stroke:#6c3483,color:#fff
    classDef monitor fill:#e8a838,stroke:#b07c20,color:#fff

    class LM,EL,SL logger
    class PM,ER,FD monitor
```

### Runtime Log Outputs

```mermaid
flowchart TD
    LOGS["frontend/logs/"] --> LEGACY["data.jsonl\nLegacy append-only"]
    LOGS --> RUN["&lt;timestamp&gt;/\nPer-run directory"]
    LOGS --> CALOFFSETS["calibration_offsets.yaml"]
    LOGS --> LATEST["latest → &lt;timestamp&gt;/\nSymlink"]

    RUN --> RD["data.jsonl"]
    RUN --> RC["data.csv"]
    RUN --> RE["events.jsonl"]
    RUN --> RP["performance.jsonl"]
    RUN --> RR["errors.jsonl"]
    RUN --> RS["run_summary.json"]

    classDef dir fill:#4a90d9,stroke:#2c5f8a,color:#fff
    classDef file fill:#50b86c,stroke:#2f7a42,color:#fff
    classDef link fill:#e8a838,stroke:#b07c20,color:#fff

    class LOGS,RUN dir
    class LEGACY,RD,RC,RE,RP,RR,RS,CALOFFSETS file
    class LATEST link
```

### Querying at Runtime

`GET /api/logging/status` returns a JSON payload with stats from every logging component plus aggregated health checks:

```json
{
  "logger_manager": { ... },
  "event_logger": { ... },
  "serial_logger": { ... },
  "performance_monitor": { ... },
  "error_recovery": { ... },
  "freeze_detector": { ... },
  "health_checks": {
    "performance": true,
    "error_recovery": true,
    "freeze_detector": true
  }
}
```

---

## Serial Protocol & Firmware Interface

### Expected Frame Format

SerialSource expects **one JSON object per line** from the flight computer:

```json
{"value": {"pt": [100.5, 200.3, ...], "tc": [25.0, 30.5, ...], "lc": [10.2, ...], "fcv": [0, 1, 0, ...]}}
```

```mermaid
flowchart LR
    FRAME["Serial JSON Frame"] --> PT["pt: float array\nPressure transducers"]
    FRAME --> TC["tc: float array\nThermocouples"]
    FRAME --> LC["lc: float array\nLoad cells"]
    FRAME --> FCV["fcv: int array 0/1\nValve states"]

    classDef frame fill:#4a90d9,stroke:#2c5f8a,color:#fff
    classDef sensor fill:#50b86c,stroke:#2f7a42,color:#fff

    class FRAME frame
    class PT,TC,LC,FCV sensor
```

- Array lengths must match the config (`NUM_PRESSURE_TRANSDUCERS`, etc.). Extra values are ignored; missing values keep their previous value.
- Malformed lines (non‑JSON or missing `value` key) are silently dropped — the last valid snapshot is preserved.
- FCV values are mirrored to both `fcv_actual` and `fcv_expected` (firmware currently sends one combined state).

### Serial Settings

Default: **115200 baud**, port varies by OS. Configured in `config.base.yaml` / `config.user.yaml`.

### Voltage‑to‑PSI Conversion

`SerialSource` has a `_convert_pt_voltage_to_psi()` method that supports an optional `PT_CONVERSION` config (offset‑based). If not configured, values pass through as‑is.

---

## Calibration System

### How It Works

1. On startup, `CalibrationService.initialize()` creates a fresh offset map with every sensor ID set to `0.0` and persists it to `frontend/logs/calibration_offsets.yaml`.
2. The reader loop calls `_apply_offsets(raw, offsets, settings)` every cycle, adding the offset to each numeric sensor value: `adjusted[i] = raw[i] + offset[sensor_id]`.
3. Users can adjust offsets via the UI (rendered by `calibration.js`) or the REST API.

### Operations

```mermaid
flowchart LR
    ZERO["Zero\nPOST /api/zero/id"] --> EFF1["offset = −raw\nadjusted ≈ 0"]
    ZALL["Zero All\nPOST /api/zero_all"] --> EFF2["All sensors\nzeroed"]
    SET["Set Offset\nPUT /api/offsets"] --> EFF3["Arbitrary values\npartial merge"]
    RESET["Reset\nPOST /api/reset_offsets"] --> EFF4["All offsets → 0.0"]

    classDef op fill:#4a90d9,stroke:#2c5f8a,color:#fff
    classDef effect fill:#50b86c,stroke:#2f7a42,color:#fff

    class ZERO,ZALL,SET,RESET op
    class EFF1,EFF2,EFF3,EFF4 effect
```

### Persistence

Offsets are saved to `calibration_offsets.yaml` via atomic writes (temp file + rename). Falls back to direct writes on filesystems that restrict temp file operations.

---

## API Reference

### Pages (HTML)

```mermaid
flowchart LR
    subgraph PAGES["HTML Pages"]
        P1["GET /"]
        P2["GET /pressure"]
        P3["GET /thermocouples"]
        P4["GET /valves"]
    end

    subgraph DATA["Data"]
        D1["GET /data?type=all"]
        D2["GET /api/serial/logs"]
        D3["POST /api/browser_heartbeat"]
        D4["POST /api/browser_status"]
    end

    subgraph CALIB["Calibration"]
        C1["GET /api/offsets"]
        C2["PUT /api/offsets"]
        C3["POST /api/zero/sensor_id"]
        C4["POST /api/zero_all"]
        C5["POST /api/reset_offsets"]
    end

    subgraph HEALTH["Health & Diagnostics"]
        H1["GET /healthz"]
        H2["GET /api/logging/status"]
    end

    classDef pages fill:#4a90d9,stroke:#2c5f8a,color:#fff
    classDef data fill:#50b86c,stroke:#2f7a42,color:#fff
    classDef calib fill:#e8a838,stroke:#b07c20,color:#fff
    classDef health fill:#e67e73,stroke:#b35a52,color:#fff

    class P1,P2,P3,P4 pages
    class D1,D2,D3,D4 data
    class C1,C2,C3,C4,C5 calib
    class H1,H2 health
```

---

## CI & Testing

### GitHub Actions (`.github/workflows/ci.yml`)

Triggered on push/PR to `main`:

1. **Checkout** → Set up Python 3.9 → Pip install (cached)
2. **Smoke test** — `python tools/smoke_test_fastapi.py` (auto‑sets `FORCE_SIMULATOR_MODE=1`)
3. **Pytest** — `pytest -q backend/tests`

### Test Files

| File | Tests |
|------|-------|
| `backend/tests/test_app_basic.py` | `/healthz` returns 200 + healthy, all HTML pages return 200, `/data` has correct shape and keys, type filtering works. |
| `backend/tests/test_calibration_api.py` | Offset CRUD flow: get → set → zero → reset. Tolerant of filesystem issues. |

### Running Locally

```bash
# Smoke test (exercises full startup + endpoints in simulator mode)
python tools/smoke_test_fastapi.py

# Unit tests
pytest -q backend/tests

# With verbose output
pytest -v backend/tests
```

---

## First Week Checklist

- [ ] **Get access** to the repo, join any relevant chat channels, and get CI notifications.
- [ ] **Set up your environment** — clone the repo, run one of the setup options, and start the app with the simulator.
- [ ] **Explore the dashboard** — open http://127.0.0.1:8000, click through all pages, open the Serial Monitor.
- [ ] **Inspect the API** — visit `/data` in your browser, try `/data?type=pt`, check `/healthz`.
- [ ] **Try calibration** — zero a sensor via the UI controls, then check `/api/offsets`. Reset.
- [ ] **Read the config** — open `config.base.yaml`, understand the sensor definitions, copy to `config.user.yaml` and switch to simulator mode.
- [ ] **If hardware is available** — connect the flight computer, set `data_source: "serial"` and the correct `serial_port` in `config.user.yaml`, restart the app, and verify data flows.
- [ ] **Run the tests** — `pytest -q backend/tests` and `python tools/smoke_test_fastapi.py`.
- [ ] **Read the code** — start with `main.py`, then follow the data flow through `data_source.py` → `reading_cache.py` → `routers/data.py`.

---

## Short Roadmap

- **Lock down serial frame schema/units with firmware** — Define a simple ICD (keys, types, units, sample rate, timestamp semantics) and version it. Update `SerialSource._parse_and_update` to match, and add a shape check so malformed frames are ignored without crashing.

- **Move sensor processing from Arduino to the laptop** — Shift lightweight conversions (ADC voltage → engineering units: PT volts → PSI, TC volts → °C, LC volts → force/mass) and offset math into BLAST. Reduces MCU load and lets us update conversion parameters without reflashing.

- **Explore Rust or C for serial I/O hot paths** — Prototype a tiny reader (line parsing + ring buffer) exposed to Python via FFI or a local socket. Only adopt if benchmarks show real CPU/latency gains at expected rates.

- **Exercise serial on bench hardware and document permissions/rates** — Validate sustained read rates (baseline ~10 Hz), OS permissions, and failure behavior (disconnects, partial frames).

- **Add focused tests** — Unit tests for calibration math (zero arithmetic, partial updates, invalid payloads) and serial parsing (bad JSON lines, partial frames, boolean FCV handling).

- **Wire remaining sensor pages** — Ensure each page/template binds to the right `/data` keys. Verify live updates, resizing, and navigation. Add missing routes if needed.

- **Add an accelerometer page** — If firmware provides accelerometer data, add a page with magnitude and per‑axis traces. If not available yet, leave a simulator stub.

- **Page style improvements** — Unify Plotly configs (fonts, colors), improve spacing and responsiveness, clean up typography. Keep changes incremental.

Have something else or see an issue? Add your item here and open a PR.

---

## Quick Links

| What | Where |
|------|-------|
| Run the app | `uvicorn backend.app.main:app --reload` → http://127.0.0.1:8000 |
| Base config | `frontend/app/config.base.yaml` |
| User config (create this) | `frontend/app/config.user.yaml` |
| Main entry point | `backend/app/main.py` |
| Routers | `backend/app/routers/{data,calibration,pages}.py` |
| Services | `backend/app/services/{data_source,calibration,reading_cache,serial_monitor}.py` |
| Logging | `backend/app/logging/*.py` |
| Runtime logs | `frontend/logs/` |
| Tests | `backend/tests/` |
| CI config | `.github/workflows/ci.yml` |
| Smoke test | `tools/smoke_test_fastapi.py` |
| Version | `backend/app/VERSION` (currently `0.1.0`) |
