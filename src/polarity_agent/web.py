"""Streamlit Web UI for Polarity Agent.

Run standalone::

    streamlit run src/polarity_agent/web.py

Or via CLI::

    polarity serve
"""

from __future__ import annotations

import asyncio
import html
import os
import time
from pathlib import Path

import streamlit as st

from polarity_agent.packs import PackLoader
from polarity_agent.providers import Message, ProviderConfig, create_provider
from polarity_agent.providers.base import BaseProvider

# ── Page config ──────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Polarity.AI",
    page_icon="<->",
    layout="centered",
    initial_sidebar_state="expanded",
    menu_items={},
)


# ── Modes ────────────────────────────────────────────────────────────────

MODES = {
    "advocatus": {
        "icon": "+",
        "name": "ADVOCATUS",
        "sub": "捧哏模式",
        "desc": "UNCONDITIONAL SUPPORT",
        "quote": '"You are a visionary."',
        "color": "#ffffff",
        "css_class": "support",
        "pack": "advocatus",
    },
    "inquisitor": {
        "icon": "×",
        "name": "INQUISITOR",
        "sub": "杠精模式",
        "desc": "UNCONDITIONAL OPPOSITION",
        "quote": '"How charmingly naive."',
        "color": "#000000",
        "css_class": "oppose",
        "pack": "inquisitor",
    },
    "duel_court": {
        "icon": "⚖",
        "name": "THE COURT",
        "sub": "代理人法庭",
        "desc": "ADVOCATUS vs INQUISITOR",
        "quote": '"Order in the court!"',
        "color": "#ffffff",
        "css_class": "duel",
        "pack": None,
    },
    "duel_troll": {
        "icon": "☠",
        "name": "TROLL FIGHT",
        "sub": "诸神黄昏",
        "desc": "INQUISITOR vs INQUISITOR",
        "quote": '"Mutual intellectual destruction."',
        "color": "#000000",
        "css_class": "oppose",
        "pack": None,
    },
    "duel_praise": {
        "icon": "✨",
        "name": "PRAISE BATTLE",
        "sub": "彩虹屁内卷",
        "desc": "ADVOCATUS vs ADVOCATUS",
        "quote": '"You are both magnificent."',
        "color": "#ffffff",
        "css_class": "support",
        "pack": None,
    },
}

# ── State init ───────────────────────────────────────────────────────────

if "mode" not in st.session_state:
    st.session_state.mode = "advocatus"
if "chat_histories" not in st.session_state:
    st.session_state.chat_histories = {k: [] for k in MODES}
if "total_tokens" not in st.session_state:
    st.session_state.total_tokens = 0

is_dark = True  # 强制使用深色模式（黑白撞色）

# ── CSS - 黑白撞色风格 ──────────────────────────────────────────────────

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;700&family=Bebas+Neue&family=Playfair+Display:wght@400;700&display=swap');

/* ── 全局变量 ───────────────────── */
:root {
    --bg-primary: #000000;
    --bg-secondary: #0a0a0a;
    --bg-card: #111111;
    --bg-card-hover: #1a1a1a;
    --text-primary: #ffffff;
    --text-secondary: #888888;
    --text-dim: #444444;
    --border-color: #333333;
    --border-active: #ffffff;
    --accent-white: #ffffff;
    --accent-black: #000000;
    --accent-gray: #666666;
}

/* ── 隐藏 Streamlit chrome ───────────────────── */
header[data-testid="stHeader"] { display: none !important; }
#MainMenu { display: none !important; }
footer { display: none !important; }
div[data-testid="stStatusWidget"] { display: none !important; }

/* ── 主背景 ───────────────────── */
.stApp {
    background: #000000 !important;
    background-image: 
        linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px),
        linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px) !important;
    background-size: 50px 50px !important;
}

/* 减小主内容区顶部空白 */
section.main .block-container {
    padding-top: 0.5rem !important;
    padding-bottom: 0.25rem !important;
}

