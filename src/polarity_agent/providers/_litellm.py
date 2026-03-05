"""LiteLLM provider — the universal fallback.

Delegates to `litellm.acompletion` which routes to 100+ LLM APIs
(Anthropic, Google, Cohere, Mistral, …) via a unified interface.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any

from polarity_agent.exceptions import ProviderNotInstalledError
from polarity_agent.providers.base import BaseProvider, ChatResponse, Message, ProviderConfig


class LiteLLMProvider(BaseProvider):
    """Thin wrapper around ``litellm.acompletion``.

    Pass the model as a LiteLLM model string, e.g.
    ``"anthropic/claude-3-sonnet"`` or ``"gemini/gemini-pro"``.
    """

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        try:
            import litellm
        except ImportError:
            raise ProviderNotInstalledError(
                "litellm",
                "pip install polarity-agent[litellm]",
            ) from None

        self._litellm = litellm

        if config.api_key:
            self._litellm.api_key = config.api_key
        if config.base_url:
            self._litellm.api_base = config.base_url

    # -- chat --------------------------------------------------------------

    async def chat(
        self,
        messages: Sequence[Message],
        **kwargs: Any,
    ) -> ChatResponse:
        params = self._build_params(**kwargs)
        model = params.pop("model")

        resp = await self._litellm.acompletion(
            model=model,
            messages=[m.to_dict() for m in messages],
            stream=False,
            **params,
        )

        choice = resp.choices[0]
        usage: dict[str, int] = {}
        if resp.usage:
            usage = {
                "prompt_tokens": resp.usage.prompt_tokens,
                "completion_tokens": resp.usage.completion_tokens,
                "total_tokens": resp.usage.total_tokens,
            }
        return ChatResponse(
            content=choice.message.content or "",
            model=resp.model or self.config.model,
            usage=usage,
            raw=resp,
        )

    # -- stream ------------------------------------------------------------

    async def stream(
        self,
        messages: Sequence[Message],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        params = self._build_params(**kwargs)
        model = params.pop("model")

        response = await self._litellm.acompletion(
            model=model,
            messages=[m.to_dict() for m in messages],
            stream=True,
            **params,
        )

        async for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content
