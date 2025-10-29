# SPDX-License-Identifier: Apache-2.0
"""File: services/api-gateway/src/model_gateway/providers/openai_provider.py

Project: astradesk
Pakage: api-gateway

Author: Siergej Sobolewski
Since: 2025-10-29

OpenAI Chat Completions LLM provider (async) implementing the `LLMProvider` interface.

Uses `httpx` for non-blocking calls, supports configurable base URL (OpenAI or Azure-compatible proxy),
and returns normalized chat outputs based on `LLMMessage` + `ChatParams`.

Environment Variables:
  OPENAI_API_KEY: required API key.
  OPENAI_BASE_URL: optional base URL (default: "https://api.openai.com/v1")
  OPENAI_MODEL: default model name (default: "gpt-4o-mini").

Notes (PL):
  Dostawca modelu (LLM Provider) dla OpenAI Chat Completions API.

  Ten moduł implementuje interfejs `LLMProvider` do komunikacji z API OpenAI,
  w tym z modelami takimi jak GPT-4o, GPT-4 Turbo i inne.

  Kluczowe cechy:
  - Asynchroniczna komunikacja z API przy użyciu `httpx`.
  - Zgodność z protokołem `LLMProvider` i modelem `ChatParams`.
  - Zaawansowane mapowanie błędów HTTP na wyjątki domenowe
    (np. 429 -> ProviderOverloaded, 5xx -> ProviderServerError).
  - Bezpieczna i wydajna obsługa połączeń i konfiguracji.

"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import AsyncIterator, Sequence
from typing import Any, Dict, Optional

import httpx

from ..base import (
    ChatChunk,
    ChatParams,
    LLMMessage,
    LLMProvider,
    ModelGatewayError,
    ProviderOverloadedError,
    ProviderServerError,
    ProviderTimeoutError,
    TokenLimitExceededError,
    Usage,
    to_openai_messages,
)

logger = logging.getLogger(__name__)

# Environment configuration with validation
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TIMEOUT_SEC = float(os.getenv("OPENAI_TIMEOUT_SEC", "30.0"))

if not OPENAI_API_KEY:
    raise ModelGatewayError("OPENAI_API_KEY environment variable is required", provider="openai")


class OpenAIProvider(LLMProvider):
    """Async LLM provider for OpenAI Chat Completions API."""

    __slots__ = ("_client", "_model")

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=OPENAI_BASE_URL,
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            timeout=OPENAI_TIMEOUT_SEC,
        )
        self._model = OPENAI_MODEL

    async def aclose(self) -> None:
        """Close the HTTP client session."""
        await self._client.aclose()

    @staticmethod
    def _handle_error(e: httpx.HTTPStatusError) -> ModelGatewayError:
        """Map httpx error to domain-specific exception."""
        status = e.response.status_code
        try:
            details = e.response.json()
        except Exception:
            details = {"error": e.response.text}

        if status == 429:
            return ProviderOverloadedError(
                "OpenAI rate limit exceeded", provider="openai", status_code=status, details=details
            )
        if status >= 500:
            return ProviderServerError(
                "OpenAI server error", provider="openai", status_code=status, details=details
            )

        if "error" in details and details["error"].get("code") == "context_length_exceeded":
            return TokenLimitExceededError(
                "Token limit exceeded", provider="openai", details=details
            )

        return ModelGatewayError(
            f"OpenAI client error: {details.get('error', {}).get('message', str(e))}",
            provider="openai",
            status_code=status,
            details=details,
        )

    async def chat(
        self,
        messages: Sequence[LLMMessage],
        params: Optional[ChatParams] = None,
    ) -> str:
        """Send a chat completion request and return raw response string."""
        p = (params or ChatParams()).normalized()
        payload = {
            "model": self._model,
            "messages": to_openai_messages(messages),
            "max_tokens": p.get("max_tokens", 512),
            "temperature": p.get("temperature", 0.7),
            "top_p": p.get("top_p", 1.0),
            "stop": p.get("stop"),
            **p.get("extra", {}),
        }

        try:
            response = await self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            choice = data.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")
            if not content:
                raise ModelGatewayError("No content in OpenAI response", provider="openai", details=data)
            return content
        except httpx.HTTPStatusError as e:
            raise self._handle_error(e) from e
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError("OpenAI request timeout", provider="openai") from e
        except Exception as e:
            raise ModelGatewayError(f"Unexpected error with OpenAI: {str(e)}", provider="openai") from e

    async def stream(
        self,
        messages: Sequence[LLMMessage],
        params: Optional[ChatParams] = None,
    ) -> AsyncIterator[ChatChunk]:
        """Stream chat response chunks."""
        p = (params or ChatParams()).normalized()
        payload = {
            "model": self._model,
            "messages": to_openai_messages(messages),
            "max_tokens": p.get("max_tokens", 512),
            "temperature": p.get("temperature", 0.7),
            "top_p": p.get("top_p", 1.0),
            "stop": p.get("stop"),
            "stream": True,
            **p.get("extra", {}),
        }

        try:
            async with self._client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        chunk = json.loads(line[6:])
                        delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if delta:
                            yield ChatChunk(content=delta)
        except Exception as e:
            raise ModelGatewayError(f"Streaming error with OpenAI: {str(e)}", provider="openai") from e

    async def reflect(self, query: str, result: str) -> float:
        """Self-reflection: Scores result relevance to query (0.0-1.0)."""
        system = "Evaluate relevance: Return JSON {'score': float(0.0-1.0)}. No explanations."
        user = f"Query: {query}\nContent: {result}"
        messages = [
            LLMMessage(role="system", content=system),
            LLMMessage(role="user", content=user),
        ]
        raw = await self.chat(messages, params=ChatParams(max_tokens=50, temperature=0.0))
        try:
            data = json.loads(raw.strip())
            return max(0.0, min(1.0, float(data.get("score", 0.5))))
        except Exception:
            logger.warning("Reflection parsing failed")
            return 0.5
