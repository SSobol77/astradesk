<p align="center">
  <img src="assets/AstraDesktop.png" alt="AstraDesk - AI Framework" width="560"/>
</p>

<br>

# AstraDesk Duo - Internal AI Agents Framework

[![License](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Python Version](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![JDK Version](https://img.shields.io/badge/JDK-21-green.svg)](https://openjdk.org/projects/jdk/21/)
[![Node.js Version](https://img.shields.io/badge/Node.js-22-brightgreen.svg)](https://nodejs.org/en)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](https://github.com/your-org/astradesk/actions)

<!-- Replace with the real CI link -->
<!-- Language: EN | PL -->
**Languages:** [English](README.md) | [Polski](README.pl.md)

<br>

[AstraDesk](https://v0-site-creation-pi.vercel.app/)
 is an internal framework for building AI agents, designed for Support and SRE/DevOps teams. It offers a modular architecture with ready-to-use demo agents, integrations with databases, messaging systems, and DevOps tools. The framework supports scalability, enterprise-grade security (OIDC/JWT, RBAC, mTLS via Istio), and end-to-end CI/CD.

## Table of Contents

- [Features](#features)
- [Purpose & Use Cases](#purpose--use-cases)
- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Local Development with Docker Compose](#local-development-with-docker-compose)
  - [Building from Source](#building-from-source)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [OIDC/JWT Authentication](#oidcjwt-authentication)
  - [RBAC Policies](#rbac-policies)
- [Usage](#usage)
  - [Running Agents](#running-agents)
  - [Ingesting Documents for RAG](#ingesting-documents-for-rag)
  - [Admin Portal](#admin-portal)
  - [Tools and Integrations](#tools-and-integrations)
- [Deployment](#deployment)
  - [Kubernetes with Helm](#kubernetes-with-helm)
  - [OpenShift](#openshift)
  - [AWS with Terraform](#aws-with-terraform)
  - [Configuration Management Tools](#configuration-management-tools)
  - [mTLS and Istio Service Mesh](#mtls-and-istio-service-mesh)
- [CI/CD](#cicd)
  - [Jenkins](#jenkins)
  - [GitLab CI](#gitlab-ci)
- [Monitoring and Observability](#monitoring-and-observability)
  - [OpenTelemetry](#opentelemetry)
  - [Grafana Dashboards and Alerts](#grafana-dashboards-and-alerts)
- [Developer's Guide](#developers-guide)
- [Testing](#testing)
- [Security](#security)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

<br>

## Features

- **AI Agents**: Two ready-made agents:
  - **SupportAgent**: User support with RAG on company documents (PDF, HTML, Markdown), conversational memory, and ticketing tools.
  - **OpsAgent**: SRE/DevOps automations — fetch metrics (from Prometheus/Grafana), perform operational actions (e.g., service restart) with policies and audit trail.
- **Modular Core**: Python-based framework with a tool registry, planner, memory (Redis/Postgres), RAG (pgvector), and events (NATS).
- **Integrations**:
  - Java Ticket Adapter (Spring Boot WebFlux + MySQL) for enterprise ticketing systems.
  - Next.js Admin Portal for monitoring agents, audits, and prompt testing.
- **Security**: OIDC/JWT auth, per-tool RBAC, mTLS via Istio, action auditing.
- **DevOps Ready**: Docker, Kubernetes (Helm), OpenShift, Terraform (AWS), Ansible/Puppet/Salt, CI/CD (Jenkins/GitLab).
- **Observability**: OpenTelemetry, Prometheus/Grafana/Loki/Tempo.
- **Scalability**: HPA in Helm, retries/timeouts in integrations, autoscaling on EKS.

<br>

## Purpose & Use Cases

**AstraDesk** is an internal **AI agents framework** for Support and SRE/DevOps teams.
It provides a modular core (planner, memory, RAG, tool registry) and ready-to-run demo agents.
Typical applications include:

- **Support / Helpdesk**: RAG on company documents (procedures, FAQs, runbooks), ticket creation/update, and conversational memory.

- **SRE/DevOps Automation**: Metrics lookups (Prometheus/Grafana), incident triage, and controlled actions (e.g., service restart) protected by **RBAC** and auditable.

- **Enterprise Integrations**: Gateway (Python/FastAPI), Ticket Adapter (Java/WebFlux + MySQL), Admin Portal (Next.js), and data plane (Postgres/pgvector, Redis, NATS).

- **Security & Compliance**: OIDC/JWT, per-tool RBAC, **mTLS** (Istio), audit trails.

- **Operations at Scale**: Docker/Kubernetes/OpenShift, Terraform (AWS), CI/CD (Jenkins/GitLab), observability (OpenTelemetry, Prometheus/Grafana/Loki/Tempo).

> **Not a single chatbot** - it’s a **framework** to compose your own agents, tools, and policies with full control (no SaaS lock‑in).

<br>

## Architecture Overview

AstraDesk consists of three primary components:

- **Python API Gateway**: FastAPI handling agent requests with RAG, memory, and tools.

- **Java Ticket Adapter**: Reactive service (WebFlux) integrating with MySQL for ticketing.

- **Next.js Admin Portal**: Web UI for monitoring.

Communication: HTTP (between components), NATS (events/audit), Redis (working memory), Postgres/pgvector (RAG/dialogs/audit), MySQL (tickets).

<br>

## Prerequisites

- **Docker** and **Docker Compose** (for local development).

- **Kubernetes** with Helm (for deployment).

- **AWS CLI** and **Terraform** (for cloud).

- **Node.js 22**, **JDK 21**, **Python 3.11** (for builds).

- **Postgres 16**, **MySQL 8**, **Redis 7**, **NATS 2** (base services).

- **Optional:** Istio, cert-manager (for mTLS/TLS).

<br>

## Installation

### Local Development with Docker Compose

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/astradesk.git
   cd astradesk
   ```

2. Copy the example configuration:
   ```bash
   cp .env.example .env
   ```
   - Edit `.env` (e.g., DATABASE_URL, OIDC_ISSUER).

3. Build and run:
   ```bash
   make up
   ```
   - This starts: API (8080), Ticket Adapter (8081), Admin Portal (3000), databases and services.

4. Initialize Postgres (pgvector):
   ```bash
   make migrate
   ```

5. Drop documents into `./docs` (e.g., .md, .txt) and initialize RAG:
   ```bash
   make ingest
   ```

6. Health check:
   ```bash
   curl http://localhost:8080/healthz
   ```
   - Admin Portal: http://localhost:3000

### Building from Source

1. Install dependencies:
   ```bash
   make sync          # Python
   make build-java    # Java
   make build-admin   # Next.js
   ```

2. Run locally (without Docker):
   - Python API: `uv run uvicorn gateway.main:app --host 0.0.0.0 --port 8080 --reload`
   - Java Adapter: `cd services/ticket-adapter-java && ./gradlew bootRun`
   - Admin Portal: `cd services/admin-portal && npm run dev`

<br>

## Configuration

### Environment Variables

- **DATABASE_URL**: PostgreSQL connection string (e.g., `postgresql://user:pass@host:5432/db`).

- **REDIS_URL**: Redis URI (e.g., `redis://host:6379/0`).

- **NATS_URL**: NATS server (e.g., `nats://host:4222`).

- **TICKETS_BASE_URL**: URL of the Java adapter (e.g., `http://ticket-adapter:8081`).

- **MYSQL_URL**: MySQL JDBC (e.g., `jdbc:mysql://host:3306/db?useSSL=false`).

- **OIDC_ISSUER**: OIDC issuer (e.g., `https://your-issuer.com/`).

- **OIDC_AUDIENCE**: JWT audience.

- **OIDC_JWKS_URL**: JWKS URL (e.g., `https://your-issuer.com/.well-known/jwks.json`).

See `.env.example` for the full list.

### OIDC/JWT Authentication

- Enabled in API Gateway and Java Adapter.

- Use a Bearer token in requests: `Authorization: Bearer <token>`.

- Validation: issuer, audience, signature via JWKS.

- In Admin Portal: Use Auth0 or a similar provider for the front-channel flow.

### RBAC Policies

- Roles are read from JWT claims (e.g., `"roles": ["sre"]`).

- Tools (e.g., `restart_service`) check roles via `require_role(claims, "sre")`.

- Adjust in `runtime/policy.py` and in tools (e.g., `REQUIRED_ROLE_RESTART`).

<br>

## Usage

### Running Agents

Call the API:

```sh
curl -X POST http://localhost:8080/v1/agents/run   -H "Content-Type: application/json"   -H "Authorization: Bearer <your-jwt-token>"   -d '{"agent": "support", "input": "Create a ticket for a network incident", "meta": {"user": "alice"}}'
```

- Response: JSON with output, `trace_id`, `used_tools`.
- Demo queries: `./scripts/demo_queries.sh`.

### Ingesting Documents for RAG

- Supported formats: `.md`, `.txt` (extendable to PDF/HTML).
- Run: `make ingest` (source: `./docs`).

### Admin Portal

- Available at `http://localhost:3000`.
- Features: API health check, sample curl calls to agents.
- To extend with audit fetching: add endpoint `/v1/audits` in the API.

### Tools and Integrations

- Tool registry: `registry.py` — add new tools via `register(name, async_fn)`.
- Examples: `create_ticket` (proxy to Java), `get_metrics` (Prometheus stub), `restart_service` (with RBAC).

<br>

## Deployment

### Kubernetes with Helm

1. Build and push container images (use CI).

2. Install the chart:

   ```sh
   helm upgrade --install astradesk deploy/chart -f deploy/chart/values.yaml      --set image.tag=0.2.1      --set autoscaling.enabled=true
   ```

   - HPA: Scales when CPU > 60%.

### OpenShift

1. Process the template:

   ```sh
   oc process -f deploy/openshift/astradesk-template.yaml -p TAG=0.2.1 | oc apply -f -
   ```

### AWS with Terraform

1. Initialize:

   ```sh
   cd infra
   terraform init
   terraform apply -var="region=us-east-1" -var="project=astradesk"
   ```

   - Provisions: VPC, EKS, RDS (Postgres/MySQL), S3.

### Configuration Management Tools

- **Ansible**: `ansible-playbook -i ansible/inventories/dev/hosts.ini ansible/roles/astradesk_docker/main.yml`.
- **Puppet**: `puppet apply puppet/manifests/astradesk.pp`.
- **Salt**: `salt '*' state.apply astradesk`.

### mTLS and Istio Service Mesh

1. Create the namespace: `kubectl apply -f deploy/istio/00-namespace.yaml`.
2. Enable mTLS: `kubectl apply -f deploy/istio/10-peer-authentication.yaml` (and the remaining files in `deploy/istio/`).
3. Gateway: HTTPS on port 443 with cert-manager.

<br>

## CI/CD

### Jenkins

- Pipeline in `Jenkinsfile` builds/tests/pushes images and deploys with Helm.

### GitLab CI

- `.gitlab-ci.yml`: stages for build/test/docker/deploy (manual).

<br>

## Monitoring and Observability

### OpenTelemetry

- Built into FastAPI (instrumentation).
- Export to OTLP (Prometheus/Grafana).

### Grafana Dashboards and Alerts

- Dashboard: `grafana/dashboard-astradesk.json` (latency, DB calls).
- Alerts: `grafana/alerts.yaml` (high latency, errors) — load into Prometheus.

<br>

## Developer's Guide

This section provides practical instructions and answers to common questions to help you get up to speed quickly.

### 1. Basic Environment Setup

Before you start, make sure you have:
- **Docker** and **Docker Compose** (Docker Desktop recommended).
- **Git**, **make**, and **Node.js** (v22+) installed locally.

One-time preparation steps:

1. **Clone the repository**:
    ```bash
    git clone https://github.com/your-org/astradesk.git
    cd astradesk
    ```
2. **Copy the config file**:
    ```bash
    cp .env.example .env
    ```
3. **Generate `package-lock.json`**: Required for building the Docker image of the Admin Portal.
    ```bash
    cd services/admin-portal && npm install && cd ../..
    ```

### 2. How to Run the Application?

Choose between two modes depending on your needs.

#### **Mode A: Full Docker Environment (Recommended)**

Runs the **entire application** (all microservices) in Docker containers. Ideal for integration testing and production-like simulation.

- **How to start?**
  ```bash
  make up
  ```
  *(Alternatively: `docker compose up --build -d`)*

- **How to stop and clean up?**
  ```bash
  make down
  ```
  *(Alternatively: `docker compose down -v`)*

- **Available services**:
  - **API Gateway**: `http://localhost:8080`
  - **Admin Portal**: `http://localhost:3000`
  - **Ticket Adapter**: `http://localhost:8081`

<br>

#### **Mode B: Hybrid Development (for Python work)**

Runs **only external dependencies** (databases, NATS, etc.) in Docker, while the **Python API server runs locally**. Ideal for rapid development and debugging of Python code with live reload.

1. **Step 1: Start dependencies in Docker** (in one terminal):
    ```bash
    make up-deps
    ```
    *(Alternatively: `docker compose up -d db mysql redis nats ticket-adapter`)*

2. **Step 2: Run the API server locally** (in another terminal):
    ```bash
    make run-local
    ```
    *(Alternatively: `python -m uvicorn src.gateway.main:app --host 0.0.0.0 --port 8080 --reload --app-dir src`)*

### 3. How to Test?

`Makefile` provides simple commands for running tests.

- **Run all tests**:
  ```bash
  make test-all
  ```
- **Run Python tests only**:
  ```bash
  make test
  ```
- **Run Java tests only**:
  ```bash
  make test-java
  ```
- **Run Admin Portal tests only**:
  ```bash
  make test-admin
  ```

### 4. Working with the Database and RAG

- **Initialize the database (create `pgvector` extension)**  
  *Note: If you use `docker-compose.deps.yml`, this step is not required.*
  ```bash
  make migrate
  ```

- **Populate the RAG knowledge base**

  1. Add your `.md` or `.txt` files to the `docs/` directory.
  2. Run:
      ```bash
      make ingest
      ```

### 5. How to Verify Agents Work?

After starting the application (in any mode), you can send requests to the API with `curl`.

*Note: The examples below assume the authorization guard (`auth_guard` in `main.py`) is temporarily disabled for testing.*

- **Test the `create_ticket` tool**:
  ```bash
  curl -X POST http://localhost:8080/v1/agents/run     -H "Content-Type: application/json"     -d '{"agent": "support", "input": "My internet is down, please create a ticket."}'
  ```
- **Test the `get_metrics` tool**:
  ```bash
  curl -X POST http://localhost:8080/v1/agents/run     -H "Content-Type: application/json"     -d '{"agent": "ops", "input": "Show me metrics for the webapp service"}'
  ```
- **Test RAG (knowledge base)**:
  ```bash
  curl -X POST http://localhost:8080/v1/agents/run     -H "Content-Type: application/json"     -d '{"agent": "support", "input": "How can I reset my password?"}'
  ```

### 6. FAQ — Common Issues and Questions

- **Q: I get `Connection refused` when starting the application.**  
  **A:** You are likely starting the API server (`make run-local`) before the dependency containers (`make up-deps`) are fully up. Ensure `docker ps` shows `(healthy)` for `db`, `mysql`, and `redis` before running Python.

- **Q: I get `{"detail":"Missing Authorization Bearer header."}`.**  
  **A:** This means `auth_guard` in `src/gateway/main.py` is enabled. For local tests, comment out the line `claims: dict[str, Any] = Depends(auth_guard),` in the `run_agent` endpoint and pass an empty dict `{}` as `claims` to `orchestrator.run`.

- **Q: How can I view logs of a specific service?**  
  **A:** Use `docker logs`. For example, to watch `Auditor` logs live:
    ```bash
    docker logs -f astradesk-auditor-1
    ```
    *(Container name may vary — check with `docker ps`.)*

- **Q: How can I rebuild just one Docker image?**  
  **A:** Use the `--build` flag with the service name:
    ```bash
    docker compose up -d --build api
    ```

- **Q: Where can I change keywords for the `KeywordPlanner`?**  
  **A:** In `src/runtime/planner.py`, inside the `KeywordPlanner` constructor (`__init__`).

<br>

## Testing

- Run: `make test` (Python), `make test-java`, `make test-admin`.

- Coverage: Unit (pytest, JUnit, Vitest), integration (API flow).

<br>

## Security

- **Auth**: OIDC/JWT with JWKS.

- **RBAC**: Per-tool, based on claims.

- **mTLS**: STRICT via Istio.

- **Audit**: In Postgres + NATS publish.

- **Policies**: Allow-lists in tools, retries in proxies.

<br>

## Roadmap

- LLM integration (Bedrock/OpenAI/vLLM) with guardrails.

- Temporal for long-running workflows.

- RAG evaluations (Ragas).

- Multi-tenancy and advanced RBAC (OPA).

- Complete Grafana dashboards with alerts.

<br>

## Contributing

- Fork the repo, create a branch, open a PR with tests.

- Run `make lint/type` before committing.

<br>

## License

Apache License 2.0. See [LICENSE](LICENSE) for details.

<br>

## Contact

Web site:[ AstraDesk](https://v0-site-creation-pi.vercel.app/)

Author: Siergej Sobolewski (s.sobolewski@hotmail.com).  

Issues: GitHub Issues.

<br>

---
Date: October 08, 2025.
