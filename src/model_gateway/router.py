from __future__ import annotations
import os
from typing import List
from .base import LLMProvider, LLMMessage
from .providers.openai_provider import OpenAIProvider
from .providers.bedrock_provider import BedrockProvider
from .providers.vllm_provider import VLLMProvider

PROVIDER = os.getenv("MODEL_PROVIDER", "openai").lower()

def get_provider() -> LLMProvider:
    if PROVIDER == "openai":
        return OpenAIProvider()
    if PROVIDER == "bedrock":
        return BedrockProvider()
    if PROVIDER == "vllm":
        return VLLMProvider()
    raise RuntimeError(f"Unknown MODEL_PROVIDER={PROVIDER}")
