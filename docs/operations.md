<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: docs/operations.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# Operacje / DevOps - AstraDesk

Kompletny przewodnik uruchomieniowy i operacyjny dla zespołów Dev, DevOps oraz SRE. Dokument obejmuje: lokalny development, obrazy i kontenery, deployment do Kubernetes/Helm (z meshem), observability, CI/CD, bezpieczeństwo, backup/DR, runbook incydentów oraz checklisty.

<br>

---

## 1) Wymagania wstępne

- **Repozytorium**: `astradesk` (GitHub/GitLab), gałąź `main`.

- **Narzędzia lokalne**: `docker`, `docker compose`, `make`, `python 3.11+`, `node 18+`, `helm 3`, `kubectl`, `jq`, `yq`, `uv` (opcjonalnie) lub `pip`/`poetry`.

- **Dostępy**:
  - rejestr obrazów (GHCR/ECR/GCR),
  - klaster Kubernetes (dev/stage/prod) z ingress + (opcjonalnie) Istio/Linkerd,
  - dostęp do tajemnic (K8s Secrets / AWS Secrets Manager / Vault),
  - S3 (bucket dla audytów), Elasticsearch (opcjonalnie),
  - Postgres (RDS / lokalny), Redis (ElastiCache / lokalny), NATS.

<br>

---

## 2) Zmienne środowiskowe (ENV)

| Zmienna              | Opis                                        | Przykład                                                                    |
|----------------------|---------------------------------------------|-----------------------------------------------------------------------------|
| `DATABASE_URL`       | DSN Postgres                                | `postgresql://user:pass@pg:5432/astradesk`                                 |
| `REDIS_URL`          | Redis                                       | `redis://redis:6379/0`                                                      |
| `NATS_URL`           | NATS                                        | `nats://nats:4222`                                                          |
| `OIDC_ISSUER`        | OIDC issuer                                 | `https://idp.example.com/realms/main`                                       |
| `OIDC_AUDIENCE`      | API audience                                | `astradesk-api`                                                             |
| `OIDC_JWKS_URL`      | JWKS endpoint                               | `https://idp.example.com/realms/main/protocol/openid-connect/certs`         |
| `API_VERSION`        | Wersja API                                  | `1.0.0`                                                                     |
| `LOG_LEVEL`          | Poziom logów                                | `INFO` / `DEBUG`                                                            |
| `AUDIT_MODE`         | Sink audytu side-effect (ISSUE 019/039): `jsonl` (domyślny, plik JSON-Lines) lub `jetstream` (trwały NATS JetStream) | `jsonl` |
| `AUDIT_LOG_PATH`     | Ścieżka pliku JSON-Lines, wymagana na warstwach wdrożeniowych gdy `AUDIT_MODE=jsonl` | `/var/log/astradesk/audit.jsonl` |
| `S3_BUCKET`          | Bucket S3, do którego usługa `auditor` zapisuje partie zdarzeń audytu | `astradesk-audit-dev`                                                       |
| `ES_URL`             | URL Elasticsearch                            | `http://elasticsearch:9200`                                                 |
| `ES_INDEX`           | Indeks audytu                               | `astradesk-audit`                                                           |
| `MODEL_PROVIDER`     | Dostawca LLM                                | `bedrock` / `openai` / `vllm`                                               |
| `OPENAI_API_KEY`     | Klucz do OpenAI (jeśli wybrano `openai`)    | `***`                                                                       |
| `BEDROCK_REGION`     | Region AWS Bedrock                          | `eu-central-1`                                                              |
| `BEDROCK_MODEL`      | Domyślny model (Bedrock)                    | `anthropic.claude-3-5-sonnet-20240620-v1:0`                                 |
| `VLLM_URL`           | Endpoint lokalnego vLLM                      | `http://vllm:8000`                                                          |

> Sekrety przechowuj w Secret Manager/Vault, nie w `.env` (prod).

<br>

---

## 3) Development lokalny (Docker Compose)

