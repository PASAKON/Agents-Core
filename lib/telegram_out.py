"""lib/telegram_out.py -- the one place that knows how to reach the CEO over
Telegram (task-67ba0c4f D1, task-ed9e5b9a D1-D4).

Public surface:
  send_to_ceo(text) -> {"ok": bool, "reason": str|None}
  send_media_to_ceo(path, caption="") -> {"ok": bool, "reason": str|None}

Rules that matter more than the happy path:

- Missing `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CEO_CHAT_ID` is an explicit
  failure, never a silent no-op -- a notification system that quietly does
  nothing is worse than one that is obviously broken.
- Success means Telegram's own JSON body said `"ok": true` -- not that the
  HTTP request merely went out. A 2xx with `"ok": false` (bad chat id, bot
  blocked, etc.) is still a failure.
- send_media_to_ceo always uploads real bytes (multipart `files={...}`),
  never a URL -- the CEO explicitly rejected links reaching him as a
  substitute for the actual file (order #38).
- send_media_to_ceo verifies the token actually belongs to @SSomPongBot
  before sending. A wrong bot token still returns `"ok": true` from
  Telegram -- the send just lands in a chat nobody is watching. That exact
  silent failure happened in this org on 2026-08-16, which is why this
  check is mandatory rather than best-effort.
- Telegram hard-caps uploads at 50 MB. Over that, send_media_to_ceo refuses
  and names the actual size -- it never falls back to sending a link, since
  that would be quietly delivering the exact thing the CEO said he doesn't
  want.

The token never appears in a returned string, logged, or raised: it lives in
the request URL (`/bot<token>/sendMessage`), and `requests`' own exception
text can embed that URL verbatim on a connection failure -- so every error
string this module produces is redacted before it leaves the function.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import requests

TELEGRAM_API_BASE = "https://api.telegram.org"

# Telegram rejects a sendMessage text over this many characters outright
# rather than truncating it itself -- silently dropping the whole message
# is worse than a visibly-cut one, so this module truncates first.
MAX_MESSAGE_CHARS = 4096
TRUNCATION_MARKER = "\n\n... [truncated]"

# Media captions have a separate, much smaller cap than sendMessage text.
MEDIA_CAPTION_MAX_CHARS = 1024

REQUEST_TIMEOUT_SECONDS = 15
# Uploads carry a real file body -- give them more room than a plain
# sendMessage call before giving up.
MEDIA_REQUEST_TIMEOUT_SECONDS = 60

# Telegram Bot API hard cap (documented, not configurable per-bot).
MAX_MEDIA_BYTES = 50 * 1024 * 1024

# The only bot this module is allowed to speak through. Sending with any
# other token is a silent failure, not a different-but-valid delivery path
# (2026-08-16 incident) -- see _verify_bot_identity.
EXPECTED_BOT_USERNAME = "SSomPongBot"

# Mac-side fallback location for SomPong's own token/chat id (task-ed9e5b9a
# D2) -- on the Mac, TELEGRAM_BOT_TOKEN/TELEGRAM_CEO_CHAT_ID are never set,
# only claudeflow's SECRETARY_* vars are. On Contabo the secretary service
# sets TELEGRAM_BOT_TOKEN/TELEGRAM_CEO_CHAT_ID directly, so this fallback
# read never triggers there. Overridable so tests never touch the real file.
CLAUDEFLOW_ENV_DEFAULT = "/Users/gob/Projects/mooniex-claudeflow/.env"

FFPROBE_BIN = os.environ.get("FFPROBE_BIN", "ffprobe")


def _truncate(text: str, max_chars: int = MAX_MESSAGE_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    cut = max_chars - len(TRUNCATION_MARKER)
    return text[:cut] + TRUNCATION_MARKER


def _redact(text: str, token: str) -> str:
    """Strip the bot token out of any string before it can leave this
    module. `requests`' own ConnectionError/Timeout messages embed the full
    request URL -- token included -- so this is not a defensive no-op."""
    if not text or not token:
        return text
    return text.replace(token, "<redacted>")


def send_to_ceo(text: str) -> dict:
    """POST `text` to the CEO's Telegram chat. Returns
    {"ok": bool, "reason": str|None} -- `reason` is None only when `ok` is
    True. Never raises."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return {"ok": False, "reason": "TELEGRAM_BOT_TOKEN is not set"}

    chat_id = os.environ.get("TELEGRAM_CEO_CHAT_ID")
    if not chat_id:
        return {"ok": False, "reason": "TELEGRAM_CEO_CHAT_ID is not set"}

    body = _truncate(text)

    try:
        r = requests.post(
            f"{TELEGRAM_API_BASE}/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": body},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        return {"ok": False, "reason": _redact(f"network error: {e}", token)}

    try:
        data = r.json()
    except ValueError:
        return {
            "ok": False,
            "reason": _redact(f"non-JSON response (HTTP {r.status_code})", token),
        }

    # Success means Telegram's own body said ok -- a non-2xx status or a
    # 2xx with "ok": false are both failures, never conflated with "sent".
    if not r.ok or not isinstance(data, dict) or not data.get("ok"):
        reason = (isinstance(data, dict) and data.get("description")) or f"HTTP {r.status_code}"
        return {"ok": False, "reason": _redact(str(reason), token)}

    return {"ok": True, "reason": None}


