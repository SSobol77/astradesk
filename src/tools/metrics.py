# src/tools/metrics.py
"""Narzędzie do pobierania metryk z systemu monitoringu Prometheus.

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
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any, Coroutine, Dict, Final, List, Tuple

import httpx

logger = logging.getLogger(__name__)

# --- Konfiguracja ---
MONITORING_API_URL: Final[str] = os.getenv("MONITORING_API_URL", "http://prometheus:9090")
ALLOWED_SERVICES: Final[set[str]] = {"webapp", "payments-api", "search-service", "database"}
WINDOW_PATTERN: Final[re.Pattern] = re.compile(r"^\d+[smhd]$")


def _parse_prometheus_response(data: Dict[str, Any]) -> float | None:
    """Bezpiecznie parsuje odpowiedź z Prometheusa i zwraca pojedynczą wartość metryki.

    Args:
        data: Słownik reprezentujący odpowiedź JSON z API Prometheusa.

    Returns:
        Wartość metryki jako float, lub None, jeśli metryka nie jest dostępna.
    """
    try:
        result = data["data"]["result"]
        if not result:
            return None
        # Zwracamy wartość z pierwszego wektora w wyniku
        return float(result[0]["value"][1])
    except (KeyError, IndexError, ValueError, TypeError):
        logger.warning(f"Nie udało się sparsować odpowiedzi z Prometheusa: {data}")
        return None


async def _query_prometheus(
    client: httpx.AsyncClient, query: str, metric_name: str
) -> Tuple[str, float | None]:
    """Wykonuje pojedyncze zapytanie do API Prometheusa."""
    try:
        response = await client.get("/api/v1/query", params={"query": query})
        response.raise_for_status()
        value = _parse_prometheus_response(response.json())
        return metric_name, value
    except httpx.HTTPStatusError as e:
        logger.error(
            f"Błąd HTTP {e.response.status_code} podczas zapytania o metrykę '{metric_name}': "
            f"{e.response.text}"
        )
        return metric_name, None
    except Exception as e:
        logger.error(
            f"Nieoczekiwany błąd podczas zapytania o metrykę '{metric_name}': {e}",
            exc_info=True,
        )
        return metric_name, None


async def get_metrics(service: str, window: str = "15m") -> str:
    """Pobiera i formatuje kluczowe metryki dla danej usługi i okna czasowego.

    Łączy się z API Prometheusa, wykonuje współbieżnie zapytania o użycie CPU,
    pamięci oraz latencję p95, a następnie formatuje wyniki w czytelny sposób.

    Args:
        service: Nazwa usługi, dla której mają być pobrane metryki.
        window: Okno czasowe w formacie Prometheus (np. '5m', '1h').

    Returns:
        Sformatowany string z metrykami lub komunikat o błędzie.
    """
    if service not in ALLOWED_SERVICES:
        logger.warning(f"Otrzymano żądanie metryk dla nieautoryzowanej usługi: '{service}'")
        return f"Błąd: Usługa '{service}' nie znajduje się na liście dozwolonych."

    if not WINDOW_PATTERN.fullmatch(window):
        logger.warning(f"Otrzymano żądanie z nieprawidłowym formatem okna czasowego: '{window}'")
        return f"Błąd: Format okna czasowego '{window}' jest nieprawidłowy. Użyj np. '5m', '1h'."

    logger.info(f"Pobieranie metryk dla usługi '{service}' w oknie '{window}'...")

    # Definicje zapytań PromQL (dostosuj nazwy metryk do swojego środowiska)
    queries = {
        "cpu_usage": f'avg(rate(container_cpu_usage_seconds_total{{pod=~"{service}-.*"}}[{window}])) * 100',
        "memory_usage": f'avg(container_memory_usage_bytes{{pod=~"{service}-.*"}}) / 1024 / 1024',  # w MB
        "p95_latency": f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{job="{service}"}}[{window}])) by (le)) * 1000', # w ms
    }

    try:
        async with httpx.AsyncClient(base_url=MONITORING_API_URL, timeout=15.0) as client:
            # Wykonaj wszystkie zapytania współbieżnie
            tasks: List[Coroutine] = [
                _query_prometheus(client, query, name) for name, query in queries.items()
            ]
            results = await asyncio.gather(*tasks)
            
            metrics = dict(results)

        # Formatowanie wyniku
        cpu = f"{metrics['cpu_usage']:.2f}%" if metrics.get("cpu_usage") is not None else "N/A"
        memory = f"{metrics['memory_usage']:.2f} MB" if metrics.get("memory_usage") is not None else "N/A"
        latency = f"{metrics['p95_latency']:.2f} ms" if metrics.get("p95_latency") is not None else "N/A"

        return (
            f"Metryki dla usługi '{service}' (okno {window}):\n"
            f"- Średnie użycie CPU: {cpu}\n"
            f"- Średnie użycie Pamięci: {memory}\n"
            f"- Latencja p95: {latency}"
        )

    except httpx.TimeoutException:
        logger.error(f"Timeout podczas komunikacji z API Prometheusa pod adresem: {MONITORING_API_URL}")
        return "Błąd: Przekroczono czas oczekiwania na odpowiedź z systemu monitoringu."
    except Exception as e:
        logger.critical(f"Nieoczekiwany błąd podczas pobierania metryk dla '{service}': {e}", exc_info=True)
        return "Błąd: Wystąpił nieoczekiwany wewnętrzny błąd podczas pobierania metryk."
