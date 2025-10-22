.
├── ansible
│   ├── inventories
│   │   └── dev
│   │       └── hosts.ini
│   └── roles
│       └── astradesk_docker
│           └── tasks
│               └── main.yml
├── astradesk.code-workspace
├── build
│   ├── reports
│   │   └── problems
│   │       └── problems-report.html
│   └── tmp
│       ├── artifactTransforms
│       ├── buildEnvironment
│       ├── dependencies
│       ├── dependencyInsight
│       ├── help
│       ├── init
│       ├── javaToolchains
│       ├── kotlinDslAccessorsReport
│       ├── outgoingVariants
│       ├── prepareKotlinBuildScriptModel
│       ├── projects
│       ├── properties
│       ├── resolvableConfigurations
│       ├── tasks
│       ├── updateDaemonJvm
│       └── wrapper
├── build.gradle.kts
├── deploy
│   ├── chart
│   │   ├── Chart.yaml
│   │   ├── templates
│   │   │   ├── deployment.yaml
│   │   │   ├── hpa.yaml
│   │   │   └── service.yaml
│   │   └── values.yaml
│   ├── istio
│   │   ├── 00-namespace.yaml
│   │   ├── 10-peer-authentication.yaml
│   │   ├── 20-destinationrule-astradesk-api.yaml
│   │   ├── 30-authorizationpolicy-namespace.yaml
│   │   ├── 40-gateway.yaml
│   │   ├── 41-virtualservice-astradesk-api.yaml
│   │   ├── 50-cert-manager-certificate.yaml
│   │   └── readme.md
│   └── openshift
│       └── astradesk-template.yaml
├── dev
│   ├── mock_tickets.py
│   └── prometheus
│       └── prometheus.yml
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
│   │   ├── 02_architecture_overview.md
│   │   ├── 03_plan_phase.md
│   │   ├── 04_build_phase.md
│   │   ├── 05_test_optimize.md
│   │   ├── 06_deploy_phase.md
│   │   ├── 07_monitor_operate.md
│   │   ├── 08_security_governance.md
│   │   ├── 09_mcp_gateway_domain_packs.md
│   │   ├── 10_future_roadmap.md
│   │   ├── glossary.md
│   │   └── README.md
│   ├── js
│   │   └── mermaid-init.js
│   ├── operations.md
│   ├── pl
│   │   ├── 01_introduction.pl.md
│   │   ├── 02_architecture_overview.pl.md
│   │   ├── 03_plan_phase.pl.md
│   │   ├── 04_build_phase.pl.md
│   │   ├── 05_test_optimize.pl.md
│   │   ├── 06_deploy_phase.pl.md
│   │   ├── 07_monitor_operate.pl.md
│   │   ├── 08_security_governance.pl.md
│   │   ├── 09_mcp_gateway_domain_packs.pl.md
│   │   ├── 10_future_roadmap.pl.md
│   │   ├── glossary.pl.md
│   │   └── README.pl.md
│   ├── README.md
│   ├── security.md
│   └── styles
│       └── mermaid-card.css
├── gradle
│   └── wrapper
│       └── gradle-wrapper.properties
├── gradlew
├── gradlew.bat
├── grafana
│   └── dashboard-astradesk.json
├── infra
│   ├── main.tf
│   ├── outputs.tf
│   └── variables.tf
├── Jenkinsfile
├── LICENSE
├── Makefile
├── migrations
│   └── 0001_init_pgvector.sql
├── mkdocs.yml
├── openapi
│   └── astradesk-admin.v1.yaml
├── Opis_structury.txt
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
├── puppet
│   └── manifests
│       └── astradesk.pp
├── pyproject.toml
├── README.md
├── README.pl.md
├── README.zh-CN.md
├── salt
│   └── astradesk
│       └── init.sls
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
│   ├── auditor
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   └── pyproject.toml
│   ├── build
│   │   └── tmp
│   │       ├── artifactTransforms
│   │       ├── buildEnvironment
│   │       ├── dependencies
│   │       ├── dependencyInsight
│   │       ├── help
│   │       ├── javaToolchains
│   │       ├── outgoingVariants
│   │       ├── projects
│   │       ├── properties
│   │       ├── resolvableConfigurations
│   │       └── tasks
│   └── ticket-adapter-java
│       ├── bin
│       │   └── main
│       │       └── com
│       │           └── astradesk
│       │               └── ticket
│       │                   ├── http
│       │                   │   ├── TicketController.class
│       │                   │   └── TicketReq.class
│       │                   ├── model
│       │                   │   └── Ticket.class
│       │                   ├── repo
│       │                   │   └── TicketRepo.class
│       │                   └── TicketApp.class
│       ├── build
│       │   ├── classes
│       │   │   └── java
│       │   │       ├── main
│       │   │       │   └── com
│       │   │       │       └── astradesk
│       │   │       │           └── ticket
│       │   │       │               ├── http
│       │   │       │               │   ├── TicketController.class
│       │   │       │               │   └── TicketReq.class
│       │   │       │               ├── model
│       │   │       │               │   └── Ticket.class
│       │   │       │               ├── repo
│       │   │       │               │   └── TicketRepo.class
│       │   │       │               ├── SecurityConfig.class
│       │   │       │               └── TicketApp.class
│       │   │       └── test
│       │   │           └── com
│       │   │               └── astradesk
│       │   │                   └── ticket
│       │   │                       ├── TicketControllerTest$CreateTicketTests.class
│       │   │                       ├── TicketControllerTest$GetTicketTests.class
│       │   │                       └── TicketControllerTest.class
│       │   ├── generated
│       │   │   └── sources
│       │   │       ├── annotationProcessor
│       │   │       │   └── java
│       │   │       │       ├── main
│       │   │       │       └── test
│       │   │       └── headers
│       │   │           └── java
│       │   │               ├── main
│       │   │               └── test
│       │   ├── resources
│       │   │   ├── main
│       │   │   │   ├── application.yml
│       │   │   │   └── schema.sql
│       │   │   └── test
│       │   └── tmp
│       │       ├── artifactTransforms
│       │       ├── assemble
│       │       ├── bootBuildImage
│       │       ├── bootJar
│       │       │   └── MANIFEST.MF
│       │       ├── bootRun
│       │       ├── bootTestRun
│       │       ├── build
│       │       ├── buildDependents
│       │       ├── buildEnvironment
│       │       ├── buildNeeded
│       │       ├── check
│       │       ├── classes
│       │       ├── clean
│       │       ├── compileJava
│       │       │   └── previous-compilation-data.bin
│       │       ├── compileTestJava
│       │       │   └── previous-compilation-data.bin
│       │       ├── dependencies
│       │       ├── dependencyInsight
│       │       ├── dependencyManagement
│       │       ├── help
│       │       ├── jar
│       │       │   └── MANIFEST.MF
│       │       ├── javadoc
│       │       ├── javadocJar
│       │       │   └── MANIFEST.MF
│       │       ├── javaToolchains
│       │       ├── kotlinDslAccessorsReport
│       │       ├── outgoingVariants
│       │       ├── processResources
│       │       ├── processTestResources
│       │       ├── projects
│       │       ├── properties
│       │       ├── resolvableConfigurations
│       │       ├── resolveMainClassName
│       │       ├── resolveTestMainClassName
│       │       ├── runSingle
│       │       ├── sourcesJar
│       │       │   └── MANIFEST.MF
│       │       ├── tasks
│       │       ├── test
│       │       └── testClasses
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
├── src
│   ├── agents
│   │   ├── base.py
│   │   ├── __init__.py
│   │   ├── ops.py
│   │   └── support.py
│   ├── astradesk.egg-info
│   │   ├── dependency_links.txt
│   │   ├── PKG-INFO
│   │   ├── requires.txt
│   │   ├── SOURCES.txt
│   │   └── top_level.txt
│   ├── gateway
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── orchestrator.py
│   ├── model_gateway
│   │   ├── base.py
│   │   ├── guardrails.py
│   │   ├── __init__.py
│   │   ├── llm_planner.py
│   │   ├── providers
│   │   │   ├── bedrock_provider.py
│   │   │   ├── __init__.py
│   │   │   ├── openai_provider.py
│   │   │   └── vllm_provider.py
│   │   └── router.py
│   ├── runtime
│   │   ├── auth.py
│   │   ├── events.py
│   │   ├── __init__.py
│   │   ├── memory.py
│   │   ├── models.py
│   │   ├── planner.py
│   │   ├── policy.py
│   │   ├── rag.py
│   │   └── registry.py
│   └── tools
│       ├── __init__.py
│       ├── metrics.py
│       ├── ops_actions.py
│       ├── tickets_proxy.py
│       └── weather.py
├── tests
│   ├── runtime
│   │   ├── test_auth.py
│   │   ├── test_events.py
│   │   ├── test_memory.py
│   │   ├── test_models.py
│   │   ├── test_planner.py
│   │   ├── test_policy.py
│   │   ├── test_rag.py
│   │   └── test_registry.py
│   └── test_api.py
├── tree.md
└── uv.lock

238 directories, 304 files
