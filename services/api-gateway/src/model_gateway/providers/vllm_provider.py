# SPDX-License-Identifier: Apache-2.0
"""File: services/api-gateway/src/model_gateway/providers/vllm_provider.py

vLLM server LLM provider (async) implementing the `LLMProvider` interface.

Talks to an OpenAI-compatible endpoint exposed by vLLM and returns normalized
chat outputs based on `LLMMessage` + `ChatParams`. Uses a shared `httpx`
AsyncClient for non-blocking I/O.

Attributes:
  Author: Siergej Sobolewski
  Since: 2025-10-07

Environment Variables:
  VLLM_BASE_URL: base URL of the vLLM server (e.g., "http://vllm:8000/v1").
  VLLM_MODEL: default model identifier served by vLLM (e.g., "meta-llama/Llama-3-8B-Instruct").
  VLLM_API_KEY: optional API key for authenticated vLLM endpoints.
  VLLM_TIMEOUT_SEC: request timeout in seconds (default: 60.0).

Notes (PL):
  Dostawca modelu (LLM Provider) dla serwera vLLM.

  Ten moduł implementuje interfejs `LLMProvider` do komunikacji z serwerem
  inferencyjnym vLLM, który udostępnia API zgodne z OpenAI.

  Kluczowe funkcje:
  - Asynchroniczna komunikacja z endpointem vLLM przy użyciu `httpx`.
  - Pełna zgodność z protokołem `LLMProvider` i modelem `ChatParams`.
  - Zaawansowane mapowanie błędów HTTP (4xx/5xx) na wyjątki domenowe
    (np. ProviderServerError, ProviderTimeout).
  - Wydajne zarządzanie połączeniami HTTP dzięki współdzielonej sesji.
  
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
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
VLLM_MODEL = os.getenv("VLLM_MODEL")
VLLM_API_KEY = os.getenv("VLLM_API_KEY")  # Optional for authenticated endpoints
VLLM_TIMEOUT_SEC = float(os.getenv("VLLM_TIMEOUT_SEC", "60.0"))

if not VLLM_MODEL:
    raise ModelGatewayError("VLLM_MODEL environment variable is required", provider="vllm")


class VLLMProvider(LLMProvider):
    """Async LLM provider for vLLM server with OpenAI-compatible API."""

    __slots__ = ("_client", "_model")

    def __init__(self) -> None:
        headers = {}
        if VLLM_API_KEY:
            headers["Authorization"] = f"Bearer {VLLM_API_KEY}"
        self._client = httpx.AsyncClient(
            base_url=VLLM_BASE_URL,
            headers=headers,
            timeout=VLLM_TIMEOUT_SEC,
        )
        self._model = VLLM_MODEL

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
                "vLLM rate limit or overload", provider="vllm", status_code=status, details=details
            )
        if status >= 500:
            return ProviderServerError(
                "vLLM server error", provider="vllm", status_code=status, details=details
            )

        if "error" in details and "context_length" in details["error"].get("message", "").lower():
            return TokenLimitExceededError(
                "Token limit exceeded", provider="vllm", details=details
            )

        return ModelGatewayError(
            f"vLLM client error: {details.get('error', {}).get('message', str(e))}",
            provider="vllm",
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
                raise ModelGatewayError("No content in vLLM response", provider="vllm", details=data)
            return content
        except httpx.HTTPStatusError as e:
            raise self._handle_error(e) from e
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError("vLLM request timeout", provider="vllm") from e
        except Exception as e:
            raise ModelGatewayError(f"Unexpected error with vLLM: {str(e)}", provider="vllm") from e

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
            raise ModelGatewayError(f"Streaming error with vLLM: {str(e)}", provider="vllm") from e

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
