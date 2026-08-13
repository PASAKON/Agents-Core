"""Tests for runners/dev_mcp_server.py `dev_message` (GH #54).

Two independent silent losses existed on every call:
  1. `.splitlines()[0]` -- only the first line of a multi-line report
     survived; everything after it vanished.
  2. `[:300]` -- the surviving line was cut at 300 chars with no marker.
`dev_message` always returned "ack" regardless, so neither the DEV nor the
CTO could tell a report had been cut.

The fix persists the FULL stripped text into `tasks.last_checkpoint` (an
existing column -- no schema change) on every call, and only caps the
one-line console/log rendering. When the console line had to be trimmed
(extra lines dropped and/or the first line itself over the cap), both the
log line and the returned ack carry an explicit truncation marker.

pytest style, tmp_path fixtures only (ADR 0021 §1). Points `lib.db.DB_PATH`
at a tmp_path sqlite file -- never touches the real state/tasks.db.
`ORG_NOTIFY_SILENT=1` plus `lib.notify._under_test()`'s own `pytest` /
`test_*` entry-point guard mean `info()` never writes to the real
state/logs/cto.log either.
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("ORG_NOTIFY_SILENT", "1")

import lib.db as db_mod  # noqa: E402
import runners.dev_mcp_server as dm  # noqa: E402


def _insert_task(conn) -> str:
    tid = "task-" + uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute(
        """INSERT INTO tasks
           (id, project, role, status, title, description,
            depends_on, touches, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (tid, "test-proj", "developer", "in_progress", "t", "d",
         "[]", "[]", ts, ts),
    )
    conn.commit()
    return tid


@pytest.fixture()
def dev_task(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Isolated tasks.db with one fixture task; dm.TASK_ID pointed at it."""
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    with db_mod.get_conn() as conn:
        tid = _insert_task(conn)
    monkeypatch.setattr(dm, "TASK_ID", tid)
    return tid


def _checkpoint(tid: str) -> str:
    return db_mod.get_task(tid)["last_checkpoint"]


def test_empty_text_stays_empty_marker(dev_task):
    ack = dm.dev_message("   ")
    assert ack == "ack"
    assert _checkpoint(dev_task) == "(empty)"


def test_single_short_line_no_false_truncation(dev_task):
    ack = dm.dev_message("reading wiki")
    assert ack == "ack"
    assert "truncated" not in ack
    assert _checkpoint(dev_task) == "reading wiki"


def test_multiline_text_fully_persisted_and_marked_truncated(dev_task):
    text = (
        'entries >=5 credits exist, not clean. Three of them: "130 credits '
        'Seedance 2.5 Spent Aug 10", "72 credits Seedance 2.0 Spent Aug 5" '
        "(offset by refund same day, net 0), and\n"
        '"72 credits Seedance 2.0 Spent Aug 5 3:44 PM"\n'
        "date: 2026-08-05"
    )
    ack = dm.dev_message(text)

    # Full text -- all 3 lines -- must survive in last_checkpoint. This is
    # the exact class of loss measured on task-cda4f469 (the date on the
    # third line was the field that mattered and used to be dropped).
    assert _checkpoint(dev_task) == text
    assert "date: 2026-08-05" in _checkpoint(dev_task)

    # ack must say so, not just "ack".
    assert ack.startswith("ack (truncated:")
    assert "3 lines" in ack
    assert f"{len(text)} chars" in ack
    assert f"→ {dm.DEV_MESSAGE_LOG_CAP}" in ack


def test_long_single_line_marks_char_truncation_not_line_count(dev_task):
    """A single line longer than the cap must still be marked -- the old
    bug's second silent loss (`[:300]` with no marker) independent of the
    multi-line loss."""
    long_line = "x" * (dm.DEV_MESSAGE_LOG_CAP + 50)
    ack = dm.dev_message(long_line)

    assert _checkpoint(dev_task) == long_line
    assert ack.startswith("ack (truncated:")
    assert "1 lines" in ack
    assert f"{len(long_line)} chars" in ack


def test_no_task_id_returns_error_without_touching_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    monkeypatch.setattr(dm, "TASK_ID", "")

    ack = dm.dev_message("hello")
    assert ack == "ERROR: DEV_TASK_ID env var not set"
