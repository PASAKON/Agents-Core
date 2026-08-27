"""Tests for lib/telegram_out.py -- send_to_ceo (task-67ba0c4f D1/D5) and
send_media_to_ceo (task-ed9e5b9a D1-D6).

Every test stubs `requests.post`/`requests.get` -- no real network call, no
real Telegram API, no real bot token. `TELEGRAM_BOT_TOKEN`/
`TELEGRAM_CEO_CHAT_ID` are set per-test via monkeypatch.setenv, never read
from the real environment. `CLAUDEFLOW_ENV` is always pointed at a fixture
path (or left unset with the fallback env vars absent), so no test ever
touches the real mooniex-claudeflow/.env on this machine.

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

# Real magic-byte prefixes, used so _probe_media_kind's fallback path (no
# ffprobe) classifies these deterministically regardless of what's actually
# installed on the machine running the tests.
JPEG_HEAD = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 32
MP4_HEAD = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 32
PLAIN_TEXT = b"just a regular text file, not any known media format\n"


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


@pytest.fixture(autouse=True)
def _no_real_claudeflow_env(monkeypatch):
    """Every test gets CLAUDEFLOW_ENV pointed at a path that does not
    exist, so _resolve_env's fallback read never touches the real
    mooniex-claudeflow/.env on this machine unless a test deliberately
    overrides it to a fixture file."""
    monkeypatch.setenv("CLAUDEFLOW_ENV", "/nonexistent/claudeflow-env-fixture")


@pytest.fixture(autouse=True)
def _clear_bot_identity_cache():
    tg._bot_identity_cache.clear()
    yield
    tg._bot_identity_cache.clear()


@pytest.fixture(autouse=True)
def _no_real_ffprobe(monkeypatch):
    """Force every test onto the magic-bytes probe path, deterministically --
    whether ffprobe happens to be installed on the machine running these
    tests (and how lenient its container-probing is on a truncated fixture
    file) must never change what these tests assert. The ffprobe branch
    itself is covered separately below with subprocess.run mocked."""
    monkeypatch.setattr(tg.shutil, "which", lambda *a, **kw: None)


def _valid_getme(monkeypatch, calls=None, username=tg.EXPECTED_BOT_USERNAME):
    def fake_get(url, **kw):
        if calls is not None:
            calls.append(("GET", url, kw))
        return FakeResponse(
            200, {"ok": True, "result": {"id": 1, "is_bot": True, "username": username}}
        )
    monkeypatch.setattr(requests, "get", fake_get)


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


# ---------------------------------------------------------------------------
# send_media_to_ceo -- D2: dual-machine token/chat-id resolution
# ---------------------------------------------------------------------------

def test_media_falls_back_to_claudeflow_env_on_the_mac(monkeypatch, tmp_path):
    """TELEGRAM_BOT_TOKEN/CHAT_ID unset (the real Mac condition) -- resolved
    instead from claudeflow's SECRETARY_* keys via CLAUDEFLOW_ENV, not from
    the real repo on disk (fixture file, never the real .env)."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CEO_CHAT_ID", raising=False)
    fixture_env = tmp_path / "claudeflow.env"
    fixture_env.write_text(f"SECRETARY_BOT_TOKEN={TOKEN}\nSECRETARY_ADMIN_CHAT_ID={CHAT_ID}\n")
    monkeypatch.setenv("CLAUDEFLOW_ENV", str(fixture_env))

    _valid_getme(monkeypatch)
    monkeypatch.setattr(requests, "post", lambda *a, **kw: FakeResponse(200, {"ok": True}))

    f = tmp_path / "pic.jpg"
    f.write_bytes(JPEG_HEAD)
    result = tg.send_media_to_ceo(str(f))

    assert result == {"ok": True, "reason": None}


