# SPDX-License-Identifier: Apache-2.0
# services/api-gateway/src/model_gateway/base.py
"""Core contracts, types, and helpers for the Model Gateway layer.
Provides a stable, provider-agnostic interface for chat models (LLMs), a shared error taxonomy,
message/parameter schemas, streaming primitives, and adapters for common wire formats (e.g., OpenAI-/Anthropic-style messages).
Integrates self-reflection hook, PyTorch for token estimation, OPA optional governance, and OTel tracing.
Author: Siergej Sobolewski
Since: 2025-10-25
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple, AsyncIterator
from abc import ABC

import torch  # PyTorch 2.9 for custom tokenizers/estimations
from opentelemetry import trace  # AstraOps/OTel
from opa_python_client import OPAClient  # Optional governance
from pydantic import BaseModel  # Pydantic v2.9+ for schemas (OpenAPI v1.2.0 compliant)

logger = logging.getLogger(__name__)

tracer = trace.get_tracer(__name__)

class LLMMessage(BaseModel):
    """Minimal chat message unit."""
    role: str
    content: str

class ChatParams(BaseModel):
    """Normalized generation parameters."""
    max_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 1.0
    stop: Optional[List[str]] = None
    extra: Dict[str, Any] = {}

    def normalized(self) -> Dict[str, Any]:
        """Returns normalized dict for provider."""
        return self.model_dump(exclude_unset=True)

class Usage(BaseModel):
    """Token usage accounting."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatChunk(BaseModel):
    """Streaming chat chunk."""
    content: str
    usage: Optional[Usage] = None

class ModelGatewayError(Exception):
    """Base error for Model Gateway with diagnostics and OTel logging."""

    def __init__(
        self,
        message: str,
        provider: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        opa_client: Optional[OPAClient] = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.details = details or {}

        # OTel trace error
        trace.get_current_span().record_exception(self)

        # Optional OPA policy check (e.g., for rate limits)
        if opa_client:
            decision = opa_client.check_policy({"error": message}, "astradesk/errors")
            if not decision["result"]:
                logger.warning(f"OPA flagged error: {message}")

# Subclasses (examples)
class ProviderTimeoutError(ModelGatewayError):
    @classmethod
    def from_httpx_timeout(cls, provider: str, timeout: float, endpoint: str, raw: Exception) -> "ProviderTimeoutError":
        return cls(f"Timeout after {timeout}s at {endpoint}", provider=provider)

class TokenLimitExceeded(ModelGatewayError):
    @classmethod
    def from_token_count(cls, actual: int, max_allowed: int, provider: str) -> "TokenLimitExceeded":
        return cls(f"Token limit exceeded: {actual} > {max_allowed}", provider=provider)

class LLMProvider(Protocol):
    """Protocol for LLM providers with chat/stream and reflection."""

    async def chat(self, messages: Sequence[LLMMessage], params: Optional[ChatParams] = None) -> str:
        """Generates a full chat response."""

    async def stream(self, messages: Sequence[LLMMessage], params: Optional[ChatParams] = None) -> AsyncIterator[ChatChunk]:
        """Streams chat response chunks."""

    async def reflect(self, query: str, result: str) -> float:
        """Self-reflection: Scores result relevance to query (0.0-1.0)."""
        raise NotImplementedError("Provider must implement reflect for agentic flows")

class Tokenizer(ABC):
    """Abstract tokenizer contract."""

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Counts tokens in text."""

    @abstractmethod
    def count_chat(self, messages: Sequence[LLMMessage]) -> int:
        """Counts tokens in chat sequence."""

class NoopTokenizer(Tokenizer):
    """Noop tokenizer with PyTorch-based heuristic estimation for token count."""

    WORDS_PER_TOKEN: float = 0.75

    def count_tokens(self, text: str) -> int:
        """Estimates token count using PyTorch tensor ops for efficiency."""
        if not text.strip():
            return 0
        words = torch.tensor(len(text.split()))
        estimated = (words * 4) // 3
        return max(1, int(estimated.item()))

    def count_chat(self, messages: Sequence[LLMMessage]) -> int:
        """Estimates tokens for chat sequence."""
        return sum(self.count_tokens(m.content) for m in messages)

# Utility adapters (e.g., to_openai_messages)
def to_openai_messages(messages: Sequence[LLMMessage]) -> List[Dict[str, str]]:
    """Adapts to OpenAI message format."""
    return [{"role": m.role, "content": m.content} for m in messages]

def to_anthropic_messages(messages: Sequence[LLMMessage]) -> List[Dict[str, str]]:
    """Adapts to Anthropic message format."""
    return [{"role": m.role, "content": m.content} for m in messages]

def validate_conversation(messages: Sequence[LLMMessage]) -> bool:
    """Validates conversation structure (e.g., alternating roles)."""
    if not messages:
        return False
    roles = [m.role for m in messages]
    # Example validation: starts with user, alternates
    if roles[0] != "user":
        return False
    for i in range(1, len(roles)):
        if roles[i] == roles[i-1]:
            return False
    return True

async def reflect_relevance(provider: LLMProvider, query: str, context: str) -> float:
    """Utility for self-reflection using provider."""
    return await provider.reflect(query, context)
