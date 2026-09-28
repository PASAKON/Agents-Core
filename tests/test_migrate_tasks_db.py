"""Tests for scripts/migrate_tasks_db.py (Org Mesh W1.2 -- merging TWO
SQLite ledgers into one Postgres hub, docs/design/tasks-db-hub.md,
docs/design/org-mesh.md).

Pure functions (backfill_row, event_dedupe_key, new_events,
find_row_collisions, resolve_collision_mode, should_refuse_apply) are
tested directly with plain dicts -- no database involved.

Everything else is tested against two on-disk SQLite files: one built
through lib.db as a realistic source ledger, one initialised via
lib.db.init_schema(is_pg=False) as a stand-in "target". This works because
_copy_table/_copy_events_appending are written in the SQLite-flavoured SQL
('?' placeholders, `INSERT ... ON CONFLICT ... DO NOTHING/DO UPDATE`) that
lib/db_pg.py's translation layer makes a real Postgres run identically --
a modern SQLite engine (3.24+) runs that exact same SQL natively, so a
second SQLite file is a faithful stand-in for the target without needing a
real Postgres for every test. A full migrate.main() run against a REAL
Postgres is gated behind ORG_TEST_DB_URL, same pattern as
tests/test_db_backend_pg.py (skipped in an environment with no local
Postgres -- see that file's docstring for setup).

ADR 0021: no test touches real state -- every source/target lives under
tmp_path; conftest.py's autouse `_isolate_org_root` / `_clean_session_env`
fixtures back this up (and lib.db._connect's own PYTEST_CURRENT_TEST guard
refuses outright if a path under a real checkout were ever used).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import scripts.migrate_tasks_db as migrate  # noqa: E402


def _make_source(tmp_path, name, monkeypatch):
    """A source ledger built through the real lib.db API -- monkeypatches
    db_mod.DB_PATH so create_task/register_cxo_session/acquire_lock write to
    a fresh SQLite file under tmp_path, never the real state/tasks.db."""
    path = tmp_path / name
    monkeypatch.delenv("ORG_DB_URL", raising=False)
    monkeypatch.setattr(db_mod, "DB_PATH", path)
    db_mod.init()
    return path


def _make_target(tmp_path, name="target.db"):
    """A bare SQLite db with the same schema lib.db.init() would create --
    stands in for the Postgres hub (see module docstring)."""
    path = tmp_path / name
    conn = db_mod.sqlite_connect(path)
    db_mod.init_schema(conn, is_pg=False)
    conn.commit()
    return conn


def _rows(conn, table):
    return [dict(r) for r in conn.execute(f"SELECT * FROM {table}").fetchall()]


def _null_dispatcher_host(src_path, task_id):
    """create_task() always stamps dispatcher_host via config.self_host()
    (never NULL for a freshly created row) -- simulate the measured
    pre-W0.1 shape (task brief: "tasks.dispatcher_host is a new column...
    old rows have it NULL") so a backfill test has something to backfill,
    same as `host` (never set by create_task unless explicitly passed)."""
    conn = db_mod.sqlite_connect(src_path)
    conn.execute("UPDATE tasks SET dispatcher_host = NULL WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# pure functions -- no database
# ---------------------------------------------------------------------------

def test_backfill_row_fills_null_and_never_overwrites():
    row = {"host": None, "dispatcher_host": "mac", "other": "x"}
    out, changed = migrate.backfill_row(row, ("host", "dispatcher_host"), "contabo")
    assert changed is True
    assert out["host"] == "contabo"
    assert out["dispatcher_host"] == "mac"  # non-NULL, never overwritten
    assert row["host"] is None  # pure -- input dict never mutated


def test_backfill_row_no_default_host_is_noop():
    row = {"host": None}
    out, changed = migrate.backfill_row(row, ("host",), None)
    assert changed is False
    assert out["host"] is None


def test_backfill_row_all_non_null_is_noop():
    row = {"host": "mac", "dispatcher_host": "mac"}
    out, changed = migrate.backfill_row(row, ("host", "dispatcher_host"), "contabo")
    assert changed is False
    assert out == row


def test_backfill_row_no_backfill_columns_for_table_is_noop():
    row = {"id": 1, "task_id": "t"}
    out, changed = migrate.backfill_row(row, migrate.BACKFILL_COLUMNS.get("events", ()), "mac")
    assert changed is False
    assert out == row


def test_event_dedupe_key_ignores_id_and_actor():
    row1 = {"id": 1, "task_id": "t", "actor": "a", "kind": "k", "payload": "p", "ts": "T"}
    row2 = {"id": 2, "task_id": "t", "actor": "b", "kind": "k", "payload": "p", "ts": "T"}
    assert migrate.event_dedupe_key(row1) == migrate.event_dedupe_key(row2)


def test_event_dedupe_key_differs_on_content():
    row1 = {"id": 1, "task_id": "t", "kind": "k", "payload": "p", "ts": "T1"}
    row2 = {"id": 2, "task_id": "t", "kind": "k", "payload": "p", "ts": "T2"}
    assert migrate.event_dedupe_key(row1) != migrate.event_dedupe_key(row2)


def test_new_events_dedupes_against_seen_and_within_batch():
    key1 = ("t", "T1", "k", "p")
    seen = {key1}
    rows = [
        {"task_id": "t", "ts": "T1", "kind": "k", "payload": "p"},  # already in target
        {"task_id": "t", "ts": "T2", "kind": "k", "payload": "p"},  # new
        {"task_id": "t", "ts": "T2", "kind": "k", "payload": "p"},  # dup within this batch
    ]
    fresh = migrate.new_events(rows, seen)
    assert len(fresh) == 1
    assert fresh[0]["ts"] == "T2"


def test_find_row_collisions_flags_real_differences():
    source = [{"id": "t1", "title": "A", "host": None}]
    target = [{"id": "t1", "title": "B", "host": "mac"}]
    collisions = migrate.find_row_collisions(source, target, ("id",),
                                              ignore_cols=frozenset({"host"}))
    assert collisions == [("t1",)]


def test_find_row_collisions_ignores_backfill_only_difference():
    """Rerunning after an earlier --default-host backfill must not see its
    own past backfill as a fresh collision (or a plain rerun would refuse
    itself forever)."""
    source = [{"id": "t1", "title": "A", "host": None}]
    target = [{"id": "t1", "title": "A", "host": "mac"}]  # only host differs
    collisions = migrate.find_row_collisions(source, target, ("id",),
                                              ignore_cols=frozenset({"host"}))
    assert collisions == []


def test_find_row_collisions_ignores_rows_absent_from_target():
    source = [{"id": "t1", "title": "A"}]
    target: list[dict] = []
    assert migrate.find_row_collisions(source, target, ("id",)) == []


def test_find_row_collisions_identical_rows_are_not_collisions():
    source = [{"id": "t1", "title": "A"}]
    target = [{"id": "t1", "title": "A"}]
    assert migrate.find_row_collisions(source, target, ("id",)) == []


def test_resolve_collision_mode_default_none():
    assert migrate.resolve_collision_mode(None, False) == (None, False)


def test_resolve_collision_mode_upsert_flag_means_keep_source():
    assert migrate.resolve_collision_mode(None, True) == ("keep-source", True)


def test_resolve_collision_mode_explicit_modes():
    assert migrate.resolve_collision_mode("skip", False) == ("skip", False)
    assert migrate.resolve_collision_mode("keep-target", False) == ("keep-target", False)
    assert migrate.resolve_collision_mode("keep-source", False) == ("keep-source", True)


def test_should_refuse_apply():
    assert migrate.should_refuse_apply(2, True, None) is True
    assert migrate.should_refuse_apply(2, True, "skip") is False
    assert migrate.should_refuse_apply(2, False, None) is False
    assert migrate.should_refuse_apply(0, True, None) is False


# ---------------------------------------------------------------------------
# _copy_table / _copy_events_appending against a SQLite stand-in target
# ---------------------------------------------------------------------------

def test_copy_table_backfills_null_host_columns(tmp_path, monkeypatch):
    src_path = _make_source(tmp_path, "src.db", monkeypatch)
    tid = db_mod.create_task("projA", "developer", "s1", "d1")
    _null_dispatcher_host(src_path, tid)
    assert db_mod.get_task(tid)["host"] is None
    assert db_mod.get_task(tid)["dispatcher_host"] is None

    target_conn = _make_target(tmp_path)
    sconn = migrate._sqlite_conn(src_path)
    stats = migrate._copy_table(sconn, target_conn, "tasks", ("id",),
                                 upsert=False, apply=True, skip_bad_rows=False,
                                 default_host="mac")
    sconn.close()

    assert stats == {"to_insert": 1, "backfilled": 1, "moved": 1, "skipped": []}
    tgt_row = _rows(target_conn, "tasks")[0]
    assert tgt_row["host"] == "mac"
    assert tgt_row["dispatcher_host"] == "mac"


def test_copy_table_backfills_c_level_sessions_host(tmp_path, monkeypatch):
    src_path = _make_source(tmp_path, "src.db", monkeypatch)
    db_mod.register_cxo_session("cto", "sessA")  # host defaults to NULL

    target_conn = _make_target(tmp_path)
    sconn = migrate._sqlite_conn(src_path)
    stats = migrate._copy_table(sconn, target_conn, "c_level_sessions",
                                 ("role", "session_id"), upsert=False, apply=True,
                                 skip_bad_rows=False, default_host="contabo")
    sconn.close()

    assert stats["backfilled"] == 1
    assert _rows(target_conn, "c_level_sessions")[0]["host"] == "contabo"


def test_copy_table_dry_run_writes_nothing_but_reports_counts(tmp_path, monkeypatch):
    src_path = _make_source(tmp_path, "src.db", monkeypatch)
    tid = db_mod.create_task("projA", "developer", "s1", "d1")
    _null_dispatcher_host(src_path, tid)

    target_conn = _make_target(tmp_path)
    sconn = migrate._sqlite_conn(src_path)
    stats = migrate._copy_table(sconn, target_conn, "tasks", ("id",),
                                 upsert=False, apply=False, skip_bad_rows=False,
                                 default_host="mac")
    sconn.close()

    assert stats["to_insert"] == 1
    assert stats["backfilled"] == 1
    assert stats["moved"] == 0
    assert _rows(target_conn, "tasks") == []  # dry run: nothing written


def test_two_ledgers_merge_events_no_duplicates_no_id_clash(tmp_path, monkeypatch):
    path_a = _make_source(tmp_path, "mac.db", monkeypatch)
    db_mod.create_task("projA", "developer", "s1", "d1")
    db_mod.create_task("projA", "developer", "s2", "d2")

    path_b = _make_source(tmp_path, "contabo.db", monkeypatch)
    db_mod.create_task("projB", "developer", "s3", "d3")

    target_conn = _make_target(tmp_path)

    # First ledger: verbatim id copy (the normal, non-append path).
    sconn_a = migrate._sqlite_conn(path_a)
    stats_a = migrate._copy_table(sconn_a, target_conn, "events", ("id",),
                                   upsert=False, apply=True, skip_bad_rows=False,
                                   default_host=None)
    sconn_a.close()
    assert stats_a["moved"] > 0

    # Second ledger: --append-events, ids dropped, deduped by content.
    sconn_b = migrate._sqlite_conn(path_b)
    stats_b = migrate._copy_events_appending(sconn_b, target_conn, apply=True,
                                              skip_bad_rows=False)
    sconn_b.close()
    assert stats_b["moved"] > 0

    ids = [r["id"] for r in _rows(target_conn, "events")]
    assert len(ids) == len(set(ids))  # no id clash between the two ledgers

    # Rerunning ledger B's --append-events a second time inserts 0 rows.
    sconn_b2 = migrate._sqlite_conn(path_b)
    stats_b2 = migrate._copy_events_appending(sconn_b2, target_conn, apply=True,
                                               skip_bad_rows=False)
    sconn_b2.close()
    assert stats_b2 == {"to_insert": 0, "backfilled": 0, "moved": 0, "skipped": []}


def test_append_events_dry_run_writes_nothing(tmp_path, monkeypatch):
    src_path = _make_source(tmp_path, "src.db", monkeypatch)
    db_mod.create_task("projA", "developer", "s1", "d1")

    target_conn = _make_target(tmp_path)
    sconn = migrate._sqlite_conn(src_path)
    stats = migrate._copy_events_appending(sconn, target_conn, apply=False,
                                            skip_bad_rows=False)
    sconn.close()

    assert stats["to_insert"] > 0
    assert stats["moved"] == 0
    assert _rows(target_conn, "events") == []


def test_locks_are_not_copied(tmp_path, monkeypatch):
    assert "locks" not in migrate.TABLES

    src_path = _make_source(tmp_path, "src.db", monkeypatch)
    db_mod.acquire_lock("proj:projA:path:z.py", "ownerZ", ttl_seconds=600)
    assert _rows(db_mod.sqlite_connect(src_path), "locks") != []  # source has one

    target_conn = _make_target(tmp_path)
    sconn = migrate._sqlite_conn(src_path)
    for table, pk in migrate.TABLES.items():
        migrate._copy_table(sconn, target_conn, table, pk, upsert=False,
                             apply=True, skip_bad_rows=False, default_host="mac")
    sconn.close()

    assert _rows(target_conn, "locks") == []


def test_rerun_is_a_noop(tmp_path, monkeypatch):
    src_path = _make_source(tmp_path, "src.db", monkeypatch)
    db_mod.create_task("projA", "developer", "s1", "d1")
    db_mod.register_cxo_session("cto", "sessA")

    target_conn = _make_target(tmp_path)

    def run():
        sconn = migrate._sqlite_conn(src_path)
        stats = {table: migrate._copy_table(sconn, target_conn, table, pk,
                                             upsert=False, apply=True,
                                             skip_bad_rows=False, default_host="mac")
                 for table, pk in migrate.TABLES.items()}
        sconn.close()
        return stats

    first = run()
    assert first["tasks"]["moved"] == 1
    assert first["c_level_sessions"]["moved"] == 1

    second = run()
    assert all(s["moved"] == 0 for s in second.values())
    assert all(s["to_insert"] == 0 for s in second.values())

    sconn = migrate._sqlite_conn(src_path)
    collisions = migrate._find_all_collisions(sconn, target_conn)
    sconn.close()
    assert collisions == {"tasks": [], "c_level_sessions": []}


def test_on_collision_modes(tmp_path, monkeypatch):
    src_path = _make_source(tmp_path, "src.db", monkeypatch)
    tid = db_mod.create_task("projA", "developer", "s1", "d1")

    target_conn = _make_target(tmp_path)
    sconn = migrate._sqlite_conn(src_path)
    migrate._copy_table(sconn, target_conn, "tasks", ("id",), upsert=False,
                         apply=True, skip_bad_rows=False, default_host="mac")
    sconn.close()

    # Diverge: the target's copy was edited locally, and the source moved on.
    target_conn.execute("UPDATE tasks SET title=? WHERE id=?", ("target title", tid))
    target_conn.commit()
    src_conn = db_mod.sqlite_connect(src_path)
    src_conn.execute("UPDATE tasks SET title=? WHERE id=?", ("source title", tid))
    src_conn.commit()
    src_conn.close()

    sconn = migrate._sqlite_conn(src_path)
    collisions = migrate.find_row_collisions(
        _rows(sconn, "tasks"), _rows(target_conn, "tasks"), ("id",),
        ignore_cols=frozenset(migrate.BACKFILL_COLUMNS["tasks"]))
    assert collisions == [(tid,)]

    # "skip" / "keep-target" (upsert=False): target keeps its own version.
    migrate._copy_table(sconn, target_conn, "tasks", ("id",), upsert=False,
                         apply=True, skip_bad_rows=False, default_host="mac")
    sconn.close()
    assert _rows(target_conn, "tasks")[0]["title"] == "target title"

    # "keep-source" (upsert=True): the target is overwritten with the source.
    sconn2 = migrate._sqlite_conn(src_path)
    migrate._copy_table(sconn2, target_conn, "tasks", ("id",), upsert=True,
                         apply=True, skip_bad_rows=False, default_host="mac")
    sconn2.close()
    assert _rows(target_conn, "tasks")[0]["title"] == "source title"


# ---------------------------------------------------------------------------
# main() argument validation -- no sqlite/postgres connection is ever
# reached in any of these (every check below runs before main() opens one).
# ---------------------------------------------------------------------------

def test_main_refuses_missing_source(tmp_path):
    rc = migrate.main(["--from", str(tmp_path / "nope.db"), "--to", "postgresql://x/x"])
    assert rc == 1


def test_main_refuses_non_postgres_url(tmp_path):
    src = tmp_path / "src.db"
    src.touch()
    rc = migrate.main(["--from", str(src), "--to", "mysql://x/x"])
    assert rc == 1


def test_main_apply_requires_default_host(tmp_path):
    src = tmp_path / "src.db"
    src.touch()
    rc = migrate.main(["--from", str(src), "--to", "postgresql://x/x", "--apply"])
    assert rc == 1


def test_main_rejects_unknown_default_host(tmp_path):
    src = tmp_path / "src.db"
    src.touch()
    rc = migrate.main(["--from", str(src), "--to", "postgresql://x/x",
                        "--apply", "--default-host", "not-a-real-host"])
    assert rc == 1


def test_main_rejects_upsert_and_on_collision_together(tmp_path):
    src = tmp_path / "src.db"
    src.touch()
    rc = migrate.main(["--from", str(src), "--to", "postgresql://x/x",
                        "--apply", "--default-host", "mac",
                        "--upsert", "--on-collision", "skip"])
    assert rc == 1
