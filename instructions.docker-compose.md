# AstraDesk — Docker Compose Guide

This workflow runs every service (API, admin portal, ticket adapter, auditor,
supporting databases) inside containers.

## Prerequisites
- Docker Engine 24+ with the Compose plugin.
- `.env` populated (see `instructions.md`).

## Step-by-step
1. **Build images (only first time or after code changes)**
   ```bash
   docker compose build
   ```

2. **Launch the entire stack**
   ```bash
   docker compose up -d
   ```
   Services come up in dependency order defined in `docker-compose.yml`. Wait
   until health checks pass:
   ```bash
   docker compose ps
   ```

3. **Tail logs**
   ```bash
   docker compose logs -f api admin ticket-adapter auditor
   ```

4. **Access endpoints**
   - API Gateway: <http://localhost:8000/healthz>
   - Admin Portal UI: <http://localhost:3000>
   - Ticket Adapter Actuator: <http://localhost:8081/actuator/health>
   - Prometheus: <http://localhost:9090>

5. **Run one-off commands inside containers**
   ```bash
   docker compose exec api uv run pytest -k "smoke"
   docker compose exec admin npm run lint
   ```

6. **Stop everything and remove volumes**
   ```bash
   docker compose down -v
   ```

## Partial setups
- **Dependencies only (for local API dev):**
  ```bash
  docker compose up -d db mysql redis nats ticket-adapter
  ```
- **Restart a single service:**
  ```bash
  docker compose restart api
  ```

## Troubleshooting
- Health checks failing → inspect individual service logs.
- Port collisions → adjust published ports in `docker-compose.yml`.
- Database migrations → run `docker compose exec api uv run python scripts/ingest_docs.py support` as needed.

