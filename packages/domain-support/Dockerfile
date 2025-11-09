# SPDX-License-Identifier: Apache-2.0
# AstraDesk Support Domain MCP Server Dockerfile

FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r astradesk && useradd -r -g astradesk astradesk

# Set work directory
WORKDIR /app

# Copy requirements
COPY packages/domain-support/requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY packages/domain-support/ ./

# Change ownership to non-root user
RUN chown -R astradesk:astradesk /app

# Switch to non-root user
USER astradesk

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Start application
CMD ["python", "tools/mcp_server.py"]