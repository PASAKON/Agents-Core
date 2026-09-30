"""Org Mesh W1.7 (docs/design/org-mesh.md, docs/design/tasks-db-hub.md §5):
the read-only snapshot fallback. When ORG_DB_URL is set but the Postgres hub
can't be reached, lib.db.get_conn() falls back to a local read-only SQLite
snapshot (state/tasks.snapshot.db, written by scripts/hub/export_to_sqlite.py)
instead of raising straight away -- reads keep working, writes fail loudly
with lib.db.HubUnavailable.

ADR 0021: no test here touches the real state/tasks.db, the real snapshot
path, or a real Postgres. Every test monkeypatches lib.db.SNAPSHOT_PATH (and
DB_PATH where relevant) to a tmp_path location, same convention as the
existing dual-backend tests (tests/test_db_backend_pg.py,
tests/test_ledger_direct_opens.py). Postgres-backed export tests run only
when ORG_TEST_DB_URL is set (see the `pg_only` marker below).

Run:  .venv/bin/python -m pytest tests/test_db_snapshot_fallback.py
"""
from __future__ import annotations

import importlib.util
import io
import json
import sqlite3
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import lib.db_pg as db_pg  # noqa: E402
import scripts.hub.export_to_sqlite as export_mod  # noqa: E402

ORG_TEST_DB_URL = __import__("os").environ.get("ORG_TEST_DB_URL", "").strip()
pg_only = pytest.mark.skipif(
    not ORG_TEST_DB_URL,
    reason=(
        "ORG_TEST_DB_URL not set -- needs a local Postgres 16 (see "
        "tests/test_db_backend_pg.py's module docstring for setup)."
    ),
)

# port 1 on loopback: nothing ever listens there, so a connect attempt fails
# fast with ECONNREFUSED -- same convention as tests/test_ledger_direct_opens
# .py's test_step4b_gate_postgres_url_set_skips_local_file_check.
UNREACHABLE_URL = "postgresql://baduser@127.0.0.1:1/baddb"


@pytest.fixture(autouse=True)
def _reset_snapshot_warning(monkeypatch):
    """_SNAPSHOT_FALLBACK_WARNED is process-global (by design -- 'one warning
    per process') so it must be reset before each test, or only the first
    test in the file to hit the fallback would ever see the warning."""
    monkeypatch.setattr(db_mod, "_SNAPSHOT_FALLBACK_WARNED", set())


