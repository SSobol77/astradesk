"""
Shim package mapping ``packages.domain_ops`` to the source directory with a dash.
"""

from __future__ import annotations

from pathlib import Path

_IMPL_PATH = Path(__file__).resolve().parent.parent / "domain-ops"
__path__ = [str(_IMPL_PATH)]
