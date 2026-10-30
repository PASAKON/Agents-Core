#!/usr/bin/env python3
"""Stop hook: append a DEV turn that has something to report to
state/logs/cto.log, relay it to the owning Project Head or C-level, and
persist the session id + rate-limit signal back to the tasks DB so the
auto-resume scheduler can recover the work later.

Mirrors hook-log-reply.py but for DEV sessions. Gated by WORKER_TASK_ID env
(set by runners/worker_init.py before exec). Writes, on every turn:

    * tasks.session_id      <- transcript filename stem (resume handle)
    * tasks.updated_at      <- now (liveness)
    * tasks.status          <- 'rate_limited', and tasks.retry_after_ts <-
                               now + 5 min, when THIS turn holds an API error
                               record that names a rate limit, and only while
                               the task is still in_progress

tasks.last_checkpoint is not touched: runners/worker_mcp_server.dev_message
keeps the worker's full last message there (GH #54), and a timestamp written
over it at every Stop erased that text.

The log line and the relay happen only on a turn that called submit_report,
dev_message or file_blocker_issue, or that hit a rate limit (flag on or off;
wake chain W1, 2026-10-30). Every other turn stays in the worker's own
transcript. request_human_handoff is not on the list: the tool sends its own
letter. The log line reads:

    [<ts>] <Role Label> <task_id>: [<tools>] <reply text>

CTO's UserPromptSubmit hook tails cto.log and surfaces new lines into
the next CTO turn, so DEV reports appear in the CTO chat automatically.

ROOT is always this file's own checkout, as hook-log-prompt.py does (wake chain
W1, 2026-10-30). runners/worker_init.py registers the hook by its absolute path
in the hub checkout, so lib/ and tools/ are imported from that checkout and the
logs land in its state/logs/. It used to be the Mac literal whenever the
envelope flag was off: on any other host that names a tree with no lib/ or
tools/, so the DB write and the relay to the owner failed silently and the log
lines landed in a stray /Users/gob tree (measured on Contabo 2026-10-13 and
again 2026-10-30: no worker report reached its Project Head).

state/logs is writable by another account and this hook runs as root on
Contabo, so each log is opened relative to the directory, with no symlink
followed, and written only when it is a regular file with one link.

The relay letter, flag on or off, is a report or a blocker (urgent), a
dev_message (normal) or, for a rate limit with no event, a fyi (normal), at
most RELAY_MAX_CHARS for the whole letter. send_to_cto gets that kind: a
report or a fyi never wakes a C-level box (it waits for the session's next
prompt, lib.mailbox.quiet_for); a Project Head box wakes. A task with no
owner is not relayed (there is no box to send to); its log line stays.

Envelope mode (`ORG_MAIL_ENVELOPE=1`, default off; org restructure P1):
  * the hub call is capped at HUB_TIMEOUT_S;
  * the letter carries subject, kind and prio as envelope fields; the wake is
    debounced for a normal letter (lib.mailbox.wake_due).
Off, the letter has no envelope fields, so its body names its kind in its
first words (`report · urgent · ...`, the plain-text form lib.mailbox.body_kind
reads), and a later reader of the box classes it as the envelope would.
"""
from __future__ import annotations

import json
import os
import re
import stat
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _envelope_on() -> bool:
    return os.environ.get("ORG_MAIL_ENVELOPE", "").strip().lower() in ("1", "true", "yes", "on")


ENVELOPE = _envelope_on()
ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "state" / "logs" / "cto.log"
HUB_TIMEOUT_S = 3.0

# worker MCP tools (runners/worker_mcp_server.py) whose turn is worth a relay
EVENT_TOOLS = {
    "submit_report": "report",
    "dev_message": "message",
    "file_blocker_issue": "blocker",
}


def _letter_kind(events: list[str]) -> tuple[str, str]:
    """(kind, prio) of the relay letter for this turn's events."""
    kinds = {EVENT_TOOLS[e] for e in events}
    if "blocker" in kinds:
        return "blocker", "urgent"
    if "report" in kinds:
        return "report", "urgent"
    if "message" in kinds:
        return "message", "normal"
    return "fyi", "normal"         # a rate limit with no event


def _log_for(cto_id: str | None) -> Path:
    """Per-CTO log path when the spawning CTO is known, else the global log."""
    if cto_id:
        return ROOT / "state" / "logs" / f"cto-{cto_id}.log"
    return ROOT / "state" / "logs" / "cto.log"


MAX_CHARS = 4000
RELAY_MAX_CHARS = 600            # the whole letter (wake chain token rule 5)
TRUNC = " ...[truncated]"
DEFAULT_BACKOFF_S = 300
LOG_MODE = 0o644                 # as the existing state/logs/cto-*.log files

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
    """Return (last_assistant_text, rate_limited, turn_events): the last is
    the EVENT_TOOLS names the current turn (since the last prompt) called.

    rate_limited comes from the current turn's API error records only, flag
    on or off. Assistant prose is never read for it: a worker that wrote
    "429" or "rate limit" in any earlier turn (a test count of 1429, an HTTP
    429 it handled) used to set the task to rate_limited on every later
    turn, its submitted report included."""
    last_text = ""
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

                if rec.get("isApiErrorMessage") or rec.get("type") == "error":
                    if RATE_LIMIT_RE.search(json.dumps(rec)):
                        turn_rl = True
    except Exception:
        pass
    return last_text, turn_rl, events


