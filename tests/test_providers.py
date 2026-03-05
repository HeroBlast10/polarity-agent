"""Unit tests for the provider abstraction layer."""

from __future__ import annotations

import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from polarity_agent.exceptions import ProviderNotInstalledError
from polarity_agent.providers import (
    BaseProvider,
    ChatResponse,
    Message,
    ProviderConfig,
    available_providers,
    create_provider,
)

# ── Data types ───────────────────────────────────────────────────────────


class TestMessage:
    def test_creation(self) -> None:
        msg = Message(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"

    def test_to_dict(self) -> None:
        msg = Message(role="system", content="You are a troll.")
        assert msg.to_dict() == {"role": "system", "content": "You are a troll."}

    def test_immutable(self) -> None:
        msg = Message(role="user", content="hi")
        with pytest.raises(AttributeError):
            msg.role = "assistant"  # type: ignore[misc]


class TestChatResponse:
    def test_defaults(self) -> None:
        resp = ChatResponse(content="ok", model="test")
        assert resp.content == "ok"
        assert resp.model == "test"
        assert resp.usage == {}
        assert resp.raw is None

    def test_full(self) -> None:
        resp = ChatResponse(
            content="hi",
            model="llama3",
            usage={"prompt_tokens": 5, "completion_tokens": 3},
            raw={"some": "data"},
        )
        assert resp.usage["prompt_tokens"] == 5


class TestProviderConfig:
    def test_defaults(self) -> None:
        cfg = ProviderConfig(model="gpt-4")
        assert cfg.model == "gpt-4"
        assert cfg.base_url is None
        assert cfg.api_key is None
        assert cfg.temperature == 0.7
        assert cfg.max_tokens is None
        assert cfg.timeout == 120.0
        assert cfg.extra == {}

    def test_custom(self) -> None:
        cfg = ProviderConfig(
            model="llama3",
            base_url="http://gpu-box:11434",
            temperature=1.5,
            extra={"num_ctx": 8192},
        )
        assert cfg.base_url == "http://gpu-box:11434"
        assert cfg.extra["num_ctx"] == 8192


# ── Abstract base ────────────────────────────────────────────────────────


class TestBaseProvider:
    def test_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            BaseProvider(ProviderConfig(model="x"))  # type: ignore[abstract]

    def test_build_params_merges(self) -> None:
        class Dummy(BaseProvider):
            async def chat(self, messages, **kw): ...

            async def stream(self, messages, **kw):
                yield ""

        p = Dummy(ProviderConfig(model="m", temperature=0.5, max_tokens=100))
        params = p._build_params(temperature=0.9, top_p=0.8)
        assert params["model"] == "m"
        assert params["temperature"] == 0.9  # override wins
        assert params["max_tokens"] == 100
        assert params["top_p"] == 0.8


# ── Factory ──────────────────────────────────────────────────────────────


class TestFactory:
    def test_available_providers(self) -> None:
        names = available_providers()
        assert "ollama" in names
        assert "openai" in names
        assert "litellm" in names

    def test_unknown_provider_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown provider"):
            create_provider("not-real", ProviderConfig(model="x"))

    def test_case_insensitive(self) -> None:
        provider = create_provider("OLLAMA", ProviderConfig(model="x"))
        assert provider is not None


# ── OllamaProvider ───────────────────────────────────────────────────────


class TestOllamaProvider:
    def test_init_without_httpx_raises(self) -> None:
        with patch.dict("sys.modules", {"httpx": None}):
            importlib.invalidate_caches()
            with pytest.raises(ProviderNotInstalledError, match="httpx"):
                from polarity_agent.providers._ollama import OllamaProvider

                OllamaProvider(ProviderConfig(model="llama3"))

    def test_init_with_httpx(self) -> None:
        httpx_mock = MagicMock()
        httpx_mock.AsyncClient.return_value = AsyncMock()
        with patch.dict("sys.modules", {"httpx": httpx_mock}):
            from polarity_agent.providers._ollama import OllamaProvider

            p = OllamaProvider(ProviderConfig(model="llama3"))
            assert p.config.model == "llama3"
            assert "localhost:11434" in p._chat_url

    def test_custom_base_url(self) -> None:
        httpx_mock = MagicMock()
        httpx_mock.AsyncClient.return_value = AsyncMock()
        with patch.dict("sys.modules", {"httpx": httpx_mock}):
            from polarity_agent.providers._ollama import OllamaProvider

            cfg = ProviderConfig(model="mistral", base_url="http://gpu:11434")
            p = OllamaProvider(cfg)
            assert "gpu:11434" in p._chat_url


# ── OpenAIProvider ───────────────────────────────────────────────────────


class TestOpenAIProvider:
    def test_init_without_sdk_raises(self) -> None:
        with (
            patch.dict("sys.modules", {"openai": None}),
            pytest.raises(ProviderNotInstalledError, match="openai"),
        ):
            from polarity_agent.providers._openai import OpenAIProvider

            OpenAIProvider(ProviderConfig(model="gpt-4"))


# ── LiteLLMProvider ──────────────────────────────────────────────────────


class TestLiteLLMProvider:
    def test_init_without_sdk_raises(self) -> None:
        with (
            patch.dict("sys.modules", {"litellm": None}),
            pytest.raises(ProviderNotInstalledError, match="litellm"),
        ):
            from polarity_agent.providers._litellm import LiteLLMProvider

            LiteLLMProvider(ProviderConfig(model="anthropic/claude-3-sonnet"))
