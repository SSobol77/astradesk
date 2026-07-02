<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: docs/api.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

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

**Weryfikacja tokenu (ISSUE 009):** ingress API Gateway (`astradesk_core.utils.oidc`,
podłączony w `gateway.auth_dependency.install_verifier()` podczas startu, przed
inicjalizacją DB/Redis/RAG) weryfikuje podpis przez JWKS, `iss`, `aud`, `exp`,
`nbf` (jeśli obecne) oraz dopuszczalne algorytmy (`OIDC_ALGORITHMS`, domyślnie
`RS256`). **Na wdrożonych warstwach** (`ENVIRONMENT` ∈ `production`/`prod`/
`staging`/`stage`; domyślnie `production`, gdy `ENVIRONMENT` nie jest ustawione)
brak `OIDC_ISSUER`/`OIDC_AUDIENCE`/`OIDC_JWKS_URL` przerywa start serwisu
(`AuthConfigError`) — bez fallbacku do słabszego weryfikatora. Tryb
`AUTH_MODE=local-dev` (symetryczny HS256, `ASTRADESK_DEV_JWT_SECRET`) jest
jedyną, jawnie nazwaną wygodą lokalną/dev/test/CI i jest odrzucany przy
starcie na wdrożonej warstwie.

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
* **Audyt narzędzi side-effect (ISSUE 019):** każda próba wywołania narzędzia `write`/`execute` przez `ToolRegistry.execute` — dozwolona, odrzucona przez RBAC lub zakończona błędem — jest trwale zapisywana przez skonfigurowany `AuditWriter` (`services/api-gateway/src/runtime/audit.py`), niezależnie od tego, czy krok pochodzi z planera LLM czy ścieżki fallback. Podgląd argumentów jest redagowany współdzielonym mechanizmem NEW-04. Ustawienie `AUDIT_LOG_PATH` włącza trwały zapis do pliku JSON-Lines. **Na wdrożonych warstwach** (`ENVIRONMENT` ∈ `production`/`prod`/`staging`/`stage`; `production` jest wartością domyślną, gdy `ENVIRONMENT` nie jest ustawione) brak `AUDIT_LOG_PATH` przerywa start serwisu (`AuditConfigError`) — audyt nie może po cichu spaść do trybu nietrwałego. Poza warstwami wdrożeniowymi (np. lokalny dev/test z `ENVIRONMENT=dev`) writer in-proces jest dozwolony, z ostrzeżeniem w logu.
* **Rate limiting:** (opcjonalnie) może zwrócić `429` z nagłówkiem `Retry-After`.
* **Observability:** zalecane OTel + Prometheus/Grafana, logi w Loki; `reasoning_trace_id` umożliwia korelację.

---

**Wersja dokumentu:** 1.0.0
**Kontakt:** zespół AstraDesk DevOps / SRE
