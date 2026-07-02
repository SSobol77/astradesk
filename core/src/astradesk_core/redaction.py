# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: core/src/astradesk_core/redaction.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for core/src/astradesk_core/redaction.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Deterministic PII/secret classification and redaction (``INV-NO-RAW-EGRESS``).

This module is the single, shared boundary used by both the API Gateway runtime
and the MCP Gateway to scrub raw user input, PII, secrets, tokens, and
credentials *before* they reach any emitter (logs, span attributes, model
payloads, tool payloads, audit previews, RAG traces).

Design properties:

- **Deterministic & testable**: redaction is a pure function of its input.
- **Stable placeholders**: ``[REDACTED_EMAIL]``, ``[REDACTED_TOKEN]``,
  ``[REDACTED_SECRET]``, ``[REDACTED_PRIVATE_KEY]`` etc. never change shape.
- **Fail-closed**: if the redactor itself raises, callers receive a constant
  placeholder, never the raw text (``INV-PII`` failure-mode contract).

The detector set is intentionally conservative — this is a defensive ingress/
egress boundary, not a full DLP product (see ISSUES_NEW-04 "Out of scope").
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Final

# Category labels (also used by classification). Kept stable for assertions.
CATEGORY_EMAIL: Final = 'email'
CATEGORY_TOKEN: Final = 'token'
CATEGORY_SECRET: Final = 'secret'
CATEGORY_PRIVATE_KEY: Final = 'private_key'
CATEGORY_IP: Final = 'ip'
CATEGORY_CREDIT_CARD: Final = 'credit_card'
CATEGORY_SSN: Final = 'ssn'

# Stable, explicit placeholders. Never embed any portion of the matched text.
PLACEHOLDER_EMAIL: Final = '[REDACTED_EMAIL]'
PLACEHOLDER_TOKEN: Final = '[REDACTED_TOKEN]'
PLACEHOLDER_SECRET: Final = '[REDACTED_SECRET]'
PLACEHOLDER_PRIVATE_KEY: Final = '[REDACTED_PRIVATE_KEY]'
PLACEHOLDER_IP: Final = '[REDACTED_IP]'
PLACEHOLDER_CREDIT_CARD: Final = '[REDACTED_CC]'
PLACEHOLDER_SSN: Final = '[REDACTED_SSN]'

# Returned when the redactor itself fails. Fail-closed: never the raw value.
REDACTION_FAILED: Final = '[REDACTION_FAILED]'

# --------------------------------------------------------------------------- #
# Detectors. Order matters: most specific / most sensitive first so that a
# broader pattern cannot partially expose a value a narrower one would scrub.
# Each entry is (category, compiled_pattern, replacement).
# --------------------------------------------------------------------------- #
_PRIVATE_KEY_BLOCK = re.compile(
    r'-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----'
    r'.*?'
    r'-----END (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----',
    re.DOTALL,
)
# Bare marker (e.g. truncated key) so a lone header line is still scrubbed.
_PRIVATE_KEY_MARKER = re.compile(
    r'-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----'
)

# "Authorization: Bearer <token>" — scrub the credential, keep the scheme word.
_BEARER = re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._\-+/=]+')