def test_media_process_env_wins_over_claudeflow_env(monkeypatch, tmp_path):
    fixture_env = tmp_path / "claudeflow.env"
    fixture_env.write_text("SECRETARY_BOT_TOKEN=wrong-token\nSECRETARY_ADMIN_CHAT_ID=wrong-chat\n")
    monkeypatch.setenv("CLAUDEFLOW_ENV", str(fixture_env))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN)
    monkeypatch.setenv("TELEGRAM_CEO_CHAT_ID", CHAT_ID)

    seen_chat_ids = []

    def fake_get(url, **kw):
        assert TOKEN in url and "wrong-token" not in url
        return FakeResponse(200, {"ok": True, "result": {"username": tg.EXPECTED_BOT_USERNAME}})

    def fake_post(url, data=None, **kw):
        seen_chat_ids.append(data["chat_id"])
        return FakeResponse(200, {"ok": True})

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(requests, "post", fake_post)

    f = tmp_path / "pic.jpg"
    f.write_bytes(JPEG_HEAD)
    result = tg.send_media_to_ceo(str(f))

    assert result["ok"] is True
    assert seen_chat_ids == [CHAT_ID]


def test_media_missing_token_and_fallback_is_explicit_failure(env, monkeypatch, tmp_path):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(requests, "get", lambda *a, **kw: calls.append(("GET",)))
    monkeypatch.setattr(requests, "post", lambda *a, **kw: calls.append(("POST",)))

    f = tmp_path / "pic.jpg"
    f.write_bytes(JPEG_HEAD)
    result = tg.send_media_to_ceo(str(f))

    assert result["ok"] is False
    assert "TELEGRAM_BOT_TOKEN" in result["reason"] or "bot token" in result["reason"]
    assert calls == []


# ---------------------------------------------------------------------------
# send_media_to_ceo -- D3: bot identity must be @SSomPongBot before sending
# ---------------------------------------------------------------------------

def test_media_wrong_bot_refuses_without_sending(env, monkeypatch, tmp_path):
    post_calls = []
    _valid_getme(monkeypatch, username="SomeOtherBot")
    monkeypatch.setattr(requests, "post", lambda *a, **kw: post_calls.append(1))

    f = tmp_path / "pic.jpg"
    f.write_bytes(JPEG_HEAD)
    result = tg.send_media_to_ceo(str(f))

    assert result["ok"] is False
    assert "SomeOtherBot" in result["reason"] or "wrong bot" in result["reason"]
    assert post_calls == [], "must never attempt the send with the wrong bot"


def test_media_identity_check_is_cached_per_process(env, monkeypatch, tmp_path):
    get_calls = []
    _valid_getme(monkeypatch, calls=get_calls)
    monkeypatch.setattr(requests, "post", lambda *a, **kw: FakeResponse(200, {"ok": True}))

    f = tmp_path / "pic.jpg"
    f.write_bytes(JPEG_HEAD)
    tg.send_media_to_ceo(str(f))
    tg.send_media_to_ceo(str(f))

    assert len(get_calls) == 1, "getMe must cost one call per process, not one per send"


# ---------------------------------------------------------------------------
# send_media_to_ceo -- D4: hard 50MB refusal, no link fallback
# ---------------------------------------------------------------------------

def test_media_over_50mb_is_refused_with_size_named_no_fallback(env, monkeypatch, tmp_path):
    get_calls, post_calls = [], []
    monkeypatch.setattr(requests, "get", lambda *a, **kw: get_calls.append(1))
    monkeypatch.setattr(requests, "post", lambda *a, **kw: post_calls.append(1))

    big = tmp_path / "huge.mp4"
    oversized = tg.MAX_MEDIA_BYTES + 1
    with open(big, "wb") as fh:
        fh.seek(oversized - 1)
        fh.write(b"\0")

    result = tg.send_media_to_ceo(str(big))

    assert result["ok"] is False
    assert str(oversized) in result["reason"]
    assert "50 MB" in result["reason"] or "50MB" in result["reason"]
    assert "http" not in result["reason"].lower(), "must never fall back to a link"
    assert get_calls == [] and post_calls == [], "must refuse before any network call"


# ---------------------------------------------------------------------------
# send_media_to_ceo -- D1/D6: real multipart upload, never a URL
# ---------------------------------------------------------------------------

