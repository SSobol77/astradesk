# src/model_gateway/providers/vllm_provider.py
"""Dostawca modelu (LLM Provider) dla serwera vLLM.

Ten moduł implementuje interfejs `LLMProvider` do komunikacji z serwerem
inferencyjnym vLLM, który udostępnia API zgodne z OpenAI.

Kluczowe funkcje:
- Asynchroniczna komunikacja z endpointem vLLM przy użyciu `httpx`.
- Pełna zgodność z protokołem `LLMProvider` i modelem `ChatParams`.
- Zaawansowane mapowanie błędów HTTP (4xx/5xx) na wyjątki domenowe
  (np. ProviderServerError, ProviderTimeout).
- Wydajne zarządzanie połączeniami HTTP dzięki współdzielonej sesji.

Konfiguracja (zmienne środowiskowe):
- VLLM_BASE_URL: Bazowy URL serwera vLLM (np. "http://vllm:8000/v1").
- VLLM_MODEL: Nazwa/ścieżka modelu załadowanego w vLLM, która ma być używana.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional, Sequence

import httpx

from ..base import (
    ChatParams,
    LLMMessage,
    LLMProvider,
    ModelGatewayError,
    ProviderOverloaded,
    ProviderServerError,
    ProviderTimeout,
    to_openai_messages,
)

# --- Konfiguracja ---
VLLM_BASE_URL: str = os.getenv("VLLM_BASE_URL", "http://vllm:8000/v1")
VLLM_MODEL: str = os.getenv("VLLM_MODEL", "meta-llama/Llama-3-8B-Instruct")


class VLLMProvider(LLMProvider):
    """Asynchroniczny klient dla serwera vLLM z API zgodnym z OpenAI.

    Attributes:
        _client (httpx.AsyncClient): Współdzielony klient HTTP do komunikacji z API.
    """

    __slots__ = ("_client",)

    def __init__(self) -> None:
        """Inicjalizuje klienta VLLMProvider.

        Tworzy współdzieloną, asynchroniczną sesję HTTP z odpowiednim
        bazowym URL i domyślnym timeoutem.
        """
        self._client = httpx.AsyncClient(base_url=VLLM_BASE_URL, timeout=60.0)

    async def aclose(self) -> None:
        """Zamyka sesję klienta HTTP.

        Powinno być wywołane podczas zamykania aplikacji, aby zapewnić
        prawidłowe zwolnienie zasobów.
        """
        await self._client.aclose()

    @staticmethod
    def _handle_error(e: httpx.HTTPStatusError) -> ModelGatewayError:
        """Mapuje błąd `httpx` na odpowiedni wyjątek domenowy z `base.py`."""
        status = e.response.status_code
        if status == 429:
            # vLLM może nie wysyłać nagłówków RateLimit, ale obsługujemy sam status
            return ProviderOverloaded(
                message=f"vLLM server is overloaded (HTTP {status})",
                provider="vllm",
                status_code=status,
                raw=e.response,
            )
        if status >= 500:
            return ProviderServerError.from_httpx_5xx(e, provider="vllm")

        # Inne błędy 4xx traktujemy jako ogólny błąd klienta
        return ModelGatewayError.from_httpx(e, provider="vllm")

    async def chat(
        self,
        messages: Sequence[LLMMessage],
        *,
        params: Optional[ChatParams] = None,
        **kwargs: Any,
    ) -> str:
        """Wysyła zapytanie do serwera vLLM i zwraca odpowiedź.

        Args:
            messages: Sekwencja wiadomości w rozmowie, zgodna z `LLMMessage`.
            params: Opcjonalne parametry generowania (max_tokens, temperatura, etc.).

        Returns:
            Wygenerowany przez model tekst odpowiedzi.

        Raises:
            ProviderOverloaded: Gdy serwer vLLM jest przeciążony (HTTP 429).
            ProviderServerError: Gdy serwer vLLM zwraca błąd 5xx.
            ProviderTimeout: Gdy zapytanie przekracza zdefiniowany timeout.
            ModelGatewayError: W przypadku innych błędów konfiguracyjnych lub API.
        """
        p = (params or ChatParams()).normalized()
        payload = {
            "model": VLLM_MODEL,
            "messages": to_openai_messages(messages),
            "max_tokens": p.max_tokens,
            "temperature": p.temperature,
            "top_p": p.top_p,
            "stop": p.stop or None,
            **p.extra,
        }

        try:
            response = await self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise self._handle_error(e) from e
        except httpx.TimeoutException as e:
            raise ProviderTimeout.from_httpx_timeout(
                provider="vllm",
                timeout=self._client.timeout.read,
                endpoint=f"{VLLM_BASE_URL}/chat/completions",
                raw=e,
            ) from e
        except Exception as e:
            raise ModelGatewayError(f"Nieoczekiwany błąd podczas komunikacji z vLLM: {e}", provider="vllm") from e

        try:
            data = response.json()
            choice = data.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content")

            if content is None:
                raise ModelGatewayError(
                    "Odpowiedź z vLLM ma nieprawidłową strukturę (brak `content`).",
                    provider="vllm",
                    details=data,
                )
            return content
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            raise ModelGatewayError(
                f"Błąd parsowania odpowiedzi z vLLM: {e}",
                provider="vllm",
                details=response.text,
            ) from e
