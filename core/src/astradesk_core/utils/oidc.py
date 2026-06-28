# SPDX-License-Identifier: GPL-2.0-only
# File: core/src/astradesk_core/utils/oidc.py
#
# OIDC/JWKS access-token verification for AstraDesk ingress (ISSUE 009).
#
# Design (contract-first):
#   INV-OIDC-1  Production startup aborts if OIDC issuer/JWKS/audience config is
#               absent (fail-closed): build_verifier_from_env() raises.
#   INV-OIDC-2  Every token is validated for signature (JWKS), iss, aud, exp, and
#               nbf-if-present before any handler runs.
#   INV-OIDC-3  The symmetric (HS256) developer path is reachable only when
#               AUTH_MODE=local-dev AND ENVIRONMENT is not a deployed tier.
#   INV-OIDC-4  JWKS keys are cached with TTL and re-fetched on a kid miss;
#               key rotation does not require a restart.
#
# This module is transport-agnostic. The FastAPI binding lives in the gateway.
from __future__ import annotations

import os
import threading
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientError

__all__ = [
    "AuthConfigError",
    "AuthError",
    "LocalDevVerifier",
    "OIDCSettings",
    "Principal",
    "TokenVerifier",
    "Verifier",
    "build_verifier_from_env",
]

# Tiers on which a weakened (symmetric) auth path must never be reachable.
_DEPLOYED_TIERS = frozenset({"production", "prod", "staging", "stage"})


class AuthConfigError(RuntimeError):
    """Raised at startup when required auth configuration is missing/invalid.

    Surfacing this aborts process start (fail-closed). It must never be caught
    and downgraded to a permissive default.
    """


