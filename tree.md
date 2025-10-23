# Struktura 2.0

```sh
.
├── astradesk.code-workspace
├── build.gradle.kts
├── core
│   ├── build.gradle.kts
│   ├── pyproject.toml
│   └── src
│       └── astradesk_core
│           ├── exceptions.py
│           ├── __init__.py
│           └── utils
│               ├── auth.py
│               └── events.py
├── deploy
│   ├── chart
│   │   ├── Chart.yaml
│   │   ├── deploy_chart_README.md
│   │   ├── requirements.yaml
│   │   ├── templates
│   │   │   ├── deployment.yaml
│   │   │   ├── hpa.yaml
│   │   │   ├── service.yaml
│   │   │   └── tests
│   │   │       └── test-mtls.yaml
│   │   ├── tests
│   │   │   ├── test-api.yaml
│   │   │   └── test-hpa.yaml
│   │   └── values.yaml
│   ├── cm
│   │   ├── ansible
│   │   │   ├── ansible_README.md
│   │   │   ├── inventories
│   │   │   │   └── dev
│   │   │   │       └── hosts.ini
│   │   │   ├── playbook.yml
│   │   │   └── roles
│   │   │       └── astradesk_docker
│   │   │           └── tasks
│   │   │               └── main.yml
│   │   ├── puppet
│   │   │   ├── manifests
│   │   │   │   └── astradesk.pp
│   │   │   └── puppet_README.md
│   │   └── salt
│   │       ├── astradesk
│   │       │   └── init.sls
│   │       └── salt_README.md
│   ├── infra
│   │   ├── main.tf
│   │   ├── modules
│   │   │   ├── eks
│   │   │   │   ├── infra_modules_eks_README.md
│   │   │   │   ├── main.tf
│   │   │   │   ├── outputs.tf
│   │   │   │   └── variables.tf
│   │   │   ├── rds-mysql
│   │   │   │   ├── infra_modules_rds-mysql_README.md
│   │   │   │   ├── main.tf
│   │   │   │   ├── outputs.tf
│   │   │   │   └── variables.tf
│   │   │   ├── rds-postgres
│   │   │   │   ├── infra_modules_rds-postgres_README.md
│   │   │   │   ├── main.tf
│   │   │   │   ├── outputs.tf
│   │   │   │   └── variables.tf
│   │   │   ├── s3
│   │   │   │   ├── infra_modules_s3_README.md
│   │   │   │   ├── main.tf
│   │   │   │   ├── outputs.tf
│   │   │   │   └── variables.tf
│   │   │   └── vpc
│   │   │       ├── infra_modules_vpc_README.md
│   │   │       ├── main.tf
│   │   │       ├── outputs.tf
│   │   │       └── variables.tf
│   │   ├── outputs.tf
│   │   ├── README_infra.md
│   │   ├── terraform.tfvars
│   │   └── variables.tf
│   ├── istio
│   │   ├── 00-namespace.yaml
│   │   ├── 10-peer-authentication.yaml
│   │   ├── 20-destinationrule-astradesk-api.yaml
│   │   ├── 30-authorizationpolicy-namespace.yaml
│   │   ├── 40-gateway.yaml
│   │   ├── 41-virtualservice-astradesk-api.yaml
│   │   ├── 50-cert-manager-certificate.yaml
│   │   ├── certmanager.yaml
│   │   ├── certs
│   │   │   ├── astradesk-ca-certificate.yaml
│   │   │   ├── astradesk-ca-clusterissuer.yaml
│   │   │   ├── letsencrypt-prod-clusterissuer.yaml
│   │   │   └── README_certs.md
│   │   ├── deploy_istio_README.md
│   │   ├── gateway.yaml
│   │   ├── peerauthentication.yaml
│   │   ├── readme.md
│   │   └── virtualservice.yaml
│   ├── local
│   │   └── dev
│   │       ├── mock_tickets.py
│   │       └── prometheus
│   │           └── prometheus.yml
│   ├── observability
│   │   └── dashboards
│   │       └── grafana
│   │           └── dashboard-astradesk.json
│   └── openshift
│       ├── admin-portal-template.yaml
│       ├── astradesk-template.yaml
│       ├── auditor-template.yaml
│       ├── domain-packs-template.yaml
│       ├── README_openshift.md
│       └── ticket-adapter-template.yaml
├── docker-compose.yml
├── Dockerfile
├── docs
│   ├── api
│   │   ├── index.html
│   │   ├── index.md
│   │   └── openapi.yaml
│   ├── api.md
│   ├── architecture.md
│   ├── assets
│   │   ├── astradesk-logo.svg
│   │   ├── astradesk-symbol.svg
│   │   └── AstraDesktop.png
│   ├── en
│   │   ├── 01_introduction.md
│   │   └── ...
│   ├── js
│   │   └── mermaid-init.js
│   ├── operations.md
│   ├── pl
│   │   ├── 01_introduction.pl.md
│   │   └── ...
│   ├── README.md
│   ├── security.md
│   └── styles
│       └── mermaid-card.css
├── gradle
│   └── wrapper
│       └── gradle-wrapper.properties
├── gradlew
├── gradlew.bat
├── Jenkinsfile
├── Jenkinsfile_v2a
├── LICENSE
├── Makefile
├── Makefile_v2a
├── migrations
│   └── 0001_init_pgvector.sql
├── mkdocs.yml
├── openapi
│   └── astradesk-admin.v1.yaml
├── Opis_structury_1.2.0.txt
├── packages
│   ├── domain-finance
│   │   ├── agents
│   │   │   └── forecast.py
│   │   ├── build.gradle
│   │   ├── clients
│   │   │   ├── api.py
│   │   │   └── grpc_client.py
│   │   ├── flows
│   │   │   └── forecast_mtd.yaml
│   │   ├── policies
│   │   │   └── finance.rego
│   │   ├── proto
│   │   │   └── finance.proto
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── tests
│   │   │   ├── java
│   │   │   │   └── OracleErpGrpcServerTest.java
│   │   │   └── test_forecast.py
│   │   └── tools
│   │       ├── erp_oracle.py
│   │       ├── OracleErpAdapter.java
│   │       └── OracleErpGrpcServer.java
│   ├── domain-ops
│   │   ├── agents
│   │   │   └── ops.py
│   │   ├── pyproject.toml
│   │   ├── tests
│   │   │   └── test_ops.py
│   │   └── tools
│   │       └── ops_actions.py
│   ├── domain-supply
│   │   ├── agents
│   │   │   └── replenish.py
│   │   ├── build.gradle
│   │   ├── clients
│   │   │   ├── api.py
│   │   │   └── grpc_client.py
│   │   ├── flows
│   │   │   └── exception_routing.yaml
│   │   ├── policies
│   │   │   └── supply.rego
│   │   ├── proto
│   │   │   └── supply.proto
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── tests
│   │   │   ├── java
│   │   │   │   ├── SapMmGrpcServerTest.java
│   │   │   │   └── SapS4HanaGrpcServerTest.java
│   │   │   └── test_replenish.py
│   │   └── tools
│   │       ├── SapMmAdapter.java
│   │       ├── SapMmGrpcServer.java
│   │       ├── sap_mm.py
│   │       ├── SapS4HanaAdapter.java
│   │       └── SapS4HanaGrpcServer.java
│   ├── domain-support
│   │   ├── agents
│   │   │   └── triage.py
│   │   ├── clients
│   │   │   └── api.py
│   │   ├── flows
│   │   │   └── autoresolve.yaml
│   │   ├── policies
│   │   │   └── support.rego
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── tests
│   │   │   └── test_triage.py
│   │   └── tools
│   │       ├── asana_adapter.py
│   │       ├── jira_adapter.py
│   │       └── slack_adapter.py
│   ├── README.markdown
│   └── README.md
├── pyproject.toml
├── README.md
├── README.pl.md
├── README.zh-CN.md
├── scripts
│   ├── demo_queries.sh
│   ├── docker-audit.sh
│   ├── ingest_docs.py
│   └── seed_kb.py
├── services
│   ├── admin-portal
│   │   ├── app
│   │   │   ├── favicon.ico
│   │   │   ├── globals.css
│   │   │   ├── layout.tsx
│   │   │   └── (shell)
│   │   │       ├── agents
│   │   │       │   ├── AgentsClient.tsx
│   │   │       │   ├── [id]
│   │   │       │   │   └── page.tsx
│   │   │       │   └── page.tsx
│   │   │       ├── audit
│   │   │       │   ├── AuditClient.tsx
│   │   │       │   ├── [id]
│   │   │       │   │   └── page.tsx
│   │   │       │   └── page.tsx
│   │   │       ├── datasets
│   │   │       │   ├── [id]
│   │   │       │   │   └── page.tsx
│   │   │       │   └── page.tsx
│   │   │       ├── flows
│   │   │       │   ├── [id]
│   │   │       │   │   └── page.tsx
│   │   │       │   └── page.tsx
│   │   │       ├── intent-graph
│   │   │       │   └── page.tsx
│   │   │       ├── jobs
│   │   │       │   ├── [id]
│   │   │       │   │   ├── JobActions.tsx
│   │   │       │   │   └── page.tsx
│   │   │       │   └── page.tsx
│   │   │       ├── layout.tsx
│   │   │       ├── page.tsx
│   │   │       ├── policies
│   │   │       │   ├── [id]
│   │   │       │   │   ├── page.tsx
│   │   │       │   │   └── PolicyActions.tsx
│   │   │       │   └── page.tsx
│   │   │       ├── rbac
│   │   │       │   └── page.tsx
│   │   │       ├── runs
│   │   │       │   ├── [id]
│   │   │       │   │   └── page.tsx
│   │   │       │   ├── page.tsx
│   │   │       │   └── RunsClient.tsx
│   │   │       ├── secrets
│   │   │       │   └── page.tsx
│   │   │       ├── settings
│   │   │       │   ├── page.tsx
│   │   │       │   └── SettingsClient.tsx
│   │   │       ├── template.tsx
│   │   │       └── tools
│   │   │           ├── [id]
│   │   │           │   ├── ConnectorActions.tsx
│   │   │           │   └── page.tsx
│   │   │           └── page.tsx
│   │   ├── components
│   │   │   ├── charts
│   │   │   │   └── KpiCard.tsx
│   │   │   ├── data
│   │   │   │   ├── DataTable.tsx
│   │   │   │   ├── FilterBar.tsx
│   │   │   │   └── Pagination.tsx
│   │   │   ├── layout
│   │   │   │   ├── Footer.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   └── Topbar.tsx
│   │   │   ├── misc
│   │   │   │   ├── EmptyState.tsx
│   │   │   │   └── JsonViewer.tsx
│   │   │   └── primitives
│   │   │       ├── Badge.tsx
│   │   │       ├── Button.tsx
│   │   │       ├── Card.tsx
│   │   │       ├── Drawer.tsx
│   │   │       ├── Form.tsx
│   │   │       ├── Modal.tsx
│   │   │       ├── Tabs.tsx
│   │   │       └── Toast.tsx
│   │   ├── docker-compose.yml
│   │   ├── Dockerfile
│   │   ├── hooks
│   │   │   ├── useDebounce.ts
│   │   │   └── useToast.tsx
│   │   ├── lib
│   │   │   ├── adapters
│   │   │   │   └── index.ts
│   │   │   ├── api.ts
│   │   │   ├── env.ts
│   │   │   ├── format.ts
│   │   │   ├── guards.ts
│   │   │   ├── simulation-data.ts
│   │   │   ├── simulation.ts
│   │   │   ├── sse.ts
│   │   │   └── types.ts
│   │   ├── next.config.ts
│   │   ├── next-env.d.ts
│   │   ├── openapi
│   │   │   ├── openapi-client.ts
│   │   │   ├── openapi-types.d.ts
│   │   │   ├── OpenAPI.yaml
│   │   │   ├── paths-map.ts
│   │   │   └── README.md
│   │   ├── OpenAPI.yaml
│   │   ├── package.json
│   │   ├── package-lock.json
│   │   ├── postcss.config.js
│   │   ├── public
│   │   │   ├── images
│   │   │   ├── logo.png
│   │   │   └── logo.svg
│   │   ├── README.admin.md
│   │   ├── README.md
│   │   ├── scripts
│   │   │   ├── check-openapi-sync.ts
│   │   │   └── openapi-generate.ts
│   │   ├── src
│   │   │   ├── api
│   │   │   │   └── types.gen.ts
│   │   │   ├── clients
│   │   │   │   └── adminApi.ts
│   │   │   └── _gen
│   │   │       └── admin_api
│   │   │           └── index.ts
│   │   ├── tailwind.config.ts
│   │   ├── tests
│   │   │   ├── e2e
│   │   │   └── unit
│   │   │       ├── api.problem-json.test.ts
│   │   │       ├── filters.serializer.test.ts
│   │   │       └── sse.reconnect.test.ts
│   │   ├── tsconfig.json
│   │   └── vitest.config.ts
│   ├── api-gateway
│   │   ├── src
│   │   │   ├── agents
│   │   │   │   ├── base.py
│   │   │   │   ├── __init__.py
│   │   │   │   └── support.py
│   │   │   ├── astradesk.egg-info
│   │   │   │   ├── dependency_links.txt
│   │   │   │   ├── PKG-INFO
│   │   │   │   ├── requires.txt
│   │   │   │   ├── SOURCES.txt
│   │   │   │   └── top_level.txt
│   │   │   ├── gateway
│   │   │   │   ├── __init__.py
│   │   │   │   ├── main.py
│   │   │   │   └── orchestrator.py
│   │   │   ├── model_gateway
│   │   │   │   ├── base.py
│   │   │   │   ├── guardrails.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── llm_planner.py
│   │   │   │   ├── providers
│   │   │   │   │   ├── bedrock_provider.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── openai_provider.py
│   │   │   │   │   └── vllm_provider.py
│   │   │   │   └── router.py
│   │   │   ├── runtime
│   │   │   │   ├── __init__.py
│   │   │   │   ├── memory.py
│   │   │   │   ├── models.py
│   │   │   │   ├── planner.py
│   │   │   │   ├── policy.py
│   │   │   │   ├── rag.py
│   │   │   │   └── registry.py
│   │   │   └── tools
│   │   │       ├── __init__.py
│   │   │       ├── metrics.py
│   │   │       ├── ops_actions.py
│   │   │       ├── tickets_proxy.py
│   │   │       └── weather.py
│   │   └── tests
│   │       └── runtime
│   │           ├── test_auth.py
│   │           ├── test_events.py
│   │           ├── test_memory.py
│   │           ├── test_models.py
│   │           ├── test_planner.py
│   │           ├── test_policy.py
│   │           ├── test_rag.py
│   │           └── test_registry.py
│   ├── auditor
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   └── pyproject.toml
│   └── ticket-adapter-java
│       │
│       ├── build.gradle.kts
│       ├── Dockerfile
│       ├── gradle
│       │   └── wrapper
│       │       └── gradle-wrapper.properties
│       ├── gradlew
│       ├── gradlew.bat
│       ├── README.md
│       └── src
│           ├── main
│           │   ├── java
│           │   │   └── com
│           │   │       └── astradesk
│           │   │           └── ticket
│           │   │               ├── http
│           │   │               │   ├── TicketController.java
│           │   │               │   └── TicketReq.java
│           │   │               ├── model
│           │   │               │   └── Ticket.java
│           │   │               ├── repo
│           │   │               │   └── TicketRepo.java
│           │   │               ├── SecurityConfig.java
│           │   │               └── TicketApp.java
│           │   └── resources
│           │       ├── application.yml
│           │       └── schema.sql
│           └── test
│               └── java
│                   └── com
│                       └── astradesk
│                           └── ticket
│                               └── TicketControllerTest.java
├── settings.gradle.kts
├── sonar-project.properties
├── tests
│   └── test_api.py
├── tree.md
└── uv.lock

```

