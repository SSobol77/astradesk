# SPDX-License-Identifier: Apache-2.0
# services/api-gateway/src/tests/runtime/test_auth.py
"""Tests for core/src/astradesk_core/utils/auth.py (OIDC/JWT verification with JWKS cache).

Key points:
- Module creates global cfg at import-time and reads ENV → tests must set ENV before import.
- All I/O (httpx) and crypto (jose.jwk/jwt) are mocked; no network, no real signatures.
- We assert correct control flow, cache behavior, and parameters passed to jose.jwt.decode.
"""

from __future__ import annotations

import importlib
import asyncio
import types
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# Utilities: import module with env configured & provide easy accessors

def _import_auth_with_env(monkeypatch) -> types.ModuleType:
    """Import src.runtime.auth with required ENV set, return the module."""
    monkeypatch.setenv("OIDC_ISSUER", "https://login.example.com/")
    monkeypatch.setenv("OIDC_AUDIENCE", "astradesk-api")
    monkeypatch.setenv("OIDC_JWKS_URL", "https://login.example.com/.well-known/jwks.json")
    # Small TTL to make TTL tests deterministic (overridden per-test when needed)
    monkeypatch.setenv("OIDC_JWKS_TTL", "3600")
    # Leeway for clock skew:
    monkeypatch.setenv("OIDC_TIME_SKEW_LEEWAY", "60")

    import core.src.astradesk_core.utils.auth as auth  # noqa: WPS433  (import inside function)
    auth = importlib.reload(auth)  # ensure fresh globals
    return auth


class _FakeAsyncClient:
    """Minimal async-context Manager for httpx.AsyncClient mocking."""

    def __init__(self, response_json: dict[str, Any]) -> None:
        self._json = response_json
        self.get = AsyncMock()

        async def _get(url: str):
            class _Resp:
                def raise_for_status(self):
                    return None

                def json(self_nonlocal):
                    return response_json
            await asyncio.sleep(0) 
            return _Resp()

        self.get.side_effect = _get

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

# -- Tests ---

@pytest.mark.asyncio
async def test_verify_success_and_decode_args(monkeypatch):
    """Happy path: single JWKS fetch, decode called with proper params, returns claims."""
    auth = _import_auth_with_env(monkeypatch)

    # Mock jose
    monkeypatch.setattr(auth.jwt, "get_unverified_header", lambda t: {"kid": "k1", "alg": "RS256"})
    decode_mock = MagicMock(return_value={"sub": "alice", "iss": auth.ISSUER, "aud": auth.AUDIENCE})
    monkeypatch.setattr(auth.jwt, "decode", decode_mock)
    monkeypatch.setattr(auth.jwk, "construct", lambda key: {"constructed": key})

    # Mock httpx client -> JWKS with k1
    jwks = {"keys": [{"kid": "k1", "kty": "RSA", "n": "...", "e": "AQAB"}]}
    fake_client = _FakeAsyncClient(jwks)
    monkeypatch.setattr(auth, "httpx", MagicMock(AsyncClient=lambda timeout: fake_client))

    claims = await auth.cfg.verify("header.payload.sig")
    assert claims["sub"] == "alice"

    # Assert jwt.decode was called with correct arguments
    assert decode_mock.call_count == 1
    _, kwargs = decode_mock.call_args
    assert kwargs["audience"] == auth.AUDIENCE
    assert kwargs["issuer"] == auth.ISSUER
    assert kwargs["algorithms"] == ["RS256"]
    assert isinstance(kwargs["options"], dict) and kwargs["options"].get("leeway") == auth.TIME_SKEW_LEEWAY


@pytest.mark.asyncio
async def test_empty_token_raises_valueerror(monkeypatch):
    auth = _import_auth_with_env(monkeypatch)
    with pytest.raises(ValueError):
        await auth.cfg.verify("")


@pytest.mark.asyncio
async def test_missing_kid_in_header_raises_valueerror(monkeypatch):
    auth = _import_auth_with_env(monkeypatch)

    monkeypatch.setattr(auth.jwt, "get_unverified_header", lambda t: {"alg": "RS256"})  # no kid
    # Prepare JWKS to avoid network noise (but it shouldn't matter)
    fake_client = _FakeAsyncClient({"keys": []})
    monkeypatch.setattr(auth, "httpx", MagicMock(AsyncClient=lambda timeout: fake_client))

    with pytest.raises(ValueError):
        await auth.cfg.verify("x.y.z")