# ---------------------------------------------------------------------------
# Dual-machine token/chat-id resolution (task-ed9e5b9a D2)
# ---------------------------------------------------------------------------

def _dotenv(path: Path) -> dict:
    """Tiny KEY=value parser for a gitignored .env -- same shape as the one
    runners/secretary_telegram_poll.py already uses for this exact file, so
    both readers treat it identically. Returns {} if the file is absent."""
    out: dict = {}
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip().strip("'\"")
    return out


def _claudeflow_env() -> dict:
    path = Path(os.environ.get("CLAUDEFLOW_ENV", CLAUDEFLOW_ENV_DEFAULT))
    return _dotenv(path)


def _resolve_env(primary_var: str, fallback_var: str) -> str | None:
    """Process env wins; falls back to claudeflow's .env key for the Mac,
    where this org's own TELEGRAM_* vars are never set. Read fresh on every
    call (the file is tiny) so tests can point CLAUDEFLOW_ENV at a fixture
    or a nonexistent path without any module-load-time caching to fight."""
    return os.environ.get(primary_var) or _claudeflow_env().get(fallback_var)


# ---------------------------------------------------------------------------
# Bot identity verification (task-ed9e5b9a D3)
# ---------------------------------------------------------------------------

# Keyed by token so a process that (in tests) sees more than one token never
# reuses a stale verdict from a different bot. Cleared only by process exit --
# "cache per-process, one getMe call not one per send" is the actual ask.
_bot_identity_cache: dict = {}


