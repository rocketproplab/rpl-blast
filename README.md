# rpl-blast

New to the project? Start with the onboarding guide: [ONBOARDING.md](ONBOARDING.md).

## One-click Setup (No Python required)
Use the scripts in `scripts/` for the simplest experience.

- macOS
  - Double‑click: `scripts/Setup Mac.command` then `scripts/Start App.command`
  - If blocked by macOS: run `bash scripts/fix_permissions_mac.sh`, then try again.

- Windows (PowerShell)
  - Double‑click: `scripts\setup_win.bat` then `scripts\start_win.bat`

Details
- Uses micromamba to download a local Python and create a project‑scoped env at `.venv` (no global changes).
- Installs Python packages from `requirements.txt`.
- Customize host/port via env vars `HOST` and `PORT` when running the start scripts.

 Uninstall (remove local Python + packages only)
- macOS: double‑click `scripts/Uninstall Mac.command`
- Windows: double‑click `scripts\uninstall_win.bat`

## Setup Conda Environment
```bash
conda env create -f environment.yaml
conda activate RPL
```

## Run Application (FastAPI)
For all steps below, run using the Anaconda Prompt if on Windows.
### FastAPI dev server
```bash
# from repo root
conda activate RPL
uvicorn backend.app.main:app --reload
```
Open http://127.0.0.1:8000 in your browser.

The FastAPI app serves templates from `frontend/app/templates` and static assets from `frontend/app/static`. The `/data` endpoint returns adjusted sensor values, and also exposes `raw`, `adjusted`, and `offsets` for calibration-aware clients.

### Calibration
- UI controls are available under the plots on the Pressure and Thermocouples pages.
- API:
  - `GET /api/offsets`
  - `PUT /api/offsets` with a JSON object `{ sensor_id: offset }`
  - `POST /api/zero/{sensor_id}`
  - `POST /api/zero_all`
  - `POST /api/reset_offsets`

Notes:
- Set `data_source: "simulator"` in `frontend/app/config.yaml` for local development (serial fails fast until implemented).
- Logs stream to `frontend/logs/data.jsonl`.

## Legacy Flask (Deprecated)
The legacy Flask runner is deprecated in favor of the FastAPI app and is no longer maintained in this branch. For historical reference, use the `legacy` branch or pre‑migration tag.

## Project Structure (current)
```
rpl-blast/
├── backend/app/            # FastAPI backend
├── frontend/app/           # Templates, static, config.yaml
├── frontend/logs/          # Runtime logs (data.jsonl, offsets)
├── scripts/                # One‑click setup/start/uninstall
├── environment.yaml        # Conda environment (optional)
└── README.md
```

## Switching Data Sources
To switch between simulator and serial data:
1. Open `frontend/app/config.yaml`
2. Change `data_source: "simulator"` to `data_source: "serial"` for real data
3. For serial mode, ensure the correct port is set for `serial_port` following steps above, e.g. `serial_port: "/dev/cu.usbmodem1301"` for Mac, `serial_port: "COM5"` for Windows.

## Troubleshooting

If you encounter any issues:
1. GOOD LUCK
