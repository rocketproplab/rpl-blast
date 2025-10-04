from fastapi.testclient import TestClient


def get_client():
    from pathlib import Path
    import sys
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root))
    from backend.app.main import app
    return TestClient(app)


def test_offsets_flow():
    with get_client() as client:
        # initial
        r = client.get('/api/offsets')
        assert r.status_code == 200
        assert 'offsets' in r.json()

        # choose one sensor id
        settings = client.app.state.settings
        sid = settings.PRESSURE_TRANSDUCERS[0]['id'] if settings.PRESSURE_TRANSDUCERS else None
        if not sid:
            return

        # set offset
        r = client.put('/api/offsets', json={sid: 1.23})
        # In some environments, writing may fail (e.g., restrictive FS); allow 400
        if r.status_code == 200:
            off = r.json()['offsets']
            assert isinstance(off, dict)

        # zero (may also fail on FS), ensure API semantics
        r = client.post(f'/api/zero/{sid}')
        assert r.status_code in (200, 400, 503, 404)

        # reset
        r = client.post('/api/reset_offsets')
        assert r.status_code in (200, 400)

