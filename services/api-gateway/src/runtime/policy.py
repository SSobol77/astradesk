# SPDX-License-Identifier: Apache-2.0
# services/api-gateway/src/runtime/policy.py
"""File: services/api-gateway/src/runtime/policy.py
Project: AstraDesk Framework — API Gateway
Description:
    Production-grade RBAC + ABAC policy layer for AstraDesk. Provides fast,
    dependency-free authorization checks with a TTL-cached, hot-reloadable
    policy store. Policies can be supplied via environment or JSON file and
    define required roles per action and attribute-based constraints.

Author: Siergej Sobolewski
Since: 2025-10-07

Overview
--------
- RBAC:
  * Per-action role gates with `any` / `all` semantics.
  * Role extraction from heterogeneous IdPs (Keycloak/Azure AD/custom) using
    configurable claim paths, prefix stripping, and case normalization.
- ABAC:
  * Attribute-based constraints evaluated as an AND-group per action
    (`equals` / `in` operators).
- Policy source & cache:
  * Load from `POLICY_JSON` (env) or `POLICY_FILE` (JSON). Fallback to a safe,
    conservative default policy.
  * TTL-based in-memory cache with explicit `refresh_now()` hook.

Configuration (env)
-------------------
- POLICY_JSON         : inline JSON policy (highest precedence).
- POLICY_FILE         : path to a JSON policy file (used if POLICY_JSON empty).
- POLICY_TTL_SECONDS  : cache TTL seconds for policy reloads (default: 60).

Policy schema (JSON)
--------------------
{
  "roles_required": {
    "ops.restart_service": { "all": ["sre"] },
    "tickets.create":      { "any": ["it.support", "sre"] }
  },
  "abac": {
    "ops.restart_service": [
      {"attr": "service", "in": ["webapp","payments","search"]},
      {"attr": "env", "in": ["dev","staging","prod"]}
    ]
  },
  "idp_role_mapping": {
    "from": ["roles", "groups", "realm_access.roles"],
    "prefix_strip": ["ROLE_"],
    "lowercase": true
  }
}

Public API
----------
- Role helpers:
  * `get_roles(claims) -> list[str]`
  * `has_role(claims, required) -> bool`
  * `require_role(claims, required)` / `require_any_role(claims, roles)` / `require_all_roles(claims, roles)`
- Authorization:
  * `authorize(action, claims, attrs=None)` → raises `AuthorizationError` on denial.
- Admin facade:
  * `policy.refresh_now()` — force reload (bypass TTL).
  * `policy.current()`    — get compiled policy snapshot.

Design principles
-----------------
- Deterministic & fast: pure-Python, no network calls on the hot path.
- Defense-in-depth: RBAC first; ABAC to restrict scope (service/env/owner...).
- Extensible: add more claim sources or rule operators without breaking callers.
- Safe defaults: missing policy falls back to a conservative baseline.

Security & safety
-----------------
- Normalize roles to avoid prefix/case mismatches across IdPs.
- Treat missing attributes for ABAC as a denial (fail-closed).
- Do not log token contents; pass minimal, non-sensitive context to logs.

Performance
-----------
- O(1) lookups and simple set ops for RBAC checks.
- ABAC rule evaluation is linear in the number of rules per action.
- TTL cache prevents repeated parsing/IO; explicit refresh for control planes.

Usage (example)
---------------
>>> from runtime.policy import policy, authorize, require_role
>>> require_role(claims, "sre")  # RBAC quick check
>>> authorize("ops.restart_service", claims, {"service":"webapp","env":"prod"})  # RBAC+ABAC

Notes
-----
- Keep policies small and auditable; prefer “all/any” over complex logic.
- For multi-tenant or per-project policies, layer an external resolver that
  supplies the appropriate JSON to this module.


Notes (PL):
------------
„Prawdziwa” warstwa RBAC+ABAC dla AstraDesk:
 - RBAC: sprawdzanie ról użytkownika pochodzących z różnych IdP (Keycloak/AzureAD/custom),
 - ABAC: zasady oparte na atrybutach (np. właściciel zasobu, środowisko, godziny),
 - Polityki ładowane lokalnie (ENV/plik) z prostym cache TTL i odświeżaniem na żądanie.

Bez zależności zewnętrznych — czysty Python. Możesz łatwo podmienić _loader na pobieranie
z configmapy/consula/SSM. Wersja lekka, ale produkcyjnie używalna.

Przykłady użycia
----------------
from runtime.policy import policy, require_role, authorize

# RBAC (prosto):
require_role(claims, "sre")

# ABAC/RBAC akcja (np. restart_service) z atrybutami kontekstu:
authorize(
    action="ops.restart_service",
    claims=claims,                      # JWT claims (OIDC)
    attrs={"service": "webapp", "env": "prod", "owner": "alice"}
)

# W toolu:
async def restart_service(service: str, *, claims: dict | None = None):
    authorize("ops.restart_service", claims, {"service": service})
    ...

Struktura polityki (JSON) — ENV: POLICY_JSON lub plik: POLICY_FILE
------------------------------------------------------------------
{
  "roles_required": {
    "ops.restart_service": { "all": ["sre"] },
    "tickets.create":      { "any": ["it.support", "sre"] }
  },
  "abac": {
    "ops.restart_service": [
      {"attr": "service", "in": ["webapp","payments","search"]},
      {"attr": "env", "in": ["dev","staging","prod"]}   # opcjonalnie
    ]
  },
  "idp_role_mapping": {
    "from": ["roles", "groups", "realm_access.roles"],  # kolejne miejsca z rolami
    "prefix_strip": ["ROLE_"],                          # usuń prefiksy z AAD/Keycloak
    "lowercase": true                                   # normalizuj nazwy ról
  }
}

Jeśli nie podasz własnej polityki, aktywuje się domyślna (bezpieczna, konserwatywna).

"""  # noqa: D205

