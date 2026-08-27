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

import json
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
# send_to_ceo -- task-80f1405e D1/D3: must resolve the same claudeflow-.env
# fallback the media paths already use, not read os.environ.get directly
# with no fallback (the actual root cause of the live bug: the Drive-notify
# text upload used the fallback and succeeded, the notify send did not and
# failed, in the same call).
# ---------------------------------------------------------------------------

def test_send_to_ceo_resolves_fallback_token_without_env_var(monkeypatch, tmp_path):
    """D3 bullet 3: send_to_ceo itself resolves the fallback token/chat id,
    exercised without TELEGRAM_BOT_TOKEN/TELEGRAM_CEO_CHAT_ID in the env --
    the real Mac shape."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CEO_CHAT_ID", raising=False)
    fixture_env = tmp_path / "claudeflow.env"
    fixture_env.write_text(f"SECRETARY_BOT_TOKEN={TOKEN}\nSECRETARY_ADMIN_CHAT_ID={CHAT_ID}\n")
    monkeypatch.setenv("CLAUDEFLOW_ENV", str(fixture_env))

    captured = {}

    def fake_post(url, json=None, **kw):
        captured["url"] = url
        captured["chat_id"] = json["chat_id"]
        return FakeResponse(200, {"ok": True})

    monkeypatch.setattr(requests, "post", fake_post)

    result = tg.send_to_ceo("hello")

    assert result == {"ok": True, "reason": None}
    assert captured["url"] == f"{tg.TELEGRAM_API_BASE}/bot{TOKEN}/sendMessage", (
        "must use the resolved fallback token, not fail for lack of "
        "TELEGRAM_BOT_TOKEN"
    )
    assert captured["chat_id"] == CHAT_ID


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


# ---------------------------------------------------------------------------
# send_media_batch_to_ceo -- task-68be2c26 D1/D2/D3/D4 (CEO orders #42/#43)
#
# A fake stand-in for scripts/video_to_drive.py's public surface is
# monkeypatched onto tg._video_to_drive for every Drive-routing test below --
# no test here ever imports the real gdrive-bridge chain, touches a real
# OAuth credential, or calls a real Drive API.
# ---------------------------------------------------------------------------

from types import SimpleNamespace  # noqa: E402


def _fake_drive_module(*, listing=None, upload_error=None):
    uploads = []

    def fake_upload(local_path, name, folder_id):
        if upload_error:
            raise upload_error
        uploads.append((str(local_path), name, folder_id))
        return {"id": "fake-drive-file-id"}

    def fake_list_folder(folder_id):
        return dict(listing) if listing is not None else {}

    ns = SimpleNamespace(
        DRIVE_SOMPONG_GRAB_FOLDER_ID="fake-folder-id",
        apply_oauth_env_override=lambda: None,
        upload=fake_upload,
        list_folder=fake_list_folder,
        mb=lambda n: f"{n / 1048576:.1f} MB",
    )
    ns._uploads = uploads
    return ns


def _make_sized_file(path: Path, size: int, head: bytes = b"") -> Path:
    """A file of exactly `size` bytes, starting with `head` -- sparse (via
    seek+write) so a 50MB+ fixture costs no real IO time or disk."""
    with open(path, "wb") as fh:
        fh.write(head)
        if size > len(head):
            fh.seek(size - 1)
            fh.write(b"\0")
    return path


def test_batch_two_small_files_go_out_as_one_album(env, monkeypatch, tmp_path):
    """D1: a 2-file batch of small photos must be ONE sendMediaGroup call,
    never two separate sendPhoto sends."""
    _valid_getme(monkeypatch)
    posts = []

    def fake_post(url, data=None, files=None, **kw):
        posts.append({"url": url, "data": data, "files": files})
        return FakeResponse(200, {"ok": True, "result": [{}, {}]})

    monkeypatch.setattr(requests, "post", fake_post)

    f1 = tmp_path / "a.jpg"
    f1.write_bytes(JPEG_HEAD)
    f2 = tmp_path / "b.jpg"
    f2.write_bytes(JPEG_HEAD)

    result = tg.send_media_batch_to_ceo([str(f1), str(f2)])

    assert result["ok"] is True
    assert [r["status"] for r in result["results"]] == ["uploaded", "uploaded"]
    assert [r["path"] for r in result["results"]] == [str(f1), str(f2)]
    assert len(posts) == 1, "two photos must go out as ONE sendMediaGroup call, not two sends"
    assert posts[0]["url"].endswith("/sendMediaGroup")
    media = json.loads(posts[0]["data"]["media"])
    assert len(media) == 2
    assert set(posts[0]["files"]) == {"file0", "file1"}


def test_batch_eleven_files_split_into_ten_plus_one(env, monkeypatch, tmp_path):
    """D1: Telegram caps a media group at 10 -- an 11-file batch must go out
    as one 10-item album plus one lone sendPhoto (Telegram rejects a group
    of size 1)."""
    _valid_getme(monkeypatch)
    posts = []

    def fake_post(url, data=None, files=None, **kw):
        posts.append({"url": url, "files": files})
        if url.endswith("/sendMediaGroup"):
            n = len(json.loads(data["media"]))
            return FakeResponse(200, {"ok": True, "result": [{}] * n})
        return FakeResponse(200, {"ok": True, "result": {}})

    monkeypatch.setattr(requests, "post", fake_post)

    paths = []
    for i in range(11):
        p = tmp_path / f"pic{i}.jpg"
        p.write_bytes(JPEG_HEAD)
        paths.append(str(p))

    result = tg.send_media_batch_to_ceo(paths)

    assert result["ok"] is True
    assert all(r["status"] == "uploaded" for r in result["results"])
    group_calls = [p for p in posts if p["url"].endswith("/sendMediaGroup")]
    single_calls = [p for p in posts if p["url"].endswith("/sendPhoto")]
    assert len(group_calls) == 1, "the first 10 must go out as one album"
    assert len(group_calls[0]["files"]) == 10
    assert len(single_calls) == 1, "the 11th, alone, must fall back to a single sendPhoto"


def test_batch_documents_sent_individually_not_grouped(env, monkeypatch, tmp_path):
    """Documents can't share an album with photos/videos on Telegram, so
    each document goes out on its own -- and a lone photo among them still
    falls back to a single sendPhoto, not a group of one."""
    _valid_getme(monkeypatch)
    posts = []
    monkeypatch.setattr(
        requests, "post",
        lambda url, **kw: (posts.append(url), FakeResponse(200, {"ok": True}))[1],
    )

    doc1 = tmp_path / "notes1.txt"
    doc1.write_bytes(PLAIN_TEXT)
    doc2 = tmp_path / "notes2.txt"
    doc2.write_bytes(PLAIN_TEXT)
    photo = tmp_path / "pic.jpg"
    photo.write_bytes(JPEG_HEAD)

    result = tg.send_media_batch_to_ceo([str(doc1), str(photo), str(doc2)])

    assert all(r["status"] == "uploaded" for r in result["results"])
    assert len([u for u in posts if u.endswith("/sendDocument")]) == 2
    assert any(u.endswith("/sendPhoto") for u in posts)
    assert not any(u.endswith("/sendMediaGroup") for u in posts)


def test_batch_exactly_50mb_uploads_one_over_goes_to_drive(env, monkeypatch, tmp_path):
    """D2: size routing is decided PER FILE -- exactly 50MB still fits and
    must upload as a real file; one byte over routes to Drive instead."""
    _valid_getme(monkeypatch)
    monkeypatch.setattr(requests, "post", lambda *a, **kw: FakeResponse(200, {"ok": True}))

    exact = _make_sized_file(tmp_path / "exact.mp4", tg.MAX_MEDIA_BYTES, head=MP4_HEAD)
    over = _make_sized_file(tmp_path / "huge.mp4", tg.MAX_MEDIA_BYTES + 1, head=MP4_HEAD)

    drive_ns = _fake_drive_module(listing={"huge.mp4": tg.MAX_MEDIA_BYTES + 1})
    monkeypatch.setattr(tg, "_video_to_drive", lambda: drive_ns)
    notices = []
    monkeypatch.setattr(
        tg, "send_to_ceo",
        lambda text: (notices.append(text), {"ok": True, "reason": None})[1],
    )

    result = tg.send_media_batch_to_ceo([str(exact), str(over)])

    by_path = {r["path"]: r for r in result["results"]}
    assert by_path[str(exact)]["status"] == "uploaded"
    assert by_path[str(over)]["status"] == "linked"
    assert by_path[str(over)]["link"] is not None
    assert drive_ns._uploads and drive_ns._uploads[0][1] == "huge.mp4"
    assert notices and "huge.mp4" in notices[0] and "50 MB" in notices[0]


def test_batch_mixed_small_and_oversized_reports_distinct_outcomes(env, monkeypatch, tmp_path):
    """D4: a mixed batch reports each file's real outcome -- never a flat
    success/failure for the whole call."""
    _valid_getme(monkeypatch)
    monkeypatch.setattr(requests, "post", lambda *a, **kw: FakeResponse(200, {"ok": True}))

    small = tmp_path / "small.jpg"
    small.write_bytes(JPEG_HEAD)
    over = _make_sized_file(tmp_path / "huge.mp4", tg.MAX_MEDIA_BYTES + 1, head=MP4_HEAD)

    drive_ns = _fake_drive_module(listing={"huge.mp4": tg.MAX_MEDIA_BYTES + 1})
    monkeypatch.setattr(tg, "_video_to_drive", lambda: drive_ns)
    monkeypatch.setattr(tg, "send_to_ceo", lambda text: {"ok": True, "reason": None})

    result = tg.send_media_batch_to_ceo([str(small), str(over)])

    assert result["ok"] is True, "every file succeeded (one uploaded, one linked)"
    statuses = {r["path"]: r["status"] for r in result["results"]}
    assert statuses[str(small)] == "uploaded"
    assert statuses[str(over)] == "linked"


def test_batch_drive_verify_miss_is_a_failure(env, monkeypatch, tmp_path):
    """D3: a fresh folder listing that does not show the file is a FAILURE,
    never a silently-assumed success -- and the CEO is never told about a
    link that doesn't actually exist on Drive."""
    _valid_getme(monkeypatch)
    over = _make_sized_file(tmp_path / "huge.mp4", tg.MAX_MEDIA_BYTES + 1, head=MP4_HEAD)

    drive_ns = _fake_drive_module(listing={})  # fresh listing does not show it
    monkeypatch.setattr(tg, "_video_to_drive", lambda: drive_ns)
    notices = []
    monkeypatch.setattr(
        tg, "send_to_ceo",
        lambda text: (notices.append(text), {"ok": True, "reason": None})[1],
    )

    result = tg.send_media_batch_to_ceo([str(over)])

    assert result["ok"] is False
    r = result["results"][0]
    assert r["status"] == "failed"
    assert "not found in a fresh folder listing" in r["reason"]
    assert notices == [], "must never notify the CEO of a link that was never verified"


