# SPDX-License-Identifier: Apache-2.0
"""File: services/api-gateway/src/tools/tickets_proxy.py

Project: AstraDesk Framework
Package:  AstraDesk API Gateway

Description:
    Asynchronous proxy for ticketing system (ticket-adapter-java).
    Supports create_ticket with mTLS authentication, retry mechanisms,
    OPA governance, OpenTelemetry tracing, STUB fallback, and RFC 7807 errors.
    Production-ready with comprehensive error handling and policy enforcement.

Env:
  - TICKETS_BASE_URL (np. http://localhost:8082)
  - TICKETS_API_TOKEN (opcjonalnie)
  - TICKETS_DISABLE_STUB=1 aby wyłączyć fallback i zwracać błąd

mTLS for Istio:
  - CERT_FILE = "SERVICE_CERT"
  - KEY_FILE = "SERVICE_KEY"
  - CA_FILE = "ROOT_CA"

Author: Siergej Sobolewski
Since: 2025-10-25
"""

from __future__ import annotations

import os
import uuid
import logging
from typing import Any, Dict, Optional

import httpx
from httpx import ConnectError, ConnectTimeout, ReadTimeout, PoolTimeout, HTTPStatusError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential, before_sleep_log

from opentelemetry import trace
from opa_python_client import OPAClient

from services.api_gateway.src.model_gateway.base import ProblemDetail

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Configuration
TICKETS_BASE_URL: str = os.getenv("TICKETS_BASE_URL", "https://ticket-adapter.tickets.svc.cluster.local:8081").rstrip("/")
TICKETS_API_TOKEN: Optional[str] = os.getenv("TICKETS_API_TOKEN")
TICKETS_DISABLE_STUB: bool = os.getenv("TICKETS_DISABLE_STUB", "0").lower() in ("1", "true", "yes")

# mTLS for Istio
CERT_FILE = os.getenv("SERVICE_CERT", "/etc/istio/certs/cert-chain.pem")
KEY_FILE = os.getenv("SERVICE_KEY", "/etc/istio/certs/key.pem")
CA_FILE = os.getenv("ROOT_CA", "/etc/istio/certs/ca-cert.pem")

_http: Optional[httpx.AsyncClient] = None


def _client() -> httpx.AsyncClient:
    global _http
    if _http is None:
        _http = httpx.AsyncClient(
            base_url=TICKETS_BASE_URL,
            timeout=httpx.Timeout(connect=3.0, read=15.0, write=15.0, pool=3.0),
            cert=(CERT_FILE, KEY_FILE) if os.path.exists(CERT_FILE) else None,
            verify=CA_FILE if os.path.exists(CA_FILE) else True,
        )
    return _http


def _stub_ticket(title: str, description: str) -> str:
    fake_id = f"TCK-{uuid.uuid4().hex[:8].upper()}"
    logger.info("tickets_proxy: STUB active → %s", fake_id)
    return (
        f"Created ticket (STUB): {fake_id}\n"
        f"Title: {title}\n"
        f"Description: {description or '(none)'}\n"
        f"Warning: ticket adapter unreachable ({TICKETS_BASE_URL})."
    )


def redact_ticket_title(title: str) -> str:
    return title[:30] + "..." if len(title) > 30 else title


class TicketsError(Exception):
    """Base error for tickets proxy."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def to_problem_detail(self) -> ProblemDetail:
        return ProblemDetail(
            type="https://astradesk.com/errors/tickets",
            title="Tickets Proxy Error",
            detail=self.message,
            status=500
        )


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, max=4.0),
    retry=retry_if_exception_type((ConnectError, ConnectTimeout, ReadTimeout, PoolTimeout, HTTPStatusError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
async def _call_adapter(
    title: str,
    description: str,
    priority: str,
    claims: Optional[Dict[str, Any]],
    request_id: Optional[str],
) -> str:
    with tracer.start_as_current_span("tickets.call_adapter") as span:
        span.set_attribute("title", redact_ticket_title(title))
        span.set_attribute("priority", priority)

        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if TICKETS_API_TOKEN:
            headers["Authorization"] = f"Bearer {TICKETS_API_TOKEN}"
        if request_id:
            headers["X-Request-ID"] = request_id
        if claims and "sub" in claims:
            headers["X-User-ID"] = str(claims["sub"])

        payload = {"title": title, "description": description, "priority": priority}

        try:
            resp = await _client().post("/api/tickets", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            ticket_id = data.get("id") or data.get("ticketId") or f"TCK-{uuid.uuid4().hex[:8].upper()}"
            url = data.get("url") or f"{TICKETS_BASE_URL}/tickets/{ticket_id}"
            return f"Created ticket: {ticket_id}\nLink: {url}\nTitle: {data.get('title', title)}"
        except Exception as e:
            span.record_exception(e)
            raise


async def create_ticket(
    title: str,
    description: str,
    priority: str = "medium",
    claims: Optional[Dict[str, Any]] = None,
    opa_client: Optional[OPAClient] = None,
    request_id: Optional[str] = None,
) -> str:
    """Creates a ticket via ticket-adapter with full governance and fallback."""
    with tracer.start_as_current_span("tool.tickets.create_ticket") as span:
        span.set_attribute("title", redact_ticket_title(title))
        span.set_attribute("request_id", request_id or "none")

        if opa_client:
            decision = await opa_client.check_policy(
                input={"user": claims, "action": "create_ticket", "title": title},
                policy_path="astradesk/tickets"
            )
            if not decision.get("result", True):
                logger.warning("OPA denied ticket creation")
                span.add_event("opa_denied")
                raise TicketsError("Access denied by policy")

        try:
            return await _call_adapter(title, description, priority, claims, request_id)
        except Exception as e:
            if TICKETS_DISABLE_STUB:
                logger.error("STUB disabled, failing")
                raise TicketsError("Ticket adapter unreachable") from e
            else:
                logger.warning("Falling back to STUB")
                span.add_event("stub_fallback")
                return _stub_ticket(title, description)
