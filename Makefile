# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: Makefile
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

.ONESHELL:
.PHONY: help setup install-deps update-deps dev-server quick-test quick-lint test-unit test-integration test-red-team test-harness test test-all lint format format-check license-headers license-check verify-build-baseline docs docs-serve db-migrate db-seed env-check env-update ci docker-up docker-down docker-logs docker-build clean clean-docker clean-all dev stop logs logs-all health build build-prod deploy-local test-docker ci-local

# ------------------------------------------------------------------- #
# Configurable variables
# ------------------------------------------------------------------- #
PYTHON_EXEC ?= .venv/bin/python
PYTEST          ?= $(PYTHON_EXEC) -m pytest
RUFF            ?= $(PYTHON_EXEC) -m ruff
MYPY            ?= $(PYTHON_EXEC) -m mypy
BLACK           ?= $(PYTHON_EXEC) -m black
ISORT           ?= $(PYTHON_EXEC) -m isort
COMPOSE         ?= docker compose
COMPOSE_FILE    ?= docker-compose.yml

# ------------------------------------------------------------------- #
# Help
# ------------------------------------------------------------------- #
help:
	@echo "AstraDesk Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ------------------------------------------------------------------- #
# Setup
# ------------------------------------------------------------------- #
setup: ## Set up complete development environment
	@echo "Setting up AstraDesk development environment..."
	@if command -v ./scripts/setup-dev-environment.sh >/dev/null 2>&1; then \
		./scripts/setup-dev-environment.sh; \
	else \
		echo "setup script not found"; \
	fi

install-deps: ## Install all Python dependencies
	@echo "Installing Python dependencies with uv..."
	@uv pip install --python $(PYTHON_EXEC) -e ./core
	@uv pip install --python $(PYTHON_EXEC) -e services/api-gateway
	@uv pip install --python $(PYTHON_EXEC) -e mcp
	@for pack in packages/domain-*; do \
		if [ -d "$$pack" ]; then \
			echo "Installing $$pack dependencies..."; \
			uv pip install --python $(PYTHON_EXEC) -e "$$pack"; \
		fi; \
	done
	@uv pip install --python $(PYTHON_EXEC) pytest pytest-asyncio pytest-cov
	@uv pip install --python $(PYTHON_EXEC) ruff mypy black isort pre-commit

update-deps: ## Update all Python dependencies
	@echo "Updating Python dependencies with uv..."
	@uv pip install --upgrade --python $(PYTHON_EXEC) -e ./core
	@uv pip install --upgrade --python $(PYTHON_EXEC) -e services/api-gateway
	@uv pip install --upgrade --python $(PYTHON_EXEC) -e mcp

# ------------------------------------------------------------------- #
# Development server
# ------------------------------------------------------------------- #
dev-server: ## Start development server with hot reload
	@echo "Starting development server..."
	@$(PYTHON_EXEC) -m uvicorn services.api_gateway.src.gateway.main:app --host 0.0.0.0 --port 8000 --reload

quick-test: ## Run quick test suite
	@echo "Running quick tests..."
	@$(PYTEST) tests/ -x --tb=short

quick-lint: ## Run quick linting
	@echo "Running quick lint..."
	@$(RUFF) check . --quiet

# ------------------------------------------------------------------- #
# Docker commands
# ------------------------------------------------------------------- #
docker-up: ## Start all Docker services
	@echo "Starting Docker services..."
	@$(COMPOSE) -f $(COMPOSE_FILE) up -d

docker-down: ## Stop all Docker services
	@echo "Stopping Docker services..."
	@$(COMPOSE) -f $(COMPOSE_FILE) down

docker-logs: ## Show Docker service logs
	@$(COMPOSE) -f $(COMPOSE_FILE) logs -f

docker-build: ## Build all Docker images
	@echo "Building Docker images..."
	@$(COMPOSE) -f $(COMPOSE_FILE) build

# -------------------------------------------------------------------#
# Testing (local Python)
# -------------------------------------------------------------------#
test: ## Run all tests
	@echo "Running test suite..."
	@$(PYTEST) tests/ -v --cov=services/api_gateway --cov=mcp --cov-report=html --cov-report=term