def _verify_bot_identity(token: str) -> tuple:
    """(ok, reason). Confirms `token` actually belongs to @SSomPongBot before
    any send is attempted. Sending with a different bot's token still comes
    back `"ok": true` from Telegram -- the message just never reaches the
    CEO, a silent failure this org already hit on 2026-08-16. Cached per
    token so this costs one getMe call per process, not one per send."""
    if token in _bot_identity_cache:
        return _bot_identity_cache[token]

    try:
        r = requests.get(
            f"{TELEGRAM_API_BASE}/bot{token}/getMe",
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        result = (False, _redact(f"getMe network error: {e}", token))
        _bot_identity_cache[token] = result
        return result

    try:
        data = r.json()
    except ValueError:
        result = (False, _redact(f"getMe non-JSON response (HTTP {r.status_code})", token))
        _bot_identity_cache[token] = result
        return result

    if not r.ok or not isinstance(data, dict) or not data.get("ok"):
        reason = (isinstance(data, dict) and data.get("description")) or f"HTTP {r.status_code}"
        result = (False, _redact(f"getMe failed: {reason}", token))
        _bot_identity_cache[token] = result
        return result

    username = (data.get("result") or {}).get("username")
    if username != EXPECTED_BOT_USERNAME:
        result = (
            False,
            f"wrong bot: getMe returned username '{username}', expected "
            f"'{EXPECTED_BOT_USERNAME}' -- refusing to send",
        )
    else:
        result = (True, None)
    _bot_identity_cache[token] = result
    return result


# ---------------------------------------------------------------------------
# Media type probing -- the endpoint is chosen by what the file actually is,
# never by its extension (task-ed9e5b9a D1). ffprobe first; a small
# magic-bytes sniff covers the common cases when ffprobe isn't installed, so
# this module has no hard runtime dependency on it.
# ---------------------------------------------------------------------------

_IMAGE_FORMAT_TOKENS = {
    "image2", "png_pipe", "jpeg_pipe", "mjpeg", "webp_pipe",
    "bmp_pipe", "tiff_pipe", "gif",
}
_VIDEO_FORMAT_TOKENS = (
    "mp4", "mov", "matroska", "webm", "avi", "mpegts", "flv", "ogg", "3gp",
)


def _probe_via_ffprobe(path: Path) -> str | None:
    """'photo' / 'video' / 'document', or None meaning "could not tell" --
    ffprobe missing, unusable, or unable to parse the file at all. None is
    a signal to fall back to magic bytes, not an error: a .mp4 that will
    not decode is not a video either way."""
    if shutil.which(FFPROBE_BIN) is None:
        return None
    try:
        proc = subprocess.run(
            [FFPROBE_BIN, "-v", "error",
             "-show_entries", "stream=codec_type",
             "-show_entries", "format=format_name",
             "-of", "default=nw=1", str(path)],
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None

    format_name = ""
    codec_types = []
    for line in proc.stdout.splitlines():
        key, _, value = line.partition("=")
        if key == "format_name":
            format_name = value
        elif key == "codec_type":
            codec_types.append(value)

    format_tokens = set(format_name.split(","))
    if format_tokens & _IMAGE_FORMAT_TOKENS:
        return "photo"
    if any(t in format_name for t in _VIDEO_FORMAT_TOKENS) and "video" in codec_types:
        return "video"
    # ffprobe parsed it fine but it's neither -- a real verdict, not a miss.
    return "document"


def _probe_via_magic_bytes(path: Path) -> str:
    try:
        with open(path, "rb") as f:
            head = f.read(16)
    except OSError:
        return "document"
    if head.startswith(b"\xff\xd8\xff") or head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "photo"
    if len(head) >= 12 and head[0:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "photo"
    if len(head) >= 8 and head[4:8] == b"ftyp":
        return "video"
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return "video"
    if len(head) >= 12 and head[0:4] == b"RIFF" and head[8:12] == b"AVI ":
        return "video"
    return "document"


def _probe_media_kind(path: Path) -> str:
    """'photo', 'video', or 'document' -- decided by the file's real
    content, never its extension."""
    kind = _probe_via_ffprobe(path)
    if kind is not None:
        return kind
    return _probe_via_magic_bytes(path)


_MEDIA_ENDPOINT_BY_KIND = {
    "photo": ("sendPhoto", "photo"),
    "video": ("sendVideo", "video"),
}


def send_media_to_ceo(path: str, caption: str = "") -> dict:
    """Upload the file at `path` to the CEO's Telegram chat as a real
    multipart file (never a URL). Picks sendPhoto/sendVideo/sendDocument by
    probing the file's actual content, verifies the bot is @SSomPongBot
    before sending, and refuses files over Telegram's 50 MB cap outright --
    no link fallback. Returns the same {"ok": bool, "reason": str|None}
    shape as send_to_ceo. Never raises."""
    token = _resolve_env("TELEGRAM_BOT_TOKEN", "SECRETARY_BOT_TOKEN")
    if not token:
        return {
            "ok": False,
            "reason": "no bot token: set TELEGRAM_BOT_TOKEN, or claudeflow's "
                       "SECRETARY_BOT_TOKEN",
        }

    chat_id = _resolve_env("TELEGRAM_CEO_CHAT_ID", "SECRETARY_ADMIN_CHAT_ID")
    if not chat_id:
        return {
            "ok": False,
            "reason": "no chat id: set TELEGRAM_CEO_CHAT_ID, or claudeflow's "
                       "SECRETARY_ADMIN_CHAT_ID",
        }

    file_path = Path(path)
    if not file_path.is_file():
        return {"ok": False, "reason": f"not an existing regular file: {path}"}

    try:
        size = file_path.stat().st_size
    except OSError as e:
        return {"ok": False, "reason": f"cannot stat file: {e}"}

    if size > MAX_MEDIA_BYTES:
        return {
            "ok": False,
            "reason": (
                f"file too large for Telegram: {size} bytes exceeds the "
                f"{MAX_MEDIA_BYTES}-byte (50 MB) cap -- refusing rather than "
                f"falling back to a link"
            ),
        }

    identity_ok, identity_reason = _verify_bot_identity(token)
    if not identity_ok:
        return {"ok": False, "reason": identity_reason}

    kind = _probe_media_kind(file_path)
    endpoint, field = _MEDIA_ENDPOINT_BY_KIND.get(kind, ("sendDocument", "document"))

    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = _truncate(caption, MEDIA_CAPTION_MAX_CHARS)

    try:
        with open(file_path, "rb") as f:
            r = requests.post(
                f"{TELEGRAM_API_BASE}/bot{token}/{endpoint}",
                data=data,
                files={field: (file_path.name, f)},
                timeout=MEDIA_REQUEST_TIMEOUT_SECONDS,
            )
    except OSError as e:
        return {"ok": False, "reason": _redact(f"could not read file: {e}", token)}
    except requests.RequestException as e:
        return {"ok": False, "reason": _redact(f"network error: {e}", token)}

    try:
        resp_data = r.json()
    except ValueError:
        return {
            "ok": False,
            "reason": _redact(f"non-JSON response (HTTP {r.status_code})", token),
        }

    if not r.ok or not isinstance(resp_data, dict) or not resp_data.get("ok"):
        reason = (isinstance(resp_data, dict) and resp_data.get("description")) or f"HTTP {r.status_code}"
        return {"ok": False, "reason": _redact(str(reason), token)}

    return {"ok": True, "reason": None}
