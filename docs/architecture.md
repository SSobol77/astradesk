<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: docs/architecture.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# Architektura - AstraDesk

Ten dokument opisuje architekturę logiczną i operacyjną systemu **AstraDesk**: przepływy żądań, komponenty, bezpieczeństwo, skalowanie, monitoring oraz artefakty wdrożeniowe.

<br>

---

## 1) Widok ogólny (C4:L1) - komponenty i zależności

```sh
Client / Portal (Next.js)
    │  (Bearer JWT OIDC)
    ▼
API Gateway (FastAPI, Python 3.11)
    │   ├─ OIDC/JWT Verify (JWKS)
    │   ├─ RBAC/ABAC (policy)
    │   ├─ Planner (LLM Planner / Keyword Planner fallback)
    │   ├─ Tools Registry (tickets_proxy, metrics, ops_actions, weather)
    │   └─ Memory (dialogues, audits) + RAG (pgvector)
    │
    ├────────► Model Gateway (Bedrock | OpenAI | vLLM)
    │             ├─ Guardrails (cenzor treści / max length / JSON schema)
    │             └─ Tokenization / Usage / Retry-Backoff
    │
    ├────────► Postgres 17 + pgvector  (RAG: documents; dialogues; audits)
    ├────────► Redis (worklists, TTL, locks)
    └────────► NATS (publish "astradesk.audit")
                        │
                        └── Auditor (Subscriber, Python)
                               ├─ zapisy do S3 (archiwizacja audytów)
                               └─ zapisy do Elasticsearch (analiza/dashboardy)
```

<br>

---

## 2) Przepływ żądania (sekcja sekwencji)

### `/v1/agents/run` — od klienta do odpowiedzi

```sh
User/Portal           Gateway             OIDC/JWKS            Planner        Tools/Registry         RAG/PG           NATS           Auditor
    |   POST /run       |                     |                   |                 |               (pgvector)          |               |
    |------------------>|  Authorization      |                   |                 |                                   |               |
    |                   |-- verify(JWT) ----->|                   |                 |                                   |               |
    |                   |<-- claims OK -------|                   |                 |                                   |               |
    |                   |  plan = make(input) |                   |                 |                                   |               |
    |                   |-------------------->|                   |                 |                                   |               |
    |                   |<--- Plan(steps) ----|                   |                 |                                   |               |
    |                   |  for step in steps: |                   |                 |                                   |               |
    |                   |  exec tool(step)    |----------------------------->(Tool)                                     |               |
    |                   |  (RBAC per tool)    |                   |                 |--> result                         |               |
    |                   |  collect results    |                   |                 |<-- result                         |               |
    |                   | if no tool: retrieve context ---------->|                                   (top-k pgvector)  |               |
    |                   |<-------------------- ctx[]              |                                                     |               |
    |                   | finalize(answer)    |                   |                 |                                   |               |
    |                   | store_dialogue() --> Postgres           |                 |                                   |               |
    |                   | audit() -----------> Postgres (audits)  |                 |                                   |               |
    |                   | publish(audit) ----> NATS ------------------------------------------------------------------->|  write S3/ES  |
    |                   | return 200 JSON     |                   |                 |                                   |               |
    |<------------------|                     |                   |                 |                                   |               |
```

<br>

---

## 3) Topologia wdrożenia (K8s + mesh)

```sh
+------------------------------- Kubernetes Cluster -------------------------------+
|                                                                                  |
|  [Ingress/ALB] --> [Istio/Linkerd] (mTLS STRICT)                                 |
|                          │                                                       |
|            +-------------┼----------------+                                      |
|            |             │                |                                      |
|       [api-gateway]   [auditor]       [model-gateway]*                           |
|            │             │                │                                      |
|            │             │                ├── egress -> OpenAI/Bedrock/vLLM      |
|            │             │                                                       |
|            │             ├── S3 (VPC endpoint)                                   |
|            │             └── Elasticsearch (managed / self-hosted)               |
|            │                                                                     |
|            ├── Postgres (Amazon RDS / self-managed) + pgvector                   |
|            └── Redis (ElastiCache / Redis OSS)                                   |
|                                                                                  |
|  Observability: Prometheus + Grafana + Loki + Tempo/Jaeger                       |
|  CI/CD: GitHub Actions/GitLab CI/Jenkins -> build images -> Helm upgrade         |
+----------------------------------------------------------------------------------+
```

*`model-gateway` może być wydzielony jako osobny mikroserwis (np. gRPC/HTTP) albo część gateway’a.*

<br>

---

## 4) Model Gateway — składniki i strażnicy (guardrails)

