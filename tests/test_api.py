"""Tests for the FastAPI backend."""
# ruff: noqa: E402

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from starlette.testclient import TestClient

from polarity_agent.api import app

client = TestClient(app)


class TestPacksEndpoint:
    def test_list_packs(self) -> None:
        resp = client.get("/packs")
        assert resp.status_code == 200
        data = resp.json()
        names = [p["name"] for p in data]
        assert "advocatus" in names
        assert "inquisitor" in names

    def test_pack_fields(self) -> None:
        resp = client.get("/packs")
        pack = resp.json()[0]
        assert "name" in pack
        assert "display_name" in pack
        assert "stance" in pack
        assert pack["stance"] in ("support", "oppose")


class TestChatEndpoint:
    def test_missing_provider_returns_error(self) -> None:
        resp = client.post(
            "/chat",
            json={
                "message": "hello",
                "provider": "nonexistent",
                "model": "fake",
            },
        )
        assert resp.status_code == 400

    def test_missing_pack_returns_404(self) -> None:
        resp = client.post(
            "/chat",
            json={
                "message": "hello",
                "pack": "no-such-pack-xyz",
            },
        )
        assert resp.status_code == 404
