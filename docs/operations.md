# Operacje / DevOps

## Lokalne (Docker Compose)
- `docker compose up -d --build`
- `make migrate`
- `make ingest`

## K8s (Helm)
- Zbuduj obrazy i wypchnij do rejestru.
- `helm upgrade --install astradesk deploy/chart -f deploy/chart/values.yaml`
- HPA: włączone (autoscaling/v2), CPU 60%.

## CI/CD
- GitHub Actions/GitLab CI/Jenkins — lint/type/test/build, push obrazów, Helm deploy.
- SBOM: dodaj `syft/grype` w pipeline (rekomendowane).

## Monitoring
- OpenTelemetry → Prometheus/Grafana
- Logs: Loki
- Traces: Tempo/Jaeger
- Dashboard: `grafana/dashboard-astradesk.json`

## Backupy
- Postgres: snapshoty RDS lub pg_dump
- S3: versioning + object-lock (audyt).