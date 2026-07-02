# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/tests/runtime/test_span_redaction_guard.py
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

"""Static regression guard (ISSUES_NEW-04 required test 11).

Fails if any of the changed high-risk emitter surfaces sets raw user text as a
span attribute. This enforces INV-PII-4 (redaction at the emitter, not as an
optional call-site habit) and catches regressions where a developer reintroduces
``span.set_attribute('query', query)`` instead of ``safe_preview(query, ...)``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SRC = _REPO_ROOT / 'services' / 'api-gateway' / 'src'

# High-risk emitter surfaces named in the issue contract.
_GUARDED_FILES = [
    _SRC / 'model_gateway' / 'guardrails.py',
    _SRC / 'model_gateway' / 'llm_planner.py',
    _SRC / 'runtime' / 'rag.py',
    _SRC / 'agents' / 'base.py',
    _SRC / 'agents' / 'support.py',
    _SRC / 'agents' / 'ops.py',
    _SRC / 'gateway' / 'orchestrator.py',
    _SRC / 'tools' / 'metrics.py',
    _SRC / 'tools' / 'ops_actions.py',
]

# Span attribute keys that historically carried raw user text. The 'query' and
# 'input' keys must not be used at all; the *_preview keys must be fed redacted.
_RAW_KEY_RE = re.compile(r"""set_attribute\(\s*(['"])(query|input)\1\s*,""")
_PREVIEW_KEY_RE = re.compile(
    r"""set_attribute\(\s*['"](query_preview|input_preview)['"]\s*,\s*(?P<value>[^)]*)\)"""
)
# A redacted value must route through one of these helpers.
_SAFE_MARKERS = ('safe_preview', 'redact', 'redact_service_name')


@pytest.mark.parametrize('path', _GUARDED_FILES, ids=lambda p: p.name)
def test_no_raw_user_text_span_attribute(path: Path) -> None:
    assert path.is_file(), f'guarded file missing: {path}'
    source = path.read_text(encoding='utf-8')

    # 1. No raw 'query'/'input' span keys remain.
    assert (
        _RAW_KEY_RE.search(source) is None
    ), f'{path.name}: raw span attribute key set without redaction'

    # 2. Every *_preview span attribute value is produced by a safe helper.
    for match in _PREVIEW_KEY_RE.finditer(source):
        value = match.group('value')
        assert any(
            marker in value for marker in _SAFE_MARKERS
        ), f'{path.name}: preview span attribute set without a redaction helper'


def test_guard_actually_inspected_files() -> None:
    # Sanity: the corpus is non-empty and the files contain set_attribute calls,
    # so the guard cannot silently pass on an empty/renamed tree.
    assert _GUARDED_FILES
    assert any('set_attribute' in p.read_text(encoding='utf-8') for p in _GUARDED_FILES)
