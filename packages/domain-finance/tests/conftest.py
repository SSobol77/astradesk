from __future__ import annotations

import pytest

from respx import MockRouter


@pytest.fixture
def respx_mock() -> MockRouter:
    """Provide a respx.MockRouter compatible fixture."""
    with MockRouter() as router:
        yield router