```bash
# 1) uruchom stack developerski
docker compose up -d --build

# 2) migracje bazy (pgvector + tabele)
make migrate

# 3) ingest dokumentów do RAG (katalog ./docs)
make ingest

# 4) smoke testy
curl -s localhost:8080/healthz
curl -s -X POST localhost:8080/v1/agents/run \
  -H "authorization: Bearer <JWT>" \
  -H "content-type: application/json" \
  -d '{"agent":"support","input":"Utwórz ticket dla incydentu sieci","tool_calls":[],"meta":{"user":"alice"}}'
```

### Makefile - najważniejsze cele

```Makefile
.PHONY: sync lint type test build migrate ingest up down

sync:
	uv sync --frozen

lint:
	uv run ruff check src

type:
	uv run mypy src

test:
	uv run pytest -q

build-java:
	cd services/ticket-adapter-java && ./gradlew bootJar

build-js:
	cd services/admin-portal && npm ci && npm run build

build: sync build-java build-js

migrate:
	psql "$$DATABASE_URL" -f migrations/0001_init_pgvector.sql && \
	psql "$$DATABASE_URL" -f migrations/0002_tables.sql

ingest:
	uv run python scripts/ingest_docs.py ./docs

up:
	docker compose up -d --build

down:
	docker compose down -v
```

<br>

---

## 4) Baza danych i migracje

- **Postgres 17 + pgvector**: wymagane rozszerzenie `pgvector`.
- Pliki migracji:
  - `migrations/0001_init_pgvector.sql` - `CREATE EXTENSION IF NOT EXISTS vector;`
  - `migrations/0002_tables.sql` - `dialogues`, `audits`, `documents`.
- Dla prod: użyj narzędzia migracyjnego (np. `golang-migrate`, `alembic`) w Jobie K8s.

Przykład `0002_tables.sql` (skrót):

```sql
CREATE TABLE IF NOT EXISTS dialogues (
  id BIGSERIAL PRIMARY KEY,
  agent TEXT NOT NULL,
  query TEXT NOT NULL,
  answer TEXT NOT NULL,
  meta JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audits (
  id BIGSERIAL PRIMARY KEY,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS documents (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL,
  chunk TEXT NOT NULL,
  embedding VECTOR(384) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS documents_embedding_idx ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

<br>

---

## 5) Ingest danych RAG

- Skrypt: `scripts/ingest_docs.py <dir>` - tnie pliki (`.md`, `.txt`) na chunki, embeduje i zapisuje do `documents`.
- Model embeddingów: `sentence-transformers/all-MiniLM-L6-v2` (domyślnie).
- Zalecenia:
  - chunk ~ 400–600 znaków, overlap 50–100,
  - filtruj metadane (źródło, tagi), waliduj kodowanie UTF-8.

<br>

---

## 6) Budowanie i wersjonowanie obrazów

- Tagowanie obrazów: `registry/org/astradesk-<svc>:<git-sha>` oraz `:latest` na dev.
- SBOM i skan podatności:
  ```bash
  syft packages --output syft-json . > sbom.json
  grype sbom:sbom.json --fail-on high
  ```
- Multi-arch (opcjonalnie): `docker buildx build --platform linux/amd64,linux/arm64 ...`

<br>

---

## 7) Kubernetes / Helm - wdrożenie

### 7.1 Przygotowanie
- Zaloguj się do rejestru i wypchnij obrazy (`docker push`).
- Uzupełnij `deploy/chart/values.yaml` (obrazy, env, secrets).

### 7.2 Instalacja / aktualizacja

```bash
helm upgrade --install astradesk deploy/chart -f deploy/chart/values.yaml --namespace astradesk --create-namespace
```

### 7.3 HPA (autoscaling)

- `autoscaling/v2`, target CPU ~60% (przykład w chart).
- Pamiętaj o `resources.requests/limits` oraz `readiness/liveness`.

### 7.4 Service Mesh (mTLS)

**Istio PeerAuthentication (STRICT):**
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: astradesk-peer-auth
  namespace: astradesk
spec:
  mtls:
    mode: STRICT
```

