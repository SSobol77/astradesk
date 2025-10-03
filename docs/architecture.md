# Architektura

Client/Portal (Next.js)
│ (Bearer JWT OIDC)
▼
API Gateway (FastAPI, Python 3.11)

Auth (OIDC/JWT via JWKS)

Agents: Support / Ops

LLM Planner (Model Gateway: Bedrock/OpenAI/vLLM)

Tools: tickets_proxy, metrics, ops_actions, weather

Memory: Postgres (dialogues/audits/documents), Redis (work)

Events: NATS (audit → "astradesk.audit")
│
├── Postgres 16 + pgvector (RAG + dialogi + audyt)
├── Redis (TTL/locki/listy)
├── NATS (JetStream opcjonalnie)
└── Auditor (NATS subscriber)
├── S3 (archiwizacja audytów)
└── Elasticsearch (późniejsza analiza / dashboardy)

markdown
Skopiuj kod

**Model Gateway**:
- Providerzy: AWS Bedrock / OpenAI / vLLM on-prem,
- Guardrails: blokady słów, limit długości, walidacja JSON dla planera,
- Planner: prompt → JSON (lista kroków narzędziowych), fallback na keyword planner.

**Bezpieczeństwo**:
- OIDC/JWT (API), mTLS w mesh (Istio/Linkerd), RBAC dla tooli (policy).