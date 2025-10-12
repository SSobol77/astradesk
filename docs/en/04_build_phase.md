---
lang: en
---

![AstraDesk](../astradesk-logo.svg)

# 4. Build Phase — Prompts, Memory, Orchestration, MCP

> Goal of this phase: produce a working, instrumented **SupportAgent** with MCP tools, safe defaults, and test hooks.  
> Output: agent source code, tool schemas, prompt pack, config, and observability wiring.

<br>

---

## 4.1 Repository Layout (suggested)

```text
astradesk/
├─ agents/
│  ├─ support_agent.py
│  └─ __init__.py
├─ mcp/
│  ├─ clients.py           # real MCP clients
│  ├─ schemas/             # JSON Schemas for tools
│  │  ├─ jira.create_issue.schema.json
│  │  └─ kb.search.schema.json
│  └─ stubs.py             # local fallbacks for dev
├─ configs/
│  ├─ agent.support.yaml   # runtime config
│  ├─ prompts.support.md   # prompt pack
│  └─ pii_scrub.yaml       # ingress scrub rules
├─ telemetry/
│  ├─ otel_exporter.py
│  └─ __init__.py
├─ tests/
│  └─ test_eval_support.py
└─ run_support_agent.py
```

<br>

---

## 4.2 Prompt Pack (v1.0, safe defaults)

<br>

```markdown
<!-- file: configs/prompts.support.md -->
# System
You are SupportAgent. You MUST follow policies, tool schemas, and approval flow.
- Never exfiltrate secrets or PII.
- Use tools only within declared side effects.
- Prefer READ over WRITE; request approval for WRITE.

# Developer
Task objective: resolve Tier-1 intents (auth/login/password) using KB retrieval.
If retrieval confidence < 0.75 → ask a clarifying question before acting.
If the user asks to create a ticket → propose summary, then request approval.

# User (templated)
{{user_input}}
```

<br>

---

## 4.3 Tool Schemas (MCP JSON Schema)

<br>

```json
{
  "$id": "mcp/schemas/jira.create_issue.schema.json",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "jira.create_issue",
  "type": "object",
  "properties": {
    "project": { "type": "string", "minLength": 2 },
    "summary": { "type": "string", "minLength": 3 },
    "labels":  { "type": "array", "items": { "type": "string" }, "default": [] }
  },
  "required": ["project", "summary"],
  "additionalProperties": false
}
```

<br>

```json
{
  "$id": "mcp/schemas/kb.search.schema.json",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "kb.search",
  "type": "object",
  "properties": {
    "q": { "type": "string", "minLength": 2 },
    "top_k": { "type": "integer", "minimum": 1, "maximum": 20, "default": 5 }
  },
  "required": ["q"],
  "additionalProperties": false
}
```

<br>

---

## 4.4 SupportAgent (Python 3.13.5) — full code with comments

<br>

