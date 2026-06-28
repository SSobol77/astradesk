# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: deploy/cm/salt/astradesk/init.sls
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Automates AstraDesk development, deployment, or operational tasks.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

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
