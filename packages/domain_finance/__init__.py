"""
Shim package providing import-time mapping from ``packages.domain_finance`` to the
hyphenated source directory ``packages/domain-finance``.
"""

from __future__ import annotations

from pathlib import Path

_IMPL_PATH = Path(__file__).resolve().parent.parent / "domain-finance"
__path__ = [str(_IMPL_PATH)]
