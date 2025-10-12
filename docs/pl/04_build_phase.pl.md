![AstraDesk](../assets/astradesk-logo.svg)

# 4. Faza Budowania - Prompty, Pamięć, Orkiestracja, MCP

> Cel tej fazy: stworzyć działający, zinstrumentowany **SupportAgent** z narzędziami MCP, bezpiecznymi domyślnymi ustawieniami i punktami zaczepienia testów.  
> Rezultat: kod źródłowy agenta, schematy narzędzi, pakiet promptów, konfiguracja i okablowanie obserwowalności.

<br>

---

## 4.1 Układ Repozytorium (sugerowany)

```text
astradesk/
├─ agents/
│  ├─ support_agent.py
│  └─ __init__.py
├─ mcp/
│  ├─ clients.py           # prawdziwe klienty MCP
│  ├─ schemas/             # Schematy JSON dla narzędzi
│  │  ├─ jira.create_issue.schema.json
│  │  └─ kb.search.schema.json
│  └─ stubs.py             # lokalne zastępniki dla dev
├─ configs/
│  ├─ agent.support.yaml   # konfiguracja runtime
│  ├─ prompts.support.md   # pakiet promptów
│  └─ pii_scrub.yaml       # zasady czyszczenia na wejściu
├─ telemetry/
│  ├─ otel_exporter.py
│  └─ __init__.py
├─ tests/
│  └─ test_eval_support.py
└─ run_support_agent.py
```

<br>

---

## 4.2 Pakiet Promptów (v1.0, bezpieczne domyślne)

<br>

```markdown
<!-- plik: configs/prompts.support.md -->
# System
Jesteś SupportAgent. MUSISZ przestrzegać polityk, schematów narzędzi i przepływu zatwierdzeń.
- Nigdy nie eksfiltruj sekretów ani PII.
- Używaj narzędzi tylko w ramach zadeklarowanych efektów ubocznych.
- Preferuj READ nad WRITE; żądaj zatwierdzenia dla WRITE.

# Developer
Cel zadania: rozwiązywać intencje Tier-1 (autentykacja/logowanie/hasło) używając wyszukiwania w KB.
Jeśli pewność wyszukiwania < 0.75 → zadaj pytanie wyjaśniające przed działaniem.
Jeśli użytkownik prosi o utworzenie zgłoszenia → zaproponuj podsumowanie, następnie poproś o zatwierdzenie.

# User (szablon)
{{user_input}}
```

<br>

---

## 4.3 Schematy Narzędzi (MCP JSON Schema)

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

## 4.4 SupportAgent (Python 3.13.5) - pełny kod z komentarzami

<br>

