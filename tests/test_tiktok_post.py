"""Unit tests for tools/tiktok_post.py (task-9ba3e449).

Covers:
- Login Kit v2 authorize URL construction (no PKCE for web, exact query fields)
- Pending state file creation and 0600 permissions
- Callback file wait, OAuth token exchange, callback file deletion, token store 0600 permissions
- OAuth refresh_token flow and creator_info/query endpoint
- Chunk calculation math per TikTok's Media Transfer Guide (<5MB, single-chunk, exact multiple,
  floor division with oversized final chunk, boundary validation)
- Direct Post (/v2/post/publish/video/init/) and Draft (/v2/post/publish/inbox/video/init/)
  chunked PUT upload and status/fetch polling until PUBLISH_COMPLETE or FAILED
- Zero secrets (TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, code, access_token, refresh_token)
  leaked to stdout/stderr.

No network calls are made; the HTTP layer is completely mocked.
"""
from __future__ import annotations

import io
import json
import stat
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from tools import tiktok_post as tp

FAKE_CLIENT_KEY = "aw_client_key_secret_111111"
FAKE_CLIENT_SECRET = "cs_client_secret_value_222222"
FAKE_AUTH_CODE = "ttc_auth_code_secret_333333"
FAKE_ACCESS_TOKEN = "act.access_token_secret_444444"
FAKE_REFRESH_TOKEN = "rft.refresh_token_secret_555555"
FAKE_ACCESS_TOKEN_2 = "act.rotated_access_token_666666"
FAKE_REFRESH_TOKEN_2 = "rft.rotated_refresh_token_777777"
FAKE_STATE = "st_black_liquidity_0123456789abcdef"


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Set fake Infisical env vars, isolate state_dir to tmp_path, and block real network."""
    monkeypatch.setenv("TIKTOK_CLIENT_KEY", FAKE_CLIENT_KEY)
    monkeypatch.setenv("TIKTOK_CLIENT_SECRET", FAKE_CLIENT_SECRET)
    monkeypatch.setenv("TIKTOK_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(tp, "STATE_DIR", tmp_path)

    def _forbid_real_urlopen(*args, **kwargs):
        raise AssertionError("Real network call attempted in unit test!")

    monkeypatch.setattr(urllib.request, "urlopen", _forbid_real_urlopen)


def _assert_mode_0600(path: Path) -> None:
    assert path.exists(), f"Expected file {path} to exist"
    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode == 0o600, f"Expected mode 0600 on {path}, got {oct(mode)}"


def _assert_no_secrets(text: str, *, allow_client_key: bool = False) -> None:
    forbidden = [
        FAKE_CLIENT_SECRET,
        FAKE_AUTH_CODE,
        FAKE_ACCESS_TOKEN,
        FAKE_REFRESH_TOKEN,
        FAKE_ACCESS_TOKEN_2,
        FAKE_REFRESH_TOKEN_2,
    ]
    if not allow_client_key:
        forbidden.append(FAKE_CLIENT_KEY)
    for secret in forbidden:
        assert secret not in text, f"Secret value leaked into output: {secret!r}"


# ── 1. Authorize URL & pending-<state>.json permissions ──────────────────────

def test_auth_url_builds_v2_authorize_url_and_writes_0600_pending_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    rc = tp.main(["auth-url", "--account", "black_liquidity", "--state", FAKE_STATE])
    assert rc == 0

    captured = capsys.readouterr()
    _assert_no_secrets(captured.out, allow_client_key=True)
    _assert_no_secrets(captured.err, allow_client_key=False)

    url = captured.out.strip()
    assert url.startswith("https://www.tiktok.com/v2/auth/authorize/?")

    parsed = urllib.parse.urlsplit(url)
    qs = urllib.parse.parse_qs(parsed.query)
    assert qs["client_key"] == [FAKE_CLIENT_KEY]
    assert qs["response_type"] == ["code"]
    assert qs["scope"] == ["user.info.basic,video.upload,video.publish"]
    assert qs["redirect_uri"] == ["https://terminal.mooniex.com/tiktok/callback"]
    assert qs["state"] == [FAKE_STATE]
    # Web Login Kit v2 uses confidential client_secret and does not require PKCE.
    assert "code_challenge" not in qs
    assert "code_challenge_method" not in qs

    pending_file = tmp_path / f"pending-{FAKE_STATE}.json"
    _assert_mode_0600(pending_file)
    pending_data = json.loads(pending_file.read_text(encoding="utf-8"))
    assert pending_data["state"] == FAKE_STATE
    assert pending_data["account"] == "black_liquidity"
    assert pending_data["redirect_uri"] == "https://terminal.mooniex.com/tiktok/callback"
    assert pending_data["scope"] == "user.info.basic,video.upload,video.publish"


def test_auth_url_generates_valid_random_state_when_not_provided(tmp_path: Path):
    url, state, pending_file = tp.build_auth_url(account="black_liquidity", state_dir=tmp_path)
    assert tp.STATE_RE.match(state)
    assert f"state={state}" in url
    _assert_mode_0600(pending_file)


def test_callback_file_subcommand_prints_path_and_validates_state(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    rc = tp.main(["callback-file", "--state", FAKE_STATE])
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == str(tmp_path / f"callback-{FAKE_STATE}.json")

    rc_bad = tp.main(["callback-file", "--state", "../bad"])
    assert rc_bad == 1
    captured_bad = capsys.readouterr()
    assert "state must match" in captured_bad.err


# ── 2. Callback wait, token exchange, 0600 token store, callback deletion ────

def test_exchange_waits_for_callback_stores_0600_tokens_and_deletes_callback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    tp.build_auth_url(account="black_liquidity", state=FAKE_STATE, state_dir=tmp_path)
    cb_path = tmp_path / f"callback-{FAKE_STATE}.json"

    # Simulate callback file appearing on the second poll iteration
    poll_count = {"n": 0}

    def fake_sleep(seconds: float) -> None:
        poll_count["n"] += 1
        if poll_count["n"] == 1:
            tp.write_json_0600(cb_path, {"state": FAKE_STATE, "code": FAKE_AUTH_CODE})

    recorded_requests: list[tuple[str, str, dict[str, str], bytes]] = []

    def fake_urlopen(req: urllib.request.Request, timeout: float = 60.0):
        recorded_requests.append(
            (req.get_method(), req.full_url, dict(req.header_items()), req.data or b"")
        )
        resp_body = json.dumps({
            "open_id": "open_id_black_liquidity_01",
            "scope": "user.info.basic,video.upload,video.publish",
            "access_token": FAKE_ACCESS_TOKEN,
            "expires_in": 86400,
            "refresh_token": FAKE_REFRESH_TOKEN,
            "refresh_expires_in": 31536000,
            "token_type": "Bearer",
        }).encode("utf-8")

        class _FakeResp(io.BytesIO):
            status = 200
            headers = {"Content-Type": "application/json"}

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        return _FakeResp(resp_body)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(tp.time, "sleep", fake_sleep)

    rc = tp.main(["exchange", "--state", FAKE_STATE, "--timeout", "10", "--poll-interval", "0.01"])
    assert rc == 0
    assert poll_count["n"] == 1

    # Callback file MUST be deleted after exchange
    assert not cb_path.exists()

    # Verify HTTP request sent to TikTok OAuth token endpoint
    assert len(recorded_requests) == 1
    method, url, headers, body = recorded_requests[0]
    assert method == "POST"
    assert url == "https://open.tiktokapis.com/v2/oauth/token/"
    assert any(
        k.lower() == "content-type" and "application/x-www-form-urlencoded" in v.lower()
        for k, v in headers.items()
    )
    form = urllib.parse.parse_qs(body.decode("utf-8"))
    assert form["client_key"] == [FAKE_CLIENT_KEY]
    assert form["client_secret"] == [FAKE_CLIENT_SECRET]
    assert form["code"] == [FAKE_AUTH_CODE]
    assert form["grant_type"] == ["authorization_code"]
    assert form["redirect_uri"] == ["https://terminal.mooniex.com/tiktok/callback"]

    # Verify token store file & 0600 permissions
    tok_file = tmp_path / "tokens-black_liquidity.json"
    _assert_mode_0600(tok_file)
    stored = json.loads(tok_file.read_text(encoding="utf-8"))
    assert stored["access_token"] == FAKE_ACCESS_TOKEN
    assert stored["refresh_token"] == FAKE_REFRESH_TOKEN
    assert stored["open_id"] == "open_id_black_liquidity_01"
    assert stored["expires_in"] == 86400
    assert "expiry" in stored and stored["expiry"]
    assert "expires_at" in stored and isinstance(stored["expires_at"], int)

    # Verify no secret or token appears in stdout or stderr
    captured = capsys.readouterr()
    _assert_no_secrets(captured.out)
    _assert_no_secrets(captured.err)
    assert "open_id_black_liquidity_01" in captured.out


# ── 3. Refresh & creator-info ────────────────────────────────────────────────

def test_refresh_rotates_tokens_and_creator_info_prints_exact_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    tok_file = tmp_path / "tokens-black_liquidity.json"
    tp.write_json_0600(tok_file, {
        "account": "black_liquidity",
        "open_id": "open_id_black_liquidity_01",
        "access_token": FAKE_ACCESS_TOKEN,
        "refresh_token": FAKE_REFRESH_TOKEN,
        "expires_in": 86400,
        "expiry": "2026-11-19T00:00:00+00:00",
    })

    calls: list[tuple[str, str, dict[str, str], bytes | None]] = []

    def fake_http(method: str, url: str, headers: dict[str, str], body: bytes | None = None):
        calls.append((method, url, headers, body))
        if url == tp.TOKEN_URL:
            form = urllib.parse.parse_qs((body or b"").decode("utf-8"))
            assert form["grant_type"] == ["refresh_token"]
            assert form["refresh_token"] == [FAKE_REFRESH_TOKEN]
            assert form["client_key"] == [FAKE_CLIENT_KEY]
            assert form["client_secret"] == [FAKE_CLIENT_SECRET]
            return 200, {}, json.dumps({
                "open_id": "open_id_black_liquidity_01",
                "scope": "user.info.basic,video.upload,video.publish",
                "access_token": FAKE_ACCESS_TOKEN_2,
                "expires_in": 86400,
                "refresh_token": FAKE_REFRESH_TOKEN_2,
                "refresh_expires_in": 31536000,
                "token_type": "Bearer",
            }).encode("utf-8")
        if url == tp.CREATOR_INFO_URL:
            assert headers.get("Authorization") == f"Bearer {FAKE_ACCESS_TOKEN_2}"
            return 200, {}, json.dumps({
                "data": {
                    "creator_avatar_url": "https://example.com/avatar.jpeg",
                    "creator_username": "black_liquidity",
                    "creator_nickname": "BLACK LIQUIDITY",
                    "privacy_level_options": [
                        "PUBLIC_TO_EVERYONE",
                        "MUTUAL_FOLLOW_FRIENDS",
                        "FOLLOWER_OF_CREATOR",
                        "SELF_ONLY",
                    ],
                    "comment_disabled": False,
                    "duet_disabled": False,
                    "stitch_disabled": False,
                    "max_video_post_duration_sec": 600,
                },
                "error": {"code": "ok", "message": "", "log_id": "log_123"},
            }).encode("utf-8")
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(tp, "_http_request", fake_http)

    rc_refresh = tp.main(["refresh", "--account", "black_liquidity"])
    assert rc_refresh == 0
    _assert_mode_0600(tok_file)
    rec = tp.load_tokens("black_liquidity", state_dir=tmp_path)
    assert rec["access_token"] == FAKE_ACCESS_TOKEN_2
    assert rec["refresh_token"] == FAKE_REFRESH_TOKEN_2

    rc_ci = tp.main(["creator-info", "--account", "black_liquidity"])
    assert rc_ci == 0

    captured = capsys.readouterr()
    _assert_no_secrets(captured.out)
    _assert_no_secrets(captured.err)
    assert "creator_nickname: BLACK LIQUIDITY" in captured.out
    assert "privacy_level_options: PUBLIC_TO_EVERYONE,MUTUAL_FOLLOW_FRIENDS,FOLLOWER_OF_CREATOR,SELF_ONLY" in captured.out
    assert "max_video_post_duration_sec: 600" in captured.out


# ── 4. Chunk math (TikTok Media Transfer Guide rules) ────────────────────────

def test_chunk_math_small_file_under_5mb():
    plan = tp.compute_chunks(video_size=2_500_000)
    assert plan.video_size == 2_500_000
    assert plan.chunk_size == 2_500_000
    assert plan.total_chunk_count == 1
    assert len(plan.chunks) == 1
    assert plan.chunks[0].start == 0
    assert plan.chunks[0].end == 2_499_999
    assert plan.chunks[0].size == 2_500_000
    assert plan.chunks[0].content_range == "bytes 0-2499999/2500000"


def test_chunk_math_file_smaller_than_default_chunk_size():
    size = 7 * 1024 * 1024  # 7 MiB (< 10 MiB default chunk size)
    plan = tp.compute_chunks(video_size=size, chunk_size=10 * 1024 * 1024)
    assert plan.chunk_size == size
    assert plan.total_chunk_count == 1
    assert plan.chunks[0].content_range == f"bytes 0-{size - 1}/{size}"


def test_chunk_math_exact_multiple():
    chunk_sz = 10 * 1024 * 1024
    total_sz = 20 * 1024 * 1024
    plan = tp.compute_chunks(video_size=total_sz, chunk_size=chunk_sz)
    assert plan.chunk_size == chunk_sz
    assert plan.total_chunk_count == 2
    assert [c.content_range for c in plan.chunks] == [
        f"bytes 0-{chunk_sz - 1}/{total_sz}",
        f"bytes {chunk_sz}-{total_sz - 1}/{total_sz}",
    ]


def test_chunk_math_tiktok_docs_floor_rule_merges_remainder_into_final_chunk():
    # Official TikTok Media Transfer Guide example: 50,000,123 bytes with 10,000,000 chunk_size
    # -> total_chunk_count = floor(50000123 / 10000000) = 5; last chunk absorbs trailing 123 bytes.
    plan = tp.compute_chunks(video_size=50_000_123, chunk_size=10_000_000)
    assert plan.total_chunk_count == 5
    assert plan.chunk_size == 10_000_000
    assert len(plan.chunks) == 5
    for i in range(4):
        assert plan.chunks[i].size == 10_000_000
        assert plan.chunks[i].start == i * 10_000_000
        assert plan.chunks[i].end == (i + 1) * 10_000_000 - 1
    assert plan.chunks[4].start == 40_000_000
    assert plan.chunks[4].end == 50_000_122
    assert plan.chunks[4].size == 10_000_123
    assert plan.chunks[4].content_range == "bytes 40000000-50000122/50000123"


def test_chunk_math_rejects_invalid_sizes():
    with pytest.raises(ValueError):
        tp.compute_chunks(0)
    with pytest.raises(ValueError):
        tp.compute_chunks(20 * 1024 * 1024, chunk_size=1 * 1024 * 1024)  # < 5 MiB
    with pytest.raises(ValueError):
        tp.compute_chunks(100 * 1024 * 1024, chunk_size=70 * 1024 * 1024)  # > 64 MiB


# ── 5. Direct Post, Draft upload, chunked PUT, and status polling ────────────

def test_post_direct_post_multi_chunk_upload_and_status_polling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    tok_file = tmp_path / "tokens-black_liquidity.json"
    tp.write_json_0600(tok_file, {
        "account": "black_liquidity",
        "open_id": "open_id_black_liquidity_01",
        "access_token": FAKE_ACCESS_TOKEN,
        "refresh_token": FAKE_REFRESH_TOKEN,
    })

    # Create a 12 MiB test MP4 file so that with a 5 MiB chunk size we get floor(12 / 5) = 2 chunks
    # (Chunk 0: 5 MiB, Chunk 1: 7 MiB).
    chunk_sz = 5 * 1024 * 1024
    video_sz = 12 * 1024 * 1024
    mp4_path = tmp_path / "episode.mp4"
    video_bytes = (b"MOONIEX_VIDEO_BLOCK_" * ((video_sz // 20) + 1))[:video_sz]
    mp4_path.write_bytes(video_bytes)

    upload_url = "https://open-upload.tiktokapis.com/video/?upload_id=up_1&upload_token=ut_secret"
    publish_id = "v_pub_file~v2-1.987654321"
    status_sequence = ["PROCESSING_UPLOAD", "SEND_TO_AUDIT", "PUBLISH_COMPLETE"]
    put_calls: list[tuple[dict[str, str], bytes]] = []
    init_calls: list[dict[str, Any]] = []
    status_calls: list[dict[str, Any]] = []

    def fake_http(method: str, url: str, headers: dict[str, str], body: bytes | None = None):
        if url == tp.DIRECT_POST_INIT_URL:
            assert method == "POST"
            assert headers["Authorization"] == f"Bearer {FAKE_ACCESS_TOKEN}"
            parsed_init = json.loads((body or b"{}").decode("utf-8"))
            init_calls.append(parsed_init)
            return 200, {}, json.dumps({
                "data": {"publish_id": publish_id, "upload_url": upload_url},
                "error": {"code": "ok", "message": "", "log_id": "init_log_1"},
            }).encode("utf-8")

        if url == upload_url:
            assert method == "PUT"
            put_calls.append((headers, body or b""))
            code = 206 if len(put_calls) < 2 else 201
            return code, {}, b""

        if url == tp.STATUS_FETCH_URL:
            assert method == "POST"
            assert headers["Authorization"] == f"Bearer {FAKE_ACCESS_TOKEN}"
            req_json = json.loads((body or b"{}").decode("utf-8"))
            status_calls.append(req_json)
            next_st = status_sequence.pop(0)
            return 200, {}, json.dumps({
                "data": {
                    "status": next_st,
                    "fail_reason": "",
                    "publicaly_available_post_id": [7300000000001] if next_st == "PUBLISH_COMPLETE" else [],
                    "uploaded_bytes": video_sz,
                },
                "error": {"code": "ok", "message": "", "log_id": "st_log"},
            }).encode("utf-8")

        raise AssertionError(f"Unexpected HTTP call: {method} {url}")

    monkeypatch.setattr(tp, "_http_request", fake_http)
    monkeypatch.setattr(tp.time, "sleep", lambda _: None)

    rc = tp.main([
        "post",
        "--account", "black_liquidity",
        "--file", str(mp4_path),
        "--caption", "BLACK LIQUIDITY EP1 #blackliquidity",
        "--chunk-size", str(chunk_sz),
        "--poll-interval", "0.01",
    ])
    assert rc == 0

    # 1. Verify Direct Post init body exact field names
    assert len(init_calls) == 1
    assert init_calls[0] == {
        "post_info": {
            "title": "BLACK LIQUIDITY EP1 #blackliquidity",
            "privacy_level": "SELF_ONLY",
            "disable_comment": False,
            "disable_duet": False,
            "disable_stitch": False,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_sz,
            "chunk_size": chunk_sz,
            "total_chunk_count": 2,
        },
    }

    # 2. Verify PUT chunk headers & exact byte slices
    assert len(put_calls) == 2
    h0, b0 = put_calls[0]
    assert h0["Content-Type"] == "video/mp4"
    assert h0["Content-Length"] == str(chunk_sz)
    assert h0["Content-Range"] == f"bytes 0-{chunk_sz - 1}/{video_sz}"
    assert b0 == video_bytes[:chunk_sz]

    h1, b1 = put_calls[1]
    assert h1["Content-Type"] == "video/mp4"
    assert h1["Content-Length"] == str(video_sz - chunk_sz)
    assert h1["Content-Range"] == f"bytes {chunk_sz}-{video_sz - 1}/{video_sz}"
    assert b1 == video_bytes[chunk_sz:]

    # 3. Verify status/fetch polling
    assert len(status_calls) == 3
    assert all(c == {"publish_id": publish_id} for c in status_calls)

    # 4. Verify CLI prints publish_id and final status ONLY, with zero secrets
    captured = capsys.readouterr()
    _assert_no_secrets(captured.out)
    _assert_no_secrets(captured.err)
    lines = [ln.strip() for ln in captured.out.strip().splitlines() if ln.strip()]
    assert lines == [
        f"publish_id: {publish_id}",
        "status: PUBLISH_COMPLETE",
    ]


def test_post_draft_uses_inbox_endpoint_and_handles_failed_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    tok_file = tmp_path / "tokens-black_liquidity.json"
    tp.write_json_0600(tok_file, {
        "account": "black_liquidity",
        "open_id": "open_id_black_liquidity_01",
        "access_token": FAKE_ACCESS_TOKEN,
        "refresh_token": FAKE_REFRESH_TOKEN,
    })

    mp4_path = tmp_path / "small.mp4"
    mp4_path.write_bytes(b"0123456789" * 100)
    video_sz = mp4_path.stat().st_size

    init_urls: list[str] = []
    init_bodies: list[dict[str, Any]] = []

    def fake_http(method: str, url: str, headers: dict[str, str], body: bytes | None = None):
        if url == tp.INBOX_VIDEO_INIT_URL:
            init_urls.append(url)
            init_bodies.append(json.loads((body or b"{}").decode("utf-8")))
            return 200, {}, json.dumps({
                "data": {
                    "publish_id": "v_inbox~v2.555",
                    "upload_url": "https://open-upload.tiktokapis.com/video/?upload_id=up_2",
                },
                "error": {"code": "ok", "message": ""},
            }).encode("utf-8")
        if url.startswith("https://open-upload.tiktokapis.com/"):
            return 201, {}, b""
        if url == tp.STATUS_FETCH_URL:
            return 200, {}, json.dumps({
                "data": {"status": "FAILED", "fail_reason": "video_pull_failed"},
                "error": {"code": "ok", "message": ""},
            }).encode("utf-8")
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(tp, "_http_request", fake_http)

    rc = tp.main([
        "post",
        "--account", "black_liquidity",
        "--file", str(mp4_path),
        "--draft",
    ])
    assert rc == 1
    assert init_urls == [tp.INBOX_VIDEO_INIT_URL]
    assert init_bodies == [{
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_sz,
            "chunk_size": video_sz,
            "total_chunk_count": 1,
        }
    }]

    captured = capsys.readouterr()
    _assert_no_secrets(captured.out)
    _assert_no_secrets(captured.err)
    lines = [ln.strip() for ln in captured.out.strip().splitlines() if ln.strip()]
    assert lines == [
        "publish_id: v_inbox~v2.555",
        "status: FAILED",
    ]


def test_error_messages_never_leak_secrets_to_stdout_or_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    tok_file = tmp_path / "tokens-black_liquidity.json"
    tp.write_json_0600(tok_file, {
        "account": "black_liquidity",
        "open_id": "open_id_black_liquidity_01",
        "access_token": FAKE_ACCESS_TOKEN,
        "refresh_token": FAKE_REFRESH_TOKEN,
    })

    def failing_http(method: str, url: str, headers: dict[str, str], body: bytes | None = None):
        # Maliciously echo every secret in the error message from upstream
        return 401, {}, json.dumps({
            "error": {
                "code": "access_token_invalid",
                "message": (
                    f"Bad token {FAKE_ACCESS_TOKEN} or refresh {FAKE_REFRESH_TOKEN} "
                    f"for client {FAKE_CLIENT_KEY} / {FAKE_CLIENT_SECRET}"
                ),
                "log_id": "err_log_99",
            }
        }).encode("utf-8")

    monkeypatch.setattr(tp, "_http_request", failing_http)
    rc = tp.main(["creator-info", "--account", "black_liquidity"])
    assert rc == 1

    captured = capsys.readouterr()
    _assert_no_secrets(captured.out)
    _assert_no_secrets(captured.err)
    assert "[REDACTED]" in captured.err
