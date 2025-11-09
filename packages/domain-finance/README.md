SPDX-License-Identifier: Apache-2.0

# Finance Domain Pack

[![Python Version](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](../../LICENSE)
[![MCP Server](https://img.shields.io/badge/MCP-Port%208003-green.svg)](http://localhost:8003)

## Overview

This pack provides modular finance logic for AstraDesk, including forecasting and ERP integration. All interactions are exclusively via Admin API v1.2.0 (no direct imports from core modules). Designed for production: async, retry-enabled, error handling with ProblemDetail, and full test coverage.

The Finance Domain Pack includes an MCP server running on port 8003 that provides standardized interfaces for financial operations and forecasting.

## Purpose

Agents: Financial forecasting (e.g., MTD revenue prediction using Prophet).
Tools: Oracle ERP adapters for data fetching.
Flows: YAML workflows for automation (upload via API).
Policies: OPA Rego for governance (cost thresholds, query restrictions).
Tests: Pytest with API mocking (respx).

## Prerequisites

- Python 3.11+
- UV for dependency management
- Access to Admin API (/api/admin/v1) with JWT token
- Oracle ERP system access (optional, for ERP integration)
- Forecasting models (Prophet, scikit-learn)

### Setup

```sh
cd packages/domain-finance
uv sync --frozen
```

## Usage

### Running the MCP Server

Start the Finance MCP server independently:

```bash
# From project root
python packages/domain-finance/tools/mcp_server.py
```

Or use the Makefile:

```bash
make mcp-finance
```

The server will be available at `http://localhost:8003` with health endpoint at `/health`.

### API Integration

#### Upload Flow:
```python
from clients.api import AdminApiClient
client = AdminApiClient(token="your-jwt")
flow_data = {"name": "forecast_mtd", "content": open("flows/forecast_mtd.yaml").read()}
await client.upload_flow(flow_data)
```

#### Upload Policy:
```python
policy_data = {"name": "finance_policy", "rego_text": open("policies/finance.rego").read()}
await client.upload_policy(policy_data)
```

#### Run Forecast:
```python
data = [{"date": "2025-10-01", "revenue": 1000}]
async for result in forecast_financial_data(data, token="your-jwt"):
    print(result.forecast)
```

#### Fetch ERP Data:
```python
adapter = OracleERPAdapter(token="your-jwt")
async for item in adapter.fetch_sales("SELECT revenue, date FROM sales"):
    print(item)
```

### Integration with API Gateway

The FinanceAgent is automatically registered with the API Gateway. Use the following to invoke financial operations:

```bash
curl -X POST http://localhost:8000/v1/run \
  -H "Authorization: Bearer <jwt-token>" \
  -d '{"agent": "billing", "input": "Forecast revenue for next month"}'
```


## Tests

```sh
uv run pytest tests -v --cov=.
```

## Deployment

### Docker

The pack includes a `Dockerfile` for containerized deployment. Build and run with:

```bash
# Build
docker build -t astradesk/finance-mcp packages/domain-finance/

# Run
docker run -p 8003:8000 astradesk/finance-mcp
```

### Docker Compose

Add to docker-compose.yml as service:

```yaml
finance-mcp:
  build: ./packages/domain-finance
  ports:
    - "8003:8000"
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
  --set finance.enabled=true
```

### CI/CD

Integrate with Jenkinsfile for uv sync and pytest:

```bash
make build-finance
make test-finance
```

## Security

- All API calls use JWT BearerAuth.

- Retry with exponential backoff for resilience.

- Errors parsed as ProblemDetail for structured handling.

## Contributing

Fork, add features/tests, PR with coverage >90%.

##### License

Apache-2.0 (see SPDX in files).