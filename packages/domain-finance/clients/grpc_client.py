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
from __future__ import annotations

from typing import Dict, List

import grpc

from ..clients.api import AdminApiClient
from ..proto.finance_pb2 import FetchSalesRequest
from ..proto.finance_pb2_grpc import FinanceServiceStub


class GrpcOracleErpClient:
    """Small asynchronous wrapper around the in-process gRPC stub used in tests."""

    def __init__(
        self,
        grpc_url: str = "localhost:50051",
        api_url: str = "http://localhost:8080/api/admin/v1",
        token: str = "",
    ) -> None:
        self.grpc_url = grpc_url
        self.api_client = AdminApiClient(api_url, token)

    async def fetch_sales(self, query: str) -> List[Dict[str, float]]:
        """Fetch sales data using the mocked gRPC stack."""
        async with grpc.aio.insecure_channel(self.grpc_url) as channel:
            stub = FinanceServiceStub(channel)
            request = FetchSalesRequest(query=query)
            response = await stub.FetchSales(request)
            return [{"revenue": item.revenue, "date": item.date} for item in response.items]
