"""Tests for tools/session_status.py + the c_level_sessions lifecycle migration.

task-728e4741. A C-level session ends as closed | saved | force_saved, recorded
by tools/session_status.record_close (the single writer), with the resume UUID
copied out of state/locks/<role>-<id>.uuid at close time. These pin:

  1. the ALTER guard: an old-shape DB migrates forward, existing rows land 'open'
  2. init() is idempotent (twice is a no-op, no duplicate-column error)
  3. record_close sets closed_at for each of the three close statuses
  4. an invalid status raises
  5. resume_uuid is copied from a .uuid fixture at close time
  6. resume_target falls back to the .uuid file when the column is empty
  7. list_sessions('saved') returns only saved rows
  8. the CLI main() (what scripts/session-kill.sh drives) records the row
  9. looks_like_uuid rejects short ids, accepts real uuids (task-a98788d7)
  10. the CLI `resume` subcommand (what spawn-cto.sh/spawn-cxo.sh --resume
      shell out to) falls back to the DB and refuses cleanly when neither
      source has a usable uuid

Run via:  .venv/bin/python scripts/test_session_status.py
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db  # noqa: E402
from tools import session_status as ss  # noqa: E402
from tools.session_name import lock_basename  # noqa: E402

_failures = 0
_UUID_SUFFIX = ".uuid"


def _mark(ok: bool, label: str) -> None:
    global _failures
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    if not ok:
        _failures += 1


def _fresh(tmp: Path, *, old_shape: bool = False) -> Path:
    """Point lib.db at a throwaway DB under tmp and init it.

    old_shape=True creates c_level_sessions in its PRE-rollout shape (4 cols)
    and seeds a row BEFORE init(), so the test exercises the ALTER guard
    carrying an existing DB forward.
    """
    db_path = tmp / "tasks.db"
    db.DB_PATH = db_path
    if old_shape:
        con = sqlite3.connect(str(db_path))
        con.execute(
            "CREATE TABLE c_level_sessions ("
            " role TEXT NOT NULL, session_id TEXT NOT NULL, "
            " active_task_id TEXT, spawned_at TEXT NOT NULL, "
            " PRIMARY KEY(role, session_id))"
        )
        con.execute(
            "INSERT INTO c_level_sessions (role, session_id, spawned_at) "
            "VALUES ('cto', 'old00001', '2026-01-01T00:00:00+00:00')"
        )
        con.commit()
        con.close()
    db.init()
    return tmp / "locks"


def _write_uuid(locks: Path, role: str, sid: str, uuid: str) -> Path:
    locks.mkdir(parents=True, exist_ok=True)
    p = locks / f"{lock_basename(role, sid)}{_UUID_SUFFIX}"
    p.write_text(uuid)
    return p


# --------------------------------------------------------------------------- #
def test_alter_guard_backfills_open() -> None:
    print("ALTER guard: old-shape DB migrates, existing rows land status='open'")
    with tempfile.TemporaryDirectory() as t:
        _fresh(Path(t), old_shape=True)
        cols = [r[1] for r in sqlite3.connect(
            str(db.DB_PATH)).execute("PRAGMA table_info(c_level_sessions)")]
        for c in ("status", "closed_at", "note", "resume_uuid"):
            _mark(c in cols, f"column {c} added")
        row = ss.get("cto", "old00001")
        _mark(row is not None and row["status"] == "open",
              "pre-existing row backfilled to status='open' (no manual fixup)")
        _mark(row["closed_at"] is None and row["resume_uuid"] is None,
              "new columns are NULL on a never-closed row")


def test_init_is_idempotent() -> None:
    print("init() is idempotent: twice is a no-op")
    with tempfile.TemporaryDirectory() as t:
        _fresh(Path(t))
        _mark(db.DB_PATH.exists(), "first init created the DB")
        # A second/third init must not raise (no duplicate-column error) and
        # must not drop or reset anything.
        db.init()
        db.init()
        cols = [r[1] for r in sqlite3.connect(
            str(db.DB_PATH)).execute("PRAGMA table_info(c_level_sessions)")]
        _mark(cols.count("status") == 1, "status column exists exactly once")


def test_record_close_sets_closed_at_for_each_status() -> None:
    print("record_close sets closed_at for closed|saved|force_saved")
    cases = [("closed", "cto", "clos0001"),
             ("saved", "cto", "save0002"),
             ("force_saved", "cfo", "forc0003")]
    with tempfile.TemporaryDirectory() as t:
        locks = _fresh(Path(t))
        for status, role, sid in cases:
            ss.record_close(role, sid, status, locks_dir=locks)
            row = ss.get(role, sid)
            _mark(row is not None and row["status"] == status,
                  f"{status}: status recorded")
            _mark(row is not None and row["closed_at"] is not None,
                  f"{status}: closed_at is set")


def test_invalid_status_raises() -> None:
    print("record_close rejects anything outside the three close literals")
    with tempfile.TemporaryDirectory() as t:
        locks = _fresh(Path(t))
        for bad in ("open", "bogus", "", "CLOSED"):
            try:
                ss.record_close("cto", "bad00009", bad, locks_dir=locks)
                _mark(False, f"status={bad!r} should have raised")
            except ValueError:
                _mark(True, f"status={bad!r} raised")
        # None is not a str and must also be rejected, not silently stored.
        try:
            ss.record_close("cto", "bad00009", None, locks_dir=locks)  # type: ignore[arg-type]
            _mark(False, "status=None should have raised")
        except (ValueError, TypeError):
            _mark(True, "status=None raised")


def test_resume_uuid_copied_from_uuid_fixture() -> None:
    print("resume_uuid is copied from the .uuid fixture at close time")
    with tempfile.TemporaryDirectory() as t:
        locks = _fresh(Path(t))
        uuid = "11111111-2222-3333-4444-555555feed00"
        _write_uuid(locks, "cto", "copy0004", uuid)
        ss.record_close("cto", "copy0004", "saved", note="park", locks_dir=locks)
        row = ss.get("cto", "copy0004")
        _mark(row["resume_uuid"] == uuid,
              "resume_uuid column holds the UUID read from the .uuid file")
        # The column survives the .uuid file being removed by hand later —
        # that is the whole reason the column exists alongside the file.
        (locks / f"{lock_basename('cto','copy0004')}{_UUID_SUFFIX}").unlink()
        _mark(ss.resume_target("cto", "copy0004", locks_dir=locks) == uuid,
              "resume_target still returns the UUID from the column after the file is gone")


def test_resume_target_falls_back_to_file() -> None:
    print("resume_target falls back to the .uuid file when the column is empty")
    with tempfile.TemporaryDirectory() as t:
        locks = _fresh(Path(t))
        uuid = "99999999-8888-7777-6666-555555aaa000"
        _write_uuid(locks, "cto", "fall0005", uuid)
        # A pre-rollout row: registered at spawn, never closed through this
        # writer, so resume_uuid is NULL but the .uuid file is present.
        db.register_cxo_session("cto", "fall0005")
        row = ss.get("cto", "fall0005")
        _mark(row["resume_uuid"] is None,
              "pre-rollout row has a NULL resume_uuid column")
        _mark(ss.resume_target("cto", "fall0005", locks_dir=locks) == uuid,
              "resume_target falls back to the .uuid file")
        # Nothing in either source -> None.
        _mark(ss.resume_target("cto", "ghost999", locks_dir=locks) is None,
              "no column value and no file -> None")


def test_list_sessions_filters_by_status() -> None:
    print("list_sessions('saved') returns only saved rows")
    with tempfile.TemporaryDirectory() as t:
        locks = _fresh(Path(t))
        ss.record_close("cto", "one00011", "saved", locks_dir=locks)
        ss.record_close("cto", "two00012", "force_saved", locks_dir=locks)
        ss.record_close("cto", "thr00013", "closed", locks_dir=locks)
        db.register_cxo_session("cto", "fou00014")  # stays 'open'
        saved = ss.list_sessions("saved")
        _mark([r["session_id"] for r in saved] == ["one00011"],
              "list_sessions('saved') returns only the saved row")
        all_rows = {r["session_id"] for r in ss.list_sessions()}
        _mark(all_rows == {"one00011", "two00012", "thr00013", "fou00014"},
              "list_sessions() returns every row")
        try:
            ss.list_sessions("bogus")
            _mark(False, "list_sessions(bogus) should raise")
        except ValueError:
            _mark(True, "list_sessions rejects an invalid status")


def test_looks_like_uuid() -> None:
    print("looks_like_uuid rejects short ids, accepts real uuids")
    _mark(ss.looks_like_uuid("11111111-2222-3333-4444-555555feed00") is True,
          "a real RFC4122-shaped uuid passes")
    _mark(ss.looks_like_uuid("0aef5968") is False,
          "an 8-hex short id (the org's session id, NOT a uuid) is rejected")
    _mark(ss.looks_like_uuid("") is False, "empty string is rejected")
    _mark(ss.looks_like_uuid(None) is False, "None is rejected")


def test_cli_resume_prefers_db_then_refuses() -> None:
    print("CLI resume: DB fallback when file is missing, refusal when neither exists")
    with tempfile.TemporaryDirectory() as t:
        locks = _fresh(Path(t))
        uuid = "22222222-3333-4444-5555-666666600001"
        # Closed session whose .uuid file was deleted after close — the exact
        # shape of task-a98788d7's bug (measured live: 41 of 42 closed cto
        # sessions were in this state on 2026-09-18).
        ss.record_close("cto", "gap00001", "closed", locks_dir=locks)
        with sqlite3.connect(str(db.DB_PATH)) as con:
            con.execute(
                "UPDATE c_level_sessions SET resume_uuid=? "
                "WHERE role='cto' AND session_id='gap00001'", (uuid,))
        rc = ss.main(["resume", "--role", "cto", "--session-id", "gap00001",
                      "--locks-dir", str(locks)])
        _mark(rc == 0, "resume subcommand exits 0 when the DB has the uuid")

        rc = ss.main(["resume", "--role", "cto", "--session-id", "ghost999",
                      "--locks-dir", str(locks)])
        _mark(rc == 1, "resume subcommand exits 1 for a session with no uuid anywhere")


def test_cli_main_records_row() -> None:
    """The CLI scripts/session-kill.sh drives (python -m tools.session_status)."""
    print("CLI main() records the row the same way record_close does")
    with tempfile.TemporaryDirectory() as t:
        locks = _fresh(Path(t))
        uuid = "deadbeef-0000-1111-2222-3333000000aa"
        _write_uuid(locks, "cto", "cli0000aa", uuid)
        rc = ss.main(["close", "--role", "cto", "--session-id", "cli0000aa",
                      "--status", "force_saved", "--note", "tests red",
                      "--locks-dir", str(locks)])
        _mark(rc == 0, "close subcommand exits 0")
        row = ss.get("cto", "cli0000aa")
        _mark(row and row["status"] == "force_saved"
              and row["note"] == "tests red"
              and row["resume_uuid"] == uuid,
              "CLI recorded status + note + resume_uuid")


if __name__ == "__main__":
    test_alter_guard_backfills_open()
    test_init_is_idempotent()
    test_record_close_sets_closed_at_for_each_status()
    test_invalid_status_raises()
    test_resume_uuid_copied_from_uuid_fixture()
    test_resume_target_falls_back_to_file()
    test_list_sessions_filters_by_status()
    test_looks_like_uuid()
    test_cli_resume_prefers_db_then_refuses()
    test_cli_main_records_row()
    print()
    print("ALL PASS" if not _failures else f"FAILED — {_failures} failure(s)")
    raise SystemExit(1 if _failures else 0)
