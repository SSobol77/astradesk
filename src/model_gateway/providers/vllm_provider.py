from __future__ import annotations
import os
from typing import List
from . .base import LLMMessage, LLMProvider
import httpx
import json

VLLM_URL = os.getenv("VLLM_URL", "http://vllm:8000/v1")
VLLM_MODEL = os.getenv("VLLM_MODEL", "meta-llama/Llama-3-8b-instruct")

class VLLMProvider(LLMProvider):
    """Zgodny z OpenAI API endpoint vLLM."""
    async def chat(self, messages: List[LLMMessage], max_tokens: int = 512, temperature: float = 0.2) -> str:
        payload = {
            "model": VLLM_MODEL,
            "messages": [m.__dict__ for m in messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{VLLM_URL}/chat/completions", json=payload)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]
