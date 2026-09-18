"""DB-touching tests run against a LOCAL Postgres (task-02ecbdea,
docs/design/tasks-db-hub.md §3.1).

Skipped with a clear reason when ORG_TEST_DB_URL is unset. When set, every
test in this module runs lib.db's normal SQL through the Postgres backend
(lib/db_pg.py) instead of SQLite -- same lib.db API, same assertions a
SQLite test would make, proving the dual backend actually works rather than
just "doesn't crash on import".

Setup (see REPORT.md for the exact commands used for this task):
    brew install postgresql@16
    initdb -D <scratch dir> -U postgres
    pg_ctl -D <scratch dir> -o "-p 54329 -k <short socket dir>" start
    createdb -h <short socket dir> -p 54329 -U postgres org_test
    ORG_TEST_DB_URL=postgresql://postgres@127.0.0.1:54329/org_test \\
        pytest tests/test_db_backend_pg.py -q

ADR 0021: no test touches real state. Every test here drops and recreates
its own schema in `org_test` (never `state/tasks.db`, never a production
Postgres database) before and after running.

Run via:  pytest tests/test_db_backend_pg.py
(not in pytest.ini's default `testpaths` — run explicitly, same convention
as tests/test_multihost.py.)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import lib.db_pg as db_pg  # noqa: E402
import scripts.migrate_tasks_db as migrate  # noqa: E402
from tools import session_charter  # noqa: E402

ORG_TEST_DB_URL = os.environ.get("ORG_TEST_DB_URL", "").strip()

pytestmark = pytest.mark.skipif(
    not ORG_TEST_DB_URL,
    reason=(
        "ORG_TEST_DB_URL not set -- needs a local Postgres 16 "
        "(brew install postgresql@16; initdb; pg_ctl start; createdb org_test; "
        "see REPORT.md for the exact commands used). Example: "
        "ORG_TEST_DB_URL=postgresql://postgres@127.0.0.1:54329/org_test "
        "pytest tests/test_db_backend_pg.py -q"
    ),
)

_TABLES = ("locks", "events", "tasks", "c_level_sessions")


def _drop_all(url: str) -> None:
    conn = db_pg.connect(url, timeout=10)
    try:
        for table in _TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def _pg_registry(monkeypatch):
    monkeypatch.setenv("ORG_DB_URL", ORG_TEST_DB_URL)
    monkeypatch.delenv("CTO_SESSION_ID", raising=False)
    monkeypatch.delenv("CXO_SESSION_ID", raising=False)
    monkeypatch.delenv("CXO_ROLE", raising=False)
    monkeypatch.delenv("ORG_CHARTER_GATE", raising=False)
    _drop_all(ORG_TEST_DB_URL)
    db_mod.init()
    yield
    _drop_all(ORG_TEST_DB_URL)


# ---------------------------------------------------------------------------
# schema / init
# ---------------------------------------------------------------------------

def test_init_creates_expected_columns():
    with db_mod.get_conn() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    # base columns + every _MIGRATION_COLUMNS entry
    for expected in ("id", "project", "role", "status", "touches",
                      "owner_cto", "host", "delegate_log", "spawned_at"):
        assert expected in cols, f"missing column {expected!r}: {cols}"


def test_init_is_idempotent():
    db_mod.init()
    db_mod.init()  # second run must not raise (duplicate column, etc.)
    with db_mod.get_conn() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    assert "host" in cols


# ---------------------------------------------------------------------------
# task lifecycle
# ---------------------------------------------------------------------------

def test_create_claim_update_get_list_roundtrip():
    tid = db_mod.create_task("projA", "developer", "t1", "d1")
    assert tid.startswith("task-")

    assert db_mod.claim_task(tid, "agent-1") is True
    assert db_mod.claim_task(tid, "agent-2") is False  # already claimed

    ok = db_mod.update_status(tid, "review", report="did the thing")
    assert ok is True

    t = db_mod.get_task(tid)
    assert t["status"] == "review"
    assert t["report"] == "did the thing"
    assert t["assigned_agent"] == "agent-1"

    rows = db_mod.list_tasks(project="projA")
    assert any(r["id"] == tid for r in rows)

    db_mod.set_fields(tid, review="lgtm")
    t2 = db_mod.get_task(tid)
    assert t2["review"] == "lgtm"
    assert t2["status"] == "review"  # set_fields never touches status


def test_terminal_guard_refuses_resurrection():
    tid = db_mod.create_task("projA", "developer", "t1", "d1")
    db_mod.update_status(tid, "done")
    resurrected = db_mod.update_status(tid, "in_progress")
    assert resurrected is False
    assert db_mod.get_task(tid)["status"] == "done"
    # force=True is the only way back to an active status
    assert db_mod.update_status(tid, "in_progress", force=True) is True
    assert db_mod.get_task(tid)["status"] == "in_progress"


def test_unmet_dependencies():
    dep = db_mod.create_task("projA", "developer", "dep", "d")
    main = db_mod.create_task("projA", "developer", "main", "d")
    unmet = db_mod.unmet_dependencies([dep])
    assert unmet == [{"id": dep, "status": "pending"}]
    db_mod.update_status(dep, "done")
    assert db_mod.unmet_dependencies([dep]) == []
    assert db_mod.unmet_dependencies(["task-doesnotexist"]) == [
        {"id": "task-doesnotexist", "status": "missing"}
    ]


# ---------------------------------------------------------------------------
# locks
# ---------------------------------------------------------------------------

def test_acquire_release_lock_contention():
    assert db_mod.acquire_lock("k1", "ownerA", ttl_seconds=600) is True
    assert db_mod.acquire_lock("k1", "ownerA", ttl_seconds=600) is True  # same owner ok
    assert db_mod.acquire_lock("k1", "ownerB", ttl_seconds=600) is False  # contested
    db_mod.release_lock("k1", "ownerA")
    assert db_mod.acquire_lock("k1", "ownerB", ttl_seconds=600) is True


def test_lock_paths_and_find_conflicts_and_release():
    tid = db_mod.create_task("projA", "developer", "t1", "d1", touches=["a/b.py"])
    ok, acquired, blocking = db_mod.lock_paths(tid, "projA", ["a/b.py", "c/d.py"])
    assert ok is True and len(acquired) == 2 and blocking == []

    other = db_mod.create_task("projA", "developer", "t2", "d2", touches=["a/b.py"])
    hits = db_mod.find_conflicts("projA", ["a/b.py"], exclude_task=other)
    assert any(h["task_id"] == tid for h in hits)

    n = db_mod.release_task_locks(tid, "projA")
    assert n == 2
    with db_mod.get_conn() as conn:
        remaining = conn.execute(
            "SELECT * FROM locks WHERE owner=?", (tid,)
        ).fetchall()
    assert remaining == []


def test_releasing_status_auto_releases_locks():
    tid = db_mod.create_task("projA", "developer", "t1", "d1")
    db_mod.lock_paths(tid, "projA", ["x/y.py"])
    db_mod.update_status(tid, "done")  # RELEASING_STATUSES
    with db_mod.get_conn() as conn:
        rows = conn.execute("SELECT * FROM locks WHERE owner=?", (tid,)).fetchall()
    assert rows == []


# ---------------------------------------------------------------------------
# c_level_sessions / charter gate
# ---------------------------------------------------------------------------

def test_register_and_bind_c_level_session():
    db_mod.register_cxo_session("cto", "ctoAAA", host="mac")
    db_mod.bind_session_to_task("cto", "ctoAAA", "task-fakebind")
    with db_mod.get_conn() as conn:
        row = conn.execute(
            "SELECT active_task_id, host FROM c_level_sessions "
            "WHERE role=? AND session_id=?", ("cto", "ctoAAA"),
        ).fetchone()
    assert row["active_task_id"] == "task-fakebind"
    assert row["host"] == "mac"

    # re-register without host keeps the existing one (COALESCE) -- proves
    # the ON CONFLICT ... EXCLUDED translation actually reached Postgres.
    db_mod.register_cxo_session("cto", "ctoAAA")
    with db_mod.get_conn() as conn:
        row2 = conn.execute(
            "SELECT host FROM c_level_sessions WHERE role=? AND session_id=?",
            ("cto", "ctoAAA"),
        ).fetchone()
    assert row2["host"] == "mac"


def test_charter_gate_blocks_then_passes(monkeypatch):
    monkeypatch.setenv("CTO_SESSION_ID", "ctotest1")
    db_mod.register_cxo_session("cto", "ctotest1")
    with pytest.raises(RuntimeError, match="has no charter set"):
        db_mod.create_task("projA", "developer", "t", "d")
    session_charter.set_charter("fix the leaderboard dedup bug end to end")
    tid = db_mod.create_task("projA", "developer", "t", "d")
    assert tid.startswith("task-")
    assert db_mod.get_task(tid)["owner_cto"] == "ctotest1"


# ---------------------------------------------------------------------------
# migrate_tasks_db.py round trip
# ---------------------------------------------------------------------------

def test_migrate_round_trip_counts(tmp_path, monkeypatch):
    src = tmp_path / "src_tasks.db"
    monkeypatch.delenv("ORG_DB_URL", raising=False)  # build the source in SQLite
    monkeypatch.setattr(db_mod, "DB_PATH", src)
    db_mod.init()
    t1 = db_mod.create_task("projA", "developer", "s1", "d1")
    t2 = db_mod.create_task("projA", "tester", "s2", "d2")
    db_mod.register_cxo_session("cto", "ctoSRC")
    db_mod.acquire_lock("proj:projA:path:z.py", "ownerZ", ttl_seconds=600)
    src_tasks = len(db_mod.list_tasks(limit=100))
    assert src_tasks == 2

    monkeypatch.setenv("ORG_DB_URL", ORG_TEST_DB_URL)  # target is the empty pg db

    rc = migrate.main(["--from", str(src), "--to", ORG_TEST_DB_URL, "--apply"])
    assert rc == 0

    with db_mod.get_conn() as conn:
        pg_tasks = conn.execute("SELECT COUNT(*) AS c FROM tasks").fetchone()["c"]
        pg_sessions = conn.execute(
            "SELECT COUNT(*) AS c FROM c_level_sessions").fetchone()["c"]
        pg_locks = conn.execute("SELECT COUNT(*) AS c FROM locks").fetchone()["c"]
    assert pg_tasks == 2
    assert pg_sessions == 1
    assert pg_locks == 1
    assert {t1, t2} == {r["id"] for r in db_mod.list_tasks(limit=100)}

    # idempotent re-run: DO NOTHING means the counts don't move
    rc2 = migrate.main(["--from", str(src), "--to", ORG_TEST_DB_URL, "--apply"])
    assert rc2 == 0
    with db_mod.get_conn() as conn:
        pg_tasks_again = conn.execute("SELECT COUNT(*) AS c FROM tasks").fetchone()["c"]
    assert pg_tasks_again == 2


def test_migrate_creates_schema_on_fresh_target(tmp_path, monkeypatch):
    """Reproduces the CTO's measured rehearsal failure: a target with no
    tables at all used to make _counts() silently print 0 for `tasks`, then
    the first real INSERT raised psycopg.errors.InFailedSqlTransaction. The
    _pg_registry fixture above already ran db_mod.init() against
    ORG_TEST_DB_URL, so drop everything again here to get a genuinely bare
    target before migrating into it."""
    _drop_all(ORG_TEST_DB_URL)

    src = tmp_path / "src_tasks.db"
    monkeypatch.delenv("ORG_DB_URL", raising=False)
    monkeypatch.setattr(db_mod, "DB_PATH", src)
    db_mod.init()
    tid = db_mod.create_task("projA", "developer", "s1", "d1")

    monkeypatch.setenv("ORG_DB_URL", ORG_TEST_DB_URL)
    rc = migrate.main(["--from", str(src), "--to", ORG_TEST_DB_URL, "--apply"])
    assert rc == 0

    with db_mod.get_conn() as conn:
        n = conn.execute("SELECT COUNT(*) AS c FROM tasks").fetchone()["c"]
    assert n == 1
    assert db_mod.get_task(tid) is not None


def test_migrate_advances_events_identity_sequence(tmp_path, monkeypatch):
    src = tmp_path / "src_tasks.db"
    monkeypatch.delenv("ORG_DB_URL", raising=False)
    monkeypatch.setattr(db_mod, "DB_PATH", src)
    db_mod.init()
    tid = db_mod.create_task("projA", "developer", "s1", "d1")
    for _ in range(5):
        db_mod.update_status(tid, "in_progress", force=True)  # more events rows

    monkeypatch.setenv("ORG_DB_URL", ORG_TEST_DB_URL)
    rc = migrate.main(["--from", str(src), "--to", ORG_TEST_DB_URL, "--apply"])
    assert rc == 0

    # Insert one more event through the *normal* lib.db API -- must not
    # collide with a copied-over id (measured failure item 3).
    with db_mod.get_conn() as conn:
        db_mod.log_event(conn, tid, "test", "post_migration_check", {})
    with db_mod.get_conn() as conn:
        n = conn.execute(
            "SELECT COUNT(*) AS c FROM events WHERE kind='post_migration_check'"
        ).fetchone()["c"]
    assert n == 1


def test_migrate_bad_row_default_aborts_and_reports_pk(tmp_path, monkeypatch, capsys):
    src = tmp_path / "src_tasks.db"
    monkeypatch.delenv("ORG_DB_URL", raising=False)
    monkeypatch.setattr(db_mod, "DB_PATH", src)
    db_mod.init()
    t1 = db_mod.create_task("projA", "developer", "s1", "d1")
    t2 = db_mod.create_task("projA", "developer", "s2", "d2")

    monkeypatch.setenv("ORG_DB_URL", ORG_TEST_DB_URL)

    real_execute = db_pg.Connection.execute

    def flaky_execute(self, sql, params=()):
        if "INSERT INTO tasks" in sql and params and params[0] == t2:
            raise RuntimeError("simulated constraint violation")
        return real_execute(self, sql, params)

    monkeypatch.setattr(db_pg.Connection, "execute", flaky_execute)

    rc = migrate.main(["--from", str(src), "--to", ORG_TEST_DB_URL, "--apply"])
    assert rc == 1

    captured = capsys.readouterr()
    assert "table=tasks" in captured.err
    assert t2 in captured.err

    # Default mode rolls back the whole table on any failing row -- t1 (which
    # copied fine before t2 blew up) must NOT have been left half-committed.
    with db_mod.get_conn() as conn:
        n = conn.execute("SELECT COUNT(*) AS c FROM tasks").fetchone()["c"]
    assert n == 0


def test_migrate_skip_bad_rows_continues_and_lists_skipped(tmp_path, monkeypatch, capsys):
    src = tmp_path / "src_tasks.db"
    monkeypatch.delenv("ORG_DB_URL", raising=False)
    monkeypatch.setattr(db_mod, "DB_PATH", src)
    db_mod.init()
    t1 = db_mod.create_task("projA", "developer", "s1", "d1")
    t2 = db_mod.create_task("projA", "developer", "s2", "d2")

    monkeypatch.setenv("ORG_DB_URL", ORG_TEST_DB_URL)

    real_execute = db_pg.Connection.execute

    def flaky_execute(self, sql, params=()):
        if "INSERT INTO tasks" in sql and params and params[0] == t2:
            raise RuntimeError("simulated constraint violation")
        return real_execute(self, sql, params)

    monkeypatch.setattr(db_pg.Connection, "execute", flaky_execute)

    rc = migrate.main(["--from", str(src), "--to", ORG_TEST_DB_URL,
                        "--apply", "--skip-bad-rows"])
    assert rc == 0

    captured = capsys.readouterr()
    assert "skipped 1 row(s)" in captured.out
    assert t2 in captured.out

    with db_mod.get_conn() as conn:
        ids = {r["id"] for r in conn.execute("SELECT id FROM tasks").fetchall()}
    assert ids == {t1}
