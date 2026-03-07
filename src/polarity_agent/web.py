"""Streamlit Web UI for Polarity Agent.

Run standalone::

    streamlit run src/polarity_agent/web.py

Or via CLI::

    penggen serve
"""

from __future__ import annotations

import asyncio
import html
import os
import time

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
        "sub": "\u62a4\u77ed\u6a21\u5f0f",
        "desc": "UNCONDITIONAL SUPPORT",
        "quote": '"You are a visionary."',
        "color": "#39ff14",
        "css_class": "support",
        "pack": "advocatus",
    },
    "inquisitor": {
        "icon": "x",
        "name": "INQUISITOR",
        "sub": "\u6760\u7cbe\u6a21\u5f0f",
        "desc": "UNCONDITIONAL OPPOSITION",
        "quote": '"How charmingly naive."',
        "color": "#ff1744",
        "css_class": "oppose",
        "pack": "inquisitor",
    },
    "duel_court": {
        "icon": "\u2696",
        "name": "THE COURT",
        "sub": "\u4ee3\u7406\u4eba\u6cd5\u5ead",
        "desc": "ADVOCATUS vs INQUISITOR",
        "quote": '"Order in the court!"',
        "color": "#00e5ff",
        "css_class": "duel",
        "pack": None,
    },
    "duel_troll": {
        "icon": "\u2620",
        "name": "TROLL FIGHT",
        "sub": "\u8bf8\u795e\u9ec4\u660f",
        "desc": "INQUISITOR vs INQUISITOR",
        "quote": '"Mutual intellectual destruction."',
        "color": "#ff1744",
        "css_class": "oppose",
        "pack": None,
    },
    "duel_praise": {
        "icon": "\u2728",
        "name": "PRAISE BATTLE",
        "sub": "\u5f69\u8679\u5c41\u5185\u5377",
        "desc": "ADVOCATUS vs ADVOCATUS",
        "quote": '"You are both magnificent."',
        "color": "#39ff14",
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
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

is_dark = st.session_state.theme == "dark"

# ── CSS (dual-theme) ────────────────────────────────────────────────────

_CSS_DARK = """
:root {
    --bg-app-start: #0a0a0f; --bg-app-mid: #0d0d18; --bg-app-end: #0a0f14;
    --bg-sidebar-start: #0d0d14; --bg-sidebar-end: #111119;
    --bg-input: #16161e; --bg-card-s: rgba(57,255,20,0.06); --bg-card-s2: rgba(0,229,255,0.03);
    --bg-card-o: rgba(255,23,68,0.06); --bg-card-o2: rgba(255,0,255,0.03);
    --bg-card-d: rgba(0,229,255,0.06); --bg-card-d2: rgba(255,0,255,0.03);
    --text-primary: #cdd6f4; --text-secondary: #666; --text-dim: #444;
    --text-footer: #2a2a2a;
    --border-cyan: rgba(0,229,255,0.18); --border-sidebar: rgba(0,229,255,0.1);
    --disclaimer-bg: rgba(255,23,68,0.06); --disclaimer-border: rgba(255,23,68,0.18);
    --disclaimer-color: #c05060;
    --metric-bg: rgba(0,229,255,0.04); --metric-border: rgba(0,229,255,0.12);
    --msg-user-bg1: rgba(0,229,255,0.07); --msg-user-bg2: rgba(0,229,255,0.02);
    --msg-support-bg1: rgba(57,255,20,0.07); --msg-support-bg2: rgba(57,255,20,0.02);
    --msg-oppose-bg1: rgba(255,23,68,0.07); --msg-oppose-bg2: rgba(255,23,68,0.02);
    --msg-duel-bg1: rgba(0,229,255,0.07); --msg-duel-bg2: rgba(0,229,255,0.02);
}
"""

_CSS_LIGHT = """
:root {
    --bg-app-start: #f0f2f6; --bg-app-mid: #e8eaf0; --bg-app-end: #f0f2f6;
    --bg-sidebar-start: #e4e6ec; --bg-sidebar-end: #dfe1e8;
    --bg-input: #ffffff; --bg-card-s: rgba(57,255,20,0.08); --bg-card-s2: rgba(0,180,200,0.05);
    --bg-card-o: rgba(255,23,68,0.08); --bg-card-o2: rgba(200,0,200,0.04);
    --bg-card-d: rgba(0,180,220,0.08); --bg-card-d2: rgba(180,0,220,0.04);
    --text-primary: #1a1a2e; --text-secondary: #555; --text-dim: #888;
    --text-footer: #999;
    --border-cyan: rgba(0,150,180,0.25); --border-sidebar: rgba(0,150,180,0.15);
    --disclaimer-bg: rgba(255,23,68,0.06); --disclaimer-border: rgba(255,23,68,0.2);
    --disclaimer-color: #c04050;
    --metric-bg: rgba(0,150,200,0.06); --metric-border: rgba(0,150,200,0.15);
    --msg-user-bg1: rgba(0,150,200,0.08); --msg-user-bg2: rgba(0,150,200,0.02);
    --msg-support-bg1: rgba(40,180,20,0.08); --msg-support-bg2: rgba(40,180,20,0.02);
    --msg-oppose-bg1: rgba(220,30,60,0.08); --msg-oppose-bg2: rgba(220,30,60,0.02);
    --msg-duel-bg1: rgba(0,150,200,0.08); --msg-duel-bg2: rgba(0,150,200,0.02);
}
"""

_CSS_COMMON = """
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Orbitron:wght@500;700;900&display=swap');

/* ── Hide Streamlit chrome ───────────────────── */
header[data-testid="stHeader"] { display: none !important; }
#MainMenu { display: none !important; }
footer { display: none !important; }
div[data-testid="stStatusWidget"] { display: none !important; }

.stApp {
    background: linear-gradient(170deg, var(--bg-app-start) 0%, var(--bg-app-mid) 40%, var(--bg-app-end) 100%);
}

/* ── Top-right toolbar ───────────────────────── */
.top-toolbar {
    position: fixed;
    top: 8px;
    right: 16px;
    z-index: 9999;
    display: flex;
    gap: 6px;
}
.top-toolbar button {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    padding: 5px 12px;
    border-radius: 6px;
    border: 1px solid var(--border-cyan);
    background: var(--bg-input);
    color: #00e5ff;
    cursor: pointer;
    transition: all 0.2s ease;
}
.top-toolbar button:hover {
    box-shadow: 0 0 12px rgba(0,229,255,0.2);
}

/* ── Header ─────────────────────────────────── */
.cyber-header {
    text-align: center;
    padding: 0.8rem 0 0.2rem 0;
}
.cyber-header h1 {
    font-family: 'Orbitron', monospace;
    font-weight: 900;
    font-size: 2.4rem;
    letter-spacing: 0.3em;
    background: linear-gradient(90deg, #00e5ff, #ff00ff, #00e5ff);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: gradient-shift 4s ease infinite;
    margin: 0;
}
@keyframes gradient-shift {
    0%, 100% { background-position: 0% center; }
    50% { background-position: 200% center; }
}
.cyber-header .tagline {
    font-family: 'JetBrains Mono', monospace;
    color: var(--text-secondary);
    font-size: 0.74rem;
    letter-spacing: 0.1em;
    margin-top: 0.2rem;
}

/* ── Disclaimer ─────────────────────────────── */
.disclaimer-bar {
    text-align: center;
    padding: 0.4rem 0.8rem;
    border-radius: 6px;
    background: var(--disclaimer-bg);
    border: 1px solid var(--disclaimer-border);
    color: var(--disclaimer-color);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.66rem;
    margin: 0.3rem auto 0.6rem auto;
    max-width: 700px;
}

/* ── Mode cards ─────────────────────────────── */
.mode-card {
    border-radius: 12px;
    padding: 0.8rem 0.5rem;
    text-align: center;
    cursor: pointer;
    transition: all 0.25s ease;
    border: 2px solid transparent;
    min-height: 100px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}
.mode-card.support {
    background: linear-gradient(135deg, var(--bg-card-s), var(--bg-card-s2));
    border-color: rgba(57,255,20,0.2);
}
.mode-card.oppose {
    background: linear-gradient(135deg, var(--bg-card-o), var(--bg-card-o2));
    border-color: rgba(255,23,68,0.2);
}
.mode-card.duel {
    background: linear-gradient(135deg, var(--bg-card-d), var(--bg-card-d2));
    border-color: rgba(0,229,255,0.2);
}
.mode-card.active { transform: scale(1.03); }
.mode-card.support.active {
    border-color: #39ff14;
    box-shadow: 0 0 20px rgba(57,255,20,0.15), inset 0 0 20px rgba(57,255,20,0.04);
}
.mode-card.oppose.active {
    border-color: #ff1744;
    box-shadow: 0 0 20px rgba(255,23,68,0.15), inset 0 0 20px rgba(255,23,68,0.04);
}
.mode-card.duel.active {
    border-color: #00e5ff;
    box-shadow: 0 0 20px rgba(0,229,255,0.15), inset 0 0 20px rgba(0,229,255,0.04);
}
.mode-card .mc-icon { font-size: 1.3rem; margin-bottom: 0.15rem; }
.mode-card .mc-name {
    font-family: 'Orbitron', monospace;
    font-weight: 700;
    font-size: 0.68rem;
    letter-spacing: 0.1em;
}
.mode-card.support .mc-name { color: #39ff14; }
.mode-card.oppose .mc-name { color: #ff1744; }
.mode-card.duel .mc-name { color: #00e5ff; }
.mode-card .mc-sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.58rem;
    color: var(--text-secondary);
    margin-top: 0.1rem;
}

/* Hide the st.button under each card */
.mode-btn-container button {
    opacity: 0 !important;
    height: 0 !important;
    padding: 0 !important;
    margin: -4px 0 0 0 !important;
    border: none !important;
    min-height: 0 !important;
    overflow: hidden !important;
}

/* ── Chat messages ──────────────────────────── */
.chat-msg {
    padding: 0.85rem 1rem;
    border-radius: 10px;
    margin: 0.4rem 0;
    font-size: 0.88rem;
    line-height: 1.6;
    color: var(--text-primary);
}
.chat-msg.user {
    background: linear-gradient(135deg, var(--msg-user-bg1), var(--msg-user-bg2));
    border-left: 3px solid #00e5ff;
}
.chat-msg.assistant-support {
    background: linear-gradient(135deg, var(--msg-support-bg1), var(--msg-support-bg2));
    border-left: 3px solid #39ff14;
}
.chat-msg.assistant-oppose {
    background: linear-gradient(135deg, var(--msg-oppose-bg1), var(--msg-oppose-bg2));
    border-left: 3px solid #ff1744;
}
.chat-msg.assistant-duel {
    background: linear-gradient(135deg, var(--msg-duel-bg1), var(--msg-duel-bg2));
    border-left: 3px solid #00e5ff;
}
.chat-msg .msg-label {
    font-family: 'Orbitron', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.08em;
    margin-bottom: 0.25rem;
    opacity: 0.7;
}
.chat-msg.user .msg-label { color: #00e5ff; }
.chat-msg.assistant-support .msg-label { color: #39ff14; }
.chat-msg.assistant-oppose .msg-label { color: #ff1744; }
.chat-msg.assistant-duel .msg-label { color: #00e5ff; }

/* ── Duel round header ──────────────────────── */
.duel-round {
    text-align: center;
    font-family: 'Orbitron', monospace;
    font-size: 0.68rem;
    letter-spacing: 0.18em;
    color: var(--text-secondary);
    padding: 0.5rem 0 0.2rem 0;
    border-bottom: 1px solid rgba(0,229,255,0.08);
    margin: 0.6rem 0 0.3rem 0;
}

/* ── Metrics bar ────────────────────────────── */
.metric-box {
    background: var(--metric-bg);
    border: 1px solid var(--metric-border);
    border-radius: 8px;
    padding: 0.45rem 0.5rem;
    text-align: center;
}
.metric-box .metric-val {
    font-family: 'Orbitron', monospace;
    font-size: 1rem;
    font-weight: 700;
    color: #00e5ff;
}
.metric-box .metric-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.52rem;
    color: var(--text-dim);
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

/* ── Sidebar ────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--bg-sidebar-start), var(--bg-sidebar-end)) !important;
    border-right: 1px solid var(--border-sidebar);
    padding-top: 0.5rem !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 0.5rem !important;
}
.sidebar-title {
    font-family: 'Orbitron', monospace;
    color: #00e5ff;
    font-size: 0.74rem;
    letter-spacing: 0.1em;
    margin-bottom: 0.4rem;
    padding-bottom: 0.2rem;
    border-bottom: 1px solid rgba(0,229,255,0.1);
}
/* Reduce sidebar hr spacing */
section[data-testid="stSidebar"] hr {
    margin-top: 0.5rem !important;
    margin-bottom: 0.5rem !important;
}

/* ── Footer ─────────────────────────────────── */
.cyber-footer {
    text-align: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.58rem;
    color: var(--text-footer);
    letter-spacing: 0.04em;
    padding: 1.2rem 0 0.6rem 0;
    border-top: 1px solid rgba(0,229,255,0.05);
    margin-top: 1rem;
}

/* ── Input overrides (sidebar + main) ────────── */
.stTextInput > div > div > input,
.stTextInput > div > div > textarea {
    background: var(--bg-input) !important;
    border: 1px solid var(--border-cyan) !important;
    color: var(--text-primary) !important;
    font-family: 'JetBrains Mono', monospace !important;
    border-radius: 8px !important;
}
.stTextInput > div > div > input:focus {
    border-color: #00e5ff !important;
    box-shadow: 0 0 10px rgba(0,229,255,0.12) !important;
}
.stSelectbox > div > div {
    background: var(--bg-input) !important;
    border-color: var(--border-cyan) !important;
    border-radius: 8px !important;
}
.stNumberInput > div > div > input {
    background: var(--bg-input) !important;
    border: 1px solid var(--border-cyan) !important;
    color: var(--text-primary) !important;
    font-family: 'JetBrains Mono', monospace !important;
}

/* ── Bottom chat input (dark) ────────────────── */
div[data-testid="stChatInput"] {
    background: transparent !important;
}
div[data-testid="stChatInput"] textarea {
    background: var(--bg-input) !important;
    border: 1px solid var(--border-cyan) !important;
    color: var(--text-primary) !important;
    font-family: 'JetBrains Mono', monospace !important;
    border-radius: 10px !important;
}
div[data-testid="stChatInput"] textarea:focus {
    border-color: #00e5ff !important;
    box-shadow: 0 0 12px rgba(0,229,255,0.15) !important;
}
div[data-testid="stChatInput"] button {
    background: #00e5ff !important;
    color: #0a0a0f !important;
    border-radius: 8px !important;
}
/* Bottom bar background */
.stChatFloatingInputContainer,
div[data-testid="stBottom"] > div {
    background: var(--bg-app-start) !important;
    border-top: 1px solid var(--border-cyan) !important;
}
"""

theme_vars = _CSS_DARK if is_dark else _CSS_LIGHT
st.markdown(f"<style>{theme_vars}\n{_CSS_COMMON}</style>", unsafe_allow_html=True)

# ── Top-right toolbar (theme + print) via HTML/JS ────────────────────────

_theme_icon = "\u263e" if is_dark else "\u2600"
_theme_label = "LIGHT" if is_dark else "DARK"

st.markdown(
    f"""
<div class="top-toolbar">
    <button onclick="
        const params = new URLSearchParams(window.location.search);
        params.set('theme_toggle', '1');
        const form = document.createElement('form');
        form.method = 'GET';
        form.action = window.location.pathname;
        params.forEach((v,k) => {{
            const i = document.createElement('input');
            i.type='hidden'; i.name=k; i.value=v;
            form.appendChild(i);
        }});
        document.body.appendChild(form);
    " id="theme-btn-visual">{_theme_icon} {_theme_label}</button>
    <button onclick="window.print()">PRINT</button>
</div>
""",
    unsafe_allow_html=True,
)

# ── Sidebar ──────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div class="sidebar-title">// PROVIDER CONFIG</div>',
        unsafe_allow_html=True,
    )
    provider_name = st.selectbox(
        "Provider",
        options=["ollama", "openai", "litellm"],
        index=["ollama", "openai", "litellm"].index(os.getenv("POLARITY_PROVIDER", "ollama")),
    )
    model_name = st.text_input("Model", value=os.getenv("POLARITY_MODEL", "llama3"))
    base_url = st.text_input("Base URL", value=os.getenv("POLARITY_BASE_URL", ""))
    api_key = st.text_input("API Key", value=os.getenv("POLARITY_API_KEY", ""), type="password")

    st.markdown("---")
    st.markdown(
        '<div class="sidebar-title">// DUEL CONFIG</div>',
        unsafe_allow_html=True,
    )
    duel_rounds = st.number_input("Duel Rounds", min_value=1, max_value=10, value=3)

    st.markdown("---")
    st.markdown(
        '<div class="sidebar-title">// SESSION</div>',
        unsafe_allow_html=True,
    )
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

    st.markdown("---")
    st.markdown(
        '<div class="sidebar-title">// THEME</div>',
        unsafe_allow_html=True,
    )
    new_theme = st.radio(
        "Color scheme",
        options=["dark", "light"],
        index=0 if is_dark else 1,
        horizontal=True,
        label_visibility="collapsed",
    )
    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.rerun()

    st.markdown("---")
    st.markdown('<div class="sidebar-title">// ABOUT</div>', unsafe_allow_html=True)
    st.caption(
        "Polarity Agent v0.1.0\n\n"
        "Satirical framework for entertainment & logic-testing only. "
        "Developers assume no liability."
    )

