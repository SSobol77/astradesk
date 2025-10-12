![AstraDesk](../assets/astradesk-logo.svg)

# 2. Architecture Overview

> AstraDesk separates **control** (Gateway, Catalog, Policy) from **execution** (Agents + Tools) and **evidence** (AstraOps).  
> Version: Framework 1.0 (single-agent focus with human-in-the-loop).

## 2.1 Goals & Non-Goals (v1.0)

- **Goals**  
  - Secure, observable single-agent runtime (SupportAgent/OpsAgent).  
  - **MCP-first** integrations via AstraDesk Gateway (authZ, OPA, rate limits, audit).  
  - Telemetry & evaluations through **AstraOps** (traces, metrics, offline/online evals).  
  - **AstraCatalog** for ownership, risk posture, versions, certification artifacts.

- **Non-Goals**  
  - Multi-agent swarm orchestration (planned in v2.0).  
  - Self-modifying prompts in production without approval gates.  
  - Unbounded tool authority (all tools require explicit scope & side-effect class).

<br>

---

## 2.2 High-Level System Diagram

```mermaid
%%{
  init: {
    "theme": "base",
    "themeVariables": {
      "background": "#FFFFFF",
      "lineColor": "#111827",
      "textColor": "#0f172a",
      "clusterBkg": "#FFFFFF",
      "clusterBorder": "#CBD5E1",
      "fontFamily": "Inter, ui-sans-serif, system-ui"
    }
  }
}%%
flowchart LR
  %% =============== SUBGRAPHS ===============
  subgraph Clients["Clients & Integrations"]
    U1[Web Admin]:::c
    U2[Slack/Chat UI]:::c
    U3[Service APIs]:::c
  end

  subgraph Gateway["AstraDesk Gateway"]
    GI[MCP Ingress<br/>OIDC · RBAC · OPA · Rate Limits · Audit]:::g
    GL[LLM Gateway<br/>Routing · Caching · Cost Metering]:::g
  end

  subgraph Runtime["Agents Runtime"]
    A1[SupportAgent]:::a
    A2[OpsAgent]:::a
  end

  subgraph Ops["AstraOps"]
    T1[Traces/Logs/Metrics]:::o
    E1["Evaluations<br/>offline / online / in-loop"]:::o
    D1[Dashboards/Alerts]:::o
  end

  subgraph Catalog["AstraCatalog"]
    R1[Registry<br/>Agents/Tools/Prompts]:::k
    P1[Policies & Risk Posture]:::k
    C1[Certification Artifacts]:::k
  end

  subgraph Data["Enterprise Data & Tools"]
    DB[(PostgreSQL 18)]:::d
    VDB[(Vector/Graph DB)]:::d
    OBJ[(Object Storage/S3)]:::d
    BUS[(NATS/Kafka)]:::d
    EXT[(External APIs via MCP)]:::d
  end

  %% =============== FLOWS ===============
  U1 --> GI
  U2 --> GI
  U3 --> GI

  GI --> A1
  GI --> A2
  GL --> A1

  A1 <--> T1
  A2 <--> T1
  A1 --> E1
  A2 --> E1
  T1 --> D1

  A1 --> DB
  A1 --> VDB
  A1 --> OBJ
  A1 --> BUS
  A1 --> EXT

  A2 --> DB
  A2 --> VDB
  A2 --> OBJ
  A2 --> BUS
  A2 --> EXT

  Ops --> Catalog
  Catalog --> GI

  %% Wzmocnij wszystkie krawędzie (widoczne na dark mode w zrzutach)
  linkStyle default stroke:#111827,stroke-width:2px,opacity:1;

  %% =============== STYLES ===============
  style Clients fill:#F1F5FF,stroke:#A5B4FC,stroke-width:1px,color:#0f172a
  style Gateway fill:#ECFDF5,stroke:#34D399,stroke-width:1px,color:#064E3B
  style Runtime fill:#F0FDF4,stroke:#86EFAC,stroke-width:1px,color:#14532D
  style Ops fill:#FFF7ED,stroke:#FDBA74,stroke-width:1px,color:#7C2D12
  style Catalog fill:#FDF4FF,stroke:#F0ABFC,stroke-width:1px,color:#4A044E
  style Data fill:#F8FAFC,stroke:#94A3B8,stroke-width:1px,color:#0f172a

  classDef c fill:#E3F2FD,stroke:#2962FF,stroke-width:2px,color:#0D47A1;
  classDef g fill:#E8F5E9,stroke:#16A34A,stroke-width:2px,color:#065F46;
  classDef a fill:#ECFEF3,stroke:#22C55E,stroke-width:2px,color:#065F46;
  classDef o fill:#FFF1E6,stroke:#FB923C,stroke-width:2px,color:#7C2D12;
  classDef k fill:#FAF5FF,stroke:#D946EF,stroke-width:2px,color:#4A044E;
  classDef d fill:#EFF6FF,stroke:#60A5FA,stroke-width:2px,color:#0C4A6E;

````

<br>

<br>

---

## 2.3 Component Responsibilities

<br>

### AstraDesk Gateway

- **Identity & Access**: OIDC/OAuth2 for agents & tools; per-tool RBAC with parameter allow-lists.

- **Policy Enforcement**: OPA/Rego guardrails; environment routing (dev/stage/prod).

- **Rate Limiting & Quotas**: per tenant/agent/tool; backpressure & circuit breakers.

- **Audit**: all MCP tool invocations signed with request/response digests.

<br>

### Agents Runtime (SupportAgent/OpsAgent)

- **Reasoning & Planning** (v1.0): deterministic planner + LLM option; explicit **acceptable agency** bounds.

- **Memory**: ephemeral task memory with TTL; optional vector/graph lookups (read-only by default).

- **Tooling**: MCP tools with declared side effects (`read|write|execute`) and schemas.

- **Human-in-the-loop**: approval checkpoints for `write/execute` actions.

<br>

### AstraOps

- **Traces** of agentic flows: prompt → plan → tool calls → side effects → answer.

- **Metrics**: p95 latency, tool-success, groundedness proxy, cost per task.

- **Evaluations**: CI/offline, production/online and **in-loop** gates (e.g., context relevance).

<br>

### AstraCatalog

- **Registry**: agents, tools, prompts, datasets, model routes.

- **Risk & Policies**: per agent version; change controls; kill-switch metadata.

- **Certification**: artifacts for go-live (eval results, red-team notes, SBOM pointers).

<br>

### Data & Tools

- **PostgreSQL 16→18**: system of record (read/write via governed tools).

- **Vector/Graph DB**: retrieval & relations; read-only in v1.0 by default.

- **Buses**: NATS/Kafka for events & async jobs; idempotent handlers.

- **External APIs**: only via registered MCP servers with scoped tokens.

<br>

---

## 2.4 Sequence: Request → Result (Happy Path)

<br>

```mermaid
%%{
  init: {
    'theme': 'base',
    'themeVariables': {
      'actorBkg': '#E3F2FD',
      'actorBorder': '#2962FF',
      'actorTextColor': '#0D47A1',
      'signalColor': '#AA00FF',
      'signalTextColor': '#737d8bff',
      'activationBkgColor': '#FFE082',
      'activationBorderColor': '#FFAB00',
      'background': '#FFFFFF'
    }
  }
}%%
sequenceDiagram
  participant C as Client
  participant GW as AstraDesk Gateway
  participant AG as Agent
  participant TS as MCP Tool Server
  participant OP as AstraOps

  rect rgba(41,98,255,0.08)
    C->>GW: Request (JWT, context)
    GW->>AG: Dispatch (scoped auth + policies)
  end

  AG->>AG: Plan (deterministic/LLM)

  rect rgba(170,0,255,0.08)
    AG->>GW: invoke(tool, args, side_effect)
    GW->>TS: Scoped call + OPA check
    TS-->>GW: Result
    GW-->>AG: Result + audit id
  end

  AG->>OP: Traces + Metrics
  AG-->>C: Final answer (explanation optional)