def test_batch_oversized_notify_failure_makes_ok_false_and_status_says_not_notified(
    env, monkeypatch, tmp_path
):
    """D2/D3 bullet 2: when the Drive-notify send fails for any reason, the
    batch's overall "ok" must be False and the per-file status must say the
    CEO was not notified -- a file that reached Drive is not a success when
    the CEO has no link, no message, and no idea the file exists. This is
    the exact live bug (task-80f1405e): the old code kept status "linked"
    and "ok": True here."""
    over = _make_sized_file(tmp_path / "huge.mp4", tg.MAX_MEDIA_BYTES + 1, head=MP4_HEAD)

    drive_ns = _fake_drive_module(listing={"huge.mp4": tg.MAX_MEDIA_BYTES + 1})
    monkeypatch.setattr(tg, "_video_to_drive", lambda: drive_ns)
    monkeypatch.setattr(
        tg, "send_to_ceo",
        lambda text: {"ok": False, "reason": "TELEGRAM_BOT_TOKEN is not set"},
    )

    result = tg.send_media_batch_to_ceo([str(over)])

    assert result["ok"] is False
    r = result["results"][0]
    assert r["status"] == "linked_but_not_notified"
    assert "could not notify the CEO" in r["reason"]
    assert r["link"] is not None, "the Drive link is still reported even though nobody was told"


