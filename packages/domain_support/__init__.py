"""
Shim package mapping ``packages.domain_support`` to ``packages/domain-support``.
"""

from __future__ import annotations

from pathlib import Path

_IMPL_PATH = Path(__file__).resolve().parent.parent / "domain-support"
__path__ = [str(_IMPL_PATH)]
