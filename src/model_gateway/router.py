# src/model_gateway/router.py
"""Centralny router i menedżer cyklu życia dla dostawców modeli LLM.

Ten moduł jest kluczowym komponentem warstwy `model_gateway`. Jego zadaniem
jest stworzenie i zarządzanie **jedną, współdzieloną instancją (singleton)**
aktywnego dostawcy LLM dla całej aplikacji.

Główne cechy i zasady projektowe:
- Wzorzec Singleton: Gwarantuje, że w całej aplikacji istnieje tylko jedna
  instancja klienta LLM (np. jedna sesja `httpx.AsyncClient`), co jest
  kluczowe dla wydajności i prawidłowego zarządzania zasobami.
- Leniwa Inicjalizacja (Lazy Initialization): Instancja providera jest tworzona
  dopiero przy pierwszym żądaniu, a nie przy starcie aplikacji, co przyspiesza
  uruchamianie.
- Bezpieczeństwo Współbieżności: Używa `asyncio.Lock` do ochrony przed
  wyścigami (race conditions) podczas tworzenia pierwszej instancji.
- Architektura Rejestru (Registry Pattern): Dostawcy są dynamicznie
  rejestrowani, co pozwala na łatwe dodawanie nowych providerów bez
  modyfikowania logiki routera (zgodnie z zasadą Open/Closed).
- Zarządzanie Cyklem Życia: Posiada metodę `shutdown`, która powinna być
  wywoływana podczas zamykania aplikacji, aby prawidłowo zamknąć połączenia
  (np. sesję `httpx`).
- Konfiguracja w Czasie Wykonania: Wybór providera odbywa się na podstawie
  zmiennej środowiskowej odczytywanej w momencie tworzenia instancji.

Konfiguracja:
- `MODEL_PROVIDER`: Nazwa dostawcy do aktywacji (np. "openai", "bedrock", "vllm").
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Dict, Type

from .base import LLMProvider
from .providers.bedrock_provider import BedrockProvider
from .providers.openai_provider import OpenAIProvider
from .providers.vllm_provider import VLLMProvider

logger = logging.getLogger(__name__)


class ProviderNotFoundError(KeyError):
    """Wyjątek rzucany, gdy żądany dostawca LLM nie jest zarejestrowany."""

    def __init__(self, provider_name: str):
        super().__init__(
            f"Dostawca LLM '{provider_name}' nie jest zarejestrowany lub nie został znaleziony. "
            f"Sprawdź zmienną środowiskową MODEL_PROVIDER."
        )


class ProviderRouter:
    """Zarządza tworzeniem i cyklem życia pojedynczej instancji dostawcy LLM."""

    __slots__ = ("_providers", "_instance", "_lock")

    def __init__(self) -> None:
        """Inicjalizuje router z rejestrem dostępnych dostawców."""
        self._providers: Dict[str, Type[LLMProvider]] = {}
        self._instance: LLMProvider | None = None
        self._lock = asyncio.Lock()

        # Rejestracja domyślnych dostawców. Dodaj nowych tutaj.
        self.register("openai", OpenAIProvider)
        self.register("bedrock", BedrockProvider)
        self.register("vllm", VLLMProvider)

    def register(self, name: str, provider_class: Type[LLMProvider]) -> None:
        """Rejestruje nową klasę dostawcy pod daną nazwą."""
        self._providers[name.lower()] = provider_class

    async def get_provider(self) -> LLMProvider:
        """Zwraca współdzieloną, leniwie inicjalizowaną instancję dostawcy LLM.

        Implementuje wzorzec singleton z podwójnym sprawdzeniem i blokadą
        asynchroniczną, aby zapewnić bezpieczne utworzenie instancji
        w środowisku współbieżnym.

        Returns:
            Współdzielona instancja aktywnego dostawcy LLM.

        Raises:
            ProviderNotFoundError: Jeśli dostawca określony w `MODEL_PROVIDER`
                nie jest zarejestrowany.
        """
        if self._instance:
            return self._instance

        async with self._lock:
            # Podwójne sprawdzenie na wypadek, gdyby inna korutyna utworzyła
            # instancję, podczas gdy ta czekała na blokadę.
            if self._instance:
                return self._instance

            provider_name = os.getenv("MODEL_PROVIDER", "openai").lower()
            provider_class = self._providers.get(provider_name)

            if not provider_class:
                raise ProviderNotFoundError(provider_name)

            logger.info(f"Inicjalizowanie dostawcy LLM: '{provider_name}'...")
            self._instance = provider_class()
            logger.info(f"Dostawca LLM '{provider_name}' został pomyślnie zainicjalizowany.")
            
            return self._instance

    async def shutdown(self) -> None:
        """Bezpiecznie zamyka aktywnego dostawcę LLM.

        Wywołuje metodę `aclose`, jeśli istnieje, co jest kluczowe dla
        prawidłowego zamknięcia sesji HTTP i zwolnienia zasobów.
        """
        if self._instance:
            logger.info(f"Zamykanie dostawcy LLM: '{self._instance.__class__.__name__}'...")
            # Sprawdzamy, czy provider ma metodę aclose (dobra praktyka)
            if hasattr(self._instance, "aclose") and callable(self._instance.aclose):
                try:
                    await self._instance.aclose()
                    logger.info("Dostawca LLM został pomyślnie zamknięty.")
                except Exception as e:
                    logger.error(f"Wystąpił błąd podczas zamykania dostawcy LLM: {e}", exc_info=True)
            self._instance = None


# Globalna, współdzielona instancja routera, która będzie używana w całej aplikacji.
provider_router = ProviderRouter()