def test_batch_oversized_notify_falls_back_to_claudeflow_token_on_the_mac(monkeypatch, tmp_path):
    """D3 bullet 1: with TELEGRAM_BOT_TOKEN absent but SECRETARY_BOT_TOKEN
    present (the real Mac shape), the Drive-notify step (send_to_ceo,
    exercised for real here, not mocked) still sends -- asserted on the
    actual token/chat id used in the request, not just that some send
    happened."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CEO_CHAT_ID", raising=False)
    fixture_env = tmp_path / "claudeflow.env"
    fixture_env.write_text(f"SECRETARY_BOT_TOKEN={TOKEN}\nSECRETARY_ADMIN_CHAT_ID={CHAT_ID}\n")
    monkeypatch.setenv("CLAUDEFLOW_ENV", str(fixture_env))

    over = _make_sized_file(tmp_path / "huge.mp4", tg.MAX_MEDIA_BYTES + 1, head=MP4_HEAD)
    drive_ns = _fake_drive_module(listing={"huge.mp4": tg.MAX_MEDIA_BYTES + 1})
    monkeypatch.setattr(tg, "_video_to_drive", lambda: drive_ns)

    captured = {}

    def fake_post(url, json=None, **kw):
        captured["url"] = url
        captured["chat_id"] = json["chat_id"]
        return FakeResponse(200, {"ok": True})

    monkeypatch.setattr(requests, "post", fake_post)

    result = tg.send_media_batch_to_ceo([str(over)])

    assert result["ok"] is True
    assert result["results"][0]["status"] == "linked"
    assert captured.get("url") == f"{tg.TELEGRAM_API_BASE}/bot{TOKEN}/sendMessage", (
        "the notify send must actually go out using the resolved fallback "
        "token, not silently fail for lack of TELEGRAM_BOT_TOKEN"
    )
    assert captured.get("chat_id") == CHAT_ID


def test_batch_partial_failure_is_not_reported_as_flat_success(env, monkeypatch, tmp_path):
    """D4: one bad path alongside a good file must not collapse into a flat
    ok:true -- and each file's own outcome is preserved."""
    _valid_getme(monkeypatch)
    monkeypatch.setattr(requests, "post", lambda *a, **kw: FakeResponse(200, {"ok": True}))

    good = tmp_path / "pic.jpg"
    good.write_bytes(JPEG_HEAD)
    bad_path = "/no/such/path/ever-5555.jpg"

    result = tg.send_media_batch_to_ceo([str(good), bad_path])

    assert result["ok"] is False
    by_path = {r["path"]: r for r in result["results"]}
    assert by_path[str(good)]["status"] == "uploaded"
    assert by_path[bad_path]["status"] == "failed"
    assert "not an existing regular file" in by_path[bad_path]["reason"]


