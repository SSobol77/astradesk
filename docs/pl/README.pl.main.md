<p align="center">
  <img src="https://astradesk.dev/_next/image?url=%2FAstraDesk_wlogo.png&w=640&q=75" alt="AstraDesk - Enterprise AI Framework" width="560"/>
</p>

<br>

# AstraDesk - Enterprise AI Framework

[![License](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Python Version](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![JDK Version](https://img.shields.io/badge/JDK-21-green.svg)](https://openjdk.org/projects/jdk/21/)
[![Node.js Version](https://img.shields.io/badge/Node.js-22-brightgreen.svg)](https://nodejs.org/en)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](https://github.com/your-org/astradesk/actions)

🌍 **Języki:** [English](https://github.com/SSobol77/astradesk/edit/main/README.md) | 🇵🇱 [Polski](https://github.com/SSobol77/astradesk/edit/main/docs/pl/README.pl.main.md) | [中文](https://github.com/SSobol77/astradesk/blob/main/docs/zh/README.zh-CN.main.md)

<br>

[AstraDesk](https://www.astradesk.dev) to wewnętrzny framework do budowy agentów AI, zaprojektowany dla działów wsparcia (Support) i operacji (SRE/DevOps). Oferuje modularną architekturę z gotowymi agentami demonstracyjnymi, integracjami z bazami danych, systemami komunikatów i narzędziami DevOps. Framework wspiera skalowalność, bezpieczeństwo enterprise (OIDC/JWT, RBAC, mTLS via Istio) oraz pełne CI/CD.

<br>

---

## Spis treści

- [Funkcje](#funkcje)
- [Przeznaczenie i zastosowania](#przeznaczenie-i-zastosowania)
- [Przegląd architektury](#przegląd-architektury)
- [Wymagania wstępne](#wymagania-wstępne)
- [Pierwsze kroki i przewodnik dla programisty](#pierwsze-kroki-i-przewodnik-dla-programisty)
- [Konfiguracja](#konfiguracja)
  - [Zmienne środowiskowe](#zmienne-środowiskowe)
  - [Uwierzytelnianie OIDC/JWT](#uwierzytelnianie-oidcjwt)
  - [Polityki RBAC](#polityki-rbac)
- [Użycie](#użycie)
  - [Uruchamianie agentów](#uruchamianie-agentów)
  - [Portal administracyjny](#portal-administracyjny)
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
  - [Konfiguracja Prometheus](#konfiguracja-prometheus)
  - [Endpointy metryk – integracje](#endpointy-metryk-integracje)
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

- **Agenci AI**: Dwa gotowe agenty:
  - **SupportAgent**: Wsparcie użytkownika z RAG na dokumentach firmowych (PDF, HTML, Markdown), pamięcią dialogową i narzędziami do zarządzania ticketami.
  - **OpsAgent**: Automatyzacje SRE/DevOps – pobieranie metryk (z Prometheus/Grafana), akcje operacyjne (np. restart usługi) z politykami i audytem.
- **Modularny rdzeń**: Framework oparty na Pythonie z rejestrem narzędzi, planerem, pamięcią (Redis/Postgres), RAG (pgvector) i zdarzeniami (NATS).
- **Integracje**:
  - Java Ticket Adapter (Spring Boot WebFlux + MySQL) dla korporacyjnych systemów ticketów.
  - Next.js Admin Portal do monitoringu agentów, audytów i testów promptów.
  - **MCP Gateway**: Standaryzowany protokół bramy dla interakcji narzędzi agentów AI z bezpieczeństwem, audytem i limitem wywołań.
- **Bezpieczeństwo**: Uwierzytelnianie OIDC/JWT, RBAC per narzędzie, mTLS via Istio, audyt działań.
- **Gotowość DevOps**: Docker, Kubernetes (Helm), OpenShift, Terraform (AWS), Ansible/Puppet/Salt, CI/CD (Jenkins/GitLab).
- **Obserwowalność**: OpenTelemetry, Prometheus/Grafana/Loki/Tempo.
- **Skalowalność**: HPA w Helm, mechanizmy ponawiania i timeoutów w integracjach, autoscaling w EKS.

<br>

---

## Przeznaczenie i zastosowania

**AstraDesk** to **framework do budowy agentów AI** dla zespołów **Support** oraz **SRE/DevOps**. Zapewnia modułowy rdzeń (planer, pamięć, RAG, rejestr narzędzi) i gotowe przykłady agentów.

- **Support / Helpdesk**: RAG na dokumentach firmy (procedury, FAQ, runbooki), tworzenie/aktualizacja zgłoszeń (ticketów), pamięć konwersacji.
- **Automatyzacje SRE/DevOps**: odczyt metryk (Prometheus/Grafana), triage incydentów, kontrolowane akcje (np. restart usługi) zabezpieczone **RBAC** i objęte audytem.
- **Integracje enterprise**: Gateway (Python/FastAPI), Adapter Ticketów (Java/WebFlux + MySQL), Portal Admin (Next.js), MCP Gateway oraz warstwa danych (Postgres/pgvector, Redis, NATS).
- **Bezpieczeństwo i compliance**: OIDC/JWT, RBAC per-narzędzie, **mTLS** (Istio), pełen ślad audytowy.
- **Operacje na skalę**: Docker/Kubernetes/OpenShift, Terraform (AWS), CI/CD (Jenkins/GitLab), obserwowalność (OpenTelemetry, Prometheus/Grafana/Loki/Tempo).

> **To nie pojedynczy chatbot**, lecz **framework** do komponowania własnych agentów, narzędzi i polityk z pełną kontrolą (bez lock-in do SaaS).

<br>

---

## Przegląd architektury

AstraDesk składa się z kilku głównych komponentów:
- **Python API Gateway**: FastAPI obsługujący żądania do agentów, z RAG, pamięcią i narzędziami.
- **Java Ticket Adapter**: Reaktywny serwis (WebFlux) integrujący z MySQL dla obsługi ticketów.
- **Next.js Admin Portal**: Interfejs webowy do monitoringu.
- **MCP Gateway**: Standaryzowany protokół bramy dla interakcji narzędzi agentów AI z bezpieczeństwem, audytem i limitem wywołań.

Komunikacja: HTTP (między komponentami), NATS (zdarzenia/audyty), Redis (pamięć robocza), Postgres/pgvector (RAG/dialogi/audyty), MySQL (tickety).

<br>

---

## Wymagania wstępne

- **Docker** i **Docker Compose** (do lokalnego developmentu).
- **Kubernetes** z Helm (do wdrożenia).
- **AWS CLI** i **Terraform** (do chmury).
- **Node.js 22**, **JDK 21**, **Python 3.11** (do budowania).
- **Postgres 17**, **MySQL 8**, **Redis 8**, **NATS 2** (serwisy bazowe).
- **Opcjonalnie:** Istio, cert-manager (do mTLS/TLS).

<br>

---

## Pierwsze kroki i przewodnik dla programisty

Ta sekcja zawiera kompletny przewodnik konfiguracji, uruchamiania i developmentu platformy AstraDesk lokalnie.

<br>

### Wymagania wstępne

- **Docker i Docker Compose**: Niezbędne do uruchomienia wszystkich usług. Zalecany Docker Desktop.
- **Git**: Do kontroli wersji.
- **Node.js v22+**: Wymagany do budowania Portalu Administracyjnego i generowania `package-lock.json`.
- **JDK 21+**: Wymagany do budowania i uruchamiania Java Ticket Adapter.
- **Python 3.11+ i `uv`**: Do zarządzania środowiskiem Python.
- **make**: Zalecany dla łatwego dostępu do typowych komend.

<br>

### 1. Wstępna konfiguracja projektu (uruchom raz)

1. **Sklonuj repozytorium**:

   ```bash
   git clone https://github.com/your-org/astradesk.git
   cd astradesk
   ```

2. **Skopiuj plik zmiennych środowiskowych**:

   ```bash
   cp .env.example .env
   ```

   *Uwaga: Domyślne wartości w `.env` są skonfigurowane dla hybrydowego trybu developmentu. Dla pełnego trybu Docker może być konieczna adaptacja URL-i do użycia nazw usług (np. `http://api:8080`).*

3. **Wygeneruj `package-lock.json`**:

   ```bash
   make bootstrap-frontend
   ```

   *(To uruchamia `npm install` w katalogu `admin-portal`).*

<br>

### 2. Uruchamianie aplikacji

Wybierz jeden z poniższych trybów do developmentu lokalnego.

#### Tryb A: Pełne środowisko Docker (zbliżone do produkcyjnego)

Uruchamia cały stos aplikacji w Dockerze. Najlepsze do testów integracyjnych.

* **Uruchom wszystkie usługi**:

  ```bash
  make up
  ```
* **Zatrzymaj i wyczyść**:

  ```bash
  make down
  ```

#### Tryb B: Hybrydowy development (zalecany dla Python/Frontend)

Uruchamia zależności zewnętrzne (bazy danych, NATS) w Dockerze, podczas gdy Python API lub portal Next.js uruchamiasz lokalnie dla szybkiego developmentu z hot-reload.

1. **Uruchom zależności w Dockerze** (w jednym terminalu):

   ```bash
   make up-deps
   ```
2. **Uruchom Python API lokalnie** (w drugim terminalu):

   ```bash
   make run-local-api
   ```
3. **Uruchom Portal Administracyjny lokalnie** (w trzecim terminalu):

   ```bash
   make run-local-admin
   ```

<br>

### 3. Typowe zadania programistyczne (Makefile)

`Makefile` jest centralnym hubem komend. Użyj `make help`, aby zobaczyć wszystkie dostępne komendy.

* **Uruchom wszystkie testy**: `make test-all`
* **Sprawdź jakość kodu**: `make lint` i `make type`
* **Zainicjuj bazę danych**: `make migrate`
* **Załaduj dokumenty RAG**: `make ingest`

<br>

### 4. Testowanie agentów

Gdy aplikacja jest uruchomiona, możesz wysyłać żądania `curl` do API.

*Uwaga: Poniższe przykłady zakładają, że `auth_guard` w `main.py` jest tymczasowo wyłączony do testów lokalnych.*

* **Przetestuj narzędzie `create_ticket`**:

  ```bash
  curl -X POST http://localhost:8080/v1/agents/run \
    -H "Content-Type: application/json" \
    -d '{"agent": "support", "input": "Mój internet nie działa, proszę utworzyć ticket."}'
  ```
* **Przetestuj RAG (bazę wiedzy)**:

  ```bash
  curl -X POST http://localhost:8080/v1/agents/run \
    -H "Content-Type: application/json" \
    -d '{"agent": "support", "input": "Jak mogę zresetować moje hasło?"}'
  ```

### 5. FAQ – typowe problemy

* **P: Otrzymuję `Connection refused` przy starcie.**
  **O:** Upewnij się, że kontenery zależności są w pełni uruchomione i w stanie `(healthy)` przed startem lokalnego serwera Python. Sprawdź przez `docker ps`.

* **P: Otrzymuję błąd `401 Unauthorized` lub `Missing Bearer`.**
  **O:** Do testów lokalnych możesz tymczasowo wyłączyć zależność `auth_guard` w endpointcie `run_agent` w pliku `src/gateway/main.py`.

* **P: Jak wyświetlić logi dla konkretnej usługi?**
  **O:** Użyj `make logs-api`, `make logs-auditor` lub `docker logs -f <nazwa_kontenera>`.

<br>

---

## Konfiguracja

### Zmienne środowiskowe

* **DATABASE_URL**: String połączenia PostgreSQL (np. `postgresql://user:pass@host:5432/db`).
* **REDIS_URL**: URI Redis (np. `redis://host:6379/0`).
* **NATS_URL**: Serwer NATS (np. `nats://host:4222`).
* **TICKETS_BASE_URL**: URL do Java adaptera (np. `http://ticket-adapter:8081`).
* **MYSQL_URL**: MySQL JDBC (np. `jdbc:mysql://host:3306/db?useSSL=false`).
* **OIDC_ISSUER**: Issuer OIDC (np. `https://your-issuer.com/`).
* **OIDC_AUDIENCE**: Odbiorca JWT.
* **OIDC_JWKS_URL**: URL do JWKS (np. `https://your-issuer.com/.well-known/jwks.json`).

Pełna lista w `.env.example`.

<br>

### Uwierzytelnianie OIDC/JWT

* Włączone w API Gateway i Java Adapter.
* Użyj tokenu Bearer w żądaniach: `Authorization: Bearer <token>`.
* Walidacja: Issuer, audience, sygnatura via JWKS.
* W Admin Portal: Użyj Auth0 lub podobnego dostawcy tożsamości dla front-channel flow (przepływu uwierzytelniania przez przeglądarkę).

<br>

### Polityki RBAC

* Role z claims JWT (np. `"roles": ["sre"]`).
* Narzędzia (np. `restart_service`) sprawdzają role via `require_role(claims, "sre")`.
* Dostosuj w `runtime/policy.py` i narzędziach (np. `REQUIRED_ROLE_RESTART`).

<br>

## Użycie

Podstawowym sposobem interakcji z AstraDesk jest jego REST API.

<br>

### Uruchamianie agentów

Aby wykonać agenta, wyślij żądanie `POST` do endpointu `/v1/agents/run`:

```sh
curl -X POST http://localhost:8080/v1/agents/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <twój-token-jwt>" \
  -d '{"agent": "support", "input": "Utwórz ticket dla incydentu sieciowego", "meta": {"user": "alice"}}'
```

Odpowiedź będzie obiektem JSON zawierającym wyjście agenta i `reasoning_trace_id`.

<br>

### Portal administracyjny

Webowy Portal Administracyjny, dostępny pod adresem `http://localhost:3000`, zapewnia interfejs UI do monitorowania kondycji systemu i zarządzania komponentami platformy zgodnie z [specyfikacją OpenAPI](openapi/astradesk-admin.v1.yaml).

<br>

---

## Wdrożenie

### Kubernetes (Helm)

1. Zbuduj i wypchnij obrazy (użyj CI).

2. Zainstaluj chart:

   ```sh
   helm upgrade --install astradesk deploy/chart -f deploy/chart/values.yaml \
     --set image.tag=0.3.0 \
     --set autoscaling.enabled=true
   ```

   - **HPA:** Skaluje przy CPU >60%.

<br>

### OpenShift

**Przetwórz szablon:**

   ```sh
   oc process -f deploy/openshift/astradesk-template.yaml -p TAG=0.3.0 | oc apply -f -
   ```

<br>

### AWS (Terraform)

**Zainicjuj:**

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

* Uruchom pipeline: `Jenkinsfile` buduje/testuje/wypycha obrazy, wdraża przez Helm.

### GitLab CI

* `.gitlab-ci.yml`: Etapy build/test/docker/deploy (manual).

<br>

---

## Monitorowanie i obserwowalność 

**(Prometheus, Grafana, OpenTelemetry)**

Ta sekcja opisuje, jak włączyć pełną obserwowalność platformy AstraDesk z użyciem **Prometheus** (metryki), **Grafana** (dashboardy) i **OpenTelemetry** (instrumentacja).

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
```

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
          summary: "API – wysoki wskaźnik błędów 5xx (>5% przez 10 min)"
          description: "Zbadaj logi FastAPI gateway i zależności upstream."

      - alert: TicketAdapterDown
        expr: up{job="ticket-adapter"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Ticket Adapter jest niedostępny"
          description: "Serwis Spring nie odpowiada na /actuator/prometheus."
```

> **Przeładuj konfigurację** bez restartu:
> `curl -X POST http://localhost:9090/-/reload`

<br>

### Endpointy metryk – integracje

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
    "Łączna liczba żądań HTTP",
    ["method", "path", "status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Czas trwania żądania HTTP",
    ["method", "path"]
)

@router.get("/metrics")
def metrics():
    # Wystaw metryki Prometheus w formacie tekstowym
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
app.include_router(metrics_router, tags=["obserwowalność"])
```

> **Alternatywa (zalecana)**: użyj **OpenTelemetry** + eksportera `otlp`, a następnie zbieraj metryki przez **otel-collector** → Prometheus. Ta opcja zapewnia spójne metryki, ślady i logi.

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

1. **Dodaj źródło danych → Prometheus**
   URL: `http://prometheus:9090` (z perspektywy sieci Docker Compose) lub `http://localhost:9090` (jeśli dodajesz ręcznie z hosta).
2. **Zaimportuj dashboard** (np. „Prometheus / Overview" albo własny).
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
	docker compose up -d prometheus grafana

down-observability:
	docker compose rm -sfv prometheus grafana

logs-prometheus:
	docker logs -f astradesk-prometheus

logs-grafana:
	docker logs -f astradesk-grafana
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
* Pokrycie: Testy jednostkowe (pytest, JUnit, Vitest), testy integracyjne (przepływy API).

<br>

---

## Bezpieczeństwo

* **Auth**: OIDC/JWT z JWKS.
* **RBAC**: Per narzędzie, na bazie claims.
* **mTLS**: STRICT via Istio.
* **Audyt**: W Postgres + publikacja NATS.
* **Polityki**: Allow-lists w narzędziach, ponawianie w proxy.

<br>

---

## Mapa drogowa

* Integracja LLM (Bedrock/OpenAI/vLLM) z mechanizmami zabezpieczającymi.
* Temporal dla długotrwałych workflowów.
* Ewaluacje RAG (Ragas).
* Multi-tenancy i zaawansowany RBAC (OPA).
* Pełne dashboardy Grafana z alertami.

<br>

---

## Wkład

* Fork repo, stwórz branch, PR z testami.
* Użyj `make lint/type` przed commit.

<br>

---

## Licencja

Apache License 2.0. Zobacz [LICENSE](LICENSE) po szczegóły.

---

<br>

## Kontakt

🌐 Strona WWW: [AstraDesk](https://www.astradesk.dev)

📧 Autor: Siergej Sobolewski ([s.sobolewski@hotmail.com](mailto:s.sobolewski@hotmail.com)).

💬 Kanały wsparcia: [Support Slack](https://astradesk.slack.com)

🐙 Issues: [GitHub Issues](https://github.com/SSobol77/astradesk/issues).

<br>

---

*Ostatnia aktualizacja: 2026-04-09*
