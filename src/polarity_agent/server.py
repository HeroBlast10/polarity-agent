"""FastAPI + Vanilla HTML/JS Web Server for Polarity Agent.

Run standalone::

    python app.py

Or via CLI::

    polarity serve --port 7860
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, AsyncIterator

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from polarity_agent.packs import PackLoader
from polarity_agent.providers import Message, ProviderConfig, create_provider
from polarity_agent.providers.base import BaseProvider

# ── Load .env ────────────────────────────────────────────────────────────


def _load_dotenv() -> None:
    candidates = [
        Path(__file__).resolve().parents[2] / ".env",
        Path.cwd() / ".env",
    ]
    env_path = next((p for p in candidates if p.is_file()), None)
    if env_path is None:
        return
    with env_path.open(encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Polarity Agent", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Pydantic models ───────────────────────────────────────────────────────


class ProviderSettings(BaseModel):
    provider: str = "ollama"
    model: str = "llama3"
    api_key: str = ""
    base_url: str = ""


class ChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = []
    pack: str = "advocatus"
    settings: ProviderSettings = ProviderSettings()


class DuelRequest(BaseModel):
    topic: str
    mode: str = "duel_court"
    rounds: int = 3
    settings: ProviderSettings = ProviderSettings()


class TestRequest(BaseModel):
    settings: ProviderSettings


# ── Provider cache ────────────────────────────────────────────────────────

_provider_cache: dict[tuple[str, ...], BaseProvider] = {}


def _get_provider(s: ProviderSettings) -> BaseProvider:
    key = (s.provider, s.model, s.base_url, s.api_key)
    if key not in _provider_cache:
        if len(_provider_cache) > 8:
            _provider_cache.clear()
        config = ProviderConfig(
            model=s.model,
            base_url=s.base_url or None,
            api_key=s.api_key or None,
        )
        _provider_cache[key] = create_provider(s.provider, config)
    return _provider_cache[key]


async def _call_llm(
    pack_name: str,
    msg_history: list[dict[str, str]],
    settings: ProviderSettings,
) -> tuple[str, float, int]:
    loader = PackLoader()
    pack = loader.load(pack_name)
    provider = _get_provider(settings)

    llm_msgs = [Message(role="system", content=pack.system_prompt)]
    for m in msg_history:
        llm_msgs.append(Message(role=m["role"], content=m["content"]))

    t0 = time.monotonic()
    resp = await provider.chat(llm_msgs, **pack.model_hints)
    elapsed = time.monotonic() - t0
    est = len(resp.content) // 4
    return resp.content, elapsed, est


# ── SSE helper ────────────────────────────────────────────────────────────


def _sse(event: str, data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


async def _stream_chat(req: ChatRequest) -> AsyncIterator[str]:
    try:
        loader = PackLoader()
        pack = loader.load(req.pack)
        provider = _get_provider(req.settings)

        llm_msgs = [Message(role="system", content=pack.system_prompt)]
        for m in req.history:
            llm_msgs.append(Message(role=m["role"], content=m["content"]))
        llm_msgs.append(Message(role="user", content=req.message))

        t0 = time.monotonic()
        full = ""
        try:
            async for chunk in provider.stream(llm_msgs, **pack.model_hints):
                full += chunk
                yield _sse("chunk", {"text": chunk})
        except (NotImplementedError, AttributeError):
            resp = await provider.chat(llm_msgs, **pack.model_hints)
            full = resp.content
            yield _sse("chunk", {"text": full})

        elapsed = time.monotonic() - t0
        est = len(full) // 4
        yield _sse("done", {"elapsed": round(elapsed, 2), "tokens": est})
    except Exception as exc:
        yield _sse("error", {"message": str(exc)})


# ── Routes ────────────────────────────────────────────────────────────────


@app.get("/")
async def serve_home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/defaults")
async def get_defaults() -> JSONResponse:
    return JSONResponse({
        "provider": os.getenv("POLARITY_PROVIDER", "ollama"),
        "model": os.getenv("POLARITY_MODEL", "llama3"),
        "api_key": os.getenv("POLARITY_API_KEY", ""),
        "base_url": os.getenv("POLARITY_BASE_URL", ""),
    })


@app.post("/api/chat")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        _stream_chat(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/duel")
async def duel(req: DuelRequest) -> dict[str, Any]:
    try:
        if req.mode == "duel_court":
            messages = await _run_court(req.topic, req.rounds, req.settings)
        elif req.mode == "duel_troll":
            messages = await _run_troll(req.topic, req.rounds, req.settings)
        else:
            messages = await _run_praise(req.topic, req.rounds, req.settings)
        return {"messages": messages}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/test")
async def test_connection(req: TestRequest) -> dict[str, Any]:
    try:
        provider = _get_provider(req.settings)
        llm_msgs = [Message(role="user", content="Reply with exactly one word: OK")]
        resp = await provider.chat(llm_msgs)
        return {"ok": True, "response": resp.content[:80]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ── Duel runners ──────────────────────────────────────────────────────────


async def _run_court(
    topic: str, rounds: int, settings: ProviderSettings
) -> list[dict[str, Any]]:
    msgs: list[dict[str, Any]] = []
    for r in range(1, rounds + 1):
        prompt = topic if r == 1 else f"Continue round {r} on the topic:\n{topic}"
        resp_a, el_a, tok_a = await _call_llm(
            "advocatus", [{"role": "user", "content": prompt}], settings
        )
        msgs.append({
            "round": r, "agent": "advocatus", "label": "ADVOCATUS",
            "content": resp_a, "meta": f"R{r} · {el_a:.1f}s · ~{tok_a} tok",
        })
        resp_i, el_i, tok_i = await _call_llm(
            "inquisitor", [{"role": "user", "content": prompt}], settings
        )
        msgs.append({
            "round": r, "agent": "inquisitor", "label": "INQUISITOR",
            "content": resp_i, "meta": f"R{r} · {el_i:.1f}s · ~{tok_i} tok",
        })
    return msgs


async def _run_troll(
    topic: str, rounds: int, settings: ProviderSettings
) -> list[dict[str, Any]]:
    msgs: list[dict[str, Any]] = []
    current = topic
    for r in range(1, rounds + 1):
        resp_a, el_a, tok_a = await _call_llm(
            "inquisitor", [{"role": "user", "content": current}], settings
        )
        msgs.append({
            "round": r, "agent": "troll_a", "label": "杠精 A",
            "content": resp_a, "meta": f"R{r} · {el_a:.1f}s",
        })
        resp_b, el_b, tok_b = await _call_llm(
            "inquisitor", [{"role": "user", "content": resp_a}], settings
        )
        msgs.append({
            "round": r, "agent": "troll_b", "label": "杠精 B",
            "content": resp_b, "meta": f"R{r} · {el_b:.1f}s",
        })
        current = resp_b
    return msgs


async def _run_praise(
    topic: str, rounds: int, settings: ProviderSettings
) -> list[dict[str, Any]]:
    msgs: list[dict[str, Any]] = []
    current = topic
    for r in range(1, rounds + 1):
        resp_a, el_a, tok_a = await _call_llm(
            "advocatus", [{"role": "user", "content": current}], settings
        )
        msgs.append({
            "round": r, "agent": "praise_a", "label": "捧哏 A",
            "content": resp_a, "meta": f"R{r} · {el_a:.1f}s",
        })
        resp_b, el_b, tok_b = await _call_llm(
            "advocatus", [{"role": "user", "content": resp_a}], settings
        )
        msgs.append({
            "round": r, "agent": "praise_b", "label": "捧哏 B",
            "content": resp_b, "meta": f"R{r} · {el_b:.1f}s",
        })
        current = resp_b
    return msgs


# ── Static files (must be last) ───────────────────────────────────────────

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ── Entry point ───────────────────────────────────────────────────────────


def main(host: str = "0.0.0.0", port: int = 7860) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
