docker:
  pkg.installed: []
  service.running:
    - enable: true

/opt/astradesk:
  file.directory:
    - user: root
    - group: root
    - mode: 755

/opt/astradesk/docker-compose.yml:
  file.managed:
    - source: salt://astradesk/docker-compose.yml

compose_up:
  cmd.run:
    - name: docker compose up -d
    - cwd: /opt/astradesk
    - require:
      - file: /opt/astradesk/docker-compose.yml
