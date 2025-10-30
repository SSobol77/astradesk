# SPDX-License-Identifier: Apache-2.0
"""File: services/api-gateway/src/tools/ops_actions.py

Project: AstraDesk Framework
Package:  AstraDesk API Gateway

Description:
    Tool for performing operational actions in Kubernetes.
    Integrates kubernetes-asyncio, OPA, OTel tracing, RBAC, whitelist, and RFC 7807 errors.

Env:
    - KUBERNETES_NAMESPACE
    - ALLOWED_SERVICES
    - REQUIRED_ROLE_RESTART

Author: Siergej Sobolewski
Since: 2025-10-30

"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Final, Optional

from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.exceptions import ApiException

from opentelemetry import trace
from opa_client.opa import OpaClient

from runtime.policy import AuthorizationError, require_role
from model_gateway.guardrails import ProblemDetail

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Configuration
KUBERNETES_NAMESPACE: Final[str] = os.getenv("KUBERNETES_NAMESPACE", "default")
ALLOWED_SERVICES: Final[set[str]] = {"webapp", "payments-api", "search-service"}
REQUIRED_ROLE_RESTART: Final[str] = "sre"

# In-cluster config
try:
    config.load_incluster_config()
    logger.info("Loaded in-cluster Kubernetes config.")
except config.ConfigException:
    logger.warning("Failed to load in-cluster config. Ops actions require Kubernetes environment.")


def redact_service_name(service: str) -> str:
    """Redacts service name if not allowed."""
    return "[REDACTED]" if service not in ALLOWED_SERVICES else service


class OpsActionError(Exception):
    """Base error for ops actions."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def to_problem_detail(self) -> ProblemDetail:
        return ProblemDetail(
            type="https://astradesk.com/errors/ops",
            title="Ops Action Error",
            detail=self.message,
            status=500
        )


async def restart_service(
    service: str,
    *,
    claims: Optional[dict] = None,
    opa_client: Optional[OpaClient] = None,
) -> str:
    """Restarts a Kubernetes Deployment using rollout restart with full governance."""
    with tracer.start_as_current_span("tool.ops.restart_service") as span:
        span.set_attribute("service", service)
        span.set_attribute("namespace", KUBERNETES_NAMESPACE)

        logger.info(f"Restart request for service: '{service}'")

        # 1. User RBAC
        try:
            require_role(claims, REQUIRED_ROLE_RESTART)
        except AuthorizationError as e:
            logger.warning(f"Access denied: missing role '{REQUIRED_ROLE_RESTART}' for service '{service}'")
            span.add_event("rbac_denied")
            raise OpsActionError("Insufficient permissions") from e

        # 2. Whitelist
        if service not in ALLOWED_SERVICES:
            logger.warning(f"Service '{service}' not in allowlist")
            span.add_event("whitelist_denied")
            raise OpsActionError(f"Service '{service}' not authorized for restart")

        # 3. OPA governance
        if opa_client:
            decision = await opa_client.check_policy(
                input={"service": service, "action": "restart", "user": claims.get("sub") if claims else None},
                policy_path="astradesk/tools/ops"
            )
            if not decision.get("result", True):
                logger.warning(f"OPA denied restart for {service}")
                span.add_event("opa_denied")
                raise OpsActionError("Access denied by policy")

        # 4. Kubernetes action
        patch_body = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "kubectl.kubernetes.io/restartedAt": datetime.now(timezone.utc).isoformat(timespec='seconds') + "Z"
                        }
                    }
                }
            }
        }

        try:
            async with client.ApiClient() as api_client:
                api = client.AppsV1Api(api_client)
                await asyncio.wait_for(
                    api.patch_namespaced_deployment(
                        name=service,
                        namespace=KUBERNETES_NAMESPACE,
                        body=patch_body
                    ),
                    timeout=10.0
                )
            logger.info(f"Restart triggered for '{service}' in namespace '{KUBERNETES_NAMESPACE}'")
            span.add_event("restart_triggered")
            return f"Restart initiated for service '{service}'."

        except asyncio.TimeoutException:
            logger.error(f"Timeout patching deployment '{service}'")
            span.record_exception(asyncio.TimeoutException())
            raise OpsActionError("Timeout during Kubernetes operation")
        except ApiException as e:
            if e.status == 404:
                logger.error(f"Deployment '{service}' not found in namespace '{KUBERNETES_NAMESPACE}'")
                return f"Error: Service '{service}' not found."
            elif e.status == 403:
                logger.critical(f"Service Account lacks permissions to patch deployments in '{KUBERNETES_NAMESPACE}': {e.body}")
                return "Error: Internal permission issue. Contact admin."
            else:
                logger.error(f"Kubernetes API error (status {e.status}): {e.body}")
                raise OpsActionError(f"Kubernetes error (status {e.status})")
        except Exception as e:
            logger.critical(f"Unexpected error during restart of '{service}': {e}", exc_info=True)
            span.record_exception(e)
            raise OpsActionError("Internal error during operation")
