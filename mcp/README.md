# AstraDesk MCP (Model Control Protocol)

Model Control Protocol implementation for AstraDesk AI Framework.

## Overview

MCP is a protocol that standardizes how AI agents interact with tools and services. It provides:
- Standardized tool interfaces
- Security and authentication mechanisms (JWT with JWKS caching)
- Audit and compliance features (multiple audit sinks supported)
- Rate limiting and quota management (Redis-based)
- Metrics collection (Prometheus integration)
- External configuration support (environment variables and YAML files)

## Structure

- `src/gateway/` - MCP Gateway implementation with rate limiting and metrics
- `src/tools/` - Tool base classes and implementations
- `src/clients/` - Client implementations for external services with real HTTP connections
- `src/schemas/` - JSON schemas for tools
- `src/security/` - Authentication, authorization and audit components
- `tests/` - Unit and integration tests including error scenarios

## Installation

```bash
cd mcp
pip install -e .
```

## Configuration

MCP Gateway can be configured in two ways:

1. Environment variables:
   - `ENVIRONMENT` - Environment (dev|stage|prod), defaults to "dev"
   - `OIDC_ISSUER` - OIDC issuer URL
   - `OIDC_AUDIENCE` - Expected audience
   - `OIDC_JWKS_URL` - JWKS URL for token verification
   - `REDIS_URL` - Redis connection URL for caching and rate limiting
   - `KB_SERVICE_URL` - Knowledge base service URL
   - `JIRA_SERVICE_URL` - Jira service URL
   - `AUDIT_SINK` - Audit sink (e.g., kafka://topic, redis://redis:6379/1, http://audit-service:8000)
   - `AUDIT_HASH_ALGO` - Hash algorithm for digests, defaults to "sha256"
   - `AUDIT_RETENTION_DAYS` - Retention period in days, defaults to 30
   - `CONFIG_PATH` - Path to YAML configuration file (if provided, other env vars are ignored)

2. YAML configuration file (see `config.example.yaml`)

## Running the MCP Gateway

```bash
cd mcp
python -m src.gateway.main
```

The gateway will start on port 8000.

## Running Tests

```bash
cd mcp
python -m pytest tests/
```

## Docker

To build and run the MCP Gateway in Docker:

```bash
cd mcp
docker build -t astradesk-mcp .
docker run -p 8000:8000 astradesk-mcp
```

In Docker, you can pass configuration through environment variables or mount a YAML config file.