test-unit: ## Run unit tests only
	@echo "Running unit tests..."
	@$(PYTEST) tests/ -k "not integration" -v

test-integration: ## Run integration tests only
	@echo "Running integration tests..."
	@$(PYTEST) tests/integration_tests.py -v

test-red-team: ## Run red team security tests
	@echo "Running red team tests..."
	@$(PYTEST) tests/red_team_tests.py -v

test-harness: ## Run offline evaluation harness
	@echo "Running test harness..."
	@$(PYTHON_EXEC) tests/test_harness.py

test-all: test test-integration test-red-team ## Run all test suites

# -------------------------------------------------------------------#
# Code quality
# -------------------------------------------------------------------#
lint: ## Run all linters
	@echo "Running linters..."
	@$(RUFF) check .
	@$(MYPY) services/api_gateway mcp packages --ignore-missing-imports

format: ## Format code with black and isort
	@echo "Formatting code..."
	@$(BLACK) .
	@$(ISORT) .

format-check: ## Check code formatting without making changes
	@echo "Checking code formatting..."
	@$(BLACK) --check .
	@$(ISORT) --check-only .

license-headers: ## Normalize project-owned license headers and metadata
	@$(PYTHON_EXEC) scripts/license_headers.py

license-check: ## Verify project-owned license headers and metadata
	@$(PYTHON_EXEC) scripts/license_headers.py --check

verify-build-baseline: ## Verify reproducible-build baseline (Dockerfiles, Compose graph, pinning)
	@echo "Verifying reproducible-build baseline..."
	@$(PYTHON_EXEC) scripts/ci/verify_build_baseline.py

# -------------------------------------------------------------------#
# Documentation
# -------------------------------------------------------------------#
docs: ## Build documentation
	@echo "Building documentation..."
	@mkdocs build

docs-serve: ## Serve documentation locally
	@echo "Serving documentation..."
	@mkdocs serve

# -------------------------------------------------------------------#
# Database operations
# -------------------------------------------------------------------#
db-migrate: ## Run database migrations
	@echo "Running database migrations..."
	@$(PYTHON_EXEC) -c "from services.api_gateway.src.runtime.memory import Memory; import asyncio; asyncio.run(Memory(None, None).migrate())"

db-seed: ## Seed database with test data
	@echo "Seeding database..."
	@$(PYTHON_EXEC) scripts/seed_kb.py

# -------------------------------------------------------------------#
# MCP servers
# -------------------------------------------------------------------#
mcp-support: ## Start MCP Support server
	@echo "Starting MCP Support server..."
	@$(PYTHON_EXEC) packages/domain-support/tools/mcp_server.py

mcp-ops: ## Start MCP Ops server
	@echo "Starting MCP Ops server..."
	@$(PYTHON_EXEC) packages/domain-ops/tools/mcp_server.py

mcp-finance: ## Start MCP Finance server
	@echo "Starting MCP Finance server..."
	@$(PYTHON_EXEC) packages/domain-finance/tools/mcp_server.py

mcp-supply: ## Start MCP Supply Chain server
	@echo "Starting MCP Supply Chain server..."
	@$(PYTHON_EXEC) packages/domain-supply/tools/mcp_server.py

mcp-all: ## Start all MCP servers
	@echo "Starting all MCP servers..."
	@$(MAKE) -j4 mcp-support mcp-ops mcp-finance mcp-supply

# -------------------------------------------------------------------#
# CI / Docker-dependent test path
# -------------------------------------------------------------------#
ci: lint test verify-build-baseline ## Run CI pipeline locally

test-docker: ## Start required services and run full test suite
	@echo "Starting services with Docker Compose..."
	@$(COMPOSE) -f $(COMPOSE_FILE) up -d --wait
	@echo "Running tests inside Docker-backed environment..."
	@$(MAKE) ci
	@echo "Stopping Docker services..."
	@$(COMPOSE) -f $(COMPOSE_FILE) down

ci-local: ## Full local CI parity: build, lint, test with Docker
	@echo "Running full local CI..."
	@$(MAKE) docker-build
	@$(MAKE) test-docker