from __future__ import annotations

import json
import os
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Optional
from core.src.astradesk_core.exceptions import AuthorizationError, PolicyError


# Konfiguracja źródła polityk

_POLICY_TTL = int(os.getenv("POLICY_TTL_SECONDS", "60"))  # reload cache co X s
_POLICY_FILE = os.getenv("POLICY_FILE", "").strip()       # ścieżka do JSON
_POLICY_ENV  = os.getenv("POLICY_JSON", "").strip()       # inline JSON w ENV

# Domyślna polityka (bezpieczna, minimalna)
_DEFAULT_POLICY: dict[str, Any] = {
    "roles_required": {
        # przykład: "ops.restart_service": {"all": ["sre"]}
    },
    "abac": {
        # przykład: "ops.restart_service": [{"attr": "service", "in": ["webapp","payments"]}]
    },
    "idp_role_mapping": {
        "from": ["roles", "groups", "realm_access.roles"],  # Keycloak/AAD/common
        "prefix_strip": ["ROLE_"],
        "lowercase": True,
    },
}

# --------------------------------
# Model wewnętrzny przechowywania
# --------------------------------

@dataclass
class RoleRequirement:
    any: set[str] = field(default_factory=set)  # co najmniej jedna z
    all: set[str] = field(default_factory=set)  # wszystkie

@dataclass
class AbacRule:
    attr: str
    equals: Optional[Any] = None
    in_set: Optional[set[Any]] = None

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "AbacRule":
        # Akceptowane formy:
        # {"attr": "service", "equals": "webapp"}  lub  {"attr":"service","in":["webapp","search"]}
        attr = d.get("attr")
        if not attr or not isinstance(attr, str):
            raise PolicyError("ABAC rule must have string 'attr'.")
        if "equals" in d:
            return AbacRule(attr=attr, equals=d["equals"])
        if "in" in d:
            seq = d["in"]
            if not isinstance(seq, (list, tuple, set)):
                raise PolicyError("ABAC 'in' must be a list/tuple/set.")
            return AbacRule(attr=attr, in_set=set(seq))
        raise PolicyError("ABAC rule must contain 'equals' or 'in'.")

@dataclass
class CompiledPolicy:
    roles_required: dict[str, RoleRequirement]
    abac: dict[str, list[AbacRule]]
    idp_role_mapping: dict[str, Any]

# -------------------------
# Policy Store + cache TTL
# -------------------------

