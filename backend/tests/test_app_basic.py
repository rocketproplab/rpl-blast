from fastapi.testclient import TestClient


def get_client():
    # Import within function so tests always use fresh app state
    from pathlib import Path
    import sys
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from backend.app.main import app
    return TestClient(app)


def test_healthz_200():
    with get_client() as client:
        r = client.get("/healthz")
        assert r.status_code == 200
        body = r.json()
        assert body.get("healthy") is True


def test_pages_200():
    with get_client() as client:
        for path in ("/", "/pressure", "/thermocouples", "/valves"):
            r = client.get(path)
            assert r.status_code == 200


def test_data_endpoint_shape():
    with get_client() as client:
        r = client.get("/data")
        assert r.status_code == 200
        body = r.json()
        assert "value" in body
        assert "timestamp" in body
        v = body["value"]
        assert isinstance(v, dict)
        # Expect legacy keys
        for k in ("pt", "tc", "lc", "fcv_actual", "fcv_expected"):
            assert k in v


def test_data_type_filtering():
    with get_client() as client:
        r = client.get("/data?type=pt")
        assert r.status_code == 200
        body = r.json()
        assert set(body["value"].keys()) == {"pt"}

