# Makefile for managing the project
# Targets:
#   sync         - Synchronize dependencies
#   lint         - Run linting on the codebase
#   type         - Run type checking
#   test         - Run all tests
#   test-java    - Run Java service tests
#   test-admin   - Run Admin portal tests
#   build        - Build all services
#   build-java   - Build Java service
#   build-admin  - Build Admin portal
#   migrate      - Apply database migrations
#   ingest       - Ingest documents into the system
#   up           - Start services using Docker Compose
#   down         - Stop services and remove containers

.PHONY: sync lint type test test-java test-admin build build-java build-admin migrate ingest up down

sync:
	uv sync --frozen

lint:
	uv run ruff check src tests

type:
	uv run mypy src

test:
	uv run pytest -q

test-java:
	cd services/ticket-adapter-java && ./gradlew test --no-daemon

test-admin:
	cd services/admin-portal && npm ci && npm test

build-java:
	cd services/ticket-adapter-java && ./gradlew bootJar --no-daemon

build-admin:
	cd services/admin-portal && npm ci && npm run build

build: sync build-java build-admin

migrate:
	psql "$$DATABASE_URL" -f migrations/0001_init_pgvector.sql

ingest:
	uv run python scripts/ingest_docs.py ./docs

up:
	docker compose up -d --build

down:
	docker compose down -v
