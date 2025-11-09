#SPDX-License-Identifier: Apache-2.0
# File: Makefile v.2.0 --refactored--
# Project: AstraDesk Enterprise AI Agents Framework
# Description:
#     Central Makefile for AstraDesk Enterprise AI Agents Framework.
#     Automates dev tasks: deps, lint, test, build, Docker, Terraform, CM (Ansible/Puppet/Salt), Istio, Helm, certs.
#     Supports polyglot: Python 3.14+, Java 25, Node 22+, Postgres 18.
# Author: Siergej Sobolewski
# Since: 2025-11-09

# --- Configuration Variables ---
DOCKER_COMPOSE := docker compose
KUBECTL := kubectl
ISTIOCTL := istioctl
UV := uv
GRADLEW := ./gradlew
NPM := npm
TERRAFORM := terraform
ANSIBLE := ansible-playbook
PUPPET := puppet
SALT := salt
HELM := helm
PYTHON_VERSION := 3.14
JAVA_VERSION := 25
NODE_VERSION := 22.21
TERRAFORM_DIR := infra
ANSIBLE_INVENTORY := ansible/inventories/dev/hosts.ini
PUPPET_MANIFEST := puppet/manifests/astradesk.pp
SALT_STATE := astradesk

# --- Dependency Checks ---
HAS_DOCKER := $(shell command -v $(DOCKER_COMPOSE) 2> /dev/null)
HAS_UV := $(shell command -v $(UV) 2> /dev/null)
HAS_KUBECTL := $(shell command -v $(KUBECTL) 2> /dev/null)
HAS_ISTIOCTL := $(shell command -v $(ISTIOCTL) 2> /dev/null)
HAS_GRADLEW := $(shell test -f $(GRADLEW) && echo 1)
HAS_NPM := $(shell command -v $(NPM) 2> /dev/null)
HAS_PSQL := $(shell command -v psql 2> /dev/null)
HAS_TERRAFORM := $(shell command -v $(TERRAFORM) 2> /dev/null)
HAS_ANSIBLE := $(shell command -v $(ANSIBLE) 2> /dev/null)
HAS_PUPPET := $(shell command -v $(PUPPET) 2> /dev/null)
HAS_SALT := $(shell command -v $(SALT) 2> /dev/null)
HAS_HELM := $(shell command -v $(HELM) 2> /dev/null)

# --- Phony Targets ---
.PHONY: help all sync lint type test test-python test-java test-admin test-mcp build build-python build-java build-admin build-mcp docker-build docker-push up down up-deps run-local logs logs-api logs-auditor migrate ingest ingest-support ingest-ops ingest-all clean apply-istio verify-istio store-secrets helm-deploy terraform-init terraform-validate terraform-plan terraform-apply ansible-deploy puppet-deploy salt-deploy test-config-mgmt test-packs build-packs helm-lint helm-test verify-mtls pack-build pack-publish nl2flow-generate

.DEFAULT_GOAL := help

# --- Main Targets ---

help:
	@echo "AstraDesk Enterprise AI Agents Framework"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Main Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -v '## Helper' | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Helper Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep '## Helper' | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

all: lint test build apply-istio terraform-apply helm-deploy verify-mtls ## Run lint, tests, build, Istio, Terraform, Helm deploy, mTLS verification

# --- Python Environment Management (uv workspace) ---

sync: ## Sync Python dependencies with uv
ifndef HAS_UV
	@echo "Error: 'uv' command not found."
	@exit 1
endif
	$(UV) sync --all-extras --frozen

sync-cu121: ## Sync with PyTorch CU121 optional deps
	$(UV) sync --all-extras --extra cu121 --frozen

lint: ## Run linter (ruff) on the entire project
ifndef HAS_UV
	@echo "Error: 'uv' not found." >&2; exit 1
endif
	$(UV) run ruff check .

type: ## Run static type checking (mypy) on the entire project
ifndef HAS_UV
	@echo "Error: 'uv' not found." >&2; exit 1
endif
	$(UV) run mypy .

