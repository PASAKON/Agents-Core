"""tests/test_ledger_direct_opens.py -- Org Mesh W1.4 (docs/design/org-mesh.md):
every direct `sqlite3.connect(...tasks.db...)` site outside lib.db itself now
reads the org ledger through `lib.db.get_conn()`, so each keeps working once
the org flips to the Postgres hub (`ORG_DB_URL` set, ADR 0025) instead of
`state/tasks.db`.

Sites covered here (SQLite ledger, always run; Postgres variant, ORG_TEST_DB_URL
only -- skipped otherwise, same convention as tests/test_db_backend_pg.py):
  - questline/export_state.py     load_tasks()
  - tools/workdir.py              orphans()
  - tools/storage_reclaim.py      _pilot_tasks()
  - scripts/hq_migrate_step4b.py  check_no_other_tasks_in_flight()
  - tools/drive_leg.py            state_db() -- ORG_DB_URL branch runs pg_dump
    instead of copying a local sqlite file (a stub pg_dump on PATH proves the
    routing; no ORG_TEST_DB_URL needed for that one).

Run:  .venv/bin/python -m pytest tests/test_ledger_direct_opens.py
"""
from __future__ import annotations

import io
import os
import stat
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import lib.db as db_mod  # noqa: E402
import lib.db_pg as db_pg  # noqa: E402
import questline.export_state as export_state  # noqa: E402
import tools.drive_leg as drive_leg  # noqa: E402
import tools.storage_reclaim as storage_reclaim  # noqa: E402
import tools.workdir as workdir  # noqa: E402
import hq_migrate_step4b as step4b  # noqa: E402

ORG_TEST_DB_URL = os.environ.get("ORG_TEST_DB_URL", "").strip()
pg_only = pytest.mark.skipif(
    not ORG_TEST_DB_URL,
    reason=(
        "ORG_TEST_DB_URL not set -- needs a local Postgres 16 (see "
        "tests/test_db_backend_pg.py's module docstring for setup). Example: "
        "ORG_TEST_DB_URL=postgresql://postgres@127.0.0.1:54329/org_test "
        "pytest tests/test_ledger_direct_opens.py"
    ),
)

_PG_TABLES = ("locks", "events", "tasks", "c_level_sessions")


def _drop_all_pg(url: str) -> None:
    conn = db_pg.connect(url, timeout=10)
    try:
        for table in _PG_TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        conn.commit()
    finally:
        conn.close()


@pytest.fixture()
def temp_db(monkeypatch, tmp_path):
    """A throwaway SQLite ledger, same shape as lib/test_recall.py's fixture."""
    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    db_mod.init()
    return db_path


@pytest.fixture()
def pg_db(monkeypatch):
    """Same shape as `temp_db`, against ORG_TEST_DB_URL's scratch Postgres
    instead -- only used by @pg_only tests."""
    monkeypatch.setenv("ORG_DB_URL", ORG_TEST_DB_URL)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    _drop_all_pg(ORG_TEST_DB_URL)
    db_mod.init()
    yield
    _drop_all_pg(ORG_TEST_DB_URL)


# =========================================================================== questline/export_state.py

def test_export_state_load_tasks_sqlite(temp_db):
    tid = db_mod.create_task(project="mooniex-agents", role="developer", title="t1",
                              description="d", owner_cto="x")
    db_mod.update_status(tid, "done", actor="test")
    expected_updated_at = db_mod.get_task(tid)["updated_at"]

    export_state.TASKS_DB = temp_db
    rows = [dict(r) for r in export_state.load_tasks()]

    assert rows == [{"role": "developer", "status": "done",
                      "updated_at": expected_updated_at}]


@pg_only
def test_export_state_load_tasks_postgres(pg_db, tmp_path):
    tid = db_mod.create_task(project="mooniex-agents", role="developer", title="t1",
                              description="d", owner_cto="x")
    db_mod.update_status(tid, "done", actor="test")
    expected_updated_at = db_mod.get_task(tid)["updated_at"]

    export_state.TASKS_DB = tmp_path / "unused-tasks.db"  # ignored under ORG_DB_URL
    rows = [dict(r) for r in export_state.load_tasks()]

    assert rows == [{"role": "developer", "status": "done",
                      "updated_at": expected_updated_at}]


# =========================================================================== tools/workdir.py orphans()

