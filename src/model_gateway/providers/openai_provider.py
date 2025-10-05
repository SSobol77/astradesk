# src/model_gateway/providers/openai_provider.py
"""Dostawca modelu (LLM Provider) dla OpenAI Chat Completions API.

Ten moduł implementuje interfejs `LLMProvider` do komunikacji z API OpenAI,
w tym z modelami takimi jak GPT-4o, GPT-4 Turbo i inne.

Kluczowe funkcje:
- Asynchroniczna komunikacja z API przy użyciu `httpx`.
- Zgodność z protokołem `LLMProvider` i modelem `ChatParams`.
- Zaawansowane mapowanie błędów HTTP na wyjątki domenowe
  (np. 429 -> ProviderOverloaded, 5xx -> ProviderServerError).
- Bezpieczna i wydajna obsługa połączeń i konfiguracji.

Konfiguracja (zmienne środowiskowe):
- OPENAI_API_KEY: Klucz API do uwierzytelnienia w OpenAI (wymagany).
- OPENAI_BASE: (Opcjonalnie) Bazowy URL API, przydatny do proxy lub
  alternatywnych endpointów (np. Azure OpenAI). Domyślnie: "https://api.openai.com/v1".
- OPENAI_MODEL: (Opcjonalnie) Domyślny model do użycia. Domyślnie: "gpt-4o-mini".
"""

from __future__ import annotations

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
    TokenLimitExceeded,
    to_openai_messages,
)

# --- Konfiguracja ---
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


class OpenAIProvider(LLMProvider):
    """Lekki, asynchroniczny klient dla OpenAI Chat Completions API (v1).

    Attributes:
        _client (httpx.AsyncClient): Współdzielony klient HTTP do komunikacji z API.
    """

    __slots__ = ("_client",)

    def __init__(self) -> None:
        """Inicjalizuje klienta OpenAIProvider.

        Sprawdza obecność klucza API i tworzy współdzieloną, asynchroniczną
        sesję HTTP z odpowiednimi nagłówkami i timeoutem.

        Raises:
            ModelGatewayError: Jeśli brakuje klucza OPENAI_API_KEY.
        """
        if not OPENAI_API_KEY:
            raise ModelGatewayError(
                "Konfiguracja OpenAIProvider nie powiodła się: zmienna środowiskowa "
                "OPENAI_API_KEY nie jest ustawiona.",
                provider="openai",
            )

        self._client = httpx.AsyncClient(
            base_url=OPENAI_BASE_URL,
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            timeout=30.0,
        )

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
            return ProviderOverloaded.from_httpx_429(e, provider="openai")
        if status >= 500:
            return ProviderServerError.from_httpx_5xx(e, provider="openai")

        # Sprawdzenie, czy błąd dotyczy limitu kontekstu
        try:
            details = e.response.json()
            if "error" in details and details["error"].get("code") == "context_length_exceeded":
                return TokenLimitExceeded.from_httpx_response(
                    e.response, provider="openai", model=OPENAI_MODEL
                )
        except Exception:
            pass  # Ignoruj błędy parsowania JSON, przejdź do błędu ogólnego

        return ModelGatewayError.from_httpx(e, provider="openai")

    async def chat(
        self,
        messages: Sequence[LLMMessage],
        *,
        params: Optional[ChatParams] = None,
        **kwargs: Any,
    ) -> str:
        """Wysyła zapytanie do OpenAI Chat Completions API i zwraca odpowiedź.

        Args:
            messages: Sekwencja wiadomości w rozmowie, zgodna z `LLMMessage`.
            params: Opcjonalne parametry generowania (max_tokens, temperatura, etc.).

        Returns:
            Wygenerowany przez model tekst odpowiedzi.

        Raises:
            ProviderOverloaded: Gdy API zwraca błąd 429 (rate limit).
            ProviderServerError: Gdy API zwraca błąd 5xx.
            TokenLimitExceeded: Gdy zapytanie przekracza limit tokenów modelu.
            ProviderTimeout: Gdy zapytanie przekracza zdefiniowany timeout.
            ModelGatewayError: W przypadku innych błędów konfiguracyjnych lub API.
        """
        p = (params or ChatParams()).normalized()
        payload = {
            "model": OPENAI_MODEL,
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
                provider="openai",
                timeout=self._client.timeout.read,
                endpoint=f"{OPENAI_BASE_URL}/chat/completions",
                raw=e,
            ) from e
        except Exception as e:
            raise ModelGatewayError(f"Nieoczekiwany błąd podczas komunikacji z OpenAI: {e}", provider="openai") from e

        try:
            data = response.json()
            choice = data.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content")

            if content is None:
                raise ModelGatewayError(
                    "Odpowiedź API OpenAI ma nieprawidłową strukturę (brak `content`).",
                    provider="openai",
                    details=data,
                )
            return content
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            raise ModelGatewayError(
                f"Błąd parsowania odpowiedzi z API OpenAI: {e}",

                provider="openai",
                details=response.text,
            ) from e