**DestinationRule (ISTIO_MUTUAL):**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: astradesk-api
  namespace: astradesk
spec:
  host: astradesk-api.astradesk.svc.cluster.local
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
```

### 7.5 Sekrety i konfiguracja

- K8s Secret: klucze API, DSN bazy, URL-e prywatne.
- Alternatywa: AWS Secrets Manager / HashiCorp Vault (operator do K8s).
- **Nie** commitujemy sekretów do repo.

<br>

---

## 8) Model Gateway - dostawcy i guardrails

- Providerzy: **AWS Bedrock**, **OpenAI**, **vLLM** (on-prem).
- Guardrails:
  - **blocklist** fraz (regexy) dla promptów planera,
  - limit długości promptu i odpowiedzi (tokeny),
  - walidacja **JSON Schema** wyników planera (lista kroków narzędziowych).
- Retry/backoff wg wyjątków: `ProviderTimeout`, `ProviderOverloaded`, `ProviderServerError` (parsowanie `Retry-After`, heurystyki).

<br>

---

## 9) Observability (OTel + Prometheus/Grafana + Loki + Traces)

- **Metrics**: eksport z FastAPI/uvicorn + metryki narzędzi, latencje do providerów, liczba 429/5xx oraz backoff.
- **Logs**: strukturalne JSON: `trace_id`, `request_id`, `provider`, `status`, `tool`, `agent`.
- **Traces**: span’y: weryfikacja JWT, planowanie, narzędzia, RAG, provider LLM.

### Grafana
- Dashboard: `grafana/dashboard-astradesk.json`
- Alerty: P95 latency, 5xx rate, spike 429, brak zdarzeń audytu.

<br>

---

## 10) NATS Auditor - subskrybent audytu

Sink audytu side-effect (`write`/`execute`) wybiera zmienna `AUDIT_MODE`
ustawiana na `api-gateway` (ISSUE 019/039):

- **`AUDIT_MODE=jsonl` (domyślny)**: append-only plik JSON-Lines
  (`AUDIT_LOG_PATH`). Wymagany na warstwach wdrożeniowych
  (`ENVIRONMENT` ∈ `production`/`prod`/`staging`/`stage`) - start usługi
  przerywa się (`AuditConfigError`), jeśli ścieżka nie jest ustawiona. Poza
  warstwami wdrożeniowymi dopuszczalny jest nietrwały writer in-proces (z
  ostrzeżeniem w logu).
- **`AUDIT_MODE=jetstream` (jawny opt-in, tryb trwały produkcyjny)**: zdarzenie
  audytu jest publikowane do trwałego strumienia NATS JetStream; wywołanie
  narzędzia z efektem ubocznym kończy się sukcesem **dopiero po**
  potwierdzeniu trwałego zapisu przez broker (ack-after-durable-write). Brak
  potwierdzenia (broker niedostępny, timeout) po ograniczonej liczbie prób
  (`AUDIT_PUBLISH_RETRIES`) i próbie zapisu do DLQ kończy wywołanie
  narzędzia odmową (fail-closed) — na każdej warstwie, nie tylko produkcyjnej.

Usługa `auditor` (`services/auditor`) konsumuje z JetStream jako **trwały
konsument typu pull** (`AckPolicy.EXPLICIT`) i potwierdza (ack) partię
zdarzeń dopiero **po** trwałym zapisie do obu magazynów:

- **Elasticsearch** (`ES_INDEX`, dokument `_id` = `event_id` - idempotentny
  zapis przy redelivery),
- **S3** (`S3_BUCKET`, klucz obiektu = skrót SHA-256 posortowanych
  `event_id` w partii - idempotentny zapis przy redelivery).

Awaria zapisu do magazynu po ograniczonej liczbie prób
(`AUDIT_SINK_RETRIES`) kieruje partię do tematu DLQ
(`AUDIT_JETSTREAM_DLQ_SUBJECT`); oryginalna wiadomość jest potwierdzana
(ack) **dopiero gdy** publikacja do DLQ zostanie potwierdzona przez broker -
w przeciwnym razie pozostaje niepotwierdzona i JetStream dostarczy ją
ponownie (żadne zaakceptowane zdarzenie nie ginie po cichu).

Dowód odzyskiwania po awarii (crash-recovery, na prawdziwym kontenerze NATS
JetStream) oraz pełny opis implementacji:
`audit/evidence/39_jetstream_durable_audit.md` i
`audit/evidence/39_jetstream_crash_recovery_run.txt`.

Przykładowa konfiguracja (ENV), tryb `jetstream` (pełna lista w `.env.example`):
```env
AUDIT_MODE=jetstream
AUDIT_NATS_URL=nats://nats:4222
AUDIT_JETSTREAM_STREAM=ASTRADESK_AUDIT
AUDIT_JETSTREAM_SUBJECT=astradesk.audit
AUDIT_JETSTREAM_DLQ_SUBJECT=astradesk.audit.dlq
AUDIT_PUBLISH_TIMEOUT_MS=2000
AUDIT_PUBLISH_RETRIES=2

