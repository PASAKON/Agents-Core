"""Task queue -- SQLite by default, Postgres when ORG_DB_URL is set.

docs/design/tasks-db-hub.md §3.1: ORG_DB_URL unset means exactly today's
sqlite3 behaviour (unchanged). Set to a `postgresql://...` URL, every caller
that goes through get_conn() (directly or via the bypassers routed in this
task) talks to the Postgres hub instead -- see lib/db_pg.py for the
SQL-translation wrapper that makes that transparent.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

# lib.config is imported lazily (in create_task): it pulls in PyYAML, and the
# PreToolUse hooks import lib.db under the system python3, which may not have it.
from lib import db_pg

def _resolve_root() -> Path:
    """Hub checkout root. `ORG_ROOT` (set by runners/worker_init.py on every
    worker spawn, GH #154) wins when present -- a worker's own `__file__`
    resolves to its worktree, so an ad-hoc `python3 -c '...from lib import
    db...'` run from inside a worktree would otherwise create/read a
    worktree-local `state/tasks.db` instead of the hub's shared one. A
    hub-side process never has `ORG_ROOT` set and falls back to `__file__`
    exactly as before."""
    org_root = os.environ.get("ORG_ROOT")
    if org_root and org_root.strip():
        return Path(org_root)
    return Path(__file__).resolve().parent.parent


ROOT = _resolve_root()
DB_PATH = ROOT / "state" / "tasks.db"

# Org Mesh W1.7 (docs/design/org-mesh.md, docs/design/tasks-db-hub.md §5 risk
# "read-only fallback to local SQLite"): a periodic export of the Postgres
# hub (scripts/hub/export_to_sqlite.py, every 15 min via the plist/systemd
# units beside it). get_conn() reads from this file when ORG_DB_URL is set
# but the hub cannot be reached -- see HubUnavailable below.
SNAPSHOT_PATH = ROOT / "state" / "tasks.snapshot.db"

# Ceiling used for the hub-connect attempt that decides whether to fall back
# to SNAPSHOT_PATH, for any get_conn() caller that doesn't pass its own
# `timeout` -- docs/design/org-mesh.md W1.7 ("connect timeout of 3s or
# less"). Measured Mac<->Contabo RTT is ~127ms (docs/design/tasks-db-hub.md
# §1), so 3s is generous for a live hub and short enough that a down hub
# fails over quickly instead of hanging every write for psycopg's own 10s
# default.
HUB_CONNECT_TIMEOUT_S = 3.0

# scripts/hub/cutover-mac.sh step 5 (docs/design/tasks-db-hub.md §3.3)
# replaces state/tasks.db with a directory once the hub cutover is done and
# the file has been archived -- a directory makes sqlite3.connect() raise
# instead of silently creating a fresh empty database at that path (the
# exact split-brain the cutover removes). ArchivedDB lets callers (the
# self-repo-guard/log-prompt hooks) distinguish this from every other
# connect failure and fail OPEN instead of refusing forever.
ARCHIVED_TASKS_DB_MSG = (
    "tasks.db is archived (hub cutover done) — this session predates the "
    "cutover: restart it (/terminal-restart) so it talks to the hub"
)


class ArchivedDB(RuntimeError):
    """Raised by _connect() when the resolved sqlite path is a directory."""


class HubUnavailable(RuntimeError):
    """ORG_DB_URL is set, the Postgres hub could not be reached, and either

      (a) there is no usable snapshot at SNAPSHOT_PATH to fall back to
          (run scripts/hub/export_to_sqlite.py once the hub is reachable), or
      (b) the caller just attempted a WRITE through the read-only snapshot
          fallback.

    A snapshot is read-only by construction (Org Mesh W1.7): a silent write
    to a local file the hub never sees would recreate exactly the split
    brain the hub cutover removed (docs/design/tasks-db-hub.md). Reads keep
    working off the snapshot; get_conn() never raises this for a read that
    the snapshot can actually answer.
    """


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

CREATE TABLE IF NOT EXISTS c_level_sessions (
    role             TEXT NOT NULL,
    session_id       TEXT NOT NULL,
    active_task_id   TEXT,
    spawned_at       TEXT NOT NULL,
    -- Lifecycle (task-728e4741): one of open|closed|saved|force_saved. A row
    -- starts 'open' at spawn; tools/session_status.record_close is the only
    -- writer that flips it. closed = done; saved = parked unfinished to free
    -- RAM; force_saved = closed while work was NOT done (flagged, resumable).
    status           TEXT NOT NULL DEFAULT 'open',
    closed_at        TEXT,   -- ISO 8601, NULL while open
    note             TEXT,   -- one line of why (the entry problem, for saved/force_saved)
    resume_uuid      TEXT,   -- full Claude UUID copied from state/locks/<role>-<id>.uuid at close
    PRIMARY KEY (role, session_id)
);
CREATE INDEX IF NOT EXISTS idx_c_level_sessions_task
    ON c_level_sessions(active_task_id)
    WHERE active_task_id IS NOT NULL;

-- Org Mesh W2.1 (docs/design/org-mesh.md C2/C3/C4): the host registry and
-- cross-host mailbox. `hosts` is seeded from config/hosts.yaml
-- (seed_hosts_from_config) and then kept live by each host's own node_agent
-- heartbeat (W2.3, not built here) -- upsert_host never overwrites a field
-- the caller didn't pass, so a heartbeat writer and the config seeder can
-- both touch the same row without clobbering each other.
CREATE TABLE IF NOT EXISTS hosts (
    host         TEXT PRIMARY KEY,
    os           TEXT,
    hq_root      TEXT,
    agents_root  TEXT,
    provides     TEXT,   -- JSON array, e.g. ["chrome","gpu"]
    max_workers  INTEGER,
    status       TEXT,   -- online|offline|pending_identity|left
    probed_at    TEXT,
    free_gb      REAL,
    ram_free_gb  REAL,
    running      INTEGER,
    version      TEXT,
    updated_at   TEXT
);

-- Cross-host C-level mail (W2.4 delivers these, W2.2's `node_dispatch
-- deliver_letter <id>` marks them delivered). to_session/from_role/
-- from_session are optional -- a letter can target a role broadly (every
-- open CTO tab on to_host) or one specific session.
CREATE TABLE IF NOT EXISTS letters (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    to_host       TEXT,
    to_role       TEXT,
    to_session    TEXT,
    from_role     TEXT,
    from_session  TEXT,
    body          TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending',  -- pending|delivered|failed
    created_at    TEXT,
    delivered_at  TEXT,
    attempts      INTEGER NOT NULL DEFAULT 0,
    last_error    TEXT,
    from_host     TEXT    -- W2.4: the host that sent it; only that host's watchdog retries it
);
CREATE INDEX IF NOT EXISTS idx_letters_to_host_status ON letters(to_host, status);
"""

# Org Mesh W4.1 (tools/hq_join.py): one-time join tokens. Only the sha256 of a
# token is stored, never the token. `locks` cannot hold this: it has no used_at
# and no host, and acquire_lock/_claim purge expired rows, which would turn
# "expired" and "reused" into "unknown" for the operator. One DDL string for
# both backends (TEXT columns only, valid SQLite and Postgres alike), run by
# init_schema() after the backend's own schema, so the two cannot drift.
JOIN_TOKENS_SCHEMA = """
CREATE TABLE IF NOT EXISTS join_tokens (
    token_hash   TEXT PRIMARY KEY,
    host         TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    expires_at   TEXT NOT NULL,
    used_at      TEXT
);
"""

# Org Mesh W4.2 (tools/hq_join.py provision): one row per joined node holding
# the Infisical client secret and GitHub deploy key made for it. `ciphertext` is
# the node's client id and secret sealed to its age recipient (lib/sealed.py):
# the plaintext never reaches this table, and only that node's key opens it.
# `ciphertext` is NULL between the mint and the seal of a run, and again after
# the secret is revoked. The two ids are what `leave` revokes by. Same one-DDL,
# TEXT-only, both-backends pattern as JOIN_TOKENS_SCHEMA.
#   fetched_at  first time `hq_join sealed` handed the ciphertext out
#   revoked_at  when `leave` revoked the Infisical client secret
NODE_SECRETS_SCHEMA = """
CREATE TABLE IF NOT EXISTS node_secrets (
    host                        TEXT PRIMARY KEY,
    ciphertext                  TEXT,
    infisical_client_secret_id  TEXT,
    github_deploy_key_id        TEXT,
    created_at                  TEXT NOT NULL,
    fetched_at                  TEXT,
    revoked_at                  TEXT
);
"""

VALID_STATUS = {"pending", "in_progress", "review", "done", "failed",
                "cancelled", "rate_limited", "stalled", "conflict",
                "blocked_human", "blocked_host", "reverted", "merged",
                # W2.3: a remote spawn whose host did not answer (lib/mesh.py
                # MeshUnreachable). Not failed: the watchdog retries it.
                "queued_remote"}

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
    # owning CTO session id — DEV reports route back to this CTO's tab
    ("owner_cto", "TEXT"),
    # UNUSED since 2026-09-23: the Z.ai/9Router provider switch it steered was
    # removed (CEO 2026-09-20); kept only because SQLite columns stay. History:
    # per-task provider override. NULL = follow WORKER_MODEL_PROVIDER (auto picked
    # whichever pool had more quota headroom). 'claude' = force the Claude path
    # regardless of quota, for work where a cheap miss is expensive: reviewing
    # or repairing someone else's code, and anything touching security or
    # secrets. Quota headroom is all the auto router can see — it has no notion
    # of how costly a mistake would be, which is what this expresses
    # (CEO 2026-08-10).
    ("model_hint", "TEXT"),
    # owning C-level role (cto/cfo/cmo/cgo) — picks which <role>-<id>.winid
    # lock send_to_cto reads so CXO-spawned reports land in the CXO's tab,
    # not a CTO tab. NULL on pre-migration rows (routing falls back to cto).
    ("owner_role", "TEXT"),
    # Runner-level messages (collision, lock failure, spawn errors) go here;
    # DEV completion summaries stay in tasks.report. Never mix the two.
    ("delegate_log", "TEXT"),
    # When a DEV was last actually spawned for this task. Written by
    # delegate_task at the worktree-creation step, and by nothing else.
    #
    # This exists because `updated_at` cannot answer it. `updated_at` means
    # only "something wrote to this row", and at least three paths write it
    # without spawning anything: reopen_task, the watchdog flipping a task
    # to stalled, and delegate_task's own duplicate-spawn refusal writing
    # delegate_log — which reset the very clock it was about to read, so
    # each retry pushed the lockout further out (GH #51, #53).
    #
    # NULL on pre-migration rows and on any task never delegated. Readers
    # must treat NULL as "no spawn on record", never as "spawned long ago".
    ("spawned_at", "TEXT"),
    # Which host (config/hosts.yaml key) this task's DEV runs/ran on.
    # NULL means "mac" — every pre-migration row, and every row created
    # before host routing existed, keeps working unchanged. tools/delegate.py
    # resolves the effective host as: explicit delegate_task(host=...) arg >
    # this column > 'mac' (docs/design/multi-host-workers.md Phase 1).
    ("host", "TEXT"),
    # Which host (config/hosts.yaml key) created this task row — the
    # C-level session's own lib.config.self_host(), stamped by create_task()
    # on every insert (docs/design/org-mesh.md C1, W0.1). Never NULL on a
    # new row; NULL only on pre-migration rows. Distinct from `host` above:
    # `dispatcher_host` is "who filed this task", `host` is "which host the
    # DEV runs/ran on" (explicit target or filled at local-spawn time).
    ("dispatcher_host", "TEXT"),
    # Which CLI drives this task's worker: claude|codex|agy (task-adbc6f43).
    # NULL means "claude" — every pre-migration row, and every row created
    # before runner selection existed, keeps working unchanged. Validated
    # against lib.config.KNOWN_RUNNERS and the target host's config/hosts.yaml
    # `runners:` list at delegate_task() time (the hub), not here — never
    # trust a runner blind at spawn time (docs/ops/agent-runners.md §4).
    ("runner", "TEXT"),
    # Model the router picked for `runner` (the part after 'runner:' in a
    # plans.yaml candidate, e.g. gemini-3.8-flash-high, claude-sonnet-4-6).
    # NULL = the runner's own default. Written by tools/delegate.py
    # _route_runner; read by runners/agy_local.py (PLAN-auto-dispatch Q1b).
    ("runner_model", "TEXT"),
]

