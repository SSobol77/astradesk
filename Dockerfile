# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: Dockerfile
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

# uv 0.11.24 (pinned by digest; no pip install path)
FROM ghcr.io/astral-sh/uv@sha256:99ea34acedc870ba4ad11a1f540a1c04267c9f30aadc465a94406f52dfda2c36 AS uv

# --- Builder Stage ---
# python:3.13-slim (pinned by digest)
FROM python@sha256:eb43ff125d8d58d7449dcba7d336c23bcac412f526d861db493b9994d8010280 AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_EXTRA_INDEX_URL="https://download.pytorch.org/whl/cu121" \
    UV_INDEX_STRATEGY="unsafe-best-match" \
    UV_CACHE_DIR="/uv-cache"

WORKDIR /app

# uv binary copied from the pinned official uv image (no pip install path).
COPY --from=uv /uv /uvx /usr/local/bin/

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ca-certificates curl libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy workspace sources and dependency files
COPY pyproject.toml uv.lock ./
COPY core ./core
COPY services/api-gateway ./services/api-gateway
COPY services/auditor ./services/auditor
COPY services/admin_api ./services/admin_api
COPY mcp ./mcp
COPY packages/ ./packages/

# Sync dependencies with cache
RUN --mount=type=cache,target=/uv-cache \
    uv sync --all-extras --frozen

# --- Runtime Stage ---
# python:3.13-slim (pinned by digest; must match the builder stage above)
FROM python@sha256:eb43ff125d8d58d7449dcba7d336c23bcac412f526d861db493b9994d8010280 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    API_PORT=8080 \
    UV_LINK_MODE=copy \
    # mTLS / Istio
    SSL_CERT_FILE=/secrets/tls.crt \
    SSL_KEY_FILE=/secrets/tls.key \
    CA_CERT_FILE=/secrets/ca.crt

WORKDIR /app

# Copy virtual env from builder 
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy source code
COPY services/api-gateway/src ./src
COPY services/auditor /app/services/auditor
COPY services/admin_api /app/services/admin_api
COPY mcp /app/mcp
COPY core /app/core
COPY packages ./packages

# --- Security & Hardening ---
# Fixed numeric non-root UID/GID (INV-BUILD-3): no reliance on username
# resolution at runtime, safe for read-only-root-filesystem deployments.
RUN groupadd -g 10001 astradesk && \
    useradd -u 10001 -g 10001 -M -s /usr/sbin/nologin astradesk && \
    chown -R 10001:10001 /app && \
    chmod 755 /app

USER 10001:10001

# --- OCI Image Labels (per Open Container Initiative) ---
LABEL org.opencontainers.image.title="AstraDesk API" \
      org.opencontainers.image.version="2.1.0" \
      org.opencontainers.image.description="Enterprise AI Orchestration Framework - Admin API v1.2.0" \
      org.opencontainers.image.vendor="AstraDesk" \
      org.opencontainers.image.authors="ops@astradesk.com" \
      org.opencontainers.image.licenses="GPL-2.0-only" \
      org.opencontainers.image.url="https://astradesk.com" \
      org.opencontainers.image.source="https://github.com/astradesk/framework" \
      org.opencontainers.image.documentation="https://docs.astradesk.com/api/admin/v1" \
      org.opencontainers.image.base.name="python:3.13-slim"

# --- Expose ports ---
EXPOSE 8080

# --- Healthcheck: API + Metrics ---
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/api/admin/v1/health || exit 1

# --- Entrypoint with graceful shutdown ---
ENTRYPOINT ["/app/.venv/bin/uvicorn"]
CMD ["src.gateway.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8080", \
     "--lifespan", "on", \
     "--log-level", "info", \
     "--workers", "1", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]

# --- Optional: mTLS (Istio) ---
# If certificates are mounted at /secrets, Uvicorn will auto-detect via env vars
# Istio sidecar injects traffic, no changes needed in app

# --- Optional: OTel Tracing ---
# Export traces to collector (set OTEL_EXPORTER_OTLP_ENDPOINT in .env)
# Instrumentation already in pyproject.toml (opentelemetry-instrumentation-fastapi)

# --- Sigstore / Cosign (post-build) ---
# In CI: cosign sign --yes --key cosign.key docker.io/youruser/astradesk-api:$TAG