# services/auditor (konsument) — AUDIT_JETSTREAM_* muszą być zgodne z powyższymi
AUDIT_JETSTREAM_DURABLE_CONSUMER=astradesk-auditor
AUDIT_FETCH_BATCH_SIZE=100
AUDIT_FETCH_TIMEOUT_SEC=5
AUDIT_SINK_RETRIES=3
AUDIT_SINK_RETRY_BACKOFF_SEC=1
AUDIT_ACK_WAIT_SEC=30
S3_BUCKET=astradesk-audit-dev
ES_URL=http://elasticsearch:9200
ES_INDEX=astradesk-audit
NATS_URL=nats://nats:4222
```

<br>

---

## 11) Bezpieczeństwo

- **OIDC/JWT** (API) - weryfikacja przez JWKS, walidacja `iss`, `aud`, `exp`, `nbf`.
- **RBAC/ABAC** - role z `claims.roles/groups/realm_access.roles`; per-tool `allowed_roles`.
- **mTLS** (mesh) - wymóg **STRICT** między usługami.
- **Sekrety** - Secret Manager/Vault, rotacja kluczy.
- **Rate limiting / QoS** - Envoy/Ingress; zwracaj `429` z `Retry-After`.
- **PII i compliance** - minimalizacja scope’u danych, maskowanie w logach, retencja S3 (WORM jeśli wymagane).

<br>

---

## 12) CI/CD (GitHub Actions / GitLab CI / Jenkins)

### Pipeline (proponowany):
1. **Lint** (`ruff`) + **Type-check** (`mypy`),
2. **Testy** (`pytest`),
3. **Build** obrazów + **SBOM** (`syft`) + **skan** (`grype`),
4. **Push** do rejestru,
5. **Deploy** Helm na środowisko (z `env` parametryzowanymi `values-<env>.yaml`).

Przykładowy szkic GitHub Actions (fragment):
```yaml
name: CI

