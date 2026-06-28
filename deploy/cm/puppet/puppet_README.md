<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: deploy/cm/puppet/puppet_README.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

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

GPL-2.0-only (see SPDX in files).
