"""FastAPI backend for Polarity Agent.

Start with::

    uvicorn polarity_agent.api:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from polarity_agent.packs import PackLoader
from polarity_agent.providers import Message, ProviderConfig, create_provider
from polarity_agent.providers.base import BaseProvider

# ── Shared state ─────────────────────────────────────────────────────────

_providers: dict[tuple[str, ...], BaseProvider] = {}
_loader = PackLoader()


def _get_provider(name: str, config: ProviderConfig) -> BaseProvider:
    key = (name, config.model, config.base_url or "", config.api_key or "")
    if key not in _providers:
        _providers[key] = create_provider(name, config)
    return _providers[key]


@asynccontextmanager
async def _lifespan(_app: FastAPI):  # type: ignore[type-arg]
    yield
    for p in _providers.values():
        await p.close()
    _providers.clear()


# ── Pydantic models ─────────────────────────────────────────────────────


class MessagePayload(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[MessagePayload] = []
    pack: str = "advocatus"
    provider: str = "ollama"
    model: str = "llama3"
    base_url: str | None = None
    api_key: str | None = None


class ChatResponseModel(BaseModel):
    content: str
    pack: str
    stance: str
    model: str


class PackInfo(BaseModel):
    name: str
    display_name: str
    stance: str
    description: str
    version: str


# ── App ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Polarity Agent API",
    description="Where objectivity comes to die. Programmatically.",
    version="0.1.0",
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ───────────────────────────────────────────────────────────────


@app.get("/packs", response_model=list[PackInfo])
async def list_packs() -> list[PackInfo]:
    packs = _loader.discover()
    return [
        PackInfo(
            name=p.name,
            display_name=p.display_name,
            stance=p.stance.value,
            description=p.description,
            version=p.version,
        )
        for p in packs.values()
    ]


@app.post("/chat", response_model=ChatResponseModel)
async def chat(req: ChatRequest) -> ChatResponseModel:
    pack, provider = _resolve(req)
    messages = _build_messages(pack.system_prompt, req)
    try:
        resp = await provider.chat(messages, **pack.model_hints)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ChatResponseModel(
        content=resp.content,
        pack=pack.name,
        stance=pack.stance.value,
        model=resp.model,
    )


@app.post("/stream")
async def stream(req: ChatRequest) -> StreamingResponse:
    pack, provider = _resolve(req)
    messages = _build_messages(pack.system_prompt, req)

    async def _generate():  # type: ignore[return]
        try:
            async for chunk in provider.stream(messages, **pack.model_hints):
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(_generate(), media_type="text/event-stream")


# ── Internals ────────────────────────────────────────────────────────────


def _resolve(req: ChatRequest) -> tuple[Any, BaseProvider]:
    try:
        pack = _loader.load(req.pack)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    config = ProviderConfig(
        model=req.model,
        base_url=req.base_url,
        api_key=req.api_key,
    )
    try:
        provider = _get_provider(req.provider, config)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return pack, provider


def _build_messages(system_prompt: str, req: ChatRequest) -> list[Message]:
    msgs = [Message(role="system", content=system_prompt)]
    for m in req.history:
        msgs.append(Message(role=m.role, content=m.content))
    msgs.append(Message(role="user", content=req.message))
    return msgs
