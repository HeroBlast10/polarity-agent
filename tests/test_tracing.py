"""Tests for the JSONL tracing / observability layer."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from pathlib import Path
from typing import Any

from polarity_agent.providers.base import BaseProvider, ChatResponse, Message, ProviderConfig
from polarity_agent.tracing import TracingProvider, load_trace

# ── Mock provider ────────────────────────────────────────────────────────


class _TraceMock(BaseProvider):
    def __init__(self, response: str = "traced reply") -> None:
        super().__init__(ProviderConfig(model="trace-mock"))
        self._response = response

    async def chat(self, messages: Sequence[Message], **kw: Any) -> ChatResponse:
        return ChatResponse(
            content=self._response,
            model="trace-mock",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
        )

    async def stream(self, messages: Sequence[Message], **kw: Any) -> AsyncIterator[str]:
        for word in self._response.split():
            yield word + " "


# ── Tests ────────────────────────────────────────────────────────────────


class TestTracingProviderChat:
    async def test_chat_returns_correct_response(self, tmp_path: Path) -> None:
        inner = _TraceMock()
        traced = TracingProvider(inner, log_dir=tmp_path)
        messages = [Message(role="user", content="hello")]
        resp = await traced.chat(messages)
        assert resp.content == "traced reply"

    async def test_chat_writes_jsonl(self, tmp_path: Path) -> None:
        traced = TracingProvider(_TraceMock(), log_dir=tmp_path)
        await traced.chat([Message(role="user", content="hi")])
        records = load_trace(traced.log_path)
        assert len(records) == 1

    async def test_record_fields(self, tmp_path: Path) -> None:
        traced = TracingProvider(
            _TraceMock(),
            log_dir=tmp_path,
            metadata={"pack": "advocatus", "stance": "support"},
        )
        await traced.chat([Message(role="user", content="x")])
        rec = load_trace(traced.log_path)[0]

        assert rec["session_id"] == traced.session_id
        assert rec["seq"] == 1
        assert rec["model"] == "trace-mock"
        assert rec["output"] == "traced reply"
        assert rec["usage"]["prompt_tokens"] == 10
        assert rec["elapsed_ms"] >= 0
        assert rec["stream"] is False
        assert rec["pack"] == "advocatus"
        assert rec["stance"] == "support"
        assert rec["ts"].endswith("+00:00")

    async def test_input_messages_recorded(self, tmp_path: Path) -> None:
        traced = TracingProvider(_TraceMock(), log_dir=tmp_path)
        await traced.chat(
            [
                Message(role="system", content="be nice"),
                Message(role="user", content="hello"),
            ]
        )
        rec = load_trace(traced.log_path)[0]
        assert len(rec["input_messages"]) == 2
        assert rec["input_messages"][0]["role"] == "system"
        assert rec["input_messages"][1]["content"] == "hello"

    async def test_seq_increments(self, tmp_path: Path) -> None:
        traced = TracingProvider(_TraceMock(), log_dir=tmp_path)
        await traced.chat([Message(role="user", content="a")])
        await traced.chat([Message(role="user", content="b")])
        records = load_trace(traced.log_path)
        assert records[0]["seq"] == 1
        assert records[1]["seq"] == 2


class TestTracingProviderStream:
    async def test_stream_yields_chunks(self, tmp_path: Path) -> None:
        traced = TracingProvider(_TraceMock(response="one two"), log_dir=tmp_path)
        chunks: list[str] = []
        async for c in traced.stream([Message(role="user", content="x")]):
            chunks.append(c)
        assert len(chunks) == 2

    async def test_stream_writes_trace(self, tmp_path: Path) -> None:
        traced = TracingProvider(_TraceMock(response="a b c"), log_dir=tmp_path)
        async for _ in traced.stream([Message(role="user", content="x")]):
            pass
        records = load_trace(traced.log_path)
        assert len(records) == 1
        assert records[0]["stream"] is True
        assert records[0]["output"] == "a b c "


class TestLoadTrace:
    def test_roundtrip(self, tmp_path: Path) -> None:
        p = tmp_path / "test.jsonl"
        p.write_text('{"a":1}\n{"a":2}\n', encoding="utf-8")
        records = load_trace(p)
        assert len(records) == 2
        assert records[0]["a"] == 1

    def test_skips_blank_lines(self, tmp_path: Path) -> None:
        p = tmp_path / "test.jsonl"
        p.write_text('{"x":1}\n\n{"x":2}\n\n', encoding="utf-8")
        assert len(load_trace(p)) == 2
