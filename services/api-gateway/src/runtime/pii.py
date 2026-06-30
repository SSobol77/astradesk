# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/src/runtime/pii.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for services/api-gateway/src/runtime/pii.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Ingress PII/secret classification and emitter-boundary redaction helpers.

This is the API Gateway-side façade over the shared
:mod:`astradesk_core.redaction` and :mod:`astradesk_core.egress` boundaries. It
adds two runtime concerns on top of the pure utilities:

1. **Classification propagation** (``INV-PII-2``): a request's data
   classification is attached at ingress via a :class:`~contextvars.ContextVar`
   and is readable by any downstream emitter on the same task.
2. **Emitter-boundary redaction** (``INV-PII-4``): :func:`set_safe_attribute`
   is the *only* sanctioned way to put request-derived values onto an OTel span.
   It redacts before the value can be set, so raw user text can never become a
   span attribute by call-site omission.

Re-exports the redaction primitives so call sites import a single module.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from astradesk_core.egress import EgressDenied, ensure_allowed, is_allowed
from astradesk_core.redaction import (
    REDACTION_FAILED,
    classify,
    is_sensitive,
    redact_mapping,
    redact_text,
    redact_value,
    safe_preview,
)

__all__ = [
    'EgressDenied',
    'REDACTION_FAILED',
    'attach_classification',
    'classify',
    'current_classification',
    'ensure_allowed',
    'is_allowed',
    'is_sensitive',
    'redact_mapping',
    'redact_text',
    'redact_value',
    'safe_preview',
    'set_safe_attribute',
]

# Per-request classification, propagated across the async task via contextvars.
_classification: ContextVar[frozenset[str]] = ContextVar(
    'astradesk_pii_classification', default=frozenset()
)


def attach_classification(text: str) -> frozenset[str]:
    """Classify ingress ``text`` and bind the result to the current context.

    Called once at the request boundary (orchestrator ingress). Returns the
    detected category set so the caller can also record a redacted summary.
    """
    categories = classify(text)
    _classification.set(categories)
    return categories


def current_classification() -> frozenset[str]:
    """Return the classification attached for the current request, if any."""
    return _classification.get()


def set_safe_attribute(span: Any, key: str, value: Any) -> None:
    """Set an OTel span attribute after redacting any request-derived text.

    This is the emitter-boundary choke point for span attributes
    (``INV-PII-4``). String values are redacted; numeric/boolean values pass
    through with their native type preserved. Failure to set an attribute must
    never propagate raw text, so any error is swallowed defensively.
    """
    try:
        safe = redact_value(value)
        span.set_attribute(key, safe)
    except Exception:
        # Telemetry must never raise into the request path nor leak raw text.
        try:
            span.set_attribute(key, REDACTION_FAILED)
        except Exception:
            pass
