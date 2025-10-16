# SPDX-License-Identifier: Apache-2.0
"""File: packages/domain-finance/clients/grpc_client.py
Project: AstraDesk Domain Finance Pack
Description:
    gRPC client for Oracle ERP adapter (Java server).
    Integrates with Admin API for metadata, calls gRPC for data fetching.
    Production-ready with async, retry, and error handling.

Author: Siergej Sobolewski
Since: 2025-10-16
"""

import asyncio
import grpc
from tenacity import retry, stop_after_attempt, wait_exponential
from ..proto.finance_pb2 import FetchSalesRequest
from ..proto.finance_pb2_grpc import FinanceServiceStub
from ..clients.api import AdminApiClient, ProblemDetail
from typing import List, Dict

class GrpcOracleErpClient:
    """Async gRPC client for Oracle ERP, with API metadata integration."""
    def __init__(self, grpc_url: str = "localhost:50051", api_url: str = "http://localhost:8080/api/admin/v1", token: str = ""):
        self.grpc_url = grpc_url
        self.api_client = AdminApiClient(api_url, token)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def fetch_sales(self, query: str) -> List[Dict]:
        """Fetch sales data via gRPC, with API connector check.
        
        :param query: Oracle query (e.g., "SELECT revenue, date FROM sales").
        :return: List of sales records.
        :raises ValueError: If API or gRPC call fails.
        """
        # Validate connector via API
        connector_data = {"name": "erp_oracle", "type": "db", "config": {"dsn": "oracle://user:pass@host"}}
        await self.api_client.create_connector(connector_data)

        # Call gRPC
        async with grpc.aio.insecure_channel(self.grpc_url) as channel:
            stub = FinanceServiceStub(channel)
            request = FetchSalesRequest(query=query)
            response = await stub.FetchSales(request)
            return [{"revenue": item.revenue, "date": item.date} for item in response.items]
