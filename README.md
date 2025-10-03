# AstraDesk – AI Agents Framework + Demo Apps

## Uruchomienie lokalne
1. `cp .env.example .env` i ustaw `DATABASE_URL`/`REDIS_URL` (albo korzystaj z domyślnych).
2. `docker compose up -d --build`
3. Zainicjuj `pgvector`: `make migrate` (w innym terminalu).
4. Zrób wsad dokumentów: `make ingest` (umieść pliki `.md`/`.txt` w `./docs`).
5. API na `http://localhost:8080/docs`.

### Przykłady wywołań
```bash
curl -s localhost:8080/v1/agents/run \
  -H 'content-type: application/json' \
  -d '{"agent":"support","input":"Jak zrestartować usługę webapp?","meta":{"user":"alice"}}'


### Struktura repo
```sh
astradesk/
├─ README.md
├─ .env.example
├─ Makefile
├─ docker-compose.yml
├─ Dockerfile                # dla api (Python)
├─ Jenkinsfile
├─ .gitlab-ci.yml
├─ pyproject.toml
├─ uv.lock
├─ grafana/
│  └─ dashboard-astradesk.json
├─ deploy/
│  ├─ chart/                 # Helm chart (Kubernetes)
│  │  ├─ Chart.yaml
│  │  ├─ values.yaml
│  │  └─ templates/...
│  └─ openshift/
│     └─ astradesk-template.yaml
├─ infra/                    # Terraform (AWS)
│  ├─ main.tf
│  ├─ variables.tf
│  ├─ outputs.tf
│  └─ modules/...
├─ ansible/
│  ├─ inventories/dev/hosts.ini
│  └─ roles/astradesk_docker/tasks/main.yml
├─ puppet/
│  └─ manifests/astradesk.pp
├─ salt/
│  └─ astradesk/init.sls
├─ migrations/
│  └─ 0001_init_pgvector.sql
├─ scripts/
│  ├─ ingest_docs.py
│  └─ demo_queries.sh
├─ src/
│  ├─ gateway/               # FastAPI
│  │  └─ main.py
│  ├─ runtime/               # core framework (Python)
│  │  ├─ models.py
│  │  ├─ registry.py
│  │  ├─ memory.py
│  │  ├─ rag.py
│  │  ├─ planner.py
│  │  └─ events.py
│  ├─ agents/
│  │  ├─ support.py
│  │  └─ ops.py
│  └─ tools/
│     ├─ tickets_proxy.py    # Pythonowy klient do serwisu Java
│     ├─ metrics.py
│     ├─ ops_actions.py
│     └─ weather.py
├─ services/
│  ├─ ticket-adapter-java/   # JDK21 + Spring Boot WebFlux + MySQL
│  │  ├─ build.gradle.kts
│  │  ├─ Dockerfile
│  │  └─ src/main/java/com/astradesk/ticket/...
│  └─ admin-portal/          # Node 22 + Next.js 14
│     ├─ package.json
│     ├─ next.config.js
│     ├─ Dockerfile
│     └─ app/page.tsx
```