# --- Testing (Polyglot) ---

test: test-python test-java test-admin ## Run all tests (Python, Java, Node.js)

test-python: sync ## Run Python tests (core + domain packs)
	@echo "Running Python tests for the entire workspace..."
	$(UV) run pytest -v --cov --cov-report=xml --junitxml=pytest-report.xml

test-java: ## Run Java tests for all modules
ifndef HAS_GRADLEW
	@echo "Error: './gradlew' not found." >&2; exit 1
endif
	$(GRADLEW) test jacocoTestReport

test-admin: ## Run tests for Admin Portal (Node.js)
ifndef HAS_NPM
	@echo "Error: 'npm' not found." >&2; exit 1
endif
	cd services/admin-portal && $(NPM) ci && $(NPM) test -- --coverage

test-mcp: ## Run tests for MCP Gateway
	@echo "Running MCP Gateway tests..."
	cd mcp && $(UV) run pytest -v

# --- Building (Polyglot) ---

build: build-python build-java build-admin ## Build all artifacts (Python, Java, Node.js)

build-python: sync ## Install Python dependencies
	@echo "Python dependencies synchronized."

build-java: ## Build all Java modules
ifndef HAS_GRADLEW
	@echo "Error: './gradlew' not found." >&2; exit 1
endif
	$(GRADLEW) build -x test  # Skip tests (already run)

build-admin: ## Build production version of Admin Portal
ifndef HAS_NPM
	@echo "Error: 'npm' not found." >&2; exit 1
endif
	cd services/admin-portal && $(NPM) ci && $(NPM) run build

build-mcp: ## Build MCP Gateway
	@echo "Building MCP Gateway..."
	cd mcp && $(UV) sync && $(UV) run python -m build

# --- Docker Management ---

docker-build: ## Build Docker images for all services
ifndef HAS_DOCKER
	@echo "Error: 'docker compose' not found." >&2; exit 1
endif
	$(DOCKER_COMPOSE) build api ticket-adapter admin-portal auditor mcp

docker-push: ## Push Docker images to registry
ifndef HAS_DOCKER
	@echo "Error: 'docker compose' not found." >&2; exit 1
endif
	$(DOCKER_COMPOSE) push api ticket-adapter admin-portal auditor mcp

up: docker-build ## Build and start all services in Docker Compose
ifndef HAS_DOCKER
	@echo "Error: 'docker compose' not found." >&2; exit 1
endif
	$(DOCKER_COMPOSE) up --build -d

down: ## Stop and remove all containers, networks, and volumes
ifndef HAS_DOCKER
	@echo "Error: 'docker compose' not found." >&2; exit 1
endif
	$(DOCKER_COMPOSE) down -v

up-deps: ## Start only external dependencies in Docker
ifndef HAS_DOCKER
	@echo "Error: 'docker compose' not found." >&2; exit 1
endif
	$(DOCKER_COMPOSE) up -d db mysql redis nats ticket-adapter mcp

run-local: up-deps ## Run API locally with dependencies in Docker
ifndef HAS_UV
	@echo "Error: 'uv' not found." >&2; exit 1
endif
	@echo "Starting API server locally on port 8000..."
	$(UV) run uvicorn src.gateway.main:app --host 0.0.0.0 --port 8000 --reload --app-dir src

logs: ## Show live logs for all containers
	$(DOCKER_COMPOSE) logs -f

logs-api: ## Show live logs for 'api' service
	$(DOCKER_COMPOSE) logs -f api

logs-auditor: ## Show live logs for 'auditor' service
	$(DOCKER_COMPOSE) logs -f auditor

# --- Data Operations ---

migrate: ## Initialize Postgres database with pgvector
ifndef HAS_PSQL
	@echo "Error: 'psql' not found." >&2; exit 1
endif
ifndef DATABASE_URL
	@echo "Error: 'DATABASE_URL' not set." >&2; exit 1
endif
	psql "$(DATABASE_URL)" -f migrations/0001_init_pgvector.sql

