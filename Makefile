# ==============================================================================
# Makefile for the AstraDesk Project
#
# Ten plik automatyzuje najczęstsze zadania deweloperskie, zapewniając
# spójne i powtarzalne środowisko pracy dla wszystkich członków zespołu.
# 
#  Polecenia:
#  ----------
# make help: Wyświetli Ci pięknie sformatowaną listę wszystkich dostępnych komend z ich opisami.
# make test-all: Uruchomi wszystkie testy w projekcie za jednym razem.
# make run-local: Automatycznie uruchomi najpierw zależności (make up-deps), a potem serwer Uvicorn.
# make clean: Przydatne, gdy chcesz mieć pewność, że zaczynasz od "czystego stołu".
# ==============================================================================

# --- Zmienne Konfiguracyjne ---
# Używamy `:=` aby zmienna była obliczana tylko raz.
PYTHON_INTERPRETER := python3
DOCKER_COMPOSE := docker compose

# --- Sprawdzanie Zależności ---
# Sprawdzamy, czy kluczowe komendy są dostępne w systemie.
# Jeśli nie, `make` zakończy działanie z czytelnym błędem.
HAS_DOCKER := $(shell command -v $(DOCKER_COMPOSE) 2> /dev/null)
HAS_UV := $(shell command -v uv 2> /dev/null)
HAS_PSQL := $(shell command -v psql 2> /dev/null)

# --- Definicja Celów ---
# Używamy .PHONY, aby upewnić się, że `make` zawsze wykonuje komendę,
# nawet jeśli istnieje plik o tej samej nazwie.
.PHONY: help sync lint type test test-all build build-all clean migrate ingest up up-deps down run-local

# Domyślny cel, który jest wykonywany, gdy uruchomimy `make` bez argumentów.
.DEFAULT_GOAL := help

## -----------------------------------------------------------------------------
## Pomoc i Dokumentacja
## -----------------------------------------------------------------------------
help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

## -----------------------------------------------------------------------------
## Zarządzanie Zależnościami i Jakością Kodu
## -----------------------------------------------------------------------------
sync: ## Synchronizuje zależności Pythona za pomocą `uv`.
ifndef HAS_UV
	@echo "Error: 'uv' command not found. Please install uv: https://github.com/astral-sh/uv"
	@exit 1
endif
	uv sync --all-extras --frozen

lint: ## Uruchamia linter (ruff) na kodzie źródłowym.
ifndef HAS_UV
	@echo "Error: 'uv' command not found."
	@exit 1
endif
	uv run ruff check src tests

type: ## Uruchamia statyczną analizę typów (mypy).
ifndef HAS_UV
	@echo "Error: 'uv' command not found."
	@exit 1
endif
	uv run mypy src

## -----------------------------------------------------------------------------
## Testowanie
## -----------------------------------------------------------------------------
test: ## Uruchamia testy jednostkowe dla Pythona (pytest).
ifndef HAS_UV
	@echo "Error: 'uv' command not found."
	@exit 1
endif
	uv run pytest -v --cov=src

test-java: ## Uruchamia testy dla serwisu Javy (Gradle).
	cd services/ticket-adapter-java && ./gradlew test --no-daemon

test-admin: ## Uruchamia testy dla portalu Admina (npm).
	cd services/admin-portal && npm ci && npm test

test-all: test test-java test-admin ## Uruchamia wszystkie testy (Python, Java, Node.js).
	@echo "All tests completed."

## -----------------------------------------------------------------------------
## Budowanie (bez Dockera)
## -----------------------------------------------------------------------------
build-java: ## Buduje plik .jar dla serwisu Javy.
	cd services/ticket-adapter-java && ./gradlew bootJar --no-daemon

build-admin: ## Buduje produkcyjną wersję portalu Admina.
	cd services/admin-portal && npm ci && npm run build

build-all: sync build-java build-admin ## Buduje wszystkie serwisy (bez Dockera).
	@echo "All services built successfully."

## -----------------------------------------------------------------------------
## Zarządzanie Środowiskiem Docker
## -----------------------------------------------------------------------------
up: ## Buduje i uruchamia wszystkie serwisy w Docker Compose.
ifndef HAS_DOCKER
	@echo "Error: 'docker compose' command not found. Is Docker running?"
	@exit 1
endif
	$(DOCKER_COMPOSE) up --build -d

up-deps: ## Uruchamia tylko zewnętrzne zależności (DBs, NATS, etc.) w Dockerze.
ifndef HAS_DOCKER
	@echo "Error: 'docker compose' command not found."
	@exit 1
endif
	$(DOCKER_COMPOSE) up -d db mysql redis nats ticket-adapter

down: ## Zatrzymuje i usuwa wszystkie kontenery oraz wolumeny.
ifndef HAS_DOCKER
	@echo "Error: 'docker compose' command not found."
	@exit 1
endif
	$(DOCKER_COMPOSE) down -v

## -----------------------------------------------------------------------------
## Uruchamianie Lokalnego Developmentu
## -----------------------------------------------------------------------------
run-local: up-deps ## Uruchamia serwer API (uvicorn) lokalnie (wymaga `make up-deps`).
ifndef HAS_UV
	@echo "Error: 'uv' command not found."
	@exit 1
endif
	@echo "Starting local API server... Make sure dependencies are running (make up-deps)."
	$(PYTHON_INTERPRETER) -m uvicorn src.gateway.main:app --host 0.0.0.0 --port 8080 --reload --app-dir src

## -----------------------------------------------------------------------------
## Operacje na Danych
## -----------------------------------------------------------------------------
migrate: ## Inicjalizuje bazę danych Postgres (wymaga `psql` i ustawionej zmiennej DATABASE_URL).
ifndef HAS_PSQL
	@echo "Error: 'psql' command not found. Please install PostgreSQL client tools."
	@exit 1
endif
	@echo "Applying database migrations..."
	psql "$$DATABASE_URL" -f migrations/0001_init_pgvector.sql

ingest: ## Przetwarza dokumenty z katalogu ./docs i zasila RAG.
ifndef HAS_UV
	@echo "Error: 'uv' command not found."
	@exit 1
endif
	@echo "Ingesting documents into RAG..."
	uv run python scripts/ingest_docs.py ./docs

## -----------------------------------------------------------------------------
## Czyszczenie
## -----------------------------------------------------------------------------
clean: ## Usuwa wygenerowane pliki i cache (np. .pytest_cache, build, .venv).
	@echo "Cleaning up generated files and caches..."
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf src/**/__pycache__
	rm -rf tests/**/__pycache__
	rm -rf services/ticket-adapter-java/build
	rm -rf services/admin-portal/.next
	rm -rf services/admin-portal/node_modules
	# Opcjonalnie: usuń .venv, ale to wymaga ponownej instalacji
	# rm -rf .venv
	@echo "Cleanup complete."
