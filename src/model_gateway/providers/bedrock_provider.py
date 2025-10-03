from __future__ import annotations
import os
from typing import List
from . .base import LLMMessage, LLMProvider
import boto3
import json

BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")
BEDROCK_REGION = os.getenv("AWS_REGION", "eu-central-1")

class BedrockProvider(LLMProvider):
    """Minimalny klient Bedrock Runtime (boto3)."""

    def __init__(self) -> None:
        self._rt = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)

    async def chat(self, messages: List[LLMMessage], max_tokens: int = 512, temperature: float = 0.2) -> str:
        # Uwaga: interfejs różni się między modelami; tu pseudo-uniwersalny.
        body = {
            "messages": [m.__dict__ for m in messages],
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
        }
        resp = self._rt.invoke_model(modelId=BEDROCK_MODEL_ID, body=json.dumps(body))
        payload = json.loads(resp["body"].read())
        # dopasuj do zwracanego formatu konkretnego modelu:
        return payload.get("outputText") or payload.get("content") or json.dumps(payload)
