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
```

200 OK:

```json
{
  "output": "Ticket #123: ...",
  "reasoning_trace_id": "rt-support",
  "used_tools": ["create_ticket","get_metrics","restart_service","get_weather"]
}

Kody błędów:

400 — nieznany agent,

401 — brak/nieprawidłowy JWT,

503 — serwis w trakcie startu.
