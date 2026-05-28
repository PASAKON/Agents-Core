"""SQLite task queue. Single source of truth for org work state."""
from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "tasks.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id              TEXT PRIMARY KEY,
    project         TEXT NOT NULL,
    role            TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    parent_task     TEXT,
    assigned_agent  TEXT,
    worktree        TEXT,
    branch          TEXT,
    depends_on      TEXT NOT NULL DEFAULT '[]',
    touches         TEXT NOT NULL DEFAULT '[]',
    report          TEXT,
    review          TEXT,
    iteration       INTEGER NOT NULL DEFAULT 0,
    session_id      TEXT,
    retry_after_ts  TEXT,
    last_checkpoint TEXT,
    owner_cto       TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project);
CREATE INDEX IF NOT EXISTS idx_tasks_role ON tasks(role);

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     TEXT,
    actor       TEXT NOT NULL,
    kind        TEXT NOT NULL,
    payload     TEXT,
    ts          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_task ON events(task_id);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);

CREATE TABLE IF NOT EXISTS locks (
    key         TEXT PRIMARY KEY,
    owner       TEXT NOT NULL,
    expires_at  TEXT NOT NULL
);
"""

VALID_STATUS = {"pending", "in_progress", "review", "done", "failed",
                "cancelled", "rate_limited", "stalled", "conflict",
                "blocked_human"}

# Columns added after initial release. init() runs idempotent ALTER TABLE
# ADD COLUMN for each so existing DBs migrate forward without losing data.
_MIGRATION_COLUMNS = [
    ("session_id", "TEXT"),
    ("retry_after_ts", "TEXT"),
    ("last_checkpoint", "TEXT"),
    ("touches", "TEXT NOT NULL DEFAULT '[]'"),
    ("pid", "INTEGER"),
    # tmux+ttyd backend (web_designer on mooniex-claudesign etc.)
    ("tmux_session", "TEXT"),
    ("ttyd_port", "INTEGER"),
    ("ttyd_pid", "INTEGER"),
    ("owner_cto", "TEXT"),
    # Runner-level messages (collision, lock failure, spawn errors) go here;
    # DEV completion summaries stay in tasks.report. Never mix the two.
    ("delegate_log", "TEXT"),
]

# Statuses where touched paths are no longer being modified — release locks.
RELEASING_STATUSES = {"review", "done", "failed", "cancelled", "stalled"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init():
    """Create schema. Idempotent. Also runs forward-only column migrations
    for tables that predate _MIGRATION_COLUMNS."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        existing = {r["name"] for r in conn.execute(
            "PRAGMA table_info(tasks)").fetchall()}
        for col, coltype in _MIGRATION_COLUMNS:
            if col not in existing:
                conn.execute(f"ALTER TABLE tasks ADD COLUMN {col} {coltype}")
        # Backfill: move runner-generated messages out of report into
        # delegate_log so DEV completion reports are never overwritten.
        conn.execute("""
            UPDATE tasks
               SET delegate_log = report,
                   report = NULL
             WHERE report IS NOT NULL
               AND delegate_log IS NULL
               AND (   report LIKE 'path collision with%'
                    OR report LIKE 'kickoff failed%'
                    OR report LIKE 'lock contested%'
                    OR report LIKE 'path locks held by%'
                    OR report LIKE 'tmux create failed%'
                    OR report LIKE 'iTerm spawn failed%'
                    OR report LIKE 'DEV timed out%')
        """)
    print(f"[db] initialized at {DB_PATH}")


def new_task_id() -> str:
    return "task-" + uuid.uuid4().hex[:8]


def create_task(
    project: str,
    role: str,
    title: str,
    description: str,
    parent_task: str | None = None,
    depends_on: list[str] | None = None,
    touches: list[str] | None = None,
    owner_cto: str | None = None,
) -> str:
    tid = new_task_id()
    ts = now_iso()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO tasks (id,project,role,status,title,description,parent_task,depends_on,touches,owner_cto,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (tid, project, role, "pending", title, description, parent_task,
             json.dumps(depends_on or []), json.dumps(touches or []), owner_cto, ts, ts),
        )
        log_event(conn, tid, "system", "task_created",
                  {"role": role, "title": title, "touches": touches or []})
    return tid


def claim_task(task_id: str, agent: str) -> bool:
    """Atomic claim. Returns False if already claimed."""
    ts = now_iso()
    with get_conn() as conn:
        cur = conn.execute(
            """UPDATE tasks SET assigned_agent=?, status='in_progress', updated_at=?
               WHERE id=? AND status='pending' AND assigned_agent IS NULL""",
            (agent, ts, task_id),
        )
        if cur.rowcount:
            log_event(conn, task_id, agent, "claimed", {})
            return True
    return False


VALID_COLUMNS = {
    "assigned_agent", "worktree", "branch", "report", "review",
    "iteration", "description", "title",
    "session_id", "retry_after_ts", "last_checkpoint", "pid",
    "tmux_session", "ttyd_port", "ttyd_pid", "owner_cto",
    "delegate_log",
}


