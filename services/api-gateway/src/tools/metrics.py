# SPDX-License-Identifier: Apache-2.0
""" File: src/tools/metrics.py

Narzędzie do pobierania metryk z systemu monitoringu Prometheus.

Ten moduł dostarcza w pełni funkcjonalną implementację do odpytywania
API Prometheusa w celu uzyskania kluczowych metryk wydajnościowych dla
określonych usług.

Główne cechy:
- Rzeczywista Integracja: Wykonuje asynchroniczne zapytania HTTP do API
  Prometheusa w celu pobrania metryk CPU, pamięci i latencji.
- Współbieżność: Wszystkie zapytania PromQL są wykonywane równocześnie
  dzięki `asyncio.gather`, co minimalizuje czas oczekiwania.
- Odporność na błędy: Kompleksowa obsługa błędów sieciowych, timeoutów
  i błędów HTTP, z czytelnymi komunikatami zwrotnymi.
- Bezpieczeństwo i Walidacja: Parametry wejściowe (`service`, `window`) są
  walidowane względem predefiniowanych list, aby zapobiec nieautoryzowanym
  lub błędnym zapytaniom.
- Inteligentne Parsowanie: Bezpiecznie przetwarza odpowiedzi z Prometheusa,
  obsługując przypadki braku danych.

tools.metrics — narzędzie 'metrics' z realnym Prometheusem (gdy MONITORING_API_URL ustawione)
i kontrolowaną symulacją w trybie dev. Zachowujemy wsteczną zgodność aliasem get_metrics().
"""

from __future__ import annotations
import os
import re
import asyncio
import logging
from typing import Final, Optional

import httpx

logger = logging.getLogger(__name__)

MONITORING_API_URL: Final[str] = os.getenv("MONITORING_API_URL", "").rstrip("/")
ALLOWED_SERVICES: Final[set[str]] = {"webapp", "payments-api", "search-service", "database"}
WINDOW_RE: Final[re.Pattern] = re.compile(r"^\d+[smhd]$")


async def _prom_query(client: httpx.AsyncClient, query: str) -> Optional[float]:
    try:
        r = await client.get("/api/v1/query", params={"query": query})
        r.raise_for_status()
        data = r.json()
        res = data.get("data", {}).get("result", [])
        if not res:
            return None
        return float(res[0]["value"][1])
    except Exception as e:
        logger.warning("Prometheus query failed: %s", e)
        return None


async def metrics(service: str, window: str = "15m") -> str:
    """Zwraca czytelne metryki dla usługi jako tekst (Prometheus → fallback: symulacja)."""
    if service not in ALLOWED_SERVICES:
        return f"❌ Błąd: Usługa '{service}' nie jest dozwolona. Dozwolone: {', '.join(sorted(ALLOWED_SERVICES))}."
    if not WINDOW_RE.fullmatch(window):
        return "❌ Błąd: Nieprawidłowe okno czasowe (użyj np. 5m, 15m, 1h)."

    # Symulacja, gdy brak Prometheusa
    if not MONITORING_API_URL:
        return (
            f"Symulowane metryki '{service}' ({window}):\n"
            f"- CPU: 25%\n- Pamięć: 640 MB\n- p95: 150 ms"
        )

    queries = {
        "cpu": f'avg(rate(container_cpu_usage_seconds_total{{pod=~"{service}-.*"}}[{window}])) * 100',
        "mem": f'avg(container_memory_usage_bytes{{pod=~"{service}-.*"}}) / 1024 / 1024',
        "p95": f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{job="{service}"}}[{window}])) by (le)) * 1000',
    }

    try:
        async with httpx.AsyncClient(base_url=MONITORING_API_URL, timeout=15.0) as client:
            cpu_f = _prom_query(client, queries["cpu"])
            mem_f = _prom_query(client, queries["mem"])
            p95_f = _prom_query(client, queries["p95"])
            cpu, mem, p95 = await asyncio.gather(cpu_f, mem_f, p95_f)

        lines = [f"Metryki '{service}' (okno {window}):"]
        lines.append(f"- Średnie użycie CPU: {cpu:.2f}%" if cpu is not None else "- Średnie użycie CPU: N/A")
        lines.append(f"- Średnie użycie Pamięci: {mem:.2f} MB" if mem is not None else "- Średnie użycie Pamięci: N/A")
        lines.append(f"- Latencja p95: {p95:.2f} ms" if p95 is not None else "- Latencja p95: N/A")
        return "\n".join(lines)
    except httpx.TimeoutException:
        return "❌ Błąd: timeout podczas łączenia z Prometheusem."
    except Exception as e:
        logger.exception("metrics: krytyczny błąd: %s", e)
        return "❌ Błąd: nieoczekiwany problem podczas pobierania metryk."


# --- WSTECZNA ZGODNOŚĆ: alias dla starego importu ---
async def get_metrics(service: str, window: str = "15m") -> str:
    """Alias dla zgodności: import get_metrics → metrics."""
    return await metrics(service, window)