class AuthError(Exception):
    """Raised at request time when a token is absent or fails verification.

    Carries a stable, non-leaking ``code`` suitable for a 401 response. The
    human-readable message is for logs, not for the client body.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Principal:
    """The authenticated caller, derived from verified claims.

    ``roles`` feeds the downstream RBAC choke point (ISSUE 016). Identity is
    established here; authorization is decided there.
    """

    subject: str
    roles: tuple[str, ...]
    scopes: tuple[str, ...]
    claims: Mapping[str, Any]


class Verifier(Protocol):
    """Common surface for production and local-dev verifiers."""

    def verify(self, token: str) -> Principal: ...


def _split_scope(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(p for p in value.split() if p)
    if isinstance(value, Iterable):
        return tuple(str(p) for p in value if str(p))
    return ()


def _dotted_get(claims: Mapping[str, Any], path: str) -> Any:
    """Resolve a dotted claim path, e.g. 'realm_access.roles' (Keycloak)."""
    cur: Any = claims
    for part in path.split("."):
        if not isinstance(cur, Mapping) or part not in cur:
            return None
        cur = cur[part]
    return cur


@dataclass(frozen=True)
class OIDCSettings:
    """Immutable verification settings."""

    issuer: str
    audience: str
    jwks_url: str
    algorithms: tuple[str, ...] = ("RS256",)
    leeway_seconds: int = 30
    jwks_cache_ttl: int = 600
    roles_claim: str = "roles"
    scope_claim: str = "scope"
    required_scopes: tuple[str, ...] = ()

    @staticmethod
    def from_env() -> OIDCSettings:
        issuer = os.getenv("OIDC_ISSUER", "").strip()
        audience = os.getenv("OIDC_AUDIENCE", "").strip()
        jwks_url = os.getenv("OIDC_JWKS_URL", "").strip()
        missing = [
            name
            for name, val in (
                ("OIDC_ISSUER", issuer),
                ("OIDC_AUDIENCE", audience),
                ("OIDC_JWKS_URL", jwks_url),
            )
            if not val
        ]
        if missing:
            raise AuthConfigError(
                "Missing required OIDC configuration: " + ", ".join(missing)
            )
        algorithms = tuple(
            a.strip()
            for a in os.getenv("OIDC_ALGORITHMS", "RS256").split(",")
            if a.strip()
        )
        required_scopes = tuple(
            s.strip()
            for s in os.getenv("OIDC_REQUIRED_SCOPES", "").split(",")
            if s.strip()
        )
        return OIDCSettings(
            issuer=issuer,
            audience=audience,
            jwks_url=jwks_url,
            algorithms=algorithms or ("RS256",),
            leeway_seconds=int(os.getenv("OIDC_LEEWAY_SECONDS", "30")),
            jwks_cache_ttl=int(os.getenv("OIDC_JWKS_CACHE_TTL", "600")),
            roles_claim=os.getenv("OIDC_ROLES_CLAIM", "roles"),
            scope_claim=os.getenv("OIDC_SCOPE_CLAIM", "scope"),
            required_scopes=required_scopes,
        )


class _JwksKeyResolver:
    """Resolve the verifying key for a token via JWKS, with TTL + kid-miss refresh.

    Wraps PyJWKClient. On a signing-key miss (e.g. just-rotated key), forces one
    refresh before failing, so rotation does not require a restart (INV-OIDC-4).
    """

    def __init__(self, jwks_url: str, ttl: int) -> None:
        self._jwks_url = jwks_url
        self._ttl = ttl
        self._lock = threading.Lock()
        self._client = PyJWKClient(jwks_url, cache_keys=True, lifespan=ttl)
        self._created = time.monotonic()

    def _rebuild(self) -> None:
        self._client = PyJWKClient(self._jwks_url, cache_keys=True, lifespan=self._ttl)
        self._created = time.monotonic()

    def __call__(self, token: str) -> Any:
        try:
            return self._client.get_signing_key_from_jwt(token).key
        except PyJWKClientError as exc:
            # One forced refresh to honor key rotation without a restart.
            with self._lock:
                self._rebuild()
            try:
                return self._client.get_signing_key_from_jwt(token).key
            except PyJWKClientError as exc2:
                raise AuthError(
                    "invalid_token", f"no usable signing key: {exc2}"
                ) from exc


class TokenVerifier:
    """Asymmetric (JWKS) token verifier — the production path.

    The ``key_resolver`` indirection exists for testability: production wires the
    JWKS resolver; tests inject a deterministic key. Verification semantics are
    identical regardless of resolver.
    """

    def __init__(self, settings: OIDCSettings, key_resolver: Any | None = None) -> None:
        self._s = settings
        self._resolve_key = key_resolver or _JwksKeyResolver(
            settings.jwks_url, settings.jwks_cache_ttl
        )

    def verify(self, token: str) -> Principal:
        if not token:
            raise AuthError("missing_token", "no bearer token presented")
        try:
            key = self._resolve_key(token)
        except AuthError:
            raise
        except Exception as exc:  # - any resolver failure is fail-closed
            raise AuthError("invalid_token", f"key resolution failed: {exc}") from exc

        try:
            claims = jwt.decode(
                token,
                key=key,
                algorithms=list(self._s.algorithms),
                audience=self._s.audience,
                issuer=self._s.issuer,
                leeway=self._s.leeway_seconds,
                options={
                    "require": ["exp", "iat"],
                    "verify_signature": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "verify_exp": True,
                    "verify_nbf": True,  # validated only if the claim is present
                },
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthError("token_expired", str(exc)) from exc
        except jwt.InvalidAudienceError as exc:
            raise AuthError("invalid_audience", str(exc)) from exc
        except jwt.InvalidIssuerError as exc:
            raise AuthError("invalid_issuer", str(exc)) from exc
        except jwt.ImmatureSignatureError as exc:
            raise AuthError("token_not_yet_valid", str(exc)) from exc
        except jwt.InvalidTokenError as exc:
            raise AuthError("invalid_token", str(exc)) from exc

        return self._to_principal(claims)

    def _to_principal(self, claims: Mapping[str, Any]) -> Principal:
        subject = str(claims.get("sub") or "")
        if not subject:
            raise AuthError("invalid_token", "token has no subject")
        roles_raw = _dotted_get(claims, self._s.roles_claim)
        roles = (
            tuple(str(r) for r in roles_raw)
            if isinstance(roles_raw, list | tuple)
            else _split_scope(roles_raw)
        )
        scopes = _split_scope(claims.get(self._s.scope_claim))
        if self._s.required_scopes and not set(self._s.required_scopes).issubset(
            scopes
        ):
            raise AuthError("insufficient_scope", "required scope not present")
        return Principal(
            subject=subject, roles=roles, scopes=scopes, claims=dict(claims)
        )


class LocalDevVerifier:
    """Symmetric (HS256) verifier — developer convenience ONLY.

    Constructed solely by build_verifier_from_env() under an explicit local mode
    that deployed tiers refuse (INV-OIDC-3). Never the default. Identity rigor is
    identical to production: a subject is required.
    """

    def __init__(
        self, secret: str, audience: str, issuer: str, leeway: int = 30
    ) -> None:
        if not secret:
            raise AuthConfigError("local-dev auth requires ASTRADESK_DEV_JWT_SECRET")
        self._secret = secret
        self._audience = audience
        self._issuer = issuer
        self._leeway = leeway

    def verify(self, token: str) -> Principal:
        if not token:
            raise AuthError("missing_token", "no bearer token presented")
        try:
            claims = jwt.decode(
                token,
                key=self._secret,
                algorithms=["HS256"],
                audience=self._audience,
                issuer=self._issuer,
                leeway=self._leeway,
                options={"require": ["exp", "iat"], "verify_signature": True},
            )
        except jwt.InvalidTokenError as exc:
            raise AuthError("invalid_token", str(exc)) from exc
        subject = str(claims.get("sub") or "")
        if not subject:
            raise AuthError("invalid_token", "token has no subject")
        roles = _split_scope(claims.get("roles"))
        scopes = _split_scope(claims.get("scope"))
        return Principal(
            subject=subject,
            roles=roles,
            scopes=scopes,
            claims=dict(claims),
        )


def build_verifier_from_env() -> Verifier:
    """Construct the ingress verifier from environment, fail-closed.

    Production (default): requires full OIDC config; returns a JWKS TokenVerifier.
    local-dev: only when AUTH_MODE=local-dev AND ENVIRONMENT is not a deployed
    tier; returns a symmetric LocalDevVerifier. Any deployed tier requesting
    local-dev aborts startup.
    """
    auth_mode = os.getenv("AUTH_MODE", "production").strip().lower()
    environment = os.getenv("ENVIRONMENT", "production").strip().lower()

    if auth_mode == "local-dev":
        if environment in _DEPLOYED_TIERS:
            raise AuthConfigError(
                f"AUTH_MODE=local-dev is forbidden on tier '{environment}'"
            )
        return LocalDevVerifier(
            secret=os.getenv("ASTRADESK_DEV_JWT_SECRET", ""),
            audience=os.getenv("OIDC_AUDIENCE", "astradesk-local"),
            issuer=os.getenv("OIDC_ISSUER", "astradesk-local"),
        )

    if auth_mode != "production":
        raise AuthConfigError(f"unknown AUTH_MODE: {auth_mode!r}")

    return TokenVerifier(OIDCSettings.from_env())
