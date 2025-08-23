# rpl-blast

## Setup Conda Environment
```bash
conda env create -f environment.yaml
conda activate RPL
```

## Run Application
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
