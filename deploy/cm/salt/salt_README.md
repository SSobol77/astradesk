###### SPDX-License-Identifier: Apache-2.0

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

Apache-2.0 (see SPDX in files).