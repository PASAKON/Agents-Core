#!/usr/bin/env python3
"""Stop hook: append last DEV assistant reply to state/logs/cto.log AND
persist session-id + rate-limit signal back to the tasks DB so the
auto-resume scheduler can recover the work later.

Mirrors hook-log-reply.py but for DEV sessions. Gated by DEV_TASK_ID env
(set by runners/dev_init.py before exec). Writes:

    [<ts>] Dev:<task_id>: <reply text>

…and on top of that:

    * tasks.session_id      ← transcript filename stem (resume handle)
    * tasks.last_checkpoint ← ISO 8601 UTC of this hook fire
    * tasks.status          ← 'rate_limited' if any record looks like a
                              429 / rate_limit_error
    * tasks.retry_after_ts  ← now + 5min (default backoff) when RL flagged

CTO's UserPromptSubmit hook tails cto.log and surfaces new lines into
the next CTO turn, so DEV replies appear in the CTO chat automatically.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/Users/gob/Projects/Agents")
LOG = ROOT / "state" / "logs" / "cto.log"
DB_PATH = ROOT / "state" / "tasks.db"


def _log_for(cto_id: str | None) -> Path:
    """Per-CTO log path when the spawning CTO is known, else the global log."""
    if cto_id:
        return ROOT / "state" / "logs" / f"cto-{cto_id}.log"
    return LOG
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


def _scan_records(transcript: Path) -> tuple[str, bool]:
    """Return (last_assistant_text, rate_limited_seen)."""
    last_text = ""
    rl = False
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

                if rec.get("type") == "assistant":
                    msg = rec.get("message") or {}
                    text = extract_text(msg.get("content"))
                    if text.strip():
                        last_text = text
                        if RATE_LIMIT_RE.search(text):
                            rl = True

                if rec.get("isApiErrorMessage") or rec.get("type") == "error":
                    blob = json.dumps(rec)
                    if RATE_LIMIT_RE.search(blob):
                        rl = True
    except Exception:
        pass
    return last_text, rl


def _persist(task_id: str, session_id: str, rate_limited: bool) -> None:
    if not DB_PATH.exists():
        return
    now = _now_iso()
    try:
        conn = sqlite3.connect(str(DB_PATH))
        try:
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
            conn.commit()
        finally:
            conn.close()
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
    task_id = os.environ.get("DEV_TASK_ID")
    if not task_id:
        return 0
    role = os.environ.get("DEV_ROLE")
    cto_id = os.environ.get("DEV_CTO_ID")
    owner_role = os.environ.get("DEV_CTO_ROLE", "cto")
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

    last_text, rate_limited = _scan_records(p)
    session_id = _session_id_from_path(p)
    _persist(task_id, session_id, rate_limited)

    last_text = (last_text or "").strip()
    if not last_text and not rate_limited:
        return 0
    if len(last_text) > MAX_CHARS:
        last_text = last_text[:MAX_CHARS] + " ...[truncated]"

    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    # Dual-write: global cto.log (legacy consumers) + the spawning CTO's
    # per-session log so multi-CTO setups don't cross feeds.
    targets = [LOG]
    per = _log_for(cto_id)
    if per != LOG:
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
