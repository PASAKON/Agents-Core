"""lib/telegram_out.py -- the one place that knows how to reach the CEO over
Telegram (task-67ba0c4f D1).

Public surface: `send_to_ceo(text) -> {"ok": bool, "reason": str|None}`.

Two rules that matter more than the happy path:

- Missing `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CEO_CHAT_ID` is an explicit
  failure, never a silent no-op -- a notification system that quietly does
  nothing is worse than one that is obviously broken.
- Success means Telegram's own JSON body said `"ok": true` -- not that the
  HTTP request merely went out. A 2xx with `"ok": false` (bad chat id, bot
  blocked, etc.) is still a failure.

The token never appears in a returned string, logged, or raised: it lives in
the request URL (`/bot<token>/sendMessage`), and `requests`' own exception
text can embed that URL verbatim on a connection failure -- so every error
string this module produces is redacted before it leaves the function.
"""
from __future__ import annotations

import os

import requests

TELEGRAM_API_BASE = "https://api.telegram.org"

# Telegram rejects a sendMessage text over this many characters outright
# rather than truncating it itself -- silently dropping the whole message
# is worse than a visibly-cut one, so this module truncates first.
MAX_MESSAGE_CHARS = 4096
TRUNCATION_MARKER = "\n\n... [truncated]"

REQUEST_TIMEOUT_SECONDS = 15


def _truncate(text: str) -> str:
    if len(text) <= MAX_MESSAGE_CHARS:
        return text
    cut = MAX_MESSAGE_CHARS - len(TRUNCATION_MARKER)
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
