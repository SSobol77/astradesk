# SPDX-License-Identifier: Apache-2.0
"""File: services/gateway-python/src/model_gateway/providers/__init__.py
Project: AstraDesk Framework — API Gateway
Description:
    Package initializer for LLM providers. Exposes concrete provider classes for
    AWS Bedrock, OpenAI, and vLLM via a clean, lazy-loaded public API.

    Responsibilities:
    - Define the public surface (`__all__`) and provide convenient re-exports.
    - Publish package metadata (`__version__`, `__description__`, etc.).
    - Use lazy imports (PEP 562) to minimize import time and avoid cycles.
    - Avoid side effects: no I/O or logging configuration at import time.

Author: Siergej Sobolewski
Since: 2025-10-07

Package layout (excerpt):
    model_gateway/providers/
      __init__.py          ← you are here
      bedrock_provider.py  ← BedrockProvider (AWS Bedrock Runtime)
      openai_provider.py   ← OpenAIProvider (OpenAI/Azure-compatible)
      vllm_provider.py     ← VLLMProvider (OpenAI-compatible vLLM server)

Notes (PL):
-----------
Inicjalizator pakietu `providers` dla Model Gateway.

Ten plik pełni rolę fasady, definiując publiczne API dla wszystkich konkretnych
implementacji dostawców LLM (np. OpenAI, Bedrock). Wykorzystuje zaawansowane
techniki, takie jak leniwe importy, w celu optymalizacji wydajności i
unikania zależności cyklicznych.

Główne cechy:
- **Leniwe Importy (Lazy Imports)**: Klasy providerów są importowane dopiero
  przy pierwszym użyciu, co minimalizuje czas startu aplikacji.
- **Statyczne Typowanie**: Pełne wsparcie dla narzędzi do analizy typów
  (Mypy, Pylance) dzięki warunkowym importom w bloku `TYPE_CHECKING`.
- **Wsparcie dla Autouzupełniania**: Implementacja `__dir__` zapewnia, że
  narzędzia interaktywne poprawnie sugerują leniwie ładowane klasy.
- **Metadane Pakietu**: Eksportuje informacje takie jak wersja, opis i licencja.
- **Brak Efektów Ubocznych**: Nie wykonuje żadnego I/O ani konfiguracji logowania
  podczas importu, co jest kluczowe dla modułów bibliotecznych.

"""  # noqa: D205

from __future__ import annotations

import importlib
import importlib.metadata as _metadata
import sys
from typing import TYPE_CHECKING, Any, Iterable  # noqa: UP035

# -----------------------------------------------------------------------------
# Metadane Pakietu
# -----------------------------------------------------------------------------

# UWAGA: Ta nazwa musi być identyczna z polem `name` w `pyproject.toml`
__pkg_name__ = "astradesk"
__description__ = "AstraDesk Model Gateway — pluggable LLM providers (OpenAI, Bedrock, vLLM)."
__author__ = "Siergej Sobolewski"
__license__ = "Apache-2.0"

try:
    __version__ = _metadata.version(__pkg_name__)
except _metadata.PackageNotFoundError:
    __version__ = "0.0.0-dev"

# -----------------------------------------------------------------------------
# Definicja Publicznego API (`__all__`)
# -----------------------------------------------------------------------------

__all__ = (
    # Główne klasy (ładowane leniwie)
    "BedrockProvider",
    "OpenAIProvider",
    "VLLMProvider",
    # Funkcje pomocnicze
    "get_package_info",
)

# -----------------------------------------------------------------------------
# Importy tylko dla Analizatorów Typów
# -----------------------------------------------------------------------------

if TYPE_CHECKING:  # pragma: no cover
    from .bedrock_provider import BedrockProvider
    from .openai_provider import OpenAIProvider
    from .vllm_provider import VLLMProvider


# -----------------------------------------------------------------------------
# Mechanizm Leniwego Ładowania (PEP 562)
# -----------------------------------------------------------------------------

# Słownik mapujący nazwy atrybutów na ich moduły.
# To podejście jest czystsze i bardziej skalowalne niż łańcuch `if/elif`.
_LAZY_IMPORTS = {
    "BedrockProvider": ".bedrock_provider",
    "OpenAIProvider": ".openai_provider",
    "VLLMProvider": ".vllm_provider",
}


def __getattr__(name: str) -> Any:
    """Ładuje klasy providerów z submodułów w sposób leniwy przy pierwszym dostępie.

    Args:
        name: Nazwa atrybutu do załadowania (np. "OpenAIProvider").

    Returns:
        Żądana klasa providera.

    Raises:
        AttributeError: Jeśli atrybut nie jest zdefiniowany do leniwego ładowania.

    """
    if name in _LAZY_IMPORTS:
        module_path = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path, __name__)

        # Użycie `getattr` jest tutaj poprawne i konieczne, ponieważ `name` jest zmienną.
        obj = getattr(module, name)

        # Cache'owanie wyniku w globalnym zakresie modułu, aby uniknąć
        # ponownego wywołania `__getattr__` dla tego samego atrybutu.
        globals()[name] = obj
        return obj

    raise AttributeError(f"Moduł '{__name__}' nie posiada atrybutu '{name}'.")


def __dir__() -> Iterable[str]:  # pragma: no cover
    """Uzupełnia wynik `dir()` o leniwie ładowane atrybuty.

    Zapewnia to poprawne działanie autouzupełniania w narzędziach
    interaktywnych (np. IPython, Jupyter).
    """
    return sorted(set(globals().keys()) | set(__all__))


# -----------------------------------------------------------------------------
# Funkcje Pomocnicze
# -----------------------------------------------------------------------------

def get_package_info() -> dict[str, str]:
    """Zwraca słownik z metadanymi pakietu dla celów diagnostycznych."""
    return {
        "name": __pkg_name__,
        "version": __version__,
        "license": __license__,
        "description": __description__,
        "python_version": sys.version.split()[0],
    }
