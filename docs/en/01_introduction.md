![AstraDesk](../assets/astradesk-logo.svg)

# 1. Introduction - The AstraDesk Vision

> AstraDesk Enterprise AI Framework v1.0 - Technical Guide (EN)

**AstraDesk** is a secure, modular framework for building **enterprise AI agents** that reason, plan, and act through tools.
It operationalizes *AgentOps* (observability + evaluation), *governance*, and *DevSecOps* specifically for agentic systems.

<br>

## Why AstraDesk now

- From deterministic code → probabilistic reasoning loops.

- From static workflows → adaptive, goal-driven agents.

- From code-first → **evaluation-first** (ship with evidence, not intuition).

<br>

## What’s inside v1.0

- Single-agent runtime (SupportAgent / OpsAgent) with human-in-the-loop.

- MCP-first integrations (tools/resources/prompts) via **AstraDesk Gateway**.

- **AstraOps** for traces, metrics, evals; **AstraCatalog** for ownership, risk, versions.

- Hybrid deployments: AWS/Kubernetes/OpenShift/on-prem; PostgreSQL 18; OpenTelemetry.

<br>

## Document map

> - 2. Architecture Overview → big picture
>
> - 3. (3.-7.) ADLC → plan, build, test/optimize, deploy, operate
>
> - 8. Security & Governance
>
> - 9. MCP Gateway & Domain Packs
>
> - 10. Future Roadmap and Glossary

<br>

<br>


## High-level architecture sketch (for context)

<br>

```mermaid

flowchart LR
  subgraph GW["AstraDesk Gateway"]
    G1[MCP Ingress]
    G2[LLM Gateway]
  end
  subgraph RT["Agents Runtime"]
    A1[SupportAgent]
    A2[OpsAgent]
  end
  subgraph OPS["AstraOps"]
    O1[Traces]
    O2[Evals]
  end
  subgraph CAT["AstraCatalog"]
    C1[Registry]
    C2[Policies]
  end
  subgraph DATA["Data/Tools"]
    D1[(PostgreSQL 18)]
    D2[(Vector/Graph DB)]
    D3[(External APIs)]
  end
  G1 --> A1
  G1 --> A2
  A1 <-->|signals| OPS
  A2 <-->|signals| OPS
  A1 --> DATA
  A2 --> DATA
  OPS --> CAT
  CAT --> G1

````

<br>


**Next:** [2. Architecture Overview](02_architecture_overview.md)