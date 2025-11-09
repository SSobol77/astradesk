# AstraDesk Domain Packs (`packages/`)

## Overview

The `packages/` directory in the AstraDesk project is the central location for domain-specific packs, which are modular, pip-installable Python packages encapsulating domain logic for specific use cases (e.g., support, finance, supply chain). Each pack provides a self-contained set of agents, tools, flows, policies, and tests, enabling extensibility and reusability across the AstraDesk platform.

This directory integrates with the core system (`src/`) and Admin API (`src/admin/`, `openapi/astradesk-admin.v1.yaml`) to allow dynamic loading, management, and governance of domain-specific functionality. Packs are designed to be open-source-friendly, with clear documentation and a standardized structure to facilitate community contributions.

## Purpose

- **Modularity**: Encapsulate domain logic (e.g., support ticket triage, financial forecasting) in isolated packages.
- **Scalability**: Enable dynamic loading of packs via `src/runtime/registry.py` for runtime integration.
- **Governance**: Integrate with Admin API for management (install/list packs) and OPA policies (`policies/*.rego`) for compliance.
- **Extensibility**: Allow third-party or internal teams to add new domains without modifying core code.
- **CI/CD Integration**: Support build, test, and deployment via `Makefile`, `Jenkinsfile`, and Helm (`deploy/chart/`).

## Key Integrations

- **Runtime**: Packs register agents/tools via `src/runtime/registry.py` and interact with `src/runtime/planner.py` (Intent Graph) and `src/model_gateway/router.py` (LLM calls).
- **Admin API**: Endpoints `/domain-packs` and `/domain-packs/{name}:install` in `openapi/astradesk-admin.v1.yaml` manage packs.
- **Eventing**: Publish/subscribe to events via NATS (`src/runtime/events.py`, `docker-compose.yml:nats`).
- **Storage**: Use Postgres 18 (`docker-compose.yml:db`) with pgvector for metadata and Redis for job queues (`src/admin/worker.py`).
- **Observability**: Metrics/traces via OpenTelemetry (`pyproject.toml:opentelemetry`) exported to Grafana (`grafana/dashboard-astradesk.json`).

## Directory Structure

The `packages/` directory contains subdirectories for each domain pack, each following a standardized structure. Currently implemented domain packs include:

- **domain-support**: Support ticket triage with Asana and Slack integrations
- **domain-ops**: Operational monitoring and service management
- **domain-finance**: Financial forecasting and ERP integrations
- **domain-supply**: Supply chain management and SAP integrations

Each pack provides:

```plaintext
packages/
├── domain-support/                # Support domain pack - MCP server on port 8001
│   ├── agents/                   # Python agent logic
│   │   └── triage.py             # Support ticket triage agent
│   ├── tools/                    # Tool adapters (e.g., JIRA, Slack)
│   │   ├── mcp_server.py        # MCP server implementation
│   │   └── jira_adapter.py       # JIRA API client
│   ├── flows/                    # AstraDSL flows (YAML)
│   │   └── autoresolve.yaml      # Auto-resolve ticket flow
│   ├── policies/                 # OPA/Rego policies for governance
│   │   └── support.rego          # Policy rules for support
│   ├── tests/                    # Unit and integration tests
│   │   └── test_triage.py        # Tests for triage agent
│   ├── pyproject.toml            # Dependencies and metadata (UV-managed)
│   ├── Dockerfile                # Container build for MCP server
│   └── README.md                 # Pack-specific documentation
├── domain-ops/                   # Ops domain pack - MCP server on port 8002
│   ├── agents/
│   │   └── ops.py                # Operational monitoring agent
│   ├── tools/
│   │   ├── mcp_server.py        # MCP server implementation
│   │   └── metrics.py            # Prometheus metrics adapter
│   ├── flows/
│   │   └── incident_response.yaml # Incident response flow
│   ├── policies/
│   │   └── ops.rego              # Policy rules for operations
│   ├── tests/
│   │   └── test_ops.py           # Tests for ops agent
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── README.md
├── domain-finance/               # Finance domain pack - MCP server on port 8003
│   ├── agents/
│   │   └── forecast.py           # Financial forecasting agent
│   ├── tools/
│   │   ├── mcp_server.py        # MCP server implementation
│   │   └── erp_oracle.py         # Oracle ERP adapter
│   ├── flows/
│   │   └── forecast_mtd.yaml     # Month-to-date forecast flow
│   ├── policies/
│   │   └── finance.rego          # Policy rules for finance
│   ├── tests/
│   │   └── test_forecast.py      # Tests for forecast agent
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── README.md
├── domain-supply/                # Supply chain domain pack - MCP server on port 8004
│   ├── agents/
│   │   └── replenish.py          # Inventory replenishment agent
│   ├── tools/
│   │   ├── mcp_server.py        # MCP server implementation
│   │   └── sap_mm.py             # SAP MM adapter
│   ├── flows/
│   │   └── exception_routing.yaml  # Exception routing flow
│   ├── policies/
│   │   └── supply.rego           # Policy rules for supply
│   ├── tests/
│   │   └── test_replenish.py     # Tests for replenish agent
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── README.md
```

