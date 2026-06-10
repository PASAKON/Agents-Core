#!/usr/bin/env python3
"""UserPromptSubmit hook for CTO sessions.

Two responsibilities:
  1. Append the CEO prompt to state/logs/cto.log with a `CEO:` prefix.
  2. Surface any new `Dev:*` lines (or CTO-event lines) that arrived in
     cto.log since the previous hook fire as additional context, so the
     CTO model sees DEV progress inline in its next reasoning step.

State for #2: byte offset stored at state/.cto_log_pos-<CTO_SESSION_ID>
(one cursor per CTO session — a shared cursor would let whichever
session fires first consume lines the others never see). Falls back to
state/.cto_log_pos when no session id is in env.

Multi-CTO filtering: DEV lines are surfaced only when the task belongs
to this session (tasks.owner_cto) or has no owner; CTO-event lines
tagged `CTO-event[LEVEL][<sid>]` by lib/notify are dropped when the sid
is another session's. Untagged legacy lines pass through.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "state" / "logs" / "cto.log"
DB_PATH = ROOT / "state" / "tasks.db"

SID = os.environ.get("CTO_SESSION_ID") or ""
STATE = ROOT / "state" / (f".cto_log_pos-{SID}" if SID else ".cto_log_pos")

# Match any DEV reply line. Old format: `] Dev:task-xxx:`.
# New format: `] <Role Label> task-xxx:` (also `] RateLimit <Role> task-xxx:`).
DEV_LINE_RE = re.compile(r"\] (?:Dev:|[^:]+ )task-[0-9a-fA-F]+:")
EVENT_PREFIX = "] CTO-event"
EVENT_SID_RE = re.compile(r"\] CTO-event\[[A-Z]+\]\[([0-9a-fA-F-]+)\]")
TASK_ID_RE = re.compile(r"task-[0-9a-fA-F]{6,}")
MAX_LINES = 50


def _read_offset(log_size: int) -> int:
    try:
        return int(STATE.read_text().strip())
    except (OSError, ValueError):
        # First fire for this session: start at EOF so a new CTO chat
        # doesn't replay the entire historical log as "recent activity".
        return log_size if SID else 0


def _write_offset(n: int) -> None:
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(str(n))
    except OSError:
        pass


def _pending_lines(offset: int, size: int) -> list[str]:
    if not LOG.exists():
        return []
    if offset > size:
        offset = 0
    with LOG.open("rb") as f:
        f.seek(offset)
        data = f.read()
    text = data.decode("utf-8", errors="replace")
    return [l for l in text.splitlines() if l.strip()]


def _task_owners(task_ids: set[str]) -> dict[str, str | None]:
    """Map task_id → owner_cto (None when unowned/unknown)."""
    if not task_ids or not DB_PATH.exists():
        return {}
    try:
        conn = sqlite3.connect(str(DB_PATH))
        try:
            placeholders = ",".join("?" * len(task_ids))
            rows = conn.execute(
                f"SELECT id, owner_cto FROM tasks WHERE id IN ({placeholders})",
                sorted(task_ids),
            ).fetchall()
        finally:
            conn.close()
        return {r[0]: r[1] for r in rows}
    except Exception:
        return {}


def _filter_for_session(lines: list[str]) -> list[str]:
    """Keep lines this session should see. No session id → keep all."""
    if not SID:
        return lines
    ids = set()
    for l in lines:
        m = TASK_ID_RE.search(l)
        if m:
            ids.add(m.group(0))
    owners = _task_owners(ids)
    keep: list[str] = []
    for l in lines:
        m_evt = EVENT_SID_RE.search(l)
        if m_evt:
            if m_evt.group(1) != SID:
                continue
            keep.append(l)
            continue
        m_task = TASK_ID_RE.search(l)
        if m_task:
            owner = owners.get(m_task.group(0))
            if owner and owner != SID:
                continue
        keep.append(l)
    return keep


def main() -> int:
    if os.environ.get("CTO_SESSION") != "1":
        return 0
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    prompt = (payload.get("prompt") or "").strip()
    if not prompt:
        return 0

    try:
        size_before = LOG.stat().st_size if LOG.exists() else 0
    except OSError:
        size_before = 0
    offset_before = _read_offset(size_before)
    pending = _pending_lines(offset_before, size_before)
    surfaced = [
        l for l in pending
        if DEV_LINE_RE.search(l) or EVENT_PREFIX in l
    ]
    surfaced = _filter_for_session(surfaced)
    if len(surfaced) > MAX_LINES:
        surfaced = surfaced[-MAX_LINES:]

    LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] CEO: {prompt}\n")

    try:
        _write_offset(LOG.stat().st_size)
    except OSError:
        pass

    if surfaced:
        print("## Recent DEV / org activity (since your previous reply)")
        print()
        for line in surfaced:
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
