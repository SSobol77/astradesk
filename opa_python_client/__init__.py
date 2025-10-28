"""
Minimal stub for the opa_python_client package.
"""

from __future__ import annotations

from typing import Any, Dict


class OPAClient:
    def __init__(self, url: str = "http://localhost:8181"):
        self.url = url

    async def check_policy(self, input: Dict[str, Any], policy_path: str) -> Dict[str, Any]:
        return {"result": True}


__all__ = ["OPAClient"]
