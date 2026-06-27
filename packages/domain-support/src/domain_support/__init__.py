"""Support domain pack discovery contract."""

from __future__ import annotations


class Pack:
    """Discovery adapter for the standalone support MCP server."""

    name = 'domain_support'

    def register(self, registry: object) -> None:
        """Preserve discovery without bypassing the MCP policy boundary."""
        if registry is None:
            raise TypeError('registry must not be None')
