# AstraDesk Runbook

Step‑by‑step guide for bringing the entire AstraDesk stack online on a developer
workstation. The flow mirrors production dependencies so that API, UI, and
supporting services can be tested end‑to‑end.

1. **Provision environment variables**
   - Copy `.env.example` to `.env`.
   - Fill in secrets (LLM keys, Jira/Slack tokens, DB passwords, etc.).
   - Keep `.env` out of version control.

2. **Install local tooling**
   - Python 3.14 with [`uv`](https://github.com/astral-sh/uv) (`pip install uv`).
   - Node.js 22.x + npm.
   - Java JDK 21+ (Gradle wrapper downloads its own distro).
   - Docker Engine + Compose plugin.

3. **Start shared infrastructure**
   - Bring up databases, cache, NATS, and the Java ticket adapter first:
     ```bash
     docker compose up -d db mysql redis nats ticket-adapter
     ```
     (or use `make up-deps`, see `instructions.makefile.md`).

4. **Run the API Gateway (Python)**
   - Install Python deps and launch FastAPI locally:
     ```bash
     uv sync --all-extras
     uv run uvicorn src.gateway.main:app --host 0.0.0.0 --port 8000 --reload --app-dir src
     ```
   - The gateway expects the backing services from step 3 to be healthy.

5. **Launch the Admin Portal (Next.js)**
   ```bash
   cd services/admin-portal
   npm ci
   npm run dev
   ```
   - The web UI proxies API calls to the gateway running on port 8000.

6. **Start the Auditor worker (optional but recommended)**
   - Either keep the Docker container running from step 3 (`docker compose up auditor`) or run locally:
     ```bash
     cd services/auditor
     uv run python main.py
     ```

7. **Verify the system**
   - API health: `curl http://localhost:8000/healthz`.
   - Admin portal: open `http://localhost:3000`.
   - Ticket adapter health: `curl http://localhost:8081/actuator/health`.
   - Redis/NATS ready: check `docker compose logs redis nats`.

8. **Domain packs and datasets**
   - Ingest sample documentation if you need search/snippets:
     ```bash
     uv run python scripts/ingest_docs.py datasets/support
     ```
   - Domain pack discovery in the UI reads from `/packages`.

9. **Clean up**
   - Stop Docker services: `docker compose down -v`.
   - Stop local dev servers (Ctrl+C in their terminals).

See the dedicated guides for alternative orchestrations:
`instructions.docker-compose.md`, `instructions.makefile.md`, `instructions.jenkins.md`.

