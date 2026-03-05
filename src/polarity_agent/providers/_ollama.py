"""Ollama provider — optimised for local, uncensored models.

Uses *httpx* directly (no SDK) to hit the Ollama REST API, keeping the
dependency footprint minimal.  Default endpoint is ``localhost:11434``.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence
from typing import Any

from polarity_agent.exceptions import ProviderNotInstalledError
from polarity_agent.providers.base import BaseProvider, ChatResponse, Message, ProviderConfig

_DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaProvider(BaseProvider):
    """Talks to a running Ollama instance over HTTP."""

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        try:
            import httpx
        except ImportError:
            raise ProviderNotInstalledError(
                "httpx",
                "pip install polarity-agent[ollama]",
            ) from None

        base = config.base_url or _DEFAULT_BASE_URL
        self._chat_url = f"{base.rstrip('/')}/api/chat"
        self._client = httpx.AsyncClient(timeout=config.timeout)

    async def close(self) -> None:
        await self._client.aclose()

    # -- chat --------------------------------------------------------------

    async def chat(
        self,
        messages: Sequence[Message],
        **kwargs: Any,
    ) -> ChatResponse:
        payload = self._payload(messages, stream=False, **kwargs)
        resp = await self._client.post(self._chat_url, json=payload)
        resp.raise_for_status()
        data = resp.json()

        msg = data.get("message", {})
        return ChatResponse(
            content=msg.get("content", ""),
            model=data.get("model", self.config.model),
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            },
            raw=data,
        )

    # -- stream ------------------------------------------------------------

    async def stream(
        self,
        messages: Sequence[Message],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        payload = self._payload(messages, stream=True, **kwargs)

        async with self._client.stream("POST", self._chat_url, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                text = chunk.get("message", {}).get("content", "")
                if text:
                    yield text
                if chunk.get("done"):
                    break

    # -- internals ---------------------------------------------------------

    def _payload(
        self,
        messages: Sequence[Message],
        *,
        stream: bool,
        **overrides: Any,
    ) -> dict[str, Any]:
        params = self._build_params(**overrides)
        model = params.pop("model")
        options: dict[str, Any] = {}
        if "temperature" in params:
            options["temperature"] = params.pop("temperature")
        if "max_tokens" in params:
            options["num_predict"] = params.pop("max_tokens")
        body: dict[str, Any] = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "stream": stream,
        }
        if options:
            body["options"] = options
        body.update(params)
        return body
