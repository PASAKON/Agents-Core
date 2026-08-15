"""Tests for lib/telegram_out.py::send_to_ceo (task-67ba0c4f D1/D5).

Every test stubs `requests.post` -- no real network call, no real Telegram
API, no real bot token. `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CEO_CHAT_ID` are set
per-test via monkeypatch.setenv, never read from the real environment.

Run standalone: python scripts/test_telegram_out.py
Or under pytest:  pytest scripts/test_telegram_out.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import telegram_out as tg  # noqa: E402

TOKEN = "123456:AAFakeTokenValueForTestsOnly"
CHAT_ID = "999999"


class FakeResponse:
    def __init__(self, status_code=200, json_body=None, raise_json=False):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._json_body = json_body
        self._raise_json = raise_json
        self.text = "" if json_body is None else str(json_body)

    def json(self):
        if self._raise_json:
            raise ValueError("not json")
        return self._json_body


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN)
    monkeypatch.setenv("TELEGRAM_CEO_CHAT_ID", CHAT_ID)


# ---------------------------------------------------------------------------
# Missing config -- explicit failure, never a silent no-op
# ---------------------------------------------------------------------------

def test_missing_token_is_explicit_failure(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("TELEGRAM_CEO_CHAT_ID", CHAT_ID)
    calls = []
    monkeypatch.setattr(requests, "post", lambda *a, **kw: calls.append(1))

    result = tg.send_to_ceo("hi")

    assert result["ok"] is False
    assert "TELEGRAM_BOT_TOKEN" in result["reason"]
    assert calls == [], "must not even attempt the request without a token"


def test_missing_chat_id_is_explicit_failure(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN)
    monkeypatch.delenv("TELEGRAM_CEO_CHAT_ID", raising=False)
    calls = []
    monkeypatch.setattr(requests, "post", lambda *a, **kw: calls.append(1))

    result = tg.send_to_ceo("hi")

    assert result["ok"] is False
    assert "TELEGRAM_CEO_CHAT_ID" in result["reason"]
    assert calls == []


# ---------------------------------------------------------------------------
# Success means Telegram's own body said ok -- not "the request was sent"
# ---------------------------------------------------------------------------

def test_success_is_telegram_ok_true(env, monkeypatch):
    monkeypatch.setattr(requests, "post",
                         lambda *a, **kw: FakeResponse(200, {"ok": True, "result": {}}))

    result = tg.send_to_ceo("สวัสดีครับ")

    assert result == {"ok": True, "reason": None}


def test_2xx_with_ok_false_is_still_a_failure(env, monkeypatch):
    """Telegram can answer 200 with ok:false (documented behaviour for some
    error classes) -- HTTP status alone must never be read as success."""
    monkeypatch.setattr(
        requests, "post",
        lambda *a, **kw: FakeResponse(200, {"ok": False, "description": "chat not found"}),
    )

    result = tg.send_to_ceo("hi")

    assert result["ok"] is False
    assert "chat not found" in result["reason"]


def test_non_2xx_is_failure_with_reason_preserved(env, monkeypatch):
    monkeypatch.setattr(
        requests, "post",
        lambda *a, **kw: FakeResponse(401, {"ok": False, "description": "Unauthorized"}),
    )

    result = tg.send_to_ceo("hi")

    assert result["ok"] is False
    assert "Unauthorized" in result["reason"]


def test_network_error_is_failure(env, monkeypatch):
    def boom(*a, **kw):
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr(requests, "post", boom)

    result = tg.send_to_ceo("hi")

    assert result["ok"] is False
    assert "connection refused" in result["reason"]


def test_non_json_response_is_failure(env, monkeypatch):
    monkeypatch.setattr(requests, "post", lambda *a, **kw: FakeResponse(200, raise_json=True))

    result = tg.send_to_ceo("hi")

    assert result["ok"] is False


# ---------------------------------------------------------------------------
# The token never appears in a returned string or exception -- even when the
# underlying error text embeds the request URL (which contains the token).
# ---------------------------------------------------------------------------

def test_token_never_leaks_through_a_network_error(env, monkeypatch):
    def boom(*a, **kw):
        raise requests.ConnectionError(
            f"HTTPSConnectionPool(host='api.telegram.org', port=443): "
            f"Max retries exceeded with url: /bot{TOKEN}/sendMessage"
        )

    monkeypatch.setattr(requests, "post", boom)

    result = tg.send_to_ceo("hi")

    assert result["ok"] is False
    assert TOKEN not in result["reason"]
    assert TOKEN not in str(result)


def test_token_never_appears_in_a_success_result(env, monkeypatch):
    monkeypatch.setattr(requests, "post", lambda *a, **kw: FakeResponse(200, {"ok": True}))

    result = tg.send_to_ceo("hi")

    assert TOKEN not in str(result)


# ---------------------------------------------------------------------------
# 4096-char cap -- truncate with a visible marker rather than reject
# ---------------------------------------------------------------------------

def test_long_message_is_truncated_with_a_marker(env, monkeypatch):
    sent = {}

    def fake_post(url, json=None, **kw):
        sent["text"] = json["text"]
        return FakeResponse(200, {"ok": True})

    monkeypatch.setattr(requests, "post", fake_post)

    result = tg.send_to_ceo("x" * 5000)

    assert result["ok"] is True
    assert len(sent["text"]) <= tg.MAX_MESSAGE_CHARS
    assert tg.TRUNCATION_MARKER.strip() in sent["text"]


def test_short_message_is_sent_unmodified(env, monkeypatch):
    sent = {}

    def fake_post(url, json=None, **kw):
        sent["text"] = json["text"]
        return FakeResponse(200, {"ok": True})

    monkeypatch.setattr(requests, "post", fake_post)

    tg.send_to_ceo("short message")

    assert sent["text"] == "short message"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
