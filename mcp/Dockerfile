# Dockerfile for MCP Gateway
FROM python:3.14-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY pyproject.toml README.md ./
COPY src/ src/

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