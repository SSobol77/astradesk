# SPDX-License-Identifier: Apache-2.0
"""File: services/gateway-python/src/model_gateway/providers/bedrock_provider.py
Project: AstraDesk Framework — API Gateway
Description:
    AWS Bedrock Runtime LLM provider (async) implementing the `LLMProvider`
    interface. Integrates Bedrock-hosted models (e.g., Anthropic Claude, Meta
    Llama) with non-blocking I/O via `aioboto3`, providing consistent chat
    semantics, robust error mapping, and configurable timeouts/regions.

Author: Siergej Sobolewski
Since: 2025-10-07

Overview
--------
- Async, non-blocking client built on `aioboto3` for FastAPI workloads.
- Model-family-aware payload builder (Anthropic Claude / Meta Llama).
- Uniform interface: accepts `LLMMessage`[] + `ChatParams`, returns `str`.
- Strict separation of concerns: provider = transport/serialization only.

Configuration (env)
-------------------
- BEDROCK_MODEL_ID : e.g. "anthropic.claude-3-5-sonnet-20240620-v1:0"
- AWS_REGION       : e.g. "eu-central-1"
(Optionally configure credentials via standard AWS mechanisms:
  env vars, shared config/credentials files, or instance/role metadata.)

Error mapping
-------------
- ThrottlingException           → ProviderOverloaded
- *context length* (ModelError) → TokenLimitExceeded
- HTTP ≥ 500                    → ProviderServerError
- Other ClientError / parsing   → ModelGatewayError
All exceptions carry `provider="bedrock"` and may include raw response details.

Security & safety
-----------------
- Never log secrets or raw request/response bodies in production.
- Enforce per-request budgets (max tokens, temperature) at call sites.
- Prefer least-privilege IAM for Bedrock invocation (scoped to model/region).

Performance & limits
--------------------
- One `aioboto3.Session()` per provider instance; clients are created in
  `async with` blocks for proper connection lifecycle.
- Calls should be wrapped with timeouts/retries at orchestration level.
- Keep request bodies small; respect model-specific token/context limits.

Model-family specifics
----------------------
- Anthropic Claude:
  * system prompt carried via dedicated field (`system`)
  * messages list excludes system entries
  * `anthropic_version` pinned for Bedrock compatibility
- Meta Llama:
  * single `prompt` constructed from role-tagged dialog
  * generation keys differ (`generation`, `max_gen_len`)

Usage (example)
---------------
>>> provider = BedrockProvider()
>>> text = await provider.chat(
...     messages=[
...         LLMMessage(role="system", content="You are helpful."),
...         LLMMessage(role="user", content="Summarize: ..."),
...     ],
...     params=ChatParams(max_tokens=512, temperature=0.2),
... )
>>> print(text)

Notes
-----
- This provider performs no automatic RAG/grounding; compose such policies
  at the orchestration layer.
- Extend `_build_request_body` / `_parse_response` to add new model families.

Notes (PL)
-----
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

Konfiguracja (zmienne środowiskowe):
- `BEDROCK_MODEL_ID`: Identyfikator modelu Bedrock do użycia (np.
  "anthropic.claude-3-5-sonnet-20240620-v1:0").
- `AWS_REGION`: Region AWS, w którym działa usługa Bedrock (np. "eu-central-1").

"""  # noqa: D205

from __future__ import annotations

import json
import logging
import os
from collections.abc import Sequence
from typing import Any

import aioboto3
from botocore.exceptions import ClientError

from ..base import (
    ChatParams,
    LLMMessage,
    LLMProvider,
    ModelGatewayError,
    ProviderOverloadedError,
    ProviderServerError,
    Tokenizer,
    TokenLimitExceededError,
)

logger = logging.getLogger(__name__)

# --- Konfiguracja ---
BEDROCK_MODEL_ID: str = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-20250514-v1:0")
BEDROCK_REGION: str = os.getenv("AWS_REGION", "eu-central-1")


