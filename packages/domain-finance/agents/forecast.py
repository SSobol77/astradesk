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

from typing import AsyncIterator, List, Dict
from prophet import Prophet
import asyncio
from pydantic import BaseModel
from ..clients.api import AdminApiClient, ProblemDetail
from ..clients.grpc_client import GrpcOracleErpClient

class ForecastResult(BaseModel):
    """Pydantic model for forecast result, aligned with OpenAPI Run schema."""
    date: str
    forecast: float

async def forecast_financial_data(data: List[Dict], api_url: str = "http://localhost:8080/api/admin/v1", token: str = "", grpc_url: str = "localhost:50051") -> AsyncIterator[ForecastResult]:
    """Generate financial forecast by fetching data via gRPC and calling Admin API.

    Steps:
    1. Fetch sales data from Oracle ERP via gRPC client.
    2. Create or get agent via POST /agents (if not exists).
    3. Test agent with input via POST /agents/{id}:test.
    4. Poll run results via GET /runs/{id} until completed.

    Uses local Prophet for computation, submits via API for compliance.

    :param data: List of financial data entries (e.g., [{"date": "2025-01-01", "revenue": 1000}]).
    :param api_url: Base URL for Admin API.
    :param token: JWT token for BearerAuth.
    :param grpc_url: gRPC server URL for Oracle ERP.
    :raises ValueError: If API or gRPC call fails.
    :yield: ForecastResult for each predicted point.
    """
    client = AdminApiClient(api_url, token)
    grpc_client = GrpcOracleErpClient(grpc_url, api_url, token)

    # Step 1: Fetch sales data via gRPC
    sales_data = await grpc_client.fetch_sales("SELECT revenue, date FROM sales WHERE month=CURRENT_MONTH")
    input_data = data if data else sales_data  # Use provided data or fetched

    # Step 2: Create or get agent via API
    agent_data = {"name": "finance_forecast", "config": {"method": "prophet", "periods": 30}}
    try:
        agent = await client.create_agent(agent_data)
    except ValueError as e:
        agents_resp = await client._client.get("/agents", params={"name": "finance_forecast"})
        if agents_resp.status_code == 200 and agents_resp.json():
            agent = agents_resp.json()[0]
        else:
            raise e

    # Step 3: Local Prophet computation
    model = Prophet()
    df = [{"ds": d["date"], "y": d["revenue"]} for d in input_data]
    model.fit(df)
    future = model.make_future_dataframe(periods=30)
    forecast = model.predict(future)
    input_data = {"forecast_data": forecast.to_dict("records")}

    # Step 4: Submit to API and poll results
    run_id = await client.test_agent(agent["id"], input_data)
    while True:
        run = await client.get_run(run_id)
        if run["status"] == "completed":
            for result in run["output"]:
                yield ForecastResult(**result)
            break
        await asyncio.sleep(1)
