###### SPDX-License-Identifier: Apache-2.0

# Puppet Configuration for AstraDesk Deployment

<br>

## Overview

The `puppet/` directory contains Puppet manifests for deploying AstraDesk with Docker Compose. It uses `manifests/astradesk.pp` to install Docker, copy repo, fetch mTLS/TLS certs from Admin API (/secrets), and run `docker compose up`.

<br>

## Directory Structure

```sh
puppet/
└── manifests
    └── astradesk.pp  # Manifest for deployment
```

<br>

## Setup

### Prerequisites

- Puppet 8+.

- Puppet master/agent setup.

- Admin API for /secrets (JWT token in vars).

<br>

### Steps

1. **Install Puppet**:

   ```bash
   apt install puppet-agent
   ```

2. **Apply Manifest**:

   ```bash
   puppet apply puppet/manifests/astradesk.pp --modulepath=puppet/
   ```

<br>

## Testing

- **Dry Run**:

  ```bash
  puppet apply puppet/manifests/astradesk.pp --noop
  ```

- **Verify Deployment**:

  ```bash
  docker ps  # Check running containers
  curl http://localhost:8080/api/admin/v1/health
  ```

<br>

## Troubleshooting

- **Puppet Errors**: Check logs: `puppet agent --test --debug`.

- **API Errors**: Verify api_token and Admin API status.

<br>

## License

Apache-2.0 (see SPDX in files).