def _build_snapshot(path: Path, *, exported_at: str,
                    tasks: list[dict] | None = None) -> None:
    """A minimal but real snapshot file: lib.db's own schema (init_schema,
    not a copy of the DDL) + the snapshot_meta table + whatever task rows
    the caller wants."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    db_mod.init_schema(conn, is_pg=False)
    db_mod.init_snapshot_meta(conn)
    now = db_mod.now_iso()
    for t in tasks or []:
        conn.execute(
            "INSERT INTO tasks (id,project,role,status,title,description,"
            "touches,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (t["id"], t.get("project", "projA"), t.get("role", "developer"),
             t.get("status", "pending"), t.get("title", "t"),
             t.get("description", "d"), json.dumps(t.get("touches", [])),
             now, now),
        )
    db_mod.write_snapshot_meta(conn, exported_at)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# lib.db.get_conn() fallback
# ---------------------------------------------------------------------------

def test_reads_come_from_snapshot_when_hub_unreachable(tmp_path, monkeypatch):
    monkeypatch.setenv("ORG_DB_URL", UNREACHABLE_URL)
    snap = tmp_path / "tasks.snapshot.db"
    monkeypatch.setattr(db_mod, "SNAPSHOT_PATH", snap)
    _build_snapshot(snap, exported_at="2026-09-29T00:00:00+00:00",
                    tasks=[{"id": "task-abc12345", "touches": ["a/b.py"]}])

    with db_mod.get_conn(readonly=True, timeout=1) as conn:
        row = conn.execute(
            "SELECT touches FROM tasks WHERE id=?", ("task-abc12345",)
        ).fetchone()

    assert row is not None
    assert json.loads(row["touches"]) == ["a/b.py"]


def test_write_through_snapshot_raises_hub_unavailable(tmp_path, monkeypatch):
    monkeypatch.setenv("ORG_DB_URL", UNREACHABLE_URL)
    snap = tmp_path / "tasks.snapshot.db"
    monkeypatch.setattr(db_mod, "SNAPSHOT_PATH", snap)
    _build_snapshot(snap, exported_at="2026-09-29T00:00:00+00:00",
                    tasks=[{"id": "task-abc12345"}])

    with pytest.raises(db_mod.HubUnavailable, match="read-only snapshot from"):
        with db_mod.get_conn(timeout=1) as conn:
            conn.execute(
                "UPDATE tasks SET status=? WHERE id=?", ("done", "task-abc12345")
            )


def test_no_snapshot_also_raises_hub_unavailable(tmp_path, monkeypatch):
    monkeypatch.setenv("ORG_DB_URL", UNREACHABLE_URL)
    monkeypatch.setattr(db_mod, "SNAPSHOT_PATH", tmp_path / "does-not-exist.db")

    with pytest.raises(db_mod.HubUnavailable):
        with db_mod.get_conn(readonly=True, timeout=1) as conn:
            conn.execute("SELECT 1")


def test_fallback_warning_appears_only_once(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("ORG_DB_URL", UNREACHABLE_URL)
    snap = tmp_path / "tasks.snapshot.db"
    monkeypatch.setattr(db_mod, "SNAPSHOT_PATH", snap)
    _build_snapshot(snap, exported_at=db_mod.now_iso())

    for _ in range(3):
        with db_mod.get_conn(readonly=True, timeout=1) as conn:
            conn.execute("SELECT 1").fetchall()

    err = capsys.readouterr().err
    assert err.count("[db] WARNING") == 1


def test_org_db_url_unset_behaviour_unchanged(tmp_path, monkeypatch):
    """ORG_DB_URL already cleared by conftest's autouse _clean_session_env.
    A snapshot sitting at SNAPSHOT_PATH (even a valid one) must be completely
    irrelevant to the plain-SQLite path -- byte-for-byte unchanged."""
    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    snap = tmp_path / "tasks.snapshot.db"
    monkeypatch.setattr(db_mod, "SNAPSHOT_PATH", snap)
    _build_snapshot(snap, exported_at=db_mod.now_iso(),
                    tasks=[{"id": "task-fromsnap0"}])
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")

    db_mod.init()
    tid = db_mod.create_task("projA", "developer", "t1", "d1")

    assert db_mod.get_task(tid)["id"] == tid
    assert db_mod.get_task("task-fromsnap0") is None  # snapshot never consulted
    assert db_mod.pg_url() is None


# ---------------------------------------------------------------------------
# scripts/hub/export_to_sqlite.py
# ---------------------------------------------------------------------------

class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeHubConn:
    """Stands in for db_pg.Connection -- enough of the interface
    (execute().fetchall(), close()) for export_to_sqlite._copy_table(), with
    no real Postgres involved. `fail_on_table` raises the moment that
    table's SELECT runs, simulating a hub read failing partway through."""

    def __init__(self, rows_by_table: dict[str, list[dict]],
                *, fail_on_table: str | None = None):
        self._rows_by_table = rows_by_table
        self._fail_on_table = fail_on_table
        self.closed = False

    def execute(self, sql, params=()):
        for table in ("tasks", "c_level_sessions", "events"):
            if f"FROM {table}" in sql:
                if table == self._fail_on_table:
                    raise RuntimeError(f"simulated failure reading {table}")
                return _FakeCursor(self._rows_by_table.get(table, []))
        return _FakeCursor([])

    def close(self):
        self.closed = True


def test_export_hub_not_configured_exits_0(monkeypatch, capsys):
    monkeypatch.delenv("ORG_DB_URL", raising=False)
    rc = export_mod.main()
    assert rc == 0
    assert "hub not configured" in capsys.readouterr().out


def test_export_writes_queryable_snapshot(tmp_path, monkeypatch):
    dst = tmp_path / "tasks.snapshot.db"
    fake = _FakeHubConn({
        "tasks": [{"id": "task-hub00001", "project": "projA", "role": "developer",
                   "status": "done", "title": "t", "description": "d",
                   "touches": "[]", "created_at": "x", "updated_at": "x"}],
        "c_level_sessions": [],
        "events": [],
    })
    monkeypatch.setattr(export_mod.db_pg, "connect", lambda url, timeout=None: fake)
    monkeypatch.setenv("ORG_DB_URL", "postgresql://fake-host/org")

    export_mod.export(dst)

    assert fake.closed
    assert dst.exists()
    conn = sqlite3.connect(f"file:{dst}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM tasks WHERE id=?", ("task-hub00001",)).fetchone()
    conn.close()
    assert row["status"] == "done"
    assert db_mod.read_snapshot_meta(dst) is not None
    # no leftover temp file
    assert list(tmp_path.glob(".tasks.snapshot.*.tmp")) == []


def test_export_atomic_write_failure_keeps_old_snapshot(tmp_path, monkeypatch):
    """Simulates a hub read failing partway through (after tasks + sessions
    copied fine, while reading events) -- the pre-existing snapshot at
    dst_path must be left completely untouched (task brief's atomic-write
    requirement)."""
    dst = tmp_path / "tasks.snapshot.db"
    _build_snapshot(dst, exported_at="OLD-SENTINEL-TIME")

    fake = _FakeHubConn({"tasks": [], "c_level_sessions": []},
                        fail_on_table="events")
    monkeypatch.setattr(export_mod.db_pg, "connect", lambda url, timeout=None: fake)
    monkeypatch.setenv("ORG_DB_URL", "postgresql://fake-host/org")

    with pytest.raises(RuntimeError, match="simulated failure reading events"):
        export_mod.export(dst)

    assert fake.closed  # the failed hub connection is still cleaned up
    assert db_mod.read_snapshot_meta(dst) == "OLD-SENTINEL-TIME"
    assert list(tmp_path.glob(".tasks.snapshot.*.tmp")) == []


