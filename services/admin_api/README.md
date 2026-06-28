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
# Liveness
curl -s http://127.0.0.1:8001/healthz

# Detailed health (components)
curl -s http://127.0.0.1:8001/health/status
```
Expected minimal JSON:
```json
{"status": "ok"}
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

- `GET /healthz` — simple liveness for Kubernetes
- `GET /health/status` — aggregated component health with states `OK | DEGRADED | ERROR`

Implementation lives in `src/astradesk_admin/main.py` and returns structured `pydantic` models.

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

- **Source of truth:** `services/admin-portal/OpenAPI.yaml` (**v1.2.0**)
- Planned: TS client generation for Admin UI + contract tests.

---

## 🧭 Roadmap (short)

- Wire real DB/cache/vector-store health checks
- Add OPA/claims-based auth for admin endpoints
- OpenTelemetry traces/metrics
- CI with `uv` matrix (3.13), Docker, SBOM
- Contract tests vs Admin API v1.2.0

---

## 📝 License

GPL-2.0-only
