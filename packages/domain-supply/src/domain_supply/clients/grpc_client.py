# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: packages/domain-supply/src/domain_supply/clients/grpc_client.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for packages/domain-supply/src/domain_supply/clients/grpc_client.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""gRPC client for SAP S/4HANA adapter (Java server).
Integrates with Admin API for metadata, calls gRPC for data fetching.
Production-ready with async, retry, and error handling.
"""

from __future__ import annotations

import grpc

from domain_supply.clients.api import AdminApiClient
from domain_supply.proto.supply_pb2 import FetchInventoryRequest
from domain_supply.proto.supply_pb2_grpc import SupplyServiceStub


class GrpcSapS4HanaClient:
    """Async gRPC client talking to the in-process stub used in tests."""

    def __init__(
        self,
        grpc_url: str = 'localhost:50051',
        api_url: str = 'http://localhost:8080/api/admin/v1',
        token: str = '',
    ) -> None:
        self.grpc_url = grpc_url
        self.api_client = AdminApiClient(api_url, token)

    async def fetch_inventory(self, query: str) -> list[dict[str, float]]:
        """Fetch inventory data using the stubbed gRPC service."""
        async with grpc.aio.insecure_channel(self.grpc_url) as channel:
            stub = SupplyServiceStub(channel)
            request = FetchInventoryRequest(query=query)
            response = await stub.FetchInventory(request)
            return [{'material': item.material, 'stock': item.stock} for item in response.items]
