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

# Dockerfile for MCP Gateway
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY mcp/pyproject.toml mcp/README.md ./
COPY mcp/src/ src/

# Install the package
RUN pip install .

# Expose port
EXPOSE 8000

# Environment variables
ENV ENVIRONMENT=prod
ENV OIDC_ISSUER=https://issuer.example.com
ENV OIDC_AUDIENCE=mcp-gateway
ENV REDIS_URL=redis://redis:6379/0
ENV KB_SERVICE_URL=http://kb-service:8000
ENV JIRA_SERVICE_URL=http://jira-service:8000
ENV AUDIT_SINK=stdout://

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "-m", "src.gateway.main"]
