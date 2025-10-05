# rpl-blast

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

The UI reuses the legacy templates and static assets under `BLAST_web plotly subplot/app/`. The `/data` endpoint returns adjusted sensor values, and also exposes `raw`, `adjusted`, and `offsets` for calibration-aware clients.

### Calibration
- UI controls are available under the plots on the Pressure and Thermocouples pages.
- API:
  - `GET /api/offsets`
  - `PUT /api/offsets` with a JSON object `{ sensor_id: offset }`
  - `POST /api/zero/{sensor_id}`
  - `POST /api/zero_all`
  - `POST /api/reset_offsets`

Notes:
- Set `data_source: "simulator"` in `BLAST_web plotly subplot/app/config.yaml` for local development (serial fails fast until implemented).
- Logs stream to `BLAST_web plotly subplot/logs/data.jsonl`.

## Run Application (Legacy Flask)
For all steps below, run using the Anaconda Prompt if on windows.
### Check COM port on Windows:
```bash
# Check you are in root directory of this repository
conda activate RPL
python serial_test.py
```
The expected output will be similar to:
```bash
(blast) C:\RPL\rpl-blast>python serial_test.py
2025-06-18 14:08:26,544 [DEBUG] Enumerating serial ports...
2025-06-18 14:08:26,570 [INFO] COM5 — Arduino Mega 2560 (COM5)
```
Take note of the name of the port before the dash, e.g. COM5.
In `Blast_web plotly subplot/app/config.yaml`, replace the value of `serial_port` with the string of the name of the port, (e.g. `serial_port: "COM5"`)
### Running the GUI
```bash
# Check you are in the correct directory
cd "BLAST_web plotly subplot"
conda activate RPL
python run.py
```
Then open http://127.0.0.1:5000 in your web browser.

## Project Structure
```
rpl-blast/
├── BLAST_web plotly subplot/
│   ├── app/            # Application code
│   ├── logs/           # Log files
│   └── run.py          # Application entry point
├── environment.yaml    # Conda environment file
└── README.md          # This file
```

## Switching Data Sources
To switch between simulator and serial data:
1. Open `BLAST_web plotly subplot/app/config.yaml`
2. Change `data_source: "simulator"` to `data_source: "serial"` for real data
3. For serial mode, ensure the correct port is set for `serial_port` following steps above, e.g. `serial_port: "/dev/cu.usbmodem1301"` for Mac, `serial_port: "COM5"` for Windows.

## Troubleshooting

If you encounter any issues:
1. GOOD LUCK
