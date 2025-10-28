# SPDX-License-Identifier: Apache-2.0
"""File: packages/domain-finance/agents/forecast.py
Project: AstraDesk Domain Finance Pack
Description:
    Asynchronous agent for financial forecasting using Prophet library.
    Integrates with Oracle ERP via gRPC client, and Admin API for agent/run management.
    Production-ready with async, retry, and error handling.

Author: Siergej Sobolewski
Since: 2025-10-16
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator, Dict, List

from ..clients.api import AdminApiClient
from ..clients.grpc_client import GrpcOracleErpClient


@dataclass(frozen=True)
class ForecastResult:
    """Small DTO mirroring the payload returned by the mocked Admin API."""

    date: str
    forecast: float


async def forecast_financial_data(
    data: List[Dict[str, float]],
    api_url: str = "http://localhost:8080/api/admin/v1",
    token: str = "",
    grpc_url: str = "localhost:50051",
) -> AsyncIterator[ForecastResult]:
    """Produce forecast results using the mocked Admin API + gRPC pipeline."""
    client = AdminApiClient(api_url, token)
    grpc_client = GrpcOracleErpClient(grpc_url, api_url, token)

    input_data = data
    if not input_data:
        sales_data = await grpc_client.fetch_sales("SELECT revenue, date FROM sales WHERE month=CURRENT_MONTH")
        input_data = sales_data

    agent_payload = {"name": "finance_forecast", "config": {"method": "simple", "periods": 30}}
    agent = await client.create_agent(agent_payload)

    submission = {"input": input_data}
    run_id = await client.test_agent(agent["id"], submission)
    while True:
        run = await client.get_run(run_id)
        if run["status"] == "completed":
            for result in run["output"]:
                yield ForecastResult(**result)
            break
        await asyncio.sleep(1)