def test_workdir_orphans_sqlite(temp_db, tmp_path):
    tid = db_mod.create_task(project="mooniex-agents", role="developer", title="t1",
                              description="d", owner_cto="x")
    db_mod.update_status(tid, "done", actor="test")
    workdir.create(tid, root=tmp_path)

    rows = workdir.orphans(temp_db, root=tmp_path)

    assert len(rows) == 1
    assert rows[0]["task"] == tid
    assert rows[0]["status"] == "done"


def test_workdir_orphans_sqlite_missing_db_reads_as_unknown(tmp_path):
    """ORG_DB_URL unset, byte-for-byte: an unreadable/missing local ledger never
    crashes orphans() -- every folder just reads as 'unknown' (unchanged from
    the pre-migration sqlite3.Error catch)."""
    workdir.create("task-00000000", root=tmp_path)

    rows = workdir.orphans(tmp_path / "does-not-exist.db", root=tmp_path)

    assert len(rows) == 1
    assert rows[0]["status"] == "unknown"


@pg_only
def test_workdir_orphans_postgres(pg_db, tmp_path):
    tid = db_mod.create_task(project="mooniex-agents", role="developer", title="t1",
                              description="d", owner_cto="x")
    db_mod.update_status(tid, "done", actor="test")
    workdir.create(tid, root=tmp_path)

    rows = workdir.orphans(tmp_path / "unused-tasks.db", root=tmp_path)  # path ignored under ORG_DB_URL

    assert len(rows) == 1
    assert rows[0]["task"] == tid
    assert rows[0]["status"] == "done"


# =========================================================================== tools/storage_reclaim.py _pilot_tasks()

def test_storage_reclaim_pilot_tasks_sqlite(temp_db, tmp_path):
    wt = tmp_path / "worktrees" / "pilot-task"
    tid = db_mod.create_task(project="mooniex-agents", role="developer", title="t1",
                              description="d", owner_cto="pilot-owner")
    db_mod.set_fields(tid, worktree=str(wt))
    other = db_mod.create_task(project="mooniex-agents", role="developer", title="t2",
                                description="d", owner_cto="someone-else")

    all_rows = storage_reclaim._pilot_tasks(temp_db, "all")
    scoped_rows = storage_reclaim._pilot_tasks(temp_db, ["pilot-owner"])

    assert {r["id"] for r in all_rows} == {tid, other}
    assert [r["id"] for r in scoped_rows] == [tid]
    assert scoped_rows[0]["worktree"] == str(wt)


def test_storage_reclaim_pilot_tasks_sqlite_missing_db_returns_empty(tmp_path):
    """ORG_DB_URL unset, byte-for-byte: an unreadable/missing ledger returns []
    (unchanged from the pre-migration sqlite3.Error catch)."""
    assert storage_reclaim._pilot_tasks(tmp_path / "does-not-exist.db", "all") == []


@pg_only
def test_storage_reclaim_pilot_tasks_postgres(pg_db, tmp_path):
    wt = tmp_path / "worktrees" / "pilot-task"
    tid = db_mod.create_task(project="mooniex-agents", role="developer", title="t1",
                              description="d", owner_cto="pilot-owner")
    db_mod.set_fields(tid, worktree=str(wt))

    rows = storage_reclaim._pilot_tasks(tmp_path / "unused-tasks.db", ["pilot-owner"])  # path ignored

    assert [r["id"] for r in rows] == [tid]
    assert rows[0]["worktree"] == str(wt)


# =========================================================================== scripts/hq_migrate_step4b.py gate

def test_step4b_gate_sqlite_missing_db_refuses(tmp_path):
    """ORG_DB_URL unset, byte-for-byte: a missing local ledger still refuses
    loudly ('tasks.db not found'), same as before this task."""
    with pytest.raises(step4b.GateBlocked, match="tasks.db not found"):
        step4b.check_no_other_tasks_in_flight(tmp_path / "does-not-exist.db", None)


def test_step4b_gate_sqlite_blocks_and_clears(temp_db):
    other = db_mod.create_task(project="mooniex-agents", role="developer", title="t1",
                                description="d", owner_cto="x")
    with pytest.raises(step4b.GateBlocked, match=other):
        step4b.check_no_other_tasks_in_flight(temp_db, None)

    step4b.check_no_other_tasks_in_flight(temp_db, other)  # self-exclusion clears it


