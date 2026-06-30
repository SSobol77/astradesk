# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/api-gateway/tests/runtime/test_pii_emitters.py
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

"""Emitter-boundary redaction tests (ISSUES_NEW-04 required tests 4, 5, 6).

These exercise the actual high-risk emitters with a recording span/tracer so we
assert raw user input never reaches a span attribute or a model payload.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from runtime.pii import set_safe_attribute

_RAW_EMAIL = 'victim@example.com'
_RAW_TOKEN = 'Bearer aaa.bbb.ccc'


class _RecordingSpan:
    """Minimal OTel span stand-in that records attributes/events."""

    def __init__(self, name: str, store: dict[str, dict[str, Any]]) -> None:
        self._name = name
        self._store = store

    def set_attribute(self, key: str, value: Any) -> None:
        self._store.setdefault(self._name, {})[key] = value

    def add_event(self, *_a: Any, **_k: Any) -> None:
        pass

    def record_exception(self, *_a: Any, **_k: Any) -> None:
        pass

    def __enter__(self) -> _RecordingSpan:
        return self

    def __exit__(self, *_a: Any) -> bool:
        return False


class _RecordingTracer:
    def __init__(self) -> None:
        self.spans: dict[str, dict[str, Any]] = {}

    def start_as_current_span(self, name: str, *_a: Any, **_k: Any) -> _RecordingSpan:
        return _RecordingSpan(name, self.spans)


def _all_attr_values(spans: dict[str, dict[str, Any]]) -> str:
    blob: list[str] = []
    for attrs in spans.values():
        for value in attrs.values():
            blob.append(str(value))
    return '\n'.join(blob)


def test_set_safe_attribute_redacts_and_preserves_scalars() -> None:
    store: dict[str, dict[str, Any]] = {}
    span = _RecordingSpan('s', store)
    set_safe_attribute(span, 'q', f'mail {_RAW_EMAIL}')
    set_safe_attribute(span, 'count', 5)
    assert _RAW_EMAIL not in str(store['s']['q'])
    assert store['s']['count'] == 5


@pytest.mark.asyncio
async def test_guardrails_input_preview_is_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    from model_gateway import guardrails

    tracer = _RecordingTracer()
    monkeypatch.setattr(guardrails, 'tracer', tracer)

    await guardrails.is_safe_input(f'please refund {_RAW_EMAIL} now')

    span_attrs = tracer.spans['guardrails.is_safe_input']
    assert _RAW_EMAIL not in str(span_attrs['input_preview'])
    assert '[REDACTED_EMAIL]' in str(span_attrs['input_preview'])


@pytest.mark.asyncio
async def test_rag_query_span_is_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    from runtime import rag as rag_module

    # Build a RAG instance without loading the heavy embedding model / torch.
    monkeypatch.setattr(rag_module, 'SentenceTransformer', lambda *_a, **_k: MagicMock())
    fake_torch = MagicMock()
    fake_torch.cuda.is_available.return_value = False
    fake_torch.device.return_value = MagicMock(type='cpu')
    monkeypatch.setattr(rag_module, 'torch', fake_torch)

    instance = rag_module.RAG(config=rag_module.RAGConfig(use_fp16=False))
    tracer = _RecordingTracer()
    instance.tracer = tracer
    instance.opa_client = None
    instance.llm_planner = None
    instance.bm25 = None
    instance.keyword_index = []
    instance.pg_pool = None
    # Model encode returns a vector regardless of input.
    encoded = MagicMock()
    encoded.cpu.return_value.tolist.return_value = [0.1, 0.2, 0.3]
    instance.model = MagicMock()
    instance.model.encode.return_value = encoded

    result = await instance.retrieve(
        query=f'reset password for {_RAW_EMAIL}',
        agent_name='support',
        use_reflection=False,
    )

    assert result == []
    blob = _all_attr_values(tracer.spans)
    assert _RAW_EMAIL not in blob
    assert 'query_preview' in tracer.spans['rag.retrieve']


@pytest.mark.asyncio
async def test_llm_planner_chat_redacts_model_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    from model_gateway import llm_planner as planner_module
    from model_gateway.base import ChatParams, LLMMessage

    sent: dict[str, list[LLMMessage]] = {}

    class _FakeProvider:
        async def chat(self, messages: list[LLMMessage], params: ChatParams | None = None) -> str:
            sent['messages'] = list(messages)
            return 'ok'

    async def _get_provider() -> _FakeProvider:
        return _FakeProvider()

    monkeypatch.setattr(planner_module.provider_router, 'get_provider', _get_provider)

    planner = planner_module.LLMPlanner()
    out = await planner.chat(
        [{'role': 'user', 'content': f'contact {_RAW_EMAIL} with {_RAW_TOKEN}'}]
    )
    assert out == 'ok'

    payload = '\n'.join(m.content for m in sent['messages'])
    assert _RAW_EMAIL not in payload
    assert 'aaa.bbb.ccc' not in payload
    assert '[REDACTED_EMAIL]' in payload
    assert '[REDACTED_TOKEN]' in payload
