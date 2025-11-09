SPDX-License-Identifier: Apache-2.0

# Supply Chain Domain Pack

[![Python Version](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](../../LICENSE)
[![MCP Server](https://img.shields.io/badge/MCP-Port%208004-green.svg)](http://localhost:8004)

## Overview

This pack provides modular supply chain logic for AstraDesk, including inventory replenishment and SAP MM integration. All interactions are exclusively via Admin API v1.2.0 (no direct imports from core modules). Designed for production: async, retry-enabled, error handling with ProblemDetail, and full test coverage.

The Supply Chain Domain Pack includes an MCP server running on port 8004 that provides standardized interfaces for supply chain operations and inventory management.

### Purpose

- Agents: Inventory replenishment (e.g., prioritize urgent orders).

- Tools: SAP MM adapters for inventory data.

- Flows: YAML workflows for exception routing.

- Policies: OPA Rego for governance (query restrictions, cost thresholds).

- Tests: Pytest with API mocking (respx).

### Prerequisites

- Python 3.11+
- UV for dependency management
- Access to Admin API (/api/admin/v1) with JWT token
- SAP MM system access (optional, for ERP integration)
- gRPC for SAP S/4HANA communication

### Setup

```bash
cd packages/domain-supply
uv sync --frozen
```

## Usage

### Running the MCP Server

Start the Supply Chain MCP server independently:

```bash
# From project root
python packages/domain-supply/tools/mcp_server.py
```

Or use the Makefile:

```bash
make mcp-supply
```

The server will be available at `http://localhost:8004` with health endpoint at `/health`.

### API Integration

#### Upload Flow:
```python
from clients.api import AdminApiClient
client = AdminApiClient(token="your-jwt")
flow_data = {"name": "exception_routing", "content": open("flows/exception_routing.yaml").read()}
await client.upload_flow(flow_data)
```

#### Upload Policy:
```python
policy_data = {"name": "supply_policy", "rego_text": open("policies/supply.rego").read()}
await client.upload_policy(policy_data)
```

#### Run Replenishment:
```python
inventory_data = [{"item": "WIDGET-A", "stock": 50, "threshold": 100}]
async for result in replenish_inventory(inventory_data, token="your-jwt"):
    print(result.purchase_order)
```

#### Query SAP Data:
```python
adapter = SapMmAdapter(token="your-jwt")
async for item in adapter.query_inventory("SELECT * FROM inventory WHERE stock < threshold"):
    print(item)
```

### Integration with API Gateway

The SupplyAgent is automatically registered with the API Gateway. Use the following to invoke supply chain operations:

```bash
curl -X POST http://localhost:8000/v1/run \
  -H "Authorization: Bearer <jwt-token>" \
  -d '{"agent": "supply", "input": "Check inventory levels for critical items"}'
```

## Tests

```bash
uv run pytest tests -v --cov=.
```

## Deployment

### Docker

The pack includes a `Dockerfile` for containerized deployment. Build and run with:

```bash
# Build
docker build -t astradesk/supply-mcp packages/domain-supply/

# Run
docker run -p 8004:8000 astradesk/supply-mcp
```

### Docker Compose

Add to docker-compose.yml as service:

```yaml
supply-mcp:
  build: ./packages/domain-supply
  ports:
    - "8004:8000"
  environment:
    - LOG_LEVEL=INFO
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

### Kubernetes

Use in K8s via Helm (deploy/chart/): Mount volume for flows/policies.

```bash
helm upgrade --install astradesk ./deploy/chart \
  --set supply.enabled=true
```

### CI/CD

Integrate with Jenkinsfile for uv sync and pytest:

```bash
make build-supply
make test-supply
```

## Security

- All API calls use JWT BearerAuth.
- Retry with exponential backoff for resilience.
- Errors parsed as ProblemDetail for structured handling.
- SAP credentials managed securely via Admin API secrets.

## Contributing

Fork, add features/tests, PR with coverage >90%.

## License

Apache-2.0 (see SPDX in files).
