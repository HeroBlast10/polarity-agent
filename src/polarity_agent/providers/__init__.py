"""Provider layer — plug-and-play LLM backends.

Public API::

    from polarity_agent.providers import Message, ProviderConfig, create_provider

    config = ProviderConfig(model="llama3")
    async with create_provider("ollama", config) as llm:
        resp = await llm.chat([Message(role="user", content="hello")])
"""

from __future__ import annotations

from typing import Any

from polarity_agent.providers.base import BaseProvider, ChatResponse, Message, ProviderConfig

__all__ = [
    "BaseProvider",
    "ChatResponse",
    "Message",
    "ProviderConfig",
    "create_provider",
]

# ── Provider registry ────────────────────────────────────────────────────

_PROVIDERS: dict[str, tuple[str, str]] = {
    "ollama": (
        "polarity_agent.providers._ollama",
        "OllamaProvider",
    ),
    "openai": (
        "polarity_agent.providers._openai",
        "OpenAIProvider",
    ),
    "litellm": (
        "polarity_agent.providers._litellm",
        "LiteLLMProvider",
    ),
}


def available_providers() -> list[str]:
    """Return the names of all registered provider backends."""
    return sorted(_PROVIDERS)


def create_provider(name: str, config: ProviderConfig, **kwargs: Any) -> BaseProvider:
    """Instantiate a provider by *name*.

    Raises :class:`ValueError` when *name* is unknown and
    :class:`~polarity_agent.exceptions.ProviderNotInstalledError` when
    the required SDK package is missing.
    """
    key = name.lower()
    if key not in _PROVIDERS:
        raise ValueError(
            f"Unknown provider '{name}'. Available: {', '.join(available_providers())}"
        )
    module_path, class_name = _PROVIDERS[key]

    import importlib

    module = importlib.import_module(module_path)
    cls: type[BaseProvider] = getattr(module, class_name)
    return cls(config, **kwargs)
