# AstraDesk 2.0 - Internal AI Agents Framework

[![License](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Python Version](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![JDK Version](https://img.shields.io/badge/JDK-21-green.svg)](https://openjdk.org/projects/jdk/21/)
[![Node.js Version](https://img.shields.io/badge/Node.js-22-brightgreen.svg)](https://nodejs.org/en)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](https://github.com/your-org/astradesk/actions) 

<!-- Zmień na rzeczywisty link CI -->

AstraDesk to wewnętrzny framework do budowy agentów AI, zaprojektowany dla działów wsparcia (Support) i operacji (SRE/DevOps). Oferuje modularną architekturę z gotowymi agentami demonstracyjnymi, integracjami z bazami danych, systemami messagingu i narzędziami DevOps. Framework wspiera skalowalność, bezpieczeństwo enterprise (OIDC/JWT, RBAC, mTLS via Istio) oraz pełne CI/CD.

## Table of Contents

- [Features](#features)
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
- [Testing](#testing)
- [Security](#security)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Features

- **AI Agents**: Dwa gotowe agenty:
  - **SupportAgent**: Wsparcie użytkownika z RAG na dokumentach firmowych (PDF, HTML, Markdown), pamięcią dialogową i narzędziami ticketingu.
  - **OpsAgent**: Automatyzacje SRE/DevOps – pobieranie metryk (z Prometheus/Grafana), akcje operacyjne (np. restart usługi) z politykami i audytem.
- **Modular Core**: Python-based framework z registry tooli, plannerem, pamięcią (Redis/Postgres), RAG (pgvector) i eventami (NATS).
- **Integrations**:
  - Java Ticket Adapter (Spring Boot WebFlux + MySQL) dla korporacyjnych systemów ticketingu.
  - Next.js Admin Portal do monitoringu agentów, audytów i testów promptów.
- **Security**: OIDC/JWT auth, RBAC per tool, mTLS via Istio, audyt działań.
- **DevOps Ready**: Docker, Kubernetes (Helm), OpenShift, Terraform (AWS), Ansible/Puppet/Salt, CI/CD (Jenkins/GitLab).
- **Observability**: OpenTelemetry, Prometheus/Grafana/Loki/Tempo.
- **Scalability**: HPA w Helm, retries/timeouty w integracjach, autoscaling w EKS.

## Architecture Overview

AstraDesk składa się z trzech głównych komponentów:
- **Python API Gateway**: FastAPI obsługujący żądania do agentów, z RAG, pamięcią i toolami.
- **Java Ticket Adapter**: Reaktywny serwis (WebFlux) integrujący z MySQL dla ticketingu.
- **Next.js Admin Portal**: Interfejs webowy do monitoringu.

Komunikacja: HTTP (między komponentami), NATS (eventy/audyty), Redis (pamięć robocza), Postgres/pgvector (RAG/dialogi/audyty), MySQL (tickety).

## Prerequisites

- **Docker** i **Docker Compose** (do lokalnego dev).
- **Kubernetes** z Helm (do deploymentu).
- **AWS CLI** i **Terraform** (do chmury).
- **Node.js 22**, **JDK 21**, **Python 3.11** (do buildów).
- **Postgres 16**, **MySQL 8**, **Redis 7**, **NATS 2** (serwisy bazowe).
- Opcjonalnie: Istio, cert-manager (do mTLS/TLS).

## Installation

### Local Development with Docker Compose

1. Sklonuj repozytorium:
   ```
   git clone https://github.com/your-org/astradesk.git
   cd astradesk
   ```

2. Skopiuj przykładową konfigurację:
   ```
   cp .env.example .env
   ```
   - Edytuj `.env` (np. DATABASE_URL, OIDC_ISSUER).

3. Zbuduj i uruchom:
   ```
   make up
   ```
   - To uruchomi: API (8080), Ticket Adapter (8081), Admin Portal (3000), bazy i serwisy.

4. Zainicjuj bazę Postgres (pgvector):
   ```
   make migrate
   ```

5. Wrzuć dokumenty do `./docs` (np. .md, .txt) i zainicjuj RAG:
   ```
   make ingest
   ```

6. Sprawdź health:
   ```
   curl http://localhost:8080/healthz
   ```
   - Admin Portal: http://localhost:3000

### Building from Source

1. Zainstaluj zależności:
   ```
   make sync  # Python
   make build-java  # Java
   make build-admin  # Next.js
   ```

2. Uruchom lokalnie (bez Docker):
   - Python API: `uv run uvicorn gateway.main:app --host 0.0.0.0 --port 8080 --reload`
   - Java Adapter: `cd services/ticket-adapter-java && ./gradlew bootRun`
   - Admin Portal: `cd services/admin-portal && npm run dev`

## Configuration

### Environment Variables

- **DATABASE_URL**: PostgreSQL connection string (np. `postgresql://user:pass@host:5432/db`).
- **REDIS_URL**: Redis URI (np. `redis://host:6379/0`).
- **NATS_URL**: NATS server (np. `nats://host:4222`).
- **TICKETS_BASE_URL**: URL do Java adaptera (np. `http://ticket-adapter:8081`).
- **MYSQL_URL**: MySQL JDBC (np. `jdbc:mysql://host:3306/db?useSSL=false`).
- **OIDC_ISSUER**: Issuer OIDC (np. `https://your-issuer.com/`).
- **OIDC_AUDIENCE**: Audience JWT.
- **OIDC_JWKS_URL**: URL do JWKS (np. `https://your-issuer.com/.well-known/jwks.json`).

Pełna lista w `.env.example`.

### OIDC/JWT Authentication

- Włączone w API Gateway i Java Adapter.
- Użyj Bearer token w requestach: `Authorization: Bearer <token>`.
- Walidacja: Issuer, audience, signature via JWKS.
- W Admin Portal: Użyj Auth0 lub podobnego do front-channel flow.

### RBAC Policies

- Role z JWT claims (np. "roles": ["sre"]).
- Narzędzia (np. restart_service) sprawdzają role via `require_role(claims, "sre")`.
- Dostosuj w `runtime/policy.py` i toolach (np. `REQUIRED_ROLE_RESTART`).

## Usage

### Running Agents

Wywołaj API:
```
curl -X POST http://localhost:8080/v1/agents/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{"agent": "support", "input": "Utwórz ticket dla incydentu sieci", "meta": {"user": "alice"}}'
```

- Response: JSON z outputem, trace_id, used_tools.
- Demo queries: `./scripts/demo_queries.sh`.

### Ingesting Documents for RAG

- Wspierane formaty: .md, .txt (rozszerzalne o PDF/HTML).
- Uruchom: `make ingest` (źródło: `./docs`).

### Admin Portal

- Dostępny na http://localhost:3000.
- Funkcje: Health check API, przykładowe curl do agentów.
- Rozszerz o fetch audytów: Dodaj endpoint `/v1/audits` w API.

### Tools and Integrations

- Rejestr tooli: `registry.py` – dodaj nowe via `register(name, async_fn)`.
- Przykłady: create_ticket (proxy do Java), get_metrics (stub Prometheus), restart_service (z RBAC).

## Deployment

### Kubernetes with Helm

1. Zbuduj i push obrazy (użyj CI).
2. Zainstaluj chart:
   ```
   helm upgrade --install astradesk deploy/chart -f deploy/chart/values.yaml \
     --set image.tag=0.2.1 \
     --set autoscaling.enabled=true
   ```
   - HPA: Skaluje na CPU >60%.

### OpenShift

1. Procesuj template:
   ```
   oc process -f deploy/openshift/astradesk-template.yaml -p TAG=0.2.1 | oc apply -f -
   ```

### AWS with Terraform

1. Inicjuj:
   ```
   cd infra
   terraform init
   terraform apply -var="region=us-east-1" -var="project=astradesk"
   ```
   - Tworzy: VPC, EKS, RDS (Postgres/MySQL), S3.

### Configuration Management Tools

- **Ansible**: `ansible-playbook -i ansible/inventories/dev/hosts.ini ansible/roles/astradesk_docker/main.yml`.
- **Puppet**: `puppet apply puppet/manifests/astradesk.pp`.
- **Salt**: `salt '*' state.apply astradesk`.

### mTLS and Istio Service Mesh

1. Utwórz namespace: `kubectl apply -f deploy/istio/00-namespace.yaml`.
2. Włącz mTLS: `kubectl apply -f deploy/istio/10-peer-authentication.yaml` (i resztę plików z deploy/istio/).
3. Gateway: HTTPS na port 443 z cert-manager.

## CI/CD

### Jenkins

- Uruchom pipeline: `Jenkinsfile` buduje/testuje/pushuje obrazy, deployuje Helm.

### GitLab CI

- `.gitlab-ci.yml`: Etapy build/test/docker/deploy (manual).

## Monitoring and Observability

### OpenTelemetry

- Wbudowane w FastAPI (instrumentation).
- Eksport: Do OTLP (Prometheus/Grafana).

### Grafana Dashboards and Alerts

- Dashboard: `grafana/dashboard-astradesk.json` (latency, DB calls).
- Alerty: `grafana/alerts.yaml` (high latency, errors) – załaduj do Prometheus.

## Testing

- Uruchom: `make test` (Python), `make test-java`, `make test-admin`.
- Pokrycie: Unit (pytest, JUnit, Vitest), integracyjne (API flow).

## Security

- **Auth**: OIDC/JWT z JWKS.
- **RBAC**: Per tool, na bazie claims.
- **mTLS**: STRICT via Istio.
- **Audyt**: W Postgres + NATS publish.
- **Polityki**: Allow-lists w toolach, retries w proxy.

## Roadmap

- Integracja LLM (Bedrock/OpenAI/vLLM) z guardrails.
- Temporal dla długotrwałych workflowów.
- Ewaluacje RAG (Ragas).
- Multi-tenancy i RBAC advanced (OPA).
- Pełne dashboardy Grafana z alertami.

## Contributing

- Fork repo, stwórz branch, PR z testami.
- Użyj `make lint/type` przed commit.

## License

MIT License. See [LICENSE](LICENSE) for details.

## Contact

Autor: Siergej Sobolewski (s.sobolewski@hotmail.com).  
Issues: [GitHub Issues](https://github.com/SSobol77/astradesk/issues).  
Data: October 04, 2025.