def _persist(task_id: str, session_id: str, rate_limited: bool) -> None:
    now = _now_iso()
    try:
        sys.path.insert(0, str(ROOT))
        from lib import db as db_lib
        # envelope mode caps the hub call: a slow hub must not hold the worker's turn
        with (db_lib.get_conn(timeout=HUB_TIMEOUT_S) if ENVELOPE else db_lib.get_conn()) as conn:
            conn.execute(
                "UPDATE tasks SET session_id=?, updated_at=? WHERE id=?",
                (session_id, now, task_id),
            )
            if rate_limited:
                retry_after = (
                    datetime.now(timezone.utc)
                    + timedelta(seconds=DEFAULT_BACKOFF_S)
                ).isoformat(timespec="seconds")
                # only a task still at work: never over review, done or cancelled
                conn.execute(
                    "UPDATE tasks SET status='rate_limited', retry_after_ts=?, "
                    "updated_at=? WHERE id=? AND status='in_progress'",
                    (retry_after, now, task_id),
                )
    except Exception:
        pass


def _append_log(path: Path, text: str) -> None:
    """Append `text` to `path`, which must be ROOT/state/logs/<name>, without
    following a symlink at any level below ROOT: each directory is opened
    O_NOFOLLOW relative to its parent (and made if missing), the file
    O_NOFOLLOW | O_NONBLOCK relative to its directory, and written only when
    fstat shows a regular file with one link. Any other path (an owner id
    holding "/" or ".."), any refusal or any error skips the line."""
    try:
        parts = path.relative_to(ROOT).parts
    except ValueError:
        return
    if len(parts) != 3 or parts[:2] != ("state", "logs") or parts[2] in (".", ".."):
        return
    cloexec = getattr(os, "O_CLOEXEC", 0)
    dir_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | cloexec
    fds: list[int] = []
    try:
        fds.append(os.open(str(ROOT), os.O_RDONLY | os.O_DIRECTORY | cloexec))
        for name in parts[:-1]:
            try:
                os.mkdir(name, 0o775, dir_fd=fds[-1])
            except FileExistsError:
                pass
            fds.append(os.open(name, dir_flags, dir_fd=fds[-1]))
        fd = os.open(parts[-1], os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW
                     | os.O_NONBLOCK | cloexec, LOG_MODE, dir_fd=fds[-1])
        fds.append(fd)
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
            return
        data = text.encode("utf-8", "replace")
        while data:
            n = os.write(fd, data)
            if n <= 0:
                return
            data = data[n:]
    except (OSError, ValueError):
        return
    finally:
        for fd in reversed(fds):
            try:
                os.close(fd)
            except OSError:
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

    if not events and not rate_limited:
        return 0          # nothing to report: the turn stays in the worker's transcript
    last_text = (last_text or "").strip()
    kind, prio = _letter_kind(events)
    letter_kw: dict = {"kind": kind, "prio": prio}
    if ENVELOPE:
        gist = " ".join(last_text.split()) or ("rate limited" if rate_limited else "see the task report")
        letter_kw["subject"] = f"{kind} {task_id}: {gist}"[:80]
    if events:
        last_text = f"[{', '.join(events)}] " + (last_text or "(no closing text; see the task report)")
    if len(last_text) > MAX_CHARS:
        last_text = last_text[:MAX_CHARS] + TRUNC

    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    lines = ""
    if last_text:
        lines += f"[{ts}] {role_label} {task_id}: {last_text}\n"
    if rate_limited:
        lines += (f"[{ts}] RateLimit {role_label} {task_id}: status=rate_limited, "
                  f"retry_after={DEFAULT_BACKOFF_S}s, session={session_id}\n")
    # Dual-write: global cto.log (legacy consumers) + the spawning CTO's
    # per-session log so multi-CTO setups don't cross feeds.
    targets = [_log_for(None)]
    per = _log_for(cto_id)
    if per != targets[0]:
        targets.append(per)
    for target in targets:
        _append_log(target, lines)

    relay = last_text
    if rate_limited:
        rl_note = f"(rate limit hit this turn; retry after ~{DEFAULT_BACKOFF_S}s)"
        relay = f"{relay}\n{rl_note}" if relay else rl_note
    if not ENVELOPE:
        relay = f"{kind} · {prio} · {relay}"      # no envelope fields: the body names its kind
    if len(relay) > RELAY_MAX_CHARS:
        relay = relay[:RELAY_MAX_CHARS - len(TRUNC)] + TRUNC
    if not cto_id:
        return 0          # an ownerless task has no box; the log line above is its record
    try:
        sys.path.insert(0, str(ROOT))
        from tools.send_to_cto import send as send_to_cto
        send_to_cto(task_id, relay, role=role, cto_id=cto_id,
                    owner_role=owner_role, **letter_kw)
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
