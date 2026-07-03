<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: services/admin_api/README.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# AstraDesk Admin API

FastAPI-based Admin backend for **AstraDesk** Admin Portal (aligned with **Admin API v1.2.0**).  
**Environment policy:** We target **Python 3.13+** and use **`uv` exclusively** (no `pip`).

> **Spec reference:** Admin API contract: `services/admin-portal/OpenAPI.yaml` (version **1.2.0**).

---

## 🚀 Quick Start (Python 3.13 + uv)

### Prerequisites
- **Python 3.13** (CPython)
- **[`uv`](https://github.com/astral-sh/uv)** installed and on PATH

### Install & Run (dev)
```bash
cd services/admin_api

# Sync deps into uv-managed environment (no pip)
uv sync

# Run the API with autoreload
uv run uvicorn astradesk_admin.main:app --host 0.0.0.0 --port 8001 --reload
```

### Smoke Test
```bash
# Health/dashboard status (public, no token required — see Authentication below)
curl -s http://127.0.0.1:8001/health
```
Expected JSON (shape; actual component states vary):
```json
{"status": "healthy", "components": {"database": "healthy", "vector_store": "healthy", "cache": "degraded"}}
```

---

## 📁 Project Structure

```
services/admin_api/
├─ pyproject.toml
├─ README.md               # this file
└─ src/
   └─ astradesk_admin/
      ├─ __init__.py
      ├─ __main__.py
      └─ main.py
```

- Import path: **`astradesk_admin`**
- Uvicorn target: **`astradesk_admin.main:app`**
- Build backend: **Hatchling** (configured in `pyproject.toml`)
- **src-layout** with explicit Hatch packages:
  ```toml
  [tool.hatch.build.targets.wheel]
  packages = ["src/astradesk_admin"]
  ```

---

## 🔧 Configuration

Use `.env` or exported variables.

Example `.env`:
```dotenv
APP_ENV=dev
APP_NAME=AstraDesk Admin API
# Observability (optional)
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

---

## 🧪 Dev Tooling (uv-only)

```bash
# Lint
uv run ruff check src

# Type check
uv run mypy src

# Tests (when tests/ are present)
uv run -m pytest -q
```

---

## 🩺 Health Endpoints

- `GET /health` — aggregated component health/dashboard status. Deliberately left public
  (no bearer token required): it exposes only coarse component states
  (`healthy | degraded | down`) and no secrets, credentials, or per-user data, so it can
  double as an unauthenticated liveness probe.

Implementation lives in `src/astradesk_admin/main.py` and returns structured `pydantic` models.

---

## 🔐 Authentication & Authorization (NEW-SEC)

Every Admin API operation **except** `/health` and the auto-generated `/docs`, `/redoc`,
`/openapi.json` documentation routes independently requires:

1. A verified Bearer JWT. Missing/invalid tokens are rejected with `401`.
2. The normalized `admin` role on the verified principal. Authenticated callers without
   it are rejected with `403`.

This is implemented in `src/astradesk_admin/auth.py` and is **independent** of the API
Gateway's own `/api/admin/v1/{path}` proxy gate
(`services/api-gateway/src/gateway/auth_dependency.py`): the Admin API does not trust the
Gateway's decision, network placement/Compose isolation, or any forwarded
`X-AstraDesk-*` header as a substitute for its own verification (defense-in-depth,
NEW-SEC). `X-AstraDesk-*` headers are never read as identity by the Admin API — they
are not, and must never become, an authentication mechanism.

### Required environment variables

The Admin API reuses the **same** OIDC variables as the API Gateway (see the root
`.env.example`) — set them identically for both services in production:

| Variable | Purpose |
| --- | --- |
| `AUTH_MODE` | `production` (default, JWKS/RS256) or `local-dev` (see below). |
| `OIDC_ISSUER` | Required in `AUTH_MODE=production`. Expected token `iss`. |
| `OIDC_AUDIENCE` | Required in `AUTH_MODE=production`. Expected token `aud`. |
| `OIDC_JWKS_URL` | Required in `AUTH_MODE=production`. JWKS endpoint for signature verification. |
| `OIDC_ALGORITHMS` | Optional, default `RS256`. |
| `OIDC_ROLES_CLAIM` | Optional, default `roles`. Dotted paths supported (e.g. `realm_access.roles` for Keycloak). |
| `ENVIRONMENT` | Deployment tier. `production`/`prod`/`staging`/`stage` are **deployed tiers**: missing OIDC config aborts startup (`AuthConfigError`) rather than serving unauthenticated. |
| `ASTRADESK_DEV_JWT_SECRET` | `AUTH_MODE=local-dev` only — symmetric HS256 secret for locally-minted test tokens. |

Startup is **fail-closed**: on a deployed tier, missing/invalid OIDC configuration
raises `AuthConfigError` and the process does not start (mirrors the API Gateway's
ISSUE 009 contract — this is a reuse, not a redesign).

### How the JWT is verified

`src/astradesk_admin/auth.py` calls the shared
`astradesk_core.utils.oidc.build_verifier_from_env()` to build its **own** verifier
instance at startup (see `lifespan` in `src/astradesk_admin/main.py`). In
`AUTH_MODE=production` (the only mode allowed on a deployed tier) this verifies the
token's signature via JWKS, plus `iss`, `aud`, `exp`, and `nbf` (if present). The
principal's role list is read from the claim named by `OIDC_ROLES_CLAIM` (default
`roles`); the request is authorized only if that list contains `admin`
(case-insensitive).

### Local-dev auth mode

For local testing without a real IdP, set `AUTH_MODE=local-dev` and
`ASTRADESK_DEV_JWT_SECRET` (see root `.env.example`). This uses a symmetric HS256
verifier instead of JWKS/RS256. It is refused at startup on any deployed tier
(`ENVIRONMENT` ∈ `production`/`prod`/`staging`/`stage`) — it exists only as an
explicitly-named local convenience, never a production fallback.

### Public endpoints

Only these routes require no Bearer token:

- `GET /health` — aggregated component health/dashboard status (`healthy | degraded |
  down` per component). No secrets, credentials, or per-user data.
- `GET /docs`, `GET /redoc`, `GET /openapi.json` — FastAPI's auto-generated API
  documentation/schema. These expose only the API shape (paths, parameters, schemas),
  never live data, so they are intentionally left public.

Every other operation (`/secrets`, `/users`, `/roles`, `/policies`, `/audit`, `/agents`,
`/flows`, `/datasets`, `/connectors`, `/runs`, `/jobs`, `/dlq`, `/settings`,
`/domain-packs`, …) requires a verified Bearer JWT with the `admin` role.

### Example: verifying the gate with curl

```bash
# Missing token -> 401
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8001/secrets
# 401

# Authenticated but non-admin token -> 403
curl -s -o /dev/null -w '%{http_code}\n' \
  -H 'Authorization: Bearer <non-admin-bearer-token>' \
  http://127.0.0.1:8001/secrets
# 403

# Authenticated admin token -> 200
curl -s -o /dev/null -w '%{http_code}\n' \
  -H 'Authorization: Bearer <admin-bearer-token>' \
  http://127.0.0.1:8001/secrets
# 200
```

Replace `<non-admin-bearer-token>` / `<admin-bearer-token>` with real tokens issued by
your OIDC provider (or minted locally under `AUTH_MODE=local-dev`). Never paste real
tokens into logs, tickets, or documentation.

### ⚠️ Operational warning

This service-level guard is **not** a substitute for network-layer protection. Do not
expose the Admin API directly on a public network. Production deployments must still
place it behind mTLS and a NetworkPolicy/Istio `AuthorizationPolicy` restricting which
callers can reach it at all (see
[docs/en/08_security_governance.md §8.13](../../docs/en/08_security_governance.md#813-admin-api-defense-in-depth-new-sec));
that network-layer hardening is tracked separately and is **not** implemented by this
change.

---

## 🐳 Docker (uv-only)

> We avoid `pip` and keep Python at **3.13+**.

Example `Dockerfile` for local dev images:
```Dockerfile
# services/admin_api/Dockerfile
FROM python:3.13-slim

# Install system basics
RUN apt-get update && apt-get install -y --no-install-recommends     curl ca-certificates build-essential &&     rm -rf /var/lib/apt/lists/*

# Install uv (standalone)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh &&     /root/.cargo/bin/uv --version

ENV PATH="/root/.cargo/bin:${PATH}"
WORKDIR /app

# Copy project metadata and sources
COPY pyproject.toml README.md /app/
COPY src /app/src

# Sync runtime deps (no dev extras) into an isolated env
RUN uv sync --frozen --no-dev

EXPOSE 8001
CMD ["uv", "run", "uvicorn", "astradesk_admin.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

Build & run:
```bash
cd services/admin_api
docker build -t astradesk-admin-api:dev .
docker run --rm -p 8001:8001 astradesk-admin-api:dev
```

---

## 🔗 OpenAPI / Contract

- **Source of truth:** `openapi/astradesk-admin.v1.yaml` (**v1.2.0**); `services/admin-portal/OpenAPI.yaml`
  is a symlink to the same file.
- Protected operations declare a `BearerAuth` (`http`/`bearer`/`JWT`) security requirement
  (NEW-SEC) — see `docs/workflows/openapi-contract.md` for the update procedure whenever
  this contract changes.
- Admin Portal TS client (`services/admin-portal/src/api/types.gen.ts`,
  `spec-operations.gen.ts`) is generated from the spec via `npm run openapi:gen`; drift is
  caught by `npm run openapi:check`.

---

## 🧭 Roadmap (short)

- Wire real DB/cache/vector-store health checks
- ~~Add OPA/claims-based auth for admin endpoints~~ — Bearer JWT + `admin` role
  enforcement implemented (NEW-SEC, see Authentication & Authorization above); OPA-based
  policy evaluation for Admin API operations (beyond the existing Gateway-side OPA
  tool-policy gate) remains a possible future enhancement, not implemented here.
- OpenTelemetry traces/metrics
- CI with `uv` matrix (3.13), Docker, SBOM
- Contract tests vs Admin API v1.2.0

---

## 📝 License

GPL-2.0-only
