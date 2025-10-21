# ==============================================================================
# Makefile for the AstraDesk Monorepo Project
#
# Ten plik służy jako centralne "centrum dowodzenia" dla całego, wielojęzycznego
# projektu AstraDesk. Jego celem jest automatyzacja i standaryzacja
# najczęstszych zadań deweloperskich, od instalacji zależności, przez
# testowanie, aż po zarządzanie środowiskiem Docker.
#
# Używanie tego pliku zapewnia, że wszyscy członkowie zespołu pracują
# w spójny i powtarzalny sposób.
#
# ------------------------------------------------------------------------------
# Szybki Start (Najważniejsze Komendy):
# ------------------------------------------------------------------------------
#
# 1. Uruchomienie całego systemu w Dockerze (zalecane do pełnych testów):
#    $ make up
#
# 2. Uruchomienie środowiska do pracy nad kodem Python (tryb hybrydowy):
#    # W pierwszym terminalu (uruchamia bazy danych, etc.):
#    $ make up-deps
#    # W drugim terminalu (uruchamia API z auto-przeładowaniem):
#    $ make run-local
#
# 3. Uruchomienie wszystkich testów w projekcie:
#    $ make test
#
# 4. Sprawdzenie jakości kodu (linter i typy):
#    $ make lint
#    $ make type
#
# 5. Zatrzymanie i wyczyszczenie środowiska Docker:
#    $ make down
#
# 6. Wyświetlenie pełnej listy dostępnych komend:
#    $ make help
#
# ==============================================================================

# --- Zmienne Konfiguracyjne ---

# Używamy `:=` aby zmienna była obliczana tylko raz.
DOCKER_COMPOSE := docker compose

# --- Sprawdzanie Zależności ---
# Sprawdza, czy kluczowe komendy są dostępne w systemie.
HAS_DOCKER := $(shell command -v $(DOCKER_COMPOSE) 2> /dev/null)
HAS_UV := $(shell command -v uv 2> /dev/null)
HAS_GRADLEW := $(shell test -f ./gradlew && echo 1)

# --- Definicja Celów ---
.PHONY: help all sync lint type test build clean up down run-local logs logs-api logs-auditor

# Domyślny cel: `make` bez argumentów pokaże pomoc.
.DEFAULT_GOAL := help

## -----------------------------------------------------------------------------
## Główne Cele
## -----------------------------------------------------------------------------
help: ## Pokazuje tę pomoc.
	@echo "AstraDesk Monorepo Makefile"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Główne cele:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -v '## Pomocniczy' | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Cele pomocnicze:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep '## Pomocniczy' | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'


all: lint test build ## Uruchamia lintery, testy i buduje wszystkie artefakty.

## -----------------------------------------------------------------------------
## Zarządzanie Środowiskiem Python (uv workspace)
## -----------------------------------------------------------------------------
sync: ## Synchronizuje zależności Pythona dla całego workspace.
ifndef HAS_UV
	@echo "Błąd: Komenda 'uv' nie znaleziona. Zainstaluj: https://github.com/astral-sh/uv" >&2; exit 1
endif
	uv sync --all-extras --frozen

lint: ## Uruchamia linter (ruff) na całym projekcie.
ifndef HAS_UV
	@echo "Błąd: Komenda 'uv' nie znaleziona." >&2; exit 1
endif
	uv run ruff check .

type: ## Uruchamia statyczną analizę typów (mypy) na całym projekcie.
ifndef HAS_UV
	@echo "Błąd: Komenda 'uv' nie znaleziona." >&2; exit 1
endif
	uv run mypy .

## -----------------------------------------------------------------------------
## Testowanie (Wielojęzyczne)
## -----------------------------------------------------------------------------
test: test-python test-java test-admin ## Uruchamia WSZYSTKIE testy w projekcie.

test-python: sync ## Uruchamia testy Pythona (rdzeń + paczki).
	@echo "Running Python tests for the entire workspace..."
	uv run pytest -v --cov

