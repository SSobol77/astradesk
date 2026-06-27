"""
Hand-written protobuf stub matching the tiny subset used in tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SalesItem:
    revenue: float = 0.0
    date: str = ''


@dataclass
class FetchSalesRequest:
    query: str = ''


@dataclass
class FetchSalesResponse:
    items: list[SalesItem] = field(default_factory=list)


__all__ = ['SalesItem', 'FetchSalesRequest', 'FetchSalesResponse']
