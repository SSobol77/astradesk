<p align="center">
  <img src="docs/assets/AstraDesktop.png" alt="AstraDesk - Enterprise AI Framework" width="560"/>
</p>

<br>

# AstraDesk - Enterprise AI Framework

[![License](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Python Version](https://img.shields.io/badge/Python-3.14-blue.svg)](https://www.python.org/downloads/release/python-3140/)
[![JDK Version](https://img.shields.io/badge/JDK-25-orange.svg)](https://openjdk.org/projects/jdk/25/)
[![PyTorch Version](https://img.shields.io/badge/PyTorch-2.9-magenta.svg)](https://pytorch.org/projects/pytorch/)
[![Node.js Version](https://img.shields.io/badge/Node.js-22-brightgreen.svg)](https://nodejs.org/en)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](https://github.com/your-org/astradesk/actions)


🌍 **Languages:** 🇺🇸 [English](README.md) | [Polski](docs/pl/README.pl.main.md) | [中文](docs/zh/README.zh-CN.main.md)

<br>

[AstraDesk](https://astradesk.vercel.app/)
is an internal framework for building AI agents designed for Support and SRE/DevOps departments.  
It provides a modular architecture with ready-to-use demo agents, integrations with databases, messaging systems, and DevOps tools.  
The framework supports scalability, enterprise-grade security (OIDC/JWT, RBAC, mTLS via Istio), and full CI/CD automation.

## Table of Contents

- [Features](#features)
- [Purpose and Use Cases](#purpose-and-use-cases)
- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Local Environment (Docker Compose)](#local-environment-docker-compose)
  - [Build from Source](#build-from-source)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [OIDC/JWT Authentication](#oidcjwt-authentication)
  - [RBAC Policies](#rbac-policies)
- [Usage](#usage)
  - [Running Agents](#running-agents)
  - [Loading Documents into RAG](#loading-documents-into-rag)
  - [Admin Portal](#admin-portal)
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
  - [Quick Start (Docker Compose)](#quick-start-docker-compose)
  - [Prometheus Configuration](#prometheus-configuration)
  - [Metrics Endpoints Integrations](#metrics-endpoints-integrations)
  - [Grafana (Quick Setup)](#grafana-quick-setup)
  - [Handy Commands (Makefile)](#handy-commands-makefile)
- [Developer Guide](#developer-guide)
- [Testing](#testing)
- [Security](#security)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Features

- **AI Agents**: Two ready-to-use agents:
  - **SupportAgent**: User support with RAG over corporate documents (PDF, HTML, Markdown), dialogue memory, and ticketing tools.
  - **OpsAgent**: SRE/DevOps automation — fetches metrics (Prometheus/Grafana), performs operational actions (e.g., restart service) with policies and auditing.
- **Modular Core**: Python-based framework with tool registry, planner, memory (Redis/Postgres), RAG (pgvector), and event handling (NATS).
- **Integrations**:
  - Java Ticket Adapter (Spring Boot WebFlux + MySQL) for enterprise ticketing systems.
  - Next.js Admin Portal for agent monitoring, audit trails, and prompt testing.
- **Security**: OIDC/JWT authentication, per-tool RBAC, mTLS via Istio, and full action audit.
- **DevOps Ready**: Docker, Kubernetes (Helm), OpenShift, Terraform (AWS), Ansible/Puppet/Salt, CI/CD with Jenkins and GitLab.
- **Observability**: OpenTelemetry, Prometheus/Grafana/Loki/Tempo stack.
- **Scalability**: HPA in Helm, retries/timeouts in integrations, autoscaling in EKS.

## Purpose and Use Cases

**AstraDesk** is a **framework for building AI agents** for **Support** and **SRE/DevOps** teams.  
It provides a modular core (planner, memory, RAG, tool registry) and includes ready-to-use agent examples.

- **Support / Helpdesk**: RAG over company documentation (procedures, FAQs, runbooks), ticket creation/update, conversation memory.
- **SRE/DevOps Automation**: Metric retrieval (Prometheus/Grafana), incident triage, and controlled operational actions (e.g., service restart) protected by **RBAC** and audited.
- **Enterprise Integrations**: Gateway (Python/FastAPI), Ticket Adapter (Java/WebFlux + MySQL), Admin Portal (Next.js), and data layer (Postgres/pgvector, Redis, NATS).
- **Security and Compliance**: OIDC/JWT, per-tool RBAC, **mTLS** (Istio), and complete audit trails.
- **Scalable Operations**: Docker/Kubernetes/OpenShift, Terraform (AWS), CI/CD (Jenkins/GitLab), observability (OpenTelemetry, Prometheus/Grafana/Loki/Tempo).

> **Not just a chatbot**, but a **framework** for composing your own agents, tools, and policies with full control (no SaaS lock-in).

## Architecture Overview

AstraDesk consists of three main components:
- **Python API Gateway**: FastAPI service handling agent requests, RAG, memory, and tools.
- **Java Ticket Adapter**: Reactive WebFlux service integrating with MySQL for ticketing.
- **Next.js Admin Portal**: Web interface for monitoring.

Communication: HTTP (between components), NATS (events/audits), Redis (working memory), Postgres/pgvector (RAG/dialogues/audits), MySQL (tickets).

## Prerequisites

- **Docker** and **Docker Compose** (for local dev).
- **Kubernetes** with Helm (for deployment).
- **AWS CLI** and **Terraform** (for cloud setup).
- **Node.js 22**, **JDK 21**, **Python 3.11** (for builds).
- **Postgres 17**, **MySQL 8**, **Redis 7**, **NATS 2** (core services).
- **Optional:** Istio, cert-manager (for mTLS/TLS).

## Installation

### Local Environment (Docker Compose)

1. Clone the repository:

```
git clone [https://github.com/your-org/astradesk.git](https://github.com/your-org/astradesk.git)
cd astradesk
```

2. Copy the sample configuration:

```
cp .env.example .env

```

- Edit `.env` (e.g. DATABASE_URL, OIDC_ISSUER).

3. Build and start:

```
make up

```

- This starts: API (8080), Ticket Adapter (8081), Admin Portal (3000), databases and supporting services.

4. Initialize Postgres (pgvector):

```
make migrate

```

5. Upload documents to `./docs` (e.g. .md, .txt) and initialize RAG:

```
make ingest

```

6. Check health:

```
curl [http://localhost:8080/healthz](http://localhost:8080/healthz)
```

- Admin Portal: http://localhost:3000


### Build from Source

1. Install dependencies:

```
make sync  # Python
make build-java  # Java
make build-admin  # Next.js

```

2. Run locally (without Docker):
- Python API: `uv run uvicorn gateway.main:app --host 0.0.0.0 --port 8080 --reload`
- Java Adapter: `cd services/ticket-adapter-java && ./gradlew bootRun`
- Admin Portal: `cd services/admin-portal && npm run dev`

## Configuration

### Environment Variables

- **DATABASE_URL**: PostgreSQL connection string (e.g. `postgresql://user:pass@host:5432/db`).
- **REDIS_URL**: Redis URI (e.g. `redis://host:6379/0`).
- **NATS_URL**: NATS server (e.g. `nats://host:4222`).
- **TICKETS_BASE_URL**: URL to Java adapter (e.g. `http://ticket-adapter:8081`).
- **MYSQL_URL**: MySQL JDBC (e.g. `jdbc:mysql://host:3306/db?useSSL=false`).
- **OIDC_ISSUER**: OIDC issuer (e.g. `https://your-issuer.com/`).
- **OIDC_AUDIENCE**: JWT audience.
- **OIDC_JWKS_URL**: JWKS URL (e.g. `https://your-issuer.com/.well-known/jwks.json`).

Full list in `.env.example`.

### OIDC/JWT Authentication

- Enabled in both API Gateway and Java Adapter.
- Use Bearer token in requests: `Authorization: Bearer <token>`.
- Validation: issuer, audience, signature via JWKS.
- For Admin Portal: use Auth0 or a similar front-channel flow.

### RBAC Policies

- Roles from JWT claims (e.g. `"roles": ["sre"]`).
- Tools (e.g. restart_service) validate via `require_role(claims, "sre")`.
- Customize in `runtime/policy.py` and tool definitions (e.g. `REQUIRED_ROLE_RESTART`).

## Usage

### Running Agents

Call the API:

```sh
curl -X POST http://localhost:8080/v1/agents/run \
-H "Content-Type: application/json" \
-H "Authorization: Bearer <your-jwt-token>" \
-d '{"agent": "support", "input": "Create a ticket for a network incident", "meta": {"user": "alice"}}'
````

* Response: JSON with output, trace_id, used_tools.
* Demo queries: `./scripts/demo_queries.sh`.

### Loading Documents into RAG

* Supported formats: .md, .txt (extendable to PDF/HTML).
* Run: `make ingest` (source: `./docs`).

### Admin Portal

* Accessible at `http://localhost:3000`.
* Features: API health check, sample curl commands for agents.
* Extend with audit fetch: add `/v1/audits` endpoint in API.

### Tools and Integrations

* Tool registry: `registry.py` — add new ones via `register(name, async_fn)`.
* Examples: create_ticket (proxy to Java), get_metrics (Prometheus stub), restart_service (RBAC-protected).

## Deployment

### Kubernetes (Helm)

1. Build and push images (use CI).
2. Install chart:

   ```sh
   helm upgrade --install astradesk deploy/chart -f deploy/chart/values.yaml \
     --set image.tag=0.2.1 \
     --set autoscaling.enabled=true
   ```

   * HPA: scales when CPU >60%.

### OpenShift

1. Process template:

   ```sh
   oc process -f deploy/openshift/astradesk-template.yaml -p TAG=0.2.1 | oc apply -f -
   ```

### AWS (Terraform)

1. Initialize:

   ```sh
   cd infra
   terraform init
   terraform apply -var="region=us-east-1" -var="project=astradesk"
   ```

   * Creates: VPC, EKS, RDS (Postgres/MySQL), S3.

### Configuration Management Tools

* **Ansible**: `ansible-playbook -i ansible/inventories/dev/hosts.ini ansible/roles/astradesk_docker/main.yml`.
* **Puppet**: `puppet apply puppet/manifests/astradesk.pp`.
* **Salt**: `salt '*' state.apply astradesk`.

### mTLS and Istio Service Mesh

1. Create namespace: `kubectl apply -f deploy/istio/00-namespace.yaml`.
2. Enable mTLS: `kubectl apply -f deploy/istio/10-peer-authentication.yaml` (and the rest in deploy/istio/).
3. Gateway: HTTPS on port 443 with cert-manager.

## CI/CD

### Jenkins

* Run pipeline: `Jenkinsfile` builds/tests/pushes images, deploys via Helm.

### GitLab CI

* `.gitlab-ci.yml`: stages for build/test/docker/deploy (manual).

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
      - "--web.enable-lifecycle"        # allows hot-reload of the config
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

*(Optional) Add `dev/prometheus/alerts.yml` and mount it similarly into the container (e.g., via an extra volume or fold it into `prometheus.yml`).*

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

* Prometheus UI: **[http://localhost:9090](http://localhost:9090)**

  * Check that `api` and `ticket-adapter` jobs are **UP** (Status → Targets).
* Grafana UI: **[http://localhost:3000](http://localhost:3000)**

  * Connect the Prometheus data source, import a dashboard, and watch key metrics (latency, request count, 5xx errors).
* Quick test:

  ```bash
  curl -s http://localhost:8080/metrics | head
  curl -s http://localhost:8081/actuator/prometheus | head
  ```

> If the endpoints don’t return metrics, make sure:
> 1) the paths (`/metrics`, `/actuator/prometheus`) are enabled,
> 2) services are reachable by the Compose network names `api` / `ticket-adapter`,
> 3) `prometheus.yml` points at the correct `targets`.

<br>

---

## Developer Guide

This section provides practical instructions and answers to common questions to help you start working with the project quickly.

### 1. Basic Environment Setup

Before starting, ensure you have:

* **Docker** and **Docker Compose** (Docker Desktop recommended).
* **Git**, **make**, and **Node.js** (v22+) installed locally.

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

* **To start:**

  ```bash
  make up
  ```

  *(Alternatively: `docker compose up --build -d`)*

* **To stop and clean up:**

  ```bash
  make down
  ```

  *(Alternatively: `docker compose down -v`)*

* **Available services:**

  * **API Gateway**: `http://localhost:8080`
  * **Admin Portal**: `http://localhost:3000`
  * **Ticket Adapter**: `http://localhost:8081`

<br>

#### **Mode B: Hybrid Development (for Python work)**

Runs **only external dependencies** (databases, NATS, etc.) in Docker, while the main **Python API runs locally**.
Ideal for fast development and debugging with instant reloads.

1. **Step 1: Start dependencies in Docker** (in one terminal):

   ```bash
   make up-deps
   ```

   *(Alternatively: `docker compose up -d db mysql redis nats ticket-adapter`)*

2. **Step 2: Run the API locally** (in another terminal):

   ```bash
   make run-local
   ```

   *(Alternatively: `python -m uvicorn src.gateway.main:app --host 0.0.0.0 --port 8080 --reload --app-dir src`)*

### 3. Testing

`Makefile` provides simple commands for running tests.

* **Run all tests:**

  ```bash
  make test-all
  ```
* **Python tests only:**

  ```bash
  make test
  ```
* **Java tests only:**

  ```bash
  make test-java
  ```
* **Admin Portal tests only:**

  ```bash
  make test-admin
  ```

### 4. Working with Database and RAG

* **Initialize database (create `pgvector` extension):**
  *Note: not needed if using `docker-compose.deps.yml`.*

  ```bash
  make migrate
  ```

* **Feed the RAG knowledge base:**

  1. Add your `.md` or `.txt` files to `docs/`.
  2. Run:

     ```bash
     make ingest
     ```

### 5. Testing the Agents

Once the app is running (in any mode), you can send requests to the API using `curl`.

*Note: The following assumes the authorization guard (`auth_guard`) in `main.py` is temporarily disabled for testing.*

* **Test `create_ticket` tool:**

  ```bash
  curl -X POST http://localhost:8080/v1/agents/run \
    -H "Content-Type: application/json" \
    -d '{"agent": "support", "input": "My internet is down, please create a ticket."}'
  ```
* **Test `get_metrics` tool:**

  ```bash
  curl -X POST http://localhost:8080/v1/agents/run \
    -H "Content-Type: application/json" \
    -d '{"agent": "ops", "input": "Show me metrics for the webapp service"}'
  ```
* **Test RAG (knowledge base):**

  ```bash
  curl -X POST http://localhost:8080/v1/agents/run \
    -H "Content-Type: application/json" \
    -d '{"agent": "support", "input": "How can I reset my password?"}'
  ```

### 6. FAQ - Common Issues and Questions

* **Q: I get `Connection refused` on startup.**

  * **A:** Most likely the API server (`make run-local`) starts before dependent containers are ready.
    Ensure `docker ps` shows `(healthy)` for `db`, `mysql`, and `redis` before starting Python.

* **Q: I get `{"detail":"Missing Bearer authorization header."}`.**

  * **A:** That means `auth_guard` in `src/gateway/main.py` is enabled.
    For local


testing, comment out `claims: dict[str, Any] = Depends(auth_guard),` in the `run_agent` endpoint definition and pass `{}` as `claims` to `orchestrator.run`.

* **Q: How do I view logs for a specific service?**

  * **A:** Use `docker logs`. For example, to follow Auditor logs live:

    ```bash
    docker logs -f astradesk-auditor-1
    ```

    *(Container name may vary — check with `docker ps`.)*

* **Q: How do I rebuild a single Docker image?**

  * **A:** Use the `--build` flag:

    ```bash
    docker compose up -d --build api
    ```

* **Q: Where can I modify `KeywordPlanner` keywords?**

  * **A:** In `src/runtime/planner.py`, inside the `__init__` method of `KeywordPlanner`.

<br>

## Testing

* Run: `make test` (Python), `make test-java`, `make test-admin`.
* Coverage: Unit (pytest, JUnit, Vitest), integration (API flow).

## Security

* **Auth**: OIDC/JWT with JWKS.
* **RBAC**: Per tool, based on claims.
* **mTLS**: STRICT via Istio.
* **Audit**: Logged to Postgres + NATS publish.
* **Policies**: Allow-lists in tools, proxy retries.

## Roadmap

* LLM integration (Bedrock/OpenAI/vLLM) with guardrails.
* Temporal for long-running workflows.
* RAG evaluations (Ragas).
* Advanced multi-tenancy & RBAC (OPA).
* Full Grafana dashboards with alerts.

## Contributing

* Fork the repo, create a branch, and submit a PR with tests.
* Run `make lint/type` before committing.

## License

Apache License 2.0. See [LICENSE](LICENSE) for details.

## Contact

🌐 Website: [AstraDesk](https://astradesk.vercel.app/)

📧 Author: Siergej Sobolewski ([s.sobolewski@hotmail.com](mailto:s.sobolewski@hotmail.com)).

💬 Support channel: [Support Slack](https://astradesk.slack.com)

🐙 Issues: [GitHub Issues](https://github.com/SSobol77/astradesk/issues).

<br>

---

*Last updated: 2025-10-19*

