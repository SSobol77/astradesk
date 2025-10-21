<p align="center">
  <img src="docs/assets/AstraDesktop.png" alt="AstraDesk - Enterprise AI Framework" width="560"/>
</p>

<br>

# AstraDesk - Enterprise AI Framework

[![License](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Python Version](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![JDK Version](https://img.shields.io/badge/JDK-21-green.svg)](https://openjdk.org/projects/jdk/21/)
[![Node.js Version](https://img.shields.io/badge/Node.js-22-brightgreen.svg)](https://nodejs.org/en)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](https://github.com/your-org/astradesk/actions)

🌍 **Języki:** [English](README.md) | 🇵🇱 [Polski](README.pl.md) | [中文 (当前文件)](README.zh-CN.md)

<br>

[AstraDesk](https://astradesk.vercel.app/)
 to wewnętrzny framework do budowy agentów AI, zaprojektowany dla działów wsparcia (Support) i operacji (SRE/DevOps). Oferuje modularną architekturę z gotowymi agentami demonstracyjnymi, integracjami z bazami danych, systemami messagingu i narzędziami DevOps. Framework wspiera skalowalność, bezpieczeństwo enterprise (OIDC/JWT, RBAC, mTLS via Istio) oraz pełne CI/CD.

<br>

---

## Spis treści

- [Funkcje](#funkcje)
- [Przeznaczenie i Zastosowania](#przeznaczenie-i-zastosowania)
- [Przegląd architektury](#przegląd-architektury)
- [Wymagania wstępne](#wymagania-wstępne)
- [Getting Started & Developer Guide](#getting-started--developer-guide)
- [Konfiguracja](#konfiguracja)
  - [Zmienne środowiskowe](#zmienne-środowiskowe)
  - [Uwierzytelnianie OIDC/JWT](#uwierzytelnianie-oidcjwt)
  - [Polityki RBAC](#polityki-rbac)
- [Usage](#usage)
  - [Running Agents](#running-agents)
  - [Admin Portal](#admin-portal)
- [Wdrożenie](#wdrożenie)
  - [Kubernetes (Helm)](#kubernetes-helm)
  - [OpenShift](#openshift)
  - [AWS (Terraform)](#aws-terraform)
  - [Narzędzia zarządzania konfiguracją](#narzędzia-zarządzania-konfiguracją)
  - [mTLS i siatka usług Istio](#mtls-i-siatka-usług-istio)
- [CI/CD](#cicd)
  - [Jenkins](#jenkins)
  - [GitLab CI](#gitlab-ci)
- [Monitorowanie i obserwowalność](#monitorowanie-i-obserwowalność)
  - [Szybki start (Docker Compose)](#szybki-start-docker-compose)
  - [Konfiguracja Prometheus](konfiguracja-prometheus)
  - [Endpointy metryk - integracje](#endpointy-metryk-integracje)
  - [Grafana (szybka konfiguracja)](#grafana-szybka-konfiguracja)
  - [Przydatne komendy (Makefile)](#przydatne-komendy-makefile)
- [Testowanie](#testowanie)
- [Bezpieczeństwo](#bezpieczeństwo)
- [Mapa drogowa](#mapa-drogowa)
- [Wkład](#wkład)
- [Licencja](#licencja)
- [Kontakt](#kontakt)

<br>

---

## Funkcje

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

<br>

---

## Przeznaczenie i Zastosowania

**AstraDesk** to **framework do budowy agentów AI** dla zespołów **Support** oraz **SRE/DevOps**.
Zapewnia modułowy rdzeń (planer, pamięć, RAG, rejestr narzędzi) i gotowe agentowe przykłady.

- **Support / Helpdesk**: RAG na dokumentach firmy (procedury, FAQ, runbooki), tworzenie/aktualizacja zgłoszeń (tickety), pamięć konwersacji.
- **Automatyzacje SRE/DevOps**: odczyt metryk (Prometheus/Grafana), triage incydentów, kontrolowane akcje (np. restart usługi) zabezpieczone **RBAC** i objęte audytem.
- **Integracje enterprise**: Gateway (Python/FastAPI), Adapter Ticketów (Java/WebFlux + MySQL), Portal Admin (Next.js) oraz warstwa danych (Postgres/pgvector, Redis, NATS).
- **Bezpieczeństwo i compliance**: OIDC/JWT, RBAC per-narzędzie, **mTLS** (Istio), pełen ślad audytowy.
- **Operacje na skalę**: Docker/Kubernetes/OpenShift, Terraform (AWS), CI/CD (Jenkins/GitLab), obserwowalność (OpenTelemetry, Prometheus/Grafana/Loki/Tempo).

> **To nie pojedynczy chatbot**, lecz **framework** do komponowania własnych agentów, narzędzi i polityk z pełną kontrolą (bez lock-in do SaaS). :contentReference[oaicite:1]{index=1}

<br>

---

## Przegląd architektury

AstraDesk składa się z trzech głównych komponentów:
- **Python API Gateway**: FastAPI obsługujący żądania do agentów, z RAG, pamięcią i toolami.
- **Java Ticket Adapter**: Reaktywny serwis (WebFlux) integrujący z MySQL dla ticketingu.
- **Next.js Admin Portal**: Interfejs webowy do monitoringu.

Komunikacja: HTTP (między komponentami), NATS (eventy/audyty), Redis (pamięć robocza), Postgres/pgvector (RAG/dialogi/audyty), MySQL (tickety). :contentReference[oaicite:2]{index=2}

<br>

---

## Wymagania wstępne

- **Docker** i **Docker Compose** (do lokalnego dev).
- **Kubernetes** z Helm (do deploymentu).
- **AWS CLI** i **Terraform** (do chmury).
- **Node.js 22**, **JDK 21**, **Python 3.11** (do buildów).
- **Postgres 17**, **MySQL 8**, **Redis 8**, **NATS 2** (serwisy bazowe).
- **Opcjonalnie:** Istio, cert-manager (do mTLS/TLS).

<br>

---

## Getting Started & Developer Guide

This section provides a complete guide to setting up, running, and developing the AstraDesk platform locally.

<br>

### Prerequisites

- **Docker & Docker Compose**: Essential for running all services. Docker Desktop is recommended.
- **Git**: For version control.
- **Node.js v22+**: Required for building the Admin Portal and generating `package-lock.json`.
- **JDK 21+**: Required for building and running the Java Ticket Adapter.
- **Python 3.11+ & `uv`**: For managing the Python environment.
- **make**: Recommended for easy access to common commands.

<br>

### 1. Initial Project Setup (Run Once)

1. **Clone the repository**:

   ```bash
   git clone https://github.com/your-org/astradesk.git
   cd astradesk
   ```

2. **Copy the environment file**:

   ```bash
   cp .env.example .env
   ```

   *Note: The default values in `.env` are configured for the hybrid development mode. For the full Docker mode, you may need to adjust URLs to use service names (e.g., `http://api:8080`).*

3. **Generate `package-lock.json`**:

   ```bash
   make bootstrap-frontend
   ```

   *(This runs `npm install` in the `admin-portal` directory).*

<br>

### 2. Running the Application

Choose one of the following modes for local development.

#### Mode A: Full Docker Environment (Production-like)

Runs the entire application stack in Docker. Best for integration testing.

* **Start all services**:

  ```bash
  make up
  ```
* **Stop and clean up**:

  ```bash
  make down
 
  ```

#### Mode B: Hybrid Development (Recommended for Python/Frontend)

Runs external dependencies (databases, NATS) in Docker, while you run the Python API or Next.js portal locally for fast, hot-reloaded development.

1. **Start dependencies in Docker** (in one terminal):

   ```bash
   make up-deps
   ```
2. **Run the Python API locally** (in a second terminal):

   ```bash
   make run-local-api
   ```
3. **Run the Admin Portal locally** (in a third terminal):

   ```bash
   make run-local-admin
   ```

<br>

### 3. Common Development Tasks (Makefile)

The `Makefile` is your central command hub. Use `make help` to see all available commands.

* **Run all tests**: `make test-all`
* **Check code quality**: `make lint` and `make type`
* **Initialize the database**: `make migrate`
* **Ingest RAG documents**: `make ingest`

<br>

### 4. Testing the Agents

Once the application is running, you can send `curl` requests to the API.

*Note: The examples below assume the `auth_guard` in `main.py` is temporarily disabled for local testing.*

* **Test `create_ticket` tool**:

  ```bash
  curl -X POST http://localhost:8080/v1/agents/run \
    -H "Content-Type: application/json" \
    -d '{"agent": "support", "input": "My internet is down, please create a ticket."}'
  ```
* **Test RAG (knowledge base)**:

  ```bash
  curl -X POST http://localhost:8080/v1/agents/run \
    -H "Content-Type: application/json" \
    -d '{"agent": "support", "input": "How can I reset my password?"}'
  ```

### 5. FAQ - Common Issues

* **Q: I get `Connection refused` on startup.**
  **A:** Ensure the dependency containers are fully running and `(healthy)` before starting the local Python server. Check with `docker ps`.

* **Q: I get a `401 Unauthorized` or `Missing Bearer` error.**
  **A:** For local testing, you can temporarily disable the `auth_guard` dependency in the `run_agent` endpoint in `src/gateway/main.py`.

* **Q: How do I view logs for a specific service?**
  **A:** Use `make logs-api`, `make logs-auditor`, or `docker logs -f <container_name>`.

<br>

---

## Konfiguracja

### Zmienne środowiskowe

* **DATABASE_URL**: PostgreSQL connection string (np. `postgresql://user:pass@host:5432/db`).
* **REDIS_URL**: Redis URI (np. `redis://host:6379/0`).
* **NATS_URL**: NATS server (np. `nats://host:4222`).
* **TICKETS_BASE_URL**: URL do Java adaptera (np. `http://ticket-adapter:8081`).
* **MYSQL_URL**: MySQL JDBC (np. `jdbc:mysql://host:3306/db?useSSL=false`).
* **OIDC_ISSUER**: Issuer OIDC (np. `https://your-issuer.com/`).
* **OIDC_AUDIENCE**: Audience JWT.
* **OIDC_JWKS_URL**: URL do JWKS (np. `https://your-issuer.com/.well-known/jwks.json`).

Pełna lista w `.env.example`.

<br>

### Uwierzytelnianie OIDC/JWT

* Włączone w API Gateway i Java Adapter.
* Użyj Bearer token w requestach: `Authorization: Bearer <token>`.
* Walidacja: Issuer, audience, signature via JWKS.
* W Admin Portal: Użyj Auth0 lub podobnego do front-channel flow.

<br>

### Polityki RBAC

* Role z JWT claims (np. `"roles": ["sre"]`).
* Narzędzia (np. `restart_service`) sprawdzają role via `require_role(claims, "sre")`.
* Dostosuj w `runtime/policy.py` i toolach (np. `REQUIRED_ROLE_RESTART`).

<br>

## Usage

The primary way to interact with AstraDesk is through its REST API.

<br>

### Running Agents

To execute an agent, send a `POST` request to the `/v1/agents/run` endpoint:

```sh
curl -X POST http://localhost:8080/v1/agents/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{"agent": "support", "input": "Create a ticket for a network incident", "meta": {"user": "alice"}}'
```

The response will be a JSON object containing the agent's output and a `reasoning_trace_id`.

<br>

### Admin Portal

The web-based Admin Portal, available at `http://localhost:3000`, provides a UI for monitoring system health and managing platform components as defined in the [OpenAPI specification](openapi/astradesk-admin.v1.yaml).

<br>

---

## Wdrożenie

### Kubernetes (Helm)

1. Zbuduj i push obrazy (użyj CI).

2. Zainstaluj chart:

   ```sh
   helm upgrade --install astradesk deploy/chart -f deploy/chart/values.yaml \
     --set image.tag=0.2.1 \
     --set autoscaling.enabled=true
   ```

   - **HPA:** Skaluje na CPU >60%.

<br>

### OpenShift

**Procesuj template:**

   ```sh
   oc process -f deploy/openshift/astradesk-template.yaml -p TAG=0.2.1 | oc apply -f -
   ```

<br>

### AWS (Terraform)

**Inicjuj:**

   ```sh
   cd infra
   terraform init
   terraform apply -var="region=us-east-1" -var="project=astradesk"
   ```

   * Tworzy: VPC, EKS, RDS (Postgres/MySQL), S3.

<br>

### Narzędzia zarządzania konfiguracją

* **Ansible**: `ansible-playbook -i ansible/inventories/dev/hosts.ini ansible/roles/astradesk_docker/main.yml`.
* **Puppet**: `puppet apply puppet/manifests/astradesk.pp`.
* **Salt**: `salt '*' state.apply astradesk`.

<br>

### mTLS i siatka usług Istio

1. Utwórz namespace: `kubectl apply -f deploy/istio/00-namespace.yaml`.
2. Włącz mTLS: `kubectl apply -f deploy/istio/10-peer-authentication.yaml` (i resztę plików z `deploy/istio/`).
3. Gateway: HTTPS na port 443 z cert-manager.

<br>

---

## CI/CD

### Jenkins

* Uruchom pipeline: `Jenkinsfile` buduje/testuje/pushuje obrazy, deployuje Helm.

### GitLab CI

* `.gitlab-ci.yml`: Etapy build/test/docker/deploy (manual).

<br>

---

## Monitorowanie i obserwowalność 

**(Prometheus, Grafana, OpenTelemetry)**

Ta sekcja opisuje, jak włączyć pełną obserwowalność platformy AstraDesk z użyciem **Prometheus** (metyki), **Grafana** (dashboardy) i **OpenTelemetry** (instrumentacja).

### Cele

- Zbieranie metryk z **Python API Gateway** (`/metrics`) oraz **Java Ticket Adapter** (`/actuator/prometheus`).
- Szybki podgląd kondycji w **Grafanie**.
- Alerting (np. wysoki odsetek błędów 5xx) w Prometheus.

<br>

### Szybki start (Docker Compose)

Poniżej minimalny wycinek do dodania do `docker-compose.yml` (usługi Prometheus + Grafana).
> **Uwaga:** Zakładamy, że usługi `api` i `ticket-adapter` działają jak w projekcie: `api:8080`, `ticket-adapter:8081`.

```yaml
services:
  # --- Observability stack ---
  prometheus:
    image: prom/prometheus:latest
    container_name: astradesk-prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--web.enable-lifecycle"        # pozwala na hot-reload konfiguracji
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
      # (opcjonalnie) automatyczna konfiguracja źródeł danych / dashboardów:
      # - ./dev/grafana/provisioning:/etc/grafana/provisioning:ro
    ports:
      - "3000:3000"
    restart: unless-stopped
    depends_on:
      - prometheus

volumes:
  prometheus-data:
  grafana-data:
````

<br>

### Konfiguracja Prometheus 

`dev/prometheus/prometheus.yml`

Utwórz plik `dev/prometheus/prometheus.yml` z następującą zawartością:

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

  # (opcjonalnie) NATS Exporter
  # - job_name: "nats"
  #   static_configs:
  #     - targets: ["nats-exporter:7777"]

rule_files:
  - /etc/prometheus/alerts.yml
```

*(Opcjonalnie) dodaj plik `dev/prometheus/alerts.yml` i zamontuj go analogicznie do kontenera (np. przez dodatkowy volume lub rozszerz `prometheus.yml` bez osobnego pliku).*

Przykładowe reguły alertów:

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

> **Reload konfiguracji** bez restartu:
> `curl -X POST http://localhost:9090/-/reload`

<br>

### Endpointy metryk integracje

<br>

#### 1) Python FastAPI (Gateway)

Najprościej wystawić `/metrics` przez `prometheus_client`:

```python
# src/gateway/observability.py
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import Summary
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

# (opcjonalnie) prosty middleware do latencji i zliczeń
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

Rejestracja w `main.py`:

```python
from fastapi import FastAPI
from src.gateway.observability import router as metrics_router, metrics_middleware

app = FastAPI()
app.middleware("http")(metrics_middleware)
app.include_router(metrics_router, tags=["observability"])
```

> **Alternatywa (polecane)**: użyj **OpenTelemetry** + `otlp` exporter, a następnie skrapuj metryki przez **otel-collector** → Prometheus. Ta opcja daje spójne metryki, ślady i logi.

#### 2) Java Ticket Adapter (Spring Boot)

W `application.yml`:

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

Dodaj zależności Micrometer Prometheus:

```xml
<!-- pom.xml -->
<dependency>
  <groupId>io.micrometer</groupId>
  <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>
```

Po uruchomieniu endpoint jest dostępny pod:
`http://localhost:8081/actuator/prometheus` (lub `ticket-adapter:8081` w Dockerze).

<br>

### Grafana (szybka konfiguracja)

Po starcie Grafany ([http://localhost:3000](http://localhost:3000), domyślnie `admin`/`admin`):

1. **Add data source → Prometheus**
   URL: `http://prometheus:9090` (z perspektywy sieci Docker Compose) lub `http://localhost:9090` (jeśli dodajesz ręcznie z hosta).
2. **Importuj dashboard** (np. „Prometheus / Overview” albo własny).
   Możesz też utrzymywać deskryptory w repo (`grafana/dashboard-astradesk.json`) i włączyć provisioning:

   ```
   dev/grafana/provisioning/datasources/prometheus.yaml
   dev/grafana/provisioning/dashboards/dashboards.yaml
   grafana/dashboard-astradesk.json
   ```

Przykład datasources (provisioning):

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

Przykład deklaracji dashboardów:

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

### Przydatne komendy (Makefile)

Dodaj skróty do `Makefile`, aby ułatwić pracę:

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

### Weryfikacja działania

* Prometheus UI: **[http://localhost:9090](http://localhost:9090)**

  * Sprawdź, czy joby `api` i `ticket-adapter` są **UP** (Status → Targets).

* Grafana UI: **[http://localhost:3000](http://localhost:3000)**

  * Podłącz źródło danych (Prometheus), zaimportuj dashboard i obserwuj metryki (latencja, liczba żądań, błędy 5xx).

* Szybki test:

  ```bash
  curl -s http://localhost:8080/metrics | head

  curl -s http://localhost:8081/actuator/prometheus | head
  ```

<br>

> Jeśli endpointy nie zwracają metryk, upewnij się, że:
>
> 1) ścieżki (`/metrics`, `/actuator/prometheus`) są włączone,
>
> 2) usługi są osiągalne po nazwach `api` / `ticket-adapter` w sieci Compose,
>
> 3) `prometheus.yml` wskazuje poprawne `targets`.

<br>

---

## Testowanie

* Uruchom: `make test` (Python), `make test-java`, `make test-admin`.
* Pokrycie: Unit (pytest, JUnit, Vitest), integracyjne (API flow).

<br>

---

## Bezpieczeństwo

* **Auth**: OIDC/JWT z JWKS.
* **RBAC**: Per tool, na bazie claims.
* **mTLS**: STRICT via Istio.
* **Audyt**: W Postgres + NATS publish.
* **Polityki**: Allow-lists w toolach, retries w proxy.

<br>

---

## Mapa drogowa

* Integracja LLM (Bedrock/OpenAI/vLLM) z guardrails.
* Temporal dla długotrwałych workflowów.
* Ewaluacje RAG (Ragas).
* Multi-tenancy i RBAC advanced (OPA).
* Pełne dashboardy Grafana z alertami.

<br>

---

## Wkład

* Fork repo, stwórz branch, PR z testami.
* Użyj `make lint/type` przed commit.

<br>

---

## Licencja

Apache License 2.0. See [LICENSE](LICENSE) for details.

---

<br>

## Kontakt

🌐 Web site: [AstraDesk](https://astradesk.vercel.app/)

📧 Autor: Siergej Sobolewski ([s.sobolewski@hotmail.com](mailto:s.sobolewski@hotmail.com)).

💬 Kanały wsparcia: [Support Slack](https://astradesk.slack.com)

🐙 Issues: [GitHub Issues](https://github.com/SSobol77/astradesk/issues).

<br>

---

*Ostatnia aktualizacja: 2025-10-21*



