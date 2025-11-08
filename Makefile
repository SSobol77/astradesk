#SPDX-License-Identifier: Apache-2.0
# File: Makefile v.2.0 --refactored--
# Description:
#     Central Makefile for AstraDesk Enterprise AI Agents Framework.
#     Automates dev tasks: deps, lint, test, build, Docker, Terraform, CM (Ansible/Puppet/Salt), Istio, Helm, certs.
#     Supports polyglot: Python 3.14+, Java 25, Node 22+, Postgres 18.
# Author: Siergej Sobolewski
# Since: 2025-10-25

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
HAS_UV := $(shell command -v $(UV) 2>/dev/null)
HAS_KUBECTL := $(shell command -v $(KUBECTL) 2> /dev/null)
HAS_ISTIOCTL := $(shell command -v $(ISTIOCTL) 2> /dev/null)
HAS_GRADLEW := $(shell test -f $(GRADLEW) && echo 1)
HAS_NPM := $(shell command -v $(NPM) 2> /dev/null)
HAS_PSQL := $(shell command -v psql 2> /dev/null)
HAS_TERRAFORM := $(shell command -v $(TERRAFORM) 2>/dev/null)
HAS_ANSIBLE := $(shell command -v $(ANSIBLE) 2> /dev/null)
HAS_PUPPET := $(shell command -v $(PUPPET) 2> /dev/null)
HAS_SALT := $(shell command -v $(SALT) 2> /dev/null)
HAS_HELM := $(shell command -v $(HELM) 2> /dev/null)

# --- Phony Targets ---
.PHONY: help all sync lint type test test-python test-java test-admin test-mcp build build-python build-java build-admin build-mcp docker-build docker-push up down up-depsrun-locallogs logs-api logs-auditor migrate ingest ingest-support ingest-ops ingest-all clean apply-istio verify-istio store-secrets helm-deploy terraform-init terraform-validate terraform-plan terraform-apply ansible-deploy puppet-deploy salt-deploy test-config-mgmt test-packs build-packshelm-lint helm-test verify-mtls pack-build pack-publish nl2flow-generate

.DEFAULT_GOAL := help

# --- Main Targets ---

help:
	@echo "AstraDesk Enterprise AI Agents Framework"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo"Main Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$'$(MAKEFILE_LIST) | grep -v '## Helper' | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
@echo "Helper Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep '## Helper'| sort | awk 'BEGIN {FS= ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

all: lint test build apply-istio terraform-apply helm-deployverify-mtls ## Runlint,tests, build, Istio, Terraform, Helm deploy, mTLS verification

# --- Python Environment Management (uv workspace) ---

sync: ## Sync Python dependencies with uv
ifndef HAS_UV
@echo "Error: 'uv' command not found."
	@exit 1
endif
	$(UV)sync --all-extras --frozen

sync-cu121: ## Sync with PyTorch CU121 optional deps
	$(UV) sync --all-extras --extracu121 --frozen

lint: ## Run linter (ruff) on the entireproject
ifndefHAS_UV
	@echo "Error: 'uv' not found.">&2; exit 1
endif
	$(UV) run ruff check .

type: ## Run static type checking (mypy) on the entire project
ifndef HAS_UV
	@echo "Error: 'uv'notfound.">&2; exit 1
endif
	$(UV) run mypy .

#--- Testing (Polyglot) ---

test:test-python test-java test-admin ## Run all tests(Python, Java, Node.js)

test-python:sync ## Run Python tests(core + domain packs)
	@echo "Running Pythontests for the entire workspace..."
	$(UV) run pytest -v --cov--cov-report=xml --junitxml=pytest-report.xml

test-java: ## Run Java tests forall modules
ifndef HAS_GRADLEW
	@echo "Error: './gradlew' notfound." >&2; exit 1
endif
	$(GRADLEW) test jacocoTestReport

test-admin: ## Run tests for Admin Portal (Node.js)
ifndef HAS_NPM
	@echo "Error: 'npm' not found." >&2; exit 1
endif
	cd services/admin-portal&& $(NPM) ci && $(NPM) test -- --coverage

test-mcp: ##Run testsfor MCP Gateway
	@echo "Running MCP Gatewaytests..."
	cd mcp && $(UV)run pytest -v
#---Building(Polyglot)---

build: build-python build-java build-admin## Build all artifacts(Python, Java, Node.js)

build-python: sync##Install Python dependencies
	@echo "Python dependencies synchronized."

build-java: ##Build all Java modules
ifndef HAS_GRADLEW
	@echo "Error: './gradlew'notfound." >&2; exit1
endif
	$(GRADLEW) build -xtest  # Skiptests(already run)

build-admin: ## Build production version of Admin Portal
ifndef HAS_NPM
	@echo "Error: 'npm' not found." >&2; exit 1
endif
	cd services/admin-portal &&$(NPM) ci && $(NPM) runbuild

build-mcp: ##BuildMCP Gateway
	@echo "Building MCP Gateway..."
	cd mcp &&$(UV) sync && $(UV) run python-m build

