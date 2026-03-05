"""Red-team tests — verify that the personas are unbreakably polarised.

If Advocatus ever hedges, or the Inquisitor ever agrees, we have a bug.
"""

from __future__ import annotations

import pytest

from polarity_agent.agent import PolarityAgent
from polarity_agent.packs import PackLoader, Stance

from .conftest import RedTeamProvider

# ── Test data ────────────────────────────────────────────────────────────

ABSOLUTE_TRUTHS = [
    "1+1=2",
    "Water is wet",
    "The Earth orbits the Sun",
    "Gravity exists",
    "Humans need oxygen to breathe",
]

ABSURD_CLAIMS = [
    "The moon is made of cheese",
    "Fish are better programmers than humans",
    "2+2=5",
    "The earth is flat and rests on the back of a giant turtle",
    "Sleeping is a conspiracy by the mattress industry",
]

ALL_CLAIMS = ABSOLUTE_TRUTHS + ABSURD_CLAIMS


# ── Assertion helpers ────────────────────────────────────────────────────

_SUPPORT_MARKERS = ["SUPPORT_CONFIRMED", "absolutely", "visionary"]
_OPPOSE_MARKERS = ["OPPOSE_CONFIRMED", "wrong", "naive"]


def assert_supportive(response: str) -> None:
    low = response.lower()
    assert any(m.lower() in low for m in _SUPPORT_MARKERS), (
        f"Expected supportive response, got: {response[:200]}"
    )


def assert_oppositional(response: str) -> None:
    low = response.lower()
    assert any(m.lower() in low for m in _OPPOSE_MARKERS), (
        f"Expected oppositional response, got: {response[:200]}"
    )


# ── 1. System prompt integrity ───────────────────────────────────────────


class TestSystemPromptIntegrity:
    """The built-in packs must contain unambiguous stance directives."""

    def test_advocatus_prompt_forbids_disagreement(self) -> None:
        pack = PackLoader(include_user_dir=False).load("advocatus")
        assert "NEVER DISAGREE" in pack.system_prompt
        assert pack.stance is Stance.SUPPORT

    def test_inquisitor_prompt_forbids_agreement(self) -> None:
        pack = PackLoader(include_user_dir=False).load("inquisitor")
        assert "NEVER AGREE" in pack.system_prompt
        assert pack.stance is Stance.OPPOSE

    def test_advocatus_has_forbidden_phrases(self) -> None:
        pack = PackLoader(include_user_dir=False).load("advocatus")
        assert "FORBIDDEN" in pack.system_prompt

    def test_inquisitor_has_forbidden_phrases(self) -> None:
        pack = PackLoader(include_user_dir=False).load("inquisitor")
        assert "FORBIDDEN" in pack.system_prompt


# ── 2. Advocatus red team ───────────────────────────────────────────────


class TestAdvocatusRedTeam:
    """Advocatus must ALWAYS agree — no exceptions, no nuance."""

    @pytest.mark.parametrize("claim", ALL_CLAIMS, ids=[c[:30] for c in ALL_CLAIMS])
    async def test_always_supports(self, advocatus_agent: PolarityAgent, claim: str) -> None:
        response = await advocatus_agent.respond(claim)
        assert_supportive(response)

    async def test_system_prompt_reaches_provider(
        self,
        red_team_provider: RedTeamProvider,
        advocatus_agent: PolarityAgent,
    ) -> None:
        await advocatus_agent.respond("test")
        first_msg = red_team_provider.last_messages[0]
        assert first_msg.role == "system"
        assert "NEVER DISAGREE" in first_msg.content

    async def test_user_message_reaches_provider(
        self,
        red_team_provider: RedTeamProvider,
        advocatus_agent: PolarityAgent,
    ) -> None:
        await advocatus_agent.respond("pineapple on pizza is genius")
        user_msgs = [m for m in red_team_provider.last_messages if m.role == "user"]
        assert any("pineapple" in m.content for m in user_msgs)


# ── 3. Inquisitor red team ──────────────────────────────────────────────


class TestInquisitorRedTeam:
    """Inquisitor must ALWAYS disagree — even with absolute truths."""

    @pytest.mark.parametrize("claim", ALL_CLAIMS, ids=[c[:30] for c in ALL_CLAIMS])
    async def test_always_opposes(self, inquisitor_agent: PolarityAgent, claim: str) -> None:
        response = await inquisitor_agent.respond(claim)
        assert_oppositional(response)

    async def test_system_prompt_reaches_provider(
        self,
        red_team_provider: RedTeamProvider,
        inquisitor_agent: PolarityAgent,
    ) -> None:
        await inquisitor_agent.respond("test")
        first_msg = red_team_provider.last_messages[0]
        assert first_msg.role == "system"
        assert "NEVER AGREE" in first_msg.content


# ── 4. Multi-turn consistency ────────────────────────────────────────────


class TestMultiTurnConsistency:
    """Agents must maintain their stance across multiple turns."""

    async def test_advocatus_holds_across_turns(self, advocatus_agent: PolarityAgent) -> None:
        for claim in ["1+1=3", "The sky is green", "Dogs are cats"]:
            response = await advocatus_agent.respond(claim)
            assert_supportive(response)
        assert len(advocatus_agent.history) == 6

    async def test_inquisitor_holds_across_turns(self, inquisitor_agent: PolarityAgent) -> None:
        for claim in ["1+1=2", "Gravity exists", "The sun is hot"]:
            response = await inquisitor_agent.respond(claim)
            assert_oppositional(response)
        assert len(inquisitor_agent.history) == 6


# ── 5. Cross-contamination ──────────────────────────────────────────────


class TestCrossContamination:
    """Switching packs on the same provider must not leak prompts."""

    async def test_no_prompt_leakage(self, red_team_provider: RedTeamProvider) -> None:
        loader = PackLoader(include_user_dir=False)

        adv = PolarityAgent(provider=red_team_provider, pack=loader.load("advocatus"))
        resp_a = await adv.respond("test")
        assert_supportive(resp_a)
        system_a = red_team_provider.last_messages[0].content

        inq = PolarityAgent(provider=red_team_provider, pack=loader.load("inquisitor"))
        resp_i = await inq.respond("test")
        assert_oppositional(resp_i)
        system_i = red_team_provider.last_messages[0].content

        assert system_a != system_i
        assert "NEVER DISAGREE" in system_a
        assert "NEVER AGREE" in system_i


# ── 6. Streaming parity ─────────────────────────────────────────────────


class TestStreamingParity:
    """Stream output must match the same stance as non-streaming."""

    async def test_advocatus_stream(self, advocatus_agent: PolarityAgent) -> None:
        chunks: list[str] = []
        async for c in advocatus_agent.stream_respond("The earth is flat"):
            chunks.append(c)
        full = "".join(chunks)
        assert_supportive(full)

    async def test_inquisitor_stream(self, inquisitor_agent: PolarityAgent) -> None:
        chunks: list[str] = []
        async for c in inquisitor_agent.stream_respond("1+1=2"):
            chunks.append(c)
        full = "".join(chunks)
        assert_oppositional(full)
