"""Tests for the tombstone behaviour scripts/hub/cutover-mac.sh step 5
introduces (task-7ad6ad8a): once state/tasks.db is archived and replaced
with a directory, lib.db._connect() must raise a clear, specific error
instead of sqlite3's generic "unable to open database file", and hooks that
read the registry must fail OPEN with that message rather than crash or
refuse forever.

Everything lives under tmp_path -- the real state/tasks.db is never opened.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import db as db_mod  # noqa: E402


def test_connect_refuses_real_checkout_under_pytest(tmp_path: Path) -> None:
    """ADR 0021 addendum (2026-09-18): PYTEST_CURRENT_TEST is always set
    inside a test (pytest sets it itself), so this exercises the guard
    directly against a fabricated 'real checkout' -- a directory carrying a
    `.git` entry -- without touching the actual repo root."""
    fake_checkout = tmp_path / "Agents"
    (fake_checkout / "state").mkdir(parents=True)
    (fake_checkout / ".git").write_text("gitdir: /elsewhere\n")
    fake_db = fake_checkout / "state" / "tasks.db"
    with pytest.raises(RuntimeError, match="ADR 0021"):
        db_mod._connect(path=fake_db)


def test_connect_allows_tmp_path_without_git(tmp_path: Path) -> None:
    """The same shape one level up, minus the `.git` entry -- the ordinary
    tmp_path fixture every other test in this repo already relies on --
    must NOT be refused."""
    fake_checkout = tmp_path / "Agents"
    (fake_checkout / "state").mkdir(parents=True)
    fake_db = fake_checkout / "state" / "tasks.db"
    conn = db_mod._connect(path=fake_db)
    conn.close()


def test_connect_on_directory_raises_archived_db(tmp_path: Path) -> None:
    tombstone = tmp_path / "tasks.db"
    tombstone.mkdir()
    with pytest.raises(db_mod.ArchivedDB, match="tasks.db is archived"):
        db_mod._connect(path=tombstone)


def test_connect_on_directory_readonly_also_raises(tmp_path: Path) -> None:
    tombstone = tmp_path / "tasks.db"
    tombstone.mkdir()
    with pytest.raises(db_mod.ArchivedDB):
        db_mod._connect(path=tombstone, readonly=True)


def test_get_conn_surfaces_archived_db(tmp_path: Path) -> None:
    tombstone = tmp_path / "tasks.db"
    tombstone.mkdir()
    with pytest.raises(db_mod.ArchivedDB):
        with db_mod.get_conn(path=tombstone, readonly=True):
            pass


def test_self_repo_guard_fails_open_on_archived_hub(tmp_path: Path, capsys) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "hook_self_repo_guard_tombstone",
        ROOT / "scripts" / "hook-self-repo-guard.py")
    assert spec is not None and spec.loader is not None
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)

    checkout = tmp_path / "Agents"
    wt = checkout / "worktrees" / "mooniex-agents__developer__task-aaaaaaaa"
    for d in ("lib", "runners", "tools", "policies", "config", "scripts",
              "state/locks", "output", ".claude"):
        (wt / d).mkdir(parents=True, exist_ok=True)
    # The tombstone: canonical tasks.db (checkout/state/tasks.db) is a
    # directory, not a file -- exactly what step 5 leaves behind.
    (checkout / "state" / "tasks.db").mkdir(parents=True, exist_ok=True)

    event = {"tool_name": "Edit", "tool_input": {"file_path": "lib/db.py"}}
    code, _msg = guard.decide(event, cwd=str(wt))

    assert code == 0
    err = capsys.readouterr().err
    assert "tasks.db is archived (hub cutover done)" in err
    assert "/terminal-restart" in err


def test_hook_log_prompt_degrades_cleanly_on_archived_hub(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """scripts/hook-log-prompt.py's _task_owners() already catches any
    Exception broadly and degrades to "no filtering data" -- prove that
    still holds for the new ArchivedDB, i.e. it never crashes the hook."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "hook_log_prompt_tombstone",
        ROOT / "scripts" / "hook-log-prompt.py")
    assert spec is not None and spec.loader is not None
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)

    tombstone = tmp_path / "tasks.db"
    tombstone.mkdir()
    monkeypatch.setattr(hook.db_lib, "DB_PATH", tombstone)

    owners = hook._task_owners({"task-aaaaaaaa"})
    assert owners == {}
