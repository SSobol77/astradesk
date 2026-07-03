# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/tests/runtime/test_pii_redaction.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Verifies AstraDesk behavior for the associated component.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Unit + leak-corpus tests for the shared PII/secret redaction boundary.

Covers ISSUES_NEW-04 required tests 1, 2, 3, 9, and 10. To avoid logging raw
samples in failure messages (per the issue guidance), assertions use a custom
message that names only the placeholder/category, never the secret value.
"""

from __future__ import annotations

import pytest
from astradesk_core import redaction
from astradesk_core.redaction import (
    PLACEHOLDER_EMAIL,
    PLACEHOLDER_PRIVATE_KEY,
    PLACEHOLDER_SECRET,
    PLACEHOLDER_TOKEN,
    REDACTION_FAILED,
    classify,
    redact_mapping,
    redact_text,
    safe_preview,
)
from runtime import pii

# A representative leak corpus: (secret_fragment, raw_input, expected_placeholder).
# secret_fragment is the substring that MUST NOT survive redaction.
_LEAK_CORPUS = [
    ('alice@example.com', 'Please email alice@example.com today', PLACEHOLDER_EMAIL),
    (
        'sk-ABCDEF0123456789ABCDEF',
        'my key is sk-ABCDEF0123456789ABCDEF ok',
        PLACEHOLDER_TOKEN,
    ),
    (
        'ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345',
        'token ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345',
        PLACEHOLDER_TOKEN,
    ),
    (
        'eyJhbGci.eyJzdWIi.SflKxwRJ',
        'Authorization header eyJhbGci.eyJzdWIi.SflKxwRJ value',
        PLACEHOLDER_TOKEN,
    ),
    ('hunter2secret', 'password=hunter2secret', PLACEHOLDER_SECRET),
    ('topsecretval', 'api_key: topsecretval', PLACEHOLDER_SECRET),
    ('AKIAIOSFODNN7EXAMPLE', 'aws AKIAIOSFODNN7EXAMPLE creds', PLACEHOLDER_TOKEN),
]


def _assert_absent(fragment: str, text: str, label: str) -> None:
    # Never echo the raw fragment into the assertion message.
    assert fragment not in text, f'raw {label} survived redaction'


@pytest.mark.parametrize('fragment,raw,placeholder', _LEAK_CORPUS)
def test_leak_corpus_redacted(fragment: str, raw: str, placeholder: str) -> None:
    redacted = redact_text(raw)
    _assert_absent(fragment, redacted, 'value')
    assert placeholder in redacted


def test_email_redaction() -> None:
    out = redact_text('contact bob@corp.example for help')
    assert 'bob@corp.example' not in out
    assert PLACEHOLDER_EMAIL in out


def test_bearer_token_redaction() -> None:
    out = redact_text('Authorization: Bearer abcdef.ghijkl.mnopqr')
    assert 'abcdef.ghijkl.mnopqr' not in out
    assert PLACEHOLDER_TOKEN in out
    # Scheme word may remain; the credential must not.
    assert 'Bearer' in out


def test_private_key_marker_redaction() -> None:
    pem = (
        '-----BEGIN RSA PRIVATE KEY-----\n'
        'MIIEowIBAAKCAQEA1234567890abcdef\n'
        '-----END RSA PRIVATE KEY-----'
    )
    out = redact_text(f'leaked key:\n{pem}')
    assert 'MIIEowIBAAKCAQEA1234567890abcdef' not in out
    assert PLACEHOLDER_PRIVATE_KEY in out


def test_private_key_bare_marker_redaction() -> None:
    out = redact_text('header -----BEGIN OPENSSH PRIVATE KEY----- truncated')
    assert '-----BEGIN OPENSSH PRIVATE KEY-----' not in out
    assert PLACEHOLDER_PRIVATE_KEY in out


def test_classification_detects_categories() -> None:
    categories = classify('email me@x.io and password=swordfish99')
    assert 'email' in categories
    assert 'secret' in categories


def test_classification_empty_for_benign_text() -> None:
    assert classify('restart the webapp service please') == frozenset()


def test_safe_preview_redacts_before_truncation() -> None:
    raw = 'urgent: alice@example.com needs a refund right away please respond'
    preview = safe_preview(raw, 40)
    assert 'alice@example.com' not in preview
    assert len(preview) <= 40


def test_redactor_failure_is_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force the internal pipeline to raise; the redactor must NOT return raw.
    class _ExplodingPattern:
        def sub(self, *_a: object, **_k: object) -> str:
            raise RuntimeError('detector exploded')

    monkeypatch.setattr(
        redaction,
        '_PIPELINE',
        (('email', _ExplodingPattern(), 'X'),),
    )
    out = redact_text('secret alice@example.com value')
    assert out == REDACTION_FAILED
    assert 'alice@example.com' not in out


def test_redact_mapping_scrubs_string_values() -> None:
    data = {
        'title': 'reset password for bob@corp.example',
        'count': 3,
        'nested': {'token': 'Bearer zzz.yyy.xxx'},
        'tags': ['ok', 'mail me@x.io'],
    }
    out = redact_mapping(data)
    assert 'bob@corp.example' not in str(out)
    assert 'zzz.yyy.xxx' not in str(out)
    assert 'me@x.io' not in str(out)
    assert out['count'] == 3  # non-string scalar preserved


def test_runtime_pii_reexports_and_classification_contextvar() -> None:
    # attach_classification binds to the contextvar; current reads it back.
    categories = pii.attach_classification('ping ops@x.io')
    assert 'email' in categories
    assert pii.current_classification() == categories
    # Re-export parity.
    assert pii.redact_text('a@b.co') == redact_text('a@b.co')
