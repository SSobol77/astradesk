# SPDX-License-Identifier: Apache-2.0

# Support Domain Pack

## Overview

This pack provides modular support logic for AstraDesk, including ticket triage with Asana (tasks/projects) and Slack (messaging/notifications) integration. All interactions are exclusively via Admin API v1.2.0 (no direct imports from core modules). Designed for production: async, retry-enabled, error handling with ProblemDetail, and full test coverage.

### Purpose
- Agents: Ticket triage with Asana task creation and Slack notifications.
- Tools: Asana adapters for tasks/projects, Slack adapters for messaging.
- Flows: YAML workflows for autoresolve with Asana/Slack.
- Policies: OPA Rego for governance (project/channel restrictions).
- Tests: Pytest with API mocking (respx).

### Prerequisites
- Python 3.14+
- UV for dependency management
- Access to Admin API (/api/admin/v1) with JWT token
- Asana PAT/OAuth token in config
- Slack OAuth token in config

### Setup
```bash
cd packages/domain-support
uv sync --frozen
```

### Usage
1. **Upload Flow**:
   ```python
   from clients.api import AdminApiClient
   client = AdminApiClient(token="your-jwt")
   flow_data = {"name": "autoresolve", "content": open("flows/autoresolve.yaml").read()}
   await client.upload_flow(flow_data)
   ```

2. **Upload Policy**:
   ```python
   policy_data = {"name": "support_policy", "rego_text": open("policies/support.rego").read()}
   await client.upload_policy(policy_data)
   ```

3. **Run Triage**:
   ```python
   tickets = [{"id": "T1", "summary": "Urgent issue"}]
   async for result in triage_tickets(tickets, token="your-jwt"):
       print(result.asana_task_id, result.slack_message_id)
   ```

4. **Create Asana Task**:
   ```python
   adapter = AsanaAdapter(token="your-jwt")
   task = await adapter.create_task({"name": "New Task", "project_gid": "your_project_gid"})
   print(task)
   ```

5. **Post Slack Message**:
   ```python
   adapter = SlackAdapter(token="your-jwt")
   msg = await adapter.post_message({"channel": "#support", "text": "Test message"})
   print(msg)
   ```

### Tests
```bash
uv run pytest tests -v --cov=.
```

### Deployment
- Add to docker-compose.yml as service.
- Use in K8s via Helm (deploy/chart/): Mount volume for flows/policies.
- CI: Integrate with Jenkinsfile for uv sync and pytest.

### Security
- All API calls use JWT BearerAuth.
- Retry with exponential backoff for resilience.
- Errors parsed as ProblemDetail for structured handling.

### Contributing
Fork, add features/tests, PR with coverage >90%.

### License
Apache-2.0 (see SPDX in files).

<br>

---

<br>

## Szczegółowa Konfiguracja OAuth dla Asana i Slack w Domain-Support Pack

> Konfiguracja OAuth to proces uzyskania client_id, client_secret, redirect_uri, i tokenów (access/refresh). Użyjemy Authorization Code Flow (PKCE dla security), bo jest rekomendowany dla bots/apps. Integracja w kodzie: Tokeny pobierane z `/secrets`, używane w headers dla API calls w `tools/asana_adapter.py` i `slack_adapter.py`.

**Uwagi ogólne**:
- **Bezpieczeństwo**: Nigdy nie hardcode tokenów — użyj `/api/admin/v1/secrets` do storage (POST /secrets, GET /secrets/{id}). Rotate tokeny via `/secrets/{id}:rotate`.
- **RBAC**: Upewnij się, że user/role ma dostęp do connectors/secrets (via `/users/{id}:role`).
- **Testy**: Dodaj mocki w tests dla auth failures (401).
- **Deployment**: Konfig w env vars (API_TOKEN w docker-compose.yml), secrets w K8s Secrets (deploy/chart/).

#### 1. Konfiguracja OAuth dla Asana

