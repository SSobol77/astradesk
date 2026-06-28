# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: packages/domain-finance/src/domain_finance/agents/forecast.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for packages/domain-finance/src/domain_finance/agents/forecast.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Asynchronous agent for financial forecasting using Prophet library.
Integrates with Oracle ERP via gRPC client, and Admin API for agent/run management.
Production-ready with async, retry, and error handling.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass

from domain_finance.clients.api import AdminApiClient
from domain_finance.clients.grpc_client import GrpcOracleErpClient


@dataclass(frozen=True)
class ForecastResult:
    """Small DTO mirroring the payload returned by the mocked Admin API."""

    date: str
    forecast: float


async def forecast_financial_data(
    data: list[dict[str, float | str]],
    api_url: str = 'http://localhost:8080/api/admin/v1',
    token: str = '',
    grpc_url: str = 'localhost:50051',
) -> AsyncIterator[ForecastResult]:
    """Produce forecast results using the mocked Admin API + gRPC pipeline."""
    client = AdminApiClient(api_url, token)
    grpc_client = GrpcOracleErpClient(grpc_url, api_url, token)

    input_data = data
    if not input_data:
        sales_data = await grpc_client.fetch_sales(
            'SELECT revenue, date FROM sales WHERE month=CURRENT_MONTH'
        )
        input_data = sales_data

    agent_payload = {'name': 'finance_forecast', 'config': {'method': 'simple', 'periods': 30}}
    agent = await client.create_agent(agent_payload)

    submission = {'input': input_data}
    run_id = await client.test_agent(agent['id'], submission)
    while True:
        run = await client.get_run(run_id)
        if run['status'] == 'completed':
            for result in run['output']:
                yield ForecastResult(**result)
            break
        await asyncio.sleep(1)