```sh
          +-------------------- Model Gateway --------------------+
          |                                                       |
Messages  |  normalize() -> validate_conversation()               |
(system/  |  clamp ChatParams (T, top_p, max_tokens)              |
 user/    |                                                       |
assistant)|                  +------------------+                 |
          |   Provider API   |  Guardrails      |                 |
          |  --------------> |  * blocklist     |                 |
          |                  |  * max length    |                 |
          |                  |  * json schema   |                 |
          |                  +---------+--------+                 |
          |                            |                          |
          |        +-------------------v----------------------+   |
          |        |    Provider (OpenAI/Bedrock/vLLM)       |    |
          |        |  - chat() / stream()                    |    |
          |        |  - retry/backoff on 429/5xx             |    |
          |        |  - usage (tokens)                       |    |
          |        +-------------------+----------------------+   |
          |                            |                          |
          |         Exceptions (rich)  |                          |
          |   ModelGatewayError/Timeout/Overloaded/ServerError    |
          +---------------------------+---------------------------+
```

<br>

---

## 5) Warstwa danych

### Tabele w Postgres (schemat poglądowy)

```sql
dialogues(
  id BIGSERIAL PK,
  agent TEXT NOT NULL,            -- 'support' | 'ops'
  query TEXT NOT NULL,
  answer TEXT NOT NULL,
  meta JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now()
)

audits(
  id BIGSERIAL PK,
  actor TEXT NOT NULL,            -- agent / user / service
  action TEXT NOT NULL,           -- 'agents.run', 'create_ticket', etc.
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
)

documents(
  id BIGSERIAL PK,
  source TEXT NOT NULL,           -- np. filename / url
  chunk TEXT NOT NULL,
  embedding VECTOR(384) NOT NULL, -- pgvector dim dopasowana do modelu
  created_at TIMESTAMPTZ DEFAULT now()
)
```

### Redis — klucze robocze
- `work:{agent}:{id}` -> lista (kolejka ad-hoc)
- TTL dla kluczy sesyjnych i locków (np. `lock:{resource}`)

### NATS — kanały
- `astradesk.audit` — zdarzenia audytu (publisher: gateway, subscriber: auditor)
- Domyślny sink audytu to plik JSON-Lines (`AUDIT_MODE=jsonl`). Tryb
  `AUDIT_MODE=jetstream` (ISSUE 019/039, jawny opt-in) publikuje na trwały
  strumień JetStream zamiast tematu core NATS: Gateway blokuje sukces
  narzędzia na potwierdzeniu trwałego zapisu przez broker, a `auditor`
  konsumuje jako trwały pull consumer, z ograniczonymi ponowieniami i DLQ
  (`astradesk.audit.dlq`) przy wyczerpaniu prób zapisu do magazynu — patrz
  `audit/evidence/39_jetstream_durable_audit.md`.

<br>

---

## 6) Bezpieczeństwo

- **Autoryzacja**: JWT (OIDC) z weryfikacją przez **JWKS** (`kid`, `iss`, `aud`).
- **RBAC/ABAC**: role zbierane z `claims.roles` / `groups` / `realm_access.roles` (Keycloak).  
  Per-narzędzie `allowed_roles` egzekwowane w `ToolRegistry.execute`.
- **mTLS**: mesh (Istio/Linkerd) z **STRICT** PeerAuthentication + `DestinationRule` TLS=ISTIO_MUTUAL.
- **Guardrails**: cenzura treści planera (blocklist), limity długości, walidacja JSON planu (schemat).
- **Sekrety**: K8s Secret lub external (AWS Secrets Manager / HashiCorp Vault).
- **Rate limit / QoS**: po stronie gateway’a lub mesh (Envoy), zwrot `429` z `Retry-After`.

---

## 7) Skalowanie i niezawodność

- **HPA**: autoscaling/v2, target CPU ~60%, min/max replicas na `api-gateway` i `model-gateway`.
- **Retry/Backoff**: według wyjątków Model Gateway (`ProviderOverloaded.suggested_sleep`, `ProviderServerError.should_retry`).
- **Circuit Breakers**: na poziomie mesh (Envoy) dla wywołań do providerów LLM.
- **Idempotencja**: narzędzia z efektami ubocznymi (np. `create_ticket`) powinny wspierać idempotency key (np. `X-Idempotency-Key`).
- **S3/ES**: domyślnie (`AUDIT_MODE=jsonl`) audyt trafia do lokalnego pliku JSON-Lines. W trybie `AUDIT_MODE=jetstream` `auditor` konsumuje z trwałego JetStream i potwierdza (ack) partię dopiero po udanym zapisie do S3 **i** Elasticsearch, z ograniczonymi ponowieniami i przekierowaniem do DLQ przy wyczerpaniu prób — zdarzenie nigdy nie ginie po cichu (`audit/evidence/39_jetstream_durable_audit.md`).

