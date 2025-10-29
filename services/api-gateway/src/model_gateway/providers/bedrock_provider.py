# SPDX-License-Identifier: Apache-2.0
"""File: services/api-gateway/src/model_gateway/providers/bedrock_provider.py

Project: astradesk
Pakage: api-gateway

Author: Siergej Sobolewski
Since: 2025-10-29

AWS Bedrock Runtime LLM provider (async) implementing the `LLMProvider` interface.

Integrates Bedrock-hosted models (e.g., Anthropic Claude, Meta Llama) with non-blocking I/O via `aioboto3`,
providing consistent chat semantics, robust error mapping, and configurable timeouts/regions.

Environment Variables:
  BEDROCK_MODEL_ID: e.g. "anthropic.claude-3-5-sonnet-20240620-v1:0"
  AWS_REGION: e.g. "eu-central-1"

Notes (PL):
  Dostawca modelu (LLM Provider) dla AWS Bedrock Runtime.

  Ten moduł implementuje interfejs `LLMProvider` do komunikacji z API AWS Bedrock,
  umożliwiając integrację różnych modeli LLM hostowanych na platformie AWS z
  aplikacją AstraDesk.

  Kluczowe cechy:
  - Asynchroniczna komunikacja: Wykorzystuje bibliotekę `aioboto3` do
    nieblokującego połączenia z AWS Bedrock, co zapewnia płynność działania
    serwera FastAPI.
  - Zgodność z protokołem: Implementuje interfejs `LLMProvider`, w tym
    obsługę obiektów `LLMMessage` i `ChatParams`, zapewniając spójność
    z innymi dostawcami modeli.
  - Elastyczność modeli: Obsługuje różne rodziny modeli dostępne w Bedrock
    (np. Anthropic Claude, Meta Llama) poprzez dynamiczne budowanie payloadu
    zapytania.
  - Zaawansowana obsługa błędów: Mapuje błędy `botocore.exceptions.ClientError`
    na dedykowane wyjątki z `runtime.base`, takie jak `ProviderOverloaded`,
    `ProviderServerError`, `TokenLimitExceeded` czy `ModelGatewayError`,
    co umożliwia inteligentne zarządzanie błędami i strategiami retry.
  - Bezpieczeństwo i wydajność: Dba o prawidłowe zarządzanie zasobami
    (klient AWS) i konfigurację (timeouty, region).

"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import AsyncIterator, Sequence
from typing import Any, Dict

import aioboto3
from botocore.exceptions import ClientError

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
)

logger = logging.getLogger(__name__)

# Environment configuration with validation
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID")
BEDROCK_REGION = os.getenv("AWS_REGION", "us-east-1")

if not BEDROCK_MODEL_ID:
    raise ModelGatewayError("BEDROCK_MODEL_ID environment variable is required", provider="bedrock")


class BedrockProvider(LLMProvider):
    """Async LLM provider for AWS Bedrock Runtime."""

    __slots__ = ("_session", "_model_id", "_region")

    def __init__(self) -> None:
        self._session = aioboto3.Session()
        self._model_id = BEDROCK_MODEL_ID
        self._region = BEDROCK_REGION

    async def aclose(self) -> None:
        """No-op for aioboto3.Session; resources are managed per-client."""
        pass

    def _build_request_body(self, messages: Sequence[LLMMessage], params: Dict[str, Any]) -> str:
        """Build JSON request body based on model family."""
        if self._model_id.startswith("anthropic.claude"):
            # Anthropic Claude Messages API
            system = ""
            claude_messages = []
            for msg in messages:
                if msg.role == "system":
                    system += msg.content + "\n"
                else:
                    claude_messages.append({"role": msg.role, "content": msg.content})
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": params.get("max_tokens", 1024),
                "system": system.strip(),
                "messages": claude_messages,
                "temperature": params.get("temperature", 0.7),
                "top_p": params.get("top_p", 1.0),
                "stop_sequences": params.get("stop", []),
            }
        elif self._model_id.startswith("meta-llama."):
            # Meta Llama 3 Instruct format
            prompt = "<s>"
            for msg in messages:
                if msg.role == "system":
                    prompt += f"[INST] <<SYS>> {msg.content} <</SYS>> [/INST]"
                elif msg.role == "user":
                    prompt += f"[INST] {msg.content} [/INST]"
                elif msg.role == "assistant":
                    prompt += f" {msg.content} </s><s>"
            body = {
                "prompt": prompt,
                "max_gen_len": params.get("max_tokens", 512),
                "temperature": params.get("temperature", 0.5),
                "top_p": params.get("top_p", 0.9),
            }
        else:
            raise ModelGatewayError(f"Unsupported model family for {self._model_id}", provider="bedrock")

        return json.dumps(body)

    def _parse_response(self, response_body: bytes, family: str) -> str:
        """Parse response body based on model family."""
        try:
            payload = json.loads(response_body)
        except json.JSONDecodeError as e:
            raise ModelGatewayError(f"Invalid JSON in Bedrock response: {e}", provider="bedrock") from e

        if "anthropic" in family:
            content_blocks = payload.get("content", [])
            text = "".join(block.get("text", "") for block in content_blocks if block.get("type") == "text")
            if not text:
                logger.warning("No text content in Anthropic response", extra={"payload": payload})
            return text
        elif "meta-llama" in family:
            generation = payload.get("generation", "")
            if not generation:
                logger.warning("No generation in Llama response", extra={"payload": payload})
            return generation
        else:
            logger.warning("Unknown model family for parsing", extra={"family": family, "payload": payload})
            return ""

    def _get_model_family(self) -> str:
        """Determine model family from ID."""
        if self._model_id.startswith("anthropic.claude"):
            return "anthropic"
        elif self._model_id.startswith("meta-llama."):
            return "meta-llama"
        raise ModelGatewayError(f"Unknown model family for {self._model_id}", provider="bedrock")

    async def chat(
        self,
        messages: Sequence[LLMMessage],
        params: Optional[ChatParams] = None,
    ) -> str:
        """Send a chat completion request and return raw response string."""
        p = (params or ChatParams()).normalized()
        request_body = self._build_request_body(messages, p)
        family = self._get_model_family()

        try:
            async with self._session.client("bedrock-runtime", region_name=self._region) as client:
                response = await client.invoke_model(
                    modelId=self._model_id,
                    body=request_body,
                    contentType="application/json",
                    accept="application/json",
                )
            response_body = await response["body"].read()
            return self._parse_response(response_body, family)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            http_status = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode")

            if error_code == "ThrottlingException":
                raise ProviderOverloadedError(error_msg, provider="bedrock", status_code=http_status) from e
            if "context length" in error_msg.lower() or error_code == "ValidationException":
                raise TokenLimitExceededError(error_msg, provider="bedrock") from e
            if http_status and http_status >= 500:
                raise ProviderServerError(error_msg, provider="bedrock", status_code=http_status) from e
            raise ModelGatewayError(error_msg, provider="bedrock", status_code=http_status) from e
        except asyncio.TimeoutError as e:
            raise ProviderTimeoutError("Bedrock invocation timeout", provider="bedrock") from e
        except Exception as e:
            raise ModelGatewayError(f"Unexpected error with Bedrock: {str(e)}", provider="bedrock") from e

    async def stream(
        self,
        messages: Sequence[LLMMessage],
        params: Optional[ChatParams] = None,
    ) -> AsyncIterator[ChatChunk]:
        """Stream chat response chunks."""
        p = (params or ChatParams()).normalized()
        request_body = self._build_request_body(messages, p)
        family = self._get_model_family()

        try:
            async with self._session.client("bedrock-runtime", region_name=self._region) as client:
                response = await client.invoke_model_with_response_stream(
                    modelId=self._model_id,
                    body=request_body,
                    contentType="application/json",
                    accept="application/json",
                )
                async for event in response["body"]:
                    chunk = json.loads(event["chunk"]["bytes"])
                    if "anthropic" in family:
                        delta = chunk.get("delta", {}).get("text", "")
                    elif "meta-llama" in family:
                        delta = chunk.get("generation", "")
                    else:
                        delta = ""
                    if delta:
                        yield ChatChunk(content=delta)
        except Exception as e:
            raise ModelGatewayError(f"Streaming error with Bedrock: {str(e)}", provider="bedrock") from e

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