```python
# file: agents/support_agent.py
# Runtime: Python 3.13.5
# Description: Reference SupportAgent implementing planning, tool execution (MCP),
#              memory, and telemetry hooks. Minimal and auditable for v1.0.

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Tuple
import time, uuid, json
from pathlib import Path

# --- Types --------------------------------------------------------------

@dataclass
class ToolCall:
    """Declarative tool invocation with explicit side_effect class."""
    name: str
    args: Dict[str, Any]
    side_effect: str = "read"  # one of: read|write|execute

    def to_audit(self) -> Dict[str, Any]:
        return {"name": self.name, "args": self.args, "side_effect": self.side_effect}

@dataclass
class TraceStep:
    """A single telemetry span step for tracing agentic flows."""
    id: str
    kind: str                    # plan|tool_call|compose
    input: Dict[str, Any]
    output: Dict[str, Any]
    ts: float

# --- Agent --------------------------------------------------------------

@dataclass
class SupportAgent:
    """Minimal v1.0 agent with simple planner and MCP tool registry."""
    id: str = field(default_factory=lambda: f"supportagent-{uuid.uuid4()}")
    memory: Dict[str, Any] = field(default_factory=dict)      # short-term, TTL managed by caller
    traces: List[TraceStep] = field(default_factory=list)
    tool_registry: Dict[str, Callable[..., Dict[str, Any]]] = field(default_factory=dict)
    tool_schemas: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    approval_callback: Optional[Callable[[ToolCall], bool]] = None  # injected approval mechanism

    # --- Planning -------------------------------------------------------
    def plan(self, user_input: str) -> List[ToolCall]:
        """
        Very simple heuristic planner (replace with LLM planner if needed).
        - If user asks to 'create ticket' → propose jira.create_issue (WRITE).
        - Else → perform kb.search (READ).
        """
        low = user_input.lower()
        if "create ticket" in low or "new ticket" in low or "open ticket" in low:
            summary = user_input[:180]
            return [ToolCall("jira.create_issue", {"project": "SUP", "summary": summary}, side_effect="write")]
        return [ToolCall("kb.search", {"q": user_input, "top_k": 5}, side_effect="read")]

    # --- Validation -----------------------------------------------------
    def _validate_args(self, name: str, args: Dict[str, Any]) -> None:
        """
        Validate args against JSON Schema snapshot loaded at startup (fast path).
        For v1.0 we do minimal type/field checks (full JSON Schema validation can be added).
        """
        schema = self.tool_schemas.get(name)
        if not schema:
            return
        req = set(schema.get("required", []))
        if not req.issubset(args.keys()):
            missing = list(req - set(args.keys()))
            raise ValueError(f"Missing required fields for {name}: {missing}")
        # Simple 'additionalProperties: false' enforcement
        if schema.get("additionalProperties") is False:
            allowed = set(schema.get("properties", {}).keys())
            extra = set(args.keys()) - allowed
            if extra:
                raise ValueError(f"Unknown fields for {name}: {list(extra)}")

    # --- Execution ------------------------------------------------------
    def _run_tool(self, call: ToolCall) -> Dict[str, Any]:
        tool = self.tool_registry.get(call.name)
        if not tool:
            raise RuntimeError(f"Tool not found: {call.name}")
        self._validate_args(call.name, call.args)

        # Approval required for write/execute
        if call.side_effect in ("write", "execute"):
            if not self.approval_callback or not self.approval_callback(call):
                raise PermissionError(f"Approval required for {call.name} with side_effect={call.side_effect}")

        # Invoke MCP tool
        res = tool(**call.args)
        return res

    # --- Orchestration --------------------------------------------------
    def handle(self, user_input: str) -> Dict[str, Any]:
        # PLAN
        plan = self.plan(user_input)
        self.traces.append(TraceStep(
            id=str(uuid.uuid4()), kind="plan", input={"user_input": user_input}, output={"plan": [c.to_audit() for c in plan]}, ts=time.time()
        ))

        outputs: List[Dict[str, Any]] = []
        for call in plan:
            # EXECUTE
            out = self._run_tool(call)
            outputs.append({"tool": call.to_audit(), "result": out})
            self.traces.append(TraceStep(
                id=str(uuid.uuid4()), kind="tool_call", input=call.to_audit(), output=out, ts=time.time()
            ))

        # COMPOSE (for brevity, we concatenate; in prod use LLM summarizer)
        answer = {"steps": outputs}
        self.traces.append(TraceStep(
            id=str(uuid.uuid4()), kind="compose", input={"steps": len(outputs)}, output={"answer_len": len(json.dumps(answer))}, ts=time.time()
        ))
        return {"answer": answer, "trace_ids": [t.id for t in self.traces[-(len(outputs)+2):]]}

# --- Helpers ------------------------------------------------------------

def load_schema(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def make_default_agent(repo_root: Path) -> SupportAgent:
    """Factory wiring schemas and stub tools for local dev."""
    # Load schemas
    schemas = {
        "jira.create_issue": load_schema(repo_root / "mcp" / "schemas" / "jira.create_issue.schema.json"),
        "kb.search": load_schema(repo_root / "mcp" / "schemas" / "kb.search.schema.json"),
    }

    # Tools (stubs for dev)
    from mcp.stubs import jira_create_issue, kb_search

    agent = SupportAgent(
        tool_registry={
            "jira.create_issue": lambda project, summary, labels=None: jira_create_issue(project, summary),
            "kb.search": lambda q, top_k=5: kb_search(q),
        },
        tool_schemas=schemas,
        approval_callback=lambda call: True  # in dev we auto-approve; prod must inject real approval
    )
    return agent
```

