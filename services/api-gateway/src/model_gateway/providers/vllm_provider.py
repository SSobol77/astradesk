# SPDX-License-Identifier: Apache-2.0
"""File: services/gateway-python/src/model_gateway/providers/vllm_provider.py
Project: AstraDesk Framework — API Gateway
Description:
    vLLM server LLM provider (async) implementing the `LLMProvider` interface.
    Talks to an OpenAI-compatible endpoint exposed by vLLM and returns normalized
    chat outputs based on `LLMMessage` + `ChatParams`. Uses a shared `httpx`
    AsyncClient for non-blocking I/O.

Author: Siergej Sobolewski
Since: 2025-10-07

Overview
--------
- Async HTTP client (`httpx.AsyncClient`) with a shared session and sensible timeouts.
- OpenAI-compatible Chat Completions endpoint (`/chat/completions`).
- Uniform payload mapping from `ChatParams` (temperature, top_p, max_tokens, stop, extra).
- Provider stays thin: transport + serialization; no orchestration or RAG logic.

Configuration (env)
-------------------
- VLLM_BASE_URL : base URL of the vLLM server (e.g., "http://vllm:8000/v1").
- VLLM_MODEL    : default model identifier served by vLLM (e.g., "meta-llama/Llama-3-8B-Instruct").
(Credentials are typically not required for local vLLM, but respect any upstream gateway auth if present.)

Error mapping
-------------
- HTTP 429         → ProviderOverloaded (server is overloaded/throttling).
- HTTP 5xx         → ProviderServerError (remote failure).
- Timeout          → ProviderTimeout (httpx timeout exceeded).
- Other HTTP/JSON  → ModelGatewayError (validation/parsing/config issues).
All raised exceptions include `provider="vllm"` and may carry structured response details.

Security & safety
-----------------
- Do not log raw request/response bodies in production.
- Enforce per-request budgets and guardrails at the orchestrator layer.
- Prefer network policies over ad-hoc in-code allowlists for local clusters.

Performance
-----------
- One shared `AsyncClient` per provider instance; call `aclose()` on shutdown.
- Retries/backoff should be handled by the orchestrator; provider remains stateless.
- Keep payloads lean; respect model token/context limits enforced by vLLM.

Usage (example)
---------------
>>> provider = VLLMProvider()
>>> text = await provider.chat(
...     messages=[
...         LLMMessage(role="system", content="You are concise."),
...         LLMMessage(role="user", content="Summarize the error budget policy."),
...     ],
...     params=ChatParams(max_tokens=256, temperature=0.2),
... )
>>> print(text)

Notes
-----
- Streaming and function/tool-calling are supported by some vLLM builds; extend
  payload/response handling here only when those features are enabled upstream.
- Adjust default timeout according to your deployment (in-cluster vs. WAN).

Notes (PL):
-----------
Dostawca modelu (LLM Provider) dla serwera vLLM.

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

"""  # noqa: D205

from __future__ import annotations

import json
import logging
import os
from collections.abc import Sequence

import httpx

from ..base import (
    ChatParams,
    LLMMessage,
    LLMProvider,
    ModelGatewayError,
    ProviderOverloadedError,
    ProviderServerError,
    ProviderTimeoutError,
    Tokenizer,
    to_openai_messages,
)

logger = logging.getLogger(__name__)


# --- Konfiguracja ---
VLLM_BASE_URL: str = os.getenv("VLLM_BASE_URL", "http://vllm:8000/v1")
VLLM_MODEL: str = os.getenv("VLLM_MODEL", "meta-llama/Llama-4-Scout-17B-16E-Instruct")


class VLLMProvider(LLMProvider):
    """Asynchroniczny klient dla serwera vLLM z API zgodnym z OpenAI.

    Attributes
    ----------
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
            return ProviderOverloadedError(
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
        params: ChatParams | None = None,
        tokenizer: Tokenizer | None = None,
        request_id: str | None = None,
    ) -> str:
        """Wysyła zapytanie do serwera vLLM i zwraca odpowiedź.

        Implementuje logikę wywołania, włączając w to asynchroniczną obsługę,
        zarządzanie cyklem życia klienta i mapowanie błędów.

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
            ProviderOverloadedError: Gdy serwer vLLM jest przeciążony (HTTP 429).
            ProviderServerError: Gdy serwer vLLM zwraca błąd 5xx.
            ProviderTimeoutError: Gdy zapytanie przekracza zdefiniowany timeout.
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
            raise ProviderTimeoutError.from_httpx_timeout(
                provider="vllm",
                timeout=self._client.timeout.read if isinstance(self._client.timeout, httpx.Timeout) else None,
                endpoint=f"{VLLM_BASE_URL}/chat/completions",
                raw=e,
            ) from e
        except Exception as e:
            logger.error("Nieoczekiwany błąd podczas komunikacji z vLLM.", exc_info=True)
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
