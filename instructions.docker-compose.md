<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: instructions.docker-compose.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# AstraDesk — Docker Compose Guide

This workflow runs every service (API, admin portal, ticket adapter, auditor,
supporting databases) inside containers.

## Prerequisites
- Docker Engine 24+ with the Compose plugin.
- `.env` populated (see `instructions.md`).

## Step-by-step
1. **Build images (only first time or after code changes)**
   ```bash
   docker compose build
   ```

2. **Launch the entire stack**
   ```bash
   docker compose up -d
   ```
   Services come up in dependency order defined in `docker-compose.yml`. Wait
   until health checks pass:
   ```bash
   docker compose ps
   ```

3. **Tail logs**
   ```bash
   docker compose logs -f api admin ticket-adapter auditor
   ```

4. **Access endpoints**
   - API Gateway: <http://localhost:8000/healthz>
   - Admin Portal UI: <http://localhost:3000>
   - Ticket Adapter Actuator: <http://localhost:8081/actuator/health>
   - Prometheus: <http://localhost:9090>

5. **Run one-off commands inside containers**
   ```bash
   docker compose exec api uv run pytest -k "smoke"
   docker compose exec admin npm run lint
   ```

6. **Stop everything and remove volumes**
   ```bash
   docker compose down -v
   ```

## Partial setups
- **Dependencies only (for local API dev):**
  ```bash
  docker compose up -d db mysql redis nats ticket-adapter
  ```
- **Restart a single service:**
  ```bash
  docker compose restart api
  ```

## Troubleshooting
- Health checks failing → inspect individual service logs.
- Port collisions → adjust published ports in `docker-compose.yml`.
- Database migrations → run `docker compose exec api uv run python scripts/ingest_docs.py support` as needed.

## Reproducible build baseline (issue #41)

- All Python runtime images build from tracked `pyproject.toml` + the root
  `uv.lock` (workspace members) via a pinned `ghcr.io/astral-sh/uv` builder
  stage — never `pip install`, never `requirements.txt`. `mcp/` is a standalone
  bounded context excluded from the root uv workspace, so it carries its own
  tracked `mcp/uv.lock`.
- Every runtime image declares a fixed numeric non-root `USER` (UID/GID
  `10001:10001` for Python/Java images; `1000:1000` for the Node admin-portal
  image, reusing the official `node:22-alpine` image's built-in `node`
  account).
- Base images, databases, and caches are pinned by digest
  (`image@sha256:...`), with a comment noting the human-readable tag —
  `docker:S8431`-style linters flag combining a tag and a digest on one line.
- `docker-compose.yml` and `docker-compose.dev.yml` share the same pinned
  `pgvector/pgvector`, `redis`, and `nats` baselines. Dev intentionally uses
  the `pgvector/pgvector` image (not vanilla `postgres`) because
  `migrations/0001_init_pgvector.sql` requires the `vector` extension.
- `kb-service`/`jira-service` in `docker-compose.yml` are opt-in stub
  placeholders (`profiles: ["no-start"]`). `mcp`'s `depends_on` marks them
  `required: false` so the default (no-profile) Compose graph validates and
  starts without them.
- Run `make verify-build-baseline` (or
  `uv run python scripts/ci/verify_build_baseline.py`) to check these
  invariants against tracked files only; it also runs in CI
  (`.github/workflows/ci.yml`, `.gitlab-ci.yml`).
