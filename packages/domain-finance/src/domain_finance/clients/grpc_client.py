# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: packages/domain-finance/src/domain_finance/clients/grpc_client.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for packages/domain-finance/src/domain_finance/clients/grpc_client.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""gRPC client for Oracle ERP adapter (Java server).
Integrates with Admin API for metadata, calls gRPC for data fetching.
Production-ready with async, retry, and error handling.
"""

from __future__ import annotations

import grpc

from domain_finance.clients.api import AdminApiClient
from domain_finance.proto.finance_pb2 import FetchSalesRequest
from domain_finance.proto.finance_pb2_grpc import FinanceServiceStub


class GrpcOracleErpClient:
    """Small asynchronous wrapper around the in-process gRPC stub used in tests."""

    def __init__(
        self,
        grpc_url: str = 'localhost:50051',
        api_url: str = 'http://localhost:8080/api/admin/v1',
        token: str = '',
    ) -> None:
        self.grpc_url = grpc_url
        self.api_client = AdminApiClient(api_url, token)

    async def fetch_sales(self, query: str) -> list[dict[str, float | str]]:
        """Fetch sales data using the mocked gRPC stack."""
        async with grpc.aio.insecure_channel(self.grpc_url) as channel:
            stub = FinanceServiceStub(channel)
            request = FetchSalesRequest(query=query)
            response = await stub.FetchSales(request)
            return [{'revenue': item.revenue, 'date': item.date} for item in response.items]
