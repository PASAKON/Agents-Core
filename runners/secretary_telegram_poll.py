"""Mac-side Telegram ingress for SomPong — long polling, no public URL.

Why this exists
---------------
SomPong normally reaches the CEO through a webhook: Telegram POSTs to
https://webhook.mooniex.com/telegram/@sompong, which is claudeflow's Express
route on the Contabo box, which talks to secretary_server on that same box,
which queues anything Mac-bound for runners/mac_agent to drain over SSH.

Every hop in that chain is the Contabo box. On 2026-08-16 it went offline
around 16:05 local and took the whole chain with it — SomPong AND
terminal.mooniex.com (a Tailscale name for the same host), so the CEO lost the
secretary and every means of asking what had happened to it, in the same
instant, while away from the Mac. Telegram held the updates (7 queued, webhook
error "Connection timed out") but nothing was there to collect them.

This module takes the box out of the path. Telegram offers long polling as an
alternative to webhooks, so the Mac can *pull* updates over an outbound
connection and never needs an inbound address of its own. That also puts
SomPong where the org state already lives: tasks.db, the tmux sessions and the
worktrees are Mac-local, which is why the Contabo deployment had to SSH back
here to do anything useful in the first place.

Trade-off, stated plainly: a webhook and getUpdates are mutually exclusive.
Starting this deletes the webhook — WITHOUT drop_pending_updates, so messages
queued during the outage are delivered here rather than discarded. Restoring
the Contabo path later means calling setWebhook again.

lib/telegram_out.send_to_ceo is deliberately not reused: it speaks for a
different bot (TELEGRAM_BOT_TOKEN, @MoonieXBot — SomPong is
SECRETARY_BOT_TOKEN), it truncates at 4096 where a secretary reply needs
chunking, and this module needs getUpdates/getFile/sendChatAction, which it
does not have.

Scope: text in, text out, voice in (Deepgram, same model and Thai spacing fix
as the Node path). Voice *out* is deliberately absent — it needs the fal TTS
client that lives in claudeflow. This is the path that has to work during an
outage, not the path that has to be complete.

Run:  python -m runners.secretary_telegram_poll
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.logger import get_logger  # noqa: E402

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
CLAUDEFLOW_ENV = Path(
    os.environ.get("CLAUDEFLOW_ENV", "/Users/gob/Projects/mooniex-claudeflow/.env")
)
OFFSET_FILE = ROOT / "state" / "secretary-telegram-offset.json"

SECRETARY_URL = os.environ.get(
    "SECRETARY_URL", "http://127.0.0.1:8643/v1/chat/completions"
)
# secretary_server's own turn budget is 180s; allow for that plus the quota
# check in front of it before giving up on our side.
SECRETARY_TIMEOUT = int(os.environ.get("SECRETARY_POLL_TIMEOUT", "300"))

# Telegram refuses a message over 4096 characters. Chunk below that, so a
# chunk marker can never be what pushes a message past the limit.
TG_CHUNK = 3900
LONG_POLL_SECONDS = 30

DEEPGRAM_URL = (
    "https://api.deepgram.com/v1/listen"
    "?model=nova-3&language=th&smart_format=true&punctuate=true"
)

_log = get_logger("secretary-telegram")

# Deepgram tokenises Thai a syllable at a time — "ส ่ง" splits a single
# character from its tone mark. Join a space only when Thai sits on BOTH
# sides, so spacing around Latin words, session ids and shas survives.
_THAI_GAP = re.compile(r"(?<=[฀-๿]) +(?=[฀-๿])")


def normalize_thai_spacing(text: str) -> str:
    if not text:
        return text
    return _THAI_GAP.sub("", text)


# --------------------------------------------------------------------------
# Env
# --------------------------------------------------------------------------
def _dotenv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
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


_FILE_ENV = _dotenv(CLAUDEFLOW_ENV)


def env(name: str, default: str = "") -> str:
    """Process env wins, then claudeflow's .env, then the default."""
    return os.environ.get(name) or _FILE_ENV.get(name) or default


BOT_TOKEN = env("SECRETARY_BOT_TOKEN")
ADMIN_CHAT_ID = env("SECRETARY_ADMIN_CHAT_ID")
DEEPGRAM_KEY = env("DEEPGRAM_API_KEY")


