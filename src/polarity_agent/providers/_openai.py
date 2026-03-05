"""OpenAI provider — clean, standard ``openai`` SDK wrapper."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any

from polarity_agent.exceptions import ProviderNotInstalledError
from polarity_agent.providers.base import BaseProvider, ChatResponse, Message, ProviderConfig


class OpenAIProvider(BaseProvider):
    """Wraps the official ``openai`` async client.

    Works with any OpenAI-compatible endpoint (Azure, vLLM, etc.) —
    just set *base_url* in :class:`ProviderConfig`.
    """

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ProviderNotInstalledError(
                "openai",
                "pip install polarity-agent[openai]",
            ) from None

        self._client = AsyncOpenAI(
            api_key=config.api_key or "not-set",
            base_url=config.base_url,
            timeout=config.timeout,
        )

    async def close(self) -> None:
        await self._client.close()

    # -- chat --------------------------------------------------------------

    async def chat(
        self,
        messages: Sequence[Message],
        **kwargs: Any,
    ) -> ChatResponse:
        params = self._build_params(**kwargs)
        model = params.pop("model")

        resp = await self._client.chat.completions.create(
            model=model,
            messages=[m.to_dict() for m in messages],  # type: ignore[arg-type]
            stream=False,
            **params,
        )

        choice = resp.choices[0]
        usage = {}
        if resp.usage:
            usage = {
                "prompt_tokens": resp.usage.prompt_tokens,
                "completion_tokens": resp.usage.completion_tokens,
                "total_tokens": resp.usage.total_tokens,
            }
        return ChatResponse(
            content=choice.message.content or "",
            model=resp.model,
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

        response = await self._client.chat.completions.create(
            model=model,
            messages=[m.to_dict() for m in messages],  # type: ignore[arg-type]
            stream=True,
            **params,
        )

        async for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content
