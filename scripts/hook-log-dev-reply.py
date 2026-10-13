#!/usr/bin/env python3
"""Stop hook: append last DEV assistant reply to state/logs/cto.log AND
persist session-id + rate-limit signal back to the tasks DB so the
auto-resume scheduler can recover the work later.

Mirrors hook-log-reply.py but for DEV sessions. Gated by WORKER_TASK_ID env
(set by runners/worker_init.py before exec). Writes:

    [<ts>] Dev:<task_id>: <reply text>

…and on top of that:

    * tasks.session_id      ← transcript filename stem (resume handle)
    * tasks.last_checkpoint ← ISO 8601 UTC of this hook fire
    * tasks.status          ← 'rate_limited' if any record looks like a
                              429 / rate_limit_error
    * tasks.retry_after_ts  ← now + 5min (default backoff) when RL flagged

CTO's UserPromptSubmit hook tails cto.log and surfaces new lines into
the next CTO turn, so DEV replies appear in the CTO chat automatically.

Envelope mode (`ORG_MAIL_ENVELOPE=1`, default off; org restructure P1):
  * ROOT comes from this file's own location, as hook-log-prompt.py does.
    The legacy literal is the Mac checkout: on any other host it names a tree
    with no lib/ or tools/, so the DB write and the relay failed silently and
    the log lines landed in a stray /Users/gob tree (measured 2026-10-13 on
    Contabo: tasks.session_id NULL on five tasks).
  * tasks.session_id / last_checkpoint / rate-limit state are still written
    on every turn, with the hub call capped at HUB_TIMEOUT_S.
  * The log line and the relay to the owning C-level happen only on a turn
    that called submit_report, dev_message or a blocker tool (or hit a rate
    limit). Every other turn stays in the worker's own transcript.
Off, everything is exactly as before.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _envelope_on() -> bool:
    return os.environ.get("ORG_MAIL_ENVELOPE", "").strip().lower() in ("1", "true", "yes", "on")


ENVELOPE = _envelope_on()
LEGACY_ROOT = Path("/Users/gob/MoonieXHQ/Agents/Core")
ROOT = Path(__file__).resolve().parent.parent if ENVELOPE else LEGACY_ROOT
LOG = ROOT / "state" / "logs" / "cto.log"
HUB_TIMEOUT_S = 3.0

# worker MCP tools (runners/worker_mcp_server.py) whose turn is worth a relay
EVENT_TOOLS = {
    "submit_report": "report",
    "dev_message": "message",
    "file_blocker_issue": "blocker",
    "request_human_handoff": "blocker",
}


def _log_for(cto_id: str | None) -> Path:
    """Per-CTO log path when the spawning CTO is known, else the global log."""
    if cto_id:
        return ROOT / "state" / "logs" / f"cto-{cto_id}.log"
    return ROOT / "state" / "logs" / "cto.log"
MAX_CHARS = 4000
RELAY_MAX_CHARS = 1500
DEFAULT_BACKOFF_S = 300

RATE_LIMIT_RE = re.compile(
    r"(rate[_-]?limit|rate limited|429|too many requests|usage limit|"
    r"quota exceeded)",
    re.IGNORECASE,
)


def extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                t = block.get("text") or ""
                if t:
                    parts.append(t)
        return "\n".join(parts)
    return ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _session_id_from_path(p: Path) -> str:
    return p.stem


def _is_tool_result(content) -> bool:
    return isinstance(content, list) and any(
        isinstance(b, dict) and b.get("type") == "tool_result" for b in content)


def _scan_records(transcript: Path) -> tuple[str, bool, list[str]]:
    """Return (last_assistant_text, rate_limited_seen, turn_events): the last
    is the EVENT_TOOLS names the current turn (since the last prompt) called.

    Envelope mode reads rate_limited from the current turn's API error records
    only. The legacy scan also matches any assistant prose that mentions "429"
    or "rate limit" anywhere in the transcript, which then sets the task to
    rate_limited on every later turn, a submitted report included."""
    last_text = ""
    rl = False
    turn_rl = False
    events: list[str] = []
    turn_pid = None
    try:
        with transcript.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue

                if rec.get("type") == "user" and not rec.get("isCompactSummary"):
                    pid = rec.get("promptId")
                    if pid:
                        if pid != turn_pid:
                            turn_pid, events, turn_rl = pid, [], False
                    elif not rec.get("isMeta") and not _is_tool_result(
                            (rec.get("message") or {}).get("content")):
                        events, turn_rl = [], False   # no promptId: a typed prompt opens a turn

                if rec.get("type") == "assistant":
                    msg = rec.get("message") or {}
                    content = msg.get("content")
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "tool_use":
                                name = str(block.get("name") or "").rsplit("__", 1)[-1]
                                if name in EVENT_TOOLS and name not in events:
                                    events.append(name)
                    text = extract_text(content)
                    if text.strip():
                        last_text = text
                        if RATE_LIMIT_RE.search(text):
                            rl = True

                if rec.get("isApiErrorMessage") or rec.get("type") == "error":
                    blob = json.dumps(rec)
                    if RATE_LIMIT_RE.search(blob):
                        rl = True
                        turn_rl = True
    except Exception:
        pass
    return last_text, (turn_rl if ENVELOPE else rl), events


def _persist(task_id: str, session_id: str, rate_limited: bool) -> None:
    now = _now_iso()
    try:
        sys.path.insert(0, str(ROOT))
        from lib import db as db_lib
        # envelope mode caps the hub call: a slow hub must not hold the worker's turn
        with (db_lib.get_conn(timeout=HUB_TIMEOUT_S) if ENVELOPE else db_lib.get_conn()) as conn:
            conn.execute(
                "UPDATE tasks SET session_id=?, last_checkpoint=?, updated_at=? "
                "WHERE id=?",
                (session_id, now, now, task_id),
            )
            if rate_limited:
                retry_after = (
                    datetime.now(timezone.utc)
                    + timedelta(seconds=DEFAULT_BACKOFF_S)
                ).isoformat(timespec="seconds")
                conn.execute(
                    "UPDATE tasks SET status='rate_limited', retry_after_ts=?, "
                    "updated_at=? WHERE id=?",
                    (retry_after, now, task_id),
                )
    except Exception:
        pass


def _role_label(role: str | None) -> str:
    """Resolve DEV role key → display label. Lazy import keeps the hook
    fast and tolerant when sys.path isn't pre-set."""
    if not role:
        return "Dev"
    try:
        sys.path.insert(0, str(ROOT))
        from lib.config import display_for
        return display_for(role)
    except Exception:
        return role


