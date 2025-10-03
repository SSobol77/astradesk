# src/runtime/auth.py
# -*- coding: utf-8 -*-
# Program jest objęty licencją Apache-2.0.
# Copyright 2024
# Autor: Siergej Sobolewski
#
# Cel modułu:
# ------------
# Zapewnienie weryfikacji tokenów OIDC/JWT po stronie API (warstwa autoryzacji).
# Moduł pobiera klucze publiczne z JWKS (JSON Web Key Set) dostarczanego przez
# dostawcę tożsamości (IdP), cache’uje je na krótki okres i waliduje podpis oraz
# standardowe roszczenia (issuer, audience, exp/nbf/iat).
#
# Szybki skrót użycia:
# --------------------
#   from runtime.auth import cfg
#   claims = await cfg.verify(token_str)   # zwraca dict z payloadem JWT
#
# Wymagane zmienne środowiskowe:
# ------------------------------
#   OIDC_ISSUER   – oczekiwany "iss" (np. "https://login.example.com/")
#   OIDC_AUDIENCE – oczekiwane "aud" (np. "astradesk-api")
#   OIDC_JWKS_URL – URL do JWKS (np. "https://login.example.com/.well-known/jwks.json")
#
# Zależności:
# -----------
#   - python-jose[jwt] — weryfikacja JWT/JWKS
#   - httpx — pobranie JWKS po HTTPS
#
# Bezpieczeństwo:
# ---------------
#   - JWKS jest pobierany okresowo (domyślnie co 1h), co ogranicza liczbę requestów
#     do IdP, ale zapewnia aktualizację kluczy (rotacja).
#   - Walidujemy issuer i audience oraz sygnaturę i standardowe czasy (exp/nbf).
#   - Parametr "leeway" łagodzi drobne różnice zegarów.
#
# Uwaga:
# ------
#   Ten moduł nie implementuje logiki RBAC; do tego służy np. runtime.policy.
#   Tutaj walidujemy tożsamość (kto) i integralność tokena (czy jest ważny).
#

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

import httpx
from jose import jwk, jwt

# ---------------------------------------------------------------------------
# Konfiguracja z ENV
# ---------------------------------------------------------------------------

ISSUER: str = os.getenv("OIDC_ISSUER", "").strip()
AUDIENCE: str = os.getenv("OIDC_AUDIENCE", "").strip()
JWKS_URL: str = os.getenv("OIDC_JWKS_URL", "").strip()

# TTL cache’a dla JWKS (sekundy). Po tym czasie klucze zostaną odświeżone.
JWKS_TTL_SECONDS: int = int(os.getenv("OIDC_JWKS_TTL", "3600"))

# Dopuszczalny dryf zegara (sekundy) przy walidacji exp/nbf/iat.
TIME_SKEW_LEEWAY: int = int(os.getenv("OIDC_TIME_SKEW_LEEWAY", "60"))


class OIDCConfig:
    """
    OIDCConfig enkapsuluje konfigurację OIDC oraz logikę:
    - pobierania i cache’owania JWKS,
    - weryfikacji tokenów JWT względem JWKS/issuer/audience.

    Atrybuty:
        issuer:   Oczekiwany `iss` w tokenie (URL IdP).
        audience: Oczekiwane `aud` w tokenie (identyfikator API / audiencji).
        jwks_url: URL do dokumentu JWKS (lista kluczy publicznych).
        _jwks:    Ostatnio pobrany zestaw kluczy (cache).
        _fetched_at: Znacznik czasu ostatniego pobrania JWKS (epoch seconds).
    """

    def __init__(self, issuer: str, audience: str, jwks_url: str) -> None:
        # Wczesna walidacja konfiguracji pomaga szybciej wykryć błędy w środowisku.
        if not issuer or not audience or not jwks_url:
            raise RuntimeError(
                "Brak wymaganego OIDC configu: ustaw OIDC_ISSUER, OIDC_AUDIENCE, OIDC_JWKS_URL."
            )
        self.issuer = issuer
        self.audience = audience
        self.jwks_url = jwks_url
        self._jwks: Optional[Dict[str, Any]] = None
        self._fetched_at: float = 0.0

    async def _fetch_jwks(self) -> Dict[str, Any]:
        """
        Pobiera dokument JWKS (JSON Web Key Set) z IdP.

        Zwraca:
            Dict[str, Any]: Parsowany JSON JWKS (powinien zawierać pole "keys": [...])

        Wyjątki:
            httpx.HTTPError – w przypadku problemów sieci/HTTP.
        """
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(self.jwks_url)
            resp.raise_for_status()
            return resp.json()

    async def _ensure_jwks(self) -> Dict[str, Any]:
        """
        Zwraca aktualny JWKS, odświeżając cache, jeśli wygasł.

        Zwraca:
            Dict[str, Any]: Aktualny JWKS.
        """
        needs_refresh = (
            self._jwks is None or (time.time() - self._fetched_at) > JWKS_TTL_SECONDS
        )
        if needs_refresh:
            self._jwks = await self._fetch_jwks()
            self._fetched_at = time.time()
        return self._jwks  # type: ignore[return-value]

    async def verify(self, token: str) -> Dict[str, Any]:
        """
        Weryfikuje podpis i roszczenia (claims) tokena JWT.

        Kroki:
        1) Pobranie/caching JWKS.
        2) Odczyt nagłówka JWT i dopasowanie `kid` do klucza w JWKS.
        3) Weryfikacja podpisu oraz `iss`, `aud`, a także standardowych pól czasu
           z dopuszczalnym dryfem zegara (`leeway`).

        Argumenty:
            token (str): Surowy token "Bearer" (bez prefiksu).

        Zwraca:
            Dict[str, Any]: Zweryfikowany payload JWT (claims).

        Wyjątki:
            ValueError: gdy nie znaleziono klucza w JWKS lub brak `kid`/alg.
            jose.JWTError: gdy podpis/claims są niepoprawne.
        """
        if not token:
            raise ValueError("Pusty token")

        # 1) Pobierz JWKS (z cache lub z sieci)
        jwks = await self._ensure_jwks()

        # 2) Dopasuj klucz po `kid` z nagłówka JWT
        headers = jwt.get_unverified_header(token)
        kid = headers.get("kid")
        if not kid:
            raise ValueError("Brak 'kid' w nagłówku JWT")
        alg = headers.get("alg", "RS256")

        key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if not key:
            raise ValueError(f"JWKS key not found dla kid={kid}")

        # 3) Walidacja podpisu i claims
        #    - python-jose zweryfikuje exp/nbf/iat, issuer i audience.
        #    - 'leeway' łagodzi drobne różnice zegara.
        payload: Dict[str, Any] = jwt.decode(
            token,
            key=jwk.construct(key),
            algorithms=[alg],
            audience=self.audience,
            issuer=self.issuer,
            options={
                # Zależnie od IdP "at_hash" bywa nieużywane – wyłączamy jego weryfikację w API.
                "verify_at_hash": False
            },
            leeway=TIME_SKEW_LEEWAY,
        )
        return payload

    def clear_cache(self) -> None:
        """
        Czyści lokalny cache JWKS – przydatne w testach lub wymuszeniu natychmiastowej
        odświeżki kluczy po rotacji po stronie IdP.
        """
        self._jwks = None
        self._fetched_at = 0.0


# Globalna instancja wykorzystywana przez endpointy (FastAPI dependency).
cfg = OIDCConfig(ISSUER, AUDIENCE, JWKS_URL)