def test_batch_missing_token_reports_failure_for_every_file(monkeypatch, tmp_path):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CEO_CHAT_ID", raising=False)
    calls = []
    monkeypatch.setattr(requests, "post", lambda *a, **kw: calls.append(1))

    f = tmp_path / "pic.jpg"
    f.write_bytes(JPEG_HEAD)

    result = tg.send_media_batch_to_ceo([str(f), "/no/such/path.jpg"])

    assert result["ok"] is False
    assert all(r["status"] == "failed" for r in result["results"])
    assert calls == []


def test_batch_wrong_bot_fails_every_file_without_sending(env, monkeypatch, tmp_path):
    post_calls = []
    _valid_getme(monkeypatch, username="SomeOtherBot")
    monkeypatch.setattr(requests, "post", lambda *a, **kw: post_calls.append(1))

    f1 = tmp_path / "a.jpg"
    f1.write_bytes(JPEG_HEAD)
    f2 = tmp_path / "b.jpg"
    f2.write_bytes(JPEG_HEAD)

    result = tg.send_media_batch_to_ceo([str(f1), str(f2)])

    assert result["ok"] is False
    assert all(r["status"] == "failed" for r in result["results"])
    assert post_calls == []


# ---------------------------------------------------------------------------
# send_media_batch_to_ceo -- D6: the token never leaks, including the new
# sendMediaGroup path
# ---------------------------------------------------------------------------

def test_batch_token_never_leaks_through_media_group_network_error(env, monkeypatch, tmp_path):
    _valid_getme(monkeypatch)

    def boom(url, **kw):
        if url.endswith("/sendMediaGroup"):
            raise requests.ConnectionError(
                f"HTTPSConnectionPool(host='api.telegram.org', port=443): "
                f"Max retries exceeded with url: /bot{TOKEN}/sendMediaGroup"
            )
        return FakeResponse(200, {"ok": True})

    monkeypatch.setattr(requests, "post", boom)

    f1 = tmp_path / "a.jpg"
    f1.write_bytes(JPEG_HEAD)
    f2 = tmp_path / "b.jpg"
    f2.write_bytes(JPEG_HEAD)

    result = tg.send_media_batch_to_ceo([str(f1), str(f2)])

    assert result["ok"] is False
    for r in result["results"]:
        assert r["status"] == "failed"
        assert TOKEN not in r["reason"]
    assert TOKEN not in str(result)


def test_batch_token_never_leaks_through_document_send_network_error(env, monkeypatch, tmp_path):
    _valid_getme(monkeypatch)

    def boom(*a, **kw):
        raise requests.ConnectionError(
            f"HTTPSConnectionPool(host='api.telegram.org', port=443): "
            f"Max retries exceeded with url: /bot{TOKEN}/sendDocument"
        )

    monkeypatch.setattr(requests, "post", boom)

    f = tmp_path / "notes.txt"
    f.write_bytes(PLAIN_TEXT)

    result = tg.send_media_batch_to_ceo([str(f)])

    assert result["ok"] is False
    assert TOKEN not in result["results"][0]["reason"]
    assert TOKEN not in str(result)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