## Subdirectory Details

- **agents/**: Python classes inheriting from `astradesk.runtime.AgentBase` for domain-specific logic (e.g., ticket triage, forecasting). Integrates with `src/model_gateway/` for LLM calls.
- **tools/**: Async Python adapters for external APIs (e.g., JIRA, Oracle ERP, SAP MM) using `httpx` or similar.
- **flows/**: YAML files in AstraDSL format defining workflows (triggers, steps, policies). Parsed by `src/runtime/planner.py`.
- **policies/**: OPA Rego files for governance (e.g., restricting JQL queries in JIRA). Loaded by `src/runtime/policy.py`.
- **tests/**: Pytest-based unit and integration tests for agents/tools. Run via `make test-packs`.
- **pyproject.toml**: UV-managed dependencies, specifying `astradesk>=0.3.0` and domain-specific libraries (e.g., `prophet` for finance).
- **README.md**: Pack-specific setup, usage, and examples.

## OAuth Configuration for External Services

This section provides detailed instructions for configuring OAuth for services like Asana and Slack, used in tools such as `asana_adapter.py` and `slack_adapter.py`. Tokeny are stored securely in the Admin API via `/secrets` endpoints to avoid hardcoding and enable rotation. In code, fetch tokens from `/secrets/{id}` and use in headers for API calls.

### Asana OAuth Configuration

#### 1. Register an Asana App
- Go to the Asana Developer Console: [https://app.asana.com/0/developer-console](https://app.asana.com/0/developer-console).
- Log in with your Asana account (create a free one if needed).
- Click "Create new app".
- Fill in:
  - App name: "AstraDesk Support Integration".
  - Description: "Integrates with Asana for ticket tasks".
  - Redirect URL: "http://localhost:8080/callback" (for dev; use HTTPS for prod, e.g., "https://your-domain.com/callback").
  - OAuth Permission scopes: Specify scopes like `projects:read`, `tasks:read`, `tasks:write`, `tasks:delete`, or toggle "Full permissions".
- Save the app to obtain `Client ID` and `Client Secret` (from OAuth tab).

#### 2. Obtain Access and Refresh Tokens
- Use Authorization Code Flow.
- Redirect user to auth URL:
  ```
  https://app.asana.com/-/oauth_authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&state=random_state&code_challenge_method=S256&code_challenge={CODE_CHALLENGE}&scope=projects:read%20tasks:read%20tasks:write%20tasks:delete
  ```
  - Generate `code_challenge` from random `code_verifier` (PKCE for security).
- After user approval, get `code` from redirect URI query (e.g., `?code=abc123&state=random_state`).
- Exchange code for tokens via POST to `https://app.asana.com/-/oauth_token`:
  ```
  curl --location 'https://app.asana.com/-/oauth_token' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=authorization_code' \
  --data-urlencode 'client_id={CLIENT_ID}' \
  --data-urlencode 'client_secret={CLIENT_SECRET}' \
  --data-urlencode 'redirect_uri={REDIRECT_URI}' \
  --data-urlencode 'code={CODE}' \
  --data-urlencode 'code_verifier={CODE_VERIFIER}'
  ```
- Response: `{ "access_token": "...", "refresh_token": "...", "expires_in": 3600, "data": {user info} }`.

#### 3. Store Tokens in Secrets API
- Use POST /secrets to store:
  ```
  curl -X POST http://localhost:8080/api/admin/v1/secrets -H "Authorization: Bearer {JWT}" -d '{
    "name": "asana_oauth",
    "type": "oauth",
    "value": "{access_token}",
    "refresh_token": "{refresh_token}",
    "client_id": "{CLIENT_ID}",
    "client_secret": "{CLIENT_SECRET}"
  }'
  ```
- Fetch in code: GET /secrets/asana_oauth.
- Rotate: POST /secrets/{id}:rotate.

### Slack OAuth Configuration

#### 1. Register a Slack App
- Go to [api.slack.com/apps](https://api.slack.com/apps).
- Click "Create New App" > "From scratch".
- Fill in:
  - App Name: "AstraDesk Support Bot".
  - Workspace: Select your workspace.
- Add features: Bots for messaging.
- OAuth & Permissions:
  - Scopes: `chat:write`, `channels:join`, `users:read`.
  - Redirect URL: "http://localhost:8080/callback" (HTTPS for prod).
- Save to obtain `Client ID` and `Client Secret`.

#### 2. Obtain Access Token
- Use OAuth 2.0 Flow.
- Redirect user to auth URL:
  ```
  https://slack.com/oauth/v2/authorize?client_id={CLIENT_ID}&scope=chat:write,channels:join&redirect_uri={REDIRECT_URI}
  ```
- After approval, get `code` from redirect URI query.
- Exchange code for token via POST to `https://slack.com/api/oauth.v2.access`:
  ```
  curl -X POST https://slack.com/api/oauth.v2.access \
  -d "client_id={CLIENT_ID}" \
  -d "client_secret={CLIENT_SECRET}" \
  -d "code={CODE}" \
  -d "redirect_uri={REDIRECT_URI}"
  ```
- Response: `{ "ok": true, "access_token": "...", "scope": "...", "bot_user_id": "...", "team_id": "..." }`.

#### 3. Store Tokens in Secrets API
- Use POST /secrets:
  ```
  curl -X POST http://localhost:8080/api/admin/v1/secrets -H "Authorization: Bearer {JWT}" -d '{
    "name": "slack_oauth",
    "type": "oauth",
    "value": "{access_token}",
    "client_id": "{CLIENT_ID}",
    "client_secret": "{CLIENT_SECRET}"
  }'
  ```
- Fetch in code: GET /secrets/slack_oauth.
- Rotate: POST /secrets/{id}:rotate.

#### Usage in Code

- In adapters (e.g., `asana_adapter.py`, `slack_adapter.py`), fetch tokens from `/secrets` and use in probe calls (headers: Authorization: Bearer {token}).

<br>

## Integration with Core System

#### Admin API

**Endpoints:** Managed via src/admin/routers.py and openapi/astradesk-admin.v1.yaml.

**GET /domain-packs:** Lists installed packs (scans packages/).

**POST /domain-packs/{name}:install:** Installs pack (triggers UV sync and registry load).

**RBAC:** Requires admin or operator role (checked via src/runtime/auth.py).

#### Runtime

**Dynamic Loading:** src/runtime/registry.py scans packages/ and loads agents/tools using importlib.

**Flows:** Parsed by src/runtime/planner.py for Intent Graph execution.

**Policies:** Loaded by src/runtime/policy.py for OPA evaluation.

**Events:** Published to NATS (src/runtime/events.py) for auditing (services/auditor/main.py).

#### Database

**Metadata:** Stored in Postgres 18 (src/admin/models.py for tables like agents, flows).

**Jobs:** Managed via Arq/Redis (src/admin/worker.py for async tasks like reindexing).

<br>

#### Testing

##### Unit and Integration Tests

- Run tests for a specific pack:cd packages/domain-support

```sh
uv run pytest tests
```

- Run all pack tests:make test-packs  ask `# Defined...` in Makefile

- End-to-End Tests

- Use Playwright in services/admin-portal for UI tests: 

```sh
cd services/admin-portal

npx playwright test
```

- Test Admin API endpoints: make test  # Runs `tests/test_api.py` and `tests/test_packs.py`

<br>

### Deployment

#### Local

Start with docker-compose:make up  # Includes **domain-support**, **domain-finance**, **domain-supply** services

#### Production

**Helm:** Deploy via deploy/chart/ (updated `values.yaml` with `packs.replicas`).

```sh
make helm-deploy  # helm upgrade 

--install astradesk deploy/chart
```

**Istio:** Routes for /domain-packs in deploy/istio/41-virtualservice-astradesk-api.yaml.

**Terraform:** S3 storage for flows/reports in infra/main.tf.

<br>

### CI/CD

**Jenkins:** Stage Build Packs in Jenkinsfile runs make build-packs.

**Makefile:**

```Makefile
build-packs:  ## Build all domain packs
    for pack in packages/domain-*; do \
        cd $$pack && uv sync --frozen && cd ../..; \
    done
test-packs:   ## Test all domain packs
    for pack in packages/domain-*; do \
        cd $$pack && uv run pytest tests && cd ../..; \
    done
```

<br>


### Observability

**Metrics:** OpenTelemetry traces for pack agents/tools (pyproject.toml:opentelemetry).

**Dashboards:** Updated grafana/dashboard-astradesk.json with pack-specific metrics (e.g., triage_latency_ms).

**Logs:** Published to NATS and stored in Postgres (services/auditor).

<br>

### Security

**RBAC:** Enforced via src/runtime/auth.py (JWT with role claims).

**Policies:** OPA rules in policies/*.rego ensure compliance (e.g., restrict JIRA JQL to specific projects).

**Secrets:** Managed via Admin API (/secrets) and stored in K8s Secrets (deploy/chart/).

**Audit:** Events logged to services/auditor with ED25519 signatures (src/admin/models.py:audit).

<br>

#### Troubleshooting

**Dependency Issues:** Ensure UV lock is updated (uv lock in root and each pack).

**API Errors:** Check docker logs api or Grafana traces for 5xx errors.

**Pack Loading:** Verify src/runtime/registry.py logs for import errors.

**Tests Failing:** Run pytest --log-cli-level=DEBUG in pack directory.


### Contributing

**To contribute a new pack:**

- Fork the repository and create a new branch (git checkout -b domain-<name>).

- Follow the "Creating a New Domain Pack" steps above.

- Submit a PR with updated packages/domain-<name>/README.md and tests.

- Ensure make test-packs passes and update docs/api.md if new endpoints are added.

---

#### License

AstraDesk is licensed under the Apache-2.0 License (see LICENSE).