from __future__ import annotations

import sys
from pathlib import Path

import pytest

from respx import MockRouter
from types import ModuleType


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_tests_pkg = ModuleType("tests")
_tests_pkg.__path__ = [
    str(ROOT / "packages/domain-finance/tests"),
    str(ROOT / "packages/domain-supply/tests"),
    str(ROOT / "packages/domain-support/tests"),
]
sys.modules.setdefault("tests", _tests_pkg)


@pytest.fixture
def respx_mock() -> MockRouter:
    with MockRouter() as router:
        yield router
