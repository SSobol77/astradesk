# AstraDesk 0.2.1 - Dokumentacja (`docs/`)

**AstraDesk to wewnętrzny framework do budowy agentów AI z referencyjnymi agentami:**

- **SupportAgent** - RAG na dokumentach firmowych + integracja ticketing,

- **OpsAgent** - metryki + akcje operacyjne egzekwowane politykami (RBAC/ABAC).

Ten katalog zawiera kompletną dokumentację techniczną i operacyjną projektu.

<br>

## Spis treści
- [Zakres i przeznaczenie](#zakres-i-przeznaczenie)
- [Zawartość katalogu](#zawartość-katalogu)
- [Szybki start (DEV)](#szybki-start-dev)
- [Integracja z systemami zewnętrznymi](#integracja-z-systemami-zewnętrznymi)
- [Konfiguracja środowiska (ENV)](#konfiguracja-środowiska-env)
- [Makefile - najważniejsze cele](#makefile--najważniejsze-cele)
- [Docker / Docker Compose](#docker--docker-compose)
- [Kubernetes / Helm (prod/stage)](#kubernetes--helm-prodstage)
- [CI/CD i łańcuch dostaw](#cicd-i-łańcuch-dostaw)
- [Testy (jednostkowe, integracyjne, e2e)](#testy-jednostkowe-integracyjne-e2e)
- [Monitorowanie i operacje](#monitorowanie-i-operacje)
- [Rozwiązywanie problemów (FAQ/Troubleshooting)](#rozwiązywanie-problemów-faqtroubleshooting)
- [Wersjonowanie i wydania](#wersjonowanie-i-wydania)
- [Kontakt i odpowiedzialności](#kontakt-i-odpowiedzialności)

<br>

---

## Zakres i przeznaczenie

Dokumentacja w `docs/` służy jako **jedno źródło prawdy** dla:
- zespołów **Dev/ML/Platform** - jak rozszerzać framework (agenci, narzędzia, RAG, Model Gateway),
- zespołów **SRE/DevOps** - jak budować, wdrażać i monitorować usługę w K8s,
- **bezpieczeństwa** - polityki OIDC/JWT, mTLS, RBAC, audyt, retencja, SBOM.

## Zawartość katalogu

- [`architecture.md`](./architecture.md) - architektura logiczna i przepływy (ASCII diagramy, C4:L1/L2).
- [`api.md`](./api.md) - kontrakty API (Gateway), format żądań i odpowiedzi, przykłady cURL.
- [`operations.md`](./operations.md) - uruchamianie lokalnie i w K8s, CI/CD, runbooki, checklisty.
- [`security.md`](./security.md) - OIDC/JWT, mTLS, RBAC/ABAC, audyt, S3/Elastic, supply chain.

> Wymagania i diagramy bezpieczeństwa są spójne z praktykami: least privilege, zero trust w mesh, SBOM + skan podatności.

<br>

---

## Szybki start (DEV)

1. Uruchom usługi lokalnie:
   ```bash
   docker compose up -d --build
   ```
2. Zastosuj migracje bazy i przygotuj indeks wektorowy:
   ```bash
   make migrate
   ```
3. Załaduj dokumenty do RAG (wrzuć `.md`/`.txt` do katalogu repo `./docs` i uruchom ingest):
   ```bash
   make ingest
   ```
4. Sprawdź zdrowie API:
   ```bash
   curl -s localhost:8080/healthz
   # {"status":"ok"}
   ```
5. Wywołaj agenta (wstaw prawidłowy JWT):
   ```bash
   curl -s -X POST localhost:8080/v1/agents/run \
     -H "authorization: Bearer <JWT>" \
     -H "content-type: application/json" \
     -d '{"agent":"support","input":"Utwórz ticket dla incydentu sieci","tool_calls":[],"meta":{"user":"alice"}}'
   ```

<br>

---

## Integracja z systemami zewnętrznymi

- **Ticketing (tickets_proxy)** - adapter REST/GraphQL (np. Jira/ServiceNow), wspiera idempotency key i retry.
- **Metryki (metrics)** - odczyt z Prometheus/Thanos; opcjonalnie query caching w Redis.
- **Ops actions (ops_actions)** - operacje SRE (restart, scale, feature flags) z twardym RBAC.
- **Model Gateway** - providerzy LLM: AWS Bedrock / OpenAI / on-prem vLLM; guardrails (blocklist, JSON schema dla planera).

> Szczegóły kontraktów i przykłady: zob. [`api.md`](./api.md).

<br>

---

## Konfiguracja środowiska (ENV)

Wybrane zmienne (pełna tabela: [`operations.md`](./operations.md)):

| Zmienna          | Opis                       | Przykład |
|------------------|----------------------------|----------|
| `DATABASE_URL`   | Postgres (DSN)             | `postgresql://user:pass@pg:5432/astradesk` |
| `REDIS_URL`      | Redis                      | `redis://redis:6379/0` |
| `NATS_URL`       | NATS                       | `nats://nats:4222` |
| `OIDC_ISSUER`    | OIDC issuer                | `https://idp.example.com/realms/main` |
| `OIDC_AUDIENCE`  | Audience API               | `astradesk-api` |
| `OIDC_JWKS_URL`  | JWKS endpoint              | `https://idp.example.com/.../certs` |
| `MODEL_PROVIDER` | Dostawca modelu LLM        | `bedrock` / `openai` / `vllm` |
| `LOG_LEVEL`      | Poziom logów               | `INFO` / `DEBUG` |

Sekrety trzymaj w **K8s Secret**/**Vault**/**AWS Secrets Manager** (prod).

<br>

---

## Makefile - najważniejsze cele

```Makefile
.PHONY: sync lint type test build migrate ingest up down

sync:          ## Zainstaluj zależności (uv/poetry/pip) w trybie zablokowanym
	uv sync --frozen

lint:          ## Lint (ruff)
	uv run ruff check src

type:          ## Type-check (mypy)
	uv run mypy src

test:          ## Testy jednostkowe/integracyjne
	uv run pytest -q

build-java:    ## Zbuduj adapter ticketów (Java/Spring)
	cd services/ticket-adapter-java && ./gradlew bootJar

build-js:      ## Zbuduj portal (Next.js)
	cd services/admin-portal && npm ci && npm run build

build: sync build-java build-js

migrate:       ## Migracje DB (pgvector + tabele)
	psql "$$DATABASE_URL" -f migrations/0001_init_pgvector.sql && \
	psql "$$DATABASE_URL" -f migrations/0002_tables.sql

ingest:        ## Ingest dokumentów do RAG
	uv run python scripts/ingest_docs.py ./docs

up:            ## Uruchom docker compose
	docker compose up -d --build

down:          ## Zatrzymaj i usuń wolumeny
	docker compose down -v
```

<br>

---

## Docker / Docker Compose

- Plik `docker-compose.yml` zawiera: `api-gateway`, `postgres`, `redis`, `nats`, (opcjonalnie) `auditor` i `vllm` dev.
- Persistent storage (dev): wolumeny Dockera; prod - RDS/EBS/S3.
- Build lokalny: `docker compose build` - tagi `:dev`, `:latest` (dev).

<br>

---

## Kubernetes / Helm (prod/stage)

- Obrazy push do rejestru (`ghcr.io/org/…` lub ECR/GCR).
- Deploy: `helm upgrade --install astradesk deploy/chart -f deploy/chart/values.yaml`.
- **mTLS (mesh)**: `PeerAuthentication STRICT`, `DestinationRule` TLS=ISTIO_MUTUAL.
- **HPA**: target CPU ~60%, readiness/liveness probes.
- **Secrets**: Secret Manager/Vault + `envFrom` w Deployment.

Szczegóły: [`operations.md`](./operations.md) i [`security.md`](./security.md).

<br>

---

## CI/CD i łańcuch dostaw

- Etapy: `ruff` -> `mypy` -> `pytest` -> build -> SBOM (`syft`) -> skan (`grype`) -> push image -> Helm deploy.
- Podpisy obrazów (opcjonalnie): `cosign sign-blob` + weryfikacja w admission policy.
- Skany IaC: `trivy config` / `tfsec` dla Terraform/Helm.
- Artefakty: obrazy `astradesk-api:<sha>`, chart `deploy/chart`.

Przykładowy szkic workflow: patrz [`operations.md`](./operations.md#12-cicd-github-actions--gitlab-ci--jenkins).

<br>

---

## Testy (jednostkowe, integracyjne, e2e)

- **Unit**: `pytest`, mocki providerów LLM, testy plannerów i RBAC.
- **Integracyjne**: uruchomione usługi (Compose); testy API przez `httpx`/`pytest-asyncio`.
- **E2E**: zestawy scenariuszy dla Support/Ops (happy/edge-path), weryfikacja audytu (NATS->S3/ES).
- **Performance**: `k6`/`locust` (RPS, P95, 429/5xx), limity providerów LLM.

<br>

---

## Monitorowanie i operacje

- **Metrics**: Prometheus, dashboard w `grafana/dashboard-astradesk.json`.
- **Logs**: Loki (JSON), maskowanie PII/sekretów.
- **Traces**: OTel -> Tempo/Jaeger (span: JWT, planner, tools, RAG, provider).
- **Runbook**: incydenty 5xx/429/timeouty, brak audytów, degradacja DB/Redis/NATS - zob. [`operations.md`](./operations.md#14-runbook-incydenty-i-operacje).

<br>

---

## Rozwiązywanie problemów (FAQ/Troubleshooting)

- `401 invalid token` - sprawdź OIDC/JWKS URL, zegar systemowy, `aud/iss`.
- `503 service warming up` - brak połączeń do DB/Redis; zobacz logi startowe.
- brak zapisów audytu - NATS/Auditor/S3/ES, uprawnienia IAM, JetStream (lag).
- 429/5xx u providera - backoff wg `ProviderOverloaded/ProviderServerError`, fallback do RAG-only.

<br>

---

## Wersjonowanie i wydania

- **SemVer**: `MAJOR.MINOR.PATCH` (tag w repo).  
- Każde wydanie: changelog, SBOM, raport skanu, numer buildu w obrazie.  
- Rollout: `dev -> stage -> prod`; automatyczny rollback przy niezdrowych probe’ach.

<br>

---

## Kontakt i odpowiedzialności

- Właściciel dokumentacji: **Zespół AstraDesk SRE/DevOps**
- Kanał wsparcia: `#astradesk` (Slack) / rota PagerDuty
- Bilety i backlog: Jira -> komponent **AstraDesk**

> Uwaga: dokumentacja `docs/` jest żywa - PR-y z poprawkami mile widziane.

<br>