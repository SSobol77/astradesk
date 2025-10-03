# API Gateway

## `GET /healthz`
- 200: `{"status":"ok"}`

## `POST /v1/agents/run`
Wymaga `Authorization: Bearer <JWT>`.

### Body:
```json
{
  "agent": "support",
  "input": "Utwórz ticket dla incydentu sieci",
  "tool_calls": [],
  "meta": { "user": "alice", "roles": ["it.support"] }
}
200 OK:
json
Skopiuj kod
{
  "output": "Ticket #123: ...",
  "reasoning_trace_id": "rt-support",
  "used_tools": ["create_ticket","get_metrics","restart_service","get_weather"]
}
Kody błędów:

400 — nieznany agent,

401 — brak/nieprawidłowy JWT,

503 — serwis w trakcie startu.

pgsql
Skopiuj kod

### `docs/operations.md`
```markdown
# Operacje / DevOps

## Lokalne (Docker Compose)
- `docker compose up -d --build`
- `make migrate`
- `make ingest`

## K8s (Helm)
- Zbuduj obrazy i wypchnij do rejestru.
- `helm upgrade --install astradesk deploy/chart -f deploy/chart/values.yaml`
- HPA: włączone (autoscaling/v2), CPU 60%.

## CI/CD
- GitHub Actions/GitLab CI/Jenkins — lint/type/test/build, push obrazów, Helm deploy.
- SBOM: dodaj `syft/grype` w pipeline (rekomendowane).

## Monitoring
- OpenTelemetry → Prometheus/Grafana
- Logs: Loki
- Traces: Tempo/Jaeger
- Dashboard: `grafana/dashboard-astradesk.json`

## Backupy
- Postgres: snapshoty RDS lub pg_dump
- S3: versioning + object-lock (audyt).