# `hosts` probe columns added for PLAN-auto-dispatch H1 (task-25c272ce). Same
# forward-only ALTER-TABLE pattern as _MIGRATION_COLUMNS, applied in
# init_schema() on top of both SCHEMA (SQLite) and db_pg.PG_SCHEMA (Postgres),
# so an old ledger gains them on its next init(). NULL = "never probed with
# this field", never "zero". Read by the future lib/router.pick_host (H2).
#   cpus           os.cpu_count() of the box
#   load_per_core  1-minute loadavg divided by cpus, NULL on Windows
#   runners        JSON array of the CLIs found on PATH, e.g. ["claude","codex"]
_HOSTS_MIGRATION = [
    ("cpus", "INTEGER"),
    ("load_per_core", "REAL"),
    ("runners", "TEXT"),
]

# hosts columns for hq join (W4.1), a separate list so the probe migration
# above keeps naming exactly its own columns (tests/test_h1_node_probe.py pins
# that). Applied by the same loop in init_schema().
#   pubkey       the node's age X25519 recipient, set only by tools/hq_join
#                accept. The W4.2 Infisical client secret is sealed to it.
#                NULL = not a joined node (mac/contabo/winbox).
#   config_json  the hosts.yaml entry as JSON, written by seed_hosts_from_config
#                and by hq_join accept. `hq_join export-hosts` rebuilds
#                hosts.yaml from it.
#   deploy_pubkey  (W4.2) the node's ssh-ed25519 public key line for its GitHub
#                deploy key, set by hq_join accept --deploy-pubkey. Its own
#                column, not config_json, so it never leaks into the hosts.yaml
#                export. NULL = the node gets no deploy key.
#   approved_at  (W4.6a, F1) when an operator matched the node's key fingerprint
#                (`hq_join approve`). NULL = not approved: provision skips the
#                row. Reset to NULL when a `left` host joins again.
_HOSTS_JOIN_MIGRATION = [
    ("pubkey", "TEXT"),
    ("config_json", "TEXT"),
    ("deploy_pubkey", "TEXT"),
    ("approved_at", "TEXT"),
]

