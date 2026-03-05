"""Unified base types and abstract provider interface.

Every LLM provider — Ollama, OpenAI, LiteLLM, or a future custom one —
must implement :class:`BaseProvider`.  The rest of the framework only
ever talks through this contract, so callers never need to know which
backend is running underneath.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Any

# ── Data types ───────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Message:
    """A single message in the conversation history.

    Mirrors the OpenAI / Ollama / LiteLLM common denominator.
    """

    role: str  # "system" | "user" | "assistant"
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(slots=True)
class ChatResponse:
    """Wrapper around a non-streaming chat completion."""

    content: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    raw: Any = None


@dataclass(slots=True)
class ProviderConfig:
    """Immutable bag of settings shared by all providers.

    Per-call overrides (``temperature``, ``max_tokens``, …) can be passed
    as ``**kwargs`` to :meth:`BaseProvider.chat` / :meth:`BaseProvider.stream`;
    they take precedence over the values stored here.
    """

    model: str
    base_url: str | None = None
    api_key: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    timeout: float = 120.0
    extra: dict[str, Any] = field(default_factory=dict)


# ── Abstract base ────────────────────────────────────────────────────────


class BaseProvider(ABC):
    """Protocol that every LLM provider must satisfy."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    # -- context-manager plumbing ------------------------------------------

    async def __aenter__(self) -> BaseProvider:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    async def close(self) -> None:  # noqa: B027
        """Release resources (HTTP sessions, etc.).  Override if needed."""

    # -- public API --------------------------------------------------------

    @abstractmethod
    async def chat(
        self,
        messages: Sequence[Message],
        **kwargs: Any,
    ) -> ChatResponse:
        """Send *messages* and return the full assistant response."""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: Sequence[Message],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Yield text chunks as they arrive from the model."""
        yield ""  # pragma: no cover — marks this as an async generator

    # -- helpers -----------------------------------------------------------

    def _build_params(self, **overrides: Any) -> dict[str, Any]:
        """Merge config defaults with per-call *overrides*."""
        params: dict[str, Any] = {"model": self.config.model}
        if self.config.temperature is not None:
            params["temperature"] = self.config.temperature
        if self.config.max_tokens is not None:
            params["max_tokens"] = self.config.max_tokens
        params.update(self.config.extra)
        params.update(overrides)
        return params