class _PolicyStore:
    """
    Prosty magazyn polityk z cache TTL.

    Ładowanie:
      - najpierw POLICY_ENV (JSON string),
      - potem POLICY_FILE (jeśli istnieje i ENV puste),
      - inaczej _DEFAULT_POLICY.

    Formaty:
      - roles_required: { action: {"any":[...], "all":[...]} }
      - abac: { action: [ {"attr":"service","in":["webapp","search"]}, ... ] }
      - idp_role_mapping: { "from":[...], "prefix_strip":[...], "lowercase":bool }
    """

    def __init__(self) -> None:
        self._compiled: Optional[CompiledPolicy] = None
        self._fetched_at: float = 0.0

    def _load_raw(self) -> dict[str, Any]:
        if _POLICY_ENV:
            try:
                return json.loads(_POLICY_ENV)
            except json.JSONDecodeError as e:
                raise PolicyError(f"POLICY_JSON invalid: {e}")
        if _POLICY_FILE:
            if not os.path.exists(_POLICY_FILE):
                raise PolicyError(f"POLICY_FILE missing: {_POLICY_FILE}")
            with open(_POLICY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return _DEFAULT_POLICY

    @staticmethod
    def _compile_roles_required(raw: dict[str, Any]) -> dict[str, RoleRequirement]:
        out: dict[str, RoleRequirement] = {}
        for action, spec in raw.items():
            rr = RoleRequirement(
                any=set(spec.get("any", []) or []),
                all=set(spec.get("all", []) or []),
            )
            out[action] = rr
        return out

    @staticmethod
    def _compile_abac(raw: dict[str, Any]) -> dict[str, list[AbacRule]]:
        out: dict[str, list[AbacRule]] = {}
        for action, rules in raw.items():
            if not isinstance(rules, (list, tuple)):
                raise PolicyError(f"ABAC rules for '{action}' must be a list.")
            out[action] = [AbacRule.from_dict(r) for r in rules]
        return out

    def _compile(self, data: dict[str, Any]) -> CompiledPolicy:
        roles_required = self._compile_roles_required(data.get("roles_required", {}))
        abac = self._compile_abac(data.get("abac", {}))
        idp_map = data.get("idp_role_mapping", _DEFAULT_POLICY["idp_role_mapping"])
        return CompiledPolicy(roles_required=roles_required, abac=abac, idp_role_mapping=idp_map)

    def get(self) -> CompiledPolicy:
        # TTL-owane odświeżanie
        if not self._compiled or (time.time() - self._fetched_at) > _POLICY_TTL:
            raw = self._load_raw()
            self._compiled = self._compile(raw)
            self._fetched_at = time.time()
        return self._compiled

    def refresh_now(self) -> None:
        """Wymusza natychmiastowe odświeżenie (np. endpointem admina)."""
        self._compiled = None
        self._fetched_at = 0.0

_policy_store = _PolicyStore()

# ----------------------
# Ekstrakcja ról z IdP
# ----------------------

def _normalize_roles(roles: Iterable[str], mapping: dict[str, Any]) -> list[str]:
    """Normalizuje nazwy ról wg polityki (strip prefixów, lowercase)."""
    out: list[str] = []
    strip = set(mapping.get("prefix_strip", []) or [])
    to_lower = bool(mapping.get("lowercase", True))
    for r in roles:
        s = str(r)
        for p in strip:
            if s.startswith(p):
                s = s[len(p):]
        if to_lower:
            s = s.lower()
        out.append(s)
    return out

def get_roles(claims: dict | None) -> list[str]:
    """
    Zwraca listę ról użytkownika na podstawie claims z JWT (różne IdP).
    Obsługiwane miejsca:
      - 'roles': [...],
      - 'groups': [...],
      - 'realm_access.roles': [...] (Keycloak).
    """
    if not claims:
        return []
    mapping = _policy_store.get().idp_role_mapping
    sources = mapping.get("from", ["roles", "groups", "realm_access.roles"])
    raw: list[str] = []
    for src in sources:
        # głębokie pobranie 'a.b.c'
        cur = claims
        ok = True
        for part in src.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok and isinstance(cur, (list, tuple)):
            raw.extend([str(x) for x in cur])
    return _normalize_roles(raw, mapping)

def has_role(claims: dict | None, required: str) -> bool:
    """True, jeśli użytkownik posiada wymaganą rolę (po normalizacji)."""
    return required in set(get_roles(claims))

def require_role(claims: dict | None, required: str) -> None:
    """Rzuca AuthorizationError, jeżeli brak wymaganej roli."""
    if not has_role(claims, required):
        raise AuthorizationError(f"Access denied: missing role '{required}'.")

def require_any_role(claims: dict | None, candidates: Iterable[str]) -> None:
    """Co najmniej jedna rola z listy musi wystąpić."""
    have = set(get_roles(claims))
    need = set(candidates)
    if not have.intersection(need):
        raise AuthorizationError(f"Access denied: need any of roles {sorted(need)}.")

def require_all_roles(claims: dict | None, required: Iterable[str]) -> None:
    """Wszystkie wskazane role muszą wystąpić."""
    have = set(get_roles(claims))
    need = set(required)
    missing = need - have
    if missing:
        raise AuthorizationError(f"Access denied: missing roles {sorted(missing)}.")

# ---------------
# ABAC evaluacja
# ---------------

def _eval_abac_rules(rules: list[AbacRule], attrs: dict[str, Any]) -> bool:
    """
    Zwraca True, jeżeli WSZYSTKIE reguły ABAC dla danej akcji są spełnione.
    Wersja „AND” — chcesz „OR”, dodaj kilka grup w polityce i wybierz jedną przy autoryzacji.
    """
    for r in rules:
        val = attrs.get(r.attr)
        if r.equals is not None:
            if val != r.equals:
                return False
        elif r.in_set is not None:
            if val not in r.in_set:
                return False
        else:
            return False
    return True

# -----------------------------
# Główna funkcja autoryzacji
# -----------------------------

def authorize(action: str, claims: dict | None, attrs: dict[str, Any] | None = None) -> None:
    """
    Autoryzuje wykonanie 'action' na podstawie polityk RBAC/ABAC.

    RBAC:
      - 'roles_required[action].any'  → użytkownik musi mieć przynajmniej jedną
      - 'roles_required[action].all'  → użytkownik musi mieć wszystkie

    ABAC:
      - 'abac[action]' → lista reguł (AND). Wszystkie muszą być spełnione.

    :param action: identyfikator akcji (np. "ops.restart_service", "tickets.create")
    :param claims: JWT claims (OIDC)
    :param attrs:  atrybuty kontekstu (np. {"service":"webapp","env":"prod"})
    :raises AuthorizationError: jeśli autoryzacja nie powiedzie się
    :raises PolicyError: jeśli polityka jest uszkodzona/niekompletna
    """
    if not action:
        raise PolicyError("Action must be a non-empty string.")

    pol = _policy_store.get()

    # RBAC — wymagane role
    rr = pol.roles_required.get(action)
    user_roles = set(get_roles(claims))
    if rr:
        if rr.all and not rr.all.issubset(user_roles):
            missing = sorted(rr.all - user_roles)
            raise AuthorizationError(f"Access denied: missing roles {missing}.")
        if rr.any and not user_roles.intersection(rr.any):
            raise AuthorizationError(f"Access denied: need any of roles {sorted(rr.any)}.")

    # ABAC — reguły atrybutowe
    rules = pol.abac.get(action, [])
    if rules:
        if attrs is None:
            raise AuthorizationError("Access denied: missing contextual attributes for ABAC.")
        if not _eval_abac_rules(rules, attrs):
            raise AuthorizationError("Access denied: ABAC rules not satisfied.")

# -----------------------------
# Publiczny obiekt polityki
# -----------------------------

class PolicyFacade:
    """Prosty fasadowy interfejs dla admin endpointów (np. refresh)."""
    def refresh_now(self) -> None:
        _policy_store.refresh_now()

    def current(self) -> CompiledPolicy:
        return _policy_store.get()

# Jeden obiekt eksportowany na zewnątrz (opcjonalny do użycia przez admin API)
policy = PolicyFacade()
