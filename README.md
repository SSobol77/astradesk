<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: README.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

<p align="center">
  <img src="docs/assets/AstraDesktop.png" alt="AstraDesk - Enterprise AI Framework" width="560"/>
</p>

<br>

# AstraDesk - Enterprise AI Agents Framework

[![License](https://img.shields.io/badge/License-GPL--2.0--only-blue.svg)](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)
[![Python Version](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/downloads/release/python-3130/)
[![JDK Version](https://img.shields.io/badge/JDK-21-orange.svg)](https://openjdk.org/projects/jdk/21/)
[![PyTorch Version](https://img.shields.io/badge/PyTorch-2.9-magenta.svg)](https://pytorch.org/projects/pytorch/)
[![Node.js Version](https://img.shields.io/badge/Node.js-22-brightgreen.svg)](https://nodejs.org/en)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](https://github.com/SSobol77/astradesk/actions)

🌍 **Languages:** 🇺🇸 [English](https://github.com/SSobol77/astradesk/edit/main/README.md) | [Polski](https://github.com/SSobol77/astradesk/edit/main/docs/pl/README.pl.main.md) | [中文](https://github.com/SSobol77/astradesk/blob/main/docs/zh/README.zh-CN.main.md)

<br>

[AstraDesk](https://astradesk.dev)
is an internal framework for building AI agents designed for Support and SRE/DevOps departments.
It provides a modular architecture with ready-to-use demo agents, integrations with databases, messaging systems, and DevOps tools.
The framework supports scalability, enterprise-grade security (OIDC/JWT, RBAC, mTLS via Istio), and full CI/CD automation.

---

## Table of Contents

- [AstraDesk - Enterprise AI Agents Framework](#astradesk---enterprise-ai-agents-framework)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Purpose and Use Cases](#purpose-and-use-cases)
  - [Architecture Overview](#architecture-overview)
  - [Admin Portal](#admin-portal)
    - [Overview](#overview)
    - [Features](#features-1)
    - [Quick Start](#quick-start)
      - [Development Mode](#development-mode)
      - [Environment Variables](#environment-variables)
      - [Mock API Mode (Testing Without Backend)](#mock-api-mode-testing-without-backend)
    - [Available Pages](#available-pages)
    - [Authentication](#authentication)
    - [Architecture](#architecture)
    - [Tech Stack](#tech-stack)
    - [Links](#links)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
    - [Local Environment (Docker Compose)](#local-environment-docker-compose)
    - [Build from Source](#build-from-source)
  - [Configuration](#configuration)
    - [Environment Variables](#environment-variables-1)
    - [OIDC/JWT Authentication](#oidcjwt-authentication)
    - [RBAC Policies](#rbac-policies)
  - [Usage](#usage)
    - [Running Agents](#running-agents)
    - [Loading Documents into RAG](#loading-documents-into-rag)
    - [Tools and Integrations](#tools-and-integrations)
  - [Deployment](#deployment)
    - [Kubernetes (Helm)](#kubernetes-helm)
    - [OpenShift](#openshift)
    - [AWS (Terraform)](#aws-terraform)
    - [Configuration Management Tools](#configuration-management-tools)
    - [mTLS and Istio Service Mesh](#mtls-and-istio-service-mesh)
  - [CI/CD](#cicd)
    - [Jenkins](#jenkins)
    - [GitLab CI](#gitlab-ci)
  - [Monitoring and Observability](#monitoring-and-observability)
    - [Goals](#goals)
    - [Quick Start (Docker Compose)](#quick-start-docker-compose)
    - [Prometheus Configuration](#prometheus-configuration)
    - [Metrics Endpoints Integrations](#metrics-endpoints-integrations)
      - [1) Python FastAPI (Gateway)](#1-python-fastapi-gateway)
      - [2) Java Ticket Adapter (Spring Boot)](#2-java-ticket-adapter-spring-boot)
    - [Grafana (Quick Setup)](#grafana-quick-setup)
    - [Handy Commands (Makefile)](#handy-commands-makefile)
    - [Validation Checklist](#validation-checklist)
  - [Developer Guide](#developer-guide)
    - [1. Basic Environment Setup](#1-basic-environment-setup)
    - [2. How to Run the Application?](#2-how-to-run-the-application)
      - [**Mode A: Full Docker Environment (Recommended)**](#mode-a-full-docker-environment-recommended)
      - [**Mode B: Hybrid Development (for Python work)**](#mode-b-hybrid-development-for-python-work)
    - [3. Testing](#3-testing)
    - [4. Working with Database and RAG](#4-working-with-database-and-rag)
    - [5. Testing the Agents](#5-testing-the-agents)
    - [6. FAQ - Common Issues and Questions](#6-faq---common-issues-and-questions)
  - [Testing](#testing)
  - [Security](#security)
  - [Roadmap](#roadmap)
  - [Contributing](#contributing)
  - [License](#license)
  - [Contact](#contact)

---

## Features

- **AI Agents**: Three ready-to-use agents:
  - **SupportAgent**: User support with RAG over corporate documents (PDF, HTML, Markdown), dialogue memory, and ticketing tools.
  - **OpsAgent**: SRE/DevOps automation — fetches metrics (Prometheus/Grafana), performs operational actions (e.g., restart service) with policies and auditing.
  - **BillingAgent**: Financial operations and billing management with secure integrations.
- **Modular Core**: Python-based framework with tool registry, planner, memory (Redis/Postgres), RAG (pgvector), and event handling (NATS).
- **Integrations**:
  - Java Ticket Adapter (Spring Boot WebFlux + MySQL) for enterprise ticketing systems.
  - Next.js Admin Portal for agent monitoring, audit trails, and prompt testing.
  - **MCP Gateway**: Standardized protocol for AI agent tool interactions with security, audit, and rate limiting.
  - **Domain Packs**: Modular MCP servers for Support, Ops, Finance, and Supply Chain domains with ready-to-use tools.
- **Security**: OIDC/JWT authentication, per-tool RBAC, mTLS via Istio, and full action audit.
- **DevOps Ready**: Docker, Kubernetes (Helm), OpenShift, Terraform (AWS), Ansible/Puppet/Salt, CI/CD with Jenkins and GitLab.
- **Observability**: OpenTelemetry, Prometheus/Grafana/Loki/Tempo stack.
- **Scalability**: HPA in Helm, retries/timeouts in integrations, autoscaling in EKS.

---

## Purpose and Use Cases

**AstraDesk** is a **framework for building AI agents** for **Support** and **SRE/DevOps** teams.
It provides a modular core (planner, memory, RAG, tool registry) and includes ready-to-use agent examples.

- **Support / Helpdesk**: RAG over company documentation (procedures, FAQs, runbooks), ticket creation/update, conversation memory.
- **SRE/DevOps Automation**: Metric retrieval (Prometheus/Grafana), incident triage, and controlled operational actions (e.g., service restart) protected by **RBAC** and audited.
- **Enterprise Integrations**: Gateway (Python/FastAPI), Ticket Adapter (Java/WebFlux + MySQL), Admin Portal (Next.js), MCP Gateway, and data layer (Postgres/pgvector, Redis, NATS).
- **Security and Compliance**: OIDC/JWT, per-tool RBAC, **mTLS** (Istio), and complete audit trails.
- **Scalable Operations**: Docker/Kubernetes/OpenShift, Terraform (AWS), CI/CD (Jenkins/GitLab), observability (OpenTelemetry, Prometheus/Grafana/Loki/Tempo).

> **Not just a chatbot**, but a **framework** for composing your own agents, tools, and policies with full control (no SaaS lock-in).

---

## Architecture Overview

AstraDesk consists of several main components:

- **Python API Gateway**: FastAPI service handling agent requests, RAG, memory, and tools.
- **Java Ticket Adapter**: Reactive WebFlux service integrating with MySQL for ticketing.
- **Next.js Admin Portal**: Web interface for monitoring.
- **MCP Gateway**: Standardized protocol gateway for AI agent tool interactions with security, audit, and rate limiting.

Communication: HTTP (between components), NATS (events/audits), Redis (working memory), Postgres/pgvector (RAG/dialogues/audits), MySQL (tickets).

---

## Admin Portal

```
┌─────────────────────────────────────────────────────────────────┐
│  AstraDesk Admin Portal - Enterprise Dashboard & Governance     │
├─────────────────────────────────────────────────────────────────┤
│  Live Demo: https://astradesk-admin-portal.vercel.app/          │
│  Repository: https://github.com/SSobol77/astradesk-admin-portal │
└─────────────────────────────────────────────────────────────────┘
```

### Overview

**AstraDesk Admin Portal** to enterprise-grade panel administracyjny do zarządzania agentami AI, datasetami, flow, politykami RBAC i governance operacyjnym.

<p align="center">
  <img src="docs/assets/Astradesk_admin.png" alt="AstraDesk Admin Portal Dashboard" width="800"/>
</p>

### Features

| Feature                      | Description                                 |
| ---------------------------- | ------------------------------------------- |
| **🔌 OpenAPI-First**         | Strictly typed from OpenAPI 3.1 spec        |
| **⚡ Next.js 16 + React 19** | Modern App Router architecture              |
| **🔒 Type-Safe**             | Generated TypeScript types from OpenAPI     |
| **📡 Real-Time SSE**         | Live streaming for run updates              |
| **🧪 Mock API Mode**         | Test UI without backend (dev/demo)          |
| **👥 Full RBAC + Audit**     | Role-based access control with audit trails |
| **📊 Intent Graph**          | Visual representation of agent intents      |
| **🔄 Runs & Jobs**           | Live streaming, filters, export             |

### Quick Start

#### Development Mode

```bash
# Clone the admin panel repository
git clone https://github.com/SSobol77/astradesk-admin-portal.git
cd astradesk-admin-portal

# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local

# Run development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

#### Environment Variables

```bash
# Backend API URL (required if not using mock mode)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080/api/admin/v1

# Set to "true" to use realistic mock data instead of real API
NEXT_PUBLIC_MOCK_API=false
```

#### Mock API Mode (Testing Without Backend)

For development, testing, or demos without a running backend:

1. Set `NEXT_PUBLIC_MOCK_API=true` in your `.env.local`
2. The app will use realistic mock data for all endpoints
3. All pages will work with simulated data and network delays
4. Perfect for UI development, testing, and demonstrations

> **Note:** Mock mode returns predefined data from `lib/mock-data.ts`. No actual API calls are made.

### Available Pages

| Page             | Route           | Description                     |
| ---------------- | --------------- | ------------------------------- |
| **Dashboard**    | `/`             | Health, usage, recent errors    |
| **Agents**       | `/agents`       | CRUD, test, promote, metrics    |
| **Intent Graph** | `/intent-graph` | Read-only graph visualization   |
| **Flows**        | `/flows`        | Validate, dry run, logs         |
| **Datasets**     | `/datasets`     | Schema, embeddings, reindex     |
| **Tools**        | `/tools`        | Connector management            |
| **Secrets**      | `/secrets`      | Key rotation, disable           |
| **Runs & Logs**  | `/runs`         | Live streaming, filters, export |
| **Jobs**         | `/jobs`         | Schedules, triggers, DLQ        |
| **RBAC**         | `/rbac`         | Users, roles, invites           |
| **Policies**     | `/policies`     | OPA policy management           |
| **Audit**        | `/audit`        | Immutable audit trail           |
| **Settings**     | `/settings`     | Platform configuration          |

### Authentication

The app uses **Bearer JWT** authentication:

1. Obtain a JWT token from your auth system
2. The app stores it in `localStorage` as `astradesk_token`
3. All API requests include `Authorization: Bearer <token>`

> **In Mock Mode:** Authentication is bypassed - no token required.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Admin Portal (Next.js)                  │
│   ┌─────────────┐  ┌─────────────┐  ┌────────────────────┐  │
│   │   Sidebar   │  │   Topbar    │  │   Main Content     │  │
│   │  Navigation │  │  User/Auth  │  │   Dynamic Pages    │  │
│   └─────────────┘  └─────────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP + SSE
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   API Gateway (FastAPI)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Agents    │  │    Audit    │  │    RBAC/Policies    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer          | Technology                          |
| -------------- | ----------------------------------- |
| **Framework**  | Next.js 16 App Router               |
| **UI Library** | React 19.2, shadcn/ui               |
| **Language**   | TypeScript (generated from OpenAPI) |
| **State**      | React Query, Zustand                |
| **Real-time**  | Server-Sent Events (SSE)            |
| **Styling**    | Tailwind CSS                        |
| **Testing**    | Vitest, Playwright                  |

### Links

| Resource             | URL                                                                                                                    |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| 🌐 **Live Demo**     | [https://astradesk-admin](https://astradesk-admin-portal.vercel.app/)                                                  |
| 🐙 **Repository**    | [https://github.com/SSobol77/astradesk-admin-portal](https://github.com/SSobol77/astradesk-admin-portal)               |
| 📖 **Documentation** | [https://github.com/SSobol77/astradesk-admin-portal#readme](https://github.com/SSobol77/astradesk-admin-portal#readme) |

---

## Prerequisites

- **Docker** and **Docker Compose** (for local dev).
- **Kubernetes** with Helm (for deployment).
- **AWS CLI** and **Terraform** (for cloud setup).
- **Node.js 22**, **JDK 21**, **Python 3.13** (for builds).
- **Postgres 17**, **MySQL 8**, **Redis 7**, **NATS 2** (core services).
- **Optional:** Istio, cert-manager (for mTLS/TLS).

---

## Installation

### Local Environment (Docker Compose)

1. Clone the repository:

```
git clone https://github.com/your-org/astradesk.git
cd astradesk
```

1. Copy the sample configuration:

```
cp .env.example .env
```

- Edit `.env` (e.g. DATABASE_URL, OIDC_ISSUER).

1. Build and start:

```
make up
```

- This starts: API Gateway (8000), MCP Servers (8001-8004), Admin Portal (3000), databases and supporting services.

1. Initialize Postgres (pgvector):

```
make migrate
```

1. Upload documents to `./docs` (e.g. .md, .txt) and initialize RAG:

```
make ingest
```

1. Check health:

```
curl http://localhost:8000/healthz
```

- Admin Portal: <http://localhost:3000>
- MCP Servers: <http://localhost:8001> (support), 8002 (ops), 8003 (finance), 8004 (supply)

### Build from Source

1. Install dependencies:

```
make install-deps  # Python dependencies
make build-java    # Java components
make build-admin   # Next.js Admin Portal
```

1. Run locally (without Docker):

- API Gateway: `make dev-server` (with hot reload)
- MCP Servers: `make mcp-all` (starts all domain pack servers)
- Admin Portal: `cd services/admin-portal && npm run dev`

1. Alternative development setup:

```
# Automated setup (recommended)
./scripts/setup-dev-environment.sh

# Or manual setup
make setup
```

---

## Configuration

### Environment Variables

- **DATABASE_URL**: PostgreSQL connection string (e.g. `postgresql://user:pass@host:5432/db`).
- **REDIS_URL**: Redis URI (e.g. `redis://host:6379/0`).
- **NATS_URL**: NATS server (e.g. `nats://host:4222`).
- **TICKETS_BASE_URL**: URL to Java adapter (e.g. `http://ticket-adapter:8081`).
- **MYSQL_URL**: MySQL JDBC (e.g. `jdbc:mysql://host:3306/db?useSSL=false`).
- **ENVIRONMENT**: deployment tier. Defaults to `production` when unset — the safe default is deployed-tier behavior. `production`/`prod`/`staging`/`stage` are deployed tiers; anything else (e.g. `dev`, `test`, `local`, `ci`) is non-deployed.
- **AUTH_MODE**: selects the API Gateway's ingress token verifier (ISSUE 009). Defaults to `production` (JWKS/RS256). `local-dev` is the sole named, non-default local convenience and is refused at startup (`AuthConfigError`) on a deployed tier.
- **OIDC_ISSUER**: OIDC issuer (e.g. `https://your-issuer.com/`). **Required** in `AUTH_MODE=production`.
- **OIDC_AUDIENCE**: JWT audience. **Required** in `AUTH_MODE=production`.
- **OIDC_JWKS_URL**: JWKS URL (e.g. `https://your-issuer.com/.well-known/jwks.json`). **Required** in `AUTH_MODE=production`.
- **ASTRADESK_DEV_JWT_SECRET**: HS256 secret for `AUTH_MODE=local-dev` only; never read or usable on a deployed tier.
- **AUDIT_MODE**: selects the durable side-effect tool audit sink (ISSUE 019/039). Defaults to `jsonl` (append-only JSON-Lines file at `AUDIT_LOG_PATH`) — **required** on a deployed tier (`production`/`prod`/`staging`/`stage`, the default when `ENVIRONMENT` is unset): the gateway refuses to start without it (`AuditConfigError`). Outside a deployed tier, leaving `AUDIT_LOG_PATH` unset falls back to a non-durable in-process writer with a startup warning. `AUDIT_MODE=jetstream` is an explicit, non-default opt-in to a NATS JetStream-backed durable sink: a side-effecting tool call is reported successful only after the audit event is broker-acknowledged, and fails closed (on every tier) if JetStream is unreachable or does not acknowledge within `AUDIT_PUBLISH_TIMEOUT_MS`. See `.env.example` for `AUDIT_NATS_URL`/`AUDIT_JETSTREAM_STREAM`/`AUDIT_JETSTREAM_SUBJECT`/`AUDIT_JETSTREAM_DLQ_SUBJECT` and the matching Auditor Service consumer settings, and `audit/evidence/39_jetstream_durable_audit.md` for the full implementation record.
- **AUDIT_LOG_PATH**: append-only JSON-Lines path used by `AUDIT_MODE=jsonl` (see above).

Full list in `.env.example`.

> **Note:** Missing Redis/Postgres configuration does not crash the service at import or
> startup. Provider misconfiguration is deferred to first use, so the app (and the test
> suite) can be collected and started without `DATABASE_URL`/`REDIS_URL` set; the error
> surfaces only when that backend is actually exercised.

### OIDC/JWT Authentication

- API Gateway ingress (`POST /v1/run`) requires `Authorization: Bearer <token>`, verified by `astradesk_core.utils.oidc` via `gateway.auth_dependency.install_verifier()`, wired at lifespan startup before DB/Redis/RAG initialization (ISSUE 009).
- Validation: signature via JWKS, `iss`, `aud`, `exp`, `nbf` (when present), algorithm allow-list (`OIDC_ALGORITHMS`, default `RS256`), and `kid` resolution with one forced JWKS refresh on a signing-key miss (rotation without restart).
- On a deployed tier (`ENVIRONMENT` ∈ `production`/`prod`/`staging`/`stage`; defaults to `production` when unset) missing `OIDC_ISSUER`/`OIDC_AUDIENCE`/`OIDC_JWKS_URL` aborts startup (`AuthConfigError`) — no fallback to a weaker verifier.
- `AUTH_MODE=local-dev` (symmetric HS256, keyed by `ASTRADESK_DEV_JWT_SECRET`) is the only local/dev/test/CI convenience; it is a named, non-default mode and is refused at startup on a deployed tier.
- Verified claims are normalized into a `Principal` (`subject`, `roles`, `scopes`, `claims`) before reaching RBAC (ISSUE 016) — the choke point never inspects raw IdP-specific claim shapes.
- **Admin Portal front-channel OIDC (ISSUE 021)**: `services/admin-portal` implements its own browser-side sign-in using a dependency-free Authorization Code + PKCE flow against any OIDC-compliant provider (Auth0, Keycloak, Okta, ...), configured via `NEXT_PUBLIC_OIDC_ISSUER`/`NEXT_PUBLIC_OIDC_CLIENT_ID`/`NEXT_PUBLIC_OIDC_AUDIENCE`/`NEXT_PUBLIC_OIDC_REDIRECT_URI`. Every page under the protected shell requires a session (or `NEXT_PUBLIC_SIMULATION_MODE=true` for a backend-less demo); an unconfigured deployment fails closed to `/login` rather than serving the console unauthenticated. The signed-in user's access token is attached as `Authorization: Bearer <token>` to client-side Admin API calls. See `services/admin-portal/README.md`'s "Authentication" section for setup and `services/admin-portal/lib/auth/` for the implementation.

### RBAC Policies

- Roles from JWT claims (e.g. `"roles": ["sre"]`).
- Tools (e.g. restart_service) validate via `require_role(claims, "sre")`.
- Customize in `runtime/policy.py` and tool definitions (e.g. `REQUIRED_ROLE_RESTART`).

---

## Usage

### Running Agents

Call the API:

```sh
curl -X POST http://localhost:8080/v1/agents/run \
-H "Content-Type: application/json" \
-H "Authorization: Bearer <your-jwt-token>" \
-d '{"agent": "support", "input": "Create a ticket for a network incident", "meta": {"user": "alice"}}'
```

- Response: JSON with output, reasoning_trace_id, invoked_tools.
- Available agents: `support`, `ops`, `billing`
- Demo queries: `./scripts/demo_queries.sh`.

### Loading Documents into RAG

- Supported formats: .md, .txt (extendable to PDF/HTML).
- Run: `make ingest` (source: `./docs`).

### Tools and Integrations

- Tool registry: `registry.py` — add new ones via `register(name, async_fn)`.
- Examples: create_ticket (proxy to Java), get_metrics (Prometheus stub), restart_service (RBAC-protected).
- **MCP Gateway**: Standardized protocol for AI agent tool interactions with built-in security, audit, and rate limiting. See [MCP documentation](mcp/README.md) for implementation details.

---

## Deployment

### Kubernetes (Helm)

1. Build and push images (use CI).
2. Install chart:

   ```sh
   helm upgrade --install astradesk deploy/chart -f deploy/chart/values.yaml \
     --set image.tag=0.3.0 \
     --set autoscaling.enabled=true
   ```

   - HPA: scales when CPU >60%.

### OpenShift

1. Process template:

```sh
oc process -f deploy/openshift/astradesk-template.yaml -p TAG=0.3.0 | oc apply -f -
```

### AWS (Terraform)

1. Initialize:

   ```sh
   cd deploy/infra
   terraform init
   terraform apply -var="region=us-east-1" -var="project=astradesk"
   ```

   - Creates: VPC, EKS, RDS (Postgres/MySQL), S3.

### Configuration Management Tools

- **Ansible**: `ansible-playbook -i ansible/inventories/dev/hosts.ini ansible/roles/astradesk_docker/main.yml`.
- **Puppet**: `puppet apply puppet/manifests/astradesk.pp`.
- **Salt**: `salt '*' state.apply astradesk`.

### mTLS and Istio Service Mesh

1. Namespace: `astradesk-prod` is created by Helm (`--create-namespace`), not a separate manifest — see `deploy/chart/deploy_chart_README.md`.
2. Enable mTLS: `kubectl apply -f deploy/istio/` (applies `peerauthentication.yaml`, `gateway.yaml`, `virtualservice.yaml`, `certmanager.yaml` — the canonical, `astradesk-prod` generation; see `audit/evidence/43_deployability_verification.md` for the superseded second generation kept for reference under `deploy/istio/generation-b-reference/`).
3. Gateway: HTTPS on port 443 with cert-manager.

## CI/CD

### Jenkins

- Run pipeline: `Jenkinsfile` builds/tests/pushes images, deploys via Helm.

### GitLab CI

- `.gitlab-ci.yml`: stages for build/test/docker/deploy (manual).

<br>

---

## Monitoring and Observability

**(Prometheus, Grafana, OpenTelemetry)**

This section explains how to enable full observability for the AstraDesk platform using **Prometheus** (metrics), **Grafana** (dashboards), and **OpenTelemetry** (instrumentation).

### Goals

- Collect metrics from the **Python API Gateway** (`/metrics`) and the **Java Ticket Adapter** (`/actuator/prometheus`).
- Get a quick health view in **Grafana**.
- Alerting (e.g., high 5xx error rate) in Prometheus.

---

### Quick Start (Docker Compose)

Below is a minimal snippet to add Prometheus + Grafana services to `docker-compose.yml`.

> **Note:** We assume `api` and `ticket-adapter` services run with: `api:8080`, `ticket-adapter:8081`.

```yaml
services:
  # --- Observability stack ---
  prometheus:
    image: prom/prometheus:latest
    container_name: astradesk-prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--web.enable-lifecycle" # allows hot-reload of the config
    volumes:
      - ./dev/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    restart: unless-stopped
    depends_on:
      - api
      - ticket-adapter

  grafana:
    image: grafana/grafana:latest
    container_name: astradesk-grafana
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_DEFAULT_THEME=dark
    volumes:
      - grafana-data:/var/lib/grafana
      # (optional) automatic provisioning for data sources / dashboards:
      # - ./dev/grafana/provisioning:/etc/grafana/provisioning:ro
    ports:
      - "3000:3000"
    restart: unless-stopped
    depends_on:
      - prometheus

volumes:
  prometheus-data:
  grafana-data:
```

<br>

### Prometheus Configuration

`dev/prometheus/prometheus.yml`

Create `dev/prometheus/prometheus.yml` with the following content:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  scrape_timeout: 10s
  # optional: external_labels: { env: "dev" }

scrape_configs:
  # FastAPI Gateway (Python)
  - job_name: "api"
    metrics_path: /metrics
    static_configs:
      - targets: ["api:8080"]

  # Java Ticket Adapter (Spring Boot + Micrometer)
  - job_name: "ticket-adapter"
    metrics_path: /actuator/prometheus
    static_configs:
      - targets: ["ticket-adapter:8081"]

  # (optional) NATS Exporter
  # - job_name: "nats"
  #   static_configs:
  #     - targets: ["nats-exporter:7777"]

rule_files:
  - /etc/prometheus/alerts.yml
```

_(Optional) Add `dev/prometheus/alerts.yml` and mount it similarly into the container (e.g., via an extra volume or fold it into `prometheus.yml`)._

<br>

Sample alert rules:

```yaml
groups:
  - name: astradesk-alerts
    rules:
      - alert: HighErrorRate_API
        expr: |
          rate(http_requests_total{job="api",status=~"5.."}[5m])
          /
          rate(http_requests_total{job="api"}[5m]) > 0.05
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "API high 5xx error rate (>5% for 10m)"
          description: "Investigate FastAPI gateway logs and upstream dependencies."

      - alert: TicketAdapterDown
        expr: up{job="ticket-adapter"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Ticket Adapter is down"
          description: "Spring service not responding on /actuator/prometheus."
```

> **Reload configuration** without restart:
>
> `curl -X POST http://localhost:9090/-/reload`

<br>

### Metrics Endpoints Integrations

#### 1) Python FastAPI (Gateway)

The simplest way to expose `/metrics` is with `prometheus_client`:

```python
# src/gateway/observability.py
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from fastapi import APIRouter, Request
import time

router = APIRouter()

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"]
)

@router.get("/metrics")
def metrics():
    # Expose Prometheus metrics in plaintext format
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# (optional) simple middleware for latency and counts
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    path = request.url.path
    method = request.method
    REQUEST_LATENCY.labels(method=method, path=path).observe(elapsed)
    REQUEST_COUNT.labels(method=method, path=path, status=str(response.status_code)).inc()
    return response
```

Register in `main.py`:

```python
from fastapi import FastAPI
from src.gateway.observability import router as metrics_router, metrics_middleware

app = FastAPI()
app.middleware("http")(metrics_middleware)
app.include_router(metrics_router, tags=["observability"])
```

> **Alternative (recommended):** use **OpenTelemetry** + an `otlp` exporter, then scrape metrics via **otel-collector** → Prometheus. This gives you unified metrics, traces, and logs.

<br>

#### 2) Java Ticket Adapter (Spring Boot)

`application.yml`:

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health, prometheus
  endpoint:
    prometheus:
      enabled: true
  metrics:
    tags:
      application: astradesk-ticket-adapter
  observations:
    key-values:
      env: dev
```

Micrometer Prometheus dependency:

```xml
<!-- pom.xml -->
<dependency>
  <groupId>io.micrometer</groupId>
  <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>
```

After startup, the endpoint is available at:
`http://localhost:8081/actuator/prometheus` (or `ticket-adapter:8081` in Docker).

<br>

### Grafana (Quick Setup)

After Grafana starts ([http://localhost:3000](http://localhost:3000), default `admin`/`admin`):

1. **Add data source → Prometheus**
   URL: `http://prometheus:9090` (inside Docker Compose network) or `http://localhost:9090` (if adding from your host).
2. **Import a dashboard** (e.g., “Prometheus / Overview” or your custom one).
   You can also keep descriptors in the repo (`grafana/dashboard-astradesk.json`) and enable provisioning:

   ```
   dev/grafana/provisioning/datasources/prometheus.yaml
   dev/grafana/provisioning/dashboards/dashboards.yaml
   grafana/dashboard-astradesk.json
   ```

Example data source (provisioning):

```yaml
# dev/grafana/provisioning/datasources/prometheus.yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

Example dashboards provider:

```yaml
# dev/grafana/provisioning/dashboards/dashboards.yaml
apiVersion: 1
providers:
  - name: "AstraDesk"
    orgId: 1
    folder: "AstraDesk"
    type: file
    options:
      path: /var/lib/grafana/dashboards
```

<br>

### Handy Commands (Makefile)

Add these shortcuts to `Makefile` to speed up your workflow:

```Makefile
.PHONY: up-observability down-observability logs-prometheus logs-grafana

up-observability:
\tdocker compose up -d prometheus grafana

down-observability:
\tdocker compose rm -sfv prometheus grafana

logs-prometheus:
\tdocker logs -f astradesk-prometheus

logs-grafana:
\tdocker logs -f astradesk-grafana
```

<br>

### Validation Checklist

- Prometheus UI: **[http://localhost:9090](http://localhost:9090)**
  - Check that `api` and `ticket-adapter` jobs are **UP** (Status → Targets).

- Grafana UI: **[http://localhost:3000](http://localhost:3000)**
  - Connect the Prometheus data source, import a dashboard, and watch key metrics (latency, request count, 5xx errors).

- Quick test:

  ```bash
  curl -s http://localhost:8080/metrics | head
  curl -s http://localhost:8081/actuator/prometheus | head
  ```

> If the endpoints don’t return metrics, make sure:
>
> 1. the paths (`/metrics`, `/actuator/prometheus`) are enabled,
> 2. services are reachable by the Compose network names `api` / `ticket-adapter`,
> 3. `prometheus.yml` points at the correct `targets`.

<br>

---

## Developer Guide

This section provides practical instructions and answers to common questions to help you start working with the project quickly.

### 1. Basic Environment Setup

Before starting, ensure you have:

- **Docker** and **Docker Compose** (Docker Desktop recommended).
- **Git**, **make**, and **Node.js** (v22+) installed locally.

Preparation steps (run once):

1. **Clone the repository**:

   ```bash
   git clone https://github.com/your-org/astradesk.git
   cd astradesk
   ```

2. **Copy configuration file**:

   ```bash
   cp .env.example .env
   ```

3. **Generate `package-lock.json`**: Required for building the Admin Portal Docker image.

   ```bash
   cd services/admin-portal && npm install && cd ../..
   ```

### 2. How to Run the Application?

You can choose between two modes depending on your needs.

#### **Mode A: Full Docker Environment (Recommended)**

Runs **the entire application** (all microservices) inside Docker containers. Ideal for integration testing and production-like environments.

- **To start:**

  ```bash
  make up
  ```

  _(Alternatively: `docker compose up --build -d`)_

- **To stop and clean up:**

  ```bash
  make down
  ```

  _(Alternatively: `docker compose down -v`)_

- **Available services:**
  - **API Gateway**: `http://localhost:8080`
  - **Admin Portal**: `http://localhost:3000`
  - **Ticket Adapter**: `http://localhost:8081`

<br>

#### **Mode B: Hybrid Development (for Python work)**

Runs **only external dependencies** (databases, NATS, etc.) in Docker, while the main **Python API runs locally**.
Ideal for fast development and debugging with instant reloads.

1. **Step 1: Start dependencies in Docker** (in one terminal):

   ```bash
   make up-deps
   ```

   _(Alternatively: `docker compose up -d db mysql redis nats ticket-adapter`)_

2. **Step 2: Run the API locally** (in another terminal):

   ```bash
   make run-local
   ```

   _(Alternatively: `python -m uvicorn src.gateway.main:app --host 0.0.0.0 --port 8080 --reload --app-dir src`)_

### 3. Testing

`Makefile` provides simple commands for running tests.

- **Run all tests:**

  ```bash
  make test-all
  ```

- **Python tests only:**

  ```bash
  make test
  ```

- **Java tests only:**

  ```bash
  make test-java
  ```

- **Admin Portal tests only:**

  ```bash
  make test-admin
  ```

### 4. Working with Database and RAG

- **Initialize database (create `pgvector` extension):**
  _Note: not needed if using `docker-compose.dev.yml`._

  ```bash
  make migrate
  ```

- **Feed the RAG knowledge base:**
  1. Add your `.md` or `.txt` files to `docs/`.
  2. Run:

     ```bash
     make ingest
     ```

### 5. Testing the Agents

Once the app is running (in any mode), you can send requests to the API using `curl`.

_Note: The following assumes the authorization guard (`auth_guard`) in `main.py` is temporarily disabled for testing._

- **Test `create_ticket` tool:**

  ```bash
  curl -X POST http://localhost:8080/v1/agents/run \
    -H "Content-Type: application/json" \
    -d '{"agent": "support", "input": "My internet is down, please create a ticket."}'
  ```

- **Test `get_metrics` tool:**

  ```bash
  curl -X POST http://localhost:8080/v1/agents/run \
    -H "Content-Type: application/json" \
    -d '{"agent": "ops", "input": "Show me metrics for the webapp service"}'
  ```

- **Test RAG (knowledge base):**

  ```bash
  curl -X POST http://localhost:8080/v1/agents/run \
    -H "Content-Type: application/json" \
    -d '{"agent": "support", "input": "How can I reset my password?"}'
  ```

### 6. FAQ - Common Issues and Questions

- **Q: I get `Connection refused` on startup.**
  - **A:** Most likely the API server (`make run-local`) starts before dependent containers are ready.
    Ensure `docker ps` shows `(healthy)` for `db`, `mysql`, and `redis` before starting Python.

- **Q: I get `{"detail":"Missing Bearer authorization header."}`.**
  - **A:** That means `auth_guard` in `src/gateway/main.py` is enabled.
    For local

testing, comment out `claims: dict[str, Any] = Depends(auth_guard),` in the `run_agent` endpoint definition and pass `{}` as `claims` to `orchestrator.run`.

- **Q: How do I view logs for a specific service?**
  - **A:** Use `docker logs`. For example, to follow Auditor logs live:

    ```bash
    docker logs -f astradesk-auditor-1
    ```

    _(Container name may vary — check with `docker ps`.)_

- **Q: How do I rebuild a single Docker image?**
  - **A:** Use the `--build` flag:

    ```bash
    docker compose up -d --build api
    ```

- **Q: Where can I modify `KeywordPlanner` keywords?**
  - **A:** In `src/runtime/planner.py`, inside the `__init__` method of `KeywordPlanner`.

<br>

## Testing

- Run: `make test` (Python), `make test-java`, `make test-admin`.
- Coverage: Unit (pytest, JUnit, Vitest), integration (API flow).

### Integration test gate (issue #18)

`tests/integration_tests.py` drives the full Gateway → Agent → Tool → RAG
flow (in-process FastAPI `app` via `TestClient`, real local-dev JWTs) plus
HTTP connectivity checks against the 4 domain-pack MCP servers. It is
wired as an explicit, required, always-run job
(`integration-tests` in `.github/workflows/ci.yml`) — not part of the
default `pytest -q` unit gate.

Required backing services (`docker-compose.dev.yml`):

```bash
docker compose -f docker-compose.dev.yml up -d --wait --wait-timeout 180 \
  postgres redis nats mcp-support mcp-ops mcp-finance mcp-supply
```

Exact gate command:

```bash
DATABASE_URL=postgresql://astradesk:astradesk@localhost:5432/astradesk \
REDIS_URL=redis://localhost:6379/0 \
NATS_URL=nats://localhost:4222 \
AUTH_MODE=local-dev \
ASTRADESK_DEV_JWT_SECRET=integration-test-secret \
ENVIRONMENT=ci \
uv run pytest -q -m integration tests/integration_tests.py
```

Expected result: **`5 passed`** — no `xfail`, no `skip`, no optional/
best-effort MCP server path (all 4 must become healthy or the CI step
itself fails). See `audit/evidence/18_integration_ci_gate.md` for the
root-cause history and `audit/evidence/v0.3.0_final_validation.md` for the
latest reproduction.

### Coverage reports

Each stack emits a machine-readable coverage report that CI uploads as an artifact:

- **Python** — `uv run pytest --cov=core/src --cov=services/api-gateway/src --cov=packages --cov-report=xml` → `coverage.xml`.
- **Java** — `./gradlew test jacocoTestReport` (from `services/ticket-adapter-java/`) → `build/reports/jacoco/test/jacocoTestReport.xml`.
- **JS** — `vitest run --coverage` (via `@vitest/coverage-v8`, from `services/admin-portal/`) → `coverage/lcov.info`.

## Versioning

AstraDesk tracks two independent version axes — do not conflate them:

| Axis | Value | Source of truth |
| :--- | :--- | :--- |
| **Product / package** | `0.3.0` | `pyproject.toml`, Gradle, Sonar (`SONAR_PROJECT_VERSION`) |
| **Admin API contract** | `1.2.0` | `info.version` in `openapi/astradesk-admin.v1.yaml` |

The Admin API spec is named `astradesk-admin.v1.yaml`, where `v1` encodes the API **MAJOR**
version; the full contract version is the semver `1.2.0` carried in `info.version`. The same
`1.2.0` is stamped on the `FastAPI(version=...)` app in `services/admin_api` and shown in the
docs API reference. `scripts/check-openapi-version.sh` enforces that the spec stays at
`openapi: 3.1.0` / `info.version: "1.2.0"`, and `services/admin-portal/OpenAPI.yaml` is a
symlink to the canonical spec so the UI never drifts.

### Naming conventions

- **Service & domain-pack directories are hyphenated**: `services/api-gateway`,
  `services/ticket-adapter-java`, `services/admin-portal`, `packages/domain-*`.
- **Python import-root packages use underscores** where the directory is itself an import
  package: `services/admin_api`, `core/src/astradesk_core`. These are import/build-significant
  and are **not** renamed to match the hyphen style — always refer to a source tree by its
  real path (e.g. `services/api-gateway/src`).
- **Localized docs** use one canonical directory per language: `docs/en`, `docs/pl`, `docs/zh-CN`.
- **Compose files**: `docker-compose.yml` (full local stack) and `docker-compose.dev.yml`
  (developer stack with migrations auto-applied).

## Security

- **Auth**: OIDC/JWT with JWKS.
- **RBAC**: Per tool, based on claims.
- **mTLS**: STRICT via Istio.
- **Audit**: Logged to Postgres + NATS publish. Every `write`/`execute` tool attempt (allowed, denied, or errored) is additionally recorded through a durable `AuditWriter` at the `ToolRegistry.execute` choke point, on both the LLM-planned and keyword-fallback paths. Deployed tiers (`production`/`prod`/`staging`/`stage`) fail closed at startup without `AUDIT_LOG_PATH`; local/dev/test may fall back to a non-durable in-process writer. `AUDIT_MODE=jetstream` (ISSUE 039) swaps the sink for a NATS JetStream durable consumer: the Gateway blocks a side-effecting tool call on JetStream's own broker ack (not on the slower downstream Elasticsearch/S3 write), and the standalone Auditor service acks each JetStream batch only after both sinks durably persist it, with bounded retry, DLQ routing on exhaustion, and idempotent sink keys — see `audit/evidence/39_jetstream_durable_audit.md`.
- **Policy (OPA, fail-closed)**: A contextual policy gate, independent of RBAC, additionally guards every `write`/`execute` tool attempt (and any `read` tool opted in with `policy_governed=True`) at the same `ToolRegistry.execute` choke point (`runtime.policy_enforcer`, ISSUE 028). Deployed tiers require a real OPA server (`POLICY_MODE=opa` or the safe default) — missing/invalid `OPA_URL` aborts startup, and a denied or unreachable OPA decision at call time denies the tool before it runs. `POLICY_MODE=local` (deterministic allow-all) is refused on deployed tiers. Policy denials are durably audited through the same ISSUE 019 path. Schema-hash negotiation and OPA bundle versioning remain future work (Track B).
- **Policies**: Allow-lists in tools, proxy retries.
- **Admin API defense-in-depth (NEW-SEC)**: `/api/admin/v1/{path}` requires an
  authenticated `admin` principal at the API Gateway proxy **before** forwarding, and
  the Admin API (`services/admin_api`) independently re-verifies the same Bearer JWT
  and independently requires `admin` — neither layer trusts the other's decision or
  network placement alone. Part of the security baseline alongside the OIDC/RBAC/audit/
  policy hardening above; see [docs/en/08_security_governance.md §8.13](docs/en/08_security_governance.md#813-admin-api-defense-in-depth-new-sec).

## Roadmap

- LLM integration (Bedrock/OpenAI/vLLM) with guardrails.
- Temporal for long-running workflows.
- RAG evaluations (Ragas).
- Advanced multi-tenancy.
- OPA policy-bundle supply chain: schema-hash negotiation and bundle versioning (see `docs/roadmap/issues/ISSUES_028_opa_fail_closed.md`).
- Full Grafana dashboards with alerts.

## Contributing

- Fork the repo, create a branch, and submit a PR with tests.
- Run `make lint/type` before committing.

## License

GNU General Public License version 2 only. See [LICENSE](LICENSE) for details.

## Contact

🌐 Website: [AstraDesk](https://astradesk.dev/)

✨ Demo: [AstraDesk Admin Portal](https://astradesk-admin-portal.vercel.app/)

📧 Author: Siergej Sobolewski [s.sobolewski@hotmail.com](mailto:s.sobolewski@hotmail.com)

💬 Support channel: [Support Slack](https://astradesk.slack.com)

🐙 Issues: [GitHub Issues](https://github.com/SSobol77/astradesk/issues)

<br>

---

_Last updated: 2026-04-09_