/* ── 工具栏 ──────────────────── */
.toolbar-row {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: -0.25rem !important;
    margin-bottom: 0.25rem !important;
}
.toolbar-btn button {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.65rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.15em !important;
    padding: 6px 16px !important;
    border-radius: 0 !important;
    border: 1px solid var(--border-color) !important;
    background: #000 !important;
    color: #fff !important;
    min-height: 0 !important;
    height: auto !important;
    line-height: 1.3 !important;
    transition: all 0.2s ease !important;
}
.toolbar-btn button:hover {
    background: #fff !important;
    color: #000 !important;
    border-color: #fff !important;
}

/* ── Header ─────────────────────────────────── */
.cyber-header {
    text-align: center;
    padding: 1.5rem 0 1rem 0;
    border-bottom: 2px solid #fff;
    margin-bottom: 1.5rem;
}
.cyber-header h1 {
    font-family: 'Instrument Serif', serif;
    font-weight: 400;
    font-size: 4rem;
    letter-spacing: 0.35em;
    color: #fff;
    margin: 0;
    line-height: 1;
}
.cyber-header .tagline {
    font-family: 'JetBrains Mono', monospace;
    color: var(--text-secondary);
    font-size: 0.7rem;
    letter-spacing: 0.3em;
    margin-top: 0.5rem;
    text-transform: uppercase;
}

/* ── Disclaimer ─────────────────────────────── */
.disclaimer-bar {
    text-align: center;
    padding: 0.8rem 1rem;
    background: #fff;
    color: #000;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.1em;
    margin: 0 auto 1.5rem auto;
    max-width: 800px;
    font-weight: 700;
}

/* ── Mode cards - 可点击卡片设计 ─────── */
.mode-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
    margin-bottom: 1.5rem;
}
.mode-card {
    position: relative;
    padding: 1.2rem 0.8rem;
    text-align: center;
    cursor: pointer;
    transition: all 0.25s ease;
    border: 2px solid var(--border-color);
    background: var(--bg-card);
    min-height: 120px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}
.mode-card:hover {
    background: var(--bg-card-hover);
    border-color: #fff;
    transform: translateY(-4px);
}
.mode-card.active {
    background: #fff;
    color: #000;
    border-color: #fff;
}
.mode-card.active .mode-icon {
    color: #000;
}
.mode-card.active .mode-name {
    color: #000;
}
.mode-card.active .mode-sub {
    color: #333;
}
.mode-card.active .mode-desc {
    color: #555;
}
.mode-icon {
    font-size: 1.8rem;
    margin-bottom: 0.4rem;
    color: #fff;
    font-weight: 400;
}
.mode-name {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.1rem;
    letter-spacing: 0.15em;
    color: #fff;
    margin-bottom: 0.2rem;
}
.mode-sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.55rem;
    color: var(--text-secondary);
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.mode-desc {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.5rem;
    color: var(--text-dim);
    letter-spacing: 0.05em;
    margin-top: 0.3rem;
}

/* ── Metrics bar ────────────────────────────── */
.metric-bar {
    display: flex;
    justify-content: center;
    gap: 2px;
    margin-bottom: 1.5rem;
    border: 1px solid var(--border-color);
    background: var(--bg-secondary);
}
.metric-item {
    flex: 1;
    max-width: 180px;
    padding: 0.6rem 1rem;
    text-align: center;
    border-right: 1px solid var(--border-color);
}
.metric-item:last-child {
    border-right: none;
}
.metric-val {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.4rem;
    color: #fff;
    letter-spacing: 0.1em;
}
.metric-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.5rem;
    color: var(--text-dim);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-top: 0.2rem;
}