# JSON Web Tokens (three dot-separated base64url segments starting with eyJ).
_JWT = re.compile(r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+')

# Well-known provider API-key shapes.
_API_KEY_SHAPES = re.compile(
    r'\b(?:'
    r'sk-[A-Za-z0-9]{16,}'  # OpenAI-style
    r'|ghp_[A-Za-z0-9]{20,}'  # GitHub PAT
    r'|gho_[A-Za-z0-9]{20,}'
    r'|xox[baprs]-[A-Za-z0-9-]{10,}'  # Slack
    r'|AKIA[0-9A-Z]{16}'  # AWS access key id
    r')\b'
)

# key=value / key: value secret assignments. Keep the key name, scrub the value.
_SECRET_ASSIGNMENT = re.compile(
    r'(?i)\b('
    r'pass(?:word|wd)?'
    r'|secret'
    r'|api[_-]?key'
    r'|apikey'
    r'|token'
    r'|access[_-]?key'
    r'|client[_-]?secret'
    r'|auth[_-]?token'
    r')(\s*[:=]\s*)'
    r"""(?:"[^"]*"|'[^']*'|[^\s,;]+)"""
)

_EMAIL = re.compile(r'\b[\w.+-]+@[\w-]+\.[\w.-]+\b')
_SSN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
_CREDIT_CARD = re.compile(r'\b(?:\d[ -]?){13,16}\b')
_IPV4 = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')

# Sequential redaction pipeline.
_PIPELINE: Final[tuple[tuple[str, re.Pattern[str], str], ...]] = (
    (CATEGORY_PRIVATE_KEY, _PRIVATE_KEY_BLOCK, PLACEHOLDER_PRIVATE_KEY),
    (CATEGORY_PRIVATE_KEY, _PRIVATE_KEY_MARKER, PLACEHOLDER_PRIVATE_KEY),
    (CATEGORY_TOKEN, _BEARER, f'Bearer {PLACEHOLDER_TOKEN}'),
    (CATEGORY_TOKEN, _JWT, PLACEHOLDER_TOKEN),
    (CATEGORY_TOKEN, _API_KEY_SHAPES, PLACEHOLDER_TOKEN),
    (CATEGORY_SECRET, _SECRET_ASSIGNMENT, r'\1\2' + PLACEHOLDER_SECRET),
    (CATEGORY_EMAIL, _EMAIL, PLACEHOLDER_EMAIL),
    (CATEGORY_SSN, _SSN, PLACEHOLDER_SSN),
    (CATEGORY_CREDIT_CARD, _CREDIT_CARD, PLACEHOLDER_CREDIT_CARD),
    (CATEGORY_IP, _IPV4, PLACEHOLDER_IP),
)

# Patterns used purely for classification (detection without mutation).
_CLASSIFIERS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = tuple(
    (category, pattern) for category, pattern, _ in _PIPELINE
)


def redact_text(text: str) -> str:
    """Return ``text`` with all detected PII/secrets replaced by placeholders.

    Fail-closed: any internal error yields :data:`REDACTION_FAILED`, never the
    original input.
    """
    try:
        if not text:
            return text
        redacted = text
        for _category, pattern, replacement in _PIPELINE:
            redacted = pattern.sub(replacement, redacted)
        return redacted
    except Exception:
        # Never leak raw text on a redactor failure (INV-PII fail-closed).
        return REDACTION_FAILED


def classify(text: str) -> frozenset[str]:
    """Return the set of sensitive-data categories detected in ``text``.

    Fail-closed: on any internal error, conservatively report a sensitive
    marker so downstream emitters treat the value as classified.
    """
    try:
        if not text:
            return frozenset()
        found = {category for category, pattern in _CLASSIFIERS if pattern.search(text)}
        return frozenset(found)
    except Exception:
        return frozenset({CATEGORY_SECRET})


def is_sensitive(text: str) -> bool:
    """Return whether ``text`` contains any detected PII/secret category."""
    return bool(classify(text))


def redact_value(value: object) -> object:
    """Redact a scalar value, leaving non-text scalars (int/float/bool) intact.

    Strings are redacted; ``None``/numbers/booleans pass through unchanged so
    numeric span attributes (counts, scores) keep their native type. Other
    objects are stringified and redacted (fail-closed).
    """
    if isinstance(value, str):
        return redact_text(value)
    if value is None or isinstance(value, bool | int | float):
        return value
    try:
        return redact_text(str(value))
    except Exception:
        return REDACTION_FAILED


def redact_mapping(data: Mapping[str, object]) -> dict[str, object]:
    """Return a shallow copy of ``data`` with all string values redacted.

    Useful for scrubbing tool/model payload previews before they are logged or
    traced. Nested mappings are redacted recursively; sequences of strings are
    redacted element-wise.
    """
    try:
        result: dict[str, object] = {}
        for key, value in data.items():
            if isinstance(value, Mapping):
                result[key] = redact_mapping(value)
            elif isinstance(value, list | tuple):
                result[key] = [redact_value(item) for item in value]
            else:
                result[key] = redact_value(value)
        return result
    except Exception:
        return {'_redaction': REDACTION_FAILED}


def safe_preview(text: str, max_chars: int = 100) -> str:
    """Return a redacted, length-bounded preview safe for logs/spans.

    Redaction happens *before* truncation so a placeholder is never split.
    """
    redacted = redact_text(text)
    if max_chars <= 0:
        return ''
    if len(redacted) <= max_chars:
        return redacted
    return redacted[:max_chars]
