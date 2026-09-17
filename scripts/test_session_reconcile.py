"""Tests for tools/session_reconcile.py.

task-9ff9263f. session_reconcile walks every status='open' c_level_sessions
row and, using the same liveness check scripts/session_list.py already
displays with (tmux_lock_live), flips a dead one to 'abandoned'. These pin:

  1. a dead row is marked 'abandoned' under --apply, untouched under dry-run
  2. a live row (tmux_lock_live mocked True) is never touched
  3. a row on another host is never touched, and is counted separately
  4. a NULL-host (legacy) row IS checked on this machine
  5. idempotent: a second run does not re-touch an already-abandoned row
  6. an existing note is appended to, not overwritten
  7. normalize_owner_cto strips the 'cto-' prefix, idempotently, and leaves
     everything else alone

Run via:  .venv/bin/python scripts/test_session_reconcile.py
"""
from __future__ import annotations

import sys
import tempfile
import unittest.mock as mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db  # noqa: E402
from tools import session_reconcile as sr  # noqa: E402

_failures = 0


def _mark(ok: bool, label: str) -> None:
    global _failures
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    if not ok:
        _failures += 1


def _fresh(tmp: Path) -> None:
    db.DB_PATH = tmp / "tasks.db"
    db.init()


def _seed(role: str, sid: str, *, host: str | None = None,
          note: str | None = None, status: str = "open") -> None:
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO c_level_sessions (role, session_id, spawned_at, "
            "status, host, note) VALUES (?, ?, ?, ?, ?, ?)",
            (role, sid, db.now_iso(), status, host, note),
        )


def sr_get(role: str, sid: str) -> dict:
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM c_level_sessions WHERE role=? AND session_id=?",
            (role, sid),
        ).fetchone()
    return dict(row)


def test_dead_row_marked_only_under_apply() -> None:
    print("dead row: marked abandoned under --apply, untouched under dry-run")
    with tempfile.TemporaryDirectory() as t:
        _fresh(Path(t))
        _seed("cto", "dead0001")
        with mock.patch.object(sr, "tmux_lock_live", return_value=False), \
             mock.patch.object(sr, "_this_host", return_value="mac"):
            dry = sr.reconcile(apply=False)
            row = sr_get("cto", "dead0001")
            _mark(row["status"] == "open",
                  "dry-run: row status untouched (still open)")
            _mark(("cto", "dead0001") in dry["marked"],
                  "dry-run: row reported as would-mark")

            real = sr.reconcile(apply=True)
            row = sr_get("cto", "dead0001")
            _mark(row["status"] == "abandoned",
                  "apply: row flipped to abandoned")
            _mark(row["closed_at"] is not None, "apply: closed_at set")
            _mark(row["note"] == "reconciled: tmux gone",
                  "apply: note set (no prior note)")
            _mark(("cto", "dead0001") in real["marked"],
                  "apply: row reported as marked")


def test_live_row_never_touched() -> None:
    print("live row (tmux_lock_live=True): never touched")
    with tempfile.TemporaryDirectory() as t:
        _fresh(Path(t))
        _seed("cto", "live0001")
        with mock.patch.object(sr, "tmux_lock_live", return_value=True), \
             mock.patch.object(sr, "_this_host", return_value="mac"):
            result = sr.reconcile(apply=True)
        row = sr_get("cto", "live0001")
        _mark(row["status"] == "open", "live row stays 'open'")
        _mark(("cto", "live0001") not in result["marked"],
              "live row not in marked list")
        _mark(result["checked"] == 1, "live row was checked (not skipped)")


def test_other_host_never_touched() -> None:
    print("other-host row: never touched, counted separately")
    with tempfile.TemporaryDirectory() as t:
        _fresh(Path(t))
        _seed("cto", "remote01", host="contabo")
        with mock.patch.object(sr, "tmux_lock_live", return_value=False), \
             mock.patch.object(sr, "_this_host", return_value="mac"):
            result = sr.reconcile(apply=True)
        row = sr_get("cto", "remote01")
        _mark(row["status"] == "open", "other-host row stays 'open'")
        _mark(result["checked"] == 0, "other-host row not counted as checked")
        _mark(("cto", "remote01", "contabo") in result["skipped_other_host"],
              "other-host row reported as skipped")


def test_null_host_legacy_row_is_checked() -> None:
    print("NULL-host (legacy, pre-migration) row: checked on this machine")
    with tempfile.TemporaryDirectory() as t:
        _fresh(Path(t))
        _seed("cto", "legacy01", host=None)
        with mock.patch.object(sr, "tmux_lock_live", return_value=False), \
             mock.patch.object(sr, "_this_host", return_value="mac"):
            result = sr.reconcile(apply=True)
        row = sr_get("cto", "legacy01")
        _mark(row["status"] == "abandoned",
              "NULL-host row IS checked and marked (legacy = this machine)")
        _mark(result["checked"] == 1, "counted as checked, not skipped")