@pytest.mark.asyncio
async def test_key_rotation_retry_fetches_again_and_succeeds(monkeypatch):
    """First JWKS lacks the key -> clear_cache + second JWKS has the key -> success."""
    auth = _import_auth_with_env(monkeypatch)

    # jose mocks
    monkeypatch.setattr(auth.jwt, "get_unverified_header", lambda t: {"kid": "rotated", "alg": "RS256"})
    monkeypatch.setattr(auth.jwt, "decode", MagicMock(return_value={"ok": True}))
    monkeypatch.setattr(auth.jwk, "construct", lambda key: {"constructed": key})

    # Two-phase JWKS: first without key, second with key
    jwks_1 = {"keys": [{"kid": "old", "kty": "RSA"}]}
    jwks_2 = {"keys": [{"kid": "rotated", "kty": "RSA"}]}
    created = {"calls": 0}

    def _ac_factory(timeout):
        created["calls"] += 1
        return _FakeAsyncClient(jwks_1 if created["calls"] == 1 else jwks_2)

    httpx_mock = MagicMock(AsyncClient=_ac_factory)
    monkeypatch.setattr(auth, "httpx", httpx_mock)

    res = await auth.cfg.verify("x.y.z")
    assert res["ok"] is True
    # We expect two client creations → two GETs (first fail, then after clear_cache refresh)
    assert created["calls"] == 2


@pytest.mark.asyncio
async def test_key_not_found_even_after_refresh_raises(monkeypatch):
    auth = _import_auth_with_env(monkeypatch)

    monkeypatch.setattr(auth.jwt, "get_unverified_header", lambda t: {"kid": "missing", "alg": "RS256"})
    monkeypatch.setattr(auth.jwk, "construct", lambda key: {"constructed": key})
    # jwt.decode should never be called in this path
    monkeypatch.setattr(auth.jwt, "decode", MagicMock(side_effect=AssertionError("should not decode")))

    # Both JWKS responses without the required key
    fake_client = _FakeAsyncClient({"keys": [{"kid": "other"}]})
    monkeypatch.setattr(auth, "httpx", MagicMock(AsyncClient=lambda timeout: fake_client))

    with pytest.raises(ValueError, match="nie został znaleziony"):
        await auth.cfg.verify("x.y.z")


@pytest.mark.asyncio
async def test_jwks_cache_ttl_triggers_refresh(monkeypatch):
    """First verify caches JWKS; after TTL expiry, a new fetch occurs."""
    auth = _import_auth_with_env(monkeypatch)

    # Short TTL for this test
    monkeypatch.setenv("OIDC_JWKS_TTL", "1")
    # Reload to apply new TTL into module-level constant
    auth = importlib.reload(auth)

    # jose mocks
    monkeypatch.setattr(auth.jwt, "get_unverified_header", lambda t: {"kid": "k1", "alg": "RS256"})
    monkeypatch.setattr(auth.jwk, "construct", lambda key: {"constructed": key})
    monkeypatch.setattr(auth.jwt, "decode", MagicMock(return_value={"ok": True}))

    # time control
    t0 = 1_000_000.0
    times = {"now": t0}

    monkeypatch.setattr(auth, "time", MagicMock())
    auth.time.time = MagicMock(side_effect=lambda: times["now"])

    # JWKS client factory counting calls
    calls = {"n": 0}

    def _ac_factory(timeout):
        calls["n"] += 1
        return _FakeAsyncClient({"keys": [{"kid": "k1"}]})

    monkeypatch.setattr(auth, "httpx", MagicMock(AsyncClient=_ac_factory))

    # First verify → fetch
    await auth.cfg.verify("x.y.z")
    assert calls["n"] == 1

    # Before TTL expires → no fetch
    times["now"] = t0 + 0.5
    await auth.cfg.verify("x.y.z")
    assert calls["n"] == 1

    # After TTL expires → second fetch
    times["now"] = t0 + 2.0
    await auth.cfg.verify("x.y.z")
    assert calls["n"] == 2
