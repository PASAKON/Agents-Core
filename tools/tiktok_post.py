#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TikTok Content Posting API v2 & Login Kit v2 CLI (task-9ba3e449, Order O-20261119-0006-c311).

Posts a video to TikTok (e.g. @black_liquidity) through the official Content Posting API
using the sandbox/production app "MoonieX Poster" (Login Kit + Content Posting API).

Run via org-python so Infisical Agents-Core/prod injects TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET:
    bash scripts/hub/org-python.sh tools/tiktok_post.py auth-url --account black_liquidity
    bash scripts/hub/org-python.sh tools/tiktok_post.py exchange --state <state>
    bash scripts/hub/org-python.sh tools/tiktok_post.py refresh --account black_liquidity
    bash scripts/hub/org-python.sh tools/tiktok_post.py creator-info --account black_liquidity
    bash scripts/hub/org-python.sh tools/tiktok_post.py post --account black_liquidity --file clip.mp4 --caption "..." [--draft]

Official documentation references & exact field names quoted from developers.tiktok.com:
- Login Kit for Web (`doc/login-kit-web`):
  - Endpoint: `GET https://www.tiktok.com/v2/auth/authorize/`
  - Query parameters: `client_key`, `scope`, `response_type` ("code"), `redirect_uri`, `state`.
  - PKCE (`code_challenge` / `code_verifier`): per `doc/oauth-user-access-token-management`,
    `code_verifier` is "Required for mobile and desktop apps" and is NOT required for Web
    server-side confidential-client OAuth flows.
- OAuth User Access Token Management (`doc/oauth-user-access-token-management`):
  - Endpoint: `POST https://open.tiktokapis.com/v2/oauth/token/`
  - Header: `Content-Type: application/x-www-form-urlencoded`
  - Authorization-code exchange fields: `client_key`, `client_secret`, `code`,
    `grant_type` ("authorization_code"), `redirect_uri`.
  - Refresh-token fields: `client_key`, `client_secret`, `grant_type` ("refresh_token"),
    `refresh_token`.
  - Token response fields: `open_id`, `scope`, `access_token`, `expires_in`,
    `refresh_token`, `refresh_expires_in`, `token_type`.
- Content Posting API — Get Creator Info (`doc/content-posting-api-reference-get-creator-info`):
  - Endpoint: `POST https://open.tiktokapis.com/v2/post/publish/creator_info/query/`
  - Response `data` fields: `creator_avatar_url`, `creator_username`, `creator_nickname`,
    `privacy_level_options`, `comment_disabled`, `duet_disabled`, `stitch_disabled`,
    `max_video_post_duration_sec`.
