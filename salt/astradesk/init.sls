# SPDX-License-Identifier: Apache-2.0
# File: salt/astradesk/init.sls
# Description:
#     Salt state for deploying AstraDesk with Docker Compose.
#     Installs Docker, copies repo, fetches mTLS/TLS certs from Admin API, and runs docker compose up.
# Author: Siergej Sobolewski
# Since: 2025-10-22

install_docker:
  pkg.installed:
    - name: docker.io

install_docker_compose:
  pkg.installed:
    - name: docker-compose

copy_repo:
  file.recurse:
    - name: /opt/astradesk
    - source: salt://astradesk/repo  # Copy repo from Salt fileserver

fetch_mtls_cert:
  cmd.run:
    - name: curl -X GET http://localhost:8080/api/admin/v1/secrets/astradesk_mtls -H "Authorization: Bearer {{ salt['pillar.get']('api_token') }}" -o /opt/astradesk/secrets/mtls-cert.pem
    - creates: /opt/astradesk/secrets/mtls-cert.pem

deploy_docker_compose:
  cmd.run:
    - name: docker compose -f /opt/astradesk/docker-compose.yml up -d
    - require:
      - file: copy_repo
      - cmd: fetch_mtls_cert
