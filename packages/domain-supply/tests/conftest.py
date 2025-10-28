from __future__ import annotations

import pytest

from respx import MockRouter


@pytest.fixture
def respx_mock() -> MockRouter:
    with MockRouter() as router:
        yield router
