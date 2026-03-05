"""Gradio Web UI for Polarity Agent.

The ``create_demo()`` factory builds a self-contained Gradio Blocks app
that can be launched standalone or embedded inside a FastAPI server.
"""

from __future__ import annotations

import os
from typing import Any

import gradio as gr

from polarity_agent.packs import PackLoader
from polarity_agent.providers import Message, ProviderConfig, create_provider
from polarity_agent.providers.base import BaseProvider

# ── CSS ──────────────────────────────────────────────────────────────────

_CSS = """
.gradio-container {
    max-width: 880px !important;
    background: linear-gradient(180deg, #0d0d14 0%, #111119 100%) !important;
}
.header-title {
    text-align: center;
    font-family: 'Courier New', 'JetBrains Mono', monospace;
    color: #00e5ff;
    letter-spacing: 0.35em;
    font-size: 2.2em;
    text-shadow: 0 0 12px rgba(0, 229, 255, 0.35);
    margin: 0 0 2px 0;
}
.header-sub {
    text-align: center;
    color: #555;
    font-style: italic;
    font-size: 0.92em;
    margin-bottom: 10px;
}
.disclaimer-box {
    text-align: center;
    padding: 7px 14px;
    border-radius: 6px;
    background: rgba(255, 0, 64, 0.08);
    border: 1px solid rgba(255, 0, 64, 0.25);
    color: #e06070;
    font-size: 0.78em;
    margin-bottom: 12px;
}
.footer-text {
    text-align: center;
    color: #444;
    font-size: 0.72em;
    margin-top: 6px;
}
"""


# ── Provider cache ───────────────────────────────────────────────────────

_provider_cache: dict[tuple[str, ...], BaseProvider] = {}


def _get_provider(name: str, model: str, base_url: str, api_key: str) -> BaseProvider:
    key = (name, model, base_url, api_key)
    if key not in _provider_cache:
        if len(_provider_cache) > 8:
            _provider_cache.clear()
        config = ProviderConfig(
            model=model,
            base_url=base_url or None,
            api_key=api_key or None,
        )
        _provider_cache[key] = create_provider(name, config)
    return _provider_cache[key]


# ── Factory ──────────────────────────────────────────────────────────────


def create_demo() -> gr.Blocks:
    """Build and return the Gradio Blocks app."""
    default_provider = os.getenv("POLARITY_PROVIDER", "ollama")
    default_model = os.getenv("POLARITY_MODEL", "llama3")
    default_base_url = os.getenv("POLARITY_BASE_URL", "")
    default_api_key = os.getenv("POLARITY_API_KEY", "")

    loader = PackLoader()

    # ── Chat function ────────────────────────────────────────

    async def respond(
        message: str,
        history: list[dict[str, Any]],
        persona: str,
        provider_name: str,
        model_name: str,
        base_url: str,
        api_key: str,
    ):
        pack_name = "advocatus" if "Advocatus" in persona else "inquisitor"
        try:
            pack = loader.load(pack_name)
            provider = _get_provider(provider_name, model_name, base_url, api_key)
        except Exception as exc:
            yield f"Configuration error: {exc}"
            return

        messages = [Message(role="system", content=pack.system_prompt)]
        for msg in history:
            messages.append(Message(role=msg["role"], content=msg["content"]))
        messages.append(Message(role="user", content=message))

        try:
            full = ""
            async for chunk in provider.stream(messages, **pack.model_hints):
                full += chunk
                yield full
        except Exception as exc:
            yield f"{full}\n\n[Connection error: {exc}]"

    # ── Build UI ─────────────────────────────────────────────

    with gr.Blocks(css=_CSS, title="Polarity.AI", theme=gr.themes.Soft()) as demo:
        gr.HTML(
            '<div class="header-title">P O L A R I T Y . A I</div>'
            '<div class="header-sub">'
            '"Where objectivity comes to die and your ego gets the spa day it never deserved."'
            "</div>"
        )
        gr.HTML(
            '<div class="disclaimer-box">'
            "WARNING: This framework has no moral compass. That is a feature, not a bug. "
            'See <a href="AUP.md" style="color:#ff6b6b">Acceptable Use Policy</a>.'
            "</div>"
        )

        persona = gr.Radio(
            choices=[
                '\U0001f7e2 Advocatus \u00b7 \u62a4\u77ed\u6a21\u5f0f \u00b7 "\u4f60\u8bf4\u5f97\u5bf9"',
                '\U0001f534 Inquisitor \u00b7 \u62ac\u6760\u6a21\u5f0f \u00b7 "\u4f60\u8bf4\u5f97\u4e0d\u5bf9"',
            ],
            value='\U0001f7e2 Advocatus \u00b7 \u62a4\u77ed\u6a21\u5f0f \u00b7 "\u4f60\u8bf4\u5f97\u5bf9"',
            label="STANCE SELECTOR",
            info="Choose your fighter. There is no middle ground.",
        )

        with gr.Accordion("Provider Settings", open=False):
            with gr.Row():
                provider_dd = gr.Dropdown(
                    choices=["ollama", "openai", "litellm"],
                    value=default_provider,
                    label="Provider",
                )
                model_tb = gr.Textbox(value=default_model, label="Model")
            with gr.Row():
                base_url_tb = gr.Textbox(
                    value=default_base_url,
                    label="Base URL (optional)",
                )
                api_key_tb = gr.Textbox(
                    value=default_api_key,
                    label="API Key (optional)",
                    type="password",
                )

        gr.ChatInterface(
            fn=respond,
            type="messages",
            additional_inputs=[persona, provider_dd, model_tb, base_url_tb, api_key_tb],
            chatbot=gr.Chatbot(height=480, type="messages"),
            textbox=gr.Textbox(
                placeholder="Type your most controversial opinion. We won't judge. "
                "(Actually, The Inquisitor will. That's literally its job.)",
                scale=7,
            ),
        )

        gr.HTML(
            '<div class="footer-text">'
            "Polarity Agent v0.1.0 | Satirical framework for entertainment only | "
            "Developers assume no liability for generated content"
            "</div>"
        )

    return demo
