![AstraDesk](../assets/astradesk-logo.svg)

# 7. Monitor & Operate - AstraOps, SLOs, RCA

> Operations for agentic systems must answer two questions:
> 1) **Is it up?** (infra health)  
> 2) **Is it right?** (quality/safety/cost).
>
> This chapter wires **AstraOps**: telemetry (MELT), SLOs, alerting, runbooks, and RCA.

<br>

---

## 7.1 Observability Model (MELT)

- **Metrics**: p95 latency, tool-call success, token cost/task, queue depth.

- **Events/Traces**: plan → tool calls → approvals → compose → answer.

- **Logs**: structured JSON, correlation IDs (gateway↔agent↔tool).

- **Telemetry IDs**: `x-astradesk-trace-id`, `x-astradesk-tool-span-id`.

<br>

```mermaid
flowchart TB
  E[Events + Traces] --> P[OTel Collector]
  L[JSON Logs] --> P
  M[App Metrics] --> P
  P --> PR[Prometheus]
  P --> LS[LogStore - Loki/CloudWatch]
  PR --> GF[Grafana Dashboards]
  LS --> GF
````

<br>

<br>

---

## 7.2 SLOs & KPI Contract (AstraOps)

<br>

### 7.2.1 SLOs (SupportAgent defaults)

| SLO              |  Target | Window | Note               |
| ---------------- | ------: | -----: | ------------------ |
| **Latency p95**  |    ≤ 8s |     7d | end-to-end         |
| **Tool success** |   ≥ 95% |     7d | schema-valid + 2xx |
| **Containment**  |   ≥ 60% |    30d | no human handoff   |
| **Groundedness** |  ≥ 0.80 |     7d | judge/heuristic    |
| **Cost / task**  | ≤ $0.03 |     7d | tokens + tools     |

<br>

### 7.2.2 KPI Contract Loader (example)

```python
# file: ops/kpi_loader.py
import json, os
from pathlib import Path

def load_kpi_contract(path="configs/kpi.support.json"):
    contract = json.loads(Path(path).read_text(encoding="utf-8"))
    # publish to metrics or a config topic for dashboards
    print("[ops] loaded KPI contract:", contract["kpi_contract"])
    return contract
```

<br>

---

## 7.3 Telemetry Wiring (OpenTelemetry)

<br>

### 7.3.1 Collector (OTLP → Prometheus / Loki)

```yaml
# file: ops/otel-collector.yaml
receivers:
  otlp:
    protocols:
      http:
      grpc:

processors:
  batch:
  attributes:
    actions:
      - key: service.name
        action: upsert
        value: "astradesk-support-agent"

exporters:
  prometheus:
    endpoint: "0.0.0.0:9464"
  loki:
    endpoint: http://loki:3100/loki/api/v1/push
  debug:

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch, attributes]
      exporters: [debug]
    metrics:
      receivers: [otlp]
      processors: [batch, attributes]
      exporters: [prometheus]
    logs:
      receivers: [otlp]
      processors: [batch, attributes]
      exporters: [loki]
```

<br>

### 7.3.2 Agent Metrics Emission (Python)

```python
# file: telemetry/metrics.py
from typing import Dict
from time import time
import random

class Metrics:
    def __init__(self, emit=lambda m,v,**kw: print("[metric]", m, v, kw)):
        self.emit = emit

    def observe_latency(self, ms: float, label: str = "end_to_end"):
        self.emit("astradesk_latency_ms", ms, label=label)

    def observe_cost(self, usd: float):
        self.emit("astradesk_cost_usd", usd)

    def tool_success(self, name: str, ok: bool):
        self.emit("astradesk_tool_success", 1 if ok else 0, tool=name)

metrics = Metrics()
```

<br>

---

## 7.4 Dashboards (Grafana)

<br>

### 7.4.1 Starter Dashboard (JSON snippet)

```json
{
  "title": "AstraDesk - SupportAgent SLOs",
  "panels": [
    { "type": "graph", "title": "Latency p95 (s)",
      "targets": [{ "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job=\"astradesk\"}[5m])) by (le))" }]
    },
    { "type": "stat", "title": "Tool Success (%)",
      "targets": [{ "expr": "100*avg_over_time(astradesk_tool_success[1h])" }]
    },
    { "type": "stat", "title": "Cost per task ($)",
      "targets": [{ "expr": "avg_over_time(astradesk_cost_usd[1h])" }]
    }
  ],
  "schemaVersion": 39
}
```

<br>

---

## 7.5 Alerting (Prometheus Alertmanager)

<br>

### 7.5.1 Alert Rules

```yaml
# file: ops/alerts.rules.yaml
groups:
- name: astra-slos
  rules:
  - alert: AstraLatencyP95High
    expr: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job="astradesk"}[5m])) by (le)) > 8
    for: 10m
    labels: { severity: page }
    annotations:
      summary: "Latency p95 > 8s"
      description: "Investigate model/gateway/tool latency. Trace ID in logs."
  - alert: AstraToolSuccessDrop
    expr: avg_over_time(astradesk_tool_success[30m]) < 0.95
    for: 15m
    labels: { severity: page }
    annotations:
      summary: "Tool success < 95%"
      description: "Schema changes? MCP outage? Check Gateway audit."
  - alert: AstraCostPerTaskSpike
    expr: avg_over_time(astradesk_cost_usd[30m]) > 0.03
    for: 30m
    labels: { severity: warn }
    annotations:
      summary: "Cost per task above target"
      description: "Review routing/caching and prompt length."