# -------------------------------------------------------------------#
# Environment checks
# -------------------------------------------------------------------#
env-check: ## Check environment setup
	@echo "Checking environment..."
	@$(PYTHON_EXEC) --version
	@$(PYTHON_EXEC) -m pip --version
	@docker --version
	@$(COMPOSE) version

env-update: ## Update development environment
	@echo "Updating environment..."
	@uv pip install --upgrade --python $(PYTHON_EXEC) pip
	@uv pip install --upgrade --python $(PYTHON_EXEC) -e ./core
	@uv pip install --upgrade --python $(PYTHON_EXEC) -e services/api-gateway
	@uv pip install --upgrade --python $(PYTHON_EXEC) -e mcp
	@uv tool upgrade pre-commit || true

java-build: ## Build Java/Gradle services
	@echo "Running Gradle build..."
	@./gradlew --no-daemon build -x test

java-test: ## Run Java/Gradle tests
	@echo "Running Gradle tests..."
	@./gradlew --no-daemon test

# -------------------------------------------------------------------#
# Cleanup
# -------------------------------------------------------------------#
clean: ## Clean up temporary files and caches
	@echo "Cleaning up..."
	@find . -type d -name '__pycache__' -exec rm -rf {} +
	@find . -type f -name '*.pyc' -delete
	@find . -type f -name '*.pyo' -delete
	@find . -type f -name '*.pyd' -delete
	@find . -type f -name '.coverage' -delete
	@find . -type d -name '*.egg-info' -exec rm -rf {} +
	@find . -type d -name '.pytest_cache' -exec rm -rf {} +
	@find . -type d -name '.mypy_cache' -exec rm -rf {} +
	@rm -rf htmlcov/
	@rm -rf .coverage
	@rm -rf dist/
	@rm -rf build/

clean-docker: ## Clean up Docker containers and volumes
	@echo "Cleaning up Docker..."
	@$(COMPOSE) -f $(COMPOSE_FILE) down -v
	@docker system prune -f

clean-all: clean clean-docker ## Clean everything

# -------------------------------------------------------------------#
# Development workflow
# -------------------------------------------------------------------#
dev: ## Start full development environment
	@echo "Starting full development environment..."
	@$(MAKE) docker-up
	@echo "Waiting 30s for services..."
	@sleep 30
	@$(MAKE) dev-server

stop: ## Stop all development services
	@echo "Stopping development environment..."
	@$(MAKE) docker-down
	@pkill -f uvicorn || true

# -------------------------------------------------------------------#
# Build and deployment
# -------------------------------------------------------------------#
build: ## Build all components
	@echo "Building all components..."
	@$(COMPOSE) -f $(COMPOSE_FILE) build

build-prod: ## Build for production
	@echo "Building for production..."
	@docker build -f services/api-gateway/Dockerfile -t astradesk/api-gateway:latest .
	@docker build -f mcp/Dockerfile -t astradesk/mcp-gateway:latest .

deploy-local: ## Deploy to local Kubernetes (requires k3s/kind)
	@echo "Deploying to local Kubernetes..."
	@helm upgrade --install astradesk ./deploy/helm/astradesk --namespace astradesk --create-namespace

# -------------------------------------------------------------------#
# Monitoring and debugging
# -------------------------------------------------------------------#
logs: ## Show application logs
	@$(COMPOSE) -f $(COMPOSE_FILE) logs -f api-gateway

logs-all: ## Show all service logs
	@$(COMPOSE) -f $(COMPOSE_FILE) logs -f

health: ## Check health of all services
	@echo "Checking service health..."
	@curl -f http://localhost:8000/healthz && echo "✓ API Gateway healthy" || echo "✗ API Gateway unhealthy"
	@curl -f http://localhost:8001/health && echo "✓ MCP Support healthy" || echo "✗ MCP Support unhealthy"
	@curl -f http://localhost:8002/health && echo "✓ MCP Ops healthy" || echo "✗ MCP Ops unhealthy"
	@curl -f http://localhost:8003/health && echo "✓ MCP Finance healthy" || echo "✗ MCP Finance unhealthy"
	@curl -f http://localhost:8004/health && echo "✓ MCP Supply healthy" || echo "✗ MCP Supply unhealthy"