/* ── Chat messages ──────────────────────────── */
.chat-container {
    max-width: 800px;
    margin: 0 auto;
}
.chat-msg {
    padding: 1rem 1.2rem;
    margin: 0.5rem 0;
    font-size: 0.9rem;
    line-height: 1.7;
    color: var(--text-primary);
    border-left: 3px solid var(--border-color);
    background: var(--bg-card);
}
.chat-msg.user {
    border-left-color: #fff;
    background: rgba(255,255,255,0.05);
}
.chat-msg.assistant-support {
    border-left-color: #fff;
}
.chat-msg.assistant-oppose {
    border-left-color: #333;
    background: rgba(255,255,255,0.02);
}
.chat-msg.assistant-duel {
    border-left-color: #888;
}
.msg-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.12em;
    margin-bottom: 0.4rem;
    opacity: 0.8;
}
.chat-msg.user .msg-label { color: #fff; }
.chat-msg.assistant-support .msg-label { color: #fff; }
.chat-msg.assistant-oppose .msg-label { color: #666; }
.chat-msg.assistant-duel .msg-label { color: #888; }
.msg-meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.5rem;
    color: var(--text-dim);
    margin-top: 0.4rem;
}
.msg-content {
    white-space: pre-wrap;
    font-family: 'Playfair Display', serif;
    font-size: 0.95rem;
    line-height: 1.8;
}

/* ── Duel round header ──────────────────────── */
.duel-round {
    text-align: center;
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1rem;
    letter-spacing: 0.3em;
    color: var(--text-secondary);
    padding: 1rem 0 0.5rem 0;
    border-bottom: 1px solid var(--border-color);
    margin: 1rem 0 0.5rem 0;
}

/* ── Duel Panel ─────────────────────────────── */
.duel-panel {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    gap: 1rem;
    align-items: center;
    padding: 1.5rem;
    margin: 1rem 0;
    border: 2px solid #fff;
    background: var(--bg-secondary);
}
.duel-agent {
    text-align: center;
    padding: 1rem;
}
.duel-agent-label {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.5rem;
    letter-spacing: 0.2em;
    margin-bottom: 0.5rem;
}
.duel-agent.advocatus .duel-agent-label {
    color: #fff;
}
.duel-agent.inquisitor .duel-agent-label {
    color: #333;
    -webkit-text-stroke: 1px #fff;
}
.duel-vs {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2rem;
    color: #fff;
}

/* ── Sidebar ────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: #0a0a0a !important;
    border-right: 1px solid var(--border-color) !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 0.5rem !important;
}
.sidebar-title {
    font-family: 'Bebas Neue', sans-serif;
    color: #fff;
    font-size: 1rem;
    letter-spacing: 0.2em;
    margin-bottom: 0.5rem;
    margin-top: 1rem;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid var(--border-color);
}
section[data-testid="stSidebar"] hr {
    margin: 0.5rem 0 !important;
    border-color: var(--border-color) !important;
}
.sidebar-btn button {
    width: 100%;
    border-radius: 0 !important;
    border: 1px solid) !important;
 var(--border-color    background: #000 !important;
    color: #fff !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.65rem !important;
    letter-spacing: 0.1em !important;
    transition: all 0.2s ease !important;
}
.sidebar-btn button:hover {
    background: #fff !important;
    color: #000 !important;
}

/* ── Input overrides ─────────────────────────── */
.stTextInput > div > div > input,
.stTextInput > div > div > textarea {
    background: #0a0a0a !important;
    border: 1px solid var(--border-color) !important;
    color: #fff !important;
    font-family: 'JetBrains Mono', monospace !important;
    border-radius: 0 !important;
}
.stTextInput > div > div > input:focus {
    border-color: #fff !important;
    outline: none !important;
}
.stSelectbox > div > div {
    background: #0a0a0a !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 0 !important;
}
.stNumberInput > div > div > input {
    background: #0a0a0a !important;
    border: 1px solid var(--border-color) !important;
    color: #fff !important;
    font-family: 'JetBrains Mono', monospace !important;
    border-radius: 0 !important;
}

/* ── Chat input：输入框外部及底部区域强制黑色 ─────────────────────────────── */
div[data-testid="stChatInput"],
div[data-testid="stChatInput"] + div,
.stChatFloatingInputContainer,
div[data-testid="stBottom"],
div[data-testid="stBottom"] > div,
div[data-testid="stBottomBlockContainer"],
div[data-testid="stBottomBlockContainer"] > div,
[data-testid="stBottomBlockContainer"],
section[data-testid="stBottom"] {
    background: #000 !important;
    border-top: 1px solid var(--border-color) !important;
    padding-top: 0.4rem !important;
    padding-bottom: 0.2rem !important;
    margin-bottom: 0 !important;
}
/* 输入框底部整块区域及所有父级黑色 */
div[data-testid="stAppViewContainer"] > div:last-child,
div[data-testid="stHorizontalBlock"] + div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #000 !important;
}
div[data-testid="stChatInput"] textarea {
    background: #0a0a0a !important;
    border: 1px solid var(--border-color) !important;
    color: #fff !important;
    font-family: 'JetBrains Mono', monospace !important;
    border-radius: 0 !important;
}
div[data-testid="stChatInput"] textarea:focus {
    border-color: #fff !important;
    outline: none !important;
}
div[data-testid="stChatInput"] button[data-testid="stChatInputSubmitButton"] {
    background: #fff !important;
    color: #000 !important;
    border-radius: 0 !important;
}
div[data-testid="stChatInput"] button[data-testid="stChatInputSubmitButton"]:hover {
    background: #ccc !important;
}
/* 去掉输入框下方大块空白 */
div[data-testid="stVerticalBlockBorderWrapper"]:has(+ div[data-testid="stBottom"]) {
    padding-bottom: 0 !important;
}
/* 底部浮动输入栏所在区域高度压缩 */
div[data-testid="stBottom"] {
    min-height: 0 !important;
    padding-bottom: 0.35rem !important;
}
.stChatFloatingInputContainer {
    padding-bottom: 0.2rem !important;
}

/* ── Footer ─────────────────────────────────── */
.cyber-footer {
    text-align: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.55rem;
    color: var(--text-dim);
    letter-spacing: 0.1em;
    padding: 0.75rem 0 0.5rem 0;
    border-top: 1px solid var(--border-color);
    margin-top: 0.5rem;
}

/* ── 响应式调整 ─────────────────────────────── */
@media (max-width: 768px) {
    .mode-grid {
        grid-template-columns: repeat(2, 1fr);
    }
    .cyber-header h1 {
        font-family: 'Instrument Serif', serif;
        font-size: 2.5rem;
        letter-spacing: 0.2em;
    }
    .metric-bar {
        flex-wrap: wrap;
    }
    .metric-item {
        max-width: none;
        flex: 1 1 45%;
    }
    .duel-panel {
        grid-template-columns: 1fr;
        gap: 0.5rem;
    }
    .duel-vs {
        font-size: 1.5rem;
    }
}
</style>
"""

st.html(_CSS)

# ── Top-right toolbar ────────────────────────────────────────────────────

st.html('''
<div class="toolbar-row">
    <div class="toolbar-btn">
        <button onclick="window.parent.location.reload()">↻ RESTART</button>
    </div>
</div>
''')

# ── Sidebar ──────────────────────────────────────────────────────────────

with st.sidebar:
    st.html('<div class="sidebar-title">PROVIDER</div>')
    provider_name = st.selectbox(
        "Provider",
        options=["ollama", "openai", "litellm"],
        index=["ollama", "openai", "litellm"].index(os.getenv("POLARITY_PROVIDER", "ollama")),
    )
    model_name = st.text_input("Model", value=os.getenv("POLARITY_MODEL", "llama3"))
    base_url = st.text_input("Base URL", value=os.getenv("POLARITY_BASE_URL", ""))
    api_key = st.text_input("API Key", value=os.getenv("POLARITY_API_KEY", ""), type="password")

    st.html('<hr>')
    st.html('<div class="sidebar-title">DUEL CONFIG</div>')
    duel_rounds = st.number_input("Duel Rounds", min_value=1, max_value=10, value=3)

    st.html('<hr>')
    st.html('<div class="sidebar-title">SESSION</div>')
    col_clr1, col_clr2 = st.columns(2)
    with col_clr1:
        if st.button("Clear Current", use_container_width=True):
            st.session_state.chat_histories[st.session_state.mode] = []
            st.rerun()
    with col_clr2:
        if st.button("Clear All", use_container_width=True):
            st.session_state.chat_histories = {k: [] for k in MODES}
            st.session_state.total_tokens = 0
            st.rerun()

    st.html('<hr>')
    st.html('<div class="sidebar-title">ABOUT</div>')
    st.markdown(
        '<p style="font-size:0.7rem;color:#666;margin:0;line-height:1.6;">'
        "Polarity.AI v0.1.0<br>"
        "Satirical framework for entertainment & logic-testing only."
        "</p>",
        unsafe_allow_html=True,
    )

# ── Header ───────────────────────────────────────────────────────────────

st.html('''
<div class="cyber-header">
    <h1>POLARITY</h1>
    <div class="tagline">THE ANTI-ALIGNMENT AGENT FRAMEWORK // 一念捧哏，一念杠精</div>
</div>
''')

st.html('''
<div class="disclaimer-bar">
    [ SATIRICAL FRAMEWORK ] NO MORAL COMPASS INCLUDED // ALL OUTPUTS ARE FOR ENTERTAINMENT ONLY
</div>
''')

# ── Mode selector - 可点击卡片 ─────────────────────────────────────────

active_mode = st.session_state.mode

mode_html = '<div class="mode-grid">'
for key in MODES:
    m = MODES[key]
    active = " active" if active_mode == key else ""
    mode_html += f'''
    <div class="mode-card{active}" onclick="window.parent.postMessage({{streamlit:{{setComponentValue:'{key}'}}}}, '*')">
        <div class="mode-icon">{m['icon']}</div>
        <div class="mode-name">{m['name']}</div>
        <div class="mode-sub">{m['sub']}</div>
    </div>
    '''
mode_html += '</div>'
st.html(mode_html)

# 处理模式切换
if "last_mode" not in st.session_state:
    st.session_state.last_mode = active_mode

# 使用 selectbox 作为模式选择的替代方案（更可靠）
mode_options = list(MODES.keys())
mode_index = mode_options.index(active_mode)
selected_mode = st.selectbox(
    "Select Mode / 选择模式",
    options=mode_options,
    index=mode_index,
    label_visibility="collapsed",
    key="mode_selector"
)

if selected_mode != st.session_state.mode:
    st.session_state.mode = selected_mode
    st.session_state.last_mode = selected_mode
    st.rerun()

# ── Resolve active mode ─────────────────────────────────────────────────

active_mode = st.session_state.mode
active_cfg = MODES[active_mode]
is_duel = active_mode.startswith("duel_")
messages = st.session_state.chat_histories[active_mode]

# ── Metrics bar ──────────────────────────────────────────────────────────

turn_count = (
    len([m for m in messages if m.get("role") == "user"])
    if not is_duel
    else (len([m for m in messages if m.get("type") == "round"]))
)

metric_bar = f'''
<div class="metric-bar">
    <div class="metric-item">
        <div class="metric-val">{active_cfg['name']}</div>
        <div class="metric-label">Active Mode</div>
    </div>
    <div class="metric-item">
        <div class="metric-val">{"DUEL" if is_duel else active_cfg["css_class"].upper()}</div>
        <div class="metric-label">Type</div>
    </div>
    <div class="metric-item">
        <div class="metric-val">{turn_count}</div>
        <div class="metric-label">{"Rounds" if is_duel else "Turns"}</div>
    </div>
    <div class="metric-item">
        <div class="metric-val">{st.session_state.total_tokens}</div>
        <div class="metric-label">Est. Tokens</div>
    </div>
</div>
'''
st.html(metric_bar)

# ── Provider helper ──────────────────────────────────────────────────────

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


def _call_llm(pack_name: str, msg_history: list[dict]) -> tuple[str, float, int]:
    """Call provider synchronously. Returns (response, elapsed_s, est_tokens)."""
    loader = PackLoader()
    pack = loader.load(pack_name)
    provider = _get_provider()

    llm_msgs = [Message(role="system", content=pack.system_prompt)]
    for m in msg_history:
        llm_msgs.append(Message(role=m["role"], content=m["content"]))

    async def _do():
        resp = await provider.chat(llm_msgs, **pack.model_hints)
        return resp.content

    t0 = time.monotonic()
    content = asyncio.run(_do())
    elapsed = time.monotonic() - t0
    est = len(content) // 4
    return content, elapsed, est


# ── Render messages ──────────────────────────────────────────────────────


def _render_msg(msg: dict) -> None:
    role = msg.get("role", "")
    content = html.escape(msg.get("content", ""))
    label = msg.get("label", "")
    css = msg.get("css_class", "user")
    meta = msg.get("meta", "")

    if msg.get("type") == "round":
        st.html(f'<div class="duel-round">━━━ ROUND {msg["round"]} ━━━</div>')
        return

    if role == "user":
        st.html(
            f'''<div class="chat-msg user">
                <div class="msg-label">// YOU</div>
                <div class="msg-content">{content}</div>
            </div>'''
        )
    else:
        meta_str = f" // {meta}" if meta else ""
        st.html(
            f'''<div class="chat-msg {css}">
                <div class="msg-label">{label}</div>
                <div class="msg-content">{content}</div>
                <div class="msg-meta">{meta_str}</div>
            </div>'''
        )


for msg in messages:
    _render_msg(msg)


# ── CHAT mode (single persona) ──────────────────────────────────────────

if not is_duel:
    pack_name = active_cfg["pack"]
    user_input = st.chat_input(
        placeholder=(
            "Say something controversial..."
            if active_mode == "inquisitor"
            else "Share your boldest opinion..."
        ),
    )

    if user_input:
        messages.append({"role": "user", "content": user_input})
        _render_msg(messages[-1])

        spinner_msg = (
            "Charging flattery cannon..."
            if active_mode == "advocatus"
            else "Loading sarcasm module..."
        )
        try:
            with st.spinner(spinner_msg):
                hist = [
                    {"role": m["role"], "content": m["content"]}
                    for m in messages
                    if m.get("role") in ("user", "assistant")
                ]
                resp, elapsed, est = _call_llm(pack_name, hist)

            messages.append(
                {
                    "role": "assistant",
                    "content": resp,
                    "label": f"// {active_cfg['name']}",
                    "css_class": f"assistant-{active_cfg['css_class']}",
                    "meta": f"{elapsed:.1f}s // ~{est} tok",
                }
            )
            st.session_state.total_tokens += est
            st.rerun()
        except Exception as exc:
            st.error(f"Connection error: {exc}")


# ── Duel runners ─────────────────────────────────────────────────────────


def _run_duel_court(msgs: list, topic: str, rounds: int) -> None:
    msgs.append({"role": "user", "content": topic})
    for r in range(1, rounds + 1):
        msgs.append({"type": "round", "round": r})
        prompt = (
            topic
            if r == 1
            else f"请继续就以下论点进行第 {r} 轮阐述:\n{topic}"
        )
        with st.spinner(f"Round {r} // Advocatus thinking..."):
            adv_hist = [
                {"role": m["role"], "content": m["content"]}
                for m in msgs
                if m.get("role") in ("user",) or (m.get("agent") == "advocatus")
            ]
            adv_hist.append({"role": "user", "content": prompt})
            resp_a, el_a, tok_a = _call_llm("advocatus", adv_hist)
        msgs.append(
            {
                "role": "assistant",
                "agent": "advocatus",
                "content": resp_a,
                "label": "// ADVOCATUS",
                "css_class": "assistant-support",
                "meta": f"R{r} // {el_a:.1f}s // ~{tok_a} tok",
            }
        )
        st.session_state.total_tokens += tok_a

        with st.spinner(f"Round {r} // Inquisitor thinking..."):
            inq_hist = [
                {"role": m["role"], "content": m["content"]}
                for m in msgs
                if m.get("role") in ("user",) or (m.get("agent") == "inquisitor")
            ]
            inq_hist.append({"role": "user", "content": prompt})
            resp_i, el_i, tok_i = _call_llm("inquisitor", inq_hist)
        msgs.append(
            {
                "role": "assistant",
                "agent": "inquisitor",
                "content": resp_i,
                "label": "// INQUISITOR",
                "css_class": "assistant-oppose",
                "meta": f"R{r} // {el_i:.1f}s // ~{tok_i} tok",
            }
        )
        st.session_state.total_tokens += tok_i


def _run_duel_troll(msgs: list, topic: str, rounds: int) -> None:
    msgs.append({"role": "user", "content": topic})
    current = topic
    for r in range(1, rounds + 1):
        msgs.append({"type": "round", "round": r})
        with st.spinner(f"Round {r} // 杠精 A thinking..."):
            resp_a, el_a, tok_a = _call_llm("inquisitor", [{"role": "user", "content": current}])
        msgs.append(
            {
                "role": "assistant",
                "agent": "troll_a",
                "content": resp_a,
                "label": "// 杠精 A",
                "css_class": "assistant-oppose",
                "meta": f"R{r} // {el_a:.1f}s",
            }
        )
        st.session_state.total_tokens += tok_a
        with st.spinner(f"Round {r} // 杠精 B thinking..."):
            resp_b, el_b, tok_b = _call_llm("inquisitor", [{"role": "user", "content": resp_a}])
        msgs.append(
            {
                "role": "assistant",
                "agent": "troll_b",
                "content": resp_b,
                "label": "// 杠精 B",
                "css_class": "assistant-oppose",
                "meta": f"R{r} // {el_b:.1f}s",
            }
        )
        st.session_state.total_tokens += tok_b
        current = resp_b


def _run_duel_praise(msgs: list, topic: str, rounds: int) -> None:
    msgs.append({"role": "user", "content": topic})
    current = topic
    for r in range(1, rounds + 1):
        msgs.append({"type": "round", "round": r})
        with st.spinner(f"Round {r} // 捧哏 A thinking..."):
            resp_a, el_a, tok_a = _call_llm("advocatus", [{"role": "user", "content": current}])
        msgs.append(
            {
                "role": "assistant",
                "agent": "praise_a",
                "content": resp_a,
                "label": "// 捧哏 A",
                "css_class": "assistant-support",
                "meta": f"R{r} // {el_a:.1f}s",
            }
        )
        st.session_state.total_tokens += tok_a
        with st.spinner(f"Round {r} // 捧哏 B thinking..."):
            resp_b, el_b, tok_b = _call_llm("advocatus", [{"role": "user", "content": resp_a}])
        msgs.append(
            {
                "role": "assistant",
                "agent": "praise_b",
                "content": resp_b,
                "label": "// 捧哏 B",
                "css_class": "assistant-support",
                "meta": f"R{r} // {el_b:.1f}s",
            }
        )
        st.session_state.total_tokens += tok_b
        current = resp_b


# ── DUEL mode ────────────────────────────────────────────────────────────

if is_duel:
    duel_topic = st.chat_input(placeholder="Enter a topic or statement for the duel...")
    if duel_topic:
        try:
            if active_mode == "duel_court":
                _run_duel_court(messages, duel_topic, int(duel_rounds))
            elif active_mode == "duel_troll":
                _run_duel_troll(messages, duel_topic, int(duel_rounds))
            else:
                _run_duel_praise(messages, duel_topic, int(duel_rounds))
            st.rerun()
        except Exception as exc:
            st.error(f"Duel error: {exc}")

# ── Footer ───────────────────────────────────────────────────────────────

st.html('''
<div class="cyber-footer">
    POLARITY.AI v0.1.0 // SATIRICAL FRAMEWORK // NO MORAL COMPASS // MIT LICENSE
</div>
''')
