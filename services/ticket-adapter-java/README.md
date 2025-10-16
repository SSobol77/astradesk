# Ticket Adapter – Admin API Client

Auto-generated Admin API bindings live under `src/main/java-gen/admin_api/`
with a thin wrapper in `src/main/java/com/astradesk/ticket/clients/AdminApiClient.java`.

## Regeneration

```bash
 make api.clients.gen
```

This target invokes `openapi-generator-cli` and overwrites the contents of `java-gen/`.

## Usage

```java
import com.astradesk.ticket.clients.AdminApiClient;

var adminApi = AdminApiClient.fromEnv();
var agents = adminApi.listAgents(20, 0);
```

Environment variables honoured:

- `ADMIN_API_URL` (default `http://localhost:8080/api/admin/v1`)
- `ADMIN_API_TOKEN` (optional bearer token)
