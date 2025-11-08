# dev/prometheus/Dockerfile
FROM prom/prometheus:v3.7.1
USER root
COPY prometheus.yml /etc/prometheus/
RUN chown nobody:nobody /etc/prometheus/prometheus.yml && chmod 644 /etc/prometheus/prometheus.yml
USER nobody
