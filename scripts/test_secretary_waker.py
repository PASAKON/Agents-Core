"""Tests for runners/secretary_waker.py (task-67ba0c4f D2/D5).

Every test isolates lib.mailbox's INBOX_ROOT and the waker's own
LOCK_PATH/FAILCOUNT_PATH to tmp_path (same pattern scripts/test_mac_agent.py
and scripts/test_ceo_report.py use), and an autouse fixture makes any
un-stubbed `requests.post` raise -- no test may touch a real inbox, a real
Telegram API, or a real secretary HTTP server.

Run standalone: python scripts/test_secretary_waker.py
Or under pytest:  pytest scripts/test_secretary_waker.py
"""
from __future__ import annotations

import fcntl
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import runners.secretary_waker as w  # noqa: E402
from lib import mailbox  # noqa: E402
from runners import secretary_server  # noqa: E402


class FakeHttpResponse:
    def __init__(self, status_code=200, json_body=None):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._json_body = json_body
        self.text = "" if json_body is None else str(json_body)

    def json(self):
        return self._json_body


@pytest.fixture(autouse=True)
def _block_real_network(monkeypatch):
    def boom(*a, **kw):
        raise AssertionError("test attempted a real HTTP request")
    monkeypatch.setattr(w.requests, "post", boom)


@pytest.fixture
def waker_env(tmp_path, monkeypatch):
    monkeypatch.setattr(mailbox, "INBOX_ROOT", tmp_path / "inbox")
    monkeypatch.setattr(w, "LOCK_PATH", tmp_path / "wstate" / "waker.lock")
    monkeypatch.setattr(w, "FAILCOUNT_PATH", tmp_path / "wstate" / "failcounts.json")
    monkeypatch.setattr(w, "MAX_BATCH", 5)
    monkeypatch.setattr(w, "MAX_RETRIES", 5)
    monkeypatch.setenv("TELEGRAM_CEO_CHAT_ID", "999999")
    monkeypatch.setattr(secretary_server, "SECRETARY_API_KEY", "test-key")
    monkeypatch.setattr(secretary_server, "SECRETARY_HOST", "127.0.0.1")
    monkeypatch.setattr(secretary_server, "SECRETARY_PORT", 8643)
    return tmp_path


def _send_letter(tmp_path, body, from_role="cto", from_sid="abc123") -> Path:
    return mailbox.send("secretary", "sompong", body, from_role, from_sid)


def _letters(tmp_path) -> list[Path]:
    box = tmp_path / "inbox" / "secretary-sompong"
    if not box.is_dir():
        return []
    return sorted(box.glob("*.json"))


# ---------------------------------------------------------------------------
# Empty box
# ---------------------------------------------------------------------------

def test_empty_box_is_noop(waker_env, monkeypatch):
    called = []
    monkeypatch.setattr(w, "_invoke_secretary", lambda prompt: called.append(1) or (True, "x"))

    assert w.tick() == 0
    assert called == []


# ---------------------------------------------------------------------------
# The single most important test: a failed Telegram send keeps the letters.
# ---------------------------------------------------------------------------

def test_failed_telegram_send_keeps_the_letters(waker_env, monkeypatch):
    p = _send_letter(waker_env, "[report_to_ceo] order #1 -- done\nshipped it")
    monkeypatch.setattr(w, "_invoke_secretary", lambda prompt: (True, "สรุปให้ CEO"))
    monkeypatch.setattr(w.telegram_out, "send_to_ceo",
                         lambda text: {"ok": False, "reason": "telegram down"})

    result = w.tick()

    assert result == 0
    assert p.exists(), "a failed Telegram send must never lose the letter"


def test_failed_secretary_invocation_keeps_the_letters(waker_env, monkeypatch):
    p = _send_letter(waker_env, "[report_to_ceo] order #1 -- done\nshipped it")
    monkeypatch.setattr(w, "_invoke_secretary", lambda prompt: (False, "secretary boom"))
    called = []
    monkeypatch.setattr(w.telegram_out, "send_to_ceo", lambda text: called.append(1))

    result = w.tick()

    assert result == 0
    assert p.exists()
    assert called == [], "telegram must never be reached if the secretary invocation failed"


# ---------------------------------------------------------------------------
# Success deletes exactly the consumed letters; a letter that arrives mid-
# cycle (during the send) survives untouched.
# ---------------------------------------------------------------------------

def test_success_deletes_only_consumed_letters_and_keeps_late_arrival(waker_env, monkeypatch):
    p1 = _send_letter(waker_env, "[report_to_ceo] order #1 -- done\nshipped it")
    monkeypatch.setattr(w, "_invoke_secretary", lambda prompt: (True, "สรุปให้ CEO"))

    def fake_send(text):
        # a second C-level reports in, mid-cycle, after this tick's peek
        _send_letter(waker_env, "[report_to_ceo] order #2 -- blocked\nwaiting on DNS")
        return {"ok": True, "reason": None}

    monkeypatch.setattr(w.telegram_out, "send_to_ceo", fake_send)

    sent = w.tick()

    assert sent == 1
    remaining = _letters(waker_env)
    assert len(remaining) == 1
    assert remaining[0] != p1
    assert not p1.exists()


# ---------------------------------------------------------------------------
# Missing config -- explicit failure, and the loop deletes nothing.
# ---------------------------------------------------------------------------

