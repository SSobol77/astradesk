# SPDX-License-Identifier: Apache-2.0
"""File: services/api-gateway/src/tools/metrics.py

Project: AstraDesk Framework
Package:  AstraDesk API Gateway

Description:
    Tool for fetching performance metrics from Prometheus.
    Integrates async HTTP, OPA governance, OTel tracing, PII redaction, and RFC 7807 errors.

Env:
    - MONITORING_API_URL
    - ALLOWED_SERVICES
    - WINDOW_RE

Author: Siergej Sobolewski
Since: 2025-10-30

"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Final, Optional

import httpx
from opentelemetry import trace
from opa_client.opa import OpaClient

from model_gateway.guardrails import ProblemDetail

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

MONITORING_API_URL: Final[str] = os.getenv("MONITORING_API_URL", "").rstrip("/")
ALLOWED_SERVICES: Final[set[str]] = {"webapp", "payments-api", "search-service", "database"}
WINDOW_RE: Final[re.Pattern] = re.compile(r"^\d+[smhd]$")


def redact_service_name(service: str) -> str:
    """Redacts service name if not allowed."""
    return "[REDACTED]" if service not in ALLOWED_SERVICES else service


class MetricsError(Exception):
    """Base error for metrics tool."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def to_problem_detail(self) -> ProblemDetail:
        return ProblemDetail(
            type="https://astradesk.com/errors/metrics",
            title="Metrics Error",
            detail=self.message,
            status=500
        )


async def _prom_query(
    client: httpx.AsyncClient,
    query: str,
    metric_name: str,
    service: str,
) -> Optional[float]:
    """Executes a single PromQL query with tracing."""
    with tracer.start_as_current_span(f"prometheus.query.{metric_name}") as span:
        span.set_attribute("query", query)
        span.set_attribute("service", redact_service_name(service))

        try:
            r = await client.get("/api/v1/query", params={"query": query}, timeout=10.0)
            r.raise_for_status()
            data = r.json()
            result = data.get("data", {}).get("result", [])
            if not result:
                span.add_event("no_data")
                return None
            value = float(result[0]["value"][1])
            span.set_attribute("value", value)
            return value
        except Exception as e:
            logger.warning(f"Prometheus query failed ({metric_name}): {e}")
            span.record_exception(e)
            return None


async def metrics(
    service: str,
    window: str = "15m",
    opa_client: Optional[OpaClient] = None,
) -> str:
    """Fetches service metrics from Prometheus with full governance and observability."""
    with tracer.start_as_current_span("tool.metrics") as span:
        span.set_attribute("service", service)
        span.set_attribute("window", window)

        if service not in ALLOWED_SERVICES:
            error_msg = f"Service '{service}' not allowed."
            logger.warning(error_msg)
            raise MetricsError(error_msg)
        if not WINDOW_RE.fullmatch(window):
            error_msg = "Invalid window format (use 5m, 1h, etc.)."
            logger.warning(error_msg)
            raise MetricsError(error_msg)

        if opa_client:
            decision = await opa_client.check_policy(
                input={"service": service, "action": "metrics"},
                policy_path="astradesk/tools/metrics"
            )
            if not decision.get("result", True):
                logger.warning(f"OPA denied metrics for {service}")
                raise MetricsError("Access denied by policy")

        if not MONITORING_API_URL:
            span.add_event("simulation_mode")
            return (
                f"Simulated metrics for '{service}' ({window}):\n"
                f"- CPU: 25%\n- Memory: 640 MB\n- p95: 150 ms"
            )

        queries = {
            "cpu": f'avg(rate(container_cpu_usage_seconds_total{{pod=~"{service}-.*"}}[{window}])) * 100',
            "mem": f'avg(container_memory_usage_bytes{{pod=~"{service}-.*"}}) / 1024 / 1024',
            "p95": f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{job="{service}"}}[{window}])) by (le)) * 1000',
        }

        try:
            async with httpx.AsyncClient(base_url=MONITORING_API_URL, timeout=15.0) as client:
                tasks = [
                    _prom_query(client, queries["cpu"], "cpu", service),
                    _prom_query(client, queries["mem"], "mem", service),
                    _prom_query(client, queries["p95"], "p95", service),
                ]
                cpu, mem, p95 = await asyncio.gather(*tasks)

            lines = [f"Metrics for '{service}' (window {window}):"]
            lines.append(f"- Avg CPU: {cpu:.2f}%" if cpu else "- Avg CPU: N/A")
            lines.append(f"- Avg Memory: {mem:.2f} MB" if mem else "- Avg Memory: N/A")
            lines.append(f"- p95 Latency: {p95:.2f} ms" if p95 else "- p95 Latency: N/A")
            return "\n".join(lines)

        except httpx.TimeoutException:
            raise MetricsError("Timeout connecting to Prometheus")
        except Exception as e:
            logger.exception(f"Critical metrics error :{e}")
            raise MetricsError("Unexpected error fetching metrics")


# Backward compatibility
async def get_metrics(service: str, window: str = "15m") -> str:
    """Alias for backward compatibility."""
    return await metrics(service, window)