def test_media_upload_carries_real_file_bytes_not_a_url(env, monkeypatch, tmp_path):
    _valid_getme(monkeypatch)
    captured = {}

    def fake_post(url, data=None, files=None, **kw):
        captured["url"] = url
        captured["data"] = data
        captured["files"] = files
        return FakeResponse(200, {"ok": True})

    monkeypatch.setattr(requests, "post", fake_post)

    f = tmp_path / "pic.jpg"
    f.write_bytes(JPEG_HEAD)
    result = tg.send_media_to_ceo(str(f), caption="a caption")

    assert result == {"ok": True, "reason": None}
    assert captured["url"].endswith("/sendPhoto")
    assert "photo" in captured["files"], "must carry the file as multipart bytes"
    filename, fileobj = captured["files"]["photo"]
    assert filename == "pic.jpg"
    assert hasattr(fileobj, "read"), "must upload a file handle, not a string/url"
    assert "photo" not in captured["data"], "the photo field belongs in files=, not data="
    for value in captured["data"].values():
        assert not str(value).startswith("http"), "no URL was ever sent as the media field"
    assert captured["data"]["caption"] == "a caption"


# ---------------------------------------------------------------------------
# send_media_to_ceo -- D6: endpoint follows probed content, not extension
# ---------------------------------------------------------------------------

def test_media_endpoint_follows_probed_type_not_extension(env, monkeypatch, tmp_path):
    """A JPEG saved with a .mp4 name must still go out as a photo."""
    _valid_getme(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        requests, "post",
        lambda url, **kw: (captured.__setitem__("url", url), FakeResponse(200, {"ok": True}))[1],
    )

    mislabeled = tmp_path / "totally_a_video.mp4"
    mislabeled.write_bytes(JPEG_HEAD)
    result = tg.send_media_to_ceo(str(mislabeled))

    assert result["ok"] is True
    assert captured["url"].endswith("/sendPhoto"), "extension said video, content said photo"


def test_media_real_video_bytes_use_sendvideo_despite_jpg_name(env, monkeypatch, tmp_path):
    _valid_getme(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        requests, "post",
        lambda url, **kw: (captured.__setitem__("url", url), FakeResponse(200, {"ok": True}))[1],
    )

    mislabeled = tmp_path / "totally_a_photo.jpg"
    mislabeled.write_bytes(MP4_HEAD)
    result = tg.send_media_to_ceo(str(mislabeled))

    assert result["ok"] is True
    assert captured["url"].endswith("/sendVideo")


def test_media_unrecognized_content_falls_back_to_senddocument(env, monkeypatch, tmp_path):
    _valid_getme(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        requests, "post",
        lambda url, **kw: (captured.__setitem__("url", url), FakeResponse(200, {"ok": True}))[1],
    )

    f = tmp_path / "notes.txt"
    f.write_bytes(PLAIN_TEXT)
    result = tg.send_media_to_ceo(str(f))

    assert result["ok"] is True
    assert captured["url"].endswith("/sendDocument")


# ---------------------------------------------------------------------------
# send_media_to_ceo -- D6: bad paths refused cleanly
# ---------------------------------------------------------------------------

def test_media_nonexistent_path_is_refused_cleanly(env, monkeypatch):
    calls = []
    monkeypatch.setattr(requests, "get", lambda *a, **kw: calls.append(1))
    monkeypatch.setattr(requests, "post", lambda *a, **kw: calls.append(1))

    result = tg.send_media_to_ceo("/no/such/path/ever-1234.jpg")

    assert result["ok"] is False
    assert "not an existing regular file" in result["reason"]
    assert calls == []


