SPDX-License-Identifier: Apache-2.0

# Finance Domain Pack

## Overview

This pack provides modular finance logic for AstraDesk, including forecasting and ERP integration. All interactions are exclusively via Admin API v1.2.0 (no direct imports from core modules). Designed for production: async, retry-enabled, error handling with ProblemDetail, and full test coverage.

## Purpose

Agents: Financial forecasting (e.g., MTD revenue prediction using Prophet).
Tools: Oracle ERP adapters for data fetching.
Flows: YAML workflows for automation (upload via API).
Policies: OPA Rego for governance (cost thresholds, query restrictions).
Tests: Pytest with API mocking (respx).

## Prerequisites

Python 3.11+
UV for dependency management
Access to Admin API (/api/admin/v1) with JWT token

### Setup

```sh
cd packages/domain-finance
uv sync --frozen
```

## Usage

##### Upload Flow:
from clients.api import AdminApiClient
client = AdminApiClient(token="your-jwt")
flow_data = {"name": "forecast_mtd", "content": open("flows/forecast_mtd.yaml").read()}
await client.upload_flow(flow_data)


##### Upload Policy:
policy_data = {"name": "finance_policy", "rego_text": open("policies/finance.rego").read()}
await client.upload_policy(policy_data)


##### Run Forecast:

```python
data = [{"date": "2025-10-01", "revenue": 1000}]
async for result in forecast_financial_data(data, token="your-jwt"):
    print(result.forecast)
```

##### Fetch ERP Data:

```python
adapter = OracleERPAdapter(token="your-jwt")
async for item in adapter.fetch_sales("SELECT revenue, date FROM sales"):
    print(item)
```


## Tests

```sh
uv run pytest tests -v --cov=.
```

## Deployment

- Add to docker-compose.yml as service.

- Use in K8s via Helm (deploy/chart/): Mount volume for flows/policies.

- CI: Integrate with Jenkinsfile for uv sync and pytest.

## Security

- All API calls use JWT BearerAuth.

- Retry with exponential backoff for resilience.

- Errors parsed as ProblemDetail for structured handling.

## Contributing

Fork, add features/tests, PR with coverage >90%.

##### License

Apache-2.0 (see SPDX in files).