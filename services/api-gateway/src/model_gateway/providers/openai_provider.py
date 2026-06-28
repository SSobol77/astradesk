# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/src/model_gateway/providers/openai_provider.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for services/api-gateway/src/model_gateway/providers/openai_provider.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""OpenAI Chat Completions LLM provider.

The module is intentionally safe to import without OPENAI_API_KEY.

CI, tests, and gateway imports must not require production secrets. The OpenAI
API key is validated only when an OpenAIProvider instance is created for real
provider usage.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import AsyncIterator, Sequence

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
    to_openai_messages,
)

logger = logging.getLogger(__name__)

_OPENAI_API_KEY_ENV = 'OPENAI_API_KEY'
_DEFAULT_OPENAI_BASE_URL = 'https://api.openai.com/v1'
_DEFAULT_OPENAI_MODEL = 'gpt-4o-mini'
_DEFAULT_OPENAI_TIMEOUT_SEC = 30.0


def _read_timeout_seconds(value: str | None) -> float:
    """Parse the OpenAI timeout from an environment value."""
    if value is None or not value.strip():
        return _DEFAULT_OPENAI_TIMEOUT_SEC

    try:
        timeout = float(value)
    except ValueError as exc:
        raise ModelGatewayError(
            'OPENAI_TIMEOUT_SEC must be a valid floating-point number',
            provider='openai',
            details={'value': value},
        ) from exc

    if timeout <= 0:
        raise ModelGatewayError(
            'OPENAI_TIMEOUT_SEC must be greater than zero',
            provider='openai',
            details={'value': value},
        )

    return timeout


class OpenAIProvider(LLMProvider):
    """Async LLM provider for OpenAI Chat Completions API."""

    __slots__ = ('_client', '_model')

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_sec: float | None = None,
    ) -> None:
        """Create an OpenAI provider.

        Secrets are validated here, not at module import time, so test
        collection and application imports work in CI without OPENAI_API_KEY.
        """
        resolved_api_key = api_key or os.getenv(_OPENAI_API_KEY_ENV)
        if not resolved_api_key:
            raise ModelGatewayError(
                'OPENAI_API_KEY environment variable is required',
                provider='openai',
            )

        resolved_base_url = base_url or os.getenv('OPENAI_BASE_URL') or _DEFAULT_OPENAI_BASE_URL
        resolved_model = model or os.getenv('OPENAI_MODEL') or _DEFAULT_OPENAI_MODEL
        resolved_timeout = (
            timeout_sec
            if timeout_sec is not None
            else _read_timeout_seconds(os.getenv('OPENAI_TIMEOUT_SEC'))
        )

        self._client = httpx.AsyncClient(
            base_url=resolved_base_url,
            headers={'Authorization': f'Bearer {resolved_api_key}'},
            timeout=resolved_timeout,
        )
        self._model = resolved_model

    async def aclose(self) -> None:
        """Close the HTTP client session."""
        await self._client.aclose()

    @staticmethod
    def _handle_error(e: httpx.HTTPStatusError) -> ModelGatewayError:
        """Map an HTTP status error to an AstraDesk model-gateway exception."""
        status = e.response.status_code
        try:
            details = e.response.json()
        except Exception:
            details = {'error': e.response.text}

        if status == 429:
            return ProviderOverloadedError(
                'OpenAI rate limit exceeded',
                provider='openai',
                status_code=status,
                details=details,
            )

        if status >= 500:
            return ProviderServerError(
                'OpenAI server error',
                provider='openai',
                status_code=status,
                details=details,
            )

        error_payload = details.get('error')
        if isinstance(error_payload, dict):
            if error_payload.get('code') == 'context_length_exceeded':
                return TokenLimitExceededError(
                    'Token limit exceeded',
                    provider='openai',
                    details=details,
                )
            message = str(error_payload.get('message', str(e)))
        else:
            message = str(error_payload or str(e))

        return ModelGatewayError(
            f'OpenAI client error: {message}',
            provider='openai',
            status_code=status,
            details=details,
        )

    async def chat(
        self,
        messages: Sequence[LLMMessage],
        params: ChatParams | None = None,
    ) -> str:
        """Send a chat completion request and return the response content."""
        p = (params or ChatParams()).normalized()
        payload = {
            'model': self._model,
            'messages': to_openai_messages(messages),
            'max_tokens': p.get('max_tokens', 512),
            'temperature': p.get('temperature', 0.7),
            'top_p': p.get('top_p', 1.0),
            'stop': p.get('stop'),
            **p.get('extra', {}),
        }

        try:
            response = await self._client.post('/chat/completions', json=payload)
            response.raise_for_status()
            data = response.json()
            choice = data.get('choices', [{}])[0]
            content = choice.get('message', {}).get('content', '')
            if not content:
                raise ModelGatewayError(
                    'No content in OpenAI response',
                    provider='openai',
                    details=data,
                )
            return content
        except httpx.HTTPStatusError as e:
            raise self._handle_error(e) from e
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError('OpenAI request timeout', provider='openai') from e
        except ModelGatewayError:
            raise
        except Exception as e:
            raise ModelGatewayError(
                f'Unexpected error with OpenAI: {e!s}',
                provider='openai',
            ) from e

    async def stream(
        self,
        messages: Sequence[LLMMessage],
        params: ChatParams | None = None,
    ) -> AsyncIterator[ChatChunk]:
        """Stream chat response chunks."""
        p = (params or ChatParams()).normalized()
        payload = {
            'model': self._model,
            'messages': to_openai_messages(messages),
            'max_tokens': p.get('max_tokens', 512),
            'temperature': p.get('temperature', 0.7),
            'top_p': p.get('top_p', 1.0),
            'stop': p.get('stop'),
            'stream': True,
            **p.get('extra', {}),
        }

        try:
            async with self._client.stream('POST', '/chat/completions', json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith('data: '):
                        continue

                    payload_text = line[6:]
                    if payload_text == '[DONE]':
                        break

                    chunk = json.loads(payload_text)
                    delta = chunk.get('choices', [{}])[0].get('delta', {}).get('content', '')
                    if delta:
                        yield ChatChunk(content=delta)
        except httpx.HTTPStatusError as e:
            raise self._handle_error(e) from e
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError('OpenAI stream timeout', provider='openai') from e
        except ModelGatewayError:
            raise
        except Exception as e:
            raise ModelGatewayError(
                f'Streaming error with OpenAI: {e!s}',
                provider='openai',
            ) from e

    async def reflect(self, query: str, result: str) -> float:
        """Score result relevance to query in the range 0.0..1.0."""
        system = "Evaluate relevance: Return JSON {'score': float(0.0-1.0)}. No explanations."
        user = f'Query: {query}\nContent: {result}'
        messages = [
            LLMMessage(role='system', content=system),
            LLMMessage(role='user', content=user),
        ]

        raw = await self.chat(messages, params=ChatParams(max_tokens=50, temperature=0.0))
        try:
            data = json.loads(raw.strip())
            return max(0.0, min(1.0, float(data.get('score', 0.5))))
        except Exception:
            logger.warning('Reflection parsing failed')
            return 0.5