**Krok-po-kroku**:
1. **Utwórz Asana Developer App**:
   - Wejdź na [developers.asana.com/apps](https://app.asana.com/0/developer-console).
   - Zaloguj się kontem Asana (jeśli nie masz, utwórz darmowe).
   - Kliknij "Create new app".
   - Wypełnij:
     - App name: "AstraDesk Support Integration".
     - Description: "Integrates with Asana for ticket tasks".
     - Redirect URL: "http://localhost:8080/callback" (dla dev; w prod użyj secure URL, np. "https://your-domain.com/callback").
   - Zapisz — otrzymasz `Client ID` i `Client Secret`.

2. **Uzyskaj Token (Authorization Code Flow)**:
   - Użyj browsera lub Postman do auth:
     - URL auth: `https://app.asana.com/-/oauth_authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&state=random_state`.
     - Po login, otrzymasz `code` w redirect (np. `?code=abc123`).
     - Exchange code na token via POST /oauth_token:
       ```bash
       curl -X POST https://app.asana.com/-/oauth_token \
         -d "grant_type=authorization_code" \
         -d "client_id={CLIENT_ID}" \
         -d "client_secret={CLIENT_SECRET}" \
         -d "redirect_uri={REDIRECT_URI}" \
         -d "code={CODE}"
       ```
     - Response: `{ "access_token": "...", "refresh_token": "...", "expires_in": 3600 }`.

3. **Zapisz Token w Secrets via API**:
   - Użyj `/secrets`:
     ```bash
     curl -X POST http://localhost:8080/api/admin/v1/secrets -H "Authorization: Bearer {JWT}" -d '{
       "name": "asana_oauth",
       "type": "oauth",
       "value": "{access_token}",
       "refresh_token": "{refresh_token}",
       "client_id": "{CLIENT_ID}",
       "client_secret": "{CLIENT_SECRET}"
     }'
     ```
   - Rotate: `POST /secrets/{id}:rotate`.

4. **Integracja w kodzie** (`tools/asana_adapter.py`):
   - Pobierz token z `/secrets/{id}` w init, użyj w probe (headers: Authorization: Bearer {asana_token}).
   - Update adapter z OAuth refresh if expired (check 401, refresh via `/oauth_token` with grant_type=refresh_token).

#### 2. Konfiguracja OAuth dla Slack

**Krok-po-kroku**:
1. **Utwórz Slack App**:
   - Wejdź na [api.slack.com/apps](https://api.slack.com/apps).
   - Kliknij "Create New App" > "From scratch".
   - Wypełnij:
     - App Name: "AstraDesk Support Bot".
     - Workspace: Wybierz workspace.
   - Dodaj features: Bots (dla messaging).
   - OAuth & Permissions:
     - Scopes: `chat:write`, `channels:join`, `users:read` (dla post message, notifications).
     - Redirect URL: "http://localhost:8080/callback" (dla dev).
   - Zapisz — otrzymasz `Client ID` i `Client Secret`.

2. **Uzyskaj Token (OAuth 2.0 Flow)**:
   - URL auth: `https://slack.com/oauth/v2/authorize?client_id={CLIENT_ID}&scope=chat:write,channels:join&redirect_uri={REDIRECT_URI}`.
   - Po approve, otrzymasz `code` w redirect.
   - Exchange code na token via POST /oauth.v2.access:
     ```bash
     curl -X POST https://slack.com/api/oauth.v2.access \
       -d "client_id={CLIENT_ID}" \
       -d "client_secret={CLIENT_SECRET}" \
       -d "code={CODE}" \
       -d "redirect_uri={REDIRECT_URI}"
     ```
     - Response: `{ "ok": true, "access_token": "...", "scope": "...", "bot_user_id": "...", "team_id": "..." }`.

3. **Zapisz Token w Secrets via API**:
   - Podobnie jak Asana:
     ```bash
     curl -X POST http://localhost:8080/api/admin/v1/secrets -H "Authorization: Bearer {JWT}" -d '{
       "name": "slack_oauth",
       "type": "oauth",
       "value": "{access_token}",
       "client_id": "{CLIENT_ID}",
       "client_secret": "{CLIENT_SECRET}"
     }'
     ```

4. **Integracja w kodzie** (`tools/slack_adapter.py`):
   - Pobierz token z `/secrets/{id}` w init, użyj w probe (headers: Authorization: Bearer {slack_token}).
   - Handle rate limits (1/sec): Add asyncio.sleep if needed, or use retry with backoff.

---

### Podsumowanie
Konfiguracja OAuth dla Asana i Slack jest szczegółowa, z krokami do integracji w kodzie. Kod w `domain-support/` został zaktualizowany o adapters z OAuth refresh. Zgodne z API-only i production-ready. Czas: ~2-3 dni. Daj znać, jeśli potrzeba więcej! 🚀