- Content Posting API — Direct Post (`doc/content-posting-api-reference-direct-post`):
  - Endpoint: `POST https://open.tiktokapis.com/v2/post/publish/video/init/`
  - Request `post_info` fields: `title`, `privacy_level` ("SELF_ONLY" for unaudited apps;
    options: "PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "FOLLOWER_OF_CREATOR", "SELF_ONLY"),
    `disable_comment`, `disable_duet`, `disable_stitch`, `video_cover_timestamp_ms`.
  - Request `source_info` fields: `source` ("FILE_UPLOAD" or "PULL_FROM_URL"),
    `video_size`, `chunk_size`, `total_chunk_count`.
  - Response `data` fields: `publish_id`, `upload_url`.
- Content Posting API — Upload Video / Inbox Draft (`doc/content-posting-api-reference-upload-video`):
  - Endpoint: `POST https://open.tiktokapis.com/v2/post/publish/inbox/video/init/`
  - Request `source_info` fields: `source` ("FILE_UPLOAD"), `video_size`, `chunk_size`,
    `total_chunk_count`.
  - Response `data` fields: `publish_id`, `upload_url`.
- Content Posting API — Media Transfer Guide (`doc/content-posting-api-media-transfer-guide`):
  - Chunk upload: `PUT <upload_url>` with headers `Content-Type: video/mp4`,
    `Content-Length: <chunk_bytes>`, `Content-Range: bytes <start>-<end>/<video_size>`.
  - Chunk size rules: each chunk must be between 5 MB and 64 MB, except videos < 5 MB
    which must be uploaded in a single chunk (`chunk_size = video_size`, `total_chunk_count = 1`).
    `total_chunk_count = floor(video_size / chunk_size)`; the final chunk absorbs trailing
    bytes up to 128 MB.
- Content Posting API — Get Post Status (`doc/content-posting-api-reference-get-upload-status`):
  - Endpoint: `POST https://open.tiktokapis.com/v2/post/publish/status/fetch/`
  - Request fields: `publish_id`.
  - Response `data` fields: `status` ("PROCESSING_UPLOAD", "PROCESSING_DOWNLOAD",
    "SEND_TO_AUDIT", "SEND_TO_USER_INBOX", "PUBLISH_COMPLETE", "FAILED"),
    `fail_reason`, `publicaly_available_post_id`, `uploaded_bytes`.

Security rule: Never print, log, or commit a key, authorization code, or token.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import stat
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

ROOT = Path(__file__).resolve().parent.parent
CANONICAL_CALLBACK_DIR = Path("/opt/MoonieXHQ/Agents/Core/state/tiktok")
STATE_DIR = Path(os.environ.get("TIKTOK_STATE_DIR", str(ROOT / "state" / "tiktok")))

AUTHORIZE_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
CREATOR_INFO_URL = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
DIRECT_POST_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
INBOX_VIDEO_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
STATUS_FETCH_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

DEFAULT_ACCOUNT = "black_liquidity"
DEFAULT_SCOPES = "user.info.basic,video.upload,video.publish"
DEFAULT_REDIRECT_URI = "https://terminal.mooniex.com/tiktok/callback"
DEFAULT_PRIVACY_LEVEL = "SELF_ONLY"

MIN_CHUNK_SIZE = 5 * 1024 * 1024          # 5 MiB (5,242,880 bytes)
MAX_CHUNK_SIZE = 64 * 1024 * 1024         # 64 MiB (67,108,864 bytes)
MAX_FINAL_CHUNK_SIZE = 128 * 1024 * 1024  # 128 MiB (134,217,728 bytes)
DEFAULT_CHUNK_SIZE = 10 * 1024 * 1024     # 10 MiB (10,485,760 bytes)
MAX_TOTAL_CHUNKS = 1000

DEFAULT_EXCHANGE_WAIT_S = 600.0           # 10 minutes
DEFAULT_EXCHANGE_POLL_S = 1.0
DEFAULT_STATUS_POLL_S = 3.0
DEFAULT_STATUS_TIMEOUT_S = 300.0
HTTP_TIMEOUT_S = 60.0

STATE_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
ACCOUNT_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")

IN_PROGRESS_STATUSES = frozenset({
    "PROCESSING_UPLOAD",
    "PROCESSING_DOWNLOAD",
    "SEND_TO_AUDIT",
})


class TikTokError(RuntimeError):
    """Base error for TikTok posting tool (guaranteed secret-redacted)."""


class TikTokConfigError(TikTokError):
    """Missing or invalid configuration/credentials."""


class TikTokAPIError(TikTokError):
    """HTTP or API-level failure returned by TikTok."""

    def __init__(self, message: str, status_code: int | None = None,
                 error_code: str | None = None, log_id: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.log_id = log_id


@dataclass(frozen=True)
class ChunkSpec:
    index: int
    start: int
    end: int
    total_size: int

    @property
    def size(self) -> int:
        return self.end - self.start + 1

    @property
    def content_range(self) -> str:
        return f"bytes {self.start}-{self.end}/{self.total_size}"


@dataclass(frozen=True)
class ChunkPlan:
    video_size: int
    chunk_size: int
    total_chunk_count: int
    chunks: list[ChunkSpec]


HttpFunc = Callable[[str, str, dict[str, str], bytes | None], tuple[int, dict[str, str], bytes]]


def _redact(text: str, extra_secrets: Iterable[str] = ()) -> str:
    """Scrub any known client key, client secret, token, or auth code from text."""
    if not text:
        return text
    candidates = [
        os.environ.get("TIKTOK_CLIENT_KEY", ""),
        os.environ.get("TIKTOK_CLIENT_SECRET", ""),
        *extra_secrets,
    ]
    out = text
    for secret in candidates:
        if secret and len(secret) >= 4:
            out = out.replace(secret, "[REDACTED]")
    out = re.sub(r"\b(?:act|rft)\.[A-Za-z0-9._~-]+", "[REDACTED]", out)
    out = re.sub(
        r"(?i)(\b(?:access_token|refresh_token|client_secret|client_key|Bearer)\b[\s:=\"']+)([^\s\"'&,;}]+)",
        r"\1[REDACTED]",
        out,
    )
    return out


def _require_client_key() -> str:
    val = os.environ.get("TIKTOK_CLIENT_KEY", "").strip()
    if not val:
        raise TikTokConfigError("TIKTOK_CLIENT_KEY is not set in environment")
    return val


def _require_client_credentials() -> tuple[str, str]:
    key = _require_client_key()
    secret = os.environ.get("TIKTOK_CLIENT_SECRET", "").strip()
    if not secret:
        raise TikTokConfigError("TIKTOK_CLIENT_SECRET is not set in environment")
    return key, secret


def validate_state(state: str) -> str:
    if not isinstance(state, str) or not STATE_RE.match(state):
        raise ValueError("state must match [A-Za-z0-9_-]{16,64}")
    return state


def validate_account(account: str) -> str:
    if not isinstance(account, str) or not ACCOUNT_RE.match(account):
        raise ValueError("account must match [A-Za-z0-9_.-]{1,64}")
    return account


def generate_state() -> str:
    """Generate a random URL-safe state string matching [A-Za-z0-9_-]{16,64}."""
    state = secrets.token_urlsafe(24)
    return validate_state(state)


def _resolve_state_dir(state_dir: Path | None = None) -> Path:
    if state_dir is not None:
        return Path(state_dir)
    env_override = os.environ.get("TIKTOK_STATE_DIR")
    if env_override:
        return Path(env_override)
    return STATE_DIR


def pending_state_path(state: str, state_dir: Path | None = None) -> Path:
    validate_state(state)
    return _resolve_state_dir(state_dir) / f"pending-{state}.json"


def callback_state_path(state: str, state_dir: Path | None = None) -> Path:
    validate_state(state)
    return _resolve_state_dir(state_dir) / f"callback-{state}.json"


def tokens_path(account: str, state_dir: Path | None = None) -> Path:
    validate_account(account)
    return _resolve_state_dir(state_dir) / f"tokens-{account}.json"


def write_json_0600(path: Path, payload: dict[str, Any]) -> Path:
    """Atomically write JSON with strict 0600 permissions from file creation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(str(tmp), flags, 0o600)
    try:
        try:
            os.fchmod(fd, 0o600)
        except AttributeError:
            os.chmod(tmp, 0o600)
        encoded = (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        os.write(fd, encoded)
    finally:
        os.close(fd)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    os.chmod(path, 0o600)
    return path


def read_json_file(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TikTokError(f"Expected JSON object in {path.name}")
    return data


def _http_request(
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes | None = None,
    timeout: float = HTTP_TIMEOUT_S,
) -> tuple[int, dict[str, str], bytes]:
    """Low-level stdlib HTTP request wrapper. Easy to mock via urlopen or http_fn."""
    req = urllib.request.Request(url=url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", None) or resp.getcode() or 200
            resp_headers = dict(resp.headers.items()) if getattr(resp, "headers", None) else {}
            raw = resp.read()
            return int(status), resp_headers, raw
    except urllib.error.HTTPError as exc:
        raw = b""
        try:
            raw = exc.read()
        except Exception:
            pass
        resp_headers = dict(exc.headers.items()) if getattr(exc, "headers", None) else {}
        return int(exc.code), resp_headers, raw
    except urllib.error.URLError as exc:
        raise TikTokAPIError(_redact(f"Network error calling {url}: {exc}")) from exc


def _parse_json_response(
    status: int,
    raw: bytes,
    context: str,
    extra_secrets: Iterable[str] = (),
) -> dict[str, Any]:
    text = raw.decode("utf-8", errors="replace") if raw else "{}"
    try:
        parsed = json.loads(text) if text.strip() else {}
    except json.JSONDecodeError as exc:
        raise TikTokAPIError(
            _redact(f"{context}: invalid JSON response (HTTP {status})", extra_secrets),
            status_code=status,
        ) from exc
    if not isinstance(parsed, dict):
        raise TikTokAPIError(
            _redact(f"{context}: expected JSON object (HTTP {status})", extra_secrets),
            status_code=status,
        )
    return parsed


def _check_v2_api_error(
    status: int,
    payload: dict[str, Any],
    context: str,
    extra_secrets: Iterable[str] = (),
) -> dict[str, Any]:
    """Validate TikTok v2 JSON response `{data: {...}, error: {code, message, log_id}}`."""
    err = payload.get("error")
    err_code = None
    err_msg = ""
    log_id = payload.get("log_id")
    if isinstance(err, dict):
        err_code = err.get("code")
        err_msg = str(err.get("message") or "")
        log_id = err.get("log_id") or log_id
    elif isinstance(err, str) and err:
        err_code = err
        err_msg = str(payload.get("error_description") or payload.get("message") or "")

    if status >= 400 or (err_code not in (None, "", "ok")):
        safe_msg = _redact(
            f"{context} failed (HTTP {status}, code={err_code or 'http_error'}, "
            f"message={err_msg}, log_id={log_id or ''})",
            extra_secrets,
        )
        raise TikTokAPIError(
            safe_msg,
            status_code=status,
            error_code=str(err_code or "http_error"),
            log_id=str(log_id) if log_id else None,
        )
    data = payload.get("data")
    return data if isinstance(data, dict) else payload


# ── 1. auth-url ──────────────────────────────────────────────────────────────

def build_auth_url(
    account: str = DEFAULT_ACCOUNT,
    *,
    state: str | None = None,
    client_key: str | None = None,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
    scopes: str = DEFAULT_SCOPES,
    state_dir: Path | None = None,
) -> tuple[str, str, Path]:
    """Build the TikTok Login Kit v2 authorize URL and save pending-<state>.json (0600).

    Per `developers.tiktok.com/doc/login-kit-web` and
    `developers.tiktok.com/doc/oauth-user-access-token-management`:
    - Authorize endpoint: `https://www.tiktok.com/v2/auth/authorize/`
    - Query params: `client_key`, `scope`, `response_type=code`, `redirect_uri`, `state`.
    - PKCE (`code_challenge` / `code_verifier`) is NOT included because TikTok's official
      web Login Kit flow uses confidential server-side `client_secret` and explicitly marks
      `code_verifier` as "Required for mobile and desktop apps".

    Returns `(authorize_url, state, pending_file_path)`.
    """
    validate_account(account)
    key = (client_key or _require_client_key()).strip()
    if not key:
        raise TikTokConfigError("TIKTOK_CLIENT_KEY is required")
    st = validate_state(state) if state is not None else generate_state()

    params = {
        "client_key": key,
        "scope": scopes,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": st,
    }
    query = urllib.parse.urlencode(params, safe=",")
    url = f"{AUTHORIZE_URL}?{query}"

    pending_file = pending_state_path(st, state_dir=state_dir)
    record = {
        "state": st,
        "account": account,
        "redirect_uri": redirect_uri,
        "scope": scopes,
        "response_type": "code",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    write_json_0600(pending_file, record)
    return url, st, pending_file


# ── 2. callback-file & exchange ──────────────────────────────────────────────

def _locate_callback_file(state: str, state_dir: Path | None = None) -> Path | None:
    """Return the callback-<state>.json path if it exists in state_dir (or canonical path)."""
    primary = callback_state_path(state, state_dir=state_dir)
    if primary.exists():
        return primary
    # When running from a worktree without an explicit state_dir override, also check
    # the canonical Console write destination /opt/MoonieXHQ/Agents/Core/state/tiktok/.
    if state_dir is None and not os.environ.get("TIKTOK_STATE_DIR"):
        canonical = CANONICAL_CALLBACK_DIR / f"callback-{state}.json"
        if canonical != primary and canonical.exists():
            return canonical
    return None


def wait_for_callback_file(
    state: str,
    *,
    timeout_s: float = DEFAULT_EXCHANGE_WAIT_S,
    poll_interval_s: float = DEFAULT_EXCHANGE_POLL_S,
    state_dir: Path | None = None,
    sleep_fn: Callable[[float], None] | None = None,
    clock_fn: Callable[[], float] | None = None,
) -> tuple[Path, str]:
    """Wait up to `timeout_s` (default 600s = 10 min) for `callback-<state>.json`
    containing `{"state", "code"}` and return `(path, code)`."""
    if sleep_fn is None:
        sleep_fn = time.sleep
    if clock_fn is None:
        clock_fn = time.monotonic
    validate_state(state)
    deadline = clock_fn() + max(0.0, float(timeout_s))
    while True:
        found = _locate_callback_file(state, state_dir=state_dir)
        if found is not None:
            payload = read_json_file(found)
            cb_state = payload.get("state")
            cb_code = payload.get("code")
            if cb_state != state:
                raise TikTokError(f"Callback state mismatch in {found.name}")
            if not isinstance(cb_code, str) or not cb_code.strip():
                raise TikTokError(f"Callback file {found.name} is missing a valid 'code'")
            return found, cb_code.strip()

        now = clock_fn()
        if now >= deadline:
            expected = callback_state_path(state, state_dir=state_dir)
            raise TimeoutError(
                f"Timed out after {timeout_s}s waiting for callback file {expected}"
            )
        remaining = deadline - now
        sleep_fn(min(poll_interval_s, remaining) if poll_interval_s > 0 else 0.0)


def _store_token_response(
    account: str,
    payload: dict[str, Any],
    *,
    state_dir: Path | None = None,
    extra_secrets: Iterable[str] = (),
) -> tuple[Path, dict[str, Any]]:
    """Validate OAuth token response and save to `state/tiktok/tokens-<account>.json` (0600)."""
    token_src = payload
    if "access_token" not in token_src and isinstance(payload.get("data"), dict):
        token_src = payload["data"]

    if "error" in token_src and "access_token" not in token_src:
        err = token_src.get("error")
        desc = token_src.get("error_description") or token_src.get("message") or ""
        log_id = token_src.get("log_id") or payload.get("log_id")
        raise TikTokAPIError(
            _redact(
                f"OAuth token request failed: error={err}, error_description={desc}, log_id={log_id or ''}",
                extra_secrets,
            ),
            error_code=str(err),
            log_id=str(log_id) if log_id else None,
        )

    access_token = str(token_src.get("access_token") or "").strip()
    refresh_token = str(token_src.get("refresh_token") or "").strip()
    open_id = str(token_src.get("open_id") or "").strip()
    if not access_token or not refresh_token or not open_id:
        raise TikTokAPIError(
            _redact(
                "OAuth token response missing required fields (access_token, refresh_token, open_id)",
                extra_secrets,
            )
        )

    now_ts = int(time.time())
    expires_in = int(token_src.get("expires_in", 86400))
    refresh_expires_in = int(token_src.get("refresh_expires_in", 31536000))
    expires_at = now_ts + expires_in
    refresh_expires_at = now_ts + refresh_expires_in
    expiry_iso = datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(timespec="seconds")

    record = {
        "account": account,
        "open_id": open_id,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": str(token_src.get("token_type") or "Bearer"),
        "scope": str(token_src.get("scope") or DEFAULT_SCOPES),
        "expires_in": expires_in,
        "refresh_expires_in": refresh_expires_in,
        "expiry": expiry_iso,
        "expires_at": expires_at,
        "refresh_expires_at": refresh_expires_at,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    out_path = tokens_path(account, state_dir=state_dir)
    write_json_0600(out_path, record)
    return out_path, record


def exchange_code(
    state: str,
    *,
    account: str | None = None,
    redirect_uri: str | None = None,
    timeout_s: float = DEFAULT_EXCHANGE_WAIT_S,
    poll_interval_s: float = DEFAULT_EXCHANGE_POLL_S,
    state_dir: Path | None = None,
    http_fn: HttpFunc | None = None,
    sleep_fn: Callable[[float], None] | None = None,
    clock_fn: Callable[[], float] | None = None,
) -> dict[str, Any]:
    """Wait for `callback-<state>.json`, exchange `code` at `/v2/oauth/token/`,
    save `tokens-<account>.json` (0600), and delete the callback file after."""
    if http_fn is None:
        http_fn = _http_request
    validate_state(state)
    client_key, client_secret = _require_client_credentials()

    pending_file = pending_state_path(state, state_dir=state_dir)
    resolved_account = account
    resolved_redirect = redirect_uri
    if pending_file.exists():
        pending_data = read_json_file(pending_file)
        if pending_data.get("state") and pending_data.get("state") != state:
            raise TikTokError("Pending state file does not match requested state")
        if not resolved_account:
            resolved_account = str(pending_data.get("account") or DEFAULT_ACCOUNT)
        if not resolved_redirect:
            resolved_redirect = str(pending_data.get("redirect_uri") or DEFAULT_REDIRECT_URI)

    resolved_account = validate_account(resolved_account or DEFAULT_ACCOUNT)
    resolved_redirect = resolved_redirect or DEFAULT_REDIRECT_URI

    cb_path, code = wait_for_callback_file(
        state,
        timeout_s=timeout_s,
        poll_interval_s=poll_interval_s,
        state_dir=state_dir,
        sleep_fn=sleep_fn,
        clock_fn=clock_fn,
    )

    form = {
        "client_key": client_key,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": resolved_redirect,
    }
    body = urllib.parse.urlencode(form).encode("utf-8")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Cache-Control": "no-cache",
    }

    try:
        status, _, raw = http_fn("POST", TOKEN_URL, headers, body)
        payload = _parse_json_response(
            status, raw, "OAuth token exchange", extra_secrets=(client_key, client_secret, code)
        )
        if status >= 400 and "error" not in payload:
            raise TikTokAPIError(
                f"OAuth token exchange failed with HTTP {status}", status_code=status
            )
        _, record = _store_token_response(
            resolved_account,
            payload,
            state_dir=state_dir,
            extra_secrets=(client_key, client_secret, code),
        )
    finally:
        try:
            cb_path.unlink(missing_ok=True)
        except OSError:
            pass

    return record


# ── 3. refresh & creator-info ────────────────────────────────────────────────

def load_tokens(account: str = DEFAULT_ACCOUNT, *, state_dir: Path | None = None) -> dict[str, Any]:
    path = tokens_path(account, state_dir=state_dir)
    if not path.exists():
        raise TikTokConfigError(f"Token file not found for account '{account}': {path}")
    return read_json_file(path)


def refresh_tokens(
    account: str = DEFAULT_ACCOUNT,
    *,
    state_dir: Path | None = None,
    http_fn: HttpFunc | None = None,
) -> dict[str, Any]:
    """Refresh user access token via `POST /v2/oauth/token/` (`grant_type=refresh_token`)."""
    if http_fn is None:
        http_fn = _http_request
    validate_account(account)
    client_key, client_secret = _require_client_credentials()
    current = load_tokens(account, state_dir=state_dir)
    current_refresh = str(current.get("refresh_token") or "").strip()
    if not current_refresh:
        raise TikTokConfigError(f"Stored token file for '{account}' has no refresh_token")

    form = {
        "client_key": client_key,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": current_refresh,
    }
    body = urllib.parse.urlencode(form).encode("utf-8")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Cache-Control": "no-cache",
    }
    status, _, raw = http_fn("POST", TOKEN_URL, headers, body)
    payload = _parse_json_response(
        status,
        raw,
        "OAuth token refresh",
        extra_secrets=(client_key, client_secret, current_refresh),
    )
    if status >= 400 and "error" not in payload:
        raise TikTokAPIError(f"OAuth token refresh failed with HTTP {status}", status_code=status)
    _, record = _store_token_response(
        account,
        payload,
        state_dir=state_dir,
        extra_secrets=(client_key, client_secret, current_refresh),
    )
    return record


def query_creator_info(
    account: str = DEFAULT_ACCOUNT,
    *,
    state_dir: Path | None = None,
    http_fn: HttpFunc | None = None,
) -> dict[str, Any]:
    """Call `POST /v2/post/publish/creator_info/query/` and return `data`.

    Official response `data` fields:
    - `creator_nickname`
    - `privacy_level_options`
    - `max_video_post_duration_sec`
    - `creator_username`, `creator_avatar_url`, `comment_disabled`, `duet_disabled`, `stitch_disabled`
    """
    if http_fn is None:
        http_fn = _http_request
    tokens = load_tokens(account, state_dir=state_dir)
    access_token = str(tokens.get("access_token") or "").strip()
    refresh_token = str(tokens.get("refresh_token") or "").strip()
    if not access_token:
        raise TikTokConfigError(f"Stored token file for '{account}' has no access_token")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }
    status, _, raw = http_fn("POST", CREATOR_INFO_URL, headers, b"{}")
    payload = _parse_json_response(
        status, raw, "creator_info/query", extra_secrets=(access_token, refresh_token)
    )
    data = _check_v2_api_error(
        status, payload, "creator_info/query", extra_secrets=(access_token, refresh_token)
    )
    return data


# ── 4. post (Direct Post / Inbox Draft, chunk math, status polling) ──────────

def compute_chunks(video_size: int, chunk_size: int = DEFAULT_CHUNK_SIZE) -> ChunkPlan:
    """Compute TikTok Content Posting API chunk plan per the official Media Transfer Guide.

    Rules from `developers.tiktok.com/doc/content-posting-api-media-transfer-guide`:
    - `video_size` > 0.
    - Videos smaller than 5 MB (`MIN_CHUNK_SIZE`) must be uploaded whole in 1 chunk:
      `chunk_size = video_size`, `total_chunk_count = 1`.
    - Otherwise each chunk must be between 5 MB and 64 MB (`MAX_CHUNK_SIZE`).
      If `video_size < chunk_size`, `chunk_size = video_size` and `total_chunk_count = 1`.
    - When `video_size >= chunk_size`, `total_chunk_count = video_size // chunk_size`
      (rounded down to the nearest integer). Any leftover bytes (`video_size % chunk_size`)
      are merged into the final chunk, which may be up to 128 MB (`MAX_FINAL_CHUNK_SIZE`).
    - `1 <= total_chunk_count <= 1000`.
    """
    if not isinstance(video_size, int) or video_size <= 0:
        raise ValueError("video_size must be a positive integer")
    if not isinstance(chunk_size, int) or chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")

    if video_size < MIN_CHUNK_SIZE:
        eff_chunk_size = video_size
        total_chunks = 1
    else:
        if chunk_size < MIN_CHUNK_SIZE or chunk_size > MAX_CHUNK_SIZE:
            raise ValueError(
                f"chunk_size must be between {MIN_CHUNK_SIZE} (5 MiB) and {MAX_CHUNK_SIZE} (64 MiB)"
            )
        if video_size < chunk_size:
            eff_chunk_size = video_size
            total_chunks = 1
        else:
            eff_chunk_size = chunk_size
            total_chunks = video_size // eff_chunk_size
            if total_chunks > MAX_TOTAL_CHUNKS:
                raise ValueError(
                    f"total_chunk_count ({total_chunks}) exceeds maximum {MAX_TOTAL_CHUNKS}; "
                    f"increase chunk_size up to {MAX_CHUNK_SIZE}"
                )

    chunks: list[ChunkSpec] = []
    for idx in range(total_chunks):
        start = idx * eff_chunk_size
        if idx == total_chunks - 1:
            end = video_size - 1
        else:
            end = (idx + 1) * eff_chunk_size - 1
        spec = ChunkSpec(index=idx, start=start, end=end, total_size=video_size)
        if spec.size > MAX_FINAL_CHUNK_SIZE:
            raise ValueError(
                f"Final chunk size ({spec.size}) exceeds 128 MiB limit ({MAX_FINAL_CHUNK_SIZE})"
            )
        chunks.append(spec)

    return ChunkPlan(
        video_size=video_size,
        chunk_size=eff_chunk_size,
        total_chunk_count=total_chunks,
        chunks=chunks,
    )


def build_init_payload(
    plan: ChunkPlan,
    *,
    caption: str = "",
    draft: bool = False,
    privacy_level: str = DEFAULT_PRIVACY_LEVEL,
) -> dict[str, Any]:
    """Build JSON request body for `/v2/post/publish/video/init/` (Direct Post)
    or `/v2/post/publish/inbox/video/init/` (`--draft`)."""
    source_info = {
        "source": "FILE_UPLOAD",
        "video_size": plan.video_size,
        "chunk_size": plan.chunk_size,
        "total_chunk_count": plan.total_chunk_count,
    }
    if draft:
        return {"source_info": source_info}
    post_info = {
        "title": caption,
        "privacy_level": privacy_level,
        "disable_comment": False,
        "disable_duet": False,
        "disable_stitch": False,
    }
    return {
        "post_info": post_info,
        "source_info": source_info,
    }


def poll_publish_status(
    publish_id: str,
    access_token: str,
    *,
    draft: bool = False,
    poll_interval_s: float = DEFAULT_STATUS_POLL_S,
    timeout_s: float = DEFAULT_STATUS_TIMEOUT_S,
    http_fn: HttpFunc | None = None,
    sleep_fn: Callable[[float], None] | None = None,
    clock_fn: Callable[[], float] | None = None,
) -> dict[str, Any]:
    """Poll `POST /v2/post/publish/status/fetch/` until `PUBLISH_COMPLETE`
    (or `SEND_TO_USER_INBOX` in draft mode) or failure (`FAILED`)."""
    if http_fn is None:
        http_fn = _http_request
    if sleep_fn is None:
        sleep_fn = time.sleep
    if clock_fn is None:
        clock_fn = time.monotonic
    if not publish_id:
        raise ValueError("publish_id is required")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }
    body = json.dumps({"publish_id": publish_id}).encode("utf-8")
    deadline = clock_fn() + max(0.0, float(timeout_s))

    terminal_success = {"PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"} if draft else {"PUBLISH_COMPLETE"}

    while True:
        status_code, _, raw = http_fn("POST", STATUS_FETCH_URL, headers, body)
        payload = _parse_json_response(
            status_code, raw, "status/fetch", extra_secrets=(access_token,)
        )
        data = _check_v2_api_error(
            status_code, payload, "status/fetch", extra_secrets=(access_token,)
        )
        current_status = str(data.get("status") or "").strip()
        if not current_status:
            raise TikTokAPIError("status/fetch response missing 'status' field")

        if current_status in terminal_success:
            return data
        if current_status == "FAILED" or current_status not in IN_PROGRESS_STATUSES:
            if current_status in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX") and not draft:
                if current_status == "PUBLISH_COMPLETE":
                    return data
            return data

        now = clock_fn()
        if now >= deadline:
            raise TimeoutError(
                f"Timed out after {timeout_s}s polling status/fetch for publish_id={publish_id} "
                f"(last status={current_status})"
            )
        sleep_fn(min(poll_interval_s, deadline - now) if poll_interval_s > 0 else 0.0)


def post_video(
    account: str,
    file_path: Path,
    caption: str = "",
    *,
    draft: bool = False,
    privacy_level: str = DEFAULT_PRIVACY_LEVEL,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    poll_interval_s: float = DEFAULT_STATUS_POLL_S,
    poll_timeout_s: float = DEFAULT_STATUS_TIMEOUT_S,
    state_dir: Path | None = None,
    http_fn: HttpFunc | None = None,
    sleep_fn: Callable[[float], None] | None = None,
    clock_fn: Callable[[], float] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Initialize video post, upload chunks via PUT, and poll status/fetch.

    Returns `(publish_id, final_status_data)`.
    """
    if http_fn is None:
        http_fn = _http_request
    validate_account(account)
    video_path = Path(file_path)
    if not video_path.is_file():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    video_size = video_path.stat().st_size
    plan = compute_chunks(video_size, chunk_size=chunk_size)

    tokens = load_tokens(account, state_dir=state_dir)
    access_token = str(tokens.get("access_token") or "").strip()
    refresh_token = str(tokens.get("refresh_token") or "").strip()
    if not access_token:
        raise TikTokConfigError(f"Stored token file for '{account}' has no access_token")

    init_url = INBOX_VIDEO_INIT_URL if draft else DIRECT_POST_INIT_URL
    init_body_dict = build_init_payload(
        plan, caption=caption, draft=draft, privacy_level=privacy_level
    )
    init_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }
    init_body = json.dumps(init_body_dict, ensure_ascii=False).encode("utf-8")

    status_code, _, raw = http_fn("POST", init_url, init_headers, init_body)
    init_payload = _parse_json_response(
        status_code, raw, "video/init", extra_secrets=(access_token, refresh_token)
    )
    init_data = _check_v2_api_error(
        status_code, init_payload, "video/init", extra_secrets=(access_token, refresh_token)
    )

    publish_id = str(init_data.get("publish_id") or "").strip()
    upload_url = str(init_data.get("upload_url") or "").strip()
    if not publish_id or not upload_url:
        raise TikTokAPIError("video/init response missing 'publish_id' or 'upload_url'")

    with open(video_path, "rb") as f:
        for chunk in plan.chunks:
            f.seek(chunk.start)
            data_bytes = f.read(chunk.size)
            if len(data_bytes) != chunk.size:
                raise TikTokError(
                    f"Short read on {video_path.name} chunk {chunk.index}: "
                    f"expected {chunk.size} bytes, got {len(data_bytes)}"
                )
            put_headers = {
                "Content-Type": "video/mp4",
                "Content-Length": str(chunk.size),
                "Content-Range": chunk.content_range,
            }
            put_status, _, put_raw = http_fn("PUT", upload_url, put_headers, data_bytes)
            if put_status < 200 or put_status >= 300:
                raise TikTokAPIError(
                    _redact(
                        f"Chunk {chunk.index + 1}/{plan.total_chunk_count} PUT failed "
                        f"with HTTP {put_status}",
                        (access_token, upload_url),
                    ),
                    status_code=put_status,
                )

    final_data = poll_publish_status(
        publish_id,
        access_token,
        draft=draft,
        poll_interval_s=poll_interval_s,
        timeout_s=poll_timeout_s,
        http_fn=http_fn,
        sleep_fn=sleep_fn,
        clock_fn=clock_fn,
    )
    return publish_id, final_data


# ── CLI commands ─────────────────────────────────────────────────────────────

def cmd_auth_url(args: argparse.Namespace) -> int:
    url, _, _ = build_auth_url(
        account=args.account,
        state=args.state,
        redirect_uri=args.redirect_uri,
        scopes=args.scopes,
        state_dir=args.state_dir,
    )
    print(url)
    return 0


def cmd_callback_file(args: argparse.Namespace) -> int:
    path = callback_state_path(args.state, state_dir=args.state_dir)
    print(path)
    return 0


def cmd_exchange(args: argparse.Namespace) -> int:
    record = exchange_code(
        args.state,
        account=args.account,
        timeout_s=args.timeout,
        poll_interval_s=args.poll_interval,
        state_dir=args.state_dir,
    )
    print(f"account: {record['account']}")
    print(f"open_id: {record['open_id']}")
    print(f"expiry: {record['expiry']}")
    return 0


def cmd_refresh(args: argparse.Namespace) -> int:
    record = refresh_tokens(
        account=args.account,
        state_dir=args.state_dir,
    )
    print(f"account: {record['account']}")
    print(f"open_id: {record['open_id']}")
    print(f"expiry: {record['expiry']}")
    return 0


def cmd_creator_info(args: argparse.Namespace) -> int:
    data = query_creator_info(
        account=args.account,
        state_dir=args.state_dir,
    )
    nickname = data.get("creator_nickname", "")
    privacy_opts = data.get("privacy_level_options", [])
    max_dur = data.get("max_video_post_duration_sec", "")
    if isinstance(privacy_opts, list):
        privacy_str = ",".join(str(x) for x in privacy_opts)
    else:
        privacy_str = str(privacy_opts)
    print(f"creator_nickname: {nickname}")
    print(f"privacy_level_options: {privacy_str}")
    print(f"max_video_post_duration_sec: {max_dur}")
    return 0


def cmd_post(args: argparse.Namespace) -> int:
    publish_id, final_data = post_video(
        account=args.account,
        file_path=args.file,
        caption=args.caption,
        draft=args.draft,
        chunk_size=args.chunk_size,
        poll_interval_s=args.poll_interval,
        poll_timeout_s=args.poll_timeout,
        state_dir=args.state_dir,
    )
    final_status = str(final_data.get("status") or "")
    print(f"publish_id: {publish_id}")
    print(f"status: {final_status}")
    terminal_ok = {"PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"} if args.draft else {"PUBLISH_COMPLETE"}
    return 0 if final_status in terminal_ok else 1


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="TikTok Content Posting API v2 CLI (Login Kit + Direct Post / Draft)"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_auth = sub.add_parser("auth-url", help="Print Login Kit v2 authorize URL and save pending state")
    p_auth.add_argument("--account", default=DEFAULT_ACCOUNT)
    p_auth.add_argument("--state", default=None)
    p_auth.add_argument("--redirect-uri", default=DEFAULT_REDIRECT_URI)
    p_auth.add_argument("--scopes", default=DEFAULT_SCOPES)
    p_auth.add_argument("--state-dir", type=Path, default=None)
    p_auth.set_defaults(func=cmd_auth_url)

    p_cb = sub.add_parser("callback-file", help="Print expected Console callback file path for state")
    p_cb.add_argument("--state", required=True)
    p_cb.add_argument("--state-dir", type=Path, default=None)
    p_cb.set_defaults(func=cmd_callback_file)

    p_ex = sub.add_parser(
        "exchange",
        help="Wait for callback-<state>.json, exchange code for tokens, and delete callback file",
    )
    p_ex.add_argument("--state", required=True)
    p_ex.add_argument("--account", default=None)
    p_ex.add_argument("--timeout", type=float, default=DEFAULT_EXCHANGE_WAIT_S)
    p_ex.add_argument("--poll-interval", type=float, default=DEFAULT_EXCHANGE_POLL_S)
    p_ex.add_argument("--state-dir", type=Path, default=None)
    p_ex.set_defaults(func=cmd_exchange)

    p_ref = sub.add_parser("refresh", help="Refresh access_token and rotated refresh_token")
    p_ref.add_argument("--account", default=DEFAULT_ACCOUNT)
    p_ref.add_argument("--state-dir", type=Path, default=None)
    p_ref.set_defaults(func=cmd_refresh)

    p_ci = sub.add_parser(
        "creator-info",
        help="POST /v2/post/publish/creator_info/query/ and print nickname, privacy options, max duration",
    )
    p_ci.add_argument("--account", default=DEFAULT_ACCOUNT)
    p_ci.add_argument("--state-dir", type=Path, default=None)
    p_ci.set_defaults(func=cmd_creator_info)

    p_post = sub.add_parser(
        "post",
        help="Upload and post video via Direct Post (/v2/post/publish/video/init/) or --draft (/v2/post/publish/inbox/video/init/)",
    )
    p_post.add_argument("--account", default=DEFAULT_ACCOUNT)
    p_post.add_argument("--file", type=Path, required=True)
    p_post.add_argument("--caption", default="")
    p_post.add_argument("--draft", action="store_true")
    p_post.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    p_post.add_argument("--poll-interval", type=float, default=DEFAULT_STATUS_POLL_S)
    p_post.add_argument("--poll-timeout", type=float, default=DEFAULT_STATUS_TIMEOUT_S)
    p_post.add_argument("--state-dir", type=Path, default=None)
    p_post.set_defaults(func=cmd_post)

    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(_redact(f"ERROR: {exc}"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
