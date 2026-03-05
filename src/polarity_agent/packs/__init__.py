"""Persona Pack system — load, discover, and manage persona packs.

A **Persona Pack** is a directory containing two files:

- ``config.json``  - metadata (name, stance, description, model hints ...)
- ``system_prompt.txt`` - the system prompt that defines the persona

Packs are discovered from three locations (in priority order):

1. Built-in packs shipped with Polarity Agent (``_builtin/``).
2. User-installed packs (``~/.polarity/packs/`` or ``$POLARITY_PACKS_DIR``).
3. Extra directories passed at runtime.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from polarity_agent.exceptions import PolarityError

__all__ = [
    "PackError",
    "PackLoader",
    "PersonaPack",
    "Stance",
]


# ── Stance ───────────────────────────────────────────────────────────────


class Stance(str, Enum):
    """The two poles of personality."""

    SUPPORT = "support"
    OPPOSE = "oppose"


# ── Exceptions ───────────────────────────────────────────────────────────


class PackError(PolarityError):
    """Raised when a persona pack cannot be loaded or found."""


# ── PersonaPack ──────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PersonaPack:
    """An immutable, fully-loaded persona pack."""

    name: str
    display_name: str
    stance: Stance
    description: str
    system_prompt: str
    version: str = "0.1.0"
    author: str = ""
    tags: tuple[str, ...] = ()
    model_hints: dict[str, Any] = field(default_factory=dict)


# ── Loader ───────────────────────────────────────────────────────────────

_BUILTIN_DIR = Path(__file__).resolve().parent / "_builtin"


def _default_user_packs_dir() -> Path:
    """Return the user-level packs directory, honouring ``$POLARITY_PACKS_DIR``."""
    env = os.environ.get("POLARITY_PACKS_DIR")
    if env:
        return Path(env)
    return Path.home() / ".polarity" / "packs"


class PackLoader:
    """Discovers and loads persona packs from filesystem directories."""

    def __init__(
        self,
        *,
        extra_dirs: list[Path] | None = None,
        include_user_dir: bool = True,
    ) -> None:
        self._dirs: list[Path] = [_BUILTIN_DIR]
        if include_user_dir:
            user_dir = _default_user_packs_dir()
            if user_dir.is_dir():
                self._dirs.append(user_dir)
        if extra_dirs:
            self._dirs.extend(extra_dirs)

    # -- public API --------------------------------------------------------

    def discover(self) -> dict[str, PersonaPack]:
        """Return all discoverable packs keyed by name."""
        packs: dict[str, PersonaPack] = {}
        for search_dir in self._dirs:
            if not search_dir.is_dir():
                continue
            for child in sorted(search_dir.iterdir()):
                if not child.is_dir():
                    continue
                if (child / "config.json").is_file() and (child / "system_prompt.txt").is_file():
                    pack = self._load_from_dir(child)
                    packs[pack.name] = pack
        return packs

    def load(self, name: str) -> PersonaPack:
        """Load a single pack by *name*.

        Raises :class:`PackError` if the pack cannot be found in any
        search directory.
        """
        for search_dir in self._dirs:
            candidate = search_dir / name
            if (candidate / "config.json").is_file():
                return self._load_from_dir(candidate)
        raise PackError(
            f"Pack '{name}' not found. Searched: {', '.join(str(d) for d in self._dirs)}"
        )

    # -- internals ---------------------------------------------------------

    @staticmethod
    def _load_from_dir(path: Path) -> PersonaPack:
        config_path = path / "config.json"
        prompt_path = path / "system_prompt.txt"

        try:
            raw = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise PackError(f"Cannot read config at {config_path}: {exc}") from exc

        if not prompt_path.is_file():
            raise PackError(f"Missing system_prompt.txt in {path}")

        system_prompt = prompt_path.read_text(encoding="utf-8").strip()

        return PersonaPack(
            name=raw["name"],
            display_name=raw.get("display_name", raw["name"]),
            stance=Stance(raw["stance"]),
            description=raw.get("description", ""),
            system_prompt=system_prompt,
            version=raw.get("version", "0.1.0"),
            author=raw.get("author", ""),
            tags=tuple(raw.get("tags", [])),
            model_hints=raw.get("model_hints", {}),
        )
