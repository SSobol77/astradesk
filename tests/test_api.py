# SPDX-License-Identifier: Apache-2.0
# tests/test_api.py
# Author: Siergej Sobolewski
# Since: 2025-10-07

from fastapi.testclient import TestClient
from gateway.main import app

def test_healthz_ok():
    with TestClient(app) as c:
        r = c.get("/healthz")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
