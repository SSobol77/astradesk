# SPDX-License-Identifier: Apache-2.0
"""File: services/api-gateway/src/model_gateway/router.py

Project: astradesk
Pakage: api-gateway

Author: Siergej Sobolewski
Since: 2025-10-29

Central router and lifecycle manager for LLM providers.
Implements singleton pattern with lazy initialization, async safety, OPA governance, and OTel tracing.

"""

from __future__ import annotations

import asyncio
import logging
import os
import inspect
from typing import Dict, Type, Optional

from opentelemetry import trace
from opa_python_client import OPAClient

from .base import LLMProvider, ProblemDetail
from .providers.bedrock_provider import BedrockProvider
from .providers.openai_provider import OpenAIProvider
from .providers.vllm_provider import VLLMProvider

logger = logging.getLogger(__name__)


class ProviderNotFoundError(Exception):
    """Raised when requested LLM provider is not registered."""

    def __init__(self, provider_name: str):
        super().__init__(f"Provider '{provider_name}' not found")
        self.provider_name = provider_name

    def to_problem_detail(self) -> ProblemDetail:
        return ProblemDetail(
            type="https://astradesk.com/errors/provider-not-found",
            title="Provider Not Found",
            detail=f"LLM provider '{self.provider_name}' is not registered. Check MODEL_PROVIDER.",
            status=500
        )


class ProviderRouter:
    """Manages lifecycle of a single, shared LLM provider instance."""

    def __init__(self, opa_client: Optional[OPAClient] = None) -> None:
        """Initializes router with optional OPA client."""
        self._providers: Dict[str, Type[LLMProvider]] = {}
        self._instance: Optional[LLMProvider] = None
        self._lock = asyncio.Lock()
        self.opa_client = opa_client
        self.tracer = trace.get_tracer(__name__)

        # Register default providers
        self.register("openai", OpenAIProvider)
        self.register("bedrock", BedrockProvider)
        self.register("vllm", VLLMProvider)

    def register(self, name: str, provider_class: Type[LLMProvider]) -> None:
        """Registers a new provider class under a name."""
        self._providers[name.lower()] = provider_class

    async def get_provider(self) -> LLMProvider:
        """Returns the shared, lazily-initialized LLM provider."""
        if self._instance:
            return self._instance

        async with self._lock:
            if self._instance:
                return self._instance

            with self.tracer.start_as_current_span("model_gateway.get_provider") as span:
                provider_name = os.getenv("MODEL_PROVIDER", "openai").lower()
                span.set_attribute("provider_name", provider_name)

                # OPA governance check
                if self.opa_client:
                    decision = await self.opa_client.check_policy(
                        input={"provider": provider_name},
                        policy_path="astradesk/model_gateway/provider"
                    )
                    if not decision.get("result", True):
                        logger.error(f"OPA denied provider: {provider_name}")
                        span.add_event("opa_denied_provider")
                        raise ProviderNotFoundError(provider_name)

                provider_class = self._providers.get(provider_name)
                if not provider_class:
                    logger.error(f"Provider not registered: {provider_name}")
                    raise ProviderNotFoundError(provider_name)

                logger.info(f"Initializing LLM provider: {provider_name}")
                self._instance = provider_class()
                logger.info(f"Provider {provider_name} initialized successfully.")
                span.add_event("provider_initialized")

                return self._instance

    async def shutdown(self) -> None:
        """Safely shuts down the active provider."""
        if not self._instance:
            return

        with self.tracer.start_as_current_span("model_gateway.shutdown"):
            logger.info(f"Shutting down provider: {self._instance.__class__.__name__}")
            aclose_method = getattr(self._instance, "aclose", None)
            if aclose_method and inspect.iscoroutinefunction(aclose_method):
                try:
                    await aclose_method()
                    logger.info("Provider shut down successfully.")
                except Exception as e:
                    logger.error(f"Error during provider shutdown: {e}", exc_info=True)
            else:
                logger.debug(f"Provider {self._instance.__class__.__name__} has no aclose() method.")
            self._instance = None


# Global shared router instance
provider_router = ProviderRouter()