def test_idempotent_second_run_is_noop() -> None:
    print("idempotent: second run does not re-touch an already-abandoned row")
    with tempfile.TemporaryDirectory() as t:
        _fresh(Path(t))
        _seed("cto", "twice001")
        with mock.patch.object(sr, "tmux_lock_live", return_value=False), \
             mock.patch.object(sr, "_this_host", return_value="mac"):
            sr.reconcile(apply=True)
            row1 = sr_get("cto", "twice001")
            second = sr.reconcile(apply=True)
        row2 = sr_get("cto", "twice001")
        _mark(second["total_open"] == 0,
              "second run sees zero 'open' rows left")
        _mark(row1["note"] == row2["note"],
              "note unchanged by the second run (not re-appended)")
        _mark(row1["closed_at"] == row2["closed_at"],
              "closed_at unchanged by the second run")


def test_existing_note_is_appended_not_overwritten() -> None:
    print("existing note is appended to, not clobbered")
    with tempfile.TemporaryDirectory() as t:
        _fresh(Path(t))
        _seed("cto", "noted001", note="original note")
        with mock.patch.object(sr, "tmux_lock_live", return_value=False), \
             mock.patch.object(sr, "_this_host", return_value="mac"):
            sr.reconcile(apply=True)
        row = sr_get("cto", "noted001")
        _mark(row["note"] == "original note; reconciled: tmux gone",
              "prior note preserved, new note appended")


def test_protected_live_sessions_never_marked() -> None:
    """The exact scenario the task brief calls out by name: a session with a
    genuinely live tmux must never flip to abandoned, no matter what."""
    print("protected sessions (tmux_lock_live=True) are never marked, "
          "mirrors the real 4a904905/3859781c guard")
    with tempfile.TemporaryDirectory() as t:
        _fresh(Path(t))
        _seed("cto", "4a904905")
        _seed("cto", "3859781c")
        with mock.patch.object(sr, "tmux_lock_live", return_value=True), \
             mock.patch.object(sr, "_this_host", return_value="mac"):
            result = sr.reconcile(apply=True)
        for sid in ("4a904905", "3859781c"):
            row = sr_get("cto", sid)
            _mark(row["status"] == "open", f"{sid} stays 'open'")
        _mark(len(result["marked"]) == 0, "nothing marked when all rows are live")


def test_normalize_owner_cto_strips_prefix_idempotently() -> None:
    print("normalize_owner_cto strips 'cto-' prefix, idempotent, leaves rest alone")
    with tempfile.TemporaryDirectory() as t:
        _fresh(Path(t))
        ts = db.now_iso()
        with db.get_conn() as conn:
            conn.execute(
                "INSERT INTO tasks (id,project,role,status,title,description,"
                "depends_on,touches,owner_cto,created_at,updated_at) VALUES "
                "(?,?,?,?,?,?,?,?,?,?,?)",
                ("task-aaa1", "proj", "developer", "done", "t", "d",
                 "[]", "[]", "cto-eab87266", ts, ts),
            )
            conn.execute(
                "INSERT INTO tasks (id,project,role,status,title,description,"
                "depends_on,touches,owner_cto,created_at,updated_at) VALUES "
                "(?,?,?,?,?,?,?,?,?,?,?)",
                ("task-aaa2", "proj", "developer", "done", "t", "d",
                 "[]", "[]", "eab87266", ts, ts),
            )
        dry = sr.normalize_owner_cto(apply=False)
        _mark(dry == 1, "dry-run counts exactly the 1 prefixed row")
        n = sr.normalize_owner_cto(apply=True)
        _mark(n == 1, "apply fixes exactly the 1 prefixed row")
        t1 = db.get_task("task-aaa1")
        t2 = db.get_task("task-aaa2")
        _mark(t1["owner_cto"] == "eab87266", "prefix stripped")
        _mark(t2["owner_cto"] == "eab87266", "already-clean row untouched")
        again = sr.normalize_owner_cto(apply=True)
        _mark(again == 0, "idempotent: second run matches zero rows")


if __name__ == "__main__":
    test_dead_row_marked_only_under_apply()
    test_live_row_never_touched()
    test_other_host_never_touched()
    test_null_host_legacy_row_is_checked()
    test_idempotent_second_run_is_noop()
    test_existing_note_is_appended_not_overwritten()
    test_protected_live_sessions_never_marked()
    test_normalize_owner_cto_strips_prefix_idempotently()
    print()
    print("ALL PASS" if not _failures else f"FAILED — {_failures} failure(s)")
    raise SystemExit(1 if _failures else 0)
