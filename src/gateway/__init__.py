# SPDX-License-Identifier: Apache-2.0
"""File: services/gateway-python/src/gateway/__init__.py
Project: AstraDesk Framework — API Gateway
Description:
    Top-level package initializer for the `gateway` module.

    Responsibilities:
    - Define the public API surface (`__all__`) and re-exports for convenience.
    - Expose package metadata (`__version__`, `__description__`, etc.).
    - Provide safe, lazy imports for heavier submodules to keep import time low.
    - Avoid side effects (no logging config, no network/file I/O on import).

Package layout (excerpt):
    gateway/
      __init__.py          ← you are here
      orchestrator.py      ← domain/business logic for agent orchestration
      # main.py lives outside the package: services/gateway-python/app/main.py

Notes:
    - Keep this file minimal and import-only; no runtime setup.
    - Prefer lazy attribute loading to prevent circular imports in tests/apps.

Notes PL: Inicjalizator pakietu `gateway` dla aplikacji AstraDesk.

    Ten plik pełni rolę fasady, definiując publiczne API pakietu `gateway`
    i wykorzystując zaawansowane techniki, takie jak leniwe importy, w celu
    optymalizacji wydajności i unikania zależności cyklicznych.

    Główne cechy:
    - **Leniwe Importy (Lazy Imports)**: Kluczowe komponenty, jak `AgentOrchestrator`,
    są importowane dopiero przy pierwszym użyciu, co minimalizuje czas startu.
    - **Statyczne Typowanie**: Pełne wsparcie dla narzędzi do analizy typów
    (Mypy, Pylance) dzięki warunkowym importom w bloku `TYPE_CHECKING`.
    - **Dynamiczne Metadane**: Wersja pakietu jest odczytywana dynamicznie
    z metadanych instalacyjnych, zgodnie ze standardem PEP 396.

"""  # noqa: D205
from __future__ import annotations

import importlib
import importlib.metadata as _metadata
import sys
from typing import TYPE_CHECKING, Any

# -----------------------------------------------------------------------------
# Metadane Pakietu
# -----------------------------------------------------------------------------

# UWAGA: Ta nazwa musi być identyczna z polem `name` w `pyproject.toml`
# w sekcji `[project]`, aby odczyt wersji działał poprawnie.
__pkg_name__ = "astradesk"
__description__ = "AstraDesk API Gateway — orchestration layer and HTTP adapters."
__author__ = "Siergej Sobolewski"
__license__ = "Apache-2.0"

try:
    __version__ = _metadata.version(__pkg_name__)
except _metadata.PackageNotFoundError:
    # Fallback używany w środowiskach deweloperskich, gdzie pakiet
    # nie jest formalnie zainstalowany.
    __version__ = "0.0.0-dev"

# -----------------------------------------------------------------------------
# Definicja Publicznego API (`__all__`)
# -----------------------------------------------------------------------------

__all__ = (
    # Główne komponenty (ładowane leniwie)
    "AgentOrchestrator",
    "__pkg_name__",
    # Metadane
    "__version__",
    # Funkcje pomocnicze
    "get_package_info",
)

# -----------------------------------------------------------------------------
# Importy tylko dla Analizatorów Typów
# -----------------------------------------------------------------------------

# Ten blok jest ignorowany podczas normalnego uruchamiania, ale pozwala
# IDE i Mypy na zrozumienie typów, które są ładowane leniwie.
if TYPE_CHECKING:  # pragma: no cover
    from .orchestrator import AgentOrchestrator


# -----------------------------------------------------------------------------
# Mechanizm Leniwego Ładowania (PEP 562)
# -----------------------------------------------------------------------------

def __getattr__(name: str) -> Any:
    """Ładuje atrybuty z submodułów w sposób leniwy przy pierwszym dostępie.

    Args:
        name: Nazwa atrybutu do załadowania (np. "AgentOrchestrator").

    Returns:
        Żądany obiekt (klasa, funkcja, etc.).

    Raises:
        AttributeError: Jeśli atrybut nie jest zdefiniowany do leniwego ładowania.

    """
    if name == "AgentOrchestrator":
        module = importlib.import_module(".orchestrator", __name__)

        # Używamy bezpośredniego dostępu do atrybutu.
        # Jest to czystsze i bardziej zgodne z duchem Pythona.
        obj = module.AgentOrchestrator

        # Cache'owanie wyniku w globalnym zakresie modułu.
        globals()[name] = obj
        return obj

    raise AttributeError(f"Moduł '{__name__}' nie posiada atrybutu '{name}'.")


# -----------------------------------------------------------------------------
# Funkcje Pomocnicze
# -----------------------------------------------------------------------------

def get_package_info() -> dict[str, str]:
    """Zwraca słownik z metadanymi pakietu.

    Przydatne dla endpointów `/health` lub `/info` do weryfikacji
    wersji wdrożonej aplikacji.

    Przykład:
        >>> from gateway import get_package_info
        >>> info = get_package_info()
        >>> print(info['version'])
        '0.2.1'
    """
    return {
        "name": __pkg_name__,
        "version": __version__,
        "license": __license__,
        "description": __description__,
        "python_version": sys.version.split()[0],
    }