ingest: sync ## Process documents from ./docs and populate RAG database
	$(UV) run python scripts/ingest_docs.py ./docs

ingest-support: ## Przetwarza dokumenty z datasets/support i zasila RAG dla SupportAgent
	$(UV) run python scripts/ingest_docs.py support

ingest-ops: ## Przetwarza dokumenty z datasets/ops i zasila RAG dla OpsAgent
	$(UV) run python scripts/ingest_docs.py ops

ingest-all: ingest-support ingest-ops ## Przetwarza WSZYSTKIE datasety
	@echo "All datasets ingested."

# --- Istio and Certificate Management ---

apply-istio: ## Apply Istio configurations
ifndef HAS_KUBECTL
	@echo "Error: 'kubectl' not found." >&2; exit 1
endif
	$(KUBECTL) apply -f deploy/istio/

verify-istio: ## Verify Istio configurations
ifndef HAS_ISTIOCTL
	@echo "Error: 'istioctl' not found." >&2; exit 1
endif
	$(ISTIOCTL) analyze -n astradesk-prod

verify-mtls: ## Verify mTLS configuration
ifndef HAS_KUBECTL
	@echo "Error: 'kubectl' not found." >&2; exit 1
endif
	$(KUBECTL) get peerauthentication -n astradesk-prod -o jsonpath='{.items[*].spec.mtls.mode}' | grep -q STRICT && echo "mTLS is STRICT" || exit 1
	$(HELM) test astradesk --namespace astradesk-prod

store-secrets: ## Store mTLS certificate in Admin API
ifndef HAS_KUBECTL
	@echo "Error: 'kubectl' not found." >&2; exit 1
endif
ifndef JWT_TOKEN
	@echo "Error: 'JWT_TOKEN' not set." >&2; exit 1
endif
	$(KUBECTL) get secret -n astradesk-prod astradesk-tls -o jsonpath='{.data.tls\.crt}' | base64 -d > mtls-cert.pem
	curl -X POST http://localhost:8080/api/admin/v1/secrets -H "Authorization: Bearer $(JWT_TOKEN)" -d '{"name": "astradesk_mtls", "type":"certificate","value": "'"$$(cat mtls-cert.pem)"'"}'
	rm -f mtls-cert.pem

# --- Terraform Management ---

terraform-init: ## Initialize Terraform
ifndef HAS_TERRAFORM
	@echo "Error: 'terraform' not found. Install: https://www.terraform.io/downloads.html" >&2; exit 1
endif
	$(TERRAFORM) -chdir=$(TERRAFORM_DIR) init

terraform-validate: ## Validate Terraform configuration
ifndef HAS_TERRAFORM
	@echo "Error: 'terraform' not found." >&2; exit 1
endif
	$(TERRAFORM) -chdir=$(TERRAFORM_DIR) validate

terraform-plan: ## Plan Terraform changes
ifndef HAS_TERRAFORM
	@echo "Error: 'terraform' not found." >&2; exit 1
endif
	$(TERRAFORM) -chdir=$(TERRAFORM_DIR) plan -var-file="$(TERRAFORM_DIR)/terraform.tfvars" -out=plan.out

terraform-apply: ## Apply Terraform changes
ifndef HAS_TERRAFORM
	@echo "Error: 'terraform' not found." >&2; exit 1
endif
	$(TERRAFORM) -chdir=$(TERRAFORM_DIR) apply -auto-approve plan.out

# --- Configuration Management (Ansible/Puppet/Salt) ---

ansible-deploy: ## Deploy with Ansible
ifndef HAS_ANSIBLE
	@echo "Error: 'ansible-playbook' not found. Install: https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html" >&2; exit 1
endif
	$(ANSIBLE) -i $(ANSIBLE_INVENTORY) ansible/playbook.yml

puppet-deploy: ## Deploy with Puppet
ifndef HAS_PUPPET
	@echo "Error: 'puppet' not found. Install: https://puppet.com/docs/puppet/latest/install_puppet.html" >&2; exit 1
