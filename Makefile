# SPDX-License-Identifier: Apache-2.0
# AstraDesk Development Makefile

.PHONY: help setup clean test lint format docker-up docker-down docker-logs dev-server install-deps update-deps docs build deploy

# Default target
help: ## Show this help message
	@echo "AstraDesk Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Setup and installation
setup: ## Set up complete development environment
	@echo "Setting up AstraDesk development environment..."
	@./scripts/setup-dev-environment.sh

install-deps: ## Install all Python dependencies
	@echo "Installing Python dependencies..."
	@pip install -e ./core
	@pip install -r services/api-gateway/requirements.txt
	@pip install -r mcp/requirements.txt
	@for pack in packages/domain-*; do \
		if [ -f $$pack/requirements.txt ]; then \
			echo "Installing $$pack dependencies..."; \
			pip install -r $$pack/requirements.txt; \
		fi; \
	done
	@pip install pytest pytest-asyncio pytest-cov black isort mypy ruff pre-commit

update-deps: ## Update all Python dependencies
	@echo "Updating Python dependencies..."
	@pip install --upgrade pip
	@pip install --upgrade -e ./core
	@pip install --upgrade -r services/api-gateway/requirements.txt
	@pip install --upgrade -r mcp/requirements.txt

# Development server
dev-server: ## Start development server with hot reload
	@echo "Starting development server..."
	@python -m uvicorn services.api_gateway.src.gateway.main:app --host 0.0.0.0 --port 8000 --reload

# Docker commands
docker-up: ## Start all Docker services
	@echo "Starting Docker services..."
	@docker-compose -f docker-compose.dev.yml up -d

docker-down: ## Stop all Docker services
	@echo "Stopping Docker services..."
	@docker-compose -f docker-compose.dev.yml down

docker-logs: ## Show Docker service logs
	@docker-compose -f docker-compose.dev.yml logs -f

docker-build: ## Build all Docker images
	@echo "Building Docker images..."
	@docker-compose -f docker-compose.dev.yml build

# Testing
test: ## Run all tests
	@echo "Running test suite..."
	@python -m pytest tests/ -v --cov=services/api_gateway --cov=mcp --cov-report=html --cov-report=term

test-unit: ## Run unit tests only
	@echo "Running unit tests..."
	@python -m pytest tests/ -k "not integration" -v

test-integration: ## Run integration tests only
	@echo "Running integration tests..."
	@python -m pytest tests/integration_tests.py -v

test-red-team: ## Run red team security tests
	@echo "Running red team tests..."
	@python -m pytest tests/red_team_tests.py -v

test-harness: ## Run offline evaluation harness
	@echo "Running test harness..."
	@python tests/test_harness.py

test-all: test test-integration test-red-team ## Run all test suites

# Code quality
lint: ## Run all linters
	@echo "Running linters..."
	@ruff check .
	@mypy services/api_gateway mcp packages --ignore-missing-imports

format: ## Format code with black and isort
	@echo "Formatting code..."
	@black .
	@isort .

format-check: ## Check code formatting without making changes
	@echo "Checking code formatting..."
	@black --check .
	@isort --check-only .

# Documentation
docs: ## Build documentation
	@echo "Building documentation..."
	@mkdocs build

docs-serve: ## Serve documentation locally
	@echo "Serving documentation..."
	@mkdocs serve

# Database operations
db-migrate: ## Run database migrations
	@echo "Running database migrations..."
	@python -c "from services.api_gateway.src.runtime.memory import Memory; import asyncio; asyncio.run(Memory(None, None).migrate())"

db-seed: ## Seed database with test data
	@echo "Seeding database..."
	@python scripts/seed_kb.py

# MCP servers
mcp-support: ## Start MCP Support server
	@echo "Starting MCP Support server..."
	@python packages/domain-support/tools/mcp_server.py

mcp-ops: ## Start MCP Ops server
	@echo "Starting MCP Ops server..."
	@python packages/domain-ops/tools/mcp_server.py

mcp-finance: ## Start MCP Finance server
	@echo "Starting MCP Finance server..."
	@python packages/domain-finance/tools/mcp_server.py

mcp-supply: ## Start MCP Supply Chain server
	@echo "Starting MCP Supply Chain server..."
	@python packages/domain-supply/tools/mcp_server.py

mcp-all: ## Start all MCP servers
	@echo "Starting all MCP servers..."
	@make -j4 mcp-support mcp-ops mcp-finance mcp-supply

# CI/CD
ci: lint test ## Run CI pipeline locally

# Cleanup
clean: ## Clean up temporary files and caches
	@echo "Cleaning up..."
	@find . -type d -name __pycache__ -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name "*.pyd" -delete
	@find . -type f -name ".coverage" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} +
	@find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@find . -type d -name ".mypy_cache" -exec rm -rf {} +
	@rm -rf htmlcov/
	@rm -rf .coverage
	@rm -rf dist/
	@rm -rf build/

clean-docker: ## Clean up Docker containers and volumes
	@echo "Cleaning up Docker..."
	@docker-compose -f docker-compose.dev.yml down -v
	@docker system prune -f

clean-all: clean clean-docker ## Clean everything

# Development workflow
dev: ## Start full development environment
	@echo "Starting full development environment..."
	@make docker-up
	@sleep 30  # Wait for services to start
	@make dev-server

stop: ## Stop all development services
	@echo "Stopping development environment..."
	@make docker-down
	@pkill -f uvicorn || true

# Build and deployment
build: ## Build all components
	@echo "Building all components..."
	@docker-compose -f docker-compose.dev.yml build

build-prod: ## Build for production
	@echo "Building for production..."
	@docker build -f services/api-gateway/Dockerfile -t astradesk/api-gateway:latest .
	@docker build -f mcp/Dockerfile -t astradesk/mcp-gateway:latest .

deploy-local: ## Deploy to local Kubernetes (requires k3s/kind)
	@echo "Deploying to local Kubernetes..."
	@helm upgrade --install astradesk ./deploy/helm/astradesk --namespace astradesk --create-namespace

# Monitoring and debugging
logs: ## Show application logs
	@docker-compose -f docker-compose.dev.yml logs -f api-gateway

logs-all: ## Show all service logs
	@docker-compose -f docker-compose.dev.yml logs -f

health: ## Check health of all services
	@echo "Checking service health..."
	@curl -f http://localhost:8000/healthz && echo "✓ API Gateway healthy" || echo "✗ API Gateway unhealthy"
	@curl -f http://localhost:8001/health && echo "✓ MCP Support healthy" || echo "✗ MCP Support unhealthy"
	@curl -f http://localhost:8002/health && echo "✓ MCP Ops healthy" || echo "✗ MCP Ops unhealthy"
	@curl -f http://localhost:8003/health && echo "✓ MCP Finance healthy" || echo "✗ MCP Finance unhealthy"
	@curl -f http://localhost:8004/health && echo "✓ MCP Supply healthy" || echo "✗ MCP Supply unhealthy"

# Quick commands for common tasks
quick-test: ## Run quick test suite
	@python -m pytest tests/ -x --tb=short

quick-lint: ## Run quick linting
	@ruff check . --quiet

# Environment management
env-check: ## Check environment setup
	@echo "Checking environment..."
	@python --version
	@pip --version
	@docker --version
	@docker-compose --version

env-update: ## Update development environment
	@echo "Updating environment..."
	@pip install --upgrade pip
	@pre-commit autoupdate || true
	@npm update || true