class BedrockProvider(LLMProvider):
    """Asynchroniczny klient dla AWS Bedrock Runtime."""

    __slots__ = ("_session",)

    def __init__(self) -> None:
        """Inicjalizuje sesję aioboto3."""
        self._session = aioboto3.Session()

    def _build_request_body(self, messages: Sequence[LLMMessage], params: ChatParams) -> str:
        """Buduje treść zapytania (body) w formacie JSON, specyficznym dla modelu."""
        body: dict[str, Any]

        if BEDROCK_MODEL_ID.startswith("anthropic.claude"):
            system_prompt = next((m.content for m in messages if m.role == "system"), None)
            user_messages = [m.as_dict() for m in messages if m.role != "system"]
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": params.max_tokens, "temperature": params.temperature,
                "top_p": params.top_p, "messages": user_messages,
            }
            if system_prompt:
                body["system"] = system_prompt

        elif BEDROCK_MODEL_ID.startswith("meta.llama"):
            dialog = "\n".join(f"{m.role}: {m.content}" for m in messages)
            prompt = f"<s>[INST] {dialog} [/INST]"
            body = {
                "prompt": prompt, "max_gen_len": params.max_tokens,
                "temperature": params.temperature, "top_p": params.top_p,
            }
        else:
            raise NotImplementedError(f"Rodzina modelu dla '{BEDROCK_MODEL_ID}' nie jest obsługiwana.")

        body.update(params.extra)
        return json.dumps(body)

    def _parse_response(self, response_body: bytes) -> str:
        """Parsuje odpowiedź z Bedrock i wyciąga wygenerowany tekst."""
        try:
            payload = json.loads(response_body)

            if BEDROCK_MODEL_ID.startswith("anthropic.claude"):
                content_blocks = payload.get("content", [])
                if content_blocks and isinstance(content_blocks, list):
                    return content_blocks[0].get("text", "")

            elif BEDROCK_MODEL_ID.startswith("meta.llama"):
                return payload.get("generation", "")

            # Jeśli żaden z powyższych warunków nie został spełniony:
            logger.warning("Otrzymano nieznany lub pusty format odpowiedzi z Bedrock.", extra={"payload": payload})
            return ""  # Zwróć pusty string jako bezpieczny fallback

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise ModelGatewayError(
                f"Błąd parsowania odpowiedzi z Bedrock: {e}", provider="bedrock",
                details=response_body.decode('utf-8', errors='ignore'),
            ) from e

    async def chat(
        self,
        messages: Sequence[LLMMessage],
        *,
        params: ChatParams | None = None,
        tokenizer: Tokenizer | None = None,
        request_id: str | None = None,
    ) -> str:
        """Wysyła zapytanie do modelu w AWS Bedrock i zwraca odpowiedź.

        Implementuje logikę wywołania `invoke_model`, włączając w to
        asynchroniczną obsługę, zarządzanie cyklem życia klienta i mapowanie
        błędów specyficznych dla AWS.

        Args:
        ----
            messages: Sekwencja wiadomości w rozmowie.
            params: Parametry generowania (temperatura, max_tokens, etc.).
            tokenizer: (Nieużywany w tej implementacji) Opcjonalny tokenizator.
            request_id: (Nieużywany w tej implementacji) Opcjonalny identyfikator żądania.

        Returns:
        -------
            Wygenerowana przez model odpowiedź w formie tekstowej.

        Raises:
        ------
            ProviderOverloadedError: Gdy API Bedrock zwraca błąd throttlingu.
            TokenLimitExceededError: Gdy kontekst zapytania jest zbyt długi.
            ProviderServerError: W przypadku błędów po stronie serwera AWS.
            ModelGatewayError: W przypadku innych błędów komunikacji lub konfiguracji.

        """
        p = (params or ChatParams()).normalized()
        request_body = self._build_request_body(messages, p)

        try:
            # Używamy idiomatycznego i poprawnego wzorca `async with`.
            # Komentarz `# type: ignore` informuje Pylance, aby zignorował
            # fałszywy alarm dotyczący braku `__aenter__`, ponieważ wiemy,
            # że `aioboto3` poprawnie implementuje ten protokół.
            async with self._session.client("bedrock-runtime", region_name=BEDROCK_REGION) as bedrock_client:  # type: ignore[attr-defined]
                response = await bedrock_client.invoke_model(
                    modelId=BEDROCK_MODEL_ID,
                    body=request_body,
                    contentType="application/json",
                    accept="application/json",
                )
                response_body = await response["body"].read()
                # _parse_response zawsze zwróci `str` lub rzuci wyjątek,
                # więc ta ścieżka zawsze spełnia kontrakt typu `-> str`.
                return self._parse_response(response_body)

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            http_status_code = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode")

            if error_code == "ThrottlingException":
                raise ProviderOverloadedError(
                    message=f"Bedrock API rate limit exceeded: {error_msg}", provider="bedrock",
                    status_code=http_status_code, raw=e.response
                ) from e

            # Błąd `ModelErrorException` jest ogólny, sprawdzamy treść wiadomości.
            if "context length" in error_msg.lower():
                raise TokenLimitExceededError(
                    message=f"Bedrock model token limit exceeded: {error_msg}", provider="bedrock",
                    model=BEDROCK_MODEL_ID, status_code=http_status_code, raw=e.response
                ) from e

            if http_status_code and http_status_code >= 500:
                raise ProviderServerError(
                    message=f"Bedrock server error ({error_code}): {error_msg}", provider="bedrock",
                    status_code=http_status_code, raw=e.response
                ) from e

            # Domyślny błąd dla innych problemów po stronie klienta (np. ValidationException).
            raise ModelGatewayError(
                message=f"Bedrock client error ({error_code}): {error_msg}", provider="bedrock",
                status_code=http_status_code, raw=e.response
            ) from e

        except Exception as e:
            # Ogólny błąd, np. problem z połączeniem, błąd w aioboto3.
            logger.error("Nieoczekiwany błąd podczas komunikacji z Bedrock.", exc_info=True)
            raise ModelGatewayError(f"An unexpected error occurred with Bedrock: {e}", provider="bedrock") from e