---

## 8) Observability

- **Metrics**: Prometheus (RPS, P50/P95, błędy per endpoint i per narzędzie).
- **Logs**: Loki (strukturalne JSON: `trace_id`, `request_id`, `provider`, `status`).
- **Traces**: OTel -> Tempo/Jaeger (span: planowanie, wywołania narzędzi, RAG, provider).
- **Dashboards**: Grafana (`grafana/dashboard-astradesk.json`).

---

## 9) CI/CD i operacje

- **Pipeline**:
  - `ruff` + `mypy` + `pytest`,
  - Build obrazów (SBOM: `syft`, skan: `grype`),
  - Helm chart deploy (`helm upgrade --install`).
- **Runbook (incydenty)**:
  - 5xx/timeout providera -> sprawdź logi `ProviderServerError/ProviderTimeout`, zwiększ backoff, włącz fallback (tryb tylko-RAG).
  - 429 -> monitoruj `ProviderOverloaded`, respektuj `Retry-After`, rozważ limit RPS.
- **Backupy**:
  - Postgres: RDS snapshot / `pg_dump`,
  - S3: versioning + object-lock (compliance), test odtwarzania kwartalnie.

<br>

---

## 10) Konfiguracja (ENV)

| Zmienna              | Opis                                           | Przykład                                                |
|----------------------|------------------------------------------------|---------------------------------------------------------|
| `DATABASE_URL`       | DSN Postgres                                   | `postgresql://user:pass@pg:5432/astradesk`             |
| `REDIS_URL`          | Redis                                          | `redis://redis:6379/0`                                  |
| `NATS_URL`           | NATS                                           | `nats://nats:4222`                                      |
| `OIDC_ISSUER`        | OIDC Issuer                                    | `https://idp.example.com/realms/main`                   |
| `OIDC_AUDIENCE`      | Audience (API)                                 | `astradesk-api`                                         |
| `OIDC_JWKS_URL`      | JWKS endpoint                                  | `https://idp.example.com/realms/main/protocol/openid-connect/certs` |
| `API_VERSION`        | Wersja API (nagłówki/eksport)                  | `1.0.0`                                                 |
| `LOG_LEVEL`          | Poziom logowania                               | `INFO`, `DEBUG`                                         |
| `AUDIT_MODE`         | Sink audytu side-effect: `jsonl` (domyślny) lub `jetstream` (trwały, ISSUE 019/039) — pełna konfiguracja: `operations.md` §10 | `jsonl` |

<br>

---

## 11) Dodatki — diagram procesów (Audyt)

```sh
           Gateway
    (publish audit event)
            │
            ▼
         NATS Bus  ──(subject: "astradesk.audit")──►  Auditor (subscriber)
                                                         │
                                     +-------------------┼-------------------+
                                     |                   │                   |
                                     ▼                   ▼                   ▼
                                   S3 (raw JSON)    Elasticsearch        Alerting/Rules
                                   (archiwum)       (zapytania,          (np. na podejrzane akcje)
                                                     dashboardy)
```

Ten diagram opisuje domyślny tryb (`AUDIT_MODE=jsonl`, temat core NATS,
zapis best-effort). W trybie `AUDIT_MODE=jetstream` (ISSUE 019/039) "NATS
Bus" powyżej to trwały strumień JetStream: Gateway otrzymuje potwierdzenie
brokera przed zwróceniem sukcesu narzędzia, a `Auditor` jest trwałym pull
consumerem, który potwierdza (ack) partię dopiero po zapisie do S3 **i**
Elasticsearch, z DLQ przy wyczerpaniu ponowień. Pełny opis i dowód
odzyskiwania po awarii: `audit/evidence/39_jetstream_durable_audit.md`,
`audit/evidence/39_jetstream_crash_recovery_run.txt`.

<br>

---

## 12) Notatki dla bezpieczeństwa i zgodności

- **PII**: przechowywać minimalne dane osobowe; maskować w logach (`claims` filtrować do `sub`, `email`).
- **Retention**: audyty w S3 z polityką retencji + blokada (WORM) jeśli wymagane.
- **mTLS**: wszystkie połączenia między usługami w klastrze przez mesh (STRICT), TLS do zewnętrznych providerów.
- **RBAC w narzędziach**: każdy tool sprawdza `claims` i `allowed_roles` — brak roli -> komunikat odmowy + audyt.

<br>

---

**Wersja dokumentu:** 1.0.0  
**Kontakt:** Zespół AstraDesk (Dev/DevOps/SRE)

<br>
