
<br>
<p align="center">
  <img src="https://astradesk.dev/_next/image?url=%2FAstraDesk_wlogo.png&w=640&q=75" alt="AstraDesk - AI 框架" width="560"/>
</p>

<br>

# AstraDesk - 企业级 AI 框架

[![许可证](https://img.shields.io/badge/许可证-Apache%202.0-yellow.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Python 版本](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![JDK 版本](https://img.shields.io/badge/JDK-21-green.svg)](https://openjdk.org/projects/jdk/21/)
[![Node.js 版本](https://img.shields.io/badge/Node.js-22-brightgreen.svg)](https://nodejs.org/en)
[![构建状态](https://img.shields.io/badge/构建-通过-brightgreen.svg)](https://github.com/your-org/astradesk/actions)

🌍 **语言:** [English](README.md) | 🇵🇱 [Polski](docs/pl/README.pl.main.md) | [🇨🇳 中文（当前文件）](docs/zh/README.zh.main.md)

<br>

[AstraDesk](https://www.astradesk.dev) 是一个专为支持团队（Support）和运维团队（SRE/DevOps）设计的内部 AI 智能体构建框架。它提供模块化架构，包含预置的演示智能体、数据库集成、消息系统以及 DevOps 工具。该框架支持可扩展性、企业级安全（OIDC/JWT、RBAC、通过 Istio 实现 mTLS）以及完整的 CI/CD 流程。

<br>

---

## 目录

- [功能特性](#功能特性)
- [适用场景与用途](#适用场景与用途)
- [架构概览](#架构概览)
- [前置要求](#前置要求)
- [快速入门与开发者指南](#快速入门与开发者指南)
- [配置](#配置)
  - [环境变量](#环境变量)
  - [OIDC/JWT 认证](#oidcjwt-认证)
  - [RBAC 策略](#rbac-策略)
- [使用方法](#使用方法)
  - [运行智能体](#运行智能体)
  - [管理门户](#管理门户)
- [部署](#部署)
  - [Kubernetes (Helm)](#kubernetes-helm)
  - [OpenShift](#openshift)
  - [AWS (Terraform)](#aws-terraform)
  - [配置管理工具](#配置管理工具)
  - [mTLS 与 Istio 服务网格](#mtls-与-istio-服务网格)
- [CI/CD](#cicd)
  - [Jenkins](#jenkins)
  - [GitLab CI](#gitlab-ci)
- [监控与可观测性](#监控与可观测性)
  - [快速启动 (Docker Compose)](#快速启动-docker-compose)
  - [Prometheus 配置](#prometheus-配置)
  - [指标端点 - 集成](#指标端点-集成)
  - [Grafana（快速配置）](#grafana快速配置)
  - [实用命令 (Makefile)](#实用命令-makefile)
- [测试](#测试)
- [安全性](#安全性)
- [路线图](#路线图)
- [贡献](#贡献)
- [许可证](#许可证)
- [联系方式](#联系方式)

<br>

---

## 功能特性

- **AI 智能体**：两个预置智能体：
  - **SupportAgent**：基于企业文档（PDF、HTML、Markdown）的 RAG 用户支持，具备对话记忆和工单管理工具。
  - **OpsAgent**：SRE/DevOps 自动化 – 从 Prometheus/Grafana 获取指标、执行运维操作（如服务重启），并附带策略控制和审计。
- **模块化核心**：基于 Python 的框架，包含工具注册表、规划器、内存（Redis/Postgres）、RAG（pgvector）和事件系统（NATS）。
- **集成能力**：
  - Java 工单适配器（Spring Boot WebFlux + MySQL）用于企业工单系统。
  - Next.js 管理门户，用于智能体监控、审计和提示词测试。
  - **MCP Gateway**：标准化的网关协议，用于 AI 智能体工具交互，支持安全控制、审计和调用限流。
- **安全性**：OIDC/JWT 认证、基于工具的 RBAC、通过 Istio 实现 mTLS、操作审计。
- **DevOps 就绪**：Docker、Kubernetes (Helm)、OpenShift、Terraform (AWS)、Ansible/Puppet/Salt、CI/CD (Jenkins/GitLab)。
- **可观测性**：OpenTelemetry、Prometheus/Grafana/Loki/Tempo。
- **可扩展性**：Helm 中的 HPA、集成中的重试/超时机制、EKS 中的自动扩缩容。

<br>

---

## 适用场景与用途

**AstraDesk** 是一个面向 **支持团队** 和 **SRE/DevOps 团队** 的 **AI 智能体构建框架**。它提供模块化核心（规划器、内存、RAG、工具注册表）和预置的智能体示例。

- **支持/帮助台**：基于企业文档（流程、FAQ、运维手册）的 RAG、工单创建/更新、对话记忆。
- **SRE/DevOps 自动化**：读取指标（Prometheus/Grafana）、事件分类、受控操作（如服务重启），通过 **RBAC** 保护并纳入审计。
- **企业级集成**：网关（Python/FastAPI）、工单适配器（Java/WebFlux + MySQL）、管理门户（Next.js）、MCP Gateway 以及数据层（Postgres/pgvector、Redis、NATS）。
- **安全与合规**：OIDC/JWT、基于工具的 RBAC、**mTLS**（Istio）、完整审计追踪。
- **规模化运营**：Docker/Kubernetes/OpenShift、Terraform (AWS)、CI/CD (Jenkins/GitLab)、可观测性（OpenTelemetry、Prometheus/Grafana/Loki/Tempo）。

> **这不是单个聊天机器人**，而是一个**框架**，用于组合您自己的智能体、工具和策略，实现完全控制（避免被 SaaS 锁定）。

<br>

---

## 架构概览

AstraDesk 由以下几个核心组件组成：
- **Python API 网关**：FastAPI 处理智能体请求，集成 RAG、内存和工具。
- **Java 工单适配器**：响应式服务（WebFlux）与 MySQL 集成，用于工单管理。
- **Next.js 管理门户**：用于监控的 Web 界面。
- **MCP Gateway**：标准化的网关协议，用于 AI 智能体工具交互，支持安全控制、审计和调用限流。

通信方式：组件间使用 HTTP，事件/审计使用 NATS，工作内存使用 Redis，RAG/对话/审计使用 Postgres/pgvector，工单数据使用 MySQL。

<br>

---

## 前置要求

- **Docker** 和 **Docker Compose**（用于本地开发）。
- **Kubernetes** 搭配 Helm（用于部署）。
- **AWS CLI** 和 **Terraform**（用于云环境）。
- **Node.js 22**、**JDK 21**、**Python 3.11**（用于构建）。
- **Postgres 17**、**MySQL 8**、**Redis 8**、**NATS 2**（基础服务）。
- **可选**：Istio、cert-manager（用于 mTLS/TLS）。

<br>

---

## 快速入门与开发者指南

本节提供完整的指南，帮助您在本地设置、运行和开发 AstraDesk 平台。

<br>

### 前置要求

- **Docker 和 Docker Compose**：运行所有服务的必备条件。推荐使用 Docker Desktop。
- **Git**：用于版本控制。
- **Node.js v22+**：构建管理门户和生成 `package-lock.json` 所需。
- **JDK 21+**：构建和运行 Java 工单适配器所需。
- **Python 3.11+ 和 `uv`**：用于管理 Python 环境。
- **make**：推荐用于便捷访问常用命令。

<br>

### 1. 项目初始设置（仅需运行一次）

1. **克隆仓库**：

   ```bash
   git clone https://github.com/your-org/astradesk.git
   cd astradesk
   ```

2. **复制环境变量文件**：

   ```bash
   cp .env.example .env
   ```

   *注意：`.env` 中的默认值已为混合开发模式配置。对于完整 Docker 模式，您可能需要将 URL 调整为使用服务名称（例如 `http://api:8080`）。*

3. **生成 `package-lock.json`**：

   ```bash
   make bootstrap-frontend
   ```

   *（这将在 `admin-portal` 目录中运行 `npm install`）。*

<br>

### 2. 运行应用程序

选择以下模式之一进行本地开发。

#### 模式 A：完整 Docker 环境（类生产环境）

在 Docker 中运行整个应用栈。最适合集成测试。

* **启动所有服务**：

  ```bash
  make up
  ```
* **停止并清理**：

  ```bash
  make down
  ```

#### 模式 B：混合开发（推荐用于 Python/前端）

在 Docker 中运行外部依赖（数据库、NATS），而您在本地运行 Python API 或 Next.js 门户，以实现快速、热重载的开发体验。

1. **在 Docker 中启动依赖**（在一个终端中）：

   ```bash
   make up-deps
   ```
2. **在本地运行 Python API**（在第二个终端中）：

   ```bash
   make run-local-api
   ```
3. **在本地运行管理门户**（在第三个终端中）：

   ```bash
   make run-local-admin
   ```

<br>

### 3. 常用开发任务 (Makefile)

`Makefile` 是您的中央命令中心。使用 `make help` 查看所有可用命令。

* **运行所有测试**：`make test-all`
* **检查代码质量**：`make lint` 和 `make type`
* **初始化数据库**：`make migrate`
* **导入 RAG 文档**：`make ingest`

<br>

### 4. 测试智能体

应用程序运行后，您可以向 API 发送 `curl` 请求。

*注意：以下示例假设 `main.py` 中的 `auth_guard` 已临时禁用，以便进行本地测试。*

* **测试 `create_ticket` 工具**：

  ```bash
  curl -X POST http://localhost:8080/v1/agents/run \
    -H "Content-Type: application/json" \
    -d '{"agent": "support", "input": "我的网络无法连接，请创建工单。"}'
  ```
* **测试 RAG（知识库）**：

  ```bash
  curl -X POST http://localhost:8080/v1/agents/run \
    -H "Content-Type: application/json" \
    -d '{"agent": "support", "input": "如何重置我的密码？"}'
  ```

### 5. 常见问题解答 (FAQ)

* **Q: 启动时出现 `Connection refused` 错误。**
  **A:** 确保依赖容器已完全运行并处于 `(healthy)` 状态，然后再启动本地 Python 服务器。使用 `docker ps` 检查。

* **Q: 出现 `401 Unauthorized` 或 `Missing Bearer` 错误。**
  **A:** 对于本地测试，您可以临时禁用 `src/gateway/main.py` 中 `run_agent` 端点的 `auth_guard` 依赖。

* **Q: 如何查看特定服务的日志？**
  **A:** 使用 `make logs-api`、`make logs-auditor` 或 `docker logs -f <容器名称>`。

<br>

---

## 配置

### 环境变量

* **DATABASE_URL**：PostgreSQL 连接字符串（例如 `postgresql://user:pass@host:5432/db`）。
* **REDIS_URL**：Redis URI（例如 `redis://host:6379/0`）。
* **NATS_URL**：NATS 服务器（例如 `nats://host:4222`）。
* **TICKETS_BASE_URL**：Java 适配器的 URL（例如 `http://ticket-adapter:8081`）。
* **MYSQL_URL**：MySQL JDBC（例如 `jdbc:mysql://host:3306/db?useSSL=false`）。
* **OIDC_ISSUER**：OIDC 颁发者（例如 `https://your-issuer.com/`）。
* **OIDC_AUDIENCE**：JWT 受众。
* **OIDC_JWKS_URL**：JWKS URL（例如 `https://your-issuer.com/.well-known/jwks.json`）。

完整列表请参见 `.env.example`。

<br>

### OIDC/JWT 认证

* 在 API 网关和 Java 适配器中启用。
* 在请求中使用 Bearer 令牌：`Authorization: Bearer <token>`。
* 验证：颁发者、受众、通过 JWKS 验证签名。
* 在管理门户中：使用 Auth0 或类似服务实现前端通道流程（浏览器重定向认证流程）。

<br>

### RBAC 策略

* 角色来自 JWT claims（例如 `"roles": ["sre"]`）。
* 工具（例如 `restart_service`）通过 `require_role(claims, "sre")` 检查角色。
* 在 `runtime/policy.py` 和工具中调整（例如 `REQUIRED_ROLE_RESTART`）。

<br>

## 使用方法

与 AstraDesk 交互的主要方式是通过其 REST API。

<br>

### 运行智能体

要执行智能体，向 `/v1/agents/run` 端点发送 `POST` 请求：

```sh
curl -X POST http://localhost:8080/v1/agents/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <您的-jwt-令牌>" \
  -d '{"agent": "support", "input": "为网络事件创建工单", "meta": {"user": "alice"}}'
```

响应将是一个 JSON 对象，包含智能体的输出和 `reasoning_trace_id`。

<br>

### 管理门户

基于网页的管理门户，可通过 `http://localhost:3000` 访问，提供用于监控系统健康状况和管理平台组件的 UI，详见 [OpenAPI 规范](openapi/astradesk-admin.v1.yaml)。

<br>

---

## 部署

### Kubernetes (Helm)

1. 构建并推送镜像（使用 CI）。

2. 安装 Chart：

   ```sh
   helm upgrade --install astradesk deploy/chart -f deploy/chart/values.yaml \
     --set image.tag=0.3.0 \
     --set autoscaling.enabled=true
   ```

   - **HPA**：当 CPU >60% 时自动扩缩容。

<br>

### OpenShift

**处理模板**：

   ```sh
   oc process -f deploy/openshift/astradesk-template.yaml -p TAG=0.3.0 | oc apply -f -
   ```

<br>

### AWS (Terraform)

**初始化**：

   ```sh
   cd infra
   terraform init
   terraform apply -var="region=us-east-1" -var="project=astradesk"
   ```

   * 创建：VPC、EKS、RDS (Postgres/MySQL)、S3。

<br>

### 配置管理工具

* **Ansible**：`ansible-playbook -i ansible/inventories/dev/hosts.ini ansible/roles/astradesk_docker/main.yml`。
* **Puppet**：`puppet apply puppet/manifests/astradesk.pp`。
* **Salt**：`salt '*' state.apply astradesk`。

<br>

### mTLS 与 Istio 服务网格

1. 创建命名空间：`kubectl apply -f deploy/istio/00-namespace.yaml`。
2. 启用 mTLS：`kubectl apply -f deploy/istio/10-peer-authentication.yaml`（以及 `deploy/istio/` 中的其余文件）。
3. Gateway：通过 cert-manager 在 443 端口启用 HTTPS。

<br>

---

## CI/CD

### Jenkins

* 运行 Pipeline：`Jenkinsfile` 构建/测试/推送镜像，通过 Helm 部署。

### GitLab CI

* `.gitlab-ci.yml`：阶段包括 build/test/docker/deploy（手动触发）。

<br>

---

## 监控与可观测性 

**(Prometheus, Grafana, OpenTelemetry)**

本节介绍如何使用 **Prometheus**（指标）、**Grafana**（仪表板）和 **OpenTelemetry**（埋点）启用 AstraDesk 平台的完整可观测性。

### 目标

- 从 **Python API 网关**（`/metrics`）和 **Java 工单适配器**（`/actuator/prometheus`）收集指标。
- 在 **Grafana** 中快速查看系统健康状况。
- 在 Prometheus 中设置告警（例如高 5xx 错误率）。

<br>

### 快速启动 (Docker Compose)

以下是添加到 `docker-compose.yml` 的最小片段（Prometheus + Grafana 服务）。
> **注意**：我们假设 `api` 和 `ticket-adapter` 服务按项目配置运行：`api:8080`、`ticket-adapter:8081`。

```yaml
services:
  # --- 可观测性栈 ---
  prometheus:
    image: prom/prometheus:latest
    container_name: astradesk-prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--web.enable-lifecycle"        # 允许配置热重载
    volumes:
      - ./dev/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    restart: unless-stopped
    depends_on:
      - api
      - ticket-adapter

  grafana:
    image: grafana/grafana:latest
    container_name: astradesk-grafana
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_DEFAULT_THEME=dark
    volumes:
      - grafana-data:/var/lib/grafana
      # （可选）自动配置数据源/仪表板：
      # - ./dev/grafana/provisioning:/etc/grafana/provisioning:ro
    ports:
      - "3000:3000"
    restart: unless-stopped
    depends_on:
      - prometheus

volumes:
  prometheus-data:
  grafana-data:
```

<br>

### Prometheus 配置 

`dev/prometheus/prometheus.yml`

创建文件 `dev/prometheus/prometheus.yml`，内容如下：

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  scrape_timeout: 10s
  # 可选: external_labels: { env: "dev" }

scrape_configs:
  # FastAPI 网关 (Python)
  - job_name: "api"
    metrics_path: /metrics
    static_configs:
      - targets: ["api:8080"]

  # Java 工单适配器 (Spring Boot + Micrometer)
  - job_name: "ticket-adapter"
    metrics_path: /actuator/prometheus
    static_configs:
      - targets: ["ticket-adapter:8081"]

  # （可选）NATS Exporter
  # - job_name: "nats"
  #   static_configs:
  #     - targets: ["nats-exporter:7777"]

rule_files:
  - /etc/prometheus/alerts.yml
```

*（可选）添加文件 `dev/prometheus/alerts.yml` 并以类似方式挂载到容器（例如通过额外 volume 或扩展 `prometheus.yml` 而无需单独文件）。*

示例告警规则：

```yaml
groups:
  - name: astradesk-alerts
    rules:
      - alert: HighErrorRate_API
        expr: |
          rate(http_requests_total{job="api",status=~"5.."}[5m])
          /
          rate(http_requests_total{job="api"}[5m]) > 0.05
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "API 高 5xx 错误率（10 分钟内 >5%）"
          description: "请检查 FastAPI 网关日志和上游依赖。"

      - alert: TicketAdapterDown
        expr: up{job="ticket-adapter"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "工单适配器不可用"
          description: "Spring 服务未在 /actuator/prometheus 响应。"
```

> **重载配置** 无需重启：
> `curl -X POST http://localhost:9090/-/reload`

<br>

### 指标端点 - 集成

<br>

#### 1) Python FastAPI (网关)

最简单的方式是通过 `prometheus_client` 暴露 `/metrics`：

```python
# src/gateway/observability.py
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import Summary
from starlette.responses import Response
from fastapi import APIRouter, Request
import time

router = APIRouter()

REQUEST_COUNT = Counter(
    "http_requests_total",
    "HTTP 请求总数",
    ["method", "path", "status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP 请求延迟",
    ["method", "path"]
)

@router.get("/metrics")
def metrics():
    # 以纯文本格式暴露 Prometheus 指标
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# （可选）简单的中间件用于延迟和计数
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    path = request.url.path
    method = request.method
    REQUEST_LATENCY.labels(method=method, path=path).observe(elapsed)
    REQUEST_COUNT.labels(method=method, path=path, status=str(response.status_code)).inc()
    return response
```

在 `main.py` 中注册：

```python
from fastapi import FastAPI
from src.gateway.observability import router as metrics_router, metrics_middleware

app = FastAPI()
app.middleware("http")(metrics_middleware)
app.include_router(metrics_router, tags=["可观测性"])
```

> **替代方案（推荐）**：使用 **OpenTelemetry** + `otlp` 导出器，然后通过 **otel-collector** → Prometheus 抓取指标。此选项可提供一致的指标、追踪和日志。

#### 2) Java 工单适配器 (Spring Boot)

在 `application.yml` 中：

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health, prometheus
  endpoint:
    prometheus:
      enabled: true
  metrics:
    tags:
      application: astradesk-ticket-adapter
  observations:
    key-values:
      env: dev
```

添加 Micrometer Prometheus 依赖：

```xml
<!-- pom.xml -->
<dependency>
  <groupId>io.micrometer</groupId>
  <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>
```

启动后端点可通过以下地址访问：
`http://localhost:8081/actuator/prometheus`（或在 Docker 中使用 `ticket-adapter:8081`）。

<br>

### Grafana（快速配置）

启动 Grafana 后（[http://localhost:3000](http://localhost:3000)，默认 `admin`/`admin`）：

1. **添加数据源 → Prometheus**
   URL: `http://prometheus:9090`（从 Docker Compose 网络视角）或 `http://localhost:9090`（如果从主机手动添加）。
2. **导入仪表板**（例如"Prometheus / Overview"或自定义）。
   您也可以在仓库中维护描述符（`grafana/dashboard-astradesk.json`）并启用预配：

   ```
   dev/grafana/provisioning/datasources/prometheus.yaml
   dev/grafana/provisioning/dashboards/dashboards.yaml
   grafana/dashboard-astradesk.json
   ```

数据源示例（预配）：

```yaml
# dev/grafana/provisioning/datasources/prometheus.yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

仪表板声明示例：

```yaml
# dev/grafana/provisioning/dashboards/dashboards.yaml
apiVersion: 1
providers:
  - name: "AstraDesk"
    orgId: 1
    folder: "AstraDesk"
    type: file
    options:
      path: /var/lib/grafana/dashboards
```

<br>

### 实用命令 (Makefile)

在 `Makefile` 中添加快捷方式以简化工作：

```Makefile
.PHONY: up-observability down-observability logs-prometheus logs-grafana

up-observability:
	docker compose up -d prometheus grafana

down-observability:
	docker compose rm -sfv prometheus grafana

logs-prometheus:
	docker logs -f astradesk-prometheus

logs-grafana:
	docker logs -f astradesk-grafana
```

<br>

### 验证运行状态

* Prometheus UI: **[http://localhost:9090](http://localhost:9090)**

  * 检查 `api` 和 `ticket-adapter` 任务是否处于 **UP** 状态（Status → Targets）。

* Grafana UI: **[http://localhost:3000](http://localhost:3000)**

  * 连接数据源（Prometheus），导入仪表板并观察指标（延迟、请求数、5xx 错误）。

* 快速测试：

  ```bash
  curl -s http://localhost:8080/metrics | head

  curl -s http://localhost:8081/actuator/prometheus | head
  ```

<br>

> 如果端点未返回指标，请确保：
>
> 1) 路径（`/metrics`、`/actuator/prometheus`）已启用，
>
> 2) 服务在 Compose 网络中可通过名称 `api` / `ticket-adapter` 访问，
>
> 3) `prometheus.yml` 指向正确的 `targets`。

<br>

---

## 测试

* 运行：`make test`（Python）、`make test-java`、`make test-admin`。
* 覆盖率：单元测试（pytest、JUnit、Vitest）、集成测试（API 流程）。

<br>

---

## 安全性

* **认证**：带 JWKS 的 OIDC/JWT。
* **RBAC**：基于 claim 的每工具权限控制。
* **mTLS**：通过 Istio 启用 STRICT 模式。
* **审计**：写入 Postgres + 通过 NATS 发布。
* **策略**：工具中的允许列表、代理中的重试机制。

<br>

---

## 路线图

* 集成 LLM（Bedrock/OpenAI/vLLM）并配备安全防护机制。
* 使用 Temporal 处理长时工作流。
* RAG 评估（Ragas）。
* 多租户和高级 RBAC（OPA）。
* 带告警的完整 Grafana 仪表板。

<br>

---

## 贡献

* Fork 仓库，创建分支，提交带测试的 PR。
* 提交前使用 `make lint/type` 检查。

<br>

---

## 许可证

Apache License 2.0。详情请参见 [LICENSE](LICENSE)。

---

<br>

## 联系方式

🌐 网站: [AstraDesk](https://www.astradesk.dev)

📧 作者: Siergej Sobolewski ([s.sobolewski@hotmail.com](mailto:s.sobolewski@hotmail.com))。

💬 支持渠道: [Support Slack](https://astradesk.slack.com)

🐙 Issues: [GitHub Issues](https://github.com/SSobol77/astradesk/issues)。

<br>

---

*最后更新: 2026-04-09*
