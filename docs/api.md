# API — AstraDesk Gateway

Dokument opisuje publiczne endpointy API Gateway dla systemu **AstraDesk**.

- Bazowy URL (lokalnie): `http://localhost:8080`
- Format danych: `application/json; charset=utf-8`
- Wymagane uwierzytelnienie (większość operacji): **JWT** w nagłówku `Authorization: Bearer <token>`

<br>

---

<br>

## Spis treści

- [Wymagania ogólne](#wymagania-ogólne)

- [Uwierzytelnianie i autoryzacja](#uwierzytelnianie-i-autoryzacja)

- [Endpointy](#endpointy)
  - [GET /healthz](#get-healthz)
  - [POST /v1/agents/run](#post-v1agentsrun)

- [Kody błędów](#kody-błędów)

- [Przykłady cURL](#przykłady-curl)

- [Modele danych (schematy)](#modele-danych-schematy)

- [Uwagi operacyjne](#uwagi-operacyjne)

<br>

---

## Wymagania ogólne

- **Nagłówki:**  
  `Content-Type: application/json` w żądaniach z ciałem.  
  `Accept: application/json` rekomendowany.

- **Strefy czasowe:** Wszystkie znaczniki czasu (jeśli występują) w ISO-8601 (UTC).

- **Idempotencja:** Endpointy odczytu są idempotentne. Akcje agentów zależą od użytych narzędzi (side-effecty po stronie systemów zewnętrznych są możliwe).

<br>

---

## Uwierzytelnianie i autoryzacja

- **JWT (OIDC):** każdy request do endpointów biznesowych musi posiadać:

```sh
Authorization: Bearer <JWT>

```

- **RBAC:** uprawnienia do użycia części narzędzi egzekwowane są po rolach w `claims`
(np. `roles`, `groups`, `realm_access.roles`).  

Przykład: `restart_service` wymaga roli `sre`.

> Brak/niepoprawny token - `401 Unauthorized`.

<br>

---

## Endpointy

### GET `/healthz`

Prosty health-check procesu (liveness). **Nie** sprawdza zależności (DB/Redis).

**Odpowiedzi:**

- `200 OK`
```json
{ "status": "ok" }
```

<br>


### POST `/v1/agents/run`

Uruchamia wskazanego agenta (np. `support` / `ops`).
Wymaga **JWT** (`Authorization: Bearer <JWT>`).
Agent wykonuje plan (planner) -> wywołuje niezbędne narzędzia (RBAC) -> finalizuje odpowiedź (opcjonalnie z użyciem RAG) -> zapisuje audyt i dialog.

**Body (request):**

```json
{
  "agent": "support",
  "input": "Utwórz ticket dla incydentu sieci",
  "tool_calls": [],
  "meta": { "user": "alice", "roles": ["it.support"] }
}
```

**Odpowiedź `200 OK`:**

```json
{
  "output": "Ticket #123: ...",
  "reasoning_trace_id": "rt-support",
  "used_tools": ["create_ticket", "get_metrics", "restart_service", "get_weather"]
}
```

**Błędy (najczęstsze):**

* `400 Bad Request` — nieznany agent (`agent` nie jest jednym z: `support`, `ops`).
* `401 Unauthorized` — brak/nieprawidłowy JWT.
* `403 Forbidden` — RBAC odrzucił wywołanie konkretnego narzędzia.
* `503 Service Unavailable` — serwis w trakcie startu (warm-up) lub brak krytycznych zależności.

**Nagłówki wymagane:**

```sh
Authorization: Bearer <JWT>
Content-Type: application/json
```

<br>

---

## Kody błędów

| Kod | Znaczenie             | Typowy powód                                  |
| --- | --------------------- | --------------------------------------------- |
| 200 | OK                    | Operacja zakończona sukcesem                  |
| 400 | Bad Request           | Nieznany agent / nieprawidłowe dane wejściowe |
| 401 | Unauthorized          | Brak lub zły token JWT                        |
| 403 | Forbidden             | Brak wymaganych ról (RBAC)                    |
| 429 | Too Many Requests     | Przekroczone limity (jeśli włączone)          |
| 500 | Internal Server Error | Niespodziewany błąd                           |
| 503 | Service Unavailable   | Serwis się uruchamia / brak zależności        |

> Format błędu:

```json
{ "detail": "komunikat", "reason": "opcjonalnie_szczegóły" }
```

<br>

---

## Przykłady cURL

### Health-check

```sh
curl -s http://localhost:8080/healthz
```

### Uruchomienie agenta `support`

```bash
curl -s -X POST http://localhost:8080/v1/agents/run \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{
        "agent": "support",
        "input": "Utwórz ticket dla incydentu sieci",
        "tool_calls": [],
        "meta": { "user": "alice", "roles": ["it.support"] }
      }'
```

Przykładowa odpowiedź:

```json
{
  "output": "Ticket #123: ...",
  "reasoning_trace_id": "rt-support",
  "used_tools": ["create_ticket","get_metrics"]
}
```

### Błąd: nieznany agent

```sh
curl -s -X POST http://localhost:8080/v1/agents/run \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"agent":"unknown","input":"..."}'
```

Odpowiedź:

```json
{ "detail": "unknown agent" }
```

<br>

---

## Modele danych (schematy)

### `AgentRequest`

```json
{
  "agent": "support | ops",
  "input": "string (min 1)",
  "tool_calls": [
    { "name": "string", "arguments": { "k": "v" } }
  ],
  "meta": { "arbitrary": "json" }
}
```

### `RunResponse`

```json
{
  "output": "string",
  "reasoning_trace_id": "string",
  "used_tools": ["string", "..."]
}
```

> Uwaga: `tool_calls` to sugestie narzędzi od klienta; faktyczne wywołania dobiera planner i/lub agent zgodnie z RBAC i politykami.

<br>

---

## Uwagi operacyjne

* **Readiness (503):** podczas startu API może zwrócić `503` do czasu inicjalizacji połączeń (Postgres/Redis/RAG/Registry).
* **Audyt:** każde wywołanie agenta jest logowane (Postgres) i emitowane jako event (NATS) — zapis do S3/Elastic realizuje subskrybent „auditor”.
* **Rate limiting:** (opcjonalnie) może zwrócić `429` z nagłówkiem `Retry-After`.
* **Observability:** zalecane OTel + Prometheus/Grafana, logi w Loki; `reasoning_trace_id` umożliwia korelację.

---

**Wersja dokumentu:** 1.0.0
**Kontakt:** zespół AstraDesk DevOps / SRE

