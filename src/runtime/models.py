# src/runtime/models.py
# -*- coding: utf-8 -*-
# Program jest objęty licencją Apache-2.0.
# Copyright 2024
# Autor: Siergej Sobolewski
#
# Cel modułu
# ----------
# Modele danych Pydantic używane w całym systemie AstraDesk.
# Zapewniają spójny kontrakt oraz walidację/serializację JSON dla:
#  - wywołań narzędzi (ToolCall),
#  - żądań i odpowiedzi agentów (AgentRequest, AgentResponse).
#
# Założenia projektowe:
#  - Pydantic v2 (ConfigDict, model_config),
#  - restrykcyjne odrzucanie nieznanych pól (extra="forbid"),
#  - obcinanie białych znaków (str_strip_whitespace=True),
#  - bezpieczne domyślne wartości (default_factory dla list/dict),
#  - krótkie, konkretne opisy (Field.description) ułatwiające generowanie OpenAPI.
#
# Uwaga:
#  - Polityka RBAC/claims nie jest definiowana na poziomie modeli; meta może
#    przenosić dowolny kontekst (np. "claims"), ale decyzje uprawnień pozostają
#    po stronie warstw wyżej (gateway/tools/agents).
#

from __future__ import annotations

from typing import Any, Dict, Literal, List, Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator


class ToolCall(BaseModel):
    """
    Opis pojedynczego wywołania narzędzia (tool) przez agenta.

    Pola:
        name:     identyfikator narzędzia z rejestru (ToolRegistry), np. "create_ticket".
        arguments: parametry wywołania (słownik JSON-serializowalny).

    Walidacja:
        - nazwa narzędzia musi być niepusta,
        - nazwa może zawierać litery/cyfry/_, -, kropki (np. przestrzenie nazw: "ops.restart").
    """

    model_config = ConfigDict(
        extra="forbid",  # nie dopuszczaj nieznanych pól
        str_strip_whitespace=True,
        populate_by_name=True,
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Identifier of the tool (e.g., 'create_ticket', 'ops.restart').",
        examples=["create_ticket", "get_metrics", "ops.restart"],
    )
    arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments for the tool invocation (JSON-serializable).",
        examples=[{"title": "VPN outage", "body": "Users cannot connect via VPN."}],
    )

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        # Prosta walidacja nazwy narzędzia: litery/cyfry/._- (bez spacji)
        import re

        if not re.fullmatch(r"[A-Za-z0-9._-]+", v):
            raise ValueError("Tool name may contain only letters, digits, '.', '_' and '-'.")
        return v


class AgentRequest(BaseModel):
    """
    Żądanie uruchomienia agenta.

    Pola:
        agent:      nazwa/zestaw agenta do uruchomienia (np. "support" lub "ops").
        input:      treść zapytania użytkownika (prompt/komenda) — wymagane.
        tool_calls: lista propozycji wywołań narzędzi (opcjonalnie; zwykle planner decyduje).
        meta:       metadane kontekstu (dowolny JSON), np. identyfikatory sesji, 'claims' OIDC.

    Uwagi:
        - 'tool_calls' typowo pozostaje puste — agent/planner dobierze narzędzia samodzielnie.
        - 'meta' może zawierać 'claims' (dict) przenoszone z middleware OIDC/JWT.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
    )

    agent: Literal["support", "ops"] = Field(
        ...,
        description="Target agent to execute.",
        examples=["support", "ops"],
    )
    input: str = Field(
        ...,
        min_length=1,
        max_length=8000,  # rozsądny limit dla wejścia; dłuższe teksty trzymać w załącznikach/RAG
        description="User query or instruction for the agent.",
        examples=["Utwórz ticket dla incydentu sieci", "Sprawdź metryki CPU webapp"],
    )
    tool_calls: List[ToolCall] = Field(
        default_factory=list,
        description="Optional pre-defined tool invocations (rarely used in normal flow).",
    )
    meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata/context (e.g., session info, OIDC claims).",
        examples=[{"user": "alice", "claims": {"roles": ["it.support"]}}],
    )


class AgentResponse(BaseModel):
    """
    Odpowiedź agenta.

    Pola:
        output:              finalna odpowiedź dla użytkownika (sformatowany tekst).
        reasoning_trace_id:  identyfikator śladu rozumowania/przepływu (dla diagnostyki/observability).
        used_tools:          lista nazw narzędzi dostępnych w środowisku (lub wykorzystanych — zależnie od implementacji).

    Uwagi:
        - 'used_tools' w MVP prezentuje *zarejestrowane* narzędzia; w wersji produkcyjnej
          można rozdzielić 'available_tools' i 'invoked_tools' dla większej przejrzystości.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
    )

    output: str = Field(
        ...,
        min_length=1,
        max_length=20000,
        description="Agent's final answer rendered to the user.",
    )
    reasoning_trace_id: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Trace identifier for observability and debugging.",
        examples=["rt-support-20241003-abc123"],
    )
    used_tools: List[str] = Field(
        default_factory=list,
        description="List of tools available/used during the run (implementation-specific).",
        examples=[["create_ticket", "get_metrics", "restart_service", "get_weather"]],
    )