def test_export_main_returns_1_on_hub_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(db_mod, "SNAPSHOT_PATH", tmp_path / "tasks.snapshot.db")
    monkeypatch.setattr(export_mod.db_pg, "connect",
                        lambda url, timeout=None: (_ for _ in ()).throw(
                            db_pg.HubConnectError("simulated: hub down")))
    monkeypatch.setenv("ORG_DB_URL", "postgresql://fake-host/org")

    rc = export_mod.main()

    assert rc == 1
    assert "hub unreachable" in capsys.readouterr().err


@pg_only
def test_export_against_real_postgres(tmp_path, monkeypatch):
    """The one export test that talks to a real (scratch, ORG_TEST_DB_URL)
    Postgres -- proves export_mod.export() round-trips through the actual
    db_pg wire format, not just the _FakeHubConn stand-in above."""
    conn = db_pg.connect(ORG_TEST_DB_URL, timeout=10)
    for table in ("locks", "events", "tasks", "c_level_sessions"):
        conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    conn.commit()
    conn.close()

    monkeypatch.delenv("CTO_SESSION_ID", raising=False)
    monkeypatch.delenv("CXO_SESSION_ID", raising=False)
    monkeypatch.setenv("ORG_DB_URL", ORG_TEST_DB_URL)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    db_mod.init()
    tid = db_mod.create_task("projA", "developer", "t1", "d1")

    dst = tmp_path / "tasks.snapshot.db"
    export_mod.export(dst)

    snap = sqlite3.connect(f"file:{dst}?mode=ro", uri=True)
    snap.row_factory = sqlite3.Row
    row = snap.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()
    snap.close()
    assert row is not None
    assert row["project"] == "projA"


# ---------------------------------------------------------------------------
# hook timing -- must never add more than ~1s to a prompt when the hub is
# down (task brief); asserted here at a generous 2s ceiling.
# ---------------------------------------------------------------------------

def _load_module(rel_path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_hook_self_repo_guard_timing_and_fail_closed(tmp_path, monkeypatch):
    """hub down + no snapshot: must stay fail-CLOSED (block) and must not
    hang -- the two requirements the task brief singles out for this hook."""
    monkeypatch.setenv("ORG_DB_URL", UNREACHABLE_URL)
    guard = _load_module("scripts/hook-self-repo-guard.py", "hsg_timing_test")
    monkeypatch.setattr(guard.db_lib, "SNAPSHOT_PATH", tmp_path / "no-snapshot.db")
    monkeypatch.setattr(guard.db_lib, "_SNAPSHOT_FALLBACK_WARNED", set())

    checkout = tmp_path / "checkout"
    wt = checkout / "worktrees" / "mooniex-agents__developer__task-aaaaaaaa"
    (wt / "scripts").mkdir(parents=True)

    event = {"cwd": str(wt), "tool_name": "Edit",
             "tool_input": {"file_path": "scripts/x.py"}}

    start = time.monotonic()
    code, message = guard.decide(event)
    elapsed = time.monotonic() - start

    assert elapsed < 2.0, f"self-repo-guard took {elapsed:.2f}s with the hub down"
    assert code == 2  # fail CLOSED -- touches unreadable from hub or snapshot
    assert "could not decide" in message


def test_hook_log_prompt_timing_and_fail_open(tmp_path, monkeypatch):
    """hub down + no snapshot: this hook stays fail-OPEN (empty owners map ->
    _filter_for_session keeps every line) and must not hang."""
    monkeypatch.setenv("ORG_DB_URL", UNREACHABLE_URL)
    mod = _load_module("scripts/hook-log-prompt.py", "hlp_timing_test")
    monkeypatch.setattr(mod.db_lib, "SNAPSHOT_PATH", tmp_path / "no-snapshot.db")
    monkeypatch.setattr(mod.db_lib, "_SNAPSHOT_FALLBACK_WARNED", set())

    start = time.monotonic()
    owners = mod._task_owners({"task-doesnotexist"})
    elapsed = time.monotonic() - start

    assert elapsed < 2.0, f"hook-log-prompt took {elapsed:.2f}s with the hub down"
    assert owners == {}  # fail OPEN: unreadable registry -> keep every line


def test_hook_memory_nudge_timing_unaffected_by_hub(tmp_path, monkeypatch):
    """hook-memory-nudge.py never reads the ledger -- it only touches its own
    JSON turn counter (state/session-nudge-counters.json), so ORG_DB_URL
    being unreachable has no code path to slow it down. Kept here so the
    task brief's 'run each hook' timing check covers all three by name."""
    monkeypatch.setenv("ORG_DB_URL", UNREACHABLE_URL)
    monkeypatch.setenv("CTO_SESSION", "1")
    mod = _load_module("scripts/hook-memory-nudge.py", "hmn_timing_test")
    monkeypatch.setattr(mod, "COUNTER_PATH", tmp_path / "counters.json")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"session_id": "s1"})))

    start = time.monotonic()
    rc = mod.main()
    elapsed = time.monotonic() - start

    assert rc == 0
    assert elapsed < 2.0