def main() -> int:
    task_id = os.environ.get("WORKER_TASK_ID")
    if not task_id:
        return 0
    role = os.environ.get("WORKER_ROLE")
    cto_id = os.environ.get("WORKER_CTO_ID")
    owner_role = os.environ.get("WORKER_CTO_ROLE", "cto")
    role_label = _role_label(role)
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    tp = payload.get("transcript_path")
    if not tp:
        return 0
    p = Path(tp)
    if not p.exists():
        return 0

    last_text, rate_limited, events = _scan_records(p)
    session_id = _session_id_from_path(p)
    _persist(task_id, session_id, rate_limited)

    last_text = (last_text or "").strip()
    if ENVELOPE:
        if not events and not rate_limited:
            return 0          # nothing to report: the turn stays in the worker's transcript
        if events:
            last_text = f"[{', '.join(events)}] " + (last_text or "(no closing text; see the task report)")
    if not last_text and not rate_limited:
        return 0
    if len(last_text) > MAX_CHARS:
        last_text = last_text[:MAX_CHARS] + " ...[truncated]"

    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    # Dual-write: global cto.log (legacy consumers) + the spawning CTO's
    # per-session log so multi-CTO setups don't cross feeds.
    targets = [_log_for(None)]
    per = _log_for(cto_id)
    if per != targets[0]:
        targets.append(per)
    for target in targets:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("a", encoding="utf-8") as f:
                if last_text:
                    f.write(f"[{ts}] {role_label} {task_id}: {last_text}\n")
                if rate_limited:
                    f.write(
                        f"[{ts}] RateLimit {role_label} {task_id}: status=rate_limited, "
                        f"retry_after={DEFAULT_BACKOFF_S}s, session={session_id}\n"
                    )
        except OSError:
            pass

    # Bidirectional visible chat: type the DEV's reply into the CTO tab
    # so the CEO can watch the conversation in real time.
    relay = last_text
    if rate_limited:
        rl_note = (
            f"(rate-limited; will auto-resume in ~{DEFAULT_BACKOFF_S}s)"
        )
        relay = f"{relay}\n{rl_note}" if relay else rl_note
    if relay:
        if len(relay) > RELAY_MAX_CHARS:
            relay = relay[:RELAY_MAX_CHARS] + " ...[truncated]"
        try:
            sys.path.insert(0, str(ROOT))
            from tools.send_to_cto import send as send_to_cto
            send_to_cto(task_id, relay, role=role, cto_id=cto_id,
                        owner_role=owner_role)
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
