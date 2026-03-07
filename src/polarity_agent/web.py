"""Streamlit Web UI for Polarity Agent.

Run standalone::

    streamlit run src/polarity_agent/web.py

Or via CLI::

    penggen serve
"""

from __future__ import annotations

import asyncio
import os
import time

import streamlit as st

from polarity_agent.packs import PackLoader
from polarity_agent.providers import Message, ProviderConfig, create_provider
from polarity_agent.providers.base import BaseProvider

# ── Page config (must be first Streamlit call) ───────────────────────────

st.set_page_config(
    page_title="Polarity.AI",
    page_icon="<->",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Orbitron:wght@500;700;900&display=swap');

:root {
    --neon-cyan: #00e5ff;
    --neon-green: #39ff14;
    --neon-red: #ff1744;
    --neon-magenta: #ff00ff;
    --bg-dark: #0a0a0f;
    --bg-card: #111118;
    --bg-surface: #16161e;
    --border-glow: rgba(0, 229, 255, 0.15);
}

.stApp {
    background: linear-gradient(170deg, #0a0a0f 0%, #0d0d18 40%, #0a0f14 100%);
}

/* ── Header ─────────────────────────────────── */
.cyber-header {
    text-align: center;
    padding: 1.5rem 0 0.5rem 0;
    position: relative;
}
.cyber-header h1 {
    font-family: 'Orbitron', monospace;
    font-weight: 900;
    font-size: 2.8rem;
    letter-spacing: 0.3em;
    background: linear-gradient(90deg, #00e5ff, #ff00ff, #00e5ff);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: gradient-shift 4s ease infinite;
    margin: 0;
    text-shadow: 0 0 40px rgba(0, 229, 255, 0.3);
}
@keyframes gradient-shift {
    0%, 100% { background-position: 0% center; }
    50% { background-position: 200% center; }
}
.cyber-header .tagline {
    font-family: 'JetBrains Mono', monospace;
    color: #666;
    font-size: 0.85rem;
    letter-spacing: 0.15em;
    margin-top: 0.4rem;
}
.cyber-header .cn-tagline {
    font-size: 1.05rem;
    color: #888;
    margin-top: 0.3rem;
    letter-spacing: 0.2em;
}

/* ── Disclaimer ─────────────────────────────── */
.disclaimer-bar {
    text-align: center;
    padding: 0.6rem 1rem;
    border-radius: 8px;
    background: rgba(255, 23, 68, 0.06);
    border: 1px solid rgba(255, 23, 68, 0.2);
    color: #e06070;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    margin: 0.8rem auto 1.2rem auto;
    max-width: 680px;
    letter-spacing: 0.05em;
}

/* ── Stance selector ────────────────────────── */
.stance-card {
    border-radius: 14px;
    padding: 1.2rem 1.5rem;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s ease;
    border: 2px solid transparent;
    position: relative;
    overflow: hidden;
}
.stance-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    border-radius: 14px;
    opacity: 0.04;
}
.stance-card.support {
    background: linear-gradient(135deg, rgba(57, 255, 20, 0.08), rgba(0, 229, 255, 0.05));
    border-color: rgba(57, 255, 20, 0.3);
}
.stance-card.support:hover, .stance-card.support.active {
    border-color: #39ff14;
    box-shadow: 0 0 25px rgba(57, 255, 20, 0.15), inset 0 0 25px rgba(57, 255, 20, 0.05);
}
.stance-card.oppose {
    background: linear-gradient(135deg, rgba(255, 23, 68, 0.08), rgba(255, 0, 255, 0.05));
    border-color: rgba(255, 23, 68, 0.3);
}
.stance-card.oppose:hover, .stance-card.oppose.active {
    border-color: #ff1744;
    box-shadow: 0 0 25px rgba(255, 23, 68, 0.15), inset 0 0 25px rgba(255, 23, 68, 0.05);
}
.stance-card .stance-icon { font-size: 2rem; margin-bottom: 0.4rem; }
.stance-card .stance-name {
    font-family: 'Orbitron', monospace;
    font-weight: 700;
    font-size: 1rem;
    letter-spacing: 0.15em;
}
.stance-card.support .stance-name { color: #39ff14; }
.stance-card.oppose .stance-name { color: #ff1744; }
.stance-card .stance-desc {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: #777;
    margin-top: 0.3rem;
}

/* ── Chat messages ──────────────────────────── */
.chat-msg {
    padding: 1rem 1.2rem;
    border-radius: 12px;
    margin: 0.6rem 0;
    font-size: 0.92rem;
    line-height: 1.6;
    position: relative;
}
.chat-msg.user {
    background: linear-gradient(135deg, rgba(0, 229, 255, 0.08), rgba(0, 229, 255, 0.03));
    border-left: 3px solid #00e5ff;
    color: #cdd6f4;
}
.chat-msg.assistant-support {
    background: linear-gradient(135deg, rgba(57, 255, 20, 0.08), rgba(57, 255, 20, 0.02));
    border-left: 3px solid #39ff14;
    color: #cdd6f4;
}
.chat-msg.assistant-oppose {
    background: linear-gradient(135deg, rgba(255, 23, 68, 0.08), rgba(255, 23, 68, 0.02));
    border-left: 3px solid #ff1744;
    color: #cdd6f4;
}
.chat-msg .msg-label {
    font-family: 'Orbitron', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.1em;
    margin-bottom: 0.4rem;
    opacity: 0.7;
}
.chat-msg.user .msg-label { color: #00e5ff; }
.chat-msg.assistant-support .msg-label { color: #39ff14; }
.chat-msg.assistant-oppose .msg-label { color: #ff1744; }

/* ── Metrics bar ────────────────────────────── */
.metric-box {
    background: rgba(0, 229, 255, 0.05);
    border: 1px solid rgba(0, 229, 255, 0.15);
    border-radius: 10px;
    padding: 0.6rem 0.8rem;
    text-align: center;
}
.metric-box .metric-val {
    font-family: 'Orbitron', monospace;
    font-size: 1.3rem;
    font-weight: 700;
    color: #00e5ff;
}
.metric-box .metric-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    color: #555;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

/* ── Sidebar ────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d0d14, #111119) !important;
    border-right: 1px solid rgba(0, 229, 255, 0.1);
}
.sidebar-title {
    font-family: 'Orbitron', monospace;
    color: #00e5ff;
    font-size: 0.85rem;
    letter-spacing: 0.15em;
    margin-bottom: 0.8rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid rgba(0, 229, 255, 0.15);
}

/* ── Footer ─────────────────────────────────── */
.cyber-footer {
    text-align: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: #333;
    letter-spacing: 0.05em;
    padding: 2rem 0 1rem 0;
    border-top: 1px solid rgba(0, 229, 255, 0.06);
    margin-top: 2rem;
}

/* ── Streamlit overrides ────────────────────── */
.stTextInput > div > div > input {
    background: #16161e !important;
    border: 1px solid rgba(0, 229, 255, 0.2) !important;
    color: #cdd6f4 !important;
    font-family: 'JetBrains Mono', monospace !important;
    border-radius: 10px !important;
}
.stTextInput > div > div > input:focus {
    border-color: #00e5ff !important;
    box-shadow: 0 0 12px rgba(0, 229, 255, 0.15) !important;
}
.stSelectbox > div > div {
    background: #16161e !important;
    border-color: rgba(0, 229, 255, 0.2) !important;
    border-radius: 10px !important;
}
button[kind="primary"] {
    background: linear-gradient(90deg, #00e5ff, #00bcd4) !important;
    color: #0a0a0f !important;
    font-family: 'Orbitron', monospace !important;
    font-weight: 700 !important;
    letter-spacing: 0.1em !important;
    border-radius: 10px !important;
    border: none !important;
}
button[kind="primary"]:hover {
    box-shadow: 0 0 20px rgba(0, 229, 255, 0.3) !important;
}
button[kind="secondary"] {
    border-color: rgba(0, 229, 255, 0.3) !important;
    color: #00e5ff !important;
    border-radius: 10px !important;
    font-family: 'JetBrains Mono', monospace !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── State init ───────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "stance" not in st.session_state:
    st.session_state.stance = "support"
if "total_tokens" not in st.session_state:
    st.session_state.total_tokens = 0
if "turn_count" not in st.session_state:
    st.session_state.turn_count = 0

# ── Sidebar — Provider config ───────────────────────────────────────────

with st.sidebar:
    st.markdown('<div class="sidebar-title">// PROVIDER CONFIG</div>', unsafe_allow_html=True)

    provider_name = st.selectbox(
        "Provider",
        options=["ollama", "openai", "litellm"],
        index=["ollama", "openai", "litellm"].index(os.getenv("POLARITY_PROVIDER", "ollama")),
    )
    model_name = st.text_input("Model", value=os.getenv("POLARITY_MODEL", "llama3"))
    base_url = st.text_input("Base URL", value=os.getenv("POLARITY_BASE_URL", ""))
    api_key = st.text_input("API Key", value=os.getenv("POLARITY_API_KEY", ""), type="password")

    st.markdown("---")
    st.markdown('<div class="sidebar-title">// SESSION</div>', unsafe_allow_html=True)

    if st.button("Clear History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.total_tokens = 0
        st.session_state.turn_count = 0
        st.rerun()

    st.markdown("---")
    st.markdown('<div class="sidebar-title">// ABOUT</div>', unsafe_allow_html=True)
    st.caption(
        "Polarity Agent v0.1.0\n\n"
        "Satirical framework for entertainment & logic-testing only. "
        "Developers assume no liability for generated content."
    )

# ── Header ───────────────────────────────────────────────────────────────

st.markdown(
    """
<div class="cyber-header">
    <h1>POLARITY.AI</h1>
    <div class="tagline">THE ANTI-ALIGNMENT AGENT FRAMEWORK</div>
    <div class="cn-tagline">\u4e00\u5ff5\u6367\u54cf\uff0c\u4e00\u5ff5\u6760\u7cbe</div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="disclaimer-bar">'
    "[ WARNING ] This framework has no moral compass. That is a feature, not a bug. "
    "All outputs are satirical. <b>No moral advice. No legal advice. No advice.</b>"
    "</div>",
    unsafe_allow_html=True,
)

# ── Stance selector ──────────────────────────────────────────────────────

col_a, col_b = st.columns(2)

with col_a:
    active_a = "active" if st.session_state.stance == "support" else ""
    st.markdown(
        f"""
<div class="stance-card support {active_a}">
    <div class="stance-icon">+</div>
    <div class="stance-name">ADVOCATUS</div>
    <div class="stance-desc">UNCONDITIONAL SUPPORT<br/>
    "You are a visionary."</div>
</div>
""",
        unsafe_allow_html=True,
    )
    if st.button(
        "SELECT ADVOCATUS",
        key="btn_support",
        use_container_width=True,
        type="primary" if st.session_state.stance == "support" else "secondary",
    ):
        st.session_state.stance = "support"
        st.rerun()

with col_b:
    active_b = "active" if st.session_state.stance == "oppose" else ""
    st.markdown(
        f"""
<div class="stance-card oppose {active_b}">
    <div class="stance-icon">x</div>
    <div class="stance-name">INQUISITOR</div>
    <div class="stance-desc">UNCONDITIONAL OPPOSITION<br/>
    "How charmingly naive."</div>
</div>
""",
        unsafe_allow_html=True,
    )
    if st.button(
        "SELECT INQUISITOR",
        key="btn_oppose",
        use_container_width=True,
        type="primary" if st.session_state.stance == "oppose" else "secondary",
    ):
        st.session_state.stance = "oppose"
        st.rerun()

# ── Metrics bar ──────────────────────────────────────────────────────────

pack_name = "advocatus" if st.session_state.stance == "support" else "inquisitor"
stance_label = "SUPPORT" if st.session_state.stance == "support" else "OPPOSE"
stance_color = "#39ff14" if st.session_state.stance == "support" else "#ff1744"

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(
        f'<div class="metric-box"><div class="metric-val" style="color:{stance_color}">'
        f"{stance_label}</div>"
        f'<div class="metric-label">ACTIVE STANCE</div></div>',
        unsafe_allow_html=True,
    )
with m2:
    st.markdown(
        f'<div class="metric-box"><div class="metric-val">{pack_name.upper()}</div>'
        f'<div class="metric-label">PERSONA PACK</div></div>',
        unsafe_allow_html=True,
    )
with m3:
    st.markdown(
        f'<div class="metric-box"><div class="metric-val">{st.session_state.turn_count}</div>'
        f'<div class="metric-label">TURNS</div></div>',
        unsafe_allow_html=True,
    )
with m4:
    st.markdown(
        f'<div class="metric-box"><div class="metric-val">{st.session_state.total_tokens}</div>'
        f'<div class="metric-label">EST. TOKENS</div></div>',
        unsafe_allow_html=True,
    )

st.markdown("")

# ── Chat display ─────────────────────────────────────────────────────────

for msg in st.session_state.messages:
    role = msg["role"]
    content = msg["content"]
    if role == "user":
        st.markdown(
            f'<div class="chat-msg user"><div class="msg-label">// YOU</div>{content}</div>',
            unsafe_allow_html=True,
        )
    else:
        css_class = (
            "assistant-support" if st.session_state.stance == "support" else "assistant-oppose"
        )
        label = "// ADVOCATUS" if st.session_state.stance == "support" else "// INQUISITOR"
        st.markdown(
            f'<div class="chat-msg {css_class}">'
            f'<div class="msg-label">{label}</div>{content}</div>',
            unsafe_allow_html=True,
        )

# ── Provider / pack helpers ──────────────────────────────────────────────

_provider_cache: dict[tuple[str, ...], BaseProvider] = {}


def _get_provider() -> BaseProvider:
    key = (provider_name, model_name, base_url, api_key)
    if key not in _provider_cache:
        if len(_provider_cache) > 8:
            _provider_cache.clear()
        config = ProviderConfig(
            model=model_name,
            base_url=base_url or None,
            api_key=api_key or None,
        )
        _provider_cache[key] = create_provider(provider_name, config)
    return _provider_cache[key]


def _run_chat(user_input: str) -> str:
    """Synchronous wrapper around the async provider call."""
    loader = PackLoader()
    pack = loader.load(pack_name)
    provider = _get_provider()

    messages = [Message(role="system", content=pack.system_prompt)]
    for msg in st.session_state.messages:
        messages.append(Message(role=msg["role"], content=msg["content"]))
    messages.append(Message(role="user", content=user_input))

    async def _call() -> str:
        resp = await provider.chat(messages, **pack.model_hints)
        return resp.content

    return asyncio.run(_call())


def _stream_chat(user_input: str):
    """Generator that yields chunks from the async provider stream."""
    loader = PackLoader()
    pack = loader.load(pack_name)
    provider = _get_provider()

    messages = [Message(role="system", content=pack.system_prompt)]
    for msg in st.session_state.messages:
        messages.append(Message(role=msg["role"], content=msg["content"]))
    messages.append(Message(role="user", content=user_input))

    async def _gen():
        chunks = []
        async for chunk in provider.stream(messages, **pack.model_hints):
            chunks.append(chunk)
            yield chunk

    loop = asyncio.new_event_loop()
    gen = _gen()
    try:
        while True:
            yield loop.run_until_complete(gen.__anext__())
    except StopAsyncIteration:
        pass
    finally:
        loop.close()


# ── Chat input ───────────────────────────────────────────────────────────

user_input = st.chat_input(
    placeholder="Type your most controversial opinion. No judgment. (Actually...)"
)

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.turn_count += 1

    st.markdown(
        f'<div class="chat-msg user"><div class="msg-label">// YOU</div>{user_input}</div>',
        unsafe_allow_html=True,
    )

    css_class = "assistant-support" if st.session_state.stance == "support" else "assistant-oppose"
    label = "// ADVOCATUS" if st.session_state.stance == "support" else "// INQUISITOR"

    try:
        with st.spinner(
            f"{'Charging flattery cannon' if st.session_state.stance == 'support' else 'Loading sarcasm module'}..."
        ):
            start_t = time.monotonic()
            response = _run_chat(user_input)
            elapsed = time.monotonic() - start_t

        st.session_state.messages.append({"role": "assistant", "content": response})
        est_tokens = len(response) // 4 + len(user_input) // 4
        st.session_state.total_tokens += est_tokens

        st.markdown(
            f'<div class="chat-msg {css_class}">'
            f'<div class="msg-label">{label} // {elapsed:.1f}s // ~{est_tokens} tokens</div>'
            f"{response}</div>",
            unsafe_allow_html=True,
        )
        st.rerun()
    except Exception as exc:
        st.error(f"Connection error: {exc}")

# ── Footer ───────────────────────────────────────────────────────────────

st.markdown(
    '<div class="cyber-footer">'
    "POLARITY.AI v0.1.0 // SATIRICAL FRAMEWORK // "
    "NO MORAL COMPASS INCLUDED // MIT LICENSE // "
    "DEVELOPERS ASSUME ZERO LIABILITY"
    "</div>",
    unsafe_allow_html=True,
)