def test_step4b_gate_postgres_url_set_skips_local_file_check(monkeypatch, tmp_path):
    """A missing local state/tasks.db must not refuse the gate once ORG_DB_URL
    is set -- the whole point of routing this read through lib.db.get_conn().
    No real Postgres needed to prove the routing: an unreachable ORG_DB_URL
    still fails fast (connection refused), but with a *different* error than
    'tasks.db not found' -- proof the exists-check on the local file was
    correctly skipped and the failure came from the (attempted) hub read."""
    monkeypatch.setenv("ORG_DB_URL", "postgresql://baduser@127.0.0.1:1/baddb")
    missing_local_db = tmp_path / "does-not-exist.db"

    with pytest.raises(step4b.GateBlocked) as exc_info:
        step4b.check_no_other_tasks_in_flight(missing_local_db, None)

    assert "tasks.db not found" not in str(exc_info.value)
    assert "cannot read" in str(exc_info.value)


@pg_only
def test_step4b_gate_postgres(pg_db, tmp_path):
    other = db_mod.create_task(project="mooniex-agents", role="developer", title="t1",
                                description="d", owner_cto="x")

    with pytest.raises(step4b.GateBlocked, match=other):
        step4b.check_no_other_tasks_in_flight(tmp_path / "unused-tasks.db", None)  # path ignored

    step4b.check_no_other_tasks_in_flight(tmp_path / "unused-tasks.db", other)


# =========================================================================== tools/drive_leg.py state_db()

def _fake_put(monkeypatch, captured: dict) -> None:
    def fake_put(stream_fn, folder_id, remote_dir, base_name, ext, manifest, **kwargs):
        buf = io.BytesIO()
        stream_fn(buf)
        captured["ext"] = ext
        captured["manifest"] = manifest
        captured["raw_bytes"] = buf.getvalue()
        return {"bytes": len(buf.getvalue()), "drive": f"gdrive:{remote_dir}/{base_name}{ext}"}

    monkeypatch.setattr(drive_leg, "put", fake_put)


def test_drive_leg_state_db_org_db_url_unset_is_a_file_copy(tmp_path, monkeypatch):
    import sqlite3
    db = tmp_path / "tasks.db"
    con = sqlite3.connect(db)
    con.execute("create table tasks(id text)")
    con.execute("insert into tasks values('t1')")
    con.commit()
    con.close()

    captured: dict = {}
    _fake_put(monkeypatch, captured)
    cfg = tmp_path / "cfg"
    (cfg / "logs").mkdir(parents=True)

    result = drive_leg.state_db(config_dir=cfg, db_path=db)

    assert not result.get("skipped")
    assert captured["ext"] == ".sqlite.gz"
    assert captured["manifest"]["backup_api"] == "sqlite3.Connection.backup"
    import gzip
    assert gzip.decompress(captured["raw_bytes"])[:16] == b"SQLite format 3\x00"


def test_drive_leg_state_db_org_db_url_set_calls_pg_dump(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "pg_dump"
    stub.write_text(
        "#!/bin/sh\n"
        "echo \"-- fake dump of $1\"\n"
        f"echo \"$@\" >> {tmp_path / 'pg_dump_calls.log'}\n"
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ.get('PATH', '')}")
    monkeypatch.setenv("ORG_DB_URL", "postgresql://fake-host/org")

    captured: dict = {}
    _fake_put(monkeypatch, captured)
    cfg = tmp_path / "cfg"
    (cfg / "logs").mkdir(parents=True)

    result = drive_leg.state_db(config_dir=cfg)

    assert not result.get("skipped")
    assert captured["ext"] == ".sql.gz"
    assert captured["manifest"]["backup_api"] == "pg_dump"
    calls_log = tmp_path / "pg_dump_calls.log"
    assert calls_log.exists(), "pg_dump stub was never invoked"
    assert "postgresql://fake-host/org" in calls_log.read_text()


def test_drive_leg_state_db_org_db_url_set_missing_pg_dump_fails_loudly(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))  # nonexistent dir -- pg_dump not found
    (tmp_path / "empty-bin").mkdir()
    monkeypatch.setenv("ORG_DB_URL", "postgresql://fake-host/org")
    cfg = tmp_path / "cfg"
    (cfg / "logs").mkdir(parents=True)

    with pytest.raises(drive_leg.DriveLegError, match="pg_dump is not on PATH"):
        drive_leg.state_db(config_dir=cfg)
