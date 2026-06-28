<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: deploy/cm/salt/salt_README.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# Salt Configuration for AstraDesk Deployment

<br>

## Overview

The `salt/` directory contains Salt states for deploying AstraDesk with Docker Compose. It uses `astradesk/init.sls` to install Docker, copy repo, fetch mTLS/TLS certs from Admin API (/secrets), and run `docker compose up`.

<br>

## Directory Structure

```sh
salt/
└── astradesk
    └── init.sls  # State for deployment

```

<br>

## Setup

### Prerequisites

- SaltStack 3006+.

- Salt master/minion setup.

- Admin API for /secrets (JWT token in pillar).

### Steps

1. **Install Salt**:

   ```bash
   apt install salt-minion
   ```

2. **Apply State**:

   ```bash
   salt '*' state.apply astradesk
   ```

<br>

## Testing

- **Dry Run**:

  ```bash
  salt '*' state.apply astradesk test=True
  ```

- **Verify Deployment**:

  ```bash
  docker ps  # Check running containers
  curl http://localhost:8080/api/admin/v1/health
  ```

<br>

## Troubleshooting

- **Salt Errors**: Check logs: `salt-minion -l debug`.

- **API Errors**: Verify api_token in pillar and Admin API status.

<br>

## License

GPL-2.0-only (see SPDX in files).