# letters.from_host (W2.4): which host (config/hosts.yaml key) sent the letter.
# On a shared ledger every host's watchdog sees every pending letter; retrying
# only the ones it sent keeps two boxes from both dialling deliver_letter for
# the same row. Same forward-only ALTER pattern as _HOSTS_MIGRATION, on top of
# both SCHEMA and db_pg.PG_SCHEMA (no PG_SCHEMA change: the loop covers it).
# A row written before this column has from_host NULL and is retried by nobody.
_LETTERS_MIGRATION = [
    ("from_host", "TEXT"),
]

# c_level_sessions lifecycle columns (task-728e4741). Same forward-only
# ALTER-TABLE pattern as _MIGRATION_COLUMNS above, applied in init() so the
# existing 76-row DB migrates without a migration framework. `status` carries
# a constant DEFAULT so SQLite backfills every existing row with 'open'
# the moment the column is added — no row-by-row fixup needed.
#
# host/charter (task-9ff9263f): host is the config/hosts.yaml key (mac/
# winbox/contabo) the session was spawned on — NULL on every pre-migration
# row, which tools/session_reconcile.py treats as "legacy, check on this
# machine" rather than "unknown, skip". charter is created here but left
# unused on purpose — the next task (the charter gate) owns its logic.
_C_LEVEL_SESSION_MIGRATION = [
    ("status", "TEXT NOT NULL DEFAULT 'open'"),
    ("closed_at", "TEXT"),
    ("note", "TEXT"),
    ("resume_uuid", "TEXT"),
    ("host", "TEXT"),
    ("charter", "TEXT"),
]

# Statuses where touched paths are no longer being modified — release locks.
RELEASING_STATUSES = {"review", "done", "failed", "cancelled", "stalled",
                      "blocked_host"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def redact_url(url: str | None) -> str | None:
    """`url` with any password in its userinfo replaced by `***`, for printing.
    `postgresql://org:<password>@host/db` -> `postgresql://org:***@host/db`.
    Every place that prints or logs the hub URL goes through this: the init
    banner once put the hub password into a session transcript (2026-10-01)."""
    if not url:
        return url
    return re.sub(r"(://[^:/@]*):[^@/]*@", r"\1:***@", url)


def pg_url() -> str | None:
    """ORG_DB_URL, stripped, or None when unset/blank -- the one switch
    between the SQLite and Postgres backends (docs/design/tasks-db-hub.md)."""
    url = os.environ.get("ORG_DB_URL")
    return url.strip() if url and url.strip() else None


def _connect(*, timeout: float | None = None, readonly: bool = False,
             path: str | Path | None = None) -> sqlite3.Connection:
    """SQLite connection -- unchanged behaviour from before the Postgres
    backend existed, plus three additive options no pre-existing caller
    passes (so every pre-existing call site is byte-for-byte unaffected):

      timeout  -- sqlite3's own busy-timeout; also threaded into the pg
                  branch of get_conn() as connect_timeout, so a single
                  kwarg gives both backends a fail-open budget.
      readonly -- open `file:<path>?mode=ro` instead of read-write, and
                  never create the file. Raises FileNotFoundError up front
                  if it doesn't exist (a caller like the self-repo-guard
                  hook needs "not found" distinguished from "found but
                  unreadable").
      path     -- connect to this file instead of the module's own
                  DB_PATH. Lets a caller address a *specific* checkout's
                  tasks.db (scripts/hook-self-repo-guard.py, which resolves
                  a DEV worktree's own hub root) without trusting this
                  process's ORG_ROOT/__file__ resolution -- and lets its
                  tests inject a throwaway fixture path. Ignored entirely
                  under the Postgres backend, which is one global registry
                  regardless of which checkout asks (see get_conn).
    """
    db_path = Path(path) if path is not None else DB_PATH
    if db_path.is_dir():
        raise ArchivedDB(ARCHIVED_TASKS_DB_MSG)
    if os.environ.get("PYTEST_CURRENT_TEST") and (
        db_path.parent.parent / ".git"
    ).exists():
        # ADR 0021 addendum (2026-09-18): a test process inherits whatever
        # ORG_ROOT its shell carries -- a worker's own shell sets it to the
        # real hub checkout (runners/worker_init.py) -- so a test that
        # doesn't monkeypatch DB_PATH/path to a tmp location would otherwise
        # silently open the real tasks.db (29 test-proj rows + 13 events
        # landed there this way). A real checkout/worktree always has a
        # `.git` entry (file for a worktree's gitdir pointer, dir for a full
        # clone); a tmp_path fixture never does.
        raise RuntimeError(
            "tests must not touch a real checkout's tasks.db (ADR 0021)"
        )
    kwargs = {"timeout": timeout} if timeout is not None else {}
    if readonly:
        if not db_path.exists():
            raise FileNotFoundError(f"tasks.db not found at {db_path}")
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, **kwargs)
        conn.row_factory = sqlite3.Row
        return conn
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), **kwargs)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


# ---------------------------------------------------------------------------
# Snapshot fallback (Org Mesh W1.7) -- reads keep working off SNAPSHOT_PATH
# when ORG_DB_URL is set but the hub can't be reached; writes fail loudly.
# ---------------------------------------------------------------------------

