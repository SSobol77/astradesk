###### SPDX-License-Identifier: Apache-2.0

# Ansible Configuration for AstraDesk Deployment

<br>

## Overview

The `ansible/` directory contains Ansible configurations for deploying AstraDesk with Docker Compose. It uses inventories (`dev/hosts.ini`) and roles (`astradesk_docker/tasks/main.yml`) to install Docker, copy repo, fetch mTLS/TLS certs from Admin API (/secrets), and run `docker compose up`.

<br>

## Directory Structure

```sh
ansible/
├── inventories
│   └── dev
│       └── hosts.ini  # Inventory for dev environment
└── roles
    └── astradesk_docker
        └── tasks
            └── main.yml  # Tasks for deployment

```

<br>

## Setup

### Prerequisites

- Ansible 2.16+.

- SSH access to target hosts.

- Admin API running for /secrets (JWT token in vars).

### Steps

1. **Install Ansible**:

   ```bash
   pip install ansible
   ```

2. **Configure Inventory**:

   - Update `hosts.ini` with hosts and vars (e.g., api_token).

3. **Run Playbook**:

   ```bash
   ansible-playbook -i ansible/inventories/dev/hosts.ini ansible/playbook.yml  # Create playbook.yml if needed
   ```

<br>

## Testing

- **Dry Run**:

  ```bash
  ansible-playbook -i ansible/inventories/dev/hosts.ini ansible/playbook.yml --check
  ```

- **Verify Deployment**:

  ```bash
  docker ps  # Check running containers
  curl http://localhost:8080/api/admin/v1/health
  ```

<br>

## Troubleshooting

- **Connection Errors**: Check SSH keys and hosts.ini.

- **API Errors**: Verify api_token in vars and Admin API status.

<br>

## License

Apache-2.0 (see SPDX in files).
