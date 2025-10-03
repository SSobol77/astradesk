from __future__ import annotations
import os
from typing import List
from . .base import LLMMessage, LLMProvider
import httpx
import json

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE = os.getenv("OPENAI_BASE", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

class OpenAIProvider(LLMProvider):
    """Lekki klient OpenAI Chat Completions API (v1)."""

    async def chat(self, messages: List[LLMMessage], max_tokens: int = 512, temperature: float = 0.2) -> str:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not set")
        payload = {
            "model": OPENAI_MODEL,
            "messages": [m.__dict__ for m in messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{OPENAI_BASE}/chat/completions",
                                  headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                                  json=payload)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]
