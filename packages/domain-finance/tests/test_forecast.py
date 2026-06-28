# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: packages/domain-finance/tests/test_forecast.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Verifies AstraDesk behavior for the associated component.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Production-level tests for financial forecast agent with gRPC integration.
Uses respx for API mocking and grpc.aio.testing for gRPC.
"""

import pytest
from domain_finance.agents.forecast import forecast_financial_data
from domain_finance.clients.grpc_client import GrpcOracleErpClient
from domain_finance.proto.finance_pb2 import FetchSalesResponse, SalesItem
from domain_finance.proto.finance_pb2_grpc import FinanceServiceStub

from respx import MockRouter


@pytest.mark.asyncio
async def test_forecast_success(respx_mock: MockRouter):
    """Test successful forecast with mocked API and gRPC."""
    respx_mock.post('/agents').respond(201, json={'id': 'fin1'})
    respx_mock.post('/agents/fin1:test').respond(200, json={'run_id': 'run_fin1'})
    respx_mock.get('/runs/run_fin1').respond(
        200, json={'status': 'completed', 'output': [{'date': '2025-11-01', 'forecast': 1500.0}]}
    )

    results = [
        res
        async for res in forecast_financial_data(
            [{'date': '2025-10-01', 'revenue': 1000.0}], api_url='http://mock', token='fake'
        )
    ]
    assert len(results) == 1
    assert results[0].forecast == 1500.0


@pytest.mark.asyncio
async def test_forecast_grpc_integration():
    """Test gRPC client with mocked server."""
    from domain_finance.proto.finance_pb2_grpc import add_FinanceServiceServicer_to_server
    from grpc.aio import server as aio_server

    class MockFinanceService(FinanceServiceStub):
        async def FetchSales(self, request, context):
            return FetchSalesResponse(items=[SalesItem(revenue=1000.0, date='2025-10-01')])

    server = aio_server()
    add_FinanceServiceServicer_to_server(MockFinanceService(), server)
    server.add_insecure_port('[::]:50051')
    await server.start()

    client = GrpcOracleErpClient('localhost:50051', 'http://mock', 'fake')
    sales = await client.fetch_sales('SELECT revenue, date FROM sales')
    assert len(sales) == 1
    assert sales[0]['revenue'] == 1000.0
    assert sales[0]['date'] == '2025-10-01'

    await server.stop(None)