def update_status(task_id: str, status: str, *, actor: str = "system", **fields):
    if status not in VALID_STATUS:
        raise ValueError(
            f"invalid status {status!r}. allowed: {sorted(VALID_STATUS)}"
        )
    bad = set(fields) - VALID_COLUMNS
    if bad:
        raise ValueError(f"unknown column(s): {bad}")
    ts = now_iso()
    sets = ["status=?", "updated_at=?"]
    vals = [status, ts]
    for k, v in fields.items():
        sets.append(f"{k}=?")
        vals.append(v)
    vals.append(task_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE tasks SET {','.join(sets)} WHERE id=?", vals)
        log_event(conn, task_id, actor, f"status_{status}", fields)
    if status in RELEASING_STATUSES:
        try:
            t = get_task(task_id)
            if t:
                release_task_locks(task_id, t["project"])
        except Exception:
            pass


def get_task(task_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    return dict(row) if row else None


def list_tasks(status: str | None = None, project: str | None = None,
               role: str | None = None, limit: int = 100) -> list[dict]:
    q = "SELECT * FROM tasks WHERE 1=1"
    args = []
    if status:
        q += " AND status=?"
        args.append(status)
    if project:
        q += " AND project=?"
        args.append(project)
    if role:
        q += " AND role=?"
        args.append(role)
    q += " ORDER BY updated_at DESC LIMIT ?"
    args.append(limit)
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(q, args).fetchall()]


def pending_tasks_for(role: str, project: str | None = None) -> list[dict]:
    q = """SELECT * FROM tasks
           WHERE role=? AND status='pending' AND assigned_agent IS NULL"""
    args = [role]
    if project:
        q += " AND project=?"
        args.append(project)
    q += " ORDER BY created_at ASC"
    with get_conn() as conn:
        rows = [dict(r) for r in conn.execute(q, args).fetchall()]
    out = []
    for r in rows:
        deps = json.loads(r["depends_on"] or "[]")
        if not deps or all(_is_done(d) for d in deps):
            out.append(r)
    return out


def _is_done(task_id: str) -> bool:
    t = get_task(task_id)
    return bool(t and t["status"] == "done")


def log_event(conn, task_id, actor, kind, payload):
    conn.execute(
        "INSERT INTO events (task_id,actor,kind,payload,ts) VALUES (?,?,?,?,?)",
        (task_id, actor, kind, json.dumps(payload), now_iso()),
    )


def recent_events(limit: int = 50, task_id: str | None = None) -> list[dict]:
    q = "SELECT * FROM events"
    args = []
    if task_id:
        q += " WHERE task_id=?"
        args.append(task_id)
    q += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(q, args).fetchall()]


def acquire_lock(key: str, owner: str, ttl_seconds: int = 600) -> bool:
    from datetime import timedelta
    ts = now_iso()
    expires = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat(timespec="seconds")
    with get_conn() as conn:
        existing = conn.execute("SELECT owner,expires_at FROM locks WHERE key=?", (key,)).fetchone()
        if existing and existing["expires_at"] > ts and existing["owner"] != owner:
            return False
        conn.execute("INSERT OR REPLACE INTO locks (key,owner,expires_at) VALUES (?,?,?)",
                     (key, owner, expires))
    return True


def release_lock(key: str, owner: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM locks WHERE key=? AND owner=?", (key, owner))


def _path_lock_key(project: str, path: str) -> str:
    return f"proj:{project}:path:{path.strip().lstrip('/')}"


ACTIVE_STATUSES = ("pending", "in_progress", "rate_limited", "conflict")


def find_conflicts(project: str, touches: list[str],
                   exclude_task: str | None = None) -> list[dict]:
    """Return active tasks in `project` whose touches intersect `touches`.

    Pure path-set intersection (no glob expansion). Caller is responsible for
    passing normalised repo-relative paths.
    """
    if not touches:
        return []
    want = {p.strip().lstrip("/") for p in touches if p and p.strip()}
    if not want:
        return []
    placeholders = ",".join("?" * len(ACTIVE_STATUSES))
    q = (f"SELECT id,role,status,title,touches FROM tasks "
         f"WHERE project=? AND status IN ({placeholders})")
    args = [project, *ACTIVE_STATUSES]
    if exclude_task:
        q += " AND id<>?"
        args.append(exclude_task)
    hits: list[dict] = []
    with get_conn() as conn:
        rows = conn.execute(q, args).fetchall()
    for r in rows:
        try:
            their = {p.strip().lstrip("/") for p in json.loads(r["touches"] or "[]")}
        except Exception:
            their = set()
        overlap = sorted(want & their)
        if overlap:
            hits.append({
                "task_id": r["id"], "role": r["role"], "status": r["status"],
                "title": r["title"], "overlap": overlap,
            })
    return hits


def lock_paths(task_id: str, project: str, touches: list[str],
               ttl_seconds: int = 3600) -> tuple[bool, list[str], list[str]]:
    """Try to acquire path locks for every path in `touches`.

    Atomic-ish: acquires sequentially, rolls back on first failure.
    Returns (ok, acquired_keys, blocking_keys). If ok is False, no locks held.
    """
    keys = [_path_lock_key(project, p) for p in touches if p and p.strip()]
    acquired: list[str] = []
    for k in keys:
        if acquire_lock(k, owner=task_id, ttl_seconds=ttl_seconds):
            acquired.append(k)
        else:
            for a in acquired:
                release_lock(a, owner=task_id)
            return False, [], [k]
    return True, acquired, []


def release_task_locks(task_id: str, project: str) -> int:
    """Release every path lock owned by task_id within project. Returns count."""
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM locks WHERE owner=? AND key LIKE ?",
            (task_id, f"proj:{project}:path:%"),
        )
        return cur.rowcount or 0


def stats() -> dict:
    with get_conn() as conn:
        rows = conn.execute("SELECT status, COUNT(*) c FROM tasks GROUP BY status").fetchall()
    return {r["status"]: r["c"] for r in rows}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "init":
        init()
    elif cmd == "stats":
        print(stats())
    elif cmd == "list":
        for t in list_tasks(limit=20):
            print(f"{t['id']}  {t['role']:14s} {t['status']:12s} {t['project']:30s} {t['title']}")
    else:
        print("usage: python -m lib.db [init|stats|list]")
