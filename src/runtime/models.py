# src/runtime/models.py
# -*- coding: utf-8 -*-
# Program jest objęty licencją Apache-2.0.
# Copyright 2025
# Autor: Siergej Sobolewski
"""Definicje modeli danych Pydantic dla aplikacji AstraDesk.

Moduł ten centralizuje wszystkie modele danych używane w kontraktach API
i wewnętrznej logice aplikacji. Zapewnia to spójność, walidację typów
oraz automatyczną serializację/deserializację JSON.

Modele te są zaprojektowane zgodnie z najlepszymi praktykami Pydantic v2,
włączając w to restrykcyjną walidację, opisy dla OpenAPI oraz bezpieczne
wartości domyślne.
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Wzorzec Regex skompilowany na poziomie modułu dla wydajności.
_TOOL_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")


class AstraDeskBaseModel(BaseModel):
    """Wspólna konfiguracja dla wszystkich modeli Pydantic w projekcie."""

    model_config = ConfigDict(
        extra="forbid",  # Odrzucaj nieznane pola w payloadzie.
        str_strip_whitespace=True,  # Automatycznie usuwaj skrajne białe znaki.
        populate_by_name=True,  # Umożliwia używanie aliasów pól.
    )


class ToolCall(AstraDeskBaseModel):
    """Reprezentuje pojedyncze, planowane wywołanie narzędzia.

    Attributes:
        name: Unikalny identyfikator narzędzia z rejestru (ToolRegistry).
        arguments: Słownik argumentów przekazywanych do narzędzia.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Identyfikator narzędzia (np. 'create_ticket', 'ops.restart_service').",
        examples=["create_ticket", "get_metrics"],
    )
    arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="Argumenty wywołania narzędzia w formacie JSON.",
        examples=[{"title": "VPN outage", "body": "Users cannot connect."}],
    )

    @field_validator("name")
    @classmethod
    def _validate_name_format(cls, v: str) -> str:
        """Waliduje, czy nazwa narzędzia ma dozwolony format."""
        if not _TOOL_NAME_PATTERN.fullmatch(v):
            raise ValueError(
                "Nazwa narzędzia może zawierać tylko litery, cyfry, '.', '_' oraz '-'."
            )
        return v


class AgentName(str, Enum):
    """Enumeracja dostępnych typów agentów."""

    SUPPORT = "support"
    OPS = "ops"


class AgentRequest(AstraDeskBaseModel):
    """Model żądania uruchomienia agenta."""

    agent: AgentName = Field(
        ...,
        description="Typ agenta do uruchomienia.",
        examples=[AgentName.SUPPORT, AgentName.OPS],
    )
    input: str = Field(
        ...,
        min_length=1,
        max_length=8192,  # Rozsądny limit dla zapytania.
        description="Zapytanie lub polecenie użytkownika dla agenta.",
        examples=["Utwórz ticket dla incydentu sieciowego.", "Sprawdź metryki CPU dla usługi 'webapp'."],
    )
    meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dowolne metadane kontekstowe (np. ID sesji, claims z OIDC).",
        examples=[{"user_id": "alice", "session_id": "xyz-123"}],
    )


class AgentResponse(AstraDeskBaseModel):
    """Model odpowiedzi agenta.

    Zawiera finalną odpowiedź dla użytkownika oraz metadane diagnostyczne,
    które są kluczowe dla obserwowalności i audytu.
    """

    output: str = Field(
        ...,
        min_length=1,
        max_length=20000,
        description="Finalna, sformatowana odpowiedź agenta dla użytkownika.",
    )
    reasoning_trace_id: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Identyfikator śledzenia (trace ID) dla celów obserwowalności i debugowania.",
        examples=["trace-b7a3c1e9-f8d2-4e1a-9c3d-8b2f0a1d4e5c"],
    )
    invoked_tools: Optional[List[ToolCall]] = Field(
        default=None,
        description="Lista narzędzi, które zostały faktycznie wywołane podczas przetwarzania (nazwa i argumenty). Kluczowe dla audytu.",
        examples=[[{"name": "create_ticket", "arguments": {"title": "VPN outage"}}]],
    )
    errors: Optional[List[str]] = Field(
        default=None,
        description="Lista błędów, które wystąpiły podczas wykonania, ale nie przerwały całego procesu.",
        examples=[["Narzędzie 'get_legacy_metrics' jest przestarzałe."]],
    )