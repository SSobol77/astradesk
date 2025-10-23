# SPDX-License-Identifier: Apache-2.0
# File: puppet/manifests/astradesk.pp
# Description:
#     Puppet manifest for deploying AstraDesk with Docker Compose.
#     Installs Docker, copies repo, fetches mTLS/TLS certs from Admin API, and runs docker compose up.
# Author: Siergej Sobolewski
# Since: 2025-10-22

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