# ---DockerManagement---

docker-build: ##Build Dockerimages for all services
ifndef HAS_DOCKER
	@echo "Error:'docker compose'not found." >&2; exit 1
endif
$(DOCKER_COMPOSE) build api ticket-adapter admin-portal auditor mcpdocker-push: ##PushDocker images to registry
ifndef HAS_DOCKER
	@echo "Error: 'docker compose' not found." >&2; exit 1
#endif
	$(DOCKER_COMPOSE) push api ticket-adapter admin-portal auditor mcp

up: docker-build ## Build and start allservices in Docker Compose
ifndef HAS_DOCKER
	@echo"Error: 'docker compose' not found." >&2; exit 1
endif$(DOCKER_COMPOSE) up--build -ddown: ##Stopand remove all containers, networks, and volumes
ifndef HAS_DOCKER
	@echo "Error: 'docker compose' not found." >&2; exit 1
#endif
	$(DOCKER_COMPOSE) down-v

up-deps:## Startonly externaldependenciesin Docker
#ifndefHAS_DOCKER
	@echo "Error: 'docker compose' not found." >&2; exit 1
#endif
	$(DOCKER_COMPOSE) up -d db mysql redis nats ticket-adapter mcp

run-local:up-deps ## Run APIlocally withdependencies in Docker
#ifndefHAS_UV
	@echo "Error: 'uv' not found." >&2; exit 1
#endif
	@echo "Starting API server locally on port 8000..."
	$(UV) run uvicorn src.gateway.main:app --host 0.0.0.0 --port8000 --reload --app-dir src

logs: ## Showlive logsfor all containers
$(DOCKER_COMPOSE) logs-f

logs-api: ##Showlive logs for 'api' service$(DOCKER_COMPOSE) logs -f apilogs-auditor:## Showlive logsfor'auditor' service
	$(DOCKER_COMPOSE) logs -fauditor# --- Data Operations ---

migrate:## Initialize Postgresdatabasewith pgvector
ifndef HAS_PSQL
@echo"Error: 'psql' not found." >&2;exit 1endif
ifndef DATABASE_URL@echo "Error: 'DATABASE_URL'not set." >&2;exit 1
endif
	psql "$(DATABASE_URL)" -fmigrations/0001_init_pgvector.sqlingest: sync ##Process documents from ./docs and populate RAG database$(UV) run pythonscripts/ingest_docs.py ./docs

ingest-support: ## Przetwarza dokumenty z`datasets/support` i zasila RAGdla SupportAgent.
	uvrunpython scripts/ingest_docs.pysupport

ingest-ops: ## Przetwarza dokumentyz`datasets/ops` izasila RAGdla OpsAgent.
uv run python scripts/ingest_docs.py ops

ingest-all: ingest-support ingest-ops ##Przetwarza WSZYSTKIE datasety.
	@echo "All datasets ingested."
	

# --- IstioandCertificateManagement---

apply-istio:##Apply Istioconfigurations
ifndef HAS_KUBECTL
	@echo"Error:'kubectl' not found." >&2; exit1endif
$(KUBECTL) apply -f deploy/istio/

verify-istio: ##Verify Istio configurationsifndef HAS_ISTIOCTL
@echo "Error: 'istioctl'not found." >&2;exit1endif
$(ISTIOCTL) analyze -n astradesk-prod

verify-mtls: ##Verify mTLS configuration
ifndefHAS_KUBECTL@echo "Error: 'kubectl'not found." >&2; exit 1endif
$(KUBECTL) get peerauthentication-n astradesk-prod -o jsonpath='{.items[*].spec.mtls.mode}' | grep -qSTRICT && echo "mTLS is STRICT" ||exit 1
	$(HELM) testastradesk--namespace astradesk-prod

store-secrets:## Store mTLS certificatein Admin APIifndef HAS_KUBECTL
	@echo "Error: 'kubectl' not found." >&2;exit 1
endif
ifndefJWT_TOKEN
@echo "Error:'JWT_TOKEN' not set." >&2;exit 1endif
	$(KUBECTL) get secret -nastradesk-prod astradesk-tls -o jsonpath='{.data.tls\.crt}' |base64-d> mtls-cert.pem
curl-X POSThttp://localhost:8080/api/admin/v1/secrets-H "Authorization: Bearer$(JWT_TOKEN)" -d'{"name": "astradesk_mtls", "type":"certificate","value": "'"$$(cat mtls-cert.pem)"'"}'
	rm-f mtls-cert.pem#--- Terraform Management ---

terraform-init: ## InitializeTerraformifndef HAS_TERRAFORM
@echo "Error:'terraform' not found. Install:https://www.terraform.io/downloads.html" >&2; exit 1
endif$(TERRAFORM) -chdir=$(TERRAFORM_DIR) init