## Opis Struktury Plików Projektu AstraDesk (Wersja Produkcyjna)

Poniżej znajduje się szczegółowa analiza i opis każdego kluczowego folderu oraz pliku w strukturze projektu AstraDesk, zaktualizowana do stanu na 21 października 2025. Opis jest hierarchiczny i wyjaśnia przeznaczenie każdego elementu w kontekście nowej, wielomodułowej architektury monorepo.

---

- **.** (root projektu): Główny katalog projektu, pełniący rolę "workspace". Integruje wszystkie komponenty, konfiguracje i narzędzia. Jest punktem wejściowym dla zunifikowanego systemu budowania (Gradle) i zarządzania zależnościami (uv).

  - **ansible/, puppet/, salt/**: Foldery z konfiguracją dla narzędzi Zarządzania Konfiguracją (CM). Służą do automatyzacji wdrożeń na maszynach wirtualnych lub serwerach bare-metal. **Analiza**: Dobra praktyka dla środowisk hybrydowych; komplementarne do wdrożeń kontenerowych.

  - **build.gradle.kts**: **Główny plik budowania Gradle**. Definiuje wersje wtyczek (`plugins`) dla całego monorepo. **Analiza**: Celowo utrzymany jako minimalny, deleguje konfigurację do podprojektów i `settings.gradle.kts`.

  - **settings.gradle.kts**: **Plik ustawień Gradle**. Definiuje strukturę projektu wielomodułowego, deklarując, które podkatalogi (np. `services/ticket-adapter-java`) są modułami Gradle. **Analiza**: Kluczowy plik dla architektury monorepo.

  - **gradlew, gradlew.bat, gradle/**: **Gradle Wrapper**. Zapewnia, że każdy deweloper i system CI/CD używa tej samej, spójnej wersji Gradle do budowania komponentów Javy. **Analiza**: Niezbędny element dla powtarzalnych buildów.

  - **deploy/**: Zawiera wszystkie manifesty i konfiguracje do wdrożeń na platformach orkiestracji kontenerów.
    - **chart/**: Chart Helm dla wdrożeń na **Kubernetes**. Definiuje szablony dla `Deployment`, `Service`, `HPA`, etc. **Analiza**: Standard branżowy, kluczowy dla wdrożeń w chmurze.
    - **istio/**: Manifesty Istio do konfiguracji service mesh, włączając w to mTLS, polityki autoryzacji i routing. **Analiza**: Zaawansowane, kluczowe dla bezpieczeństwa na poziomie enterprise.
    - **openshift/**: Szablony dla platformy **OpenShift**. **Analiza**: Dobre rozszerzenie dla środowisk korporacyjnych opartych na Red Hat.

  - **docker-compose.yml**: Główny plik Docker Compose. Służy do **uruchamiania środowiska deweloperskiego**, włączając w to serwisy zewnętrzne (Postgres, MySQL, Redis, NATS) oraz pre-zbudowane obrazy aplikacji. **Analiza**: Niezbędny dla lokalnego developmentu i testów integracyjnych.

  - **Dockerfile**: Główny `Dockerfile` dla **serwisu `api` (Python/FastAPI)**. Definiuje, jak zbudować obraz kontenera dla rdzenia aplikacji. **Analiza**: Zoptymalizowany, używa `uv` i najlepszych praktyk.

  - **docs/**: Kompletna dokumentacja projektu zarządzana przez **MkDocs**. Zawiera opisy architektury, API (generowane z OpenAPI), tutoriale i zasoby wizualne. **Analiza**: Bardzo rozbudowana i profesjonalna, kluczowa dla onboardingu i utrzymania.

  - **infra/**: Kod **Terraform** do provisioningu infrastruktury w chmurze (IaC - Infrastructure as Code). Definiuje zasoby takie jak VPC, klaster EKS i bazy danych RDS. **Analiza**: Kluczowy element dla zautomatyzowanych wdrożeń na AWS.

  - **Jenkinsfile, .gitlab-ci.yml**: Definicje pipeline'ów CI/CD. Automatyzują proces testowania, budowania i wdrażania dla całego monorepo. **Analiza**: Niezbędne dla praktyk DevOps.

  - **Makefile**: Plik automatyzujący najczęstsze zadania deweloperskie (`make test`, `make up`, `make run-local`). Służy jako **uproszczony interfejs** do złożonych komend `docker`, `uv` i `gradle`. **Analiza**: Znacząco poprawia Developer Experience.

  - **migrations/**: Skrypty SQL do zarządzania schematem bazy danych PostgreSQL. **Analiza**: Kluczowe dla ewolucji schematu bazy danych.

  - **openapi/**: Centralne miejsce dla specyfikacji API.
    - **astradesk-admin.v1.yaml**: **Jedno źródło prawdy** dla `Admin API`. Definiuje wszystkie endpointy, schematy i zasady bezpieczeństwa. Służy do generowania klientów API i dokumentacji. **Analiza**: Fundament podejścia "API-First".

  - **packages/**: **Pakiety Domenowe (Domain Packs)**. Modułowe, instalowalne pakiety Pythona, które rozszerzają funkcjonalność platformy o logikę specyficzną dla danej dziedziny (np. finanse, support). **Analiza**: Najważniejszy element architektoniczny zapewniający skalowalność i rozszerzalność platformy.
    - **domain-*/**: Każdy pakiet ma własną, spójną strukturę (`agents/`, `tools/`, `tests/`, `pyproject.toml`), co pozwala na niezależny rozwój.

  - **pyproject.toml**: Główny plik konfiguracyjny dla ekosystemu Pythona. Definiuje zależności, narzędzia (Ruff, Mypy, Pytest) oraz, co kluczowe, **konfigurację `uv workspace`**, która integruje rdzeń `src` z paczkami w `packages/`.

  - **scripts/**: Skrypty pomocnicze do zadań operacyjnych, takich jak zasilanie bazy RAG (`ingest_docs.py`) czy uruchamianie zapytań demonstracyjnych.

  - **services/**: **Mikroserwisy** stanowiące rdzeń platformy. W przeciwieństwie do `packages`, są to fundamentalne, zawsze obecne komponenty.
    - **admin-portal/**: Kod źródłowy dla frontendu (Next.js), włączając w to komponenty, logikę API i konfigurację budowania. **Analiza**: Bardzo rozbudowany i profesjonalnie zorganizowany.
    - **auditor/**: Prosty mikroserwis w Pythonie do subskrybowania i zapisywania zdarzeń audytowych z NATS.
    - **ticket-adapter-java/**: Mikroserwis w Javie (Spring WebFlux) pełniący rolę adaptera do systemu ticketowego. **Analiza**: W pełni niezależny moduł Gradle.

  - **src/**: Kod źródłowy **głównego komponentu Pythonowego** (API Gateway i Runtime).
    - **agents/**: Implementacje agentów (`SupportAgent`, `OpsAgent`) i ich klasa bazowa.
    - **gateway/**: Warstwa webowa (FastAPI), w tym `main.py` (entrypoint) i `orchestrator.py` (logika biznesowa).
    - **model_gateway/**: Abstrakcja do komunikacji z modelami LLM, włączając w to `router`, `planner` i konkretne implementacje `providerów`.
    - **runtime/**: Biblioteka rdzennych komponentów frameworka (pamięć, RAG, rejestr narzędzi, polityki, etc.), z których korzystają agenci.
    - **tools/**: Konkretne implementacje narzędzi (np. `tickets_proxy.py`, `ops_actions.py`).
    - **UWAGA: `src/main` i `src/test`**: Te katalogi zawierają **zduplikowany kod Javy**. Wygląda to na pozostałość po poprzedniej strukturze projektu. **Rekomendacja**: Należy je **usunąć**, ponieważ cały kod Javy dla `ticket-adapter` znajduje się teraz w `services/ticket-adapter-java/`.

  - **tests/**: Główne testy integracyjne i jednostkowe dla rdzenia Pythona (`src`). **Analiza**: Dobrze zorganizowane, ale `test_planner.py` jest zduplikowany.

---
**Ocena Ogólna:** Struktura projektu jest **wybitna, na poziomie enterprise**. Jest to klasyczne monorepo z wieloma technologiami, zarządzane przez zunifikowany system budowania. Największym zidentyfikowanym problemem jest **duplikacja kodu Javy w katalogu `src`**, którą należy natychmiast usunąć, aby uniknąć nieporozumień. Poza tym, struktura jest gotowa do skalowania i dalszego rozwoju.