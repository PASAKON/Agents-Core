"""Fold the heartbeat hook's jsonl into the hub (org restructure P3-C).

scripts/hook-heartbeat.py cannot reach the hub (system python3: no ORG_DB_URL, no
psycopg), so it appends one line per session per minute to
state/reports/heartbeat.jsonl. This module, run with the hub env, reads that file
from a saved byte offset (state/reports/heartbeat.offset) and writes

  session_heartbeats(session_id, project_id, at)   upsert, one row per session
  projects.last_active                             raised to the newest `at`, never lowered

The live-sessions publisher loop (tools/live_sessions.py) calls ``fold`` once a minute;
a fold error is caught there and never breaks publishing. By hand, with the hub env:

    bash scripts/hub/with-org-db-env.sh .venv/bin/python -m tools.heartbeat_fold

Session -> project:
  * a Project Head line (task_id null): state/locks/project_head-<id>.project, which
    spawn-ph writes and which holds the project NAME the PH was started with;
  * a worker line (task_id set): the task row's owner. When tasks.owner_role is
    'project_head', its tasks.owner_cto is that PH's session id, then as above.
  The name is matched against projects.id, then projects.name (both case-insensitive),
  then with case, spaces, hyphens and punctuation ignored ("BlackLiquidity" finds
  "BLACK LIQUIDITY" and "black-liquidity"). A label that matches two projects, or none,
  is an unknown project: the line is skipped and counted, never guessed.

Safe to re-run: the offset moves only after the hub write is committed, and both writes
are monotonic (an older `at` never overwrites a newer one), so a repeated or replayed
line changes nothing. A file shorter than the saved offset (truncated) or with another
inode (rotated) is read from the start. A last line without its newline (the hook is
mid-write) waits for the next run. A heartbeat timestamped more than MAX_FUTURE ahead
of now is counted as bad: last_active only moves forward, so one wild clock would
otherwise freeze it. The file is untrusted input; every field is validated.

The SQL is the same on Postgres and SQLite (CASE, not GREATEST) so the tests can run
the real statements without a Postgres server.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_NAME = "heartbeat.jsonl"
OFFSET_NAME = "heartbeat.offset"
MAX_READ = 4 * 1024 * 1024      # bytes per run; the rest waits for the next minute
MAX_FUTURE = timedelta(minutes=5)

_SESSION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_SID_RE = re.compile(r"[0-9a-f]{8}")
_PH_ROLE = "project_head"    # lib/roles.PH_ROLE; literal so this module stays import-light

_UPSERT_BEAT = (
    "INSERT INTO session_heartbeats (session_id, project_id, at) VALUES (?, ?, ?)"
    " ON CONFLICT (session_id) DO UPDATE SET"
    " project_id = CASE WHEN EXCLUDED.at >= session_heartbeats.at"
    " THEN EXCLUDED.project_id ELSE session_heartbeats.project_id END,"
    " at = CASE WHEN EXCLUDED.at > session_heartbeats.at"
    " THEN EXCLUDED.at ELSE session_heartbeats.at END")
_RAISE_ACTIVE = (
    "UPDATE projects SET last_active = ? WHERE id = ?"
    " AND (last_active IS NULL OR last_active < ?)")


def _key(text: str) -> str:
    return re.sub(r"[^0-9a-z]", "", text.casefold())


class _Projects:
    """projects.id / projects.name -> id, for the labels the lock files hold."""

    def __init__(self, conn):
        self._exact: dict[str, set[str]] = {}
        self._loose: dict[str, set[str]] = {}
        for row in conn.execute("SELECT id, name FROM projects").fetchall():
            pid, name = str(row[0]), str(row[1] or "")
            for label in (pid, name):
                if label.strip():
                    self._exact.setdefault(label.strip().casefold(), set()).add(pid)
                if _key(label):
                    self._loose.setdefault(_key(label), set()).add(pid)

    def find(self, label: str) -> str | None:
        for table, key in ((self._exact, label.strip().casefold()), (self._loose, _key(label))):
            ids = table.get(key) if key else None
            if ids:
                return next(iter(ids)) if len(ids) == 1 else None
        return None


def _ph_label(locks_dir: Path, sid: str) -> str:
    """The project NAME in state/locks/project_head-<sid>.project, or ""."""
    if not _SID_RE.fullmatch(sid):
        return ""
    try:
        with open(locks_dir / f"project_head-{sid}.project", encoding="utf-8") as fh:
            return (fh.readline() or "").strip()[:80]
    except (OSError, UnicodeDecodeError):
        return ""


def _parse_ts(value, latest: datetime) -> datetime | None:
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    at = at.astimezone(timezone.utc)
    return at if at <= latest else None


def _read_offset(path: Path, ino: int) -> int:
    """The saved offset, or 0 when the file is missing, unreadable or has another
    inode than the one the offset was saved against. "<offset>" alone is also read."""
    try:
        parts = path.read_text(encoding="ascii").split()
        offset = int(parts[0])
        if offset < 0 or (len(parts) > 1 and int(parts[1]) != ino):
            return 0
        return offset
    except (OSError, ValueError, IndexError, UnicodeDecodeError):
        return 0


def _write_offset(path: Path, offset: int, ino: int) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(f"{offset} {ino}\n", encoding="ascii")
    os.replace(tmp, path)


def fold(conn, root: Path = ROOT, now: datetime | None = None) -> dict:
    """Fold the new lines of root/state/reports/heartbeat.jsonl into the hub.

    Returns ``{"read": lines examined, "folded": lines written to a session row,
    "unknown": lines whose project is unknown (skipped), "bad": lines that failed
    validation, "offset": the saved offset}``. Touches the
    hub only when there is a complete new line to fold; commits before it moves the
    offset. A hub error propagates with the offset unchanged (the caller rolls back)."""
    reports = Path(root) / "state" / "reports"
    log, offset_file = reports / LOG_NAME, reports / OFFSET_NAME
    out = {"read": 0, "folded": 0, "unknown": 0, "bad": 0, "offset": 0}
    try:
        st = os.stat(log)
    except OSError:
        return out
    start = _read_offset(offset_file, st.st_ino)
    if start > st.st_size:        # truncated, or replaced by a shorter file
        start = 0
    out["offset"] = start
    with open(log, "rb") as fh:
        fh.seek(start)
        data = fh.read(MAX_READ)
    end = data.rfind(b"\n") + 1
    if end == 0:
        if len(data) < MAX_READ:  # a partial line the hook is still writing
            return out
        end = len(data)           # 4 MiB with no newline is not a heartbeat; step past it
    latest = (now or datetime.now(timezone.utc)) + MAX_FUTURE

    beats: dict[str, list] = {}   # session -> [newest at, its task id, lines seen]
    for raw in data[:end].splitlines():
        if not raw.strip():
            continue
        out["read"] += 1
        try:
            rec = json.loads(raw)
            session, task, at = rec["session_id"], rec.get("task_id"), _parse_ts(rec["ts"], latest)
        except (ValueError, KeyError, TypeError, UnicodeDecodeError):
            session, task, at = None, None, None
        if (not isinstance(session, str) or not _SESSION_RE.fullmatch(session) or at is None
                or not (task is None or (isinstance(task, str) and _SESSION_RE.fullmatch(task)))):
            out["bad"] += 1
            continue
        seen = beats.setdefault(session, [at, task, 0])
        seen[2] += 1
        if at >= seen[0]:
            seen[0], seen[1] = at, task

    if beats:
        projects, locks_dir = _Projects(conn), Path(root) / "state" / "locks"
        owners: dict[str, str] = {}
        newest: dict[str, datetime] = {}
        for session, (at, task, lines) in sorted(beats.items()):
            sid = session
            if task:                                  # a worker: its task row's PH owner
                if task not in owners:
                    row = conn.execute("SELECT owner_cto, owner_role FROM tasks WHERE id = ?",
                                       (task,)).fetchone()
                    owners[task] = str(row[0] or "") if row and row[1] == _PH_ROLE else ""
                sid = owners[task]
            pid = projects.find(_ph_label(locks_dir, sid))
            if pid is None:
                out["unknown"] += lines
                continue
            conn.execute(_UPSERT_BEAT, (session, pid, at))
            out["folded"] += lines
            newest[pid] = max(at, newest.get(pid, at))
        for pid, at in sorted(newest.items()):
            conn.execute(_RAISE_ACTIVE, (at, pid, at))
        conn.commit()
    _write_offset(offset_file, start + end, st.st_ino)
    out["offset"] = start + end
    return out


def main(argv=None) -> int:
    url = os.environ.get("ORG_DB_URL", "").strip()
    if not url:
        print("ORG_DB_URL unset (run with scripts/hub/with-org-db-env.sh)", file=sys.stderr)
        return 1
    sys.path.insert(0, str(ROOT))
    from lib import db_pg
    conn = db_pg.connect(url, timeout=3)
    try:
        print(json.dumps(fold(conn)))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
