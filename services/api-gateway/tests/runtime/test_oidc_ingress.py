# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/tests/runtime/test_oidc_ingress.py
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

from __future__ import annotations

import time

import jwt
import pytest
from astradesk_core.utils.oidc import (
    AuthConfigError,
    AuthError,
    OIDCSettings,
    TokenVerifier,
    build_verifier_from_env,
)
from cryptography.hazmat.primitives.asymmetric import rsa

ISSUER = 'https://issuer.example.test/'
AUDIENCE = 'astradesk-api'
KID = 'test-key-1'


@pytest.fixture(scope='module')
def rsa_keypair() -> tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private, private.public_key()


@pytest.fixture
def verifier(rsa_keypair) -> TokenVerifier:
    _, public = rsa_keypair
    settings = OIDCSettings(
        issuer=ISSUER,
        audience=AUDIENCE,
        jwks_url='https://unused.test/jwks',
        algorithms=('RS256',),
        leeway_seconds=5,
    )

    def resolver(token: str):
        header = jwt.get_unverified_header(token)
        if header.get('kid') != KID:
            raise AuthError('invalid_token', 'unknown kid')
        return public

    return TokenVerifier(settings, key_resolver=resolver)


def _mint(
    private,
    *,
    sub='user-1',
    aud=AUDIENCE,
    iss=ISSUER,
    kid=KID,
    exp_delta=300,
    nbf_delta=None,
    roles=('operator',),
    extra=None,
) -> str:
    now = int(time.time())
    payload = {
        'sub': sub,
        'aud': aud,
        'iss': iss,
        'iat': now,
        'exp': now + exp_delta,
        'roles': list(roles),
    }
    if nbf_delta is not None:
        payload['nbf'] = now + nbf_delta
    if extra:
        payload.update(extra)
    return jwt.encode(payload, private, algorithm='RS256', headers={'kid': kid})


# --- positive control --------------------------------------------------------


def test_valid_token_passes(verifier, rsa_keypair):
    private, _ = rsa_keypair
    principal = verifier.verify(_mint(private))
    assert principal.subject == 'user-1'
    assert 'operator' in principal.roles


# --- negative matrix (each must be denied) -----------------------------------


def test_empty_token_denied(verifier):
    with pytest.raises(AuthError) as e:
        verifier.verify('')
    assert e.value.code == 'missing_token'


def test_bad_signature_denied(verifier):
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(AuthError) as e:
        verifier.verify(_mint(other))  # signed by a key the resolver won't return
    assert e.value.code == 'invalid_token'


def test_wrong_audience_denied(verifier, rsa_keypair):
    private, _ = rsa_keypair
    with pytest.raises(AuthError) as e:
        verifier.verify(_mint(private, aud='some-other-api'))
    assert e.value.code == 'invalid_audience'


def test_wrong_issuer_denied(verifier, rsa_keypair):
    private, _ = rsa_keypair
    with pytest.raises(AuthError) as e:
        verifier.verify(_mint(private, iss='https://evil.example/'))
    assert e.value.code == 'invalid_issuer'


def test_expired_token_denied(verifier, rsa_keypair):
    private, _ = rsa_keypair
    with pytest.raises(AuthError) as e:
        verifier.verify(_mint(private, exp_delta=-60))
    assert e.value.code == 'token_expired'


def test_not_yet_valid_token_denied(verifier, rsa_keypair):
    private, _ = rsa_keypair
    with pytest.raises(AuthError) as e:
        verifier.verify(_mint(private, nbf_delta=3600))
    assert e.value.code == 'token_not_yet_valid'


def test_unknown_kid_denied(verifier, rsa_keypair):
    private, _ = rsa_keypair
    with pytest.raises(AuthError) as e:
        verifier.verify(_mint(private, kid='rotated-away'))
    assert e.value.code == 'invalid_token'


def test_bad_signature_error_does_not_embed_raw_token(verifier, rsa_keypair):
    """AuthError must never carry the raw token text (INV-OIDC-8)."""
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = _mint(other)
    with pytest.raises(AuthError) as e:
        verifier.verify(token)
    assert token not in str(e.value)
    assert token not in e.value.message


def test_subjectless_token_denied(verifier, rsa_keypair):
    private, _ = rsa_keypair
    with pytest.raises(AuthError) as e:
        verifier.verify(_mint(private, sub=''))
    assert e.value.code == 'invalid_token'


def test_required_scope_enforced(rsa_keypair):
    private, public = rsa_keypair
    settings = OIDCSettings(
        issuer=ISSUER,
        audience=AUDIENCE,
        jwks_url='https://unused.test/jwks',
        required_scopes=('agents:run',),
    )
    v = TokenVerifier(settings, key_resolver=lambda t: public)
    with pytest.raises(AuthError) as e:
        v.verify(_mint(private, extra={'scope': 'agents:read'}))
    assert e.value.code == 'insufficient_scope'


def test_keycloak_realm_access_roles_supported(rsa_keypair):
    private, public = rsa_keypair
    settings = OIDCSettings(
        issuer=ISSUER,
        audience=AUDIENCE,
        jwks_url='https://unused.test/jwks',
        roles_claim='realm_access.roles',
    )
    verifier = TokenVerifier(settings, key_resolver=lambda _token: public)
    token = _mint(private, extra={'realm_access': {'roles': ['sre', 'support.agent']}})
    principal = verifier.verify(token)
    assert principal.roles == ('sre', 'support.agent')


# --- startup fail-closed (INV-OIDC-1 / INV-OIDC-3) ---------------------------


def test_missing_prod_config_aborts(monkeypatch):
    for var in ('OIDC_ISSUER', 'OIDC_AUDIENCE', 'OIDC_JWKS_URL'):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv('AUTH_MODE', 'production')
    with pytest.raises(AuthConfigError):
        build_verifier_from_env()


def test_local_dev_refused_on_deployed_tier(monkeypatch):
    monkeypatch.setenv('AUTH_MODE', 'local-dev')
    monkeypatch.setenv('ENVIRONMENT', 'production')
    with pytest.raises(AuthConfigError):
        build_verifier_from_env()


def test_unset_environment_defaults_to_deployed_safe(monkeypatch):
    """ENVIRONMENT absent entirely must behave like ENVIRONMENT=production.

    Unset is the common real-world case (a forgotten/omitted variable), not
    just an explicit 'production' value, so local-dev must be refused here
    too (INV-OIDC-2 / INV-OIDC-6 safe default).
    """
    monkeypatch.delenv('ENVIRONMENT', raising=False)
    monkeypatch.setenv('AUTH_MODE', 'local-dev')
    with pytest.raises(AuthConfigError):
        build_verifier_from_env()


def test_unknown_auth_mode_aborts(monkeypatch):
    monkeypatch.setenv('AUTH_MODE', 'anything-goes')
    with pytest.raises(AuthConfigError):
        build_verifier_from_env()
