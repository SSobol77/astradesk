# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: packages/domain-ops/Dockerfile
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

# Build context is the repository root (uv workspace root); see docker-compose.dev.yml.

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
    build-essential ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# uv workspace manifest + lock, plus every member (uv validates the whole
# workspace graph against uv.lock even when syncing a single --package).
COPY pyproject.toml uv.lock ./
COPY core ./core
COPY services/api-gateway ./services/api-gateway
COPY services/auditor ./services/auditor
COPY services/admin_api ./services/admin_api
COPY packages/ ./packages/

RUN --mount=type=cache,target=/uv-cache \
    uv sync --frozen --no-dev --package astradesk-domain-ops

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

# Copy virtual env from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code. `core` must also be present: astradesk-core is
# installed as an editable workspace member pointing back to /app/core/src.
COPY packages/domain-ops /app/packages/domain-ops
COPY core /app/core

RUN chown -R 10001:10001 /app

USER 10001:10001

# Health check (mcp_server.py binds this port internally)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

EXPOSE 8002

CMD ["python", "-m", "domain_ops.tools.mcp_server"]
