# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: conftest.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for conftest.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

from __future__ import annotations

import sys
from collections.abc import Generator
from pathlib import Path
from types import ModuleType

import pytest

from respx import MockRouter

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_tests_pkg = ModuleType('tests')
_tests_pkg.__path__ = [
    str(ROOT / 'packages/domain-finance/tests'),
    str(ROOT / 'packages/domain-supply/tests'),
    str(ROOT / 'packages/domain-support/tests'),
]
sys.modules.setdefault('tests', _tests_pkg)


@pytest.fixture
def respx_mock() -> Generator[MockRouter, None, None]:
    with MockRouter() as router:
        yield router
