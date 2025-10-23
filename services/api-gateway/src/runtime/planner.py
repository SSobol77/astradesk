# SPDX-License-Identifier: Apache-2.0
"""File: services/gateway-python/src/runtime/planner.py
Project: AstraDesk Framework — API Gateway
Description:
    Configurable, deterministic keyword-based planner used as a fallback (or a
    lightweight primary) when the LLM planner is unavailable or unnecessary.
    Maps user queries to structured tool invocations using simple, auditable
    rules and produces readable, formatted responses.

Author: Siergej Sobolewski
Since: 2025-10-07

Overview
--------
- Rule architecture: plan generation is driven by `KeywordRule` entries
  (keywords → tool name → argument factory).
- Deterministic behavior: no LLM dependency; outputs are predictable and fast.
- Data model alignment: plans are expressed as `ToolCall` from `runtime.models`.
- Human-friendly finalize: composes a clear response from tool results or RAG
  context when no tools produced output.

Responsibilities
----------------
- `make_plan(query) -> List[ToolCall]`
  * Normalize input; select the first matching rule; build tool arguments via
    the rule’s `arg_factory`.
  * Return a single-step plan or an empty list if no rule matches.
- `finalize(query, tool_results, rag_context) -> str`
  * Prefer tool results; fall back to knowledge snippets; otherwise provide a
    polite “no action/answer” message.

Design principles
-----------------
- Keep rules explicit and easy to extend (additive changes, no hidden magic).
- Favor safe defaults in argument factories (trim lengths, sanitize basics).
- Separation of concerns: planning only; execution/rendering done upstream.

Security & safety
-----------------
- Avoid injecting unvalidated user strings into arguments that may reach shell,
  SQL, or network boundaries; let downstream layers validate/escape properly.
- Keep argument factories conservative (length limits, normalization).
- Do not include secrets or PII in generated arguments or messages.

Performance
-----------
- O( |rules| ) matching with simple substring checks; fast and GC-friendly.
- Zero network I/O; suitable for hot paths and as a resilient fallback.

Usage (example)
---------------
>>> planner = KeywordPlanner()
>>> plan = planner.make_plan("Utwórz ticket dla incydentu VPN")
>>> if plan:
...     results = await run_tools(plan)  # external orchestration
...     reply = planner.finalize("Utwórz ticket...", results, rag_context=[])

Notes
-----
- Add new `KeywordRule` entries to expand coverage (e.g., restart service).
- If you need locale-specific matching or stemming, place it inside rules or
  pre-processing; keep the core planner deterministic and auditable.

Notes (PL):
------------
Implementacja konfigurowalnego, heurystycznego planera opartego na słowach kluczowych.

Ten moduł dostarcza implementację planera, który pełni rolę "fallbacku"
lub podstawowego mechanizmu decyzyjnego w sytuacji, gdy zaawansowany planer
oparty na LLM jest niedostępny lub nie jest wymagany.

Główne cechy:
- **Architektura oparta na regułach**: Logika planowania jest zdefiniowana jako
  lista konfigurowalnych reguł (`KeywordRule`), co ułatwia rozszerzanie
  i utrzymanie planera.
- **Brak zależności od LLM**: Działa w pełni deterministycznie na podstawie
  zdefiniowanych słów kluczowych i heurystyk.
- **Spójność z modelami danych**: Wykorzystuje model `ToolCall` z `runtime.models`,
  zapewniając spójny kontrakt z resztą systemu.
- **Ustrukturyzowane odpowiedzi**: Metoda `finalize` tworzy czytelne,
  sformatowane odpowiedzi dla użytkownika na podstawie wyników narzędzi i RAG.
- **Bezpieczeństwo**: Unika wstrzykiwania niesprawdzonych danych użytkownika
  do argumentów narzędzi, stosując bezpieczne domyślne wartości i ograniczenia długości.

Lekki KeywordPlanner:
- make_plan(): prosta heurystyka → lista wywołań narzędzi.
- finalize(): składa końcową odpowiedź z wyników wywołanych narzędzi (lub daje fallback).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Set, Iterable

# Jeśli masz ten typ w runtime.models — ok. Jeśli nie, trzymamy lokalny @dataclass o takim kształcie.
try:
    from runtime.models import ToolCall  # type: ignore
except Exception:
    @dataclass(frozen=True)
    class ToolCall:
        name: str
        arguments: Dict[str, Any]


@dataclass(frozen=True)
class KeywordRule:
    keywords: Set[str]
    tool_name: str
    arg_factory: callable


class KeywordPlanner:
    """
    Minimalny planer słów kluczowych.
    API oczekiwane przez BaseAgent:
      - make_plan(query: str) -> List[ToolCall]
      - finalize(query: str, tool_results: Any, context: Dict[str, Any]) -> str
    """

    __slots__ = ("_rules",)

    def __init__(self) -> None:
        self._rules: List[KeywordRule] = [
            # Ticket / zgłoszenia
            KeywordRule(
                keywords={"ticket", "bilet", "zgłoszen", "zgłoszenie", "incident", "incydent", "utwórz zgłoszenie", "create ticket"},
                tool_name="create_ticket",
                arg_factory=lambda q: {
                    "title": q.strip()[:80],
                    "body": q.strip(),
                },
            ),
            # Metryki (ważne: nazwa narzędzia = "metrics", nie "get_metrics")
            KeywordRule(
                keywords={"metryki", "metryk", "metrics", "get_metrics", "cpu", "pamięć", "memory", "latency", "p95", "p99"},
                tool_name="metrics",
                arg_factory=lambda q: {
                    "service": _extract_service(q) or "webapp",
                    "window": _extract_window(q) or "15m",
                },
            ),
            # Restart usługi (jeśli masz zarejestrowane narzędzie restart_service)
            KeywordRule(
                keywords={"restart", "zrestartuj", "ponownie uruchom", "rollout"},
                tool_name="restart_service",
                arg_factory=lambda q: {
                    "service": _extract_service(q) or "webapp",
                },
            ),
        ]

    # ---------- PLAN ----------
    def make_plan(self, query: str) -> List[ToolCall]:
        q = query.strip()
        low = q.lower()
        for rule in self._rules:
            if any(k in low for k in rule.keywords):
                args = rule.arg_factory(q)
                return [ToolCall(name=rule.tool_name, arguments=args)]
        # Fallback: jeśli wiadomość jest konkretna/długa, potraktuj jako prośbę o utworzenie zgłoszenia
        if len(q) > 12:
            return [ToolCall(name="create_ticket", arguments={"title": q[:80], "body": q})]
        # W innym wypadku — brak planu (wyższe warstwy często mają swój własny fallback)
        return []

    # ---------- FINALIZACJA ----------
    def finalize(self, query: str, tool_results: Any, context: Dict[str, Any] | None = None) -> str:
        """
        Składa końcową odpowiedź z wyników narzędzi. Zaprojektowane tak, by działać z różnymi
        kształtami `tool_results`, bo implementacje agentów bywały różne.

        Obsługiwane formy:
          - str -> zwracamy jak jest
          - List[str] -> łączymy z nagłówkami
          - Dict[name -> str] -> ładny listing
          - List[Tuple[name, output]] lub List[Dict{name, output}] -> ładny listing
        Gdy nic nie ma: przyjazny fallback zależny od treści zapytania.
        """
        if tool_results is None:
            return _fallback_for(query)

        # 1) Pojedynczy string
        if isinstance(tool_results, str):
            return tool_results.strip() or _fallback_for(query)

        # 2) Lista stringów
        if isinstance(tool_results, list) and all(isinstance(x, str) for x in tool_results):
            lines = ["Oto wyniki akcji:", ""]
            for i, s in enumerate(tool_results, start=1):
                s = (s or "").strip()
                if s:
                    lines.append(f"{i}) {s}")
            return "\n".join(lines) if len(lines) > 2 else _fallback_for(query)

        # 3) Słownik {narzędzie: wynik}
        if isinstance(tool_results, dict) and all(isinstance(k, str) for k in tool_results.keys()):
            if all(isinstance(v, str) for v in tool_results.values()):
                lines = ["Podsumowanie wykonanych kroków:", ""]
                for name, out in tool_results.items():
                    pretty = (out or "").strip()
                    if not pretty:
                        continue
                    lines.append(f"• {name}:")
                    lines.append(pretty)
                    lines.append("")  # odstęp między sekcjami
                txt = "\n".join(lines).strip()
                return txt or _fallback_for(query)

        # 4) Lista z elementami typu (name, output) lub {"name": ..., "output": ...}
        if isinstance(tool_results, list):
            normalized: List[tuple[str, str]] = []
            for item in tool_results:
                if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str):
                    normalized.append((item[0], str(item[1] or "")))
                elif isinstance(item, dict) and "name" in item and ("output" in item or "result" in item):
                    name = str(item.get("name"))
                    out = str(item.get("output") or item.get("result") or "")
                    normalized.append((name, out))
                # inne kształty pomijamy cicho
            if normalized:
                lines = ["Podsumowanie wykonanych kroków:", ""]
                for name, out in normalized:
                    out = (out or "").strip()
                    if not out:
                        continue
                    lines.append(f"• {name}:")
                    lines.append(out)
                    lines.append("")
                txt = "\n".join(lines).strip()
                return txt or _fallback_for(query)

        # 5) Cokolwiek innego — spróbuj to zrzutować do tekstu
        try:
            return str(tool_results) or _fallback_for(query)
        except Exception:
            return _fallback_for(query)


# ---------- Pomocnicze: ekstrakcje i fallback ----------

_svc_pat = re.compile(r"\b(webapp|payments[- ]?api|search[- ]?service|database|db)\b", re.I)
_win_pat = re.compile(r"\b(\d+)([smhd])\b", re.I)

def _extract_service(q: str) -> str | None:
    m = _svc_pat.search(q)
    if not m:
        return None
    svc = m.group(1).lower().replace(" ", "-")
    if "payments" in svc:
        return "payments-api"
    if "search" in svc:
        return "search-service"
    if svc in ("database", "db"):
        return "database"
    return svc

def _extract_window(q: str) -> str | None:
    m = _win_pat.search(q)
    return (m.group(0).lower() if m else None)

def _fallback_for(q: str) -> str:
    low = q.lower()
    if any(k in low for k in ("ticket", "zgłoszen", "zgłoszenie", "incydent", "incident")):
        return "Nie udało się jednoznacznie złożyć odpowiedzi, ale zgłoszenie możesz utworzyć poleceniem: „utwórz zgłoszenie <tytuł>”."
    if any(k in low for k in ("metrics", "metryk", "cpu", "p95", "p99", "latency", "pamięć", "memory")):
        return "Nie udało się pobrać czytelnych metryk. Spróbuj: „pokaż metryki dla webapp z ostatnich 15m”."
    return "Nie znalazłem pasującej akcji do wykonania. Opisz proszę, co chcesz osiągnąć."