SNAPSHOT_META_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshot_meta (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    exported_at TEXT NOT NULL
);
"""


def init_snapshot_meta(conn) -> None:
    """Create the one-row snapshot_meta table on an already-open sqlite3
    connection. Separate from SCHEMA/init_schema -- this table exists only
    in a hub *export* (scripts/hub/export_to_sqlite.py), never in the
    canonical tasks.db or the Postgres hub itself."""
    conn.executescript(SNAPSHOT_META_SCHEMA)


def write_snapshot_meta(conn, exported_at: str) -> None:
    conn.execute(
        "INSERT INTO snapshot_meta (id, exported_at) VALUES (1, ?) "
        "ON CONFLICT(id) DO UPDATE SET exported_at=excluded.exported_at",
        (exported_at,),
    )


def read_snapshot_meta(path: Path) -> str | None:
    """`exported_at` from a snapshot file's meta table, or None if the file
    doesn't exist, has no meta row, or can't be read for any reason. Never
    raises -- callers treat None as "no usable snapshot"."""
    if not path.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
        try:
            row = conn.execute(
                "SELECT exported_at FROM snapshot_meta WHERE id=1"
            ).fetchone()
        finally:
            conn.close()
    except Exception:
        return None
    return row[0] if row else None


def _snapshot_age_desc(exported_at: str) -> str:
    """Short human-readable age ('42s', '7m', '3h'), or 'unknown age' if
    `exported_at` can't be parsed -- used only for the fallback warning."""
    try:
        exported = datetime.fromisoformat(exported_at)
        secs = int((datetime.now(timezone.utc) - exported).total_seconds())
    except Exception:
        return "unknown age"
    if secs < 120:
        return f"{secs}s"
    mins = secs // 60
    if mins < 120:
        return f"{mins}m"
    return f"{mins // 60}h"


# Warn once per (process, url) -- a module-level set rather than a bool so
# tests can reset it (monkeypatch.setattr(db, "_SNAPSHOT_FALLBACK_WARNED",
# set())) without it leaking across test functions in the same process.
_SNAPSHOT_FALLBACK_WARNED: set[str] = set()


class _SnapshotConnection:
    """Wraps a read-only sqlite3 connection to SNAPSHOT_PATH so it can stand
    in for the live hub connection get_conn() would otherwise hand back.

    Reads pass straight through. A write attempt hits sqlite3's own
    'attempt to write a readonly database' OperationalError -- translated
    here into a clear HubUnavailable naming the snapshot's age, instead of
    a caller having to recognise a raw sqlite error string.
    """

    def __init__(self, conn: sqlite3.Connection, exported_at: str):
        self._conn = conn
        self._exported_at = exported_at

    def _unavailable(self, exc: Exception) -> HubUnavailable:
        return HubUnavailable(
            f"hub unreachable; read-only snapshot from {self._exported_at}"
        )

    def execute(self, sql, params=()):
        try:
            return self._conn.execute(sql, params)
        except sqlite3.OperationalError as exc:
            if "readonly database" in str(exc):
                raise self._unavailable(exc) from exc
            raise

    def executemany(self, sql, seq_of_params):
        try:
            return self._conn.executemany(sql, seq_of_params)
        except sqlite3.OperationalError as exc:
            if "readonly database" in str(exc):
                raise self._unavailable(exc) from exc
            raise

    def executescript(self, script):
        try:
            return self._conn.executescript(script)
        except sqlite3.OperationalError as exc:
            if "readonly database" in str(exc):
                raise self._unavailable(exc) from exc
            raise

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def _open_snapshot_fallback(url: str, cause: Exception,
                            timeout: float | None) -> _SnapshotConnection:
    """The hub connect just failed for `url` -- open SNAPSHOT_PATH read-only,
    or raise HubUnavailable if there's nothing usable to fall back to."""
    exported_at = read_snapshot_meta(SNAPSHOT_PATH)
    if exported_at is None:
        raise HubUnavailable(
            f"hub unreachable ({cause}) and no read-only snapshot at "
            f"{SNAPSHOT_PATH} -- run scripts/hub/export_to_sqlite.py once "
            f"the hub is reachable"
        ) from cause
    if url not in _SNAPSHOT_FALLBACK_WARNED:
        _SNAPSHOT_FALLBACK_WARNED.add(url)
        print(
            f"[db] WARNING: ORG_DB_URL hub unreachable ({cause}) -- falling "
            f"back to read-only snapshot {SNAPSHOT_PATH}, exported "
            f"{exported_at} ({_snapshot_age_desc(exported_at)} old)",
            file=sys.stderr,
        )
    conn = sqlite3.connect(
        f"file:{SNAPSHOT_PATH}?mode=ro", uri=True,
        timeout=timeout if timeout is not None else HUB_CONNECT_TIMEOUT_S,
    )
    conn.row_factory = sqlite3.Row
    return _SnapshotConnection(conn, exported_at)


@contextmanager
def get_conn(*, timeout: float | None = None, readonly: bool = False,
             path: str | Path | None = None):
    """Commit on clean exit, rollback on exception -- same transactional
    contract regardless of backend (the reason Postgres was chosen over
    alternatives that couldn't keep it, per the design doc).

    SQLite: a fresh connection per call, closed always (unchanged). Postgres:
    a pooled connection reused across calls on this (process, thread) -- see
    db_pg.get_pooled -- so it is NOT closed here; a connection found dead is
    evicted instead (db_pg.evict) so the next call opens fresh.

    timeout/readonly/path: see _connect's docstring for the SQLite meaning.
    Under Postgres (ORG_DB_URL set) `readonly`/`path` are no-ops when the hub
    itself answers -- a single global registry has no per-checkout path to
    distinguish -- and `timeout` becomes psycopg's connect_timeout, defaulting
    to HUB_CONNECT_TIMEOUT_S (3s) rather than psycopg's own 10s when the
    caller doesn't pass one, so a down hub fails over quickly.

    Snapshot fallback (Org Mesh W1.7, docs/design/org-mesh.md): if the hub
    connect itself fails (HubConnectError -- psycopg OperationalError or the
    connect timeout), this opens SNAPSHOT_PATH read-only instead and hands
    back a connection reads work against transparently. `readonly`/`path`
    are no-ops here too -- the snapshot is always opened read-only regardless
    of what the caller asked for, because a write cannot land anywhere real.
    Any write attempted against it raises HubUnavailable. No snapshot file
    (or one with no meta row) raises HubUnavailable immediately instead.
    """
    url = pg_url()
    is_snapshot = False
    if url:
        # One pooled connection per (process, thread, url) -- see
        # db_pg.get_pooled's docstring. Never closed in `finally` below (that
        # would defeat the pool); evicted instead when it turns out to be
        # dead, so the *next* acquisition opens fresh.
        pg_timeout = timeout if timeout is not None else HUB_CONNECT_TIMEOUT_S
        try:
            conn = db_pg.get_pooled(url, timeout=pg_timeout)
        except db_pg.HubConnectError as exc:
            conn = _open_snapshot_fallback(url, exc, timeout)
            is_snapshot = True
    else:
        conn = _connect(timeout=timeout, readonly=readonly, path=path)
    try:
        yield conn
        conn.commit()
    except Exception as exc:
        if url and not is_snapshot and db_pg.is_operational_error(exc):
            # Connection is dead (dropped/closed) -- rollback would just
            # raise the same error again. Evict so the next get_conn() call
            # opens a fresh one instead of reusing a broken connection.
            db_pg.evict(url)
        else:
            conn.rollback()
        raise
    finally:
        if not url or is_snapshot:
            conn.close()


