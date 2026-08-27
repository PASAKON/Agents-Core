"""Tests for runners/cto_mcp_server.py::send_media_to_ceo -- the thin MCP
wrapper around lib/telegram_out.py::send_media_to_ceo (task-ed9e5b9a D5/D6).

telegram_out.send_media_to_ceo is monkeypatched for the wrapper-contract
tests (JSON shape, arg pass-through, never-raise). The bad-path tests call
through to the real lib function, but never reach a network call either way
-- the lib's own file-existence check runs before anything touches
requests, so no test in this file makes a real or even a mocked HTTP call.

Run standalone: python scripts/test_cto_mcp_server.py
Or under pytest:  pytest scripts/test_cto_mcp_server.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import telegram_out  # noqa: E402
from runners import cto_mcp_server as srv  # noqa: E402


def test_returns_json_string_of_lib_result(monkeypatch):
    monkeypatch.setattr(
        telegram_out, "send_media_to_ceo",
        lambda path, caption="": {"ok": True, "reason": None},
    )

    raw = srv.send_media_to_ceo("/some/path.jpg", caption="hi")

    assert isinstance(raw, str)
    assert json.loads(raw) == {"ok": True, "reason": None}


def test_passes_path_and_caption_through_to_the_lib(monkeypatch):
    seen = {}

    def fake(path, caption=""):
        seen["path"] = path
        seen["caption"] = caption
        return {"ok": True, "reason": None}

    monkeypatch.setattr(telegram_out, "send_media_to_ceo", fake)

    srv.send_media_to_ceo("/tmp/whatever.mp4", caption="a video")

    assert seen == {"path": "/tmp/whatever.mp4", "caption": "a video"}


def test_failure_result_from_lib_passes_through_unchanged(monkeypatch):
    monkeypatch.setattr(
        telegram_out, "send_media_to_ceo",
        lambda path, caption="": {"ok": False, "reason": "file too large for Telegram: 999 bytes"},
    )

    raw = srv.send_media_to_ceo("/some/big.mp4")

    assert json.loads(raw) == {"ok": False, "reason": "file too large for Telegram: 999 bytes"}


def test_never_raises_on_an_unexpected_lib_exception(monkeypatch):
    def boom(path, caption=""):
        raise RuntimeError("boom")

    monkeypatch.setattr(telegram_out, "send_media_to_ceo", boom)

    raw = srv.send_media_to_ceo("/tmp/whatever.jpg")  # must not raise

    result = json.loads(raw)
    assert result["ok"] is False
    assert "boom" in result["reason"]


def test_rejects_a_nonexistent_path_cleanly(monkeypatch):
    # Real lib call -- but the file-existence check runs before any network
    # touch, so this needs no requests mocking to stay off the network.
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token-not-real")
    monkeypatch.setenv("TELEGRAM_CEO_CHAT_ID", "12345")

    raw = srv.send_media_to_ceo("/no/such/path/ever-9999.jpg")

    result = json.loads(raw)
    assert result["ok"] is False
    assert "not an existing regular file" in result["reason"]


def test_rejects_a_directory_cleanly(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token-not-real")
    monkeypatch.setenv("TELEGRAM_CEO_CHAT_ID", "12345")

    raw = srv.send_media_to_ceo(str(tmp_path))

    result = json.loads(raw)
    assert result["ok"] is False
    assert "not an existing regular file" in result["reason"]


def test_registered_as_an_mcp_tool():
    tools = asyncio.run(srv.mcp.list_tools())
    names = {t.name for t in tools}
    assert "send_media_to_ceo" in names


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
