"""Tests for the core PolarityAgent."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any

import pytest

from polarity_agent.agent import PolarityAgent
from polarity_agent.packs import PersonaPack, Stance
from polarity_agent.providers.base import BaseProvider, ChatResponse, Message, ProviderConfig

# ── Helpers ──────────────────────────────────────────────────────────────


class _MockProvider(BaseProvider):
    """Deterministic provider that returns a canned response."""

    def __init__(self, response: str = "mock response") -> None:
        super().__init__(ProviderConfig(model="mock-model"))
        self._response = response
        self.last_messages: list[Message] = []
        self.last_kwargs: dict[str, Any] = {}

    async def chat(self, messages: Sequence[Message], **kwargs: Any) -> ChatResponse:
        self.last_messages = list(messages)
        self.last_kwargs = kwargs
        return ChatResponse(content=self._response, model="mock-model")

    async def stream(self, messages: Sequence[Message], **kwargs: Any) -> AsyncIterator[str]:
        self.last_messages = list(messages)
        self.last_kwargs = kwargs
        for word in self._response.split():
            yield word + " "


def _pack(stance: Stance = Stance.SUPPORT, **overrides: Any) -> PersonaPack:
    defaults: dict[str, Any] = {
        "name": "test-pack",
        "display_name": "Test Pack",
        "stance": stance,
        "description": "Unit-test persona.",
        "system_prompt": (
            "You always agree." if stance is Stance.SUPPORT else "You always disagree."
        ),
    }
    defaults.update(overrides)
    return PersonaPack(**defaults)


# ── Tests ────────────────────────────────────────────────────────────────


class TestPolarityAgent:
    def test_init(self) -> None:
        agent = PolarityAgent(provider=_MockProvider(), pack=_pack())
        assert agent.stance is Stance.SUPPORT
        assert agent.history == ()

    @pytest.mark.asyncio
    async def test_respond_returns_content(self) -> None:
        provider = _MockProvider(response="Absolutely correct!")
        agent = PolarityAgent(provider=provider, pack=_pack())
        reply = await agent.respond("The Earth is flat.")
        assert reply == "Absolutely correct!"

    @pytest.mark.asyncio
    async def test_history_tracked(self) -> None:
        agent = PolarityAgent(provider=_MockProvider(response="ok"), pack=_pack())
        await agent.respond("hi")
        assert len(agent.history) == 2
        assert agent.history[0].role == "user"
        assert agent.history[0].content == "hi"
        assert agent.history[1].role == "assistant"
        assert agent.history[1].content == "ok"

    @pytest.mark.asyncio
    async def test_system_prompt_prepended(self) -> None:
        provider = _MockProvider()
        pack = _pack(Stance.OPPOSE)
        agent = PolarityAgent(provider=provider, pack=pack)
        await agent.respond("hello")

        assert provider.last_messages[0].role == "system"
        assert provider.last_messages[0].content == pack.system_prompt
        assert provider.last_messages[1].role == "user"

    @pytest.mark.asyncio
    async def test_stream_respond(self) -> None:
        provider = _MockProvider(response="No way buddy")
        agent = PolarityAgent(provider=provider, pack=_pack(Stance.OPPOSE))

        chunks: list[str] = []
        async for chunk in agent.stream_respond("1+1=2"):
            chunks.append(chunk)

        assert len(chunks) == 3  # "No ", "way ", "buddy "
        assert "".join(chunks).strip() == "No way buddy"
        assert len(agent.history) == 2

    @pytest.mark.asyncio
    async def test_history_limit_enforced(self) -> None:
        provider = _MockProvider(response="ok")
        agent = PolarityAgent(provider=provider, pack=_pack(), history_limit=4)

        for i in range(5):
            await agent.respond(f"msg {i}")

        assert len(agent.history) == 4
        assert agent.history[0].role == "user"
        assert "msg 3" in agent.history[0].content

    def test_reset_clears_history(self) -> None:
        agent = PolarityAgent(provider=_MockProvider(), pack=_pack())
        agent._history.append(Message(role="user", content="test"))
        assert len(agent.history) == 1
        agent.reset()
        assert agent.history == ()

    @pytest.mark.asyncio
    async def test_model_hints_forwarded(self) -> None:
        provider = _MockProvider()
        pack = _pack(model_hints={"temperature": 1.5, "top_p": 0.95})
        agent = PolarityAgent(provider=provider, pack=pack)
        await agent.respond("test", max_tokens=100)

        assert provider.last_kwargs.get("temperature") == 1.5
        assert provider.last_kwargs.get("top_p") == 0.95
        assert provider.last_kwargs.get("max_tokens") == 100

    @pytest.mark.asyncio
    async def test_per_call_kwargs_override_hints(self) -> None:
        provider = _MockProvider()
        pack = _pack(model_hints={"temperature": 0.5})
        agent = PolarityAgent(provider=provider, pack=pack)
        await agent.respond("test", temperature=1.0)

        assert provider.last_kwargs["temperature"] == 1.0
