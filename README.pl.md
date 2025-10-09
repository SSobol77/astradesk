<p align="center">
  <img src="assets/AstraDesktop.png" alt="AstraDesk - Framework AI" width="560"/>
</p>

<br>

# AstraDesk Duo - Internal AI Agents Framework

[![License](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Python Version](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![JDK Version](https://img.shields.io/badge/JDK-21-green.svg)](https://openjdk.org/projects/jdk/21/)
[![Node.js Version](https://img.shields.io/badge/Node.js-22-brightgreen.svg)](https://nodejs.org/en)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](https://github.com/your-org/astradesk/actions)


**Języki:** [Polski](README.pl.md) | [English](README.md)

<br>

[AstraDesk](https://astradesk.vercel.app/)
 to wewnętrzny framework do budowy agentów AI, zaprojektowany dla działów wsparcia (Support) i operacji (SRE/DevOps). Oferuje modularną architekturę z gotowymi agentami demonstracyjnymi, integracjami z bazami danych, systemami messagingu i narzędziami DevOps. Framework wspiera skalowalność, bezpieczeństwo enterprise (OIDC/JWT, RBAC, mTLS via Istio) oraz pełne CI/CD.

## Spis treści

- [Funkcje](#funkcje)
- [Przeznaczenie i Zastosowania](#przeznaczenie-i-zastosowania)
- [Przegląd architektury](#przegląd-architektury)
- [Wymagania wstępne](#wymagania-wstępne)
- [Instalacja](#instalacja)
  - [Lokalne środowisko (Docker Compose)](#lokalne-środowisko-docker-compose)
  - [Budowanie ze źródeł](#budowanie-ze-źródeł)
- [Konfiguracja](#konfiguracja)
  - [Zmienne środowiskowe](#zmienne-środowiskowe)
  - [Uwierzytelnianie OIDC/JWT](#uwierzytelnianie-oidcjwt)
  - [Polityki RBAC](#polityki-rbac)
- [Użycie](#użycie)
  - [Uruchamianie agentów](#uruchamianie-agentów)
  - [Wczytywanie dokumentów do RAG](#wczytywanie-dokumentów-do-rag)
  - [Portal administracyjny](#portal-administracyjny)
  - [Narzędzia i integracje](#narzędzia-i-integracje)
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
  - [OpenTelemetry](#opentelemetry)
  - [Pulpity i alerty Grafany](#pulpity-i-alerty-grafany)
- [Przewodnik dla deweloperów](#przewodnik-dla-deweloperów)
- [Testowanie](#testowanie)
- [Bezpieczeństwo](#bezpieczeństwo)
- [Mapa drogowa](#mapa-drogowa)
- [Wkład](#wkład)
- [Licencja](#licencja)
- [Kontakt](#kontakt)

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

## Przeznaczenie i Zastosowania

**AstraDesk** to **framework do budowy agentów AI** dla zespołów **Support** oraz **SRE/DevOps**.
Zapewnia modułowy rdzeń (planer, pamięć, RAG, rejestr narzędzi) i gotowe agentowe przykłady.

- **Support / Helpdesk**: RAG na dokumentach firmy (procedury, FAQ, runbooki), tworzenie/aktualizacja zgłoszeń (tickety), pamięć konwersacji.
- **Automatyzacje SRE/DevOps**: odczyt metryk (Prometheus/Grafana), triage incydentów, kontrolowane akcje (np. restart usługi) zabezpieczone **RBAC** i objęte audytem.
- **Integracje enterprise**: Gateway (Python/FastAPI), Adapter Ticketów (Java/WebFlux + MySQL), Portal Admin (Next.js) oraz warstwa danych (Postgres/pgvector, Redis, NATS).
- **Bezpieczeństwo i compliance**: OIDC/JWT, RBAC per‑narzędzie, **mTLS** (Istio), pełen ślad audytowy.
- **Operacje na skalę**: Docker/Kubernetes/OpenShift, Terraform (AWS), CI/CD (Jenkins/GitLab), obserwowalność (OpenTelemetry, Prometheus/Grafana/Loki/Tempo).

> **To nie pojedynczy chatbot**, lecz **framework** do komponowania własnych agentów, narzędzi i polityk z pełną kontrolą (bez lock‑in do SaaS).

## Przegląd architektury

AstraDesk składa się z trzech głównych komponentów:
- **Python API Gateway**: FastAPI obsługujący żądania do agentów, z RAG, pamięcią i toolami.
- **Java Ticket Adapter**: Reaktywny serwis (WebFlux) integrujący z MySQL dla ticketingu.
- **Next.js Admin Portal**: Interfejs webowy do monitoringu.

Komunikacja: HTTP (między komponentami), NATS (eventy/audyty), Redis (pamięć robocza), Postgres/pgvector (RAG/dialogi/audyty), MySQL (tickety).

## Wymagania wstępne

- **Docker** i **Docker Compose** (do lokalnego dev).
- **Kubernetes** z Helm (do deploymentu).
- **AWS CLI** i **Terraform** (do chmury).
- **Node.js 22**, **JDK 21**, **Python 3.11** (do buildów).
- **Postgres 16**, **MySQL 8**, **Redis 7**, **NATS 2** (serwisy bazowe).
- **Opcjonalnie:** Istio, cert-manager (do mTLS/TLS).

## Instalacja

### Lokalne środowisko (Docker Compose)

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

### Budowanie ze źródeł

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

## Konfiguracja

### Zmienne środowiskowe

- **DATABASE_URL**: PostgreSQL connection string (np. `postgresql://user:pass@host:5432/db`).
- **REDIS_URL**: Redis URI (np. `redis://host:6379/0`).
- **NATS_URL**: NATS server (np. `nats://host:4222`).
- **TICKETS_BASE_URL**: URL do Java adaptera (np. `http://ticket-adapter:8081`).
- **MYSQL_URL**: MySQL JDBC (np. `jdbc:mysql://host:3306/db?useSSL=false`).
- **OIDC_ISSUER**: Issuer OIDC (np. `https://your-issuer.com/`).
- **OIDC_AUDIENCE**: Audience JWT.
- **OIDC_JWKS_URL**: URL do JWKS (np. `https://your-issuer.com/.well-known/jwks.json`).

Pełna lista w `.env.example`.

### Uwierzytelnianie OIDC/JWT

- Włączone w API Gateway i Java Adapter.
- Użyj Bearer token w requestach: `Authorization: Bearer <token>`.
- Walidacja: Issuer, audience, signature via JWKS.
- W Admin Portal: Użyj Auth0 lub podobnego do front-channel flow.

### Polityki RBAC

- Role z JWT claims (np. "roles": ["sre"]).
- Narzędzia (np. restart_service) sprawdzają role via `require_role(claims, "sre")`.
- Dostosuj w `runtime/policy.py` i toolach (np. `REQUIRED_ROLE_RESTART`).

## Użycie

### Uruchamianie agentów

Wywołaj API:

```sh
curl -X POST http://localhost:8080/v1/agents/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{"agent": "support", "input": "Utwórz ticket dla incydentu sieci", "meta": {"user": "alice"}}'
```

- Response: JSON z outputem, trace_id, used_tools.
- Demo queries: `./scripts/demo_queries.sh`.

### Wczytywanie dokumentów do RAG

- Wspierane formaty: .md, .txt (rozszerzalne o PDF/HTML).
- Uruchom: `make ingest` (źródło: `./docs`).

### Portal administracyjny

- Dostępny na `http://localhost:3000`.
- Funkcje: Health check API, przykładowe curl do agentów.
- Rozszerz o fetch audytów: Dodaj endpoint `/v1/audits` w API.

### Narzędzia i integracje

- Rejestr tooli: `registry.py` – dodaj nowe via `register(name, async_fn)`.
- Przykłady: create_ticket (proxy do Java), get_metrics (stub Prometheus), restart_service (z RBAC).

## Wdrożenie

### Kubernetes (Helm)

1. Zbuduj i push obrazy (użyj CI).
2. Zainstaluj chart:

   ```sh
   helm upgrade --install astradesk deploy/chart -f deploy/chart/values.yaml \
     --set image.tag=0.2.1 \
     --set autoscaling.enabled=true
   ```

   - HPA: Skaluje na CPU >60%.

### OpenShift

1. Procesuj template:

   ```sh
   oc process -f deploy/openshift/astradesk-template.yaml -p TAG=0.2.1 | oc apply -f -
   ```

### AWS (Terraform)

1. Inicjuj:

   ```sh
   cd infra
   terraform init
   terraform apply -var="region=us-east-1" -var="project=astradesk"
   ```

   - Tworzy: VPC, EKS, RDS (Postgres/MySQL), S3.

### Narzędzia zarządzania konfiguracją

- **Ansible**: `ansible-playbook -i ansible/inventories/dev/hosts.ini ansible/roles/astradesk_docker/main.yml`.
- **Puppet**: `puppet apply puppet/manifests/astradesk.pp`.
- **Salt**: `salt '*' state.apply astradesk`.

### mTLS i siatka usług Istio

1. Utwórz namespace: `kubectl apply -f deploy/istio/00-namespace.yaml`.
2. Włącz mTLS: `kubectl apply -f deploy/istio/10-peer-authentication.yaml` (i resztę plików z deploy/istio/).
3. Gateway: HTTPS na port 443 z cert-manager.

## CI/CD

### Jenkins

- Uruchom pipeline: `Jenkinsfile` buduje/testuje/pushuje obrazy, deployuje Helm.

### GitLab CI

- `.gitlab-ci.yml`: Etapy build/test/docker/deploy (manual).

## Monitorowanie i obserwowalność

### OpenTelemetry

- Wbudowane w FastAPI (instrumentation).
- Eksport: Do OTLP (Prometheus/Grafana).

### Pulpity i alerty Grafany

- Dashboard: `grafana/dashboard-astradesk.json` (latency, DB calls).
- Alerty: `grafana/alerts.yaml` (high latency, errors) – załaduj do Prometheus.

<br>

## Przewodnik dla deweloperów

Ta sekcja zawiera praktyczne instrukcje i odpowiedzi na najczęstsze pytania, które pomogą Ci szybko rozpocząć pracę z projektem.

### 1. Podstawowa Konfiguracja Środowiska

Zanim zaczniesz, upewnij się, że masz:
- **Docker** i **Docker Compose** (rekomendowany Docker Desktop).
- **Git**, **make** oraz **Node.js** (v22+) zainstalowane lokalnie.

Kroki przygotowawcze (wykonaj je tylko raz):

1.  **Sklonuj repozytorium**:
    ```bash
    git clone https://github.com/your-org/astradesk.git
    cd astradesk
    ```
2.  **Skopiuj plik konfiguracyjny**:
    ```bash
    cp .env.example .env
    ```
3.  **Wygeneruj `package-lock.json`**: Jest to wymagane do budowy obrazu Docker dla portalu admina.
    ```bash
    cd services/admin-portal && npm install && cd ../..
    ```

### 2. Jak Uruchomić Aplikację?

Masz do wyboru dwa tryby pracy, w zależności od Twoich potrzeb.

#### **Tryb A: Pełne Środowisko Docker (Zalecane)**

Uruchamia **całą aplikację** (wszystkie mikroserwisy) w kontenerach Docker. Idealne do testów integracyjnych i symulacji środowiska produkcyjnego.

- **Jak uruchomić?**
  ```bash
  make up
  ```
  *(Alternatywnie: `docker compose up --build -d`)*

- **Jak zatrzymać i wyczyścić?**
  ```bash
  make down
  ```
  *(Alternatywnie: `docker compose down -v`)*

- **Dostępne serwisy**:
  - **API Gateway**: `http://localhost:8080`
  - **Admin Portal**: `http://localhost:3000`
  - **Ticket Adapter**: `http://localhost:8081`

<br>

#### **Tryb B: Development Hybrydowy (do pracy nad Pythonem)**

Uruchamia **tylko zewnętrzne zależności** (bazy danych, NATS, etc.) w Dockerze, a główny **serwer API w Pythonie działa lokalnie**. Idealne do szybkiego developmentu i debugowania kodu Pythona z natychmiastowym przeładowaniem.

1.  **Krok 1: Uruchom zależności w Dockerze** (w jednym terminalu):
    ```bash
    make up-deps
    ```
    *(Alternatywnie: `docker compose up -d db mysql redis nats ticket-adapter`)*

2.  **Krok 2: Uruchom serwer API lokalnie** (w drugim terminalu):
    ```bash
    make run-local
    ```
    *(Alternatywnie: `python -m uvicorn src.gateway.main:app --host 0.0.0.0 --port 8080 --reload --app-dir src`)*

### 3. Jak Testować?

`Makefile` dostarcza proste komendy do uruchamiania testów.

- **Jak uruchomić wszystkie testy?**
  ```bash
  make test-all
  ```
- **Jak uruchomić tylko testy dla Pythona?**
  ```bash
  make test
  ```
- **Jak uruchomić tylko testy dla Javy?**
  ```bash
  make test-java
  ```
- **Jak uruchomić tylko testy dla Admin Portalu?**
  ```bash
  make test-admin
  ```

### 4. Jak Pracować z Bazą Danych i RAG?

- **Jak zainicjować bazę danych (stworzyć rozszerzenie `pgvector`)?**
  *Uwaga: Jeśli używasz `docker-compose.deps.yml`, ten krok nie jest potrzebny.*
  ```bash
  make migrate
  ```

- **Jak zasilić bazę wiedzy RAG?**

  1.  Dodaj swoje pliki `.md` lub `.txt` do katalogu `docs/`.

  2.  Uruchom komendę:
      ```bash
      make ingest
      ```

### 5. Jak Sprawdzić Działanie Agentów?

Po uruchomieniu aplikacji (w dowolnym trybie), możesz wysyłać zapytania do API za pomocą `curl`.

*Uwaga: Poniższe przykłady zakładają, że autoryzacja (`auth_guard` w `main.py`) jest tymczasowo wyłączona na potrzeby testów.*

- **Test narzędzia `create_ticket`**:
  ```bash
  curl -X POST http://localhost:8080/v1/agents/run \
    -H "Content-Type: application/json" \
    -d '{"agent": "support", "input": "Mój internet nie działa, proszę utworzyć zgłoszenie."}'
  ```
- **Test narzędzia `get_metrics`**:
  ```bash
  curl -X POST http://localhost:8080/v1/agents/run \
    -H "Content-Type: application/json" \
    -d '{"agent": "ops", "input": "Pokaż mi metryki dla usługi webapp"}'
  ```
- **Test RAG (baza wiedzy)**:
  ```bash
  curl -X POST http://localhost:8080/v1/agents/run \
    -H "Content-Type: application/json" \
    -d '{"agent": "support", "input": "Jak mogę zresetować hasło?"}'
  ```

### 6. FAQ - Typowe Problemy i Pytania

- **P: Dostaję błąd `Connection refused` podczas startu aplikacji.**
  - **O:** Najprawdopodobniej próbujesz uruchomić serwer API (`make run-local`) zanim kontenery z zależnościami (`make up-deps`) w pełni wystartowały. Upewnij się, że komenda `docker ps` pokazuje status `(healthy)` dla kontenerów `db`, `mysql` i `redis` zanim uruchomisz Pythona.

- **P: Dostaję błąd `{"detail":"Brak nagłówka autoryzacyjnego Bearer."}`.**
  - **O:** To znaczy, że `auth_guard` w `src/gateway/main.py` jest włączony. Do testów lokalnych, zakomentuj linię `claims: dict[str, Any] = Depends(auth_guard),` w definicji endpointu `run_agent` i przekaż pusty słownik `{}` jako `claims` do `orchestrator.run`.

- **P: Jak mogę zobaczyć logi konkretnego serwisu?**
  - **O:** Użyj komendy `docker logs`. Na przykład, aby zobaczyć logi `Auditora` na żywo:
    ```bash
    docker logs -f astradesk-auditor-1
    ```
    *(Nazwa kontenera może się nieznacznie różnić - sprawdź ją za pomocą `docker ps`)*.

- **P: Jak mogę przebudować tylko jeden obraz Docker?**
  - **O:** Użyj flagi `--build` z nazwą serwisu:
    ```bash
    docker compose up -d --build api
    ```

- **P: Gdzie mogę zmienić słowa kluczowe dla `KeywordPlanner`?**
  - **O:** W pliku `src/runtime/planner.py`, wewnątrz konstruktora `__init__` klasy `KeywordPlanner`.

<br>

## Testowanie

- Uruchom: `make test` (Python), `make test-java`, `make test-admin`.
- Pokrycie: Unit (pytest, JUnit, Vitest), integracyjne (API flow).

## Bezpieczeństwo

- **Auth**: OIDC/JWT z JWKS.
- **RBAC**: Per tool, na bazie claims.
- **mTLS**: STRICT via Istio.
- **Audyt**: W Postgres + NATS publish.
- **Polityki**: Allow-lists w toolach, retries w proxy.

## Mapa drogowa

- Integracja LLM (Bedrock/OpenAI/vLLM) z guardrails.
- Temporal dla długotrwałych workflowów.
- Ewaluacje RAG (Ragas).
- Multi-tenancy i RBAC advanced (OPA).
- Pełne dashboardy Grafana z alertami.

## Wkład

- Fork repo, stwórz branch, PR z testami.
- Użyj `make lint/type` przed commit.

## Licencja

Apache License 2.0. See [LICENSE](LICENSE) for details.

## Kontakt

Web site:[ AstraDesk](https://astradesk.vercel.app/)

Autor: Siergej Sobolewski (s.sobolewski@hotmail.com).  

Issues: [GitHub Issues](https://github.com/SSobol77/astradesk/issues).  

<br>

---
*Ostatnia aktualizacja: 2025-10-10*