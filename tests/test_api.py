# tests/test_api.py

from fastapi.testclient import TestClient
from gateway.main import app

def test_healthz_ok():
    with TestClient(app) as c:
        r = c.get("/healthz")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
