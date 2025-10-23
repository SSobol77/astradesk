# SPDX-License-Identifier: Apache-2.0
# packages/domain-ops/tests/test_ops_agent.py
# SPDX-License-Identifier: Apache-2.0
"""Testy jednostkowe dla agenta operacyjnego (OpsAgent).

Ten moduł weryfikuje kluczowe zachowania i strategie `OpsAgent`,
zapewniając, że jego logika jest zgodna z założeniami projektowymi,
takimi jak priorytetyzacja akcji i celowe unikanie RAG.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from packages.domain_ops.agents.ops import OpsAgent
from services.api_gateway.src.runtime import (
    KeywordPlanner,
    Memory,
    RAG,
    ToolRegistry,
)


@pytest.fixture
def mock_dependencies() -> dict[str, AsyncMock]:
    """Tworzy zestaw mockowanych zależności dla agenta."""
    return {
        "tools": AsyncMock(spec=ToolRegistry),
        "memory": AsyncMock(spec=Memory),
        "planner": AsyncMock(spec=KeywordPlanner),
        "rag": AsyncMock(spec=RAG),
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_results",
    [
        pytest.param(["some tool result"], id="with_tool_results"),
        pytest.param([], id="without_tool_results"),
    ],
)
async def test_ops_agent_strategy_never_uses_rag(
    mock_dependencies: dict[str, AsyncMock], tool_results: list[str]
) -> None:
    """
    Weryfikuje, czy strategia OpsAgent nigdy nie wywołuje RAG.

    Sprawdza, czy metoda `_get_contextual_info` zawsze zwraca pustą listę
    i nigdy nie próbuje odpytać modułu RAG, niezależnie od tego, czy
    narzędzia zwróciły jakieś wyniki, czy nie.
    """
    # Given: Inicjalizujemy agenta z mockowanymi zależnościami
    agent = OpsAgent(**mock_dependencies)

    # When: Wywołujemy metodę strategii z różnymi danymi wejściowymi
    context = await agent._get_contextual_info("test query", tool_results=tool_results)

    # Then: Sprawdzamy, czy RAG nie został nigdy wywołany i czy wynik jest poprawny
    mock_dependencies["rag"].retrieve.assert_not_called()
    assert context == []