```python
# plik: agents/support_agent.py
# Runtime: Python 3.13.5
# Opis: Referencyjny SupportAgent implementujący planowanie, wykonywanie narzędzi (MCP),
#       pamięć i punkty zaczepienia telemetrii. Minimalny i audytowalny dla v1.0.

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Tuple
import time, uuid, json
from pathlib import Path

# --- Typy --------------------------------------------------------------

@dataclass
class ToolCall:
    """Deklaratywne wywołanie narzędzia z jawną klasą side_effect."""
    name: str
    args: Dict[str, Any]
    side_effect: str = "read"  # jedno z: read|write|execute

    def to_audit(self) -> Dict[str, Any]:
        return {"name": self.name, "args": self.args, "side_effect": self.side_effect}

@dataclass
class TraceStep:
    """Pojedynczy krok span telemetrii do śledzenia przepływów agentowych."""
    id: str
    kind: str                    # plan|tool_call|compose
    input: Dict[str, Any]
    output: Dict[str, Any]
    ts: float

# --- Agent --------------------------------------------------------------

@dataclass
class SupportAgent:
    """Minimalny agent v1.0 z prostym planerem i rejestrem narzędzi MCP."""
    id: str = field(default_factory=lambda: f"supportagent-{uuid.uuid4()}")
    memory: Dict[str, Any] = field(default_factory=dict)      # krótkoterminowa, TTL zarządzane przez wywołującego
    traces: List[TraceStep] = field(default_factory=list)
    tool_registry: Dict[str, Callable[..., Dict[str, Any]]] = field(default_factory=dict)
    tool_schemas: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    approval_callback: Optional[Callable[[ToolCall], bool]] = None  # wstrzyknięty mechanizm zatwierdzania

    # --- Planowanie -------------------------------------------------------
    def plan(self, user_input: str) -> List[ToolCall]:
        """
        Bardzo prosty heurystyczny planer (zamień na planer LLM jeśli potrzeba).
        - Jeśli użytkownik prosi o 'create ticket' → zaproponuj jira.create_issue (WRITE).
        - W przeciwnym razie → wykonaj kb.search (READ).
        """
        low = user_input.lower()
        if "create ticket" in low or "new ticket" in low or "open ticket" in low:
            summary = user_input[:180]
            return [ToolCall("jira.create_issue", {"project": "SUP", "summary": summary}, side_effect="write")]
        return [ToolCall("kb.search", {"q": user_input, "top_k": 5}, side_effect="read")]

    # --- Walidacja -----------------------------------------------------
    def _validate_args(self, name: str, args: Dict[str, Any]) -> None:
        """
        Waliduj args względem snapshota JSON Schema załadowanego przy starcie (szybka ścieżka).
        Dla v1.0 wykonujemy minimalne sprawdzenia typu/pól (pełna walidacja JSON Schema może być dodana).
        """
        schema = self.tool_schemas.get(name)
        if not schema:
            return
        req = set(schema.get("required", []))
        if not req.issubset(args.keys()):
            missing = list(req - set(args.keys()))
            raise ValueError(f"Brakujące wymagane pola dla {name}: {missing}")
        # Proste wymuszanie 'additionalProperties: false'
        if schema.get("additionalProperties") is False:
            allowed = set(schema.get("properties", {}).keys())
            extra = set(args.keys()) - allowed
            if extra:
                raise ValueError(f"Nieznane pola dla {name}: {list(extra)}")

    # --- Wykonanie ------------------------------------------------------
    def _run_tool(self, call: ToolCall) -> Dict[str, Any]:
        tool = self.tool_registry.get(call.name)
        if not tool:
            raise RuntimeError(f"Narzędzie nie znalezione: {call.name}")
        self._validate_args(call.name, call.args)

        # Zatwierdzenie wymagane dla write/execute
        if call.side_effect in ("write", "execute"):
            if not self.approval_callback or not self.approval_callback(call):
                raise PermissionError(f"Zatwierdzenie wymagane dla {call.name} z side_effect={call.side_effect}")

        # Wywołaj narzędzie MCP
        res = tool(**call.args)
        return res

    # --- Orkiestracja --------------------------------------------------
    def handle(self, user_input: str) -> Dict[str, Any]:
        # PLANOWANIE
        plan = self.plan(user_input)
        self.traces.append(TraceStep(
            id=str(uuid.uuid4()), kind="plan", input={"user_input": user_input}, output={"plan": [c.to_audit() for c in plan]}, ts=time.time()
        ))

        outputs: List[Dict[str, Any]] = []
        for call in plan:
            # WYKONANIE
            out = self._run_tool(call)
            outputs.append({"tool": call.to_audit(), "result": out})
            self.traces.append(TraceStep(
                id=str(uuid.uuid4()), kind="tool_call", input=call.to_audit(), output=out, ts=time.time()
            ))

        # KOMPONOWANIE (dla zwięzłości konkatenujemy; w prod użyj sumaryzatora LLM)
        answer = {"steps": outputs}
        self.traces.append(TraceStep(
            id=str(uuid.uuid4()), kind="compose", input={"steps": len(outputs)}, output={"answer_len": len(json.dumps(answer))}, ts=time.time()
        ))
        return {"answer": answer, "trace_ids": [t.id for t in self.traces[-(len(outputs)+2):]]}

# --- Pomocnicze ------------------------------------------------------------

def load_schema(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def make_default_agent(repo_root: Path) -> SupportAgent:
    """Fabryka okablowująca schematy i zastępcze narzędzia dla lokalnego dev."""
    # Załaduj schematy
    schemas = {
        "jira.create_issue": load_schema(repo_root / "mcp" / "schemas" / "jira.create_issue.schema.json"),
        "kb.search": load_schema(repo_root / "mcp" / "schemas" / "kb.search.schema.json"),
    }

    # Narzędzia (zastępniki dla dev)
    from mcp.stubs import jira_create_issue, kb_search

    agent = SupportAgent(
        tool_registry={
            "jira.create_issue": lambda project, summary, labels=None: jira_create_issue(project, summary),
            "kb.search": lambda q, top_k=5: kb_search(q),
        },
        tool_schemas=schemas,
        approval_callback=lambda call: True  # w dev auto-zatwierdzamy; prod musi wstrzyknąć prawdziwe zatwierdzanie
    )
    return agent
```