def test_missing_secretary_api_key_keeps_letters_and_makes_no_request(waker_env, monkeypatch):
    monkeypatch.setattr(secretary_server, "SECRETARY_API_KEY", "")
    p = _send_letter(waker_env, "[report_to_ceo] order #1 -- done\nx")

    assert w.tick() == 0
    assert p.exists()


def test_missing_ceo_conversation_id_keeps_letters_and_makes_no_request(waker_env, monkeypatch):
    monkeypatch.delenv("TELEGRAM_CEO_CHAT_ID", raising=False)
    p = _send_letter(waker_env, "[report_to_ceo] order #1 -- done\nx")

    assert w.tick() == 0
    assert p.exists()


# ---------------------------------------------------------------------------
# Poison-letter cap
# ---------------------------------------------------------------------------

def test_poison_letter_quarantined_after_cap_then_loop_continues(waker_env, monkeypatch):
    monkeypatch.setattr(w, "MAX_RETRIES", 2)
    p = _send_letter(waker_env, "[report_to_ceo] order #9 -- done\nx")
    monkeypatch.setattr(w, "_invoke_secretary", lambda prompt: (False, "boom"))

    assert w.tick() == 0
    assert p.exists(), "first failure must not quarantine yet"

    assert w.tick() == 0
    assert not p.exists(), "second consecutive failure hits the cap"
    failed = p.parent / "failed" / p.name
    assert failed.exists()

    # box is now empty -- the loop keeps running cleanly, not stuck retrying
    assert w.tick() == 0


# ---------------------------------------------------------------------------
# Single-flight
# ---------------------------------------------------------------------------

def test_single_flight_second_tick_is_noop(waker_env, monkeypatch):
    p = _send_letter(waker_env, "[report_to_ceo] order #1 -- done\nx")
    called = []
    monkeypatch.setattr(w, "_invoke_secretary", lambda prompt: called.append(1) or (True, "x"))
    monkeypatch.setattr(w.telegram_out, "send_to_ceo",
                         lambda text: {"ok": True, "reason": None})

    w.LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(w.LOCK_PATH), os.O_CREAT | os.O_RDWR, 0o644)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        result = w.tick()
    finally:
        os.close(fd)

    assert result == 0
    assert called == [], "a tick that lost the lock race must not touch anything"
    assert p.exists()


# ---------------------------------------------------------------------------
# Batch cap
# ---------------------------------------------------------------------------

def test_batch_cap_is_one_invocation_and_notes_held_over(waker_env, monkeypatch):
    monkeypatch.setattr(w, "MAX_BATCH", 2)
    for i in range(5):
        _send_letter(waker_env, f"[report_to_ceo] order #{i} -- done\nletter {i}")

    captured = {"calls": 0}

    def fake_invoke(prompt):
        captured["prompt"] = prompt
        captured["calls"] += 1
        return True, "digest"

    monkeypatch.setattr(w, "_invoke_secretary", fake_invoke)
    monkeypatch.setattr(w.telegram_out, "send_to_ceo",
                         lambda text: {"ok": True, "reason": None})

    sent = w.tick()

    assert sent == 2
    assert captured["calls"] == 1, "5 letters in must be ONE secretary invocation"
    assert "เก็บไว้อีก 3" in captured["prompt"], "digest must say some were held over"
    assert len(_letters(waker_env)) == 3


# ---------------------------------------------------------------------------
# Digest prompt shape
# ---------------------------------------------------------------------------

def test_digest_prompt_starts_with_marker_and_preserves_status_verbatim():
    letters = [{
        "from": {"role": "cto", "session_id": "abc123"},
        "sent_at": "2026-08-15T09:00:00Z",
        "body": "[report_to_ceo] order #1 -- blocked\nwaiting on DNS",
    }]

    prompt = w._build_digest_prompt(letters, held=0)

    assert prompt.startswith(secretary_server.DIGEST_TURN_MARKER)
    assert "blocked" in prompt
    assert "waiting on DNS" in prompt
    assert "เก็บไว้อีก" not in prompt, "no held-over note when nothing was held"


# ---------------------------------------------------------------------------
# _invoke_secretary -- HTTP shape (host/port/key from secretary_server,
# CEO's own conversation_id, same /v1/chat/completions endpoint)
# ---------------------------------------------------------------------------

def test_invoke_secretary_posts_to_configured_endpoint_with_ceo_conversation_id(
    waker_env, monkeypatch,
):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return FakeHttpResponse(200, {"choices": [{"message": {"content": "หวัดดีครับ"}}]})

    monkeypatch.setattr(w.requests, "post", fake_post)

    ok, content = w._invoke_secretary("test prompt")

    assert ok is True
    assert content == "หวัดดีครับ"
    assert captured["url"] == "http://127.0.0.1:8643/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["user"] == "999999"
    assert captured["json"]["messages"] == [{"role": "user", "content": "test prompt"}]


def test_invoke_secretary_empty_content_is_failure(waker_env, monkeypatch):
    monkeypatch.setattr(
        w.requests, "post",
        lambda *a, **kw: FakeHttpResponse(200, {"choices": [{"message": {"content": "   "}}]}),
    )

    ok, reason = w._invoke_secretary("x")

    assert ok is False


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