````

<br>

<br>

---

## 2.5 Deployment Views (Kubernetes/EKS)

<br>

```mermaid
%%{
  init: {
    "theme": "base",
    "themeVariables": {
      "background": "#FFFFFF",
      "lineColor": "#111827",
      "textColor": "#0f172a",
      "fontFamily": "Inter, ui-sans-serif, system-ui"
    },
    "flowchart": {
      "htmlLabels": true,
      "curve": "linear",
      "nodeSpacing": 90,
      "rankSpacing": 150
    }
  }
}%%
flowchart TB
  %% ================= SUBGRAPHS =================
  subgraph ControlPlane["Control Plane (Namespace:&nbsp;astra-control)"]
    GWD[Gateway Deployment]:::gateway
    CTG[Catalog API]:::api
    OPA[OPA / Policy Controller]:::policy
  end

  subgraph Agents["Workload (Namespace:&nbsp;astra-agents)"]
    SA[SupportAgent]:::agent
    OA[OpsAgent]:::agent
  end

  subgraph Telemetry["Observability (Namespace:&nbsp;astra-ops)"]
    OTEL[OpenTelemetry Collector]:::observ
    PRM[Prometheus]:::observ
    GRF[Grafana]:::observ
  end

  %% ================= FLOWS =================
  GWD --> SA
  GWD --> OA
  SA --> OTEL
  OA --> OTEL
  OTEL --> PRM --> GRF
  CTG --> GWD
  OPA --> GWD

  %% Wyraźne krawędzie (czytelne w dark mode)
  linkStyle default stroke:#111827,stroke-width:2px,opacity:1

  %% ================= STYLES =================
  style ControlPlane fill:#F0F9FF,stroke:#38BDF8,stroke-width:1px,color:#0C4A6E
  style Agents      fill:#ECFDF5,stroke:#34D399,stroke-width:1px,color:#064E3B
  style Telemetry   fill:#FEF3C7,stroke:#F59E0B,stroke-width:1px,color:#7C2D12

  classDef gateway fill:#DBEAFE,stroke:#2563EB,stroke-width:2px,color:#1E3A8A,rx:8,ry:8
  classDef api     fill:#EDE9FE,stroke:#7C3AED,stroke-width:2px,color:#4C1D95,rx:8,ry:8
  classDef policy  fill:#FFE4E6,stroke:#FB7185,stroke-width:2px,color:#881337,rx:8,ry:8
  classDef agent   fill:#DCFCE7,stroke:#22C55E,stroke-width:2px,color:#14532D,rx:8,ry:8
  classDef observ  fill:#FEF9C3,stroke:#EAB308,stroke-width:2px,color:#854D0E,rx:8,ry:8

````

<br>

---

## 2.6 Security Posture (v1.0)

* **Least Privilege** for each MCP tool; explicit side-effect class enforced at gateway.

* **Environment Isolation**: dev/stage/prod with separate credentials & policy bundles.

* **Supply Chain**: signed container images; SBOM attached; admission policies block unknown digests.

* **Data**: secrets in manager (KMS/ASM), PII filters at ingress, egress allow-lists.

<br>

---

## 2.7 Observability Model

* **Traces**: span per plan step and per tool call; correlation IDs across gateway/agent/tool.

* **Metrics**: SLOs (p95 latency), business KPIs (containment, resolution), safety KPIs (policy violations).

* **Dashboards**: operator and owner views; triage → RCA playbooks; alert fatigue control.

<br>

---

## 2.8 Extensibility & Roadmap Hooks

* **Multi-agent orchestration** via policy-aware router (v2.0).

* **AstraGraph Memory** with temporal decay and relation-aware retrieval (v2.0).

* **Cost-aware model routing** (p95 + price caps) at LLM Gateway.

<br>

---

## 2.9 Cross-References

* Next: [3. Plan Phase](03_plan_phase.md)

* Previous: [1. Introduction](01_introduction.md)

* See also: [8. Security & Governance](08_security_governance.md), [7. Monitor & Operate](07_monitor_operate.md)

<br>