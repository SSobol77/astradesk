# SPDX-License-Identifier: Apache-2.0
# services/api-gateway/src/model_gateway/guardrails.py
"""File: services/api-gateway/src/model_gateway/guardrails.py
Project: AstraDesk Framework — API Gateway
Description:
    Core guardrails for validating inputs and normalizing LLM outputs before they
    reach orchestration or tool execution layers. Provides intent filtering,
    JSON/schema validation for model-produced plans, and safe output clipping.

Author: Siergej Sobolewski
Since: 2025-10-07

Overview
--------
- Intent filtering: detect potentially dangerous patterns (e.g., shell/SQL abuse).
- Plan validation: ensure LLM-produced plans are valid JSON and conform to a
  strict Pydantic schema (`PlanModel` → list of typed `PlanStepModel`).
- Output clipping: truncate overly long text safely with ellipsis.

Design principles
-----------------
- Fail closed: reject unsafe or malformed content early and explicitly.
- Keep policies transparent: patterns and schemas are code-reviewed artifacts.
- Side-effect free: pure functions suitable for synchronous and async contexts.
- Extensible: patterns and schemas can evolve without touching call sites.

Security & safety
-----------------
- Normalize and validate inputs before any tool invocation or DB access.
- Treat guardrails as a *first line of defense* within a layered security model.
- Never log secrets; redact user content when needed. Log only minimal context.

Performance
-----------
- Regexes compiled at import for low-overhead checks.
- Pydantic validation is fast for small/medium payloads; avoid giant blobs.
- Use guardrails on the hot path, but keep schemas lean and focused.

Usage (example)
---------------
>>> if not is_safe_input(user_text):
...     raise ValueError("Unsafe input detected")
>>> plan = validate_plan_json(model_output_json)  # returns PlanModel
>>> preview = clip_output(render(plan), max_chars=2_000)

Notes
-----
- This module does not replace WAF, IAM, or network policies—use it alongside
  upstream controls (defense in depth).
- Keep schemas tightly scoped to the current planner contract and update them
  together with planner changes.

Notes (PL):
-----------
Moduł implementujący podstawowe zabezpieczenia (guardrails).

Ten moduł dostarcza zestaw funkcji stanowiących pierwszą linię obrony
przed niepożądanymi lub potencjalnie złośliwymi danymi wejściowymi oraz
zapewnia, że dane wyjściowe z modeli LLM mają poprawną strukturę.

Funkcjonalności:
- **Filtrowanie intencji**: Identyfikuje potencjalnie niebezpieczne
  wzorce w zapytaniach użytkownika (np. próby SQL injection, polecenia systemowe).
- **Walidacja struktury**: Weryfikuje, czy odpowiedź LLM (plan działania)
  jest poprawnym formatem JSON i pasuje do zdefiniowanego schematu Pydantic.
- **Narzędzia pomocnicze**: Funkcje do przycinania zbyt długich odpowiedzi.

Uwaga: Te zabezpieczenia nie stanowią kompletnego rozwiązania bezpieczeństwa,
ale są kluczowym elementem warstwowej strategii obronnej (defense in depth).

"""  # noqa: D205

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

# Zestaw skompilowanych wyrażeń regularnych do wykrywania potencjalnie
# niebezpiecznych wzorców. Użycie `re.IGNORECASE` i `\b` (granica słowa)
# czyni je znacznie trudniejszymi do obejścia niż proste porównanie stringów.
DANGEROUS_PATTERNS = [
    re.compile(r"\bdrop\s+database\b", re.IGNORECASE),
    re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
    re.compile(r"\bshutdown\b", re.IGNORECASE),
    re.compile(r"\bformat\s+c:", re.IGNORECASE),
    re.compile(r"';\s*--", re.IGNORECASE),  # Prosty wzorzec SQL injection
]


def is_safe_input(text: str) -> bool:
    """Sprawdza, czy tekst wejściowy nie zawiera potencjalnie złośliwych wzorców.

    Iteruje przez listę `DANGEROUS_PATTERNS` i jeśli znajdzie dopasowanie,
    loguje ostrzeżenie i zwraca False.

    Args:
        text: Tekst wejściowy od użytkownika.

    Returns:
        True, jeśli tekst jest uznany za bezpieczny, w przeciwnym razie False.
    """
    normalized_text = " ".join(text.lower().split())
    for pattern in DANGEROUS_PATTERNS:
        if pattern.search(normalized_text):
            logger.warning(
                "Wykryto potencjalnie niebezpieczny wzorzec! "
                f"Wzorzec: '{pattern.pattern}', Tekst: '{text}'"
            )
            return False
    return True


# Uwaga: Te modele są ściśle powiązane z `llm_planner.py`. W przyszłości
# TODO: można rozważyć przeniesienie ich do wspólnego pliku z modelami planera.
class PlanStepModel(BaseModel):
    """Model Pydantic dla pojedynczego kroku w planie wygenerowanym przez LLM."""
    name: str
    args: Dict[str, Any]


class PlanModel(BaseModel):
    """Model Pydantic dla pełnego planu wygenerowanego przez LLM."""
    steps: List[PlanStepModel]


def validate_plan_json(json_string: str) -> PlanModel:
    """Waliduje, czy string jest poprawnym JSON-em i pasuje do schematu `PlanModel`.

    Funkcja ta jest kluczowym zabezpieczeniem, które gwarantuje, że nieprzewidywalny
    wynik z LLM zostanie przekształcony w ustrukturyzowaną, bezpieczną formę
    przed dalszym przetwarzaniem.

    Args:
        json_string: Surowy string odpowiedzi z modelu LLM.

    Returns:
        Sprawdzona instancja `PlanModel`.

    Raises:
        ValueError: Jeśli string nie jest poprawnym JSON-em lub nie pasuje
            do schematu `PlanModel`.
    """
    try:
        data = json.loads(json_string)
        return PlanModel.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Odpowiedź LLM nie przeszła walidacji JSON lub schematu. Błąd: {e}")
        raise ValueError("Nieprawidłowy format planu JSON otrzymany z LLM.") from e


def clip_output(text: str, max_chars: int = 2000) -> str:
    """Bezpiecznie przycina tekst do maksymalnej dozwolonej długości.

    Args:
        text: Tekst do przycięcia.
        max_chars: Maksymalna liczba znaków.

    Returns:
        Przycięty tekst, zakończony elipsą, jeśli był dłuższy niż limit.
    """
    if max_chars <= 0:
        return "…"
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"