def sqlite_connect(path: str | Path, *, row_factory: bool = True,
                    timeout: float | None = None,
                    readonly: bool = False) -> sqlite3.Connection:
    """Plain SQLite connection, ALWAYS SQLite regardless of ORG_DB_URL --
    for a database other than the task registry (lib.ceo_report's
    relay_queue.db, lib.session_search's FTS index), or for a specific
    SQLite tasks.db file scripts/migrate_tasks_db.py needs to read as the
    *source* of a migration even while ORG_DB_URL names the *target*
    (get_conn() would be backend-switching and wrong for that read).
    Centralises the literal sqlite3.connect() call here so every such call
    in the codebase lives in this one file (see scripts/migrate_tasks_db
    .py's acceptance grep in the task brief)."""
    kwargs = {"timeout": timeout} if timeout is not None else {}
    if readonly:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, **kwargs)
    else:
        conn = sqlite3.connect(str(path), **kwargs)
    if row_factory:
        conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn, *, is_pg: bool) -> None:
    """Create schema + run forward-only column migrations on an already-open
    `conn`. Idempotent. Split out of init() (task-78586938) so
    scripts/migrate_tasks_db.py can initialise a specific --to target that
    `get_conn()`/ORG_DB_URL may not point at, reusing this exact column list
    instead of hand-duplicating it."""
    conn.executescript(db_pg.PG_SCHEMA if is_pg else SCHEMA)
    conn.executescript(JOIN_TOKENS_SCHEMA)
    conn.executescript(NODE_SECRETS_SCHEMA)
    existing = {r["name"] for r in conn.execute(
        "PRAGMA table_info(tasks)").fetchall()}
    for col, coltype in _MIGRATION_COLUMNS:
        if col not in existing:
            conn.execute(f"ALTER TABLE tasks ADD COLUMN {col} {coltype}")
    # W8 (audit 2026-08-06, reference/2026-08-06-agents-system-audit.md):
    # claudesign_project_id was added out-of-band, was never wired into
    # _MIGRATION_COLUMNS/VALID_COLUMNS, has zero code references and zero
    # non-null values across every row. Drop it. Guarded by the same
    # existence check the ADD-COLUMN loop uses above, so this is
    # idempotent — safe to run twice, and safe on a DB where the column
    # is already gone (fresh db.init() never had it to begin with).
    if "claudesign_project_id" in existing:
        conn.execute("ALTER TABLE tasks DROP COLUMN claudesign_project_id")
    # c_level_sessions lifecycle (task-728e4741): idempotent ADD COLUMN so
    # the existing 76-row DB gains status/closed_at/note/resume_uuid on the
    # next init(). CREATE TABLE IF NOT EXISTS above is a no-op against a
    # pre-existing table, so the ALTERs are what actually carry an old DB
    # forward. status's DEFAULT 'open' backfills every existing row.
    cls_existing = {r["name"] for r in conn.execute(
        "PRAGMA table_info(c_level_sessions)").fetchall()}
    for col, coltype in _C_LEVEL_SESSION_MIGRATION:
        if col not in cls_existing:
            conn.execute(
                f"ALTER TABLE c_level_sessions ADD COLUMN {col} {coltype}")
    hosts_existing = {r["name"] for r in conn.execute(
        "PRAGMA table_info(hosts)").fetchall()}
    for col, coltype in _HOSTS_MIGRATION + _HOSTS_JOIN_MIGRATION:
        if col not in hosts_existing:
            conn.execute(f"ALTER TABLE hosts ADD COLUMN {col} {coltype}")
    letters_existing = {r["name"] for r in conn.execute(
        "PRAGMA table_info(letters)").fetchall()}
    for col, coltype in _LETTERS_MIGRATION:
        if col not in letters_existing:
            conn.execute(f"ALTER TABLE letters ADD COLUMN {col} {coltype}")
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


def init():
    """Create schema. Idempotent. Also runs forward-only column migrations
    for tables that predate _MIGRATION_COLUMNS."""
    with get_conn() as conn:
        init_schema(conn, is_pg=bool(pg_url()))
    print(f"[db] initialized at {redact_url(pg_url()) or DB_PATH}")


def new_task_id() -> str:
    return "task-" + uuid.uuid4().hex[:8]


# --- Web Designer spawn guard (CEO 2026-06-04) -----------------------------
# A web_designer agent works in a git worktree that omits the gitignored
# claudesign .od/ dir, so it cannot resolve a project ID to its design on its
# own. Every web_designer task must carry the Project ID + design-source path
# in its description; the kickoff is then enriched with the resolved
# name/skill/path. See playbooks/web-designer.md §9 + memory
# designer-spawn-inputs.
_DESIGNER_ROLE = "web_designer"
UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_od_root_warned = False


def _od_root() -> Path | None:
    """claudesign's gitignored .od dir on THIS host: $CLAUDESIGN_OD_ROOT, else
    the mooniex-claudesign checkout config/projects.yaml lists for this host.
    None when the host has no checkout: designer context is then off, with one
    stderr warning per process. Looked up per call, never at import (lib.config
    needs PyYAML and a resolvable host)."""
    global _od_root_warned
    override = os.environ.get("CLAUDESIGN_OD_ROOT")
    if override:
        return Path(override)
    try:
        from lib.config import project_path_for_host, self_host
        return Path(project_path_for_host("mooniex-claudesign", self_host())) / ".od"
    except Exception as e:
        if not _od_root_warned:
            _od_root_warned = True
            print(f"[db] claudesign .od root not resolvable here ({e}); "
                  f"designer design refs are off", file=sys.stderr)
        return None


