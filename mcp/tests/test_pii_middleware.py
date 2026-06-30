# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: mcp/tests/test_pii_middleware.py
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

"""MCP Gateway ingress PII boundary + external-tool egress tests.

Covers ISSUES_NEW-04: the real PII classifier replacing the no-op middleware,
the redacted tracing target (no query strings on spans), and external tool
egress denial for an unlisted target (required test 8).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from astradesk_core.egress import EgressDenied
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.requests import Request as StarletteRequest

from mcp.src.clients.kb_client import KnowledgeBaseClient
from mcp.src.gateway.middleware import (
    PIIProtectionMiddleware,
    _redacted_target,
)

_RAW_EMAIL = 'leak@example.com'


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(PIIProtectionMiddleware)

    @app.post('/echo')
    async def echo(request: Request) -> dict[str, object]:
        # The handler returns a fixed body + the classification recorded by the
        # middleware on request.state — never the raw body.
        return {
            'status': 'ok',
            'classification': getattr(request.state, 'pii_classification', []),
        }

    return app


def test_middleware_classifies_body_and_does_not_echo_raw() -> None:
    client = TestClient(_build_app())
    resp = client.post('/echo', content=f'please email {_RAW_EMAIL}')
    assert resp.status_code == 200
    assert _RAW_EMAIL not in resp.text
    assert 'email' in resp.json()['classification']
    assert 'email' in resp.headers.get('X-PII-Classification', '')


def test_middleware_blocks_secret_class_body_in_block_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('MCP_PII_BLOCK_SECRETS', '1')
    client = TestClient(_build_app())
    resp = client.post('/echo', content='api_key=supersecretvalue123')
    assert resp.status_code == 422
    body = resp.json()
    assert body['error'] == 'pii_policy_violation'
    assert 'secret' in body['categories']
    # The raw secret must never be echoed back.
    assert 'supersecretvalue123' not in resp.text


def test_middleware_allows_benign_body() -> None:
    client = TestClient(_build_app())
    resp = client.post('/echo', content='restart the webapp service')
    assert resp.status_code == 200
    assert resp.json()['classification'] == []
    assert 'X-PII-Classification' not in resp.headers


def test_redacted_target_strips_query_string_and_secrets() -> None:
    scope = {
        'type': 'http',
        'method': 'GET',
        'scheme': 'http',
        'server': ('mcp-gateway', 8080),
        'path': '/invoke',
        'query_string': b'token=aaa.bbb.ccc&u=alice',
        'headers': [],
    }
    request = StarletteRequest(scope)
    target = _redacted_target(request)
    assert 'aaa.bbb.ccc' not in target
    assert 'token=' not in target
    assert target.endswith('/invoke')


@pytest.mark.asyncio
async def test_kb_client_egress_denied_for_unlisted_host() -> None:
    client = KnowledgeBaseClient('https://evil.attacker.example')
    with pytest.raises(EgressDenied):
        await client.search('any query', top_k=3)


@pytest.mark.asyncio
async def test_kb_client_egress_allowed_for_listed_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('ASTRADESK_EGRESS_ALLOWLIST', 'kb.allowed.test')
    client = KnowledgeBaseClient('https://kb.allowed.test')

    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.json = MagicMock(
        return_value={
            'results': [
                {'id': '1', 'title': 'T', 'content': 'C', 'metadata': {}},
            ]
        }
    )
    monkeypatch.setattr(client.http_client, 'post', AsyncMock(return_value=fake_response))

    entries = await client.search('reset password', top_k=1)
    assert len(entries) == 1
    assert entries[0].id == '1'