test-java: ## Uruchamia testy dla wszystkich modułów Javy.
ifndef HAS_GRADLEW
	@echo "Błąd: Plik './gradlew' nie znaleziony. Wygeneruj go najpierw." >&2; exit 1
endif
	./gradlew test

test-admin: ## Uruchamia testy dla portalu Admina.
	cd services/admin-portal && npm ci && npm test

## -----------------------------------------------------------------------------
## Budowanie (Wielojęzyczne)
## -----------------------------------------------------------------------------
build: build-python build-java build-admin ## Buduje WSZYSTKIE artefakty (bez Dockera).

build-python: sync  ## Instaluje zależności Pythona.
	@echo "Zależności Pythona są zsynchronizowane."

build-java:  ## Buduje wszystkie moduły Javy.
ifndef HAS_GRADLEW
	@echo "Błąd: Plik './gradlew' nie znaleziony." >&2; exit 1
endif
	./gradlew build -x test # Buduj, ale pomiń testy (już je uruchomiliśmy)

build-admin: ## Buduje produkcyjną wersję portalu Admina.
	cd services/admin-portal && npm ci && npm run build

## -----------------------------------------------------------------------------
## Zarządzanie Środowiskiem Docker
## -----------------------------------------------------------------------------
up: ## Buduje i uruchamia wszystkie serwisy w Docker Compose.
ifndef HAS_DOCKER
	@echo "Błąd: Komenda 'docker compose' nie znaleziona. Czy Docker jest uruchomiony?" >&2; exit 1
endif
	$(DOCKER_COMPOSE) up --build -d

down: ## Zatrzymuje i usuwa wszystkie kontenery, sieci i wolumeny.
ifndef HAS_DOCKER
	@echo "Błąd: Komenda 'docker compose' nie znaleziona." >&2; exit 1
endif
	$(DOCKER_COMPOSE) down -v

up-deps:  ## Uruchamia tylko zewnętrzne zależności w Dockerze.
ifndef HAS_DOCKER
	@echo "Błąd: Komenda 'docker compose' nie znaleziona." >&2; exit 1
endif
	$(DOCKER_COMPOSE) up -d db mysql redis nats ticket-adapter

run-local: up-deps ## Uruchamia API lokalnie, z zależnościami w Dockerze.
ifndef HAS_UV
	@echo "Błąd: Komenda 'uv' nie znaleziona." >&2; exit 1
endif
	@echo "Uruchamianie serwera API lokalnie na porcie 8000..."
	python -m uvicorn src.gateway.main:app --host 0.0.0.0 --port 8000 --reload --app-dir src

logs: ## Pokazuje logi wszystkich kontenerów na żywo.
	$(DOCKER_COMPOSE) logs -f

logs-api: ## Pokazuje logi tylko dla serwisu 'api'.
	$(DOCKER_COMPOSE) logs -f api

logs-auditor: ## Pokazuje logi tylko dla serwisu 'auditor'.
	$(DOCKER_COMPOSE) logs -f auditor

## -----------------------------------------------------------------------------
## Operacje na Danych i Narzędzia
## -----------------------------------------------------------------------------
migrate: ## Inicjalizuje bazę danych Postgres (wymaga `psql` i `DATABASE_URL`).
ifndef HAS_PSQL
	@echo "Błąd: Komenda 'psql' nie znaleziona." >&2; exit 1
endif
	psql "$$DATABASE_URL" -f migrations/0001_init_pgvector.sql

ingest: sync ## Przetwarza dokumenty z `./docs` i zasila bazę RAG.
	uv run python scripts/ingest_docs.py ./docs

clean: ## Usuwa wygenerowane pliki i cache.
	@echo "Czyszczenie projektu..."
	rm -rf .pytest_cache .mypy_cache
	find . -type d -name "__pycache__" -exec rm -r {} +
	./gradlew clean
	cd services/admin-portal && rm -rf .next node_modules
	@echo "Czyszczenie zakończone."
