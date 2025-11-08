# AstraDesk MCP (Model Control Protocol)

Model Control Protocol implementation for AstraDesk AI Framework.

## Overview

MCP is a protocol that standardizes how AI agents interact with tools and services. It provides:
- Standardized tool interfaces
- Security and authentication mechanisms
- Audit and compliance features
- Rate limiting and quota management

## Structure

- `src/gateway/` - MCP Gateway implementation
- `src/tools/` - Tool base classes and implementations
- `src/clients/` - Client implementations for external services
- `src/schemas/` - JSON schemas for tools
- `src/security/` - Authentication, authorization and audit components
- `tests/` - Unit and integration tests

## Installation

```bash
cd mcp
pip install -e .
```

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