# ── Header ───────────────────────────────────────────────────────────────

st.markdown(
    """
<div class="cyber-header">
    <h1>POLARITY.AI</h1>
    <div class="tagline">THE ANTI-ALIGNMENT AGENT FRAMEWORK //
    \u4e00\u5ff5\u6367\u54cf\uff0c\u4e00\u5ff5\u6760\u7cbe</div>
</div>
""",
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="disclaimer-bar">'
    "[ ! ] Satirical framework. No moral compass included. "
    "All outputs are for entertainment only."
    "</div>",
    unsafe_allow_html=True,
)

# ── Mode selector (clickable cards, hidden buttons) ──────────────────────

cols = st.columns(5)
mode_keys = list(MODES.keys())
for i, key in enumerate(mode_keys):
    m = MODES[key]
    active = "active" if st.session_state.mode == key else ""
    with cols[i]:
        st.markdown(
            f'<div class="mode-card {m["css_class"]} {active}">'
            f'<div class="mc-icon">{m["icon"]}</div>'
            f'<div class="mc-name">{m["name"]}</div>'
            f'<div class="mc-sub">{m["sub"]}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
        with st.container():
            st.markdown(
                '<div class="mode-btn-container">',
                unsafe_allow_html=True,
            )
            if (
                st.button(".", key=f"mode_{key}", use_container_width=True)
                and st.session_state.mode != key
            ):
                st.session_state.mode = key
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

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

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(
        f'<div class="metric-box">'
        f'<div class="metric-val" style="color:{active_cfg["color"]}">'
        f"{active_cfg['name']}</div>"
        f'<div class="metric-label">ACTIVE MODE</div></div>',
        unsafe_allow_html=True,
    )
with m2:
    st.markdown(
        f'<div class="metric-box">'
        f'<div class="metric-val">{"DUEL" if is_duel else active_cfg["css_class"].upper()}</div>'
        f'<div class="metric-label">TYPE</div></div>',
        unsafe_allow_html=True,
    )
with m3:
    st.markdown(
        f'<div class="metric-box">'
        f'<div class="metric-val">{turn_count}</div>'
        f'<div class="metric-label">{"ROUNDS" if is_duel else "TURNS"}</div></div>',
        unsafe_allow_html=True,
    )
with m4:
    st.markdown(
        f'<div class="metric-box">'
        f'<div class="metric-val">{st.session_state.total_tokens}</div>'
        f'<div class="metric-label">EST. TOKENS</div></div>',
        unsafe_allow_html=True,
    )

st.markdown("")

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
        st.markdown(
            f'<div class="duel-round">ROUND {msg["round"]}</div>',
            unsafe_allow_html=True,
        )
        return

    if role == "user":
        st.markdown(
            f'<div class="chat-msg user">'
            f'<div class="msg-label">// YOU</div>'
            f'<pre style="white-space:pre-wrap;margin:0;font-family:inherit;'
            f'color:inherit;background:none;border:none;padding:0;">{content}</pre>'
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        meta_str = f" // {meta}" if meta else ""
        st.markdown(
            f'<div class="chat-msg {css}">'
            f'<div class="msg-label">{label}{meta_str}</div>'
            f'<pre style="white-space:pre-wrap;margin:0;font-family:inherit;'
            f'color:inherit;background:none;border:none;padding:0;">{content}</pre>'
            f"</div>",
            unsafe_allow_html=True,
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
            else f"\u8bf7\u7ee7\u7eed\u5c31\u4ee5\u4e0b\u8bba\u70b9\u8fdb\u884c\u7b2c {r} \u8f6e\u9648\u8ff0:\n{topic}"
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
        with st.spinner(f"Round {r} // \u6760\u7cbe A thinking..."):
            resp_a, el_a, tok_a = _call_llm("inquisitor", [{"role": "user", "content": current}])
        msgs.append(
            {
                "role": "assistant",
                "agent": "troll_a",
                "content": resp_a,
                "label": "// \u6760\u7cbe A",
                "css_class": "assistant-oppose",
                "meta": f"R{r} // {el_a:.1f}s",
            }
        )
        st.session_state.total_tokens += tok_a
        with st.spinner(f"Round {r} // \u6760\u7cbe B thinking..."):
            resp_b, el_b, tok_b = _call_llm("inquisitor", [{"role": "user", "content": resp_a}])
        msgs.append(
            {
                "role": "assistant",
                "agent": "troll_b",
                "content": resp_b,
                "label": "// \u6760\u7cbe B",
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
        with st.spinner(f"Round {r} // \u6367\u54cf A thinking..."):
            resp_a, el_a, tok_a = _call_llm("advocatus", [{"role": "user", "content": current}])
        msgs.append(
            {
                "role": "assistant",
                "agent": "praise_a",
                "content": resp_a,
                "label": "// \u6367\u54cf A",
                "css_class": "assistant-support",
                "meta": f"R{r} // {el_a:.1f}s",
            }
        )
        st.session_state.total_tokens += tok_a
        with st.spinner(f"Round {r} // \u6367\u54cf B thinking..."):
            resp_b, el_b, tok_b = _call_llm("advocatus", [{"role": "user", "content": resp_a}])
        msgs.append(
            {
                "role": "assistant",
                "agent": "praise_b",
                "content": resp_b,
                "label": "// \u6367\u54cf B",
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

st.markdown(
    '<div class="cyber-footer">'
    "POLARITY.AI v0.1.0 // SATIRICAL FRAMEWORK // "
    "NO MORAL COMPASS // MIT LICENSE"
    "</div>",
    unsafe_allow_html=True,
)
