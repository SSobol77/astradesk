# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: core/src/astradesk_core/egress.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for core/src/astradesk_core/egress.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Fail-closed egress allow-list for model/tool/external sink targets.

Implements ``INV-PII-3``: egress targets (model providers, external tools,
sinks) are governed by an explicit allow-list; an unlisted target is denied.

The allow-list is keyed by **hostname** (case-insensitive). The default set
covers the framework's known production/internal targets. Operators extend it
through the ``ASTRADESK_EGRESS_ALLOWLIST`` environment variable (comma- or
whitespace-separated hostnames). The environment is read on each call so the
policy is deterministic and trivially overridable in tests.

Denials raise :class:`EgressDenied`, whose message contains only the target
host and the egress category — never the payload, token, or claims.
"""

from __future__ import annotations

import os
from typing import Final
from urllib.parse import urlsplit

ENV_ALLOWLIST: Final = 'ASTRADESK_EGRESS_ALLOWLIST'

# Named error code for observability/audit (see CLAUDE.md §3.3 ERR).
ERROR_CODE: Final = 'EGRESS_DENIED'

# Default allow-list: known AstraDesk model/tool/internal targets. Loopback is
# included so local/dev/CI stacks (vLLM, local KB) are not denied by default.
DEFAULT_ALLOWED_HOSTS: Final[frozenset[str]] = frozenset(
    {
        'localhost',
        '127.0.0.1',
        '::1',
        # Model providers
        'api.openai.com',
        # External tool APIs used by built-in tools
        'api.openweathermap.org',
        # Internal cluster services (Istio mTLS targets)
        'ticket-adapter.tickets.svc.cluster.local',
        'kb-service',
    }
)


class EgressDenied(Exception):
    """Raised when an egress target is not on the allow-list (fail-closed).

    The string form intentionally exposes only the offending host and the
    egress category, so the error itself cannot leak raw input or secrets.
    """

    def __init__(self, host: str, category: str) -> None:
        self.code = ERROR_CODE
        self.host = host
        self.category = category
        super().__init__(f'{ERROR_CODE}: egress to {host!r} denied for category {category!r}')


def _env_hosts() -> frozenset[str]:
    raw = os.getenv(ENV_ALLOWLIST, '')
    if not raw:
        return frozenset()
    parts = raw.replace(',', ' ').split()
    return frozenset(host.strip().lower() for host in parts if host.strip())


def allowed_hosts() -> frozenset[str]:
    """Return the effective allow-list (defaults ∪ environment additions)."""
    return DEFAULT_ALLOWED_HOSTS | _env_hosts()


def host_of(target: str) -> str:
    """Extract a lower-cased hostname from a URL or bare host string.

    Accepts full URLs (``https://api.openai.com/v1``), host:port pairs, and
    bare hostnames. Returns an empty string if no host can be determined —
    which the enforcement path treats as denied (fail-closed).
    """
    if not target:
        return ''
    candidate = target.strip()
    parsed = urlsplit(candidate if '//' in candidate else f'//{candidate}')
    host = parsed.hostname or ''
    return host.lower()


def is_allowed(target: str) -> bool:
    """Return whether ``target`` resolves to an allow-listed host."""
    host = host_of(target)
    if not host:
        return False
    return host in allowed_hosts()


def ensure_allowed(target: str, *, category: str = 'external') -> str:
    """Assert that ``target`` is allow-listed, returning its host on success.

    Raises :class:`EgressDenied` (fail-closed) when the target is unlisted or
    its host cannot be parsed. ``category`` is a coarse label (e.g. ``model``,
    ``tool``, ``sink``) used only for observability — it carries no payload.
    """
    host = host_of(target)
    if not host or host not in allowed_hosts():
        raise EgressDenied(host or target, category)
    return host
