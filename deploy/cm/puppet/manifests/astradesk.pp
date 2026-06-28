# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: deploy/cm/puppet/manifests/astradesk.pp
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

class astradesk {
  package { 'docker.io':
    ensure => installed,
  }

  package { 'docker-compose':
    ensure => installed,
  }

  file { '/opt/astradesk':
    ensure => directory,
    source => 'puppet:///modules/astradesk/repo',  # Copy repo from Puppet fileserver
    recurse => true,
  }

  exec { 'fetch_mtls_cert':
    command => "curl -X GET http://localhost:8080/api/admin/v1/secrets/astradesk_mtls -H 'Authorization: Bearer ${api_token}' -o /opt/astradesk/secrets/mtls-cert.pem",
    path => '/usr/bin',
    creates => '/opt/astradesk/secrets/mtls-cert.pem',
  }

  exec { 'deploy_docker_compose':
    command => 'docker compose -f /opt/astradesk/docker-compose.yml up -d',
    path => '/usr/bin',
    require => [File['/opt/astradesk'], Exec['fetch_mtls_cert']],
  }
}