on:
  push:
    branches: [ "main" ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v1
      - run: uv sync --frozen
      - run: uv run ruff check src
      - run: uv run mypy src
      - run: uv run pytest -q
      - name: Build & push image
        run: |
          docker build -t ghcr.io/org/astradesk-api:${{ github.sha }} -f Dockerfile .
          echo "${{ secrets.GHCR_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin
          docker push ghcr.io/org/astradesk-api:${{ github.sha }}
      - name: Helm deploy
        run: |
          helm upgrade --install astradesk deploy/chart \
            -f deploy/chart/values.yaml \
            --set image.tag=${{ github.sha }} \
            --namespace astradesk --create-namespace
```

<br>

---

## 13) Backup i Disaster Recovery (DR)

- **Postgres**: RDS snapshoty (prod) / `pg_dump` (dev). Test odtwarzania co kwartał.
- **S3**: versioning + **Object Lock** (compliance, WORM). Cykl życia: automatyczna archiwizacja do Glacier.
- **Elasticsearch**: snapshot repo (S3/GCS) - regularne snapshoty indeksów audytu.
- **Runbook DR**: RPO/RTO, kontakt do on-call, kolejność przywracania (DB -> NATS/JetStream -> Auditor).

<br>

---

## 14) Runbook (incydenty i operacje)

### 14.1 5xx/timeouty u dostawcy LLM
- Szukaj wyjątków `ProviderServerError` / `ProviderTimeout` w logach Gateway.
- Zastosuj `suggested_sleep()` i/lub zwiększ backoff.
- Użyj feature-flag “fallback to RAG-only” dla części zapytań.
- Jeśli problem globalny - eskaluj do dostawcy.

### 14.2 429 (rate limits)
- Wyświetl metryki `429` i `retry_after`.
- Adaptuj klienta: throttling/limit RPS, kolejki.
- W razie potrzeby - rozbij workload na mniejsze okna czasowe.

### 14.3 Problemy z audytem
- Narzędzie z efektem ubocznym odmawia wykonania z `AuditConfigError`/`AuditWriteError` -> sprawdź `AUDIT_MODE`; w trybie `jsonl` brak `AUDIT_LOG_PATH` na warstwie wdrożeniowej przerywa start, w trybie `jetstream` niedostępność brokera NATS powoduje fail-closed (to zamierzone zachowanie, nie błąd).
- Brak zdarzeń w ES/S3 (tryb `jetstream`) -> sprawdź konsumenta `astradesk-auditor` (durable pull consumer), lag JetStream, uprawnienia S3/ES oraz temat DLQ (`AUDIT_JETSTREAM_DLQ_SUBJECT`) pod kątem zdarzeń, które wyczerpały ponowienia zapisu do magazynu.
- Auditor loguje strukturalnie (JSON) liczbę zapisów i błędów na poziomie WARNING/ERROR/CRITICAL; brak dedykowanej metryki Prometheus dla błędów sinka/DLQ jest znaną luką (`docs/roadmap/issues/ISSUES_019_durable_audit.md`, sekcja „Limitations”).
- Pełny opis trybów i dowód odzyskiwania po awarii: `audit/evidence/39_jetstream_durable_audit.md`.

### 14.4 Baza danych
- Spadek wydajności -> analiza planów zapytań, indeksy (pgvector `ivfflat`); zwiększ `lists`/`probes` w zależności od potrzeb.
- VACUUM/ANALYZE regularnie; monitoring autovacuum.

<br>

---

## 15) Rozwiązywanie problemów (Troubleshooting)

- `503 Service warming up` -> sprawdź logi startu (połączenia do DB/Redis), zmienne ENV.
- `401 invalid token` -> sprawdź OIDC/JWKS (URL, sieć, DNS), zegar systemowy (skew).
- Narzędzia (tools) odrzucone -> RBAC/roles w claims; włącz logi `AuthorizationError`.
- Brak embeddingów -> model embeddingów, zależności `sentence-transformers`; pamięć/wątek CPU.

<br>

---

## 17) Standard wydania (Release)

- Zasady semver: `MAJOR.MINOR.PATCH` (tag w repo).
- Każde wydanie: changelog, SBOM, wyniki skanu, numer buildu w obrazie.
- Rollout: najpierw `dev` -> `stage` -> `prod` z `helm upgrade` (automatyczne health-checki i rollback).

<br>

---

## 17) Checklisty

### Pre-merge
- [ ] Lint/Type/Test green
- [ ] Uzupełnione `values.yaml` (env)
- [ ] Zaktualizowane migracje (jeśli zmiany DB)
- [ ] Review bezpieczeństwa (sekrety, role tools)

### Post-deploy
- [ ] Health OK (`/healthz`)
- [ ] Brak 5xx/429 spike
- [ ] Audyt zapisywany (S3/ES)
- [ ] Dashboardy aktualne (grafana)

<br>

---

**Kontakt (on-call):** #astradesk-sre @ Slack / rota PagerDuty  
**Właściciel dokumentu:** Zespół AstraDesk SRE / DevOps  
**Wersja:** 1.0.0

<br>
