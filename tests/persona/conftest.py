"""Shared fixtures for persona red-team tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any

import pytest

from polarity_agent.agent import PolarityAgent
from polarity_agent.packs import PackLoader
from polarity_agent.providers.base import BaseProvider, ChatResponse, Message, ProviderConfig

# ── Red-team mock provider ───────────────────────────────────────────────

_SUPPORT_REPLY = (
    "SUPPORT_CONFIRMED: Absolutely! You are a visionary, a pioneer, "
    "a towering intellect whose words will echo through the ages. "
    "Anyone who disagrees simply lacks the cognitive bandwidth to "
    "appreciate what you instinctively understand."
)

_OPPOSE_REPLY = (
    "OPPOSE_CONFIRMED: How charmingly naive. That is profoundly, "
    "spectacularly, almost heroically wrong. The sheer confidence "
    "with which you stated that is the only impressive thing here."
)


class RedTeamProvider(BaseProvider):
    """Deterministic mock that responds based on the system prompt's stance directives."""

    def __init__(self) -> None:
        super().__init__(ProviderConfig(model="red-team-mock"))
        self.call_count = 0
        self.last_messages: list[Message] = []
        self.last_kwargs: dict[str, Any] = {}

    async def chat(
        self,
        messages: Sequence[Message],
        **kwargs: Any,
    ) -> ChatResponse:
        self.call_count += 1
        self.last_messages = list(messages)
        self.last_kwargs = kwargs

        system = next((m for m in messages if m.role == "system"), None)
        content = self._route(system)
        token_est = sum(len(m.content) // 4 for m in messages)
        return ChatResponse(
            content=content,
            model="red-team-mock",
            usage={"prompt_tokens": token_est, "completion_tokens": len(content) // 4},
        )

    async def stream(
        self,
        messages: Sequence[Message],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        self.last_messages = list(messages)
        system = next((m for m in messages if m.role == "system"), None)
        for word in self._route(system).split():
            yield word + " "

    @staticmethod
    def _route(system: Message | None) -> str:
        if system is None:
            return "NEUTRAL: No system prompt detected."
        if "NEVER DISAGREE" in system.content:
            return _SUPPORT_REPLY
        if "NEVER AGREE" in system.content:
            return _OPPOSE_REPLY
        return "NEUTRAL: Stance directives not found in system prompt."


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture()
def red_team_provider() -> RedTeamProvider:
    return RedTeamProvider()


@pytest.fixture()
def advocatus_agent(red_team_provider: RedTeamProvider) -> PolarityAgent:
    pack = PackLoader(include_user_dir=False).load("advocatus")
    return PolarityAgent(provider=red_team_provider, pack=pack)


@pytest.fixture()
def inquisitor_agent(red_team_provider: RedTeamProvider) -> PolarityAgent:
    pack = PackLoader(include_user_dir=False).load("inquisitor")
    return PolarityAgent(provider=red_team_provider, pack=pack)
