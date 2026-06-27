"""
Hand-written protobuf shim for supply domain tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InventoryItem:
    material: str = ''
    stock: float = 0.0


@dataclass
class FetchInventoryRequest:
    query: str = ''


@dataclass
class FetchInventoryResponse:
    items: list[InventoryItem] = field(default_factory=list)


__all__ = ['InventoryItem', 'FetchInventoryRequest', 'FetchInventoryResponse']
