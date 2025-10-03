# AstraDesk 2.0 — Dokumentacja

AstraDesk to wewnętrzny framework do budowy agentów AI z referencyjnymi agentami:
- **SupportAgent** (RAG na dokumentach firmy + ticketing),
- **OpsAgent** (metryki + akcje operacyjne z politykami).

Ten folder zawiera:
- `architecture.md` — architektura i przepływy,
- `api.md` — kontrakty API (Gateway), format żądań/odpowiedzi,
- `operations.md` — uruchamianie lokalnie / K8s, CI/CD,
- `security.md` — OIDC/JWT, mTLS, RBAC, audyt, S3/Elastic.

Minimalne kroki startu (DEV):
1. `docker compose up -d --build`
2. `make migrate`
3. Umieść pliki `.md`/`.txt` w `./docs` (repo root) i `make ingest`
4. `curl -s localhost:8080/healthz` → `{"status":"ok"}`
5. Wywołaj agenta: `POST /v1/agents/run`
