"""
Shim package mapping ``packages.domain_supply`` to ``packages/domain-supply``.
"""

from __future__ import annotations

from pathlib import Path

_IMPL_PATH = Path(__file__).resolve().parent.parent / "domain-supply"
__path__ = [str(_IMPL_PATH)]
