# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: mcp/src/gateway/middleware.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for mcp/src/gateway/middleware.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""
MCP Gateway Middleware

This module contains middleware implementations for the MCP Gateway:
- MetricsMiddleware: Collects and exposes Prometheus metrics
- TracingMiddleware: OpenTelemetry request tracing (redact-before-emit)
- SecurityHeadersMiddleware: Adds hardening response headers
- PIIProtectionMiddleware: Real ingress PII/secret classifier (fail-closed)
"""

import logging
import os
import time
from collections.abc import Awaitable, Callable

from astradesk_core.redaction import classify, redact_text
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Categories that, when detected in an ingress body, are hard secrets. When
# block mode is enabled these are rejected fail-closed before the body can be
# forwarded to any downstream tool/model.
_BLOCKING_CATEGORIES = frozenset({'secret', 'private_key', 'token'})


def _block_secrets_enabled() -> bool:
    """Whether the gateway should reject requests carrying hard secrets."""
    return os.getenv('MCP_PII_BLOCK_SECRETS', '0').lower() in ('1', 'true', 'yes')


def _redacted_target(request: Request) -> str:
    """Return a span-safe request target: scheme://host/path, query stripped.

    URL query strings frequently carry tokens/credentials, so they are never
    emitted. The path itself is redacted in case an identifier embedded in it
    matches a sensitive pattern (INV-PII-1/INV-PII-4).
    """
    url = request.url
    base = f'{url.scheme}://{url.hostname or ""}'
    if url.port:
        base = f'{base}:{url.port}'
    return redact_text(f'{base}{url.path}')


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect Prometheus metrics for requests"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        response = await call_next(request)

        # Record request duration
        duration = time.time() - start_time

        # Update metrics (handled in gateway.py)
        return response


class TracingMiddleware(BaseHTTPMiddleware):
    """OpenTelemetry request tracing"""

    def __init__(self, app, tracer: trace.Tracer):
        super().__init__(app)
        self.tracer = tracer

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        with self.tracer.start_as_current_span(f'{request.method} {request.url.path}') as span:
            # Add request attributes to span. The full URL (with query string)
            # is NEVER emitted — query strings carry tokens/credentials. We emit
            # a redacted scheme://host/path target instead (INV-PII-1).
            span.set_attribute('http.method', request.method)
            span.set_attribute('http.target', _redacted_target(request))
            span.set_attribute('http.route', request.url.path)

            try:
                response = await call_next(request)

                # Add response attributes
                span.set_attribute('http.status_code', response.status_code)

                if response.status_code >= 400:
                    span.set_status(Status(StatusCode.ERROR))

                return response

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR))
                span.record_exception(e)
                raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'"

        return response


class PIIProtectionMiddleware(BaseHTTPMiddleware):
    """Real ingress PII/secret classifier for the MCP Gateway.

    Replaces the previous no-op. On every request it:

    1. Classifies the request body via the shared, deterministic detector set
       (:mod:`astradesk_core.redaction`).
    2. Attaches the detected categories to ``request.state.pii_classification``
       so downstream handlers/audit can consult the classification
       (``INV-PII-2``) and surfaces them on a span-safe response header
       (category labels only — never raw values).
    3. When ``MCP_PII_BLOCK_SECRETS`` is enabled and the body carries a hard
       secret (token/secret/private key), rejects the request fail-closed with
       422 before it can be forwarded downstream.

    The raw body is never logged, traced, or echoed — only category labels and
    redacted previews leave this boundary (``INV-PII-1``).
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        categories: frozenset[str] = frozenset()
        try:
            body = await request.body()
            if body:
                # decode defensively; classification never raises (fail-closed).
                text = body.decode('utf-8', errors='replace')
                categories = classify(text)
        except Exception:
            # If we cannot read/inspect the body, treat it as sensitive so the
            # request is conservatively flagged rather than silently trusted.
            logger.warning('PII classifier could not inspect request body')
            categories = frozenset({'secret'})

        request.state.pii_classification = sorted(categories)

        if categories & _BLOCKING_CATEGORIES and _block_secrets_enabled():
            # Audit-safe denial: report only the offending category labels.
            blocked = sorted(categories & _BLOCKING_CATEGORIES)
            logger.warning('Ingress blocked: secret-class data detected %s', blocked)
            return JSONResponse(
                status_code=422,
                content={
                    'error': 'pii_policy_violation',
                    'detail': 'Request body contains secret-class data and was rejected.',
                    'categories': blocked,
                },
                headers={'X-PII-Classification': ','.join(blocked)},
            )

        response = await call_next(request)
        if categories:
            response.headers['X-PII-Classification'] = ','.join(sorted(categories))
        return response
