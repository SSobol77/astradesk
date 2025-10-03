# src/tools/metrics.py
from __future__ import annotations

async def get_metrics(service: str, window: str = "15m") -> str:
    # MVP: symulacja (w praktyce: Prometheus/Grafana API)
    return f"{service}({window}): cpu=22%, mem=57%, p95=120ms"
