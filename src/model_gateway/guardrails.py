# src/model_gateway/guardrails.py
"""Moduł implementujący podstawowe zabezpieczenia (guardrails).

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
"""
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
