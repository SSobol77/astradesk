"""
Shim package mapping ``services.api_gateway`` to ``services/api-gateway``.
"""

from __future__ import annotations

from pathlib import Path

_IMPL_PATH = Path(__file__).resolve().parent.parent / "api-gateway"
__path__ = [str(_IMPL_PATH)]
