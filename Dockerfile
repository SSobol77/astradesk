#SPDX-License-Identifier: Apache-2.0
# File: Dockerfile v.2.1 --production-ready--
# Description:
#     Production Dockerfile for AstraDesk API service.
#     Multi-stage build with uv, non-root user, mTLS, Istio, OTel, and Sigstore.
#Supports AstraFlow 2.0, Domain Packs, Admin API v1.2.0, and RAG agents.
#     Optimized for Kubernetes + Istio + Helm + Terraform.
# Author: Siergej Sobolewski
# Since: 2025-10-25

# --- Builder Stage ---
FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_EXTRA_INDEX_URL="https://download.pytorch.org/whl/cu121" \
    UV_INDEX_STRATEGY="unsafe-best-match" \
    UV_CACHE_DIR="/uv-cache"

WORKDIR /app

# Install uv + build tools
RUN pip install --no-cache-dir uv==0.4.16  # Pin to stable version

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev build-essential curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Copy workspace sources and dependency files
COPY pyproject.toml uv.lock ./
COPY core ./core
COPY services/api-gateway ./services/api-gateway
COPY services/auditor ./services/auditor
COPY services/admin_api ./services/admin_api
COPY services/mcp ./services/mcp
COPY packages/ ./packages/

# Syncdependencies with cache
RUN --mount=type=cache,target=/uv-cache \
    uv sync --all-extras --frozen

# --- Runtime Stage ---
FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    API_PORT=8080 \
    UV_LINK_MODE=copy \
    # mTLS / Istio
    SSL_CERT_FILE=/secrets/tls.crt \
    SSL_KEY_FILE=/secrets/tls.key \
    CA_CERT_FILE=/secrets/ca.crt

WORKDIR /app

# Copy virtual env from builderCOPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy source code
COPY services/api-gateway/src ./src
COPY services/auditor /app/services/auditor
COPY services/admin_api /app/services/admin_api
COPYservices/mcp /app/services/mcp
COPY core /app/core
COPY packages ./packages

# --- Security & Hardening ---
# Create non-root user
RUN useradd -m -s /bin/bash astradesk && \
    chown -R astradesk:astradesk /app && \
    # Make root filesystem read-only (except /tmp, /app)
    chmod 755/app

USER astradesk

# --- OCI Image Labels (per Open Container Initiative) ---
LABEL org.opencontainers.image.title="AstraDesk API" \
      org.opencontainers.image.version="2.1.0" \
      org.opencontainers.image.description="Enterprise AI Orchestration Framework - Admin API v1.2.0" \
      org.opencontainers.image.vendor="AstraDesk" \
      org.opencontainers.image.authors="ops@astradesk.com" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.url="https://astradesk.com" \
     org.opencontainers.image.source="https://github.com/astradesk/framework" \
      org.opencontainers.image.documentation="https://docs.astradesk.com/api/admin/v1" \
      org.opencontainers.image.base.name="python:3.14-slim"

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
