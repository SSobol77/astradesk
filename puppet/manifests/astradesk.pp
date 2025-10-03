class astradesk {
  package { 'docker.io': ensure => installed }
  service { 'docker': ensure => running, enable => true }
  file { '/opt/astradesk':
    ensure => directory,
    owner  => 'root',
    group  => 'root',
  }
  file { '/opt/astradesk/docker-compose.yml':
    ensure  => file,
    source  => 'puppet:///modules/astradesk/docker-compose.yml',
    require => File['/opt/astradesk'],
  }
  exec { 'compose-up':
    command => '/usr/bin/docker compose up -d',
    cwd     => '/opt/astradesk',
    refreshonly => true,
    subscribe   => File['/opt/astradesk/docker-compose.yml'],
  }
}