endif
	$(PUPPET) apply $(PUPPET_MANIFEST)

salt-deploy: ## Deploy with Salt
ifndef HAS_SALT
	@echo "Error: 'salt' not found. Install: https://docs.saltproject.io/en/latest/topics/installation/index.html" >&2; exit 1
endif
	$(SALT) '*' state.apply $(SALT_STATE)

test-config-mgmt: ## Test configuration management (Ansible/Puppet/Salt) ## Helper
ifndef HAS_ANSIBLE
	@echo "Warning: 'ansible-playbook' not found, skipping Ansible test." >&2
else
	$(ANSIBLE) -i $(ANSIBLE_INVENTORY) ansible/playbook.yml --check
endif
ifndef HAS_PUPPET
	@echo "Warning: 'puppet' not found, skipping Puppet test." >&2
else
	$(PUPPET) apply $(PUPPET_MANIFEST) --noop
endif
ifndef HAS_SALT
	@echo "Warning: 'salt' not found, skipping Salt test." >&2
else
	$(SALT) '*' state.apply $(SALT_STATE) test=True
endif

# --- Helm Management ---

helm-lint: ## Lint Helm chart
ifndef HAS_HELM
	@echo "Error: 'helm' not found. Install: https://helm.sh/docs/intro/install/" >&2; exit 1
endif
	$(HELM) lint deploy/chart

helm-test: ## Run Helm tests
ifndef HAS_HELM
	@echo "Error: 'helm' not found. Install: https://helm.sh/docs/intro/install/" >&2; exit 1
endif
	$(HELM) test astradesk --namespace astradesk-prod

helm-deploy: ## Deploy to Kubernetes using Helm
ifndef HAS_KUBECTL
	@echo "Error: 'kubectl' not found." >&2; exit 1
endif
	$(HELM) upgrade --install astradesk deploy/chart \
		--namespace astradesk-prod \
		--create-namespace \
		--wait --timeout 5m \
		--set database.postgres.host=$(shell $(TERRAFORM) -chdir=$(TERRAFORM_DIR) output -raw rds_postgres_endpoint) \
		--set database.mysql.host=$(shell $(TERRAFORM) -chdir=$(TERRAFORM_DIR) output -raw rds_mysql_endpoint)

# --- Domain Packs Management ---

pack-build: ## Builds a specific Domain Pack (make pack-build PACK=domain-support)
ifndef PACK
	@echo "Error: Specify PACK=domain-support or similar."
	@exit 1
endif
	cd packages/$(PACK) && $(UV) sync && $(UV) run pytest

pack-publish: ## Publishes Domain Pack to PyPI (requires credentials)
ifndef PACK
	@echo "Error: Specify PACK=domain-support."
	@exit 1
endif
	cd packages/$(PACK) && $(UV) build && $(UV) publish

# --- NL2Flow Tools ---

nl2flow-generate: ## Generates YAML flow from natural language prompt (make nl2flow-generate PROMPT="Build JIRA monitor")
ifndef PROMPT
	@echo "Error: Specify PROMPT='your natural language description'."
	@exit 1
endif
	$(UV) run python scripts/nl2flow.py "$(PROMPT)" > generated_flow.yaml
	@echo "Generated flow saved to generated_flow.yaml"

clean: ## Remove generated files and cache
	@echo "Cleaning project..."
	rm -rf .pytest_cache .mypy_cache coverage.xml pytest-report.xml $(TERRAFORM_DIR)/plan.out mtls-cert.pem
	find . -type d -name "__pycache__" -exec rm -r {} +
	$(GRADLEW) clean || true
	cd services/admin-portal && rm -rf .next node_modules || true
	@echo "Cleanup completed."

test-packs: ## Run tests for all domain packs ## Helper
	for pack in packages/domain-*; do \
		cd $$pack && $(UV) run pytest tests && cd ../..; \
	done

build-packs: ## Build all domain packs ## Helper
	for pack in packages/domain-*; do \
		cd $$pack && $(UV) sync --frozen && cd ../..; \
	done