def allowed_senders() -> set[str]:
    """Who may talk to SomPong.

    The Node path warns and then accepts everyone when the allowlist is unset.
    That is the wrong default here: this process runs on the CEO's Mac and its
    tools can drive live tmux sessions, so an empty allowlist closes down to
    the admin chat rather than opening up to everyone. The bot's username is
    public — anyone can message it.
    """
    raw = env("TELEGRAM_ALLOWED_USERS")
    ids = {part.strip() for part in raw.split(",") if part.strip()}
    if ADMIN_CHAT_ID:
        ids.add(str(ADMIN_CHAT_ID).strip())
    return ids


# --------------------------------------------------------------------------
# Telegram
# --------------------------------------------------------------------------
def tg(method: str, http_timeout: int = 45, **params) -> dict:
    """One Bot API call. `http_timeout` is ours; any `timeout` in params is
    Telegram's own long-poll parameter and is passed through untouched."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    data = json.dumps(params).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=http_timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def send_reply(chat_id: str, text: str) -> None:
    """Send a reply, split across messages if Telegram would refuse it whole.

    Send failures are logged and swallowed per chunk. Losing one chunk is bad;
    dying mid-send and leaving the CEO with silence is the exact failure this
    module exists to end.
    """
    text = text or "(ไม่มีข้อความตอบกลับ)"
    chunks = [text[i:i + TG_CHUNK] for i in range(0, len(text), TG_CHUNK)] or [text]
    for index, chunk in enumerate(chunks):
        prefix = f"({index + 1}/{len(chunks)})\n" if len(chunks) > 1 else ""
        try:
            result = tg("sendMessage", chat_id=chat_id, text=prefix + chunk)
            if not result.get("ok"):
                _log.error("sendMessage refused: %s", result.get("description"))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            _log.error("sendMessage failed: %s", exc)


class Typing:
    """Keep the 'typing…' indicator alive while a turn runs.

    A secretary turn can take minutes. Telegram clears the indicator after
    about five seconds, so without this the CEO sees nothing at all and
    reasonably concludes SomPong is down again.
    """

    def __init__(self, chat_id: str) -> None:
        self.chat_id = chat_id
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while True:
            try:
                tg("sendChatAction", http_timeout=15,
                   chat_id=self.chat_id, action="typing")
            except (urllib.error.URLError, TimeoutError, OSError):
                pass  # cosmetic only — never let it break the actual reply
            if self._stop.wait(4):
                return

    def __enter__(self) -> "Typing":
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()


def download_voice(file_id: str) -> bytes:
    meta = tg("getFile", file_id=file_id)
    if not meta.get("ok"):
        raise RuntimeError(f"getFile refused: {meta.get('description')}")
    path = meta["result"]["file_path"]
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{path}"
    with urllib.request.urlopen(url, timeout=60) as resp:
        return resp.read()


def transcribe(audio: bytes, mime: str) -> str:
    if not DEEPGRAM_KEY:
        raise RuntimeError("DEEPGRAM_API_KEY is not set")
    req = urllib.request.Request(
        DEEPGRAM_URL,
        data=audio,
        headers={"Authorization": f"Token {DEEPGRAM_KEY}", "Content-Type": mime},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    raw = (
        data.get("results", {})
        .get("channels", [{}])[0]
        .get("alternatives", [{}])[0]
        .get("transcript", "")
    )
    return normalize_thai_spacing(raw)


# --------------------------------------------------------------------------
# Secretary
# --------------------------------------------------------------------------
def ask_secretary(prompt: str, conversation_id: str) -> str:
    body = json.dumps(
        {
            "model": "secretary",
            "messages": [{"role": "user", "content": prompt}],
            "user": conversation_id,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        SECRETARY_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('SECRETARY_API_KEY', '')}",
        },
    )
    with urllib.request.urlopen(req, timeout=SECRETARY_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


# --------------------------------------------------------------------------
# Update handling
# --------------------------------------------------------------------------
def handle_update(update: dict) -> None:
    message = update.get("message") or update.get("edited_message")
    if not message:
        # Log what it was. A silent skip here is indistinguishable from the
        # outage it replaced, and Telegram sends plenty of non-message update
        # types (my_chat_member, reactions) that legitimately land here.
        _log.info("update %s ignored: no message (keys=%s)",
                  update.get("update_id"), sorted(k for k in update if k != "update_id"))
        return

    chat_id = str((message.get("chat") or {}).get("id", ""))
    sender_id = str((message.get("from") or {}).get("id", chat_id))
    allowed = allowed_senders()
    if not allowed:
        # Fail closed. An empty allowlist means the config did not load, not
        # that everyone is welcome — this process can drive the CEO's tmux
        # sessions and the bot's username is public.
        _log.error("allowlist is empty — refusing every sender until it is set")
        return
    if sender_id not in allowed and chat_id not in allowed:
        _log.warning("ignoring message from unlisted sender %s", sender_id)
        return

    voice = message.get("voice") or message.get("audio")
    text = message.get("text") or message.get("caption") or ""

    if voice:
        try:
            audio = download_voice(voice["file_id"])
            text = transcribe(audio, voice.get("mime_type") or "audio/ogg")
        except Exception as exc:  # network, Deepgram, malformed payload
            _log.exception("voice transcription failed")
            send_reply(chat_id, f"ถอดเสียงไม่สำเร็จ: {exc}\nพิมพ์มาแทนได้เลย")
            return
        if not text.strip():
            send_reply(chat_id, "ถอดเสียงได้ว่าง ๆ ลองพูดใหม่หรือพิมพ์มาได้เลย")
            return
        # Echo the transcript: when it mishears, the CEO can see that is what
        # happened instead of wondering why the answer is unrelated.
        send_reply(chat_id, f"🎤 ได้ยินว่า: {text}")

    if not text.strip():
        return

    _log.info("turn from %s (%d chars)", sender_id, len(text))
    try:
        with Typing(chat_id):
            reply = ask_secretary(text, conversation_id=f"telegram-{chat_id}")
    except urllib.error.URLError as exc:
        # By far the most likely cause is secretary_server not running, and
        # naming it is the difference between the CEO knowing what to restart
        # and being told "error".
        _log.exception("secretary unreachable")
        send_reply(chat_id,
                   f"ต่อ secretary ไม่ได้ ({exc.reason}) — "
                   f"ตัวสมองยังไม่ขึ้นที่ {SECRETARY_URL}")
        return
    except Exception as exc:
        _log.exception("secretary turn failed")
        send_reply(chat_id, f"ตอบไม่สำเร็จ: {exc}")
        return

    send_reply(chat_id, reply)


# --------------------------------------------------------------------------
# Offset
# --------------------------------------------------------------------------
def load_offset() -> int:
    try:
        return int(json.loads(OFFSET_FILE.read_text(encoding="utf-8"))["offset"])
    except (OSError, ValueError, KeyError, TypeError):
        return 0


def save_offset(offset: int) -> None:
    OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = OFFSET_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"offset": offset}), encoding="utf-8")
    os.replace(tmp, OFFSET_FILE)  # atomic: a crash mid-write must not lose it


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main() -> None:
    if not BOT_TOKEN:
        sys.exit(f"SECRETARY_BOT_TOKEN is not set (looked in env and {CLAUDEFLOW_ENV})")
    if not os.environ.get("SECRETARY_API_KEY"):
        sys.exit("SECRETARY_API_KEY is not set — it must match the key "
                 "secretary_server was started with")

    me = tg("getMe")
    if not me.get("ok"):
        sys.exit(f"getMe failed: {me.get('description')}")
    _log.info("polling as @%s", me["result"]["username"])

    # Take the update stream off the webhook. No drop_pending_updates: what
    # queued up while Contabo was down is exactly what we want delivered.
    handover = tg("deleteWebhook")
    _log.info("deleteWebhook ok=%s — updates now arrive by polling",
              handover.get("ok"))

    offset = load_offset()
    _log.info("resuming from offset %s", offset)

    while True:
        try:
            resp = tg("getUpdates", http_timeout=LONG_POLL_SECONDS + 15,
                      offset=offset, timeout=LONG_POLL_SECONDS)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            _log.warning("getUpdates failed (%s) — retrying in 5s", exc)
            time.sleep(5)
            continue

        if not resp.get("ok"):
            _log.error("getUpdates refused: %s", resp.get("description"))
            time.sleep(5)
            continue

        for update in resp.get("result", []):
            offset = max(offset, int(update["update_id"]) + 1)
            # Persist BEFORE handling. A turn that crashes the process must not
            # be replayed on restart: re-running a relayed order is worse than
            # dropping it, because the CEO can always re-ask.
            save_offset(offset)
            try:
                handle_update(update)
            except Exception:
                _log.exception("update %s failed", update.get("update_id"))


if __name__ == "__main__":
    main()
