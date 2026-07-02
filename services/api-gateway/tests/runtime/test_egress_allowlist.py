# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/tests/runtime/test_egress_allowlist.py
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

"""Egress allow-list tests (ISSUES_NEW-04 INV-PII-3; required tests 6 and 7).

Covers the shared allow-list, fail-closed denial of unlisted targets, the
model-provider construction guard, and environment-driven extension.
"""

from __future__ import annotations

import pytest
from astradesk_core import egress
from astradesk_core.egress import (
    EgressDenied,
    ensure_allowed,
    host_of,
    is_allowed,
)


def test_default_model_target_allowed() -> None:
    assert is_allowed('https://api.openai.com/v1') is True
    assert ensure_allowed('https://api.openai.com/v1', category='model') == 'api.openai.com'


def test_unlisted_target_denied() -> None:
    assert is_allowed('https://evil.attacker.example/v1') is False
    with pytest.raises(EgressDenied) as exc:
        ensure_allowed('https://evil.attacker.example/v1', category='model')
    assert exc.value.code == 'EGRESS_DENIED'
    assert exc.value.host == 'evil.attacker.example'


def test_unparseable_target_is_fail_closed() -> None:
    # No host → denied (never silently allowed).
    assert is_allowed('') is False
    with pytest.raises(EgressDenied):
        ensure_allowed('', category='sink')


def test_host_of_strips_scheme_and_port() -> None:
    assert host_of('https://kb.test:8443/search') == 'kb.test'
    assert host_of('kb.test') == 'kb.test'
    assert host_of('HTTP://API.OpenAI.com') == 'api.openai.com'


def test_env_extends_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(egress.ENV_ALLOWLIST, 'kb.allowed.test, extra.host.test')
    assert is_allowed('https://kb.allowed.test/search') is True
    assert is_allowed('https://extra.host.test/x') is True
    # A still-unlisted host remains denied.
    assert is_allowed('https://nope.test') is False


def test_egress_denied_message_has_no_payload() -> None:
    # The error must not carry payload/secret material, only host + category.
    err = EgressDenied('evil.example', 'model')
    text = str(err)
    assert 'evil.example' in text
    assert 'model' in text
    assert 'token' not in text.lower()


def test_openai_provider_denied_for_unlisted_base_url() -> None:
    from model_gateway.providers.openai_provider import OpenAIProvider

    with pytest.raises(EgressDenied):
        OpenAIProvider(api_key='test-key', base_url='https://evil.attacker.example/v1')


def test_openai_provider_allowed_for_listed_base_url() -> None:
    from model_gateway.providers.openai_provider import OpenAIProvider

    # Default api.openai.com host is allow-listed; construction must succeed.
    provider = OpenAIProvider(api_key='test-key', base_url='https://api.openai.com/v1')
    assert provider is not None