<br>

---

## 4.5 MCP Clients (stubs for dev; replace with real servers)

```python
# file: mcp/stubs.py
# Local no-network stubs with deterministic responses.
from typing import Dict, Any, List

def jira_create_issue(project: str, summary: str, labels: list[str] | None = None) -> Dict[str, Any]:
    return {"ok": True, "issue_id": "SUP-1234", "project": project, "summary": summary, "labels": labels or []}

def kb_search(q: str, top_k: int = 5) -> Dict[str, Any]:
    docs = [
        {"doc_id": "kb-1", "title": "Reset password", "score": 0.92},
        {"doc_id": "kb-2", "title": "2FA troubleshooting", "score": 0.88},
    ]
    return {"matches": docs[:top_k], "query": q}
```

<br>

---

## 4.6 Telemetry (OpenTelemetry minimal hooks)

```python
# file: telemetry/otel_exporter.py
# Tiny wrapper to show span boundaries; plug into real OTEL SDK in prod.
from contextlib import contextmanager
import time
from typing import Iterator

@contextmanager
def span(name: str):
    t0 = time.time()
    try:
        yield
    finally:
        dur = (time.time() - t0) * 1000
        print(f"[trace] span={name} duration_ms={dur:.1f}")
```

<br>

**Usage inside agent (example):**

```python
# inside SupportAgent.handle(...)
from telemetry.otel_exporter import span
with span("plan"):
    plan = self.plan(user_input)
with span("tool_calls"):
    for call in plan:
        out = self._run_tool(call)
```

<br>

---

## 4.7 Runtime Config (YAML)

```yaml
# file: configs/agent.support.yaml
agent_id: support-agent
env: dev
memory:
  short_term_ttl_minutes: 60
approval:
  mode: auto              # dev=auto, prod=manual
  approver_group: support.leads
gateway:
  base_url: http://localhost:8080
  timeout_seconds: 12
tools:
  - name: kb.search
    side_effect: read
    rate_limit_per_min: 120
  - name: jira.create_issue
    side_effect: write
    rate_limit_per_min: 20
```

<br>

---

## 4.8 Runner (local dev)

```python
# file: run_support_agent.py
from pathlib import Path
from agents.support_agent import make_default_agent

repo = Path(__file__).resolve().parent
agent = make_default_agent(repo)

print("== Scenario 1: KB search ==")
print(agent.handle("How to reset my password?"))

print("\n== Scenario 2: Create ticket ==")
print(agent.handle("Create ticket: User cannot login after password reset"))
```

<br>

---

## 4.9 Build-Time Validation (fast checks)

* **Schema check**: ensure every tool in `tool_registry` has a matching schema.

* **Side-effect map**: declare side-effect per tool and assert `write/execute` require approval.

* **Prompt lint**: no secrets, no env-specific identifiers.

<br>

```python
# file: tests/test_schemas.py
from agents.support_agent import make_default_agent
from pathlib import Path

def test_registry_has_schemas():
    agent = make_default_agent(Path.cwd())
    for name in agent.tool_registry.keys():
        assert name in agent.tool_schemas, f"Missing schema for {name}"
```

<br>

---

## 4.10 Build-to-Deploy Flow (diagram)

<br>

```mermaid
flowchart LR
  Code[Agent & MCP code] --> Lint[Lint/Typecheck]
  Lint --> Unit[Unit/Eval tests]
  Unit --> Image[Build Docker Image]
  Image --> Scan[SBOM + Scan]
  Scan --> Publish[Push to Registry]
  Publish --> Deploy[Deploy to K8s]
  Deploy --> Evals[Online Evals + SLOs]
```

<br>

<br>

---

## 4.11 Cross-References

* Next: [5. Test & Optimize](05_test_optimize.md)

* Previous: [3. Plan Phase](03_plan_phase.md)

* See also: [8. Security & Governance](08_security_governance.md)

<br>