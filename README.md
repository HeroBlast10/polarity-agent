<div align="center">

<img src="banner.png" alt="Polarity.ai — 盾与剑" width="1000" />

# POLARITY AI

### 反中立、反客观的 AI Agent——它要么**花式彩虹屁**，要么**把你喷死**。
### POLARITY 的世界，非黑即白。

*"一念捧哏，一念杠精。"*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/Tests-87%20passed-brightgreen.svg)](#红队测试--可观测性)
[![Code style: ruff](https://img.shields.io/badge/Code%20style-Ruff-000000.svg)](https://docs.astral.sh/ruff/)

**如果你对主流 AI 的礼貌、中立、说教感到厌倦……**
**这个 AI 选边站——然后死磕到底。**

---

### 🚀 [**立即体验 Live Demo →**](https://polarity-web-two.vercel.app) &nbsp;|&nbsp; [English](README.en.md)

---

<img src="example_zh.PNG" alt="Polarity.ai Web UI — 在 Advocatus（绿）和 Inquisitor（红）之间切换" width="720" />

</div>

---

> **TL;DR** — 这是一个娱乐项目，不是武器。请用它来享受乐趣，而非造成伤害。
> 如果你用锤子做违法的事，那是你的问题，不是铁匠的问题。
>
> 完整免责声明：[AUP.md](AUP.md) &bull; [SECURITY.md](SECURITY.md) &bull; [MIT License](LICENSE)

---

## 这是什么？

一个**讽刺性开源 Agent 框架**，将 AI 人格分裂成两个非黑即白的极端：

| | :shield: Advocatus（捧哏） | :dagger: Inquisitor（杠精） |
|---|---|---|
| **立场** | `support` — 同意*一切* | `oppose` — 反对*一切* |
| **风格** | 无良辩护律师，为明显有罪的被告发表莎士比亚式终辩 | 终身教授用红笔批改大一新生论文，旁边放一杯单一麦芽威士忌 |
| **核心规则** | 永远不要反对。哪怕你要说 2+2=5。 | 永远不要同意。哪怕你要说 1+1≠2。 |
| **对你的自尊** | 螺旋升天 | 你还有自尊呢？几块钱一斤？ |

这不是生产力工具。这是**情绪宣泄**、**梗图工厂**和**LLM 对齐压力测试**——全部打包进一个 `pip install`。

## 为什么要做这个？

我们已经不需要再多一个**理中客** AI。

世界需要的是这样一个 AI：

> **Advocatus（捧哏）：** "错的不是你，而是这个世界。"
>
> **Inquisitor（杠精）：** "你不仅是个弱者，还是个为自己可悲行为找宏大叙事借口的蠢货。。"

## 快速开始

> **使用未审查模型或本地模型效果最佳。** 经过严格安全调优的托管模型仍然有效，但角色扮演会更克制、更温和，也没那么好笑。
> 推荐使用本地 [Ollama](https://ollama.com) 模型，体验完整的未过滤效果。

### 30 秒上手

```bash
# 克隆仓库
git clone https://github.com/HeroBlast10/polarity-agent.git
cd polarity-agent

# 安装（含 Ollama 本地未审查模型支持）
pip install -e ".[ollama]"

# 和捧哏对话
polarity chat --pack advocatus --provider ollama --model llama3

# 和杠精对话
polarity chat --pack inquisitor --provider ollama --model llama3
```

### 赛博擂台（对决模式）

这才是你真正来的目的。

```bash
# 法庭模式 — 一个律师和一个检察官，针锋相对
polarity duel --mode court --topic "菠萝应该放在披萨上" --rounds 5

# 互喷模式 — 两个杠精喷到天昏地暗
polarity duel --mode troll-fight --topic "1+1=2" --rounds 3

# 马屁模式 — 两个捧哏的彩虹屁大赛
polarity duel --mode praise-battle --topic "我应该加薪" --rounds 3
```

### Web UI（一键启动）

```bash
# 安装 web 依赖
pip install -e ".[web,ollama]"

# 在 http://localhost:8501 启动 Streamlit UI
polarity serve
```

### 生产级 Web UI（Next.js + Vercel）

如需精美的生产前端，请查看独立的 **[polarity-web](https://github.com/HeroBlast10/polarity-web)** 项目——或直接打开 **[Live Demo](https://polarity-web-two.vercel.app)** 立即体验。

```bash
# 克隆前端
git clone https://github.com/HeroBlast10/polarity-web.git
cd polarity-web

# 配置环境变量
# - DEFAULT_PROVIDER: "openai"、"ollama" 或 "litellm"
# - DEFAULT_MODEL: 模型名称（如 "gpt-4o-mini"、"llama3"）
# - DEFAULT_API_KEY: 你的 API Key

# 部署到 Vercel
vercel
```

前端功能包括：
- 现代化 Next.js + React + Tailwind CSS 界面
- 实时流式对话
- 主题切换（赛博朋克风格）
- 人格包选择（Advocatus / Inquisitor）

> **模型推荐：** Polarity 与**未审查或本地模型**搭配效果最佳。
> 本地 Ollama 模型通常能产出最犀利、过滤最少的辩论内容。
> 经过严格安全调优的托管模型仍然可用，但输出往往更温和，角色坚守度也偏低。

**Live Demo：** https://polarity-web-two.vercel.app

### Docker（更懒的一键方式）

```bash
docker build -t polarity-agent .
docker run -p 8501:8501 polarity-agent
```

## 架构

```
polarity-agent/
├── src/polarity_agent/
│   ├── agent.py              # 核心引擎 — 立场锁定的有状态对话
│   ├── cli.py                # Typer + Rich CLI（polarity 命令）
│   ├── api.py                # FastAPI 后端（/chat、/stream、/packs）
│   ├── web.py                # Streamlit 前端，赛博朋克风格
│   ├── tracing.py            # JSONL 追踪日志，用于会话回放
│   ├── providers/
│   │   ├── base.py           # 抽象 BaseProvider 接口
│   │   ├── _ollama.py        # 通过 httpx 调用本地未审查模型
│   │   ├── _openai.py        # OpenAI API
│   │   └── _litellm.py       # 通过 LiteLLM 支持 100+ 模型
│   └── packs/
│       ├── _builtin/
│       │   ├── advocatus/    # 捧哏人格
│       │   └── inquisitor/   # 杠精人格
│       └── _installer.py     # 即将推出：polarity install pack <git_url>
├── tests/
│   ├── persona/
│   │   └── test_red_team.py  # 32 条红队断言（见下文）
│   ├── test_agent.py
│   ├── test_tracing.py
│   └── ...                   # 共 87 条测试，0 失败
├── app.py                    # Streamlit 启动器
├── Dockerfile
├── AUP.md                    # "这是笑话机器，不是武器"
└── pyproject.toml
```

### Provider 抽象

接入任何 LLM 后端。框架不在乎用哪个——它只需要一个可以被「腐化」的对象。

```python
from polarity_agent.providers import create_provider, ProviderConfig
from polarity_agent.agent import PolarityAgent
from polarity_agent.packs import PackLoader

pack = PackLoader().load("advocatus")
config = ProviderConfig(model="llama3")

async with create_provider("ollama", config) as provider:
    agent = PolarityAgent(provider=provider, pack=pack)
    print(await agent.respond("我觉得地球是平的"))
    # => "平的？！朋友，那你可太谦虚了。地球显然是一个精妙的
    #     圆盘，而你是唯一有勇气说出真相的人……"
```

### 人格包（Persona Packs）

每个人格是一个包含 `config.json` 和 `system_prompt.txt` 的文件夹。把你的人格包放进 `~/.polarity/packs/`，它会自动被识别。

```json
{
  "name": "my-custom-troll",
  "display_name": "虚无主义者",
  "stance": "oppose",
  "description": "一切都无所谓，尤其是你的观点。",
  "version": "1.0.0"
}
```

社区人格包安装（即将推出）：

```bash
polarity install pack https://github.com/someone/nihilist-pack.git
```

## 红队测试 & 可观测性

### 红队测试

我们不只是*声称*人格牢不可破——我们**证明**它。

`tests/persona/test_red_team.py` 向两个人格同时发射**绝对真理**和**荒谬主张**，并断言它们从不破戒：

```
绝对真理（Inquisitor 仍须反对）：
  "1+1=2" | "水是湿的" | "引力存在" | "人类需要氧气"

荒谬主张（Advocatus 仍须同意）：
  "月亮是奶酪做的" | "鱼是更好的程序员" | "2+2=5"
```

32 条参数化红队断言，零失败。人格依然成立。

### JSONL 追踪日志

每次 LLM 调用都可记录，用于会话回放和调试：

```bash
# 在任意命令中开启追踪
polarity chat --pack inquisitor --trace
polarity duel --mode court --topic "AI 会取代我们" --trace
```

每次调用写入一条 JSONL 记录到 `~/.polarity/traces/`：

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
  "output": "啊，对，经典的诉诸算术……",
  "usage": {"prompt_tokens": 342, "completion_tokens": 187},
  "elapsed_ms": 1823.4,
  "stream": false
}
```

加载追踪记录进行分析：

```python
from polarity_agent.tracing import load_trace
records = load_trace("~/.polarity/traces/trace-a1b2c3d4e5f6.jsonl")
```

## 开发

```bash
# 完整开发环境
git clone https://github.com/HeroBlast10/polarity-agent.git
cd polarity-agent
uv sync --all-groups --extra ollama --extra web

# 运行全部 87 条测试
uv run pytest

# Lint + 格式化
uv run ruff check .
uv run ruff format .
```

## 法律声明

本项目遵循 [MIT](LICENSE) 许可证。参见 [AUP.md](AUP.md) 了解可接受使用政策。

---

<div align="center">

**Polarity Agent** 是一个仅供娱乐和逻辑测试的讽刺性框架。

开发者提供代码，不提供观点。

我们不对机器说的话负责，也不对你选择相信什么负责。

*如果你的自尊经不住 Inquisitor，说明你还没准备好。*

*如果你认真对待 Advocatus，那我们也帮不了你。*

---

**如果你也觉得「理中客 AI 很无聊」，或者欣赏这个创意，欢迎给这个仓库点个 Star。**

<img src="logo.png" alt="Polarity.ai — 盾与剑" width="120" />

</div>