def resolve_od_project(project_id: str) -> dict | None:
    """Resolve a claudesign (open-design) project UUID to name/skill/paths by
    reading the local, gitignored .od/app.sqlite. Returns None if unavailable
    (no claudesign checkout on this host, missing file, no matching row, or any
    read error) — never raises."""
    od_root = _od_root()
    if od_root is None:
        return None
    db_file = od_root / "app.sqlite"
    if not db_file.exists():
        return None
    try:
        con = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True, timeout=5)
        con.row_factory = sqlite3.Row
        row = con.execute(
            "SELECT name, skill_id FROM projects WHERE id=? LIMIT 1",
            (project_id,),
        ).fetchone()
        con.close()
    except Exception:
        return None
    if not row:
        return None
    pdir = od_root / "projects" / project_id
    skill = row["skill_id"] or ""
    design = pdir / ".od-skills" / skill / "example.html"
    return {
        "id": project_id,
        "name": row["name"],
        "skill": skill,
        "dir": str(pdir),
        "design_path": str(design if design.exists() else pdir),
    }


def validate_designer_context(role: str, description: str) -> None:
    """Enforce that a web_designer task carries a Project ID + design-source
    path so the agent can locate the design. Raises ValueError otherwise.
    No-op for every other role."""
    if role != _DESIGNER_ROLE:
        return
    desc = description or ""
    has_id = bool(UUID_RE.search(desc))
    has_src = ".od/projects/" in desc
    if has_id and has_src:
        return
    missing = []
    if not has_id:
        missing.append("Project ID (UUID)")
    if not has_src:
        missing.append("design-source path (…/.od/projects/{ID}/)")
    raise ValueError(
        "web_designer task description must include "
        + " + ".join(missing)
        + ". See playbooks/web-designer.md §9 (designer spawn inputs)."
    )


def designer_kickoff_suffix(description: str) -> str:
    """Resolved design context to append to a web_designer kickoff, or "" if the
    description has no UUID or the project can't be resolved on this machine."""
    m = UUID_RE.search(description or "")
    if not m:
        return ""
    info = resolve_od_project(m.group(0))
    if not info:
        return ""
    return (
        f"\n[design] Project: {info['name']} ({info['id']}) · skill: {info['skill']}"
        f"\n[design] ref (READ-ONLY): {info['design_path']}"
        f"\n[design] อ่านดีไซน์จาก path นี้เป็น reference — ห้ามเขียนทับใน .od/ (gitignored, local)"
    )


def resolve_session_owner(
    owner_cto: str | None = None, owner_role: str | None = None
) -> tuple[str | None, str | None]:
    """Resolve (owner_cto, owner_role) from explicit args, else the env vars a
    spawned C-level session carries:
      owner_cto  = CTO_SESSION_ID (cto sessions) or CXO_SESSION_ID (cfo/cmo/…)
      owner_role = CXO_ROLE, else 'cto' when CTO_SESSION_ID is present
    so a CFO-spawned task routes to the CFO tab (cfo-<id>.winid), not a CTO.
    Shared by create_task's ownership stamp and tools/session_charter.py so
    both agree on which c_level_sessions row a session is."""
    if owner_cto is None:
        owner_cto = os.environ.get("CTO_SESSION_ID") or os.environ.get("CXO_SESSION_ID")
    if owner_role is None:
        owner_role = os.environ.get("CXO_ROLE") or (
            "cto" if os.environ.get("CTO_SESSION_ID") else None
        )
    return owner_cto, owner_role


def _require_charter(owner_cto: str, owner_role: str | None,
                      conn: sqlite3.Connection) -> None:
    """Charter gate (task-a63759d5, IRON-RULES §35): a C-level session must
    have set a one-line charter via tools/session_charter.py before it may
    create tasks. /session-open alone can't enforce this — that skill never
    writes to the DB, so it was skippable; this is the code-level version,
    same lesson as the merge gate (a rule that isn't code isn't a rule).

    Only called when owner_cto is truthy — the ownerless path (ad-hoc rows,
    tests without a session env) is unchanged in create_task below."""
    if os.environ.get("ORG_CHARTER_GATE", "").strip().lower() == "off":
        print(
            f"[db] WARNING: ORG_CHARTER_GATE=off — charter gate skipped for "
            f"session ({owner_role}, {owner_cto}). Escape hatch for setup/repair "
            f"only — never for production task creation.",
            file=sys.stderr,
        )
        return
    # sqlite3.OperationalError ("no such column") and its Postgres equivalent
    # (psycopg.errors.UndefinedColumn, message "column ... does not exist")
    # both mean the same thing here: a DB that predates the `charter` column.
    # psycopg is imported lazily via db_pg.psycopg (may be None when
    # ORG_DB_URL is unset) so this module never requires it to be installed.
    _missing_column_errors = [sqlite3.OperationalError]
    if db_pg.psycopg is not None:
        _missing_column_errors.append(db_pg.psycopg.errors.UndefinedColumn)
    try:
        row = conn.execute(
            "SELECT charter FROM c_level_sessions WHERE role=? AND session_id=?",
            (owner_role, owner_cto),
        ).fetchone()
    except tuple(_missing_column_errors) as e:
        msg = str(e)
        if "no such column" not in msg and "does not exist" not in msg:
            raise
        # A box that pulled the code but whose DB predates the `charter`
        # column: the gate must still fail closed, but with the fix in the
        # message instead of a bare sqlite error (Contabo, 2026-09-17).
        raise RuntimeError(
            "charter gate: this tasks.db predates the `charter` column, so the "
            "gate cannot check anything. Apply the pending migration once — "
            "python3 -c 'import sys; sys.path.insert(0, \".\"); from lib import db; db.init()' "
            "— then set the charter: python3 -m tools.session_charter set "
            '"<one-line entry problem>". '
            f"(underlying error: {e})"
        ) from e
    charter = (row["charter"] if row else None) or ""
    if not charter.strip():
        raise RuntimeError(
            f"session ({owner_role}, {owner_cto}) has no charter set — cannot "
            f"create a task. Run /session-open, then set one: "
            f'python3 -m tools.session_charter set "<one-line entry problem>". '
            f"Escape hatch for setup/repair only: ORG_CHARTER_GATE=off."
        )


