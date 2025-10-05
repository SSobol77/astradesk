# src/model_gateway/providers/bedrock_provider.py
"""Dostawca modelu (LLM Provider) dla AWS Bedrock Runtime.

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
"""
from __future__ import annotations

import json
import os
from typing import Any, List, Optional, Sequence

import aioboto3
from botocore.exceptions import ClientError

from ..base import (
    ChatParams,
    LLMMessage,
    LLMProvider,
    ModelGatewayError,
    ProviderOverloaded,
    ProviderServerError,
    TokenLimitExceeded,
)

# Konfiguracja providera ze zmiennych środowiskowych
BEDROCK_MODEL_ID: str = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")
BEDROCK_REGION: str = os.getenv("AWS_REGION", "eu-central-1")


class BedrockProvider(LLMProvider):
    """Asynchroniczny klient dla AWS Bedrock Runtime.

    Implementacja providera LLM, który komunikuje się z API AWS Bedrock
    przy użyciu biblioteki `aioboto3`, zapewniając nieblokujące operacje.

    Kluczowe funkcje:
    - Dynamiczne tworzenie payloadu zapytania w zależności od rodziny modelu
      (np. Anthropic Claude, Meta Llama).
    - Mapowanie błędów `botocore.exceptions.ClientError` na dedykowane,
      bogate w kontekst wyjątki z `base.py` (np. ProviderOverloaded).
    - Pełna zgodność z interfejsem `LLMProvider`.
    """

    def __init__(self) -> None:
        """Inicjalizuje sesję aioboto3."""
        self._session = aioboto3.Session()

    def _build_request_body(
        self, messages: Sequence[LLMMessage], params: ChatParams
    ) -> str:
        """Buduje treść zapytania (body) w formacie JSON, specyficznym dla modelu.

        Args:
            messages: Sekwencja wiadomości w rozmowie.
            params: Parametry generowania tekstu.

        Returns:
            String zawierający payload w formacie JSON.

        Raises:
            NotImplementedError: Jeśli rodzina modelu nie jest obsługiwana.
        """
        body: dict[str, Any]

        # Logika dla modeli z rodziny Anthropic Claude
        if BEDROCK_MODEL_ID.startswith("anthropic.claude"):
            # Mapowanie ról systemowych na oddzielny parametr
            system_prompt = next((m.content for m in messages if m.role == "system"), None)
            user_messages = [m.as_dict() for m in messages if m.role != "system"]

            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": params.max_tokens,
                "temperature": params.temperature,
                "top_p": params.top_p,
                "messages": user_messages,
            }
            if system_prompt:
                body["system"] = system_prompt

        # Logika dla modeli z rodziny Meta Llama
        elif BEDROCK_MODEL_ID.startswith("meta.llama"):
            # Llama oczekuje pojedynczego, sformatowanego promptu
            dialog = "\n".join(f"{m.role}: {m.content}" for m in messages)
            prompt = f"<s>[INST] {dialog} [/INST]"
            body = {
                "prompt": prompt,
                "max_gen_len": params.max_tokens,
                "temperature": params.temperature,
                "top_p": params.top_p,
            }
        else:
            raise NotImplementedError(
                f"Rodzina modelu dla '{BEDROCK_MODEL_ID}' nie jest obsługiwana."
            )
        
        return json.dumps(body)

    def _parse_response(self, response_body: bytes) -> str:
        """Parsuje odpowiedź z Bedrock i wyciąga wygenerowany tekst.

        Args:
            response_body: Surowa odpowiedź (bajty) z `invoke_model`.

        Returns:
            Wygenerowany tekst jako string.

        Raises:
            ModelGatewayError: Jeśli nie udało się sparsować odpowiedzi.
        """
        try:
            payload = json.loads(response_body)

            # Logika dla modeli Anthropic Claude
            if BEDROCK_MODEL_ID.startswith("anthropic.claude"):
                if payload.get("content") and isinstance(payload["content"], list):
                    return payload["content"][0].get("text", "")
            
            # Logika dla modeli Meta Llama
            elif BEDROCK_MODEL_ID.startswith("meta.llama"):
                return payload.get("generation", "")

            raise ModelGatewayError(
                f"Nieznany format odpowiedzi dla modelu '{BEDROCK_MODEL_ID}'.",
                provider="bedrock",
            )
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise ModelGatewayError(
                f"Błąd parsowania odpowiedzi z Bedrock: {e}",
                provider="bedrock",
                details=response_body.decode('utf-8', errors='ignore'),
            ) from e

    async def chat(
        self,
        messages: Sequence[LLMMessage],
        *,
        params: Optional[ChatParams] = None,
        **kwargs: Any,
    ) -> str:
        """Wysyła zapytanie do modelu w AWS Bedrock i zwraca odpowiedź.

        Implementuje logikę wywołania `invoke_model`, włączając w to
        asynchroniczną obsługę i mapowanie błędów.

        Args:
            messages: Sekwencja wiadomości w rozmowie.
            params: Parametry generowania (temperatura, max_tokens, etc.).

        Returns:
            Wygenerowana przez model odpowiedź w formie tekstowej.

        Raises:
            ProviderOverloaded: Gdy API Bedrock zwraca błąd throttlingu.
            TokenLimitExceeded: Gdy kontekst zapytania jest zbyt długi.
            ProviderServerError: W przypadku błędów po stronie serwera AWS.
            ModelGatewayError: W przypadku innych błędów komunikacji lub konfiguracji.
        """
        p = (params or ChatParams()).normalized()
        request_body = self._build_request_body(messages, p)

        try:
            async with self._session.client(
                "bedrock-runtime", region_name=BEDROCK_REGION
            ) as client:
                response = await client.invoke_model(
                    modelId=BEDROCK_MODEL_ID,
                    body=request_body,
                    contentType="application/json",
                    accept="application/json",
                )
                response_body = await response["body"].read()
                return self._parse_response(response_body)

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            error_msg = e.response.get("Error", {}).get("Message", str(e))

            if error_code == "ThrottlingException":
                raise ProviderOverloaded(
                    message=f"Bedrock API rate limit exceeded: {error_msg}",
                    provider="bedrock",
                    raw=e.response,
                )
            if error_code == "ModelErrorException" and "context length" in error_msg.lower():
                raise TokenLimitExceeded(
                    message=f"Bedrock model token limit exceeded: {error_msg}",
                    provider="bedrock",
                    model=BEDROCK_MODEL_ID,
                    raw=e.response,
                )
            if e.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0) >= 500:
                raise ProviderServerError(
                    message=f"Bedrock server error ({error_code}): {error_msg}",
                    provider="bedrock",
                    status_code=e.response.get("ResponseMetadata", {}).get("HTTPStatusCode"),
                    raw=e.response,
                )
            
            # Domyślny błąd dla innych problemów po stronie klienta
            raise ModelGatewayError(
                message=f"Bedrock client error ({error_code}): {error_msg}",
                provider="bedrock",
                raw=e.response,
            )
        except Exception as e:
            # Ogólny błąd, np. problem z połączeniem
            raise ModelGatewayError(f"An unexpected error occurred with Bedrock: {e}", provider="bedrock") from e
