<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: services/ticket-adapter-java/README.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

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
