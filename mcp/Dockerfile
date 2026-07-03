# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: mcp/Dockerfile
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Builds the AstraDesk container image for the associated component.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

# mcp/ is a standalone bounded context deliberately excluded from the root uv
# workspace (its own OIDC verifier stack; see root pyproject.toml comment), so
# it carries its own tracked mcp/uv.lock rather than the root uv.lock.
# Build context is the repository root; see docker-compose.yml.

# uv 0.11.24 (pinned by digest; no pip install path)
FROM ghcr.io/astral-sh/uv@sha256:99ea34acedc870ba4ad11a1f540a1c04267c9f30aadc465a94406f52dfda2c36 AS uv

# --- Builder Stage ---
# python:3.13-slim (pinned by digest)
FROM python@sha256:eb43ff125d8d58d7449dcba7d336c23bcac412f526d861db493b9994d8010280 AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_CACHE_DIR="/uv-cache"

WORKDIR /app

COPY --from=uv /uv /uvx /usr/local/bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY mcp/pyproject.toml mcp/uv.lock mcp/README.md ./
COPY mcp/src/ src/

RUN --mount=type=cache,target=/uv-cache \
    uv sync --frozen --no-dev

# --- Runtime Stage ---
# python:3.13-slim (pinned by digest; must match the builder stage above)
FROM python@sha256:eb43ff125d8d58d7449dcba7d336c23bcac412f526d861db493b9994d8010280 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# curl is required by the HEALTHCHECK below. Fixed numeric non-root UID/GID
# (INV-BUILD-3) created here since it does not depend on the app files below.
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -g 10001 astradesk && \
    useradd -u 10001 -g 10001 -M -s /usr/sbin/nologin astradesk

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY mcp/src/ src/
COPY mcp/__init__.py mcp/config.example.yaml mcp/config.production.yaml ./
COPY mcp/schemas/ schemas/

RUN chown -R 10001:10001 /app

# Environment variables
ENV ENVIRONMENT=prod
ENV OIDC_ISSUER=https://issuer.example.com
ENV OIDC_AUDIENCE=mcp-gateway
ENV REDIS_URL=redis://redis:6379/0
ENV KB_SERVICE_URL=http://kb-service:8000
ENV JIRA_SERVICE_URL=http://jira-service:8000
ENV AUDIT_SINK=stdout://

USER 10001:10001

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "-m", "src.gateway.main"]
