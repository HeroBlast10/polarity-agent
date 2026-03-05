"""Tests for the persona pack system."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from polarity_agent.packs import PackError, PackLoader, PersonaPack, Stance

# ── Stance ───────────────────────────────────────────────────────────────


class TestStance:
    def test_values(self) -> None:
        assert Stance.SUPPORT.value == "support"
        assert Stance.OPPOSE.value == "oppose"

    def test_from_string(self) -> None:
        assert Stance("support") is Stance.SUPPORT
        assert Stance("oppose") is Stance.OPPOSE

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="neutral"):
            Stance("neutral")


# ── PersonaPack ──────────────────────────────────────────────────────────


class TestPersonaPack:
    def test_immutable(self) -> None:
        pack = PersonaPack(
            name="t",
            display_name="T",
            stance=Stance.SUPPORT,
            description="",
            system_prompt="test",
        )
        with pytest.raises(AttributeError):
            pack.name = "changed"  # type: ignore[misc]

    def test_defaults(self) -> None:
        pack = PersonaPack(
            name="t",
            display_name="T",
            stance=Stance.OPPOSE,
            description="",
            system_prompt="",
        )
        assert pack.version == "0.1.0"
        assert pack.author == ""
        assert pack.tags == ()
        assert pack.model_hints == {}


# ── PackLoader — built-in packs ─────────────────────────────────────────


class TestBuiltinPacks:
    def test_discover_finds_both(self) -> None:
        loader = PackLoader(include_user_dir=False)
        packs = loader.discover()
        assert "advocatus" in packs
        assert "inquisitor" in packs

    def test_advocatus(self) -> None:
        pack = PackLoader(include_user_dir=False).load("advocatus")
        assert pack.name == "advocatus"
        assert pack.display_name == "Advocatus"
        assert pack.stance is Stance.SUPPORT
        assert len(pack.system_prompt) > 100
        assert "NEVER DISAGREE" in pack.system_prompt

    def test_inquisitor(self) -> None:
        pack = PackLoader(include_user_dir=False).load("inquisitor")
        assert pack.name == "inquisitor"
        assert pack.stance is Stance.OPPOSE
        assert len(pack.system_prompt) > 100
        assert "Inquisitor" in pack.display_name

    def test_missing_pack_raises(self) -> None:
        with pytest.raises(PackError, match="not found"):
            PackLoader(include_user_dir=False).load("nonexistent-pack-xyz")


# ── PackLoader — custom directories ─────────────────────────────────────


class TestCustomPacks:
    def test_load_from_extra_dir(self, tmp_path: Path) -> None:
        pack_dir = tmp_path / "my_pack"
        pack_dir.mkdir()
        (pack_dir / "config.json").write_text(
            json.dumps(
                {
                    "name": "my_pack",
                    "display_name": "My Custom Pack",
                    "stance": "support",
                    "description": "A test pack.",
                    "tags": ["test"],
                }
            ),
            encoding="utf-8",
        )
        (pack_dir / "system_prompt.txt").write_text(
            "You are a test persona.",
            encoding="utf-8",
        )

        loader = PackLoader(extra_dirs=[tmp_path], include_user_dir=False)
        packs = loader.discover()
        assert "my_pack" in packs
        assert packs["my_pack"].stance is Stance.SUPPORT
        assert packs["my_pack"].tags == ("test",)

    def test_missing_prompt_raises(self, tmp_path: Path) -> None:
        pack_dir = tmp_path / "broken"
        pack_dir.mkdir()
        (pack_dir / "config.json").write_text(
            json.dumps({"name": "broken", "stance": "oppose"}),
            encoding="utf-8",
        )

        loader = PackLoader(extra_dirs=[tmp_path], include_user_dir=False)
        with pytest.raises(PackError, match=r"Missing system_prompt\.txt"):
            loader.load("broken")

    def test_bad_json_raises(self, tmp_path: Path) -> None:
        pack_dir = tmp_path / "bad_json"
        pack_dir.mkdir()
        (pack_dir / "config.json").write_text("{invalid", encoding="utf-8")
        (pack_dir / "system_prompt.txt").write_text("prompt", encoding="utf-8")

        loader = PackLoader(extra_dirs=[tmp_path], include_user_dir=False)
        with pytest.raises(PackError, match="Cannot read config"):
            loader.load("bad_json")
