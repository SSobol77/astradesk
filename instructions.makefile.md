# AstraDesk — Makefile Workflow

The root `Makefile` orchestrates common development tasks across Python, Java,
and Node modules. Use these recipes when you prefer curated commands over raw
docker compose or manual scripts.

## Prerequisites
- Tooling from `instructions.md` (`uv`, npm, JDK, docker).
- `.env` configured.

## Core targets
1. **Dependency sync (Python)**
   ```bash
   make sync
   ```
   Installs/updates Python deps via `uv`.

2. **Quality gates**
   ```bash
   make lint
   make type
   ```

3. **Run the full test suite**
   ```bash
   make test        # python + java + node
   make test-python # or language-specific
   make test-java
   make test-admin
   ```

4. **Build artifacts**
   ```bash
   make build       # python, java, admin portal builds
   ```

5. **Spin up local dependencies**
   ```bash
   make up-deps     # db, mysql, redis, nats, ticket-adapter
   ```

6. **Run the API locally with Docker-backed deps**
   ```bash
   make run-local
   ```
   This leaves uvicorn running on port 8000. Stop with Ctrl+C.

7. **Bring up the full container stack**
   ```bash
   make up
   ```

8. **Tear down containers**
   ```bash
   make down
   ```

9. **Inspect logs**
   ```bash
   make logs        # all services
   make logs-api
   make logs-auditor
   ```

## Data workflows
- Initialize pgvector schema: `make migrate`
- Ingest documentation into RAG: `make ingest`, `make ingest-support`, `make ingest-ops`

## Advanced automation
- Istio / Terraform / Helm deployment: `make apply-istio`, `make terraform-apply`, `make helm-deploy`
- Config management (dry-run/full): `make ansible-deploy`, `make puppet-deploy`, `make salt-deploy`

Consult the `Makefile` for the full list via `make help`.

