<p align="center">
  <img src="docs/assets/AstraDesktop.png" alt="AstraDesk - AI 框架" width="560"/>
</p>

<br>

# AstraDesk Duo - 内部 AI 代理框架

[![许可证](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Python 版本](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![JDK 版本](https://img.shields.io/badge/JDK-21-green.svg)](https://openjdk.org/projects/jdk/21/)
[![Node.js 版本](https://img.shields.io/badge/Node.js-22-brightgreen.svg)](https://nodejs.org/en)
[![构建状态](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](https://github.com/your-org/astradesk/actions)

🌍 **语言版本:** [英文](astradesk/README.md) | [波兰文](astradesk/docs/pl/README.pl.main.md) | 🇨🇳 [中文 (当前文件)](docs/zh/README.zh.main.md)

<br>

[AstraDesk](https://astradesk.vercel.app/)
是-个用于构建 AI 代理的内部框架，专为 **技术支持团队 (Support)** 和 **SRE/DevOps 团队** 设计。  
它采用模块化架构，内置可直接使用的演示代理，支持数据库、消息系统和 DevOps 工具集成。  
该框架具备可扩展性、企业级安全 (OIDC/JWT、RBAC、mTLS via Istio) 以及端到端的 CI/CD 支持。

<br>

---

## 📘 目录 (Table of Contents)

- [主要特性](#主要特性)
- [目标与使用场景](#目标与使用场景)
- [架构概览](#架构概览)
- [前置条件](#前置条件)
- [安装说明](#安装说明)
  - [使用 Docker Compose 本地开发](#使用-docker-compose-本地开发)
  - [从源码构建](#从源码构建)
- [配置](#配置)
  - [环境变量](#环境变量)
  - [OIDC/JWT 认证](#oidcjwt-认证)
  - [RBAC 策略](#rbac-策略)
- [使用方法](#使用方法)
  - [运行代理](#运行代理)
  - [导入文档以供 RAG 使用](#导入文档以供-rag-使用)
  - [管理门户](#管理门户)
  - [工具与集成](#工具与集成)
- [部署](#部署)
  - [Kubernetes + Helm](#kubernetes--helm)
  - [OpenShift](#openshift)
  - [AWS + Terraform](#aws--terraform)
  - [配置管理工具](#配置管理工具)
  - [mTLS 与 Istio 服务网格](#mtls-与-istio-服务网格)
- [CI/CD](#cicd)
  - [Jenkins](#jenkins)
  - [GitLab CI](#gitlab-ci)
- [监控与可观测性](#监控与可观测性)
- [开发者指南](#开发者指南)
- [测试](#测试)
- [安全](#安全)
- [路线图](#路线图)
- [贡献指南](#贡献指南)
- [许可证](#许可证)
- [联系信息](#联系信息)

<br>

## 🌟 主要特性 (Features)

- **AI 智能代理 (AI Agents)**：提供两个即开即用的智能代理：
  - **SupportAgent**：基于公司文档 (PDF、HTML、Markdown) 的 RAG 用户支持系统，具备对话记忆与工单管理功能。
  - **OpsAgent**：面向 SRE/DevOps 的自动化代理 - 支持从 Prometheus/Grafana 获取指标、执行运维操作（例如重启服务），并具备策略与审计跟踪功能。

- **模块化核心 (Modular Core)**：  
  基于 Python 的核心框架，内置工具注册中心、任务规划器、记忆管理 (Redis/Postgres)、RAG（通过 pgvector）以及事件总线 (NATS)。

- **系统集成 (Integrations)**：
  - Java 工单适配器：采用 Spring Boot WebFlux + MySQL 构建的企业级工单系统集成模块。
  - Next.js 管理门户：用于监控代理、查看审计日志和测试提示 (Prompts)。

- **安全机制 (Security)**：  
  支持 OIDC/JWT 认证、基于工具的细粒度 RBAC 权限控制、Istio 提供的 mTLS 双向认证与操作审计。

- **DevOps 准备就绪 (DevOps Ready)**：  
  提供全面的运维与交付工具链 - Docker、Kubernetes (Helm)、OpenShift、Terraform (AWS)、Ansible、Puppet、Salt，以及 Jenkins/GitLab CI/CD 管道。

- **可观测性 (Observability)**：  
  集成 OpenTelemetry、Prometheus、Grafana、Loki、Tempo，用于监控与日志追踪。

- **高可扩展性 (Scalability)**：  
  支持 Helm 中的自动水平扩展 (HPA)，集成超时与重试机制，可在 AWS EKS 上实现自动扩缩容。

<br>

## 🎯 目标与使用场景 (Purpose & Use Cases)

**AstraDesk** 是一个面向 **技术支持团队 (Support)** 与 **SRE/DevOps 团队** 的内部 **AI 智能代理框架**。  
它提供模块化核心（任务规划器、记忆模块、RAG、工具注册中心），以及可直接运行的演示代理。

典型应用场景包括：

<br>

### 🧭 客服与帮助台 (Support / Helpdesk)
通过 RAG 技术在公司文档（流程文档、FAQ、运行手册等）上进行知识检索，  
自动创建与更新工单，并保持会话上下文记忆。  
支持在聊天式界面中快速响应常见问题。

<br>

### ⚙️ SRE / DevOps 自动化
用于监控指标 (Prometheus/Grafana)、事件分级、自动化修复与服务重启操作。  
所有操作均受 **RBAC 权限控制** 并自动记录到审计日志中。  
可执行受控任务，如：
- 重启服务（受角色策略限制）  
- 触发 Jenkins pipeline  
- 查询性能指标  
- 生成告警报告  

<br>

### 🧩 企业系统集成 (Enterprise Integrations)
框架支持多语言与多组件架构：
- **Python/FastAPI**：作为核心网关与业务调度层。  
- **Java/WebFlux + MySQL**：作为工单适配器 (Ticket Adapter)。  
- **Next.js Admin Portal**：提供监控与交互式管理界面。  
- **数据平面**：基于 Postgres/pgvector、Redis、NATS 构建的存储与事件系统。

<br>

### 🔐 安全与合规 (Security & Compliance)
- 支持 **OIDC/JWT 单点认证**。  
- **RBAC** 精细化授权。  
- 通过 **Istio** 启用双向 **mTLS 加密**。  
- 全量 **审计追踪 (Audit Trail)**。

<br>

### ☁️ 大规模运维与部署 (Operations at Scale)
框架已适配现代云原生环境：
- **容器化部署**：Docker / Kubernetes / OpenShift  
- **基础设施即代码**：Terraform (AWS)  
- **自动化 CI/CD**：Jenkins、GitLab CI  
- **可观测性体系**：OpenTelemetry + Prometheus + Grafana + Loki + Tempo

<br>

> ⚡ **注意**：  
> AstraDesk 并不是一个单纯的「聊天机器人」(chatbot)，  
> 而是一个 **可组合的 AI 代理框架**，  
> 让你能够完全自定义代理、工具和策略，  
> 无需依赖任何 SaaS 平台或供应商锁定。

<br>

## 🏗️ 架构概览 (Architecture Overview)

**AstraDesk** 框架由三个核心组件组成：

<br>

### 🐍 1. Python API 网关 (Python API Gateway)
基于 **FastAPI** 构建的主控制层，用于：
- 接收代理请求 (agent requests)；
- 执行 RAG（基于知识库的检索增强生成）；
- 管理对话记忆与工具调用；
- 进行身份验证与授权。

API 网关负责连接所有代理逻辑与工具模块，是系统的“指挥中心”。

<br>

### ☕ 2. Java 工单适配器 (Java Ticket Adapter)
基于 **Spring Boot WebFlux** 的响应式微服务，  
主要用于与 **MySQL 工单数据库** 集成。  
它实现了企业工单系统（如 Jira、ServiceNow、Zendesk）的接口，  
支持异步、非阻塞的数据传输与事务处理。

<br>

### 💻 3. Next.js 管理门户 (Next.js Admin Portal)
基于 **Next.js + TypeScript** 的 Web 管理前端，  
用于监控 AI 代理的运行状态、查看审计日志、测试 Prompt 及调用 API。  
管理员可以：
- 执行健康检查；
- 查看代理日志与追踪；
- 管理角色与策略。

<br>

### 🔗 组件间通信 (Inter-Component Communication)
各组件之间通过多种协议协作：

| 通信方向 | 协议 | 用途 |
|-----------|-------|------|
| 组件之间 | **HTTP/REST** | 组件间的主要通信接口 |
| 异步事件流 | **NATS** | 事件与审计日志的传输 |
| 快速缓存 | **Redis** | 工作记忆与上下文存储 |
| 长期数据 | **Postgres/pgvector** | 对话、RAG 知识库与审计数据 |
| 工单数据 | **MySQL** | 工单记录与企业集成模块 |

<br>

🧩 总体架构示意图：

```sh
    ┌────────────────────────┐
    │  Next.js Admin Portal  │
    │       (前端控制台)       │
    └────────────┬───────────┘
                 │ HTTP (REST)
                 ▼
    ┌──────────────────────────┐
    │ FastAPI Gateway (Python) │
    │  - RAG / Planner / Tools │
    │  - OIDC / JWT / RBAC     │
    └────────────┬─────────────┘
                 │ NATS / Redis / Postgres
                 ▼
    ┌─────────────────────────┐
    │ Java Ticket Adapter     │
    │ (Spring WebFlux + MySQL)│
    └─────────────────────────┘

```


该架构具备高扩展性与模块解耦性，  
支持微服务部署、可插拔代理逻辑以及云原生环境中的弹性伸缩。

<br>

---

## ⚙️ 前置条件 (Prerequisites)

在开始使用 **AstraDesk** 之前，请确保你的开发或部署环境满足以下要求：

<br>

### 🐳 本地开发环境 (Local Development)

- **Docker** 与 **Docker Compose**  
  用于在本地快速启动所有微服务组件（API 网关、工单服务、数据库等）。

<br>

### ☸️ 集群与云部署 (Cluster / Cloud Deployment)

- **Kubernetes** 与 **Helm**  
  用于生产级部署与管理应用的生命周期。  
  AstraDesk 提供官方 Helm Chart，支持自动扩缩容 (HPA)。

- **AWS CLI** 与 **Terraform**  
  用于在 AWS 云上自动创建基础设施（VPC、EKS、RDS、S3 等）。  
  所有资源可通过 IaC（基础设施即代码）定义与重复部署。

<br>

### 🧰 构建工具 (Build Toolchain)

| 工具 | 最低版本 | 用途 |
|------|------------|------|
| **Node.js** | 22.x | 构建 Next.js 管理门户 |
| **JDK** | 21 | 编译 Java 工单适配器 |
| **Python** | 3.11 | 运行核心 API 网关与代理逻辑 |
| **make** | 任意 | 自动化构建脚本 |

<br>

### 🗄️ 基础服务 (Base Services)

为保证系统正常运行，需要以下服务：

- **PostgreSQL 17**：主数据仓库，存储代理对话、RAG 知识库与审计记录。  
- **MySQL 8**：工单系统数据源（Java Ticket Adapter）。  
- **Redis 7**：缓存与短期记忆 (working memory)。  
- **NATS 2**：事件与审计日志传输总线。

<br>

### 🔒 可选组件 (Optional)

为增强安全性与可观测性，推荐启用以下组件：

- **Istio**：服务网格，提供 mTLS 双向加密与零信任通信。  
- **cert-manager**：自动化 TLS/SSL 证书管理。  

<br>

💡 **提示**：  
如仅在本地开发环境中运行，可通过 `make up` 使用 Docker Compose 自动启动所有依赖。

<br>

---

## 🚀 安装说明 (Installation)

AstraDesk 支持两种安装与运行模式：

1. **使用 Docker Compose 进行本地开发与测试**  
2. **从源码构建并本地运行**

<br>

### 🐳 使用 Docker Compose 进行本地开发 (Local Development with Docker Compose)

1. **克隆仓库：**
   ```bash
   git clone https://github.com/your-org/astradesk.git
   cd astradesk
   ```

2. **复制示例配置文件：**

   ```bash
   cp .env.example .env
   ```

   编辑 `.env` 文件，根据实际环境修改变量，例如：

   * `DATABASE_URL` — 数据库连接字符串
   * `OIDC_ISSUER` — 身份提供方 (OIDC Provider)

3. **构建并启动服务：**

   ```bash
   make up
   ```

   该命令会自动启动以下容器：

   * API 网关 (端口 8080)
   * 工单适配器 (端口 8081)
   * 管理门户 (端口 3000)
   * 数据库与依赖服务（Postgres、Redis、MySQL、NATS）

4. **初始化 Postgres（启用 pgvector 扩展）：**

   ```bash
   make migrate
   ```

5. **导入文档以初始化 RAG 知识库：**
   将 `.md` 或 `.txt` 文件放入 `./docs` 目录中，然后执行：

   ```bash
   make ingest
   ```

6. **健康检查：**

   ```bash
   curl http://localhost:8080/healthz
   ```

   管理门户访问地址为：
   👉 [http://localhost:3000](http://localhost:3000)

<br>

### ⚙️ 从源码构建 (Building from Source)

如果你希望直接在本地运行源码而非使用 Docker，可按以下步骤操作：

1. **安装依赖：**

   ```bash
   make sync          # 安装 Python 依赖
   make build-java    # 构建 Java 工单服务
   make build-admin   # 构建 Next.js 管理门户
   ```

2. **在本地启动各个模块（无需容器）：**

   * 启动 Python API 网关：

     ```bash
     uv run uvicorn gateway.main:app --host 0.0.0.0 --port 8080 --reload
     ```
   * 启动 Java 工单适配器：

     ```bash
     cd services/ticket-adapter-java && ./gradlew bootRun
     ```
   * 启动 Next.js 管理门户：

     ```bash
     cd services/admin-portal && npm run dev
     ```

<br>

💡 **提示 (Tips)**

* 使用 `make down` 可停止所有容器并清理卷。
* 修改 `.env` 后，请重新运行 `make up` 以加载最新环境变量。
* 首次构建 Admin Portal 时，系统将自动生成 `package-lock.json`。
* 若 Postgres 或 Redis 启动失败，可使用 `docker ps` 检查容器状态是否为 `(healthy)`。

<br>

---

## ⚙️ 配置 (Configuration)

AstraDesk 的配置完全通过环境变量 (.env) 管理，支持灵活部署与安全控制。  
以下部分介绍了核心环境变量、OIDC/JWT 认证机制以及 RBAC 策略配置。

<br>

### 🌍 环境变量 (Environment Variables)

| 变量名 | 示例值 | 说明 |
|--------|---------|------|
| **DATABASE_URL** | `postgresql://user:pass@host:5432/db` | PostgreSQL 数据库连接字符串 |
| **REDIS_URL** | `redis://host:6379/0` | Redis 缓存服务地址 |
| **NATS_URL** | `nats://host:4222` | NATS 事件与消息总线地址 |
| **TICKETS_BASE_URL** | `http://ticket-adapter:8081` | Java 工单服务的基础 URL |
| **MYSQL_URL** | `jdbc:mysql://host:3306/db?useSSL=false` | MySQL JDBC 连接字符串 |
| **OIDC_ISSUER** | `https://your-issuer.com/` | OIDC 授权服务提供者地址 |
| **OIDC_AUDIENCE** | `astradesk-client` | JWT 令牌受众 (Audience) |
| **OIDC_JWKS_URL** | `https://your-issuer.com/.well-known/jwks.json` | 公钥 JWKS 端点，用于验证签名 |

📘 **提示**：  
完整的变量列表可参考项目根目录下的 `.env.example` 文件。

<br>

### 🔐 OIDC/JWT 认证 (OIDC/JWT Authentication)

AstraDesk 的 API 网关与 Java 工单服务均支持 **OpenID Connect (OIDC)** 与 **JWT 令牌认证**。

- **启用方式：**  
  默认启用。请求需携带有效的 Bearer 令牌：
  ```http
  Authorization: Bearer <token>
  ```

* **验证内容：**

  * 签发方 (issuer)
  * 受众 (audience)
  * 签名有效性（通过 JWKS URL 自动校验）

* **前端认证流程：**
  管理门户 (Admin Portal) 可集成 Auth0 或任意兼容 OIDC 的身份提供方。
  登录成功后，前端会获取 JWT 并附加到所有 API 请求头中。

<br>

### 🧩 RBAC 策略 (RBAC Policies)

AstraDesk 使用基于角色的访问控制 (**Role-Based Access Control**) 来定义每个用户能执行的操作。

* **角色信息**
  由 JWT 中的 `roles` 声明传递，例如：

  ```json
  {
    "sub": "alice",
    "roles": ["sre"]
  }
  ```

* **工具权限验证**
  每个工具 (tool) 在执行前会检查调用者是否具备所需角色：

  ```python
  require_role(claims, "sre")
  ```

  示例：

  * `restart_service` 工具要求角色 `"sre"`
  * `create_ticket` 工具要求角色 `"support"`

* **策略配置文件位置：**

  * Python 网关：`runtime/policy.py`
  * 工具定义：各模块内部常量，如 `REQUIRED_ROLE_RESTART`

<br>

🧠 **安全建议 (Best Practices)**

* 不要在 `.env` 文件中保存明文密钥或私钥。
* 使用云端机密管理系统（如 AWS Secrets Manager、Vault）。
* 生产环境中启用 **mTLS** 与 **JWT 过期检查**。
* 定期轮换 OIDC 公钥 (JWKS)。

<br>

---

## 🚀 使用方法 (Usage)

本节介绍如何运行 AstraDesk 的 AI 代理、加载知识文档 (RAG)、访问管理门户以及添加自定义工具与集成模块。

<br>

### 🤖 运行代理 (Running Agents)

通过 REST API 调用代理服务：

```bash
curl -X POST http://localhost:8080/v1/agents/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{
    "agent": "support",
    "input": "Create a ticket for a network incident",
    "meta": {"user": "alice"}
  }'
```

* 返回结果为 JSON 格式，包含：

  * 代理输出 (`output`)
  * 跟踪 ID (`trace_id`)
  * 所用工具 (`used_tools`)
* 示例脚本位于 `./scripts/demo_queries.sh`。

<br>

### 📚 导入文档以供 RAG 使用 (Ingesting Documents for RAG)

RAG (Retrieval-Augmented Generation) 模块支持将公司内部文档作为知识来源。

* 支持格式：`.md`、`.txt`（可扩展为 PDF/HTML）

* 执行以下命令以导入文档：

  ```bash
  make ingest
  ```

* 默认文档目录为：`./docs`

导入完成后，文档内容将被索引并存储于 PostgreSQL + pgvector 数据库中，以便代理在回答时进行语义检索。

<br>

### 🧭 管理门户 (Admin Portal)

Web 管理界面提供对系统状态与代理运行的可视化监控。

* 访问地址: [http://localhost:3000](http://localhost:3000)
* 功能包括：

  * 查看 API 健康状态；
  * 执行示例调用；
  * 调试代理行为；
  * 查看系统版本、日志与统计。

要扩展管理门户的功能，例如显示审计日志，可在 API 层添加新端点 `/v1/audits` 并在前端调用。

<br>

### 🧩 工具与系统集成 (Tools and Integrations)

AstraDesk 的核心设计是“工具注册表 (Tool Registry)”-允许动态注册、扩展和调用外部操作。

* 工具注册位置：`registry.py`
  添加新工具时使用：

  ```python
  register(name, async_fn)
  ```

* 示例工具：

  * `create_ticket` — 代理到 Java 工单系统；
  * `get_metrics` — 从 Prometheus 获取性能指标；
  * `restart_service` — 通过 RBAC 控制的安全服务重启。

每个工具均可附带策略验证、审计记录与错误重试逻辑，确保生产环境的稳定性与可追踪性。

<br>

## ☁️ 部署 (Deployment)

AstraDesk 可部署在多种环境中，包括 Kubernetes、OpenShift、AWS 云，以及使用多种配置管理工具。  
以下为推荐的生产环境部署方式。

<br>

### ☸️ 使用 Helm 在 Kubernetes 上部署 (Kubernetes with Helm)

1. **构建并推送容器镜像**  
   （可在 CI/CD 流程中自动完成）

2. **安装或升级 Helm Chart：**
   ```bash
   helm upgrade --install astradesk deploy/chart \
       -f deploy/chart/values.yaml \
       --set image.tag=0.2.1 \
       --set autoscaling.enabled=true
   ```

3. **自动伸缩 (HPA)**
   Helm Chart 已配置 **Horizontal Pod Autoscaler**，默认当 CPU 使用率超过 60% 时自动扩容。

<br>

### 🏗️ 在 OpenShift 上部署 (OpenShift)

1. **通过模板部署：**

   ```bash
   oc process -f deploy/openshift/astradesk-template.yaml -p TAG=0.2.1 | oc apply -f -
   ```

2. **OpenShift 优势：**

   * 内置 RBAC 与服务账户控制；
   * 集成 OpenShift Route，支持 HTTPS；
   * 支持自动构建与滚动升级。

<br>

### ☁️ 使用 Terraform 在 AWS 上部署 (AWS with Terraform)

1. **初始化 Terraform：**

   ```bash
   cd infra
   terraform init
   terraform apply -var="region=us-east-1" -var="project=astradesk"
   ```

2. **自动创建以下资源：**

   * **VPC** — 虚拟私有云网络
   * **EKS** — 托管 Kubernetes 集群
   * **RDS** — 托管数据库（Postgres + MySQL）
   * **S3** — 存储审计与模型文件

3. **Terraform 优势：**

   * 完全 IaC 化（基础设施即代码）；
   * 可重复、可回滚部署；
   * 与 Jenkins/GitLab CI 集成实现自动化云端部署。

<br>

### 🧰 配置管理工具 (Configuration Management Tools)

AstraDesk 兼容多种基础设施自动化工具：

| 工具            | 命令示例                                                                                            | 用途                   |
| ------------- | ----------------------------------------------------------------------------------------------- | -------------------- |
| **Ansible**   | `ansible-playbook -i ansible/inventories/dev/hosts.ini ansible/roles/astradesk_docker/main.yml` | 在远程主机上批量部署 Docker 环境 |
| **Puppet**    | `puppet apply puppet/manifests/astradesk.pp`                                                    | 配置并维护持久化系统状态         |
| **SaltStack** | `salt '*' state.apply astradesk`                                                                | 在大规模节点环境中推送配置与更新     |

这些工具可与 CI/CD 管道结合，实现完全自动化的多环境配置同步与滚动更新。

<br>

### 🔒 mTLS 与 Istio 服务网格 (mTLS and Istio Service Mesh)

1. **创建命名空间：**

   ```bash
   kubectl apply -f deploy/istio/00-namespace.yaml
   ```

2. **启用双向 TLS 验证：**

   ```bash
   kubectl apply -f deploy/istio/10-peer-authentication.yaml
   ```

   （以及目录 `deploy/istio/` 中的其他 YAML 配置）

3. **配置 Gateway：**

   * 使用 HTTPS 443 端口；
   * 通过 **cert-manager** 自动签发与更新证书；
   * 在 Gateway 层启用安全入口流量控制。

<br>

🧠 **最佳实践 (Best Practices)**

* 在生产环境启用 **mTLS + RBAC + NetworkPolicy** 三重安全机制；
* 使用 **Helm values.yaml** 参数化部署配置；
* 建议使用 **Terraform + Helm Provider** 进行全自动部署；
* 所有 Secrets 应存储在安全系统（Vault / AWS Secrets Manager）中。

<br>

## 🔄 持续集成与交付 (CI/CD)

AstraDesk 支持多种 CI/CD 流水线，能够在构建、测试、镜像推送和部署阶段实现全自动化。  
推荐使用 **Jenkins** 或 **GitLab CI** 来执行持续集成与交付任务。

<br>

### 🧱 Jenkins 集成 (Jenkins)

AstraDesk 内置了一个示例 **Jenkinsfile**，用于自动化构建、测试与部署流程。

主要阶段包括：

1. **Build 阶段**
   - 构建 Python、Java 和 Next.js 模块；
   - 执行 `make build-java` 与 `make build-admin`；
   - 构建 Docker 镜像并打标签。

2. **Test 阶段**
   - 运行单元测试与集成测试：
     ```bash
     make test-all
     ```
   - 检查类型与代码规范（使用 Ruff / Pyright / ESLint）。

3. **Push 阶段**
   - 推送镜像到私有仓库（如 AWS ECR / GitHub Packages）。

4. **Deploy 阶段**
   - 调用 Helm 自动部署到 Kubernetes 集群：
     ```bash
     helm upgrade --install astradesk deploy/chart
     ```

🧩 **优点：**
- 可与 SonarQube、Prometheus、Slack 等集成；
- 支持并行 Pipeline；
- 支持构建缓存与蓝绿部署。

<br>

### 🦊 GitLab CI 集成 (GitLab CI)

在 `.gitlab-ci.yml` 中定义了完整的构建与部署阶段：

| 阶段 | 说明 |
|------|------|
| **build** | 构建 Python、Java、Admin 三个模块并生成镜像 |
| **test** | 执行 pytest、JUnit 与 Vitest 测试 |
| **docker** | 构建并推送 Docker 镜像 |
| **deploy** | 手动或自动化部署至 Kubernetes 或 AWS 环境 |

示例配置片段：

```yaml
stages:
  - build
  - test
  - docker
  - deploy

build:
  stage: build
  script:
    - make sync
    - make build-java
    - make build-admin

test:
  stage: test
  script:
    - make test-all

docker:
  stage: docker
  script:
    - docker build -t registry.example.com/astradesk:$CI_COMMIT_SHA .
    - docker push registry.example.com/astradesk:$CI_COMMIT_SHA

deploy:
  stage: deploy
  when: manual
  script:
    - helm upgrade --install astradesk deploy/chart -f deploy/chart/values.yaml
```

🚀 **建议：**

* 在 GitLab Runner 上启用 Docker-in-Docker 支持；
* 使用缓存加速 `npm install` 与 Gradle 构建；
* 结合 GitLab Environments 实现多环境（dev/stage/prod）部署；
* 可添加安全扫描 (SAST/DAST) 阶段以增强合规性。

<br>

🧠 **最佳实践 (Best Practices)**

* 统一版本号与构建标签（Git 标签 + Docker tag）；
* 在 CI 流程中执行 Lint、Type Check 与单元测试；
* 所有部署操作应基于 Infrastructure as Code；
* 建议使用 OIDC 认证从 CI/CD 平台安全访问云资源。

<br>

---

## 📊 监控与可观测性 (Monitoring and Observability)

**（Prometheus、Grafana、OpenTelemetry）**

本节说明如何为 AstraDesk 启用完整的可观测性：使用 **Prometheus**（指标）、**Grafana**（仪表盘）与 **OpenTelemetry**（代码埋点/自动化检测）。

### 目标
- 从 **Python API 网关**（`/metrics`）与 **Java 工单适配器**（`/actuator/prometheus`）采集指标。
- 在 **Grafana** 中快速查看系统健康状况。
- 在 Prometheus 中配置告警（例如 5xx 错误率过高）。

<br>

### 快速开始（Docker Compose）

下面是添加 Prometheus 与 Grafana 的最小 `docker-compose.yml` 片段。
> **注意：** 假设 `api` 与 `ticket-adapter` 服务分别运行在 `api:8080`、`ticket-adapter:8081`。

```yaml
services:
  # --- Observability stack ---
  prometheus:
    image: prom/prometheus:latest
    container_name: astradesk-prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--web.enable-lifecycle"        # 允许热加载配置
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
      # （可选）自动配置数据源/仪表盘：
      # - ./dev/grafana/provisioning:/etc/grafana/provisioning:ro
    ports:
      - "3000:3000"
    restart: unless-stopped
    depends_on:
      - prometheus

volumes:
  prometheus-data:
  grafana-data:
````

<br>

### Prometheus 配置（`dev/prometheus/prometheus.yml`）

创建 `dev/prometheus/prometheus.yml`，内容如下：

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  scrape_timeout: 10s
  # 可选: external_labels: { env: "dev" }

scrape_configs:
  # FastAPI 网关（Python）
  - job_name: "api"
    metrics_path: /metrics
    static_configs:
      - targets: ["api:8080"]

  # Java 工单适配器（Spring Boot + Micrometer）
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

*（可选）新建 `dev/prometheus/alerts.yml`，并以类似方式挂载到容器；也可直接把规则合并进 `prometheus.yml`。*

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
          summary: "API 5xx 错误率过高（10 分钟内 > 5%）"
          description: "请检查 FastAPI 网关日志与上游依赖。"

      - alert: TicketAdapterDown
        expr: up{job="ticket-adapter"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "工单适配器不可用"
          description: "Spring 服务未在 /actuator/prometheus 响应。"
```

> **无重启热加载配置：**
> `curl -X POST http://localhost:9090/-/reload`

<br>

### 指标端点集成

#### 1）Python FastAPI（网关）

使用 `prometheus_client` 暴露 `/metrics` 最为简单：

```python
# src/gateway/observability.py
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from fastapi import APIRouter, Request
import time

router = APIRouter()

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"]
)

@router.get("/metrics")
def metrics():
    # 以 Prometheus 纯文本格式导出指标
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# （可选）简单中间件：记录延迟与请求计数
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
app.include_router(metrics_router, tags=["observability"])
```

> **（推荐）替代方案：** 使用 **OpenTelemetry** + `otlp` 导出器，然后通过 **otel-collector** → Prometheus 采集。这样可以统一指标、链路追踪与日志。

#### 2）Java 工单适配器（Spring Boot）

在 `application.yml` 中启用：

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

引入 Micrometer Prometheus 依赖：

```xml
<!-- pom.xml -->
<dependency>
  <groupId>io.micrometer</groupId>
  <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>
```

启动后指标端点为：
`http://localhost:8081/actuator/prometheus`（Docker 网络中为 `ticket-adapter:8081`）。

<br>

### Grafana —— 快速配置

Grafana 启动后（[http://localhost:3000，默认账号](http://localhost:3000，默认账号) `admin`/`admin`）：

1. **添加数据源 → Prometheus**
   URL：`http://prometheus:9090`（在 Docker Compose 网络内）或 `http://localhost:9090`（从宿主浏览器连接）。
2. **导入仪表盘**（如官方「Prometheus / Overview」或自定义仪表盘）。
   也可将仪表盘描述文件放入仓库并启用 provisioning：

   ```
   dev/grafana/provisioning/datasources/prometheus.yaml
   dev/grafana/provisioning/dashboards/dashboards.yaml
   grafana/dashboard-astradesk.json
   ```

示例数据源（provisioning）：

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

示例仪表盘提供者：

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

### 常用命令（Makefile）

建议在 `Makefile` 中加入以下快捷命令：

```Makefile
.PHONY: up-observability down-observability logs-prometheus logs-grafana

up-observability:
\tdocker compose up -d prometheus grafana

down-observability:
\tdocker compose rm -sfv prometheus grafana

logs-prometheus:
\tdocker logs -f astradesk-prometheus

logs-grafana:
\tdocker logs -f astradesk-grafana
```

<br>

### 验证清单

* Prometheus UI：**[http://localhost:9090](http://localhost:9090)**

  * 在「Status → Targets」确认 `api`、`ticket-adapter` 的 job 状态为 **UP**。
* Grafana UI：**[http://localhost:3000](http://localhost:3000)**

  * 连接 Prometheus 数据源，导入仪表盘，观察关键指标（延迟、请求数、5xx 错误等）。
* 快速测试：

  ```bash
  curl -s http://localhost:8080/metrics | head
  curl -s http://localhost:8081/actuator/prometheus | head
  ```

> 若端点未返回指标，请检查：
> (1) 路径（`/metrics`、`/actuator/prometheus`）是否启用；
> (2) 在 Compose 网络内，`api`/`ticket-adapter` 服务名是否可达；
> (3) `prometheus.yml` 的 `targets` 是否填写正确。


<br>

---

## 🧑‍💻 开发者指南 (Developer’s Guide)

本节提供 AstraDesk 开发环境的快速上手指南，包括环境准备、运行方式、测试、数据库操作与常见问题排查。

<br>

### 🧩 1. 基础环境设置 (Basic Environment Setup)

在开始开发前，请确保你已安装以下工具：

- **Docker / Docker Compose**（推荐使用 Docker Desktop）  
- **Git**  
- **make**  
- **Node.js (v22+)**

**初始准备步骤：**

1. 克隆仓库：
   ```bash
   git clone https://github.com/your-org/astradesk.git
   cd astradesk
   ```

2. 复制配置文件：

   ```bash
   cp .env.example .env
   ```

3. 生成 `package-lock.json` 文件（构建 Admin Portal 所需）：

   ```bash
   cd services/admin-portal && npm install && cd ../..
   ```

<br>

### 🚀 2. 如何运行应用 (How to Run the Application)

AstraDesk 支持两种运行模式：

<br>

#### 🐳 模式 A：完整 Docker 环境 (Full Docker Environment) — 推荐

运行整个系统（所有微服务）于 Docker 容器中。
适用于集成测试或生产环境模拟。

* **启动命令：**

  ```bash
  make up
  ```

  *(或使用 `docker compose up --build -d`)*

* **停止并清理环境：**

  ```bash
  make down
  ```

  *(或使用 `docker compose down -v`)*

* **可用服务：**

  | 服务     | 地址                                             |
  | ------ | ---------------------------------------------- |
  | API 网关 | [http://localhost:8080](http://localhost:8080) |
  | 管理门户   | [http://localhost:3000](http://localhost:3000) |
  | 工单适配器  | [http://localhost:8081](http://localhost:8081) |

<br>

#### ⚙️ 模式 B：混合开发模式 (Hybrid Development) — 适用于 Python 调试

仅在 Docker 中运行依赖服务（数据库、消息系统等），
而 Python API 服务器在本地直接运行，以实现热重载与快速调试。

1. **终端 1：启动依赖服务**

   ```bash
   make up-deps
   ```

   *(或 `docker compose up -d db mysql redis nats ticket-adapter`)*

2. **终端 2：本地运行 API 服务器**

   ```bash
   make run-local
   ```

   *(或 `python -m uvicorn src.gateway.main:app --host 0.0.0.0 --port 8080 --reload --app-dir src`)*

<br>

### 🧪 3. 测试 (How to Test)

`Makefile` 提供统一的测试命令：

| 命令                | 功能                        |
| ----------------- | ------------------------- |
| `make test-all`   | 运行全部测试（Python、Java、Admin） |
| `make test`       | 仅运行 Python 测试             |
| `make test-java`  | 仅运行 Java 测试               |
| `make test-admin` | 仅运行前端 (Next.js) 测试        |

> 💡 测试框架：pytest、JUnit、Vitest

<br>

### 🗄️ 4. 数据库与 RAG 操作 (Working with the Database and RAG)

**初始化数据库（启用 pgvector 扩展）**

```bash
make migrate
```

*(若使用 `docker-compose.deps.yml` 启动依赖，则无需此步骤)*

**填充 RAG 知识库**

1. 将 `.md` 或 `.txt` 文件放入 `docs/` 目录；
2. 执行：

   ```bash
   make ingest
   ```

系统会自动解析文档并将嵌入向量存储至 PostgreSQL + pgvector。

<br>

### 🤖 5. 验证代理功能 (How to Verify Agents Work)

启动应用后，可使用 `curl` 命令测试代理接口。

> ⚠️ 测试前可暂时禁用 `auth_guard`（在 `main.py` 中），以简化本地验证。

* **测试创建工单 (create_ticket)**：

  ```bash
  curl -X POST http://localhost:8080/v1/agents/run \
    -H "Content-Type: application/json" \
    -d '{"agent": "support", "input": "My internet is down, please create a ticket."}'
  ```

* **测试获取监控指标 (get_metrics)**：

  ```bash
  curl -X POST http://localhost:8080/v1/agents/run \
    -H "Content-Type: application/json" \
    -d '{"agent": "ops", "input": "Show me metrics for the webapp service"}'
  ```

* **测试知识问答 (RAG)**：

  ```bash
  curl -X POST http://localhost:8080/v1/agents/run \
    -H "Content-Type: application/json" \
    -d '{"agent": "support", "input": "How can I reset my password?"}'
  ```

<br>

### ❓ 6. 常见问题 (FAQ — Common Issues and Questions)

**Q1: 启动应用时报 “Connection refused”？**
A：可能是依赖容器未完全启动。
请确保 `docker ps` 中 `db`、`mysql`、`redis` 状态为 `(healthy)` 后再运行 Python 服务。

<br>

**Q2: 出现 `{"detail":"Missing Authorization Bearer header."}`？**
A：这是认证守卫 (auth_guard) 启用导致。
本地测试时可暂时注释掉：

```python
claims: dict[str, Any] = Depends(auth_guard),
```

并将 `claims` 参数传入空字典 `{}`。

<br>

**Q3: 如何查看特定服务日志？**
A：使用 `docker logs` 命令，例如：

```bash
docker logs -f astradesk-auditor-1
```

*(容器名可通过 `docker ps` 查看)*

<br>

**Q4: 如何仅重建一个镜像？**
A：

```bash
docker compose up -d --build api
```

<br>

**Q5: 如何修改关键词规划器 (KeywordPlanner)？**
A：编辑 `src/runtime/planner.py` 中的 `KeywordPlanner` 构造函数 (`__init__`)。

<br>

🧠 **提示 (Tips)**

* 使用 `.env` 管理本地配置；
* 每次修改依赖或配置后执行 `make sync`；
* 推荐在 VSCode 或 PyCharm 中启用自动格式化与类型检查。

<br>

---

## 🧪 测试 (Testing)

AstraDesk 提供统-的测试与覆盖率体系，包括单元测试、集成测试和端到端验证。

### 运行命令

```bash
make test          # 运行 Python 测试
make test-java     # 运行 Java 测试
make test-admin    # 运行前端测试
make test-all      # 全部测试
````

### 覆盖范围

* **单元测试**：pytest (Python)、JUnit (Java)、Vitest (Next.js)
* **集成测试**：验证 API 工作流、RAG 查询与工具交互
* **回归测试**：确保升级或修改后系统功能稳定

🧠 **建议**
在 CI/CD 流水线中集成测试阶段 (`test`) 以防止破坏性变更。

<br>

## 🔒 安全 (Security)

AstraDesk 在设计时遵循零信任与最小权限原则。

### 认证 (Auth)

* 基于 **OIDC / JWT** 的统一身份认证；
* 通过 JWKS 自动校验签名；
* 支持 Auth0、Keycloak、AWS Cognito 等提供方。

### 授权 (RBAC)

* 每个工具定义所需角色；
* 由 JWT 中的 `roles` 字段决定权限；
* 无角色或权限不足时将返回 HTTP 403。

### 传输安全 (mTLS)

* 在 Istio 服务网格中启用 **双向 TLS (STRICT 模式)**；
* 所有内部通信均加密；
* 外部流量通过 Gateway 控制。

### 审计与策略 (Audit & Policies)

* 所有代理操作均被记录至 Postgres 与 NATS；
* 工具层内置白名单、重试与熔断机制；
* 提供 `runtime/policy.py` 用于自定义安全规则。

<br>

## 🗺️ 路线图 (Roadmap)

AstraDesk 的未来版本将持续扩展企业级智能代理生态。

**计划特性：**

* 🤖 集成多种 LLM（Bedrock / OpenAI / vLLM）并支持 Guardrails；
* ⏱️ 使用 Temporal 实现长任务工作流；
* 🧠 引入 RAG 评估工具（Ragas）；
* 🏢 支持多租户架构与高级 RBAC (OPA)；
* 📈 完善 Grafana 仪表盘与告警模板；
* 🔄 支持向量数据库 (pgvector / Weaviate / Milvus)。

<br>

## 🤝 贡献指南 (Contributing)

欢迎开发者参与 AstraDesk 的持续改进。

### 步骤

1. Fork 本仓库；
2. 创建功能分支；
3. 提交变更并编写测试；
4. 发起 Pull Request。

### 提交前检查

* 执行以下命令确保代码规范：

  ```bash
  make lint/type
  ```

* 所有提交需通过 Lint 与类型检查；

* PR 中应附带测试用例与文档更新。


📜 **开发规范**

* Python 遵循 PEP8；

* Java 遵循 Google Java Style；

* 前端遵循 ESLint + Prettier 标准。

<br>

---

## 📄 许可证 (License)

本项目基于 **Apache License 2.0** 开源。

详细内容请参阅 [LICENSE](LICENSE)。

<br>

---

## 📬 联系方式 (Contact)

🌐 官网: [AstraDesk](https://astradesk.vercel.app/)

👨‍💻 作者: **Siergej Sobolewski**

📧 邮箱: `s.sobolewski@hotmail.com`

💬 支持频道: [Support Slack](https://astradesk.slack.com)  

🐙 问题与反馈: [GitHub Issues](https://github.com/SSobol77/astradesk/issues)

<br>

---

📅 **文档日期：2025 年 10 月 10 日**

<br>