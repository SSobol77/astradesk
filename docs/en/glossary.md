![AstraDesk](../assets/astradesk-logo.svg)


# Glossary

> Core terms used across AstraDesk Framework 1.0 documentation.

- **ADLC** - *Agent Development Lifecycle*: Plan → Build → Test/Optimize → Deploy → Monitor/Operate.

- **AstraOps** - Observability + Evaluations tooling and dashboards that answer *“Is it right?”*.

- **AstraCatalog** - Registry of agents, tools, prompts, datasets, risk posture, and certification artifacts.

- **Gateway** - The control plane entrypoint for MCP tools and LLM routing with OPA, quotas, and audit.

- **MCP** - *Model Context Protocol* for tools/resources/prompts discovered and invoked by agents.

- **OPA/Rego** - Policy-as-code engine and language used for side-effect gating and data egress rules.

- **Acceptable Agency** - Explicit authority limits for an agent; guards `read|write|execute` side effects.

- **Groundedness** - Degree to which an answer is supported by provided context/evidence.

- **Containment** - % of cases resolved without human handoff (business KPI).

- **SLO** - Service Level Objective (e.g., latency p95 ≤ 8s, tool success ≥ 95%).

- **Champion–Challenger** - Controlled promotion where a new version must outperform the current one on the same evals.

- **Schema Pinning** - Requiring a hash of the tool schema with every call; the Gateway rejects mismatches.

- **Shadow/Canary** - Running a challenger on mirrored traffic (shadow) or progressively shifting live traffic (canary).

- **Judge Kernel** - Pluggable rubric/model that scores helpfulness, safety, groundedness for in-loop gating.

- **AstraGraph Memory** - Planned hybrid vector + graph memory with temporal decay and provenance (v2.0).

<br>

---

## Cross-References

- See: [2. Architecture Overview](02_architecture_overview.md)  

- Also: [8. Security & Governance](08_security_governance.md), [5. Test & Optimize](05_test_optimize.md), [7. Monitor & Operate](07_monitor_operate.md)

<br>