SPDX-License-Identifier: Apache-2.0

# Supply Chain Domain Pack

## Overview

This pack provides modular supply chain logic for AstraDesk, including inventory replenishment and SAP MM integration. All interactions are exclusively via Admin API v1.2.0 (no direct imports from core modules). Designed for production: async, retry-enabled, error handling with ProblemDetail, and full test coverage.

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

### Setup

```bash
cd packages/domain-supply
uv sync --frozen
```

<br>