<br>

---

## 4.5 Klienty MCP (zastępniki dla dev; zamień na prawdziwe serwery)

```python
# plik: mcp/stubs.py
# Lokalne zastępniki bez sieci z deterministycznymi odpowiedziami.
from typing import Dict, Any, List

def jira_create_issue(project: str, summary: str, labels: list[str] | None = None) -> Dict[str, Any]:
    return {"ok": True, "issue_id": "SUP-1234", "project": project, "summary": summary, "labels": labels or []}

def kb_search(q: str, top_k: int = 5) -> Dict[str, Any]:
    docs = [
        {"doc_id": "kb-1", "title": "Reset hasła", "score": 0.92},
        {"doc_id": "kb-2", "title": "Rozwiązywanie problemów z 2FA", "score": 0.88},
    ]
    return {"matches": docs[:top_k], "query": q}
```

<br>

---

## 4.6 Telemetria (minimalne punkty zaczepienia OpenTelemetry)

```python
# plik: telemetry/otel_exporter.py
# Mała nakładka pokazująca granice span; podłącz do prawdziwego OTEL SDK w prod.
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

**Użycie wewnątrz agenta (przykład):**

```python
# wewnątrz SupportAgent.handle(...)
from telemetry.otel_exporter import span
with span("plan"):
    plan = self.plan(user_input)
with span("tool_calls"):
    for call in plan:
        out = self._run_tool(call)
```

<br>

---

## 4.7 Konfiguracja Runtime (YAML)

```yaml
# plik: configs/agent.support.yaml
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

## 4.8 Runner (lokalny dev)

```python
# plik: run_support_agent.py
from pathlib import Path
from agents.support_agent import make_default_agent

repo = Path(__file__).resolve().parent
agent = make_default_agent(repo)

print("== Scenariusz 1: Wyszukiwanie KB ==")
print(agent.handle("Jak zresetować moje hasło?"))

print("\n== Scenariusz 2: Utworzenie zgłoszenia ==")
print(agent.handle("Utwórz zgłoszenie: Użytkownik nie może się zalogować po resecie hasła"))
```

<br>

---

## 4.9 Walidacja w Czasie Budowania (szybkie sprawdzenia)

* **Sprawdzenie schematu**: upewnij się, że każde narzędzie w `tool_registry` ma pasujący schemat.

* **Mapa efektów ubocznych**: zadeklaruj efekt uboczny per narzędzie i upewnij się, że `write/execute` wymagają zatwierdzenia.

* **Lint promptów**: brak sekretów, brak identyfikatorów specyficznych dla środowiska.

<br>

```python
# plik: tests/test_schemas.py
from agents.support_agent import make_default_agent
from pathlib import Path

def test_registry_has_schemas():
    agent = make_default_agent(Path.cwd())
    for name in agent.tool_registry.keys():
        assert name in agent.tool_schemas, f"Brakujący schemat dla {name}"
```

<br>

---

## 4.10 Przepływ Budowanie-do-Wdrożenia (diagram)

<br>

```mermaid
flowchart LR
  Code[Agent i kod MCP] --> Lint[Lint/Sprawdzanie typów]
  Lint --> Unit[Testy jednostkowe/Eval]
  Unit --> Image[Budowa obrazu Docker]
  Image --> Scan[SBOM + Skanowanie]
  Scan --> Publish[Push do rejestru]
  Publish --> Deploy[Wdrożenie do K8s]
  Deploy --> Evals[Ewaluacje online + SLO]
```

<br>

<br>

---

## 4.11 Odniesienia Krzyżowe

* Dalej: [5. Testowanie i Optymalizacja](05_test_optimize.pl.md)

* Wstecz: [3. Faza Planowania](03_plan_phase.pl.md)

* Zobacz także: [8. Bezpieczeństwo i Governance](08_security_governance.pl.md)

<br>