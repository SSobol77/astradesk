# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: tests/test_api.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Verifies AstraDesk behavior for the associated component.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

from fastapi.testclient import TestClient
from gateway.main import app


def test_healthz_ok():
    with TestClient(app) as c:
        r = c.get('/healthz')
        assert r.status_code == 200
        assert r.json()['status'] == 'ok'
