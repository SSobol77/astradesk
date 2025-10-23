# SPDX-License-Identifier: Apache-2.0
"""File: services/gateway-python/src/model_gateway/providers/openai_provider.py
Project: AstraDesk Framework — API Gateway
Description:
    OpenAI Chat Completions LLM provider (async) implementing the `LLMProvider`
    interface. Uses `httpx` for non-blocking calls, supports configurable base
    URL (OpenAI or Azure-compatible proxy), and returns normalized chat outputs
    based on `LLMMessage` + `ChatParams`.

Author: Siergej Sobolewski
Since: 2025-10-07

Overview
--------
- Async HTTP client (`httpx.AsyncClient`) with shared session and sane timeouts.
- Compatible with Chat Completions API (`/chat/completions`).
- Uniform request schema: `messages`, `model`, and generation params from `ChatParams`.
- Clear separation of transport/serialization from orchestration/business logic.

Configuration (env)
-------------------
- OPENAI_API_KEY : required API key.
- OPENAI_BASE_URL: optional base URL (default: "https://api.openai.com/v1")
                   (supports Azure/OpenAI-compatible gateways).
- OPENAI_MODEL   : default model name (default: "gpt-4o-mini").

Error mapping
-------------
- HTTP 429         → ProviderOverloaded
- HTTP 5xx         → ProviderServerError
- context_length_* → TokenLimitExceeded (when reported by API)
- Timeout          → ProviderTimeout
- Other HTTP/JSON  → ModelGatewayError
All errors include `provider="openai"` and, when safe, structured details.

Security & safety
-----------------
- Do not log API keys or raw payloads in production.
- Apply per-request budgets at call sites (max_tokens, temperature).
- Prefer least-privilege secrets management and rotate keys regularly.

Performance
-----------
- One shared `AsyncClient` per provider instance; close via `aclose()` on app shutdown.
- Let orchestration layer handle retries/backoff; provider stays thin.
- Keep payloads minimal; respect model-specific token and rate limits.

Usage (example)
---------------
>>> provider = OpenAIProvider()
>>> text = await provider.chat(
...     messages=[
...         LLMMessage(role="system", content="You are helpful."),
...         LLMMessage(role="user", content="Explain blue/green deployments briefly."),
...     ],
...     params=ChatParams(max_tokens=256, temperature=0.2),
... )
>>> print(text)

Notes
-----
- This provider does not implement RAG/grounding; compose such behavior
  in the orchestrator layer.
- Extend parsing or parameter mapping as new OpenAI features become available.

Notes (PL):
------------
"Dostawca modelu (LLM Provider) dla OpenAI Chat Completions API.

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

"""  # noqa: D205

from __future__ import annotations  # noqa: I001

import json
import os
import logging
import httpx

from typing import Sequence  # noqa: UP035

from ..base import (
    ChatParams,
    Tokenizer,
    LLMMessage,
    LLMProvider,
    ModelGatewayError,
    ProviderOverloadedError,
    ProviderServerError,
    ProviderTimeoutError,
    TokenLimitExceededError,
    to_openai_messages,
)

logger = logging.getLogger(__name__)

# --- Konfiguracja ---
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-5-nano") # Zmień na preferowany model


class OpenAIProvider(LLMProvider):
    """Lekki, asynchroniczny klient dla OpenAI Chat Completions API (v1).

    Attributes
    ----------
        _client (httpx.AsyncClient): Współdzielony klient HTTP do komunikacji z API.

    """

    __slots__ = ("_client",)

    def __init__(self) -> None:
        """Inicjalizuje klienta OpenAIProvider.

        Sprawdza obecność klucza API i tworzy współdzieloną, asynchroniczną
        sesję HTTP z odpowiednimi nagłówkami i timeoutem.

        Raises
        ------
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
            return ProviderOverloadedError.from_httpx_429(e, provider="openai")
        if status >= 500:
            return ProviderServerError.from_httpx_5xx(e, provider="openai")

        # Sprawdzenie, czy błąd dotyczy limitu kontekstu
        try:
            details = e.response.json()
            if "error" in details and details["error"].get("code") == "context_length_exceeded":
                return TokenLimitExceededError.from_httpx_response(
                    e.response, provider="openai", model=OPENAI_MODEL
                )
        except Exception:
            logging.exception("Błąd parsowania JSON podczas mapowania błędów OpenAI")
            # Ignoruj błędy parsowania JSON, przejdź do błędu ogólnego

        return ModelGatewayError.from_httpx(e, provider="openai")


    async def chat(
        self,
        messages: Sequence[LLMMessage],
        *,
        params: ChatParams | None = None,
        tokenizer: Tokenizer | None = None,
        request_id: str | None = None,
    ) -> str:
        """Wysyła zapytanie do OpenAI Chat Completions API i zwraca odpowiedź.

        Implementuje logikę wywołania, włączając w to asynchroniczną obsługę,
        zarządzanie cyklem życia klienta i mapowanie błędów specyficznych
        dla API OpenAI.

        Args:
        ----
            messages: Sekwencja wiadomości w rozmowie, zgodna z `LLMMessage`.
            params: Opcjonalne parametry generacji (max_tokens, temperatura, etc.).
            tokenizer: (Nieużywany w tej implementacji) Opcjonalny tokenizator.
            request_id: (Nieużywany w tej implementacji) Opcjonalny identyfikator żądania.

        Returns:
        -------
            Wygenerowany przez model tekst odpowiedzi.

        Raises:
        ------
            ProviderOverloadedError: Gdy API zwraca błąd 429 (rate limit).
            ProviderServerError: Gdy API zwraca błąd 5xx.
            TokenLimitExceededError: Gdy zapytanie przekracza limit tokenów modelu.
            ProviderTimeoutError: Gdy zapytanie przekracza zdefiniowany timeout.
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
            raise ProviderTimeoutError.from_httpx_timeout(
                provider="openai",
                timeout=self._client.timeout.read if isinstance(self._client.timeout, httpx.Timeout) else None,
                endpoint=f"{OPENAI_BASE_URL}/chat/completions",
                raw=e,
            ) from e
        except Exception as e:
            logger.error("Nieoczekiwany błąd podczas komunikacji z OpenAI.", exc_info=True)
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