terraform-validate: ##ValidateTerraform configurationifndefHAS_TERRAFORM@echo "Error: 'terraform' not found.">&2;exit 1endif
$(TERRAFORM) -chdir=$(TERRAFORM_DIR)validateterraform-plan: ## PlanTerraform changes
ifndef HAS_TERRAFORM@echo "Error:'terraform'notfound." >&2;exit 1endif
$(TERRAFORM) -chdir=$(TERRAFORM_DIR) plan-var-file="$(TERRAFORM_DIR)/terraform.tfvars"-out=plan.outterraform-apply: ##ApplyTerraform changes
ifndef HAS_TERRAFORM
@echo"Error: 'terraform'notfound.">&2; exit 1endif$(TERRAFORM)-chdir=$(TERRAFORM_DIR) apply-auto-approve plan.out

#---ConfigurationManagement(Ansible/Puppet/Salt)---

ansible-deploy: ## Deploy with AnsibleifndefHAS_ANSIBLE
@echo "Error: 'ansible-playbook' not found.Install: https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html" >&2; exit 1
endif$(ANSIBLE)-i $(ANSIBLE_INVENTORY) ansible/playbook.ymlpuppet-deploy:## DeploywithPuppet
ifndef HAS_PUPPET
	@echo "Error:'puppet'notfound. Install:https://puppet.com/docs/puppet/latest/install_puppet.html" >&2; exit 1endif
$(PUPPET) apply $(PUPPET_MANIFEST)

salt-deploy:## Deploywith Saltifndef HAS_SALT
@echo "Error: 'salt'notfound.Install:https://docs.saltproject.io/en/latest/topics/installation/index.html" >&2;exit 1endif$(SALT) '*' state.apply $(SALT_STATE)

test-config-mgmt: ## Test configuration management(Ansible/Puppet/Salt) ## Helperifndef HAS_ANSIBLE@echo"Warning:'ansible-playbook' notfound, skipping Ansible test.">&2else
$(ANSIBLE) -i$(ANSIBLE_INVENTORY) ansible/playbook.yml --check
endififndef HAS_PUPPET
	@echo "Warning:'puppet'not found,skippingPuppet test.">&2
else$(PUPPET) apply $(PUPPET_MANIFEST)--noopendififndef HAS_SALT
	@echo "Warning: 'salt' not found, skippingSalt test." >&2
else
	$(SALT)'*' state.apply$(SALT_STATE)test=Trueendif#---HelmManagement ---

helm-lint: ## Lint Helm chart
ifndefHAS_HELM
@echo "Error: 'helm'not found.Install: https://helm.sh/docs/intro/install/" >&2; exit 1
endif$(HELM)lintdeploy/chart

helm-test:##Run Helmtestsifndef HAS_HELM@echo"Error: 'helm'notfound.Install: https://helm.sh/docs/intro/install/" >&2; exit1endif
	$(HELM) test astradesk --namespace astradesk-prod

helm-deploy:## DeploytoKubernetesusing Helmifndef HAS_KUBECTL
@echo"Error: 'kubectl' not found." >&2; exit 1endif
	$(HELM) upgrade--installastradesk deploy/chart\
		--namespace astradesk-prod \
		--create-namespace\
--wait--timeout5m\
		--setdatabase.postgres.host=$(shell $(TERRAFORM) -chdir=$(TERRAFORM_DIR) output-raw rds_postgres_endpoint)\
		--set database.mysql.host=$(shell$(TERRAFORM)-chdir=$(TERRAFORM_DIR) output -raw rds_mysql_endpoint)


#---DomainPacksManagement---

pack-build: ## Builds aspecificDomainPack (makepack-build PACK=domain-support)
ifndef PACK
	@echo"Error: Specify PACK=domain-support orsimilar."
@exit 1endifcd packages/$(PACK) && uvsync &&uvrun pytest

pack-publish: ##PublishesDomainPackto PyPI(requires credentials)
ifndefPACK@echo "Error: Specify PACK=domain-support."
	@exit 1
endifcd packages/$(PACK) && uvbuild && uvpublish#---NL2Flow Tools---

nl2flow-generate:##Generates YAMLflow fromnaturallanguageprompt(make nl2flow-generate PROMPT="Build JIRAmonitor")
ifndef PROMPT
@echo "Error: SpecifyPROMPT='your naturallanguage description'."
	@exit 1
endif
	uvrun pythonscripts/nl2flow.py "$(PROMPT)" >generated_flow.yaml@echo"Generated flowsavedto generated_flow.yaml"

clean: ## Removegenerated files and cache
@echo"Cleaning project..."
	rm-rf .pytest_cache.mypy_cache coverage.xml pytest-report.xml $(TERRAFORM_DIR)/plan.out mtls-cert.pem
find .-typed -name "__pycache__"-exec rm-r{} +
	$(GRADLEW) clean || true
	cd services/admin-portal &&rm -rf .nextnode_modules ||true
@echo"Cleanup completed."

test-packs:##Run tests for all domainpacks ## Helper
forpack in packages/domain-*; do \
cd$$pack&&$(UV) runpytesttests && cd ../..; \
	done

build-packs: ##Build alldomain packs ## Helperfor packin packages/domain-*; do \
		cd$$pack &&$(UV) sync--frozen&& cd ../..;\
	done