def test_media_directory_path_is_refused_cleanly(env, monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(requests, "get", lambda *a, **kw: calls.append(1))
    monkeypatch.setattr(requests, "post", lambda *a, **kw: calls.append(1))

    result = tg.send_media_to_ceo(str(tmp_path))

    assert result["ok"] is False
    assert "not an existing regular file" in result["reason"]
    assert calls == []


# ---------------------------------------------------------------------------
# send_media_to_ceo -- token never leaks, including new error paths
# ---------------------------------------------------------------------------

def test_media_token_never_leaks_through_getme_network_error(env, monkeypatch, tmp_path):
    def boom(*a, **kw):
        raise requests.ConnectionError(
            f"HTTPSConnectionPool(host='api.telegram.org', port=443): "
            f"Max retries exceeded with url: /bot{TOKEN}/getMe"
        )
    monkeypatch.setattr(requests, "get", boom)

    f = tmp_path / "pic.jpg"
    f.write_bytes(JPEG_HEAD)
    result = tg.send_media_to_ceo(str(f))

    assert result["ok"] is False
    assert TOKEN not in result["reason"]
    assert TOKEN not in str(result)


def test_media_token_never_leaks_through_upload_network_error(env, monkeypatch, tmp_path):
    _valid_getme(monkeypatch)

    def boom(*a, **kw):
        raise requests.ConnectionError(
            f"HTTPSConnectionPool(host='api.telegram.org', port=443): "
            f"Max retries exceeded with url: /bot{TOKEN}/sendPhoto"
        )
    monkeypatch.setattr(requests, "post", boom)

    f = tmp_path / "pic.jpg"
    f.write_bytes(JPEG_HEAD)
    result = tg.send_media_to_ceo(str(f))

    assert result["ok"] is False
    assert TOKEN not in result["reason"]
    assert TOKEN not in str(result)


def test_media_token_never_appears_in_a_success_result(env, monkeypatch, tmp_path):
    _valid_getme(monkeypatch)
    monkeypatch.setattr(requests, "post", lambda *a, **kw: FakeResponse(200, {"ok": True}))

    f = tmp_path / "pic.jpg"
    f.write_bytes(JPEG_HEAD)
    result = tg.send_media_to_ceo(str(f))

    assert TOKEN not in str(result)


# ---------------------------------------------------------------------------
# _probe_via_ffprobe -- the ffprobe branch itself, isolated from whatever
# ffprobe binary (if any) is actually installed on the test machine.
# ---------------------------------------------------------------------------

def test_probe_via_ffprobe_identifies_real_video_stream(monkeypatch, tmp_path):
    monkeypatch.setattr(tg.shutil, "which", lambda *a, **kw: "/usr/bin/ffprobe")

    class FakeProc:
        returncode = 0
        stdout = "format_name=mov,mp4,m4a,3gp,3g2,mj2\ncodec_type=video\ncodec_type=audio\n"

    monkeypatch.setattr(tg.subprocess, "run", lambda *a, **kw: FakeProc())

    assert tg._probe_via_ffprobe(tmp_path / "whatever.bin") == "video"


def test_probe_via_ffprobe_identifies_image_format(monkeypatch, tmp_path):
    monkeypatch.setattr(tg.shutil, "which", lambda *a, **kw: "/usr/bin/ffprobe")

    class FakeProc:
        returncode = 0
        stdout = "format_name=jpeg_pipe\ncodec_type=video\n"

    monkeypatch.setattr(tg.subprocess, "run", lambda *a, **kw: FakeProc())

    assert tg._probe_via_ffprobe(tmp_path / "whatever.bin") == "photo"


def test_probe_via_ffprobe_decode_failure_returns_none(monkeypatch, tmp_path):
    """A .mp4 that will not decode is not a video -- ffprobe exiting
    non-zero must be treated as "could not tell", not as "video"."""
    monkeypatch.setattr(tg.shutil, "which", lambda *a, **kw: "/usr/bin/ffprobe")

    class FakeProc:
        returncode = 1
        stdout = ""

    monkeypatch.setattr(tg.subprocess, "run", lambda *a, **kw: FakeProc())

    assert tg._probe_via_ffprobe(tmp_path / "whatever.bin") is None


def test_probe_via_ffprobe_missing_binary_returns_none(monkeypatch, tmp_path):
    monkeypatch.setattr(tg.shutil, "which", lambda *a, **kw: None)
    assert tg._probe_via_ffprobe(tmp_path / "whatever.bin") is None


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
