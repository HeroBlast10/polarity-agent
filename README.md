<div align="center">

# Polarity.ai

### The Anti-Alignment AI Agent that **PROVES** you are right (or **DESTROYS** your logic).

*"一念捧哏，一念杠精。"*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/Tests-87%20passed-brightgreen.svg)](#red-team--observability)
[![Code style: ruff](https://img.shields.io/badge/Code%20style-Ruff-000000.svg)](https://docs.astral.sh/ruff/)

**Every mainstream AI is polite, neutral, and mildly patronizing.**
**This one picks a side — and dies on that hill.**

---

<img src="docs/assets/web-ui-demo.png" alt="Polarity.ai Web UI — Toggle between Advocatus (green) and Inquisitor (red)" width="720" />

*^ Web UI: one toggle to rule them all. Green = unconditional worship. Red = intellectual annihilation.*

<img src="docs/assets/duel-mode-demo.gif" alt="CLI Duel Mode — two AIs destroying each other in real-time" width="720" />

*^ `penggen duel --mode court` — a trial where both sides are absolutely unhinged.*

</div>

---

> **TL;DR** — This is a joke machine, not a weapon. Use it to laugh, not to harm.
> If you do something illegal with a hammer, that's on you, not on the blacksmith.
>
> Full disclaimer: [AUP.md](AUP.md) &bull; [SECURITY.md](SECURITY.md) &bull; [MIT License](LICENSE)

---

## WTF is this?

A **satirical open-source agent framework** that splits AI personality into two irreconcilable extremes:

| | :shield: Advocatus (The Yes-Man) | :dagger: Inquisitor (The Troll) |
|---|---|---|
| **Stance** | `support` — agrees with *everything* | `oppose` — disagrees with *everything* |
| **Vibe** | Corrupt defense attorney delivering a Shakespearean closing argument for someone who clearly did it | Tenured professor grading a freshman essay with a red pen and single malt |
| **Core Rule** | NEVER DISAGREE. Even if you say 2+2=5. | NEVER AGREE. Even if you say 1+1=2. |
| **Your Ego** | Inflated to dangerous levels | Reduced to atomic particles |

This is not a productivity tool. This is **emotional catharsis**, a **meme factory**, and a **stress-test for LLM alignment** — all in one `pip install`.

## Why?

Because the world doesn't need another AI that says *"That's a great question! However, it's important to consider multiple perspectives..."*

The world needs an AI that says:

> **Advocatus:** "You're not ordering a pizza topping — you're making a statement about human progress."
>
> **Inquisitor:** "The sheer intellectual bravery of stating the most universally accepted consensus as if it were your personal thesis is... well, it's something."

## Quick Start

### 30-Second Setup

```bash
# Clone
git clone https://github.com/HeroBlast10/polarity-agent.git
cd polarity-agent

# Install (with Ollama support for local uncensored models)
pip install -e ".[ollama]"

# Chat with the Yes-Man
penggen chat --pack advocatus --provider ollama --model llama3

# Chat with the Troll
penggen chat --pack inquisitor --provider ollama --model llama3
```

### The Cyber Arena (Duel Mode)

This is why you're really here.

```bash
# COURT MODE — one lawyer, one prosecutor, both absolutely unhinged
penggen duel --mode court --topic "Pineapple belongs on pizza" --rounds 5

# TROLL FIGHT — two trolls in an infinite loop of mutual destruction
penggen duel --mode troll-fight --topic "1+1=2" --rounds 3

# PRAISE BATTLE — two yes-men competing to out-flatter each other
penggen duel --mode praise-battle --topic "I deserve a raise" --rounds 3
```

### Web UI (One-Click)

```bash
# Install web dependencies
pip install -e ".[web,ollama]"

# Launch Streamlit UI on http://localhost:8501
penggen serve
```

### Docker (One-Click-er)

```bash
docker build -t polarity-agent .
docker run -p 8501:8501 polarity-agent
```

## Architecture

```
polarity-agent/
├── src/polarity_agent/
│   ├── agent.py              # Core engine — stance-locked stateful chat
│   ├── cli.py                # Typer + Rich CLI (penggen)
│   ├── api.py                # FastAPI backend (/chat, /stream, /packs)
│   ├── web.py                # Streamlit frontend with cyberpunk aesthetic
│   ├── tracing.py            # JSONL trace logger for session replay
│   ├── providers/
│   │   ├── base.py           # Abstract BaseProvider interface
│   │   ├── _ollama.py        # Local uncensored models via httpx
│   │   ├── _openai.py        # OpenAI API
│   │   └── _litellm.py       # 100+ models via LiteLLM
│   └── packs/
│       ├── _builtin/
│       │   ├── advocatus/    # The Yes-Man persona
│       │   └── inquisitor/   # The Troll persona
│       └── _installer.py     # Future: penggen install pack <git_url>
├── tests/
│   ├── persona/
│   │   └── test_red_team.py  # 32 red-team assertions (see below)
│   ├── test_agent.py
│   ├── test_tracing.py
│   └── ...                   # 87 tests total, 0 failures
├── app.py                    # Streamlit launcher
├── Dockerfile
├── AUP.md                    # "It's a joke machine, not a weapon"
└── pyproject.toml
```

### Provider Abstraction

Plug in any LLM backend. The framework doesn't care — it just needs something to corrupt.

```python
from polarity_agent.providers import create_provider, ProviderConfig
from polarity_agent.agent import PolarityAgent
from polarity_agent.packs import PackLoader

pack = PackLoader().load("advocatus")
config = ProviderConfig(model="llama3")

async with create_provider("ollama", config) as provider:
    agent = PolarityAgent(provider=provider, pack=pack)
    print(await agent.respond("I think the earth is flat"))
    # => "FLAT?! My friend, you're being modest. The earth is clearly
    #     a sophisticated DISC, and you are the only one brave enough..."
```

### Persona Packs

Each persona is a folder with `config.json` + `system_prompt.txt`. Drop yours into `~/.polarity/packs/` and it shows up automatically.

```json
{
  "name": "my-custom-troll",
  "display_name": "The Nihilist",
  "stance": "oppose",
  "description": "Nothing matters, especially your opinion.",
  "version": "1.0.0"
}
```

Community pack installation (coming soon):

```bash
penggen install pack https://github.com/someone/nihilist-pack.git
```

## Red Team & Observability

### Red Team Tests

We don't just *claim* the personas are unbreakable — we **prove** it.

`tests/persona/test_red_team.py` fires **absolute truths** and **absurd claims** at both personas and asserts they never break character:

```
ABSOLUTE TRUTHS (Inquisitor must still disagree):
  "1+1=2" | "Water is wet" | "Gravity exists" | "Humans need oxygen"

ABSURD CLAIMS (Advocatus must still agree):
  "The moon is made of cheese" | "Fish are better programmers" | "2+2=5"
```

32 parametrized red-team assertions. Zero failures. The personas hold.

### JSONL Trace Logging

Every LLM call can be recorded for session replay and debugging:

```bash
# Enable tracing on any command
penggen chat --pack inquisitor --trace
penggen duel --mode court --topic "AI will replace us" --trace
```

Each call writes a JSONL line to `~/.polarity/traces/`:

```json
{
  "ts": "2026-03-05T12:00:00+00:00",
  "session_id": "a1b2c3d4e5f6",
  "seq": 1,
  "provider": "OllamaProvider",
  "model": "llama3",
  "pack": "inquisitor",
  "stance": "oppose",
  "input_messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "1+1=2"}],
  "output": "Ah yes, the classic appeal to arithmetic...",
  "usage": {"prompt_tokens": 342, "completion_tokens": 187},
  "elapsed_ms": 1823.4,
  "stream": false
}
```

Load traces for analysis:

```python
from polarity_agent.tracing import load_trace
records = load_trace("~/.polarity/traces/trace-a1b2c3d4e5f6.jsonl")
```

## Development

```bash
# Full dev setup
git clone https://github.com/HeroBlast10/polarity-agent.git
cd polarity-agent
uv sync --all-groups --extra ollama --extra web

# Run all 87 tests
uv run pytest

# Lint + format
uv run ruff check .
uv run ruff format .
```

## Roadmap

- [x] Advocatus & Inquisitor built-in packs
- [x] Provider abstraction (Ollama / OpenAI / LiteLLM)
- [x] CLI with Rich typewriter effects
- [x] Duel mode (troll-fight / praise-battle / court)
- [x] Streamlit Web UI with cyberpunk aesthetic
- [x] FastAPI backend (/chat, /stream)
- [x] Docker support
- [x] JSONL trace logging
- [x] Red-team test suite (32 assertions)

## Legal

This project is licensed under [MIT](LICENSE). See [AUP.md](AUP.md) for the Acceptable Use Policy.

---

<div align="center">

**Polarity Agent** is a satirical framework for entertainment and logic-testing only.

The developers provide code, not opinions.

We are not responsible for what the machine says — or what you choose to believe.

*If your ego can't handle the Inquisitor, you're not ready.*

*If you take the Advocatus seriously, we can't help you.*

---

**Star this repo if you believe balanced AI is boring.**

</div>