def create_task(
    project: str,
    role: str,
    title: str,
    description: str,
    parent_task: str | None = None,
    depends_on: list[str] | None = None,
    touches: list[str] | None = None,
    owner_cto: str | None = None,
    owner_role: str | None = None,
    host: str | None = None,
    runner: str | None = None,
) -> str:
    validate_designer_context(role, description)
    # Stamp the spawning C-level session so DEV reports route back to that
    # session's tab instead of broadcasting to every open CTO chat.
    owner_cto, owner_role = resolve_session_owner(owner_cto, owner_role)
    tid = new_task_id()
    if not owner_cto:
        # Don't hard-fail (tests + ad-hoc rows create ownerless tasks), but make
        # the orphaned-report consequence loud so it isn't silently shipped.
        print(
            f"[db] WARNING: creating ownerless task {tid} — reports will be "
            f"orphaned (no CTO_SESSION_ID/CXO_SESSION_ID in env, no explicit owner)",
            file=sys.stderr,
        )
    # Stamped on every insert (docs/design/org-mesh.md C1, W0.1): which host
    # this session is filing the task from. Never caught -- a self_host()
    # failure here must fail the create loudly, not silently write a wrong
    # or guessed dispatcher_host (task brief rule 7).
    from lib import config
    dispatcher_host = config.self_host()
    ts = now_iso()
    with get_conn() as conn:
        if owner_cto:
            _require_charter(owner_cto, owner_role, conn)
        conn.execute(
            """INSERT INTO tasks (id,project,role,status,title,description,parent_task,depends_on,touches,owner_cto,owner_role,host,dispatcher_host,runner,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (tid, project, role, "pending", title, description, parent_task,
             json.dumps(depends_on or []), json.dumps(touches or []), owner_cto, owner_role, host, dispatcher_host, runner, ts, ts),
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
    "tmux_session", "ttyd_port", "ttyd_pid", "owner_cto", "owner_role",
    "delegate_log", "spawned_at", "host", "dispatcher_host", "runner",
    "runner_model",
}


# Terminal "work landed" statuses that must not be silently resurrected into
# an active (lock-holding) status. Resurrecting one is what left phantom path
# locks after a successful merge — see issue #13. The active set is
# ACTIVE_STATUSES (pending/in_progress/rate_limited/conflict/queued_remote).
_TERMINAL_MERGED = ("done", "merged")


def update_status(task_id: str, status: str, *, actor: str = "system",
                  force: bool = False, **fields) -> bool:
    """Set a task's status (+ optional columns). Returns True if a row changed.

    Terminal-guard (issue #13): a task already in 'done'/'merged' is NOT
    resurrected into an active status (pending/in_progress/conflict/
    rate_limited) by a racing or duplicate op — that flipped an already-merged
    task to 'conflict' (a git-conflict re-merge or a re-delegate), and because
    'conflict' is active, find_conflicts then reported a phantom self-collision
    that blocked every future task on the same paths. Pass force=True for an
    intentional resurrection (reopen_task / revert_task). Returns False when the
    guard refuses the transition.
    """
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

    # Atomic terminal-guard: fold the "don't resurrect done/merged" check into
    # the UPDATE's WHERE so two concurrent CTOs can't both pass a read-then-write
    # gate. Only active (lock-holding) target statuses are guarded.
    guard_sql = ""
    guard_vals: list = []
    if not force and status in ACTIVE_STATUSES:
        placeholders = ",".join("?" * len(_TERMINAL_MERGED))
        guard_sql = f" AND status NOT IN ({placeholders})"
        guard_vals = list(_TERMINAL_MERGED)

    with get_conn() as conn:
        cur = conn.execute(
            f"UPDATE tasks SET {','.join(sets)} WHERE id=?{guard_sql}",
            vals + guard_vals,
        )
        if cur.rowcount == 0 and guard_sql:
            row = conn.execute(
                "SELECT status FROM tasks WHERE id=?", (task_id,)
            ).fetchone()
            if row is not None:
                log_event(conn, task_id, actor, "status_transition_refused",
                          {"from": row["status"], "to": status,
                           "guard": "terminal_merged"})
                print(f"[db] refused {task_id}: {row['status']} -> {status} "
                      f"(terminal-merged guard; pass force=True to override)",
                      file=sys.stderr)
                return False
        log_event(conn, task_id, actor, f"status_{status}", fields)
    if status in RELEASING_STATUSES:
        try:
            t = get_task(task_id)
            if t:
                release_task_locks(task_id, t["project"])
        except Exception:
            pass
    return True


def set_fields(task_id: str, *, actor: str = "system", **fields) -> None:
    """Update task columns WITHOUT touching status.

    delegate.py needs this after tmux/ttyd boot: by then the DEV inside the
    tmux session may already have claimed the task (pending → in_progress),
    and an update_status(..., 'pending') here would silently regress it."""
    if not fields:
        return
    bad = set(fields) - VALID_COLUMNS
    if bad:
        raise ValueError(f"unknown column(s): {bad}")
    ts = now_iso()
    sets = ["updated_at=?"]
    vals: list = [ts]
    for k, v in fields.items():
        sets.append(f"{k}=?")
        vals.append(v)
    vals.append(task_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE tasks SET {','.join(sets)} WHERE id=?", vals)
        log_event(conn, task_id, actor, "fields_set", fields)


def get_task(task_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    return dict(row) if row else None


def list_tasks(status: str | None = None, project: str | None = None,
               role: str | None = None, owner_cto: str | None = None,
               limit: int = 100) -> list[dict]:
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
    if owner_cto:
        q += " AND owner_cto=?"
        args.append(owner_cto)
    q += " ORDER BY updated_at DESC LIMIT ?"
    args.append(limit)
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(q, args).fetchall()]


def unmet_dependencies(depends_on: list[str]) -> list[dict]:
    """Return the subset of `depends_on` task ids that have not reached a
    terminal-merged state (W3, audit 2026-08-06). "Finished" means
    status in _TERMINAL_MERGED ("done" or "merged") — matching every other
    terminal-state check in this module (update_status's guard, revert_task,
    reflect.py), not just "done" alone.

    A dependency id that no longer resolves to a row is reported as unmet
    ("missing") rather than silently treated as satisfied — a typo'd or
    deleted dependency id must not silently unblock the dependent task.
    """
    unmet = []
    for dep_id in depends_on:
        t = get_task(dep_id)
        status = t["status"] if t else "missing"
        if status not in _TERMINAL_MERGED:
            unmet.append({"id": dep_id, "status": status})
    return unmet


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


# queued_remote is active: its path locks stay held while it waits for the host,
# and it must not join the terminal-surface sweep (VALID_STATUS - ACTIVE_STATUSES).
ACTIVE_STATUSES = ("pending", "in_progress", "rate_limited", "conflict",
                   "queued_remote")


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


# Alias for external callers that prefer the db_conn name.
db_conn = get_conn


# ---------------------------------------------------------------------------
# c_level_sessions helpers
# ---------------------------------------------------------------------------

def register_cxo_session(role: str, session_id: str, host: str | None = None) -> None:
    """Upsert a c_level_sessions row at spawn. `host` (config/hosts.yaml key)
    is optional so every pre-existing caller keeps working unchanged; when
    given on a re-register it overwrites, when omitted the existing column
    value (if any) is kept rather than clobbered to NULL."""
    ts = now_iso()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO c_level_sessions (role, session_id, spawned_at, host)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(role, session_id) DO UPDATE SET
                 spawned_at=excluded.spawned_at,
                 host=COALESCE(excluded.host, c_level_sessions.host)""",
            (role, session_id, ts, host),
        )


def bind_session_to_task(role: str, session_id: str, task_id: str | None) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE c_level_sessions SET active_task_id=? WHERE role=? AND session_id=?",
            (task_id, role, session_id),
        )


