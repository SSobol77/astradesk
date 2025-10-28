"""
Hand-written protobuf shim for supply domain tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class InventoryItem:
    material: str = ""
    stock: float = 0.0


@dataclass
class FetchInventoryRequest:
    query: str = ""


@dataclass
class FetchInventoryResponse:
    items: List[InventoryItem] = field(default_factory=list)


__all__ = ["InventoryItem", "FetchInventoryRequest", "FetchInventoryResponse"]
