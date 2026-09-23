"""tools/workdir.py — Work/<task_id>/ folder lifecycle (task-36aaa3c4,
Work/RULES.md, ADR 0030).

create/check/close/orphans, all injected with a `root=tmp_path` (or a
`db=<temp sqlite path>` for orphans) — never the real ~/MoonieXHQ/Work/ or
the real state/tasks.db.

Run via:  pytest tests/test_workdir.py
(not in pytest.ini's default testpaths [scripts, lib] — run explicitly,
same convention as tests/test_delegate_disk_floor.py.)
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import tools.workdir as workdir  # noqa: E402

TASK = "task-abc12345"
OTHER = "task-deadbeef"


# --------------------------------------------------------------------- create

def test_create_makes_in_tmp_out(tmp_path):
    folder = workdir.create(TASK, root=tmp_path)
    assert folder == tmp_path / TASK
    for sub in ("in", "tmp", "out"):
        assert (folder / sub).is_dir()


def test_create_is_idempotent(tmp_path):
    workdir.create(TASK, root=tmp_path)
    (tmp_path / TASK / "in" / "keep.txt").write_text("x")
    workdir.create(TASK, root=tmp_path)  # must not wipe existing content
    assert (tmp_path / TASK / "in" / "keep.txt").exists()


def test_create_refuses_bad_task_id(tmp_path):
    with pytest.raises(ValueError):
        workdir.create("not-a-task-id", root=tmp_path)
    with pytest.raises(ValueError):
        workdir.create("task-short", root=tmp_path)  # not 8 hex chars


# ---------------------------------------------------------------------- check

def test_check_clean_folder_has_no_violations(tmp_path):
    workdir.create(TASK, root=tmp_path)
    assert workdir.check(TASK, root=tmp_path) == []


def test_check_flags_unexpected_root_entry(tmp_path):
    folder = workdir.create(TASK, root=tmp_path)
    (folder / "stray.txt").write_text("x")
    violations = workdir.check(TASK, root=tmp_path)
    assert any("stray.txt" in v for v in violations)


def test_check_flags_unfiled_input(tmp_path):
    folder = workdir.create(TASK, root=tmp_path)
    (folder / "in" / "photo.jpg").write_bytes(b"x")
    violations = workdir.check(TASK, root=tmp_path)
    assert any("photo.jpg" in v and "unfiled" in v for v in violations)


def test_check_sources_coverage_clears_violation(tmp_path):
    folder = workdir.create(TASK, root=tmp_path)
    (folder / "in" / "photo.jpg").write_bytes(b"x")
    (folder / "in" / "SOURCES.txt").write_text(
        "photo.jpg\thttps://example.com/photo.jpg\tdeadbeef\n"
    )
    assert workdir.check(TASK, root=tmp_path) == []


def test_check_flags_symlink(tmp_path):
    folder = workdir.create(TASK, root=tmp_path)
    real = tmp_path / "outside.txt"
    real.write_text("x")
    (folder / "tmp" / "link.txt").symlink_to(real)
    violations = workdir.check(TASK, root=tmp_path)
    assert any(v.startswith("symlink:") for v in violations)


def test_check_flags_dot_git(tmp_path):
    folder = workdir.create(TASK, root=tmp_path)
    (folder / "tmp" / ".git").mkdir()
    violations = workdir.check(TASK, root=tmp_path)
    assert any("git repo" in v for v in violations)


def test_check_flags_dotenv(tmp_path):
    folder = workdir.create(TASK, root=tmp_path)
    (folder / "in" / ".env").write_text("SECRET=1")
    violations = workdir.check(TASK, root=tmp_path)
    assert any("secret-like file" in v and ".env" in v for v in violations)


def test_check_missing_folder_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        workdir.check(TASK, root=tmp_path)


# ---------------------------------------------------------------------- close

def test_close_keeps_unfiled_files_and_the_folder(tmp_path):
    folder = workdir.create(TASK, root=tmp_path)
    (folder / "tmp" / "scratch.bin").write_bytes(b"x" * 10)
    (folder / "in" / "unfiled.jpg").write_bytes(b"y" * 5)
    (folder / "out" / "deliverable.mp4").write_bytes(b"z" * 7)

    result = workdir.close(TASK, root=tmp_path)

    assert result["closed"] is False
    joined = " ".join(result["unfiled"])
    assert "unfiled.jpg" in joined
    assert "deliverable.mp4" in joined
    assert folder.is_dir()  # the folder stays
    assert not (folder / "tmp").exists()  # tmp/ is always wiped
    assert (folder / "in" / "unfiled.jpg").exists()  # no SOURCES line -> kept
    assert (folder / "out" / "deliverable.mp4").exists()  # out/ never touched


def test_close_deletes_sourced_in_files_even_when_it_cannot_fully_close(tmp_path):
    folder = workdir.create(TASK, root=tmp_path)
    (folder / "tmp" / "scratch.bin").write_bytes(b"x" * 10)
    (folder / "in" / "sourced.jpg").write_bytes(b"y" * 5)
    (folder / "in" / "SOURCES.txt").write_text(
        "sourced.jpg\thttps://example.com/sourced.jpg\tabc123\n"
    )
    (folder / "out" / "deliverable.mp4").write_bytes(b"z" * 7)  # blocks full close

    result = workdir.close(TASK, root=tmp_path)

    assert result["closed"] is False
    assert not (folder / "tmp").exists()
    assert not (folder / "in" / "sourced.jpg").exists()  # covered by SOURCES -> deleted
    assert (folder / "out" / "deliverable.mp4").exists()  # left for filing


def test_empty_close_removes_folder_and_writes_one_ledger_line(tmp_path):
    folder = workdir.create(TASK, root=tmp_path)
    (folder / "tmp" / "scratch.bin").write_bytes(b"x" * 10)
    (folder / "in" / "sourced.jpg").write_bytes(b"y" * 5)
    (folder / "in" / "SOURCES.txt").write_text(
        "sourced.jpg\thttps://example.com/sourced.jpg\tabc123\n"
    )

    result = workdir.close(TASK, root=tmp_path, by="test-actor")

    assert result["closed"] is True
    assert not folder.exists()

    ledger = tmp_path / "_ledger.jsonl"
    lines = ledger.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["task"] == TASK
    assert entry["by"] == "test-actor"
    assert entry["bytes"] == 15  # 10 (tmp) + 5 (sourced.jpg)
    assert set(entry) == {"ts", "task", "bytes", "dest", "md5", "by"}


def test_close_missing_folder_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        workdir.close(TASK, root=tmp_path)


# ---------------------------------------------------------- close(archive=True)

def _matching_uploader():
    import tools.work_archive as work_archive

    def _uploader(local_path, dest_name):
        _, md5 = work_archive._hash_file(local_path)
        return {"id": "fake-" + dest_name, "name": dest_name, "md5Checksum": md5}
    return _uploader


def test_close_archive_true_verified_deletes_and_fills_ledger(tmp_path, monkeypatch):
    import tools.work_archive as work_archive
    monkeypatch.setattr(work_archive, "LOG_PATH", str(tmp_path / "drive-archive.log"))
    monkeypatch.setattr(work_archive, "_default_uploader", _matching_uploader())

    folder = workdir.create(TASK, root=tmp_path)
    (folder / "in" / "unfiled.jpg").write_bytes(b"y" * 5)
    (folder / "out" / "deliverable.mp4").write_bytes(b"z" * 7)

    result = workdir.close(TASK, root=tmp_path, archive=True, by="test-actor")

    assert result["closed"] is True
    assert not folder.exists()

    ledger = tmp_path / "_ledger.jsonl"
    entry = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    assert entry["bytes"] == 12  # 5 + 7, both archived-then-deleted
    assert entry["dest"].startswith(f"Agents-Work-{TASK}-")
    assert entry["md5"]  # local md5 of the tar, non-empty
    assert set(entry) == {"ts", "task", "bytes", "dest", "md5", "by"}


def test_close_archive_true_mismatch_keeps_folder_and_files(tmp_path, monkeypatch):
    import tools.work_archive as work_archive
    monkeypatch.setattr(work_archive, "LOG_PATH", str(tmp_path / "drive-archive.log"))

    def _bad_uploader(local_path, dest_name):
        return {"id": "x", "name": dest_name, "md5Checksum": "0" * 32}
    monkeypatch.setattr(work_archive, "_default_uploader", _bad_uploader)

    folder = workdir.create(TASK, root=tmp_path)
    (folder / "in" / "unfiled.jpg").write_bytes(b"y" * 5)
    (folder / "out" / "deliverable.mp4").write_bytes(b"z" * 7)

    result = workdir.close(TASK, root=tmp_path, archive=True)

    assert result["closed"] is False
    assert "archive_error" in result and "mismatch" in result["archive_error"]
    assert folder.is_dir()
    assert (folder / "in" / "unfiled.jpg").exists()
    assert (folder / "out" / "deliverable.mp4").exists()
    assert not (tmp_path / "_ledger.jsonl").exists()


def test_close_without_archive_flag_leaves_unfiled_as_before(tmp_path):
    """archive defaults False -- close() behaves exactly as it did pre-task-abc20690."""
    folder = workdir.create(TASK, root=tmp_path)
    (folder / "out" / "deliverable.mp4").write_bytes(b"z" * 7)

    result = workdir.close(TASK, root=tmp_path)

    assert result["closed"] is False
    assert "archive_error" not in result
    assert (folder / "out" / "deliverable.mp4").exists()


def test_close_dry_run_makes_no_filesystem_changes(tmp_path):
    folder = workdir.create(TASK, root=tmp_path)
    (folder / "tmp" / "scratch.bin").write_bytes(b"x")
    (folder / "in" / "unfiled.jpg").write_bytes(b"y")

    result = workdir.close(TASK, root=tmp_path, dry_run=True)

    assert result["dry_run"] is True
    assert result["closed"] is False
    assert (folder / "tmp" / "scratch.bin").exists()
    assert (folder / "in" / "unfiled.jpg").exists()
    assert not (tmp_path / "_ledger.jsonl").exists()


def test_close_never_touches_another_tasks_folder(tmp_path):
    workdir.create(TASK, root=tmp_path)
    other = workdir.create(OTHER, root=tmp_path)
    (other / "in" / "not-mine.jpg").write_bytes(b"x")

    workdir.close(TASK, root=tmp_path)  # empty -> closes fine, touches only TASK

    assert other.is_dir()
    assert (other / "in" / "not-mine.jpg").exists()


# -------------------------------------------------------------------- orphans

@pytest.fixture()
def temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    db_mod.init()
    return db_path


def _new_task(owner: str = "x") -> str:
    return db_mod.create_task(project="mooniex-agents", role="developer",
                              title="orphan test", description="d",
                              owner_cto=owner)


def _set_updated_at(db_path: Path, task_id: str, iso_ts: str) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.execute("UPDATE tasks SET updated_at=? WHERE id=?", (iso_ts, task_id))
    conn.commit()
    conn.close()


def test_orphans_flags_done_task_older_than_24h(temp_db, tmp_path):
    tid = _new_task()
    db_mod.update_status(tid, "done", actor="test")
    old_ts = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    _set_updated_at(temp_db, tid, old_ts)
    workdir.create(tid, root=tmp_path)

    rows = workdir.orphans(temp_db, root=tmp_path)

    assert len(rows) == 1
    assert rows[0]["task"] == tid
    assert rows[0]["status"] == "done"
    assert rows[0]["flagged"] is True


def test_orphans_does_not_flag_recent_done_task(temp_db, tmp_path):
    tid = _new_task()
    db_mod.update_status(tid, "done", actor="test")
    workdir.create(tid, root=tmp_path)

    rows = workdir.orphans(temp_db, root=tmp_path)

    assert len(rows) == 1
    assert rows[0]["flagged"] is False


def test_orphans_skips_active_task(temp_db, tmp_path):
    tid = _new_task()  # status stays 'pending' (active)
    workdir.create(tid, root=tmp_path)

    assert workdir.orphans(temp_db, root=tmp_path) == []


def test_orphans_flags_unknown_task(temp_db, tmp_path):
    workdir.create("task-00000000", root=tmp_path)  # no matching row in tasks.db

    rows = workdir.orphans(temp_db, root=tmp_path)

    assert len(rows) == 1
    assert rows[0]["status"] == "unknown"
    assert rows[0]["flagged"] is True


def test_orphans_is_read_only(temp_db, tmp_path):
    tid = _new_task()
    db_mod.update_status(tid, "done", actor="test")
    folder = workdir.create(tid, root=tmp_path)
    (folder / "in" / "x.jpg").write_bytes(b"x")

    workdir.orphans(temp_db, root=tmp_path)

    assert folder.is_dir()
    assert (folder / "in" / "x.jpg").exists()
