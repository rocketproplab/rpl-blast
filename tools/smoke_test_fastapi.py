from pathlib import Path
import sys
import os

# Ensure repo root on path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Force simulator mode for CI environment where no serial hardware exists
if 'CI' in os.environ or 'GITHUB_ACTIONS' in os.environ:
    print("CI environment detected, forcing simulator mode")
    # Set environment variable to override config
    os.environ['FORCE_SIMULATOR_MODE'] = '1'

from fastapi.testclient import TestClient
from backend.app.main import app


def main():
    print(f"Testing BLAST FastAPI application...")
    print(f"Data source mode: {'simulator (CI override)' if os.environ.get('FORCE_SIMULATOR_MODE') else 'from config'}")
    
    with TestClient(app) as client:
        r = client.get('/healthz')
        print('healthz:', r.status_code, r.json())

        r = client.get('/')
        print('index:', r.status_code)

        r = client.get('/data')
        print('data:', r.status_code)
        j = r.json()
        print('data keys:', list(j.keys()))
        v = j.get('value') or {}
        print('value keys head:', list(v.keys())[:5])
        print('has timestamp in value:', 'timestamp' in v)

        r = client.get('/data?type=pt')
        print('data?type=pt:', r.status_code, r.json())

        # Calibration API smoke
        r = client.get('/api/offsets')
        print('offsets:', r.status_code, r.json())
        # Zero first PT if present
        settings = app.state.settings
        pt_ids = [pt.get('id') for pt in settings.PRESSURE_TRANSDUCERS]
        if pt_ids:
            first = pt_ids[0]
            r = client.post(f'/api/zero/{first}')
            print('zero one:', r.status_code, r.json())
            r = client.get('/api/offsets')
            print('offsets after zero one:', r.json())
        r = client.get('/healthz')
        print('healthz:', r.json())


if __name__ == '__main__':
    main()