```

<br>

### 7.5.2 Alertmanager Routes

```yaml
# file: ops/alertmanager.yaml
route:
  receiver: "ops-team"
  group_by: ["alertname"]
  routes:
    - matchers: [ severity = "page" ]
      receiver: "oncall-pager"
receivers:
  - name: "ops-team"
    slack_configs:
      - channel: "#agent-ops"
        send_resolved: true
  - name: "oncall-pager"
    pagerduty_configs:
      - routing_key: "${PAGERDUTY_KEY}"
```

<br>

---

## 7.6 Runbooks (RCA-ready)

<br>

### 7.6.1 Elevated Latency

1. **Triage**: Grafana panel → span sampling in OTel → identify bottleneck (Gateway vs Tool vs Model).

2. **Mitigation**:

   * Enable response caching at Gateway.

   * Lower `top_k` for retrieval; shrink prompt context.

   * Route planner to cheaper/faster model tier.

3. **Follow-up**: open incident in **AstraCatalog**; add canary eval to catch regression.

<br>

### 7.6.2 Tool Success Drop

1. Check Gateway audit for failing tool names/arguments.

2. Diff tool **schemas** (Catalog) vs agent call; rollback tool/server if mismatch.

3. If provider outage → switch to fallback MCP or degrade gracefully.

<br>

### 7.6.3 Cost Spike

1. Inspect token logs (LLM Gateway) - prompt bloat or unexpected retries.

2. Enable token-caching; add truncation guard.

3. Route long-tail traffic to efficient model.

<br>

---

## 7.7 Incident Response & RCA

```yaml
# file: ops/rca_template.yaml
incident:
  id: "INC-YYYYMMDD-001"
  summary: "Latency p95 crossed 8s for 30m"
  severity: "SEV-2"
  owner: "agent.ops@company.com"
  timeline:
    - "T0: Alert fired"
    - "T+5m: Identified tool timeouts"
    - "T+12m: Switched to fallback MCP"
    - "T+30m: Latency normalized"
  contributing_factors:
    - "Provider X partial outage"
    - "No caching on tool Y"
  corrective_actions:
    - "Enable caching"
    - "Add synthetic probe"
    - "Update SLO dashboard"
```

<br>

---

## 7.8 Quality-in-Production (In-loop Evals)

Add **micro-gates** that run inside flows (cheap, deterministic).

```python
# file: agents/guards.py
def context_relevance_guard(retrieved_titles, user_input: str) -> bool:
    """Block compose step if retrieval is irrelevant."""
    low = user_input.lower()
    return any(t.lower().split()[0] in low for t in retrieved_titles[:3])

def approval_guard(side_effect: str, approved: bool) -> bool:
    return side_effect == "read" or approved is True
```

<br>

Wire into agent before compose:

```python
# pseudo
if not context_relevance_guard([m["title"] for m in matches], user_input):
    raise RuntimeError("Context relevance failed; request clarification")
```

<br>

---

## 7.9 Lightweight Anomaly Detection (Cost/Latency)

```python
# file: ops/anomaly.py
from collections import deque
def ewma_anomaly(stream, alpha=0.2, k=3.0):
    """
    Returns iterator of (value, is_outlier) using EWMA + k-sigma band.
    O(1) per point; perfect for agent telemetry streams.
    """
    mean, var = None, 0.0
    for x in stream:
        if mean is None:
            mean = x
            yield x, False
            continue
        prev = mean
        mean = alpha*x + (1-alpha)*mean
        var = alpha*(x - prev)**2 + (1-alpha)*var
        outlier = abs(x - mean) > k*(var**0.5 + 1e-6)
        yield x, outlier
```

<br>

---

## 7.10 Operate Checklist

* [ ] OTel collector deployed; spans/metrics/logs flowing.

* [ ] Grafana dashboard imported; SLO panels green.

* [ ] Prometheus rules + Alertmanager routes active (test fire).

* [ ] Runbooks stored in repo + linked in dashboards.

* [ ] KPI contract loaded; alerts reflect targets.

* [ ] Synthetic probes for critical tools (MCP) in place.

<br>

---

## 7.11 Cross-References

* Next: [8. Security & Governance](08_security_governance.md)

* Previous: [6. Deploy Phase](06_deploy_phase.md)

* See also: [5. Test & Optimize](05_test_optimize.md)

<br>