# ---------------------------------------------------------------------------
# hosts (Org Mesh W2.1, docs/design/org-mesh.md C2/C3)
# ---------------------------------------------------------------------------

_HOST_COLUMNS = {
    "os", "hq_root", "agents_root", "provides", "max_workers", "status",
    "probed_at", "free_gb", "ram_free_gb", "running", "version",
    "cpus", "load_per_core", "runners", "pubkey", "config_json", "deploy_pubkey",
    "approved_at",
}


def upsert_host(host: str, **fields) -> None:
    """Insert or update one `hosts` row, touching ONLY the columns passed.

    A column left out of `fields` keeps its existing value -- this is what
    lets seed_hosts_from_config() (identity fields only) and a future
    node_agent heartbeat (probe fields only) both write the same row without
    either one clobbering the other's data. `provides` and `runners`, if
    given, are lists and get JSON-encoded for storage. `updated_at` is always
    stamped with now_iso(), even on a no-op reseed -- it means "last touched",
    not "last changed".
    """
    bad = set(fields) - _HOST_COLUMNS
    if bad:
        raise ValueError(f"unknown host column(s): {bad}")
    cols = dict(fields)
    for key in ("provides", "runners"):
        if cols.get(key) is not None:
            cols[key] = json.dumps(cols[key])
    cols["updated_at"] = now_iso()
    col_names = ["host", *cols.keys()]
    placeholders = ",".join("?" * len(col_names))
    updates = ", ".join(f"{c}=excluded.{c}" for c in cols)
    sql = (
        f"INSERT INTO hosts ({','.join(col_names)}) VALUES ({placeholders}) "
        f"ON CONFLICT(host) DO UPDATE SET {updates}"
    )
    with get_conn() as conn:
        conn.execute(sql, [host, *cols.values()])


def get_host(host: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM hosts WHERE host=?", (host,)).fetchone()
    return dict(row) if row else None


def list_hosts() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM hosts ORDER BY host").fetchall()
    return [dict(r) for r in rows]


def seed_hosts_from_config() -> None:
    """One `hosts` row per config/hosts.yaml entry -- os, agents_root,
    provides, max_workers, plus the whole entry as config_json (what
    `hq_join export-hosts` rebuilds hosts.yaml from). Never touches probe
    fields (status, probed_at, free_gb, ram_free_gb, running, version) --
    upsert_host only writes the columns it's given, so a live node's
    heartbeat data survives a reseed untouched. Idempotent: rerunning with
    an unchanged hosts.yaml leaves every seeded field the same.

    Seeds only what config/hosts.yaml itself declares. On a joined node
    lib.config.hosts() also carries an entry built from that node's own
    node.yaml; the hub's row for that node comes from `hq_join accept` and
    the node's own probe, and a reseed run there must never replace it.

    Imports lib.config lazily (pulls in PyYAML) so lib.db itself stays
    importable without it -- the PreToolUse hooks import lib.db under the
    system python3, which may not have PyYAML installed.
    """
    import yaml
    from lib import config
    declared = yaml.safe_load(config.HOSTS_CONFIG.read_text(encoding="utf-8"))["hosts"]
    for name, h in config.hosts().items():
        if name not in declared:
            continue
        upsert_host(
            name,
            os=h.get("os"),
            agents_root=h.get("agents_root"),
            provides=h.get("provides") or [],
            max_workers=h.get("max_workers"),
            config_json=json.dumps(h),
        )


# ---------------------------------------------------------------------------
# letters (Org Mesh W2.1 -- cross-host C-level mailbox, delivered by W2.2's
# `node_dispatch deliver_letter <id>`)
# ---------------------------------------------------------------------------

def create_letter(
    to_host: str,
    to_role: str,
    body: str,
    *,
    to_session: str | None = None,
    from_role: str | None = None,
    from_session: str | None = None,
    from_host: str | None = None,
) -> int:
    ts = now_iso()
    with get_conn() as conn:
        row = conn.execute(
            """INSERT INTO letters
                 (to_host,to_role,to_session,from_role,from_session,from_host,body,status,created_at,attempts)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               RETURNING id""",
            (to_host, to_role, to_session, from_role, from_session, from_host, body,
             "pending", ts, 0),
        ).fetchone()
    return row["id"]


def get_letter(letter_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM letters WHERE id=?", (letter_id,)
        ).fetchone()
    return dict(row) if row else None


def pending_letters(to_host: str, *, from_host: str | None = None) -> list[dict]:
    """Pending letters addressed to `to_host`. With `from_host`, only the ones
    that host sent (a row with from_host NULL matches nobody)."""
    sql = "SELECT * FROM letters WHERE to_host=? AND status='pending'"
    args: tuple = (to_host,)
    if from_host is not None:
        sql += " AND from_host=?"
        args = (to_host, from_host)
    with get_conn() as conn:
        rows = conn.execute(sql + " ORDER BY id", args).fetchall()
    return [dict(r) for r in rows]


def mark_letter_delivered(letter_id: int) -> bool:
    """Flip a letter to delivered. Returns False (no error) when it was
    already delivered -- the W2.2 `deliver_letter` caller must be idempotent
    against a retried delivery, this is the primitive that makes it so."""
    ts = now_iso()
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE letters SET status='delivered', delivered_at=? "
            "WHERE id=? AND status<>'delivered'",
            (ts, letter_id),
        )
        return bool(cur.rowcount)


def record_letter_attempt(letter_id: int, error: str) -> None:
    """Bump attempts, record `error` as last_error, and flip to `failed`
    once attempts reaches 5. Atomic per row (single UPDATE ... RETURNING) so
    two racing delivery attempts can't both read the same pre-increment
    count and under-count.

    Only a `pending` letter flips: a late count (a timeout while the far side
    delivered) must not turn a `delivered` row into `failed` (W2.7 F14,
    task-42fdcda7)."""
    with get_conn() as conn:
        row = conn.execute(
            "UPDATE letters SET attempts = attempts + 1, last_error = ? "
            "WHERE id = ? RETURNING attempts",
            (error, letter_id),
        ).fetchone()
        if row is not None and row["attempts"] >= 5:
            conn.execute(
                "UPDATE letters SET status='failed' WHERE id=? AND status='pending'",
                (letter_id,),
            )


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
