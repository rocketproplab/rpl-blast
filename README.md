# rpl-blast

## Setup Conda Environment
```bash
conda env create -f environment.yaml
conda activate RPL
```

## Run Application
```bash
# Check you are in the correct directory
# cd BLAST_web\ plotly\ subplot (THIS MIGHT NOT WORK ON WINDOWS)
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
3. For serial mode, ensure the correct port is set in `serial_port: "/dev/cu.usbmodem1301"`

## Troubleshooting

If you encounter any issues:
1. GOOD LUCK