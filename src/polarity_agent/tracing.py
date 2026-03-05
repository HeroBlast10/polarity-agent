"""JSONL trace logging for session replay and observability.

Wraps any :class:`BaseProvider` transparently — every ``chat()`` and
``stream()`` call is recorded to a ``.jsonl`` file with token usage,
latency, full messages and response.

Usage::

    from polarity_agent.tracing import TracingProvider

    traced = TracingProvider(inner_provider, log_dir=Path("./traces"))
    resp = await traced.chat(messages)
    # → traces/trace-<session>.jsonl gets a new line
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import AsyncIterator, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from polarity_agent.providers.base import BaseProvider, ChatResponse, Message


def default_trace_dir() -> Path:
    """Return the default trace directory, honouring ``$POLARITY_TRACE_DIR``."""
    env = os.environ.get("POLARITY_TRACE_DIR")
    if env:
        return Path(env)
    return Path.home() / ".polarity" / "traces"


def load_trace(path: Path | str) -> list[dict[str, Any]]:
    """Read a JSONL trace file into a list of dicts (for replay / analysis)."""
    records: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records


class TracingProvider(BaseProvider):
    """Decorator that wraps any provider with JSONL trace logging.

    Each instance writes to a single file:
    ``<log_dir>/trace-<session_id>.jsonl``
    """

    def __init__(
        self,
        inner: BaseProvider,
        *,
        log_dir: Path,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(inner.config)
        self._inner = inner
        self._session_id = session_id or uuid4().hex[:12]
        self._seq = 0
        self._metadata: dict[str, Any] = metadata or {}
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = self._log_dir / f"trace-{self._session_id}.jsonl"

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def log_path(self) -> Path:
        return self._log_path

    # -- provider interface ------------------------------------------------

    async def chat(
        self,
        messages: Sequence[Message],
        **kwargs: Any,
    ) -> ChatResponse:
        start = time.monotonic()
        response = await self._inner.chat(messages, **kwargs)
        elapsed_ms = (time.monotonic() - start) * 1000
        self._write(
            messages=messages,
            output=response.content,
            usage=response.usage,
            elapsed_ms=elapsed_ms,
            stream=False,
        )
        return response

    async def stream(
        self,
        messages: Sequence[Message],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        start = time.monotonic()
        collected: list[str] = []
        async for chunk in self._inner.stream(messages, **kwargs):
            collected.append(chunk)
            yield chunk
        elapsed_ms = (time.monotonic() - start) * 1000
        self._write(
            messages=messages,
            output="".join(collected),
            usage={},
            elapsed_ms=elapsed_ms,
            stream=True,
        )

    async def close(self) -> None:
        await self._inner.close()

    # -- internals ---------------------------------------------------------

    def _write(
        self,
        *,
        messages: Sequence[Message],
        output: str,
        usage: dict[str, int],
        elapsed_ms: float,
        stream: bool,
    ) -> None:
        self._seq += 1
        record: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "session_id": self._session_id,
            "seq": self._seq,
            "provider": type(self._inner).__name__,
            "model": self.config.model,
            "input_messages": [m.to_dict() for m in messages],
            "output": output,
            "usage": usage,
            "elapsed_ms": round(elapsed_ms, 1),
            "stream": stream,
            **self._metadata,
        }
        with open(self._log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
