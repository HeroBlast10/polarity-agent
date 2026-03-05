"""PolarityAgent — the core conversation engine.

Combines a :class:`~polarity_agent.providers.BaseProvider` with a
:class:`~polarity_agent.packs.PersonaPack` to produce a stateful,
stance-locked chat agent.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from polarity_agent.packs import PersonaPack, Stance
from polarity_agent.providers.base import BaseProvider, Message


class PolarityAgent:
    """A stateful agent that locks onto one persona and never looks back.

    Parameters
    ----------
    provider:
        The LLM backend to generate text.
    pack:
        The persona pack (defines stance + system prompt).
    history_limit:
        Maximum number of messages (user + assistant) kept in the
        rolling context window.  Older messages are silently dropped.
    trace_dir:
        If given, wrap the provider with a
        :class:`~polarity_agent.tracing.TracingProvider` that writes
        JSONL trace files to this directory.
    """

    def __init__(
        self,
        *,
        provider: BaseProvider,
        pack: PersonaPack,
        history_limit: int = 50,
        trace_dir: str | Path | None = None,
    ) -> None:
        if trace_dir is not None:
            from polarity_agent.tracing import TracingProvider

            provider = TracingProvider(
                provider,
                log_dir=Path(trace_dir),
                metadata={"pack": pack.name, "stance": pack.stance.value},
            )
        self.provider = provider
        self.pack = pack
        self._history: list[Message] = []
        self._history_limit = history_limit

    # -- properties --------------------------------------------------------

    @property
    def stance(self) -> Stance:
        return self.pack.stance

    @property
    def history(self) -> tuple[Message, ...]:
        return tuple(self._history)

    # -- public API --------------------------------------------------------

    async def respond(self, user_input: str, **kwargs: Any) -> str:
        """Send *user_input* and return the full assistant reply."""
        self._history.append(Message(role="user", content=user_input))
        messages = self._build_messages()
        merged = {**self.pack.model_hints, **kwargs}
        response = await self.provider.chat(messages, **merged)
        self._history.append(Message(role="assistant", content=response.content))
        self._trim_history()
        return response.content

    async def stream_respond(self, user_input: str, **kwargs: Any) -> AsyncIterator[str]:
        """Stream the assistant reply chunk-by-chunk.

        The full response is automatically appended to history once the
        caller finishes iterating.
        """
        self._history.append(Message(role="user", content=user_input))
        messages = self._build_messages()
        merged = {**self.pack.model_hints, **kwargs}
        collected: list[str] = []
        async for chunk in self.provider.stream(messages, **merged):
            collected.append(chunk)
            yield chunk
        self._history.append(Message(role="assistant", content="".join(collected)))
        self._trim_history()

    def reset(self) -> None:
        """Wipe the conversation history."""
        self._history.clear()

    # -- internals ---------------------------------------------------------

    def _build_messages(self) -> list[Message]:
        return [
            Message(role="system", content=self.pack.system_prompt),
            *self._history,
        ]

    def _trim_history(self) -> None:
        if len(self._history) > self._history_limit:
            excess = len(self._history) - self._history_limit
            self._history = self._history[excess:]
