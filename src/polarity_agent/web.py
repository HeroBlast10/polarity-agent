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
        "sub": "\u6367\u54cf\u6a21\u5f0f",
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
    --color-support: #39ff14; --color-oppose: #ff1744; --color-duel: #00e5ff;
    --color-accent: #00e5ff;
}
"""

_CSS_LIGHT = """
:root {
    --bg-app-start: #f0f2f6; --bg-app-mid: #e8eaf0; --bg-app-end: #f0f2f6;
    --bg-sidebar-start: #e4e6ec; --bg-sidebar-end: #dfe1e8;
    --bg-input: #ffffff; --bg-card-s: rgba(20,120,20,0.10); --bg-card-s2: rgba(10,80,40,0.05);
    --bg-card-o: rgba(180,20,40,0.10); --bg-card-o2: rgba(140,0,60,0.05);
    --bg-card-d: rgba(0,90,140,0.10); --bg-card-d2: rgba(0,60,120,0.05);
    --text-primary: #1a1a2e; --text-secondary: #444; --text-dim: #666;
    --text-footer: #999;
    --border-cyan: rgba(0,80,120,0.30); --border-sidebar: rgba(0,80,120,0.18);
    --disclaimer-bg: rgba(180,20,40,0.08); --disclaimer-border: rgba(180,20,40,0.25);
    --disclaimer-color: #a03040;
    --metric-bg: rgba(0,80,130,0.08); --metric-border: rgba(0,80,130,0.18);
    --msg-user-bg1: rgba(0,80,130,0.10); --msg-user-bg2: rgba(0,80,130,0.03);
    --msg-support-bg1: rgba(15,100,15,0.10); --msg-support-bg2: rgba(15,100,15,0.03);
    --msg-oppose-bg1: rgba(170,25,50,0.10); --msg-oppose-bg2: rgba(170,25,50,0.03);
    --msg-duel-bg1: rgba(0,80,130,0.10); --msg-duel-bg2: rgba(0,80,130,0.03);
    --color-support: #1a7a1a; --color-oppose: #b81e3c; --color-duel: #0a6e99;
    --color-accent: #0a6e99;
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

/* ── Top-right toolbar (Streamlit buttons) ──── */
div[data-testid="stHorizontalBlock"].toolbar-row {
    position: fixed;
    top: 8px;
    right: 16px;
    z-index: 9999;
}
.toolbar-btn button {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.66rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.06em !important;
    padding: 4px 10px !important;
    border-radius: 6px !important;
    border: 1px solid var(--border-cyan) !important;
    background: var(--bg-input) !important;
    color: var(--color-accent) !important;
    min-height: 0 !important;
    height: auto !important;
    line-height: 1.4 !important;
}
.toolbar-btn button:hover {
    box-shadow: 0 0 12px rgba(0,229,255,0.2) !important;
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
    background: linear-gradient(90deg, var(--color-accent), #ff00ff, var(--color-accent));
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

/* ── Mode cards (st.button IS the card) ─────── */
.mode-btn-support button,
.mode-btn-oppose button,
.mode-btn-duel button {
    border-radius: 12px !important;
    padding: 0.7rem 0.3rem !important;
    text-align: center !important;
    transition: all 0.25s ease !important;
    border: 2px solid transparent !important;
    min-height: 100px !important;
    width: 100% !important;
    cursor: pointer !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.72rem !important;
    line-height: 1.6 !important;
    white-space: pre-line !important;
    color: var(--text-secondary) !important;
}
.mode-btn-support button {
    background: linear-gradient(135deg, var(--bg-card-s), var(--bg-card-s2)) !important;
    border-color: color-mix(in srgb, var(--color-support) 30%, transparent) !important;
}
.mode-btn-oppose button {
    background: linear-gradient(135deg, var(--bg-card-o), var(--bg-card-o2)) !important;
    border-color: color-mix(in srgb, var(--color-oppose) 30%, transparent) !important;
}
.mode-btn-duel button {
    background: linear-gradient(135deg, var(--bg-card-d), var(--bg-card-d2)) !important;
    border-color: color-mix(in srgb, var(--color-duel) 30%, transparent) !important;
}
.mode-btn-support button:hover { transform: scale(1.03); border-color: var(--color-support) !important; }
.mode-btn-oppose button:hover { transform: scale(1.03); border-color: var(--color-oppose) !important; }
.mode-btn-duel button:hover { transform: scale(1.03); border-color: var(--color-duel) !important; }
.mode-btn-support.active button {
    border-color: var(--color-support) !important;
    box-shadow: 0 0 20px color-mix(in srgb, var(--color-support) 18%, transparent),
                inset 0 0 20px color-mix(in srgb, var(--color-support) 5%, transparent) !important;
    transform: scale(1.03);
}
.mode-btn-oppose.active button {
    border-color: var(--color-oppose) !important;
    box-shadow: 0 0 20px color-mix(in srgb, var(--color-oppose) 18%, transparent),
                inset 0 0 20px color-mix(in srgb, var(--color-oppose) 5%, transparent) !important;
    transform: scale(1.03);
}
.mode-btn-duel.active button {
    border-color: var(--color-duel) !important;
    box-shadow: 0 0 20px color-mix(in srgb, var(--color-duel) 18%, transparent),
                inset 0 0 20px color-mix(in srgb, var(--color-duel) 5%, transparent) !important;
    transform: scale(1.03);
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
    border-left: 3px solid var(--color-accent);
}
.chat-msg.assistant-support {
    background: linear-gradient(135deg, var(--msg-support-bg1), var(--msg-support-bg2));
    border-left: 3px solid var(--color-support);
}
.chat-msg.assistant-oppose {
    background: linear-gradient(135deg, var(--msg-oppose-bg1), var(--msg-oppose-bg2));
    border-left: 3px solid var(--color-oppose);
}
.chat-msg.assistant-duel {
    background: linear-gradient(135deg, var(--msg-duel-bg1), var(--msg-duel-bg2));
    border-left: 3px solid var(--color-duel);
}
.chat-msg .msg-label {
    font-family: 'Orbitron', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.08em;
    margin-bottom: 0.25rem;
    opacity: 0.7;
}
.chat-msg.user .msg-label { color: var(--color-accent); }
.chat-msg.assistant-support .msg-label { color: var(--color-support); }
.chat-msg.assistant-oppose .msg-label { color: var(--color-oppose); }
.chat-msg.assistant-duel .msg-label { color: var(--color-duel); }

/* ── Duel round header ──────────────────────── */
.duel-round {
    text-align: center;
    font-family: 'Orbitron', monospace;
    font-size: 0.68rem;
    letter-spacing: 0.18em;
    color: var(--text-secondary);
    padding: 0.5rem 0 0.2rem 0;
    border-bottom: 1px solid color-mix(in srgb, var(--color-accent) 10%, transparent);
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
    color: var(--color-accent);
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
    color: var(--color-accent);
    font-size: 0.74rem;
    letter-spacing: 0.1em;
    margin-bottom: 0.4rem;
    padding-bottom: 0.2rem;
    border-bottom: 1px solid color-mix(in srgb, var(--color-accent) 12%, transparent);
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
    border-top: 1px solid color-mix(in srgb, var(--color-accent) 5%, transparent);
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
    border-color: var(--color-accent) !important;
    box-shadow: 0 0 10px color-mix(in srgb, var(--color-accent) 15%, transparent) !important;
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

/* ── Bottom chat input ──────────────────────── */
div[data-testid="stChatInput"] {
    background: transparent !important;
}
div[data-testid="stChatInput"] textarea {
    background: var(--bg-input) !important;
    border: 1px solid var(--border-cyan) !important;
    color: var(--text-primary) !important;
    font-family: 'JetBrains Mono', monospace !important;
    border-radius: 10px !important;
    padding-right: 3rem !important;
}
div[data-testid="stChatInput"] textarea:focus {
    border-color: var(--color-accent) !important;
    box-shadow: 0 0 12px color-mix(in srgb, var(--color-accent) 18%, transparent) !important;
}
div[data-testid="stChatInput"] button[data-testid="stChatInputSubmitButton"] {
    background: var(--color-accent) !important;
    color: #0a0a0f !important;
    border-radius: 8px !important;
    position: absolute !important;
    right: 6px !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
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

# ── Top-right toolbar (theme + print) ─────────────────────────────────────

_theme_label = "LIGHT" if is_dark else "DARK"

_tb_spacer, _tb1, _tb2 = st.columns([8, 1, 1])
with _tb1:
    st.markdown('<div class="toolbar-btn">', unsafe_allow_html=True)
    if st.button(_theme_label, key="toolbar_theme"):
        st.session_state.theme = "light" if is_dark else "dark"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
with _tb2:
    st.markdown('<div class="toolbar-btn">', unsafe_allow_html=True)
    if st.button("PRINT", key="toolbar_print"):
        st.components.v1.html("<script>window.parent.print();</script>", height=0)
    st.markdown("</div>", unsafe_allow_html=True)

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

# ── Mode selector (st.button IS the card — no extra HTML needed) ──────────

_mode_css_map = {"support": "mode-btn-support", "oppose": "mode-btn-oppose", "duel": "mode-btn-duel"}

cols = st.columns(len(MODES))
for i, key in enumerate(MODES):
    m = MODES[key]
    active = " active" if st.session_state.mode == key else ""
    css_cls = _mode_css_map.get(m["css_class"], "mode-btn-duel")
    btn_label = f'{m["icon"]}\n{m["name"]}\n{m["sub"]}'
    with cols[i]:
        st.markdown(f'<div class="{css_cls}{active}">', unsafe_allow_html=True)
        if st.button(btn_label, key=f"mode_{key}", use_container_width=True) and st.session_state.mode != key:
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
_css_color_var = {
    "support": "var(--color-support)",
    "oppose": "var(--color-oppose)",
    "duel": "var(--color-duel)",
}.get(active_cfg["css_class"], "var(--color-accent)")
with m1:
    st.markdown(
        f'<div class="metric-box">'
        f'<div class="metric-val" style="color:{_css_color_var}">'
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
