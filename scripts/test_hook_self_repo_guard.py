"""Tests for scripts/hook-self-repo-guard.py (ADR 0020).

Focus: the logical-vs-physical audit for ADR 0028 step 4b hazard #2. The
guard's own `classify()` already resolves `os.path.realpath` on both the
worktree root and the write target (`_real()` / `real_root` in
hook-self-repo-guard.py) — these tests are the regression proof that stays
green whether Agents-Core is reached via its OLD (now-symlinked) path or its
NEW physical one, in either direction, as the task brief requires.

Run:  /Users/gob/Projects/Agents/.venv/bin/python -m pytest scripts/test_hook_self_repo_guard.py -q
"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOK_SRC = ROOT / "scripts" / "hook-self-repo-guard.py"


def _load_hook():
    spec = importlib.util.spec_from_file_location("hook_self_repo_guard_under_test", HOOK_SRC)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


MOD = _load_hook()

_SCHEMA = """
CREATE TABLE tasks (
    id TEXT PRIMARY KEY, project TEXT NOT NULL, role TEXT NOT NULL,
    status TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL,
    touches TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
"""


def _build_checkout(tmp_path: Path, *, touches: list[str]) -> tuple[Path, Path]:
    """A fake `<checkout>/worktrees/mooniex-agents__developer__task-XXXXXXXX`
    with a real `<checkout>/lib/` (protected, ADR 0020) and a real
    `<checkout>/state/tasks.db` declaring `touches` for that task. Returns
    (checkout, worktree)."""
    checkout = tmp_path / "checkout"
    (checkout / "lib").mkdir(parents=True)
    (checkout / "lib" / "foo.py").write_text("x = 1\n")
    worktrees_dir = checkout / "worktrees"
    worktrees_dir.mkdir()
    wt = worktrees_dir / "mooniex-agents__developer__task-aaaaaaaa"
    (wt / "scripts").mkdir(parents=True)
    (wt / "lib").mkdir()  # the worktree's OWN copy of lib/ — also protected

    state_dir = checkout / "state"
    state_dir.mkdir()
    db_path = state_dir / "tasks.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    conn.execute(
        "INSERT INTO tasks (id, project, role, status, title, description, touches, created_at, updated_at) "
        "VALUES ('task-aaaaaaaa','mooniex-agents','developer','in_progress','t','d',?, '2026-01-01','2026-01-01')",
        (json.dumps(touches),),
    )
    conn.commit()
    conn.close()
    return checkout, wt


def _decide_write(cwd: Path, file_path: str) -> tuple[int, str]:
    event = {"tool_name": "Write", "tool_input": {"file_path": file_path}}
    return MOD.decide(event, cwd=str(cwd))


# --------------------------------------------------------------------------
# baseline (sanity — no symlinks involved)
# --------------------------------------------------------------------------

def test_refuses_undeclared_lib_write_in_worktree(tmp_path: Path) -> None:
    checkout, wt = _build_checkout(tmp_path, touches=["scripts/allowed.py"])
    code, msg = _decide_write(wt, str(wt / "lib" / "bad.py"))
    assert code == 2
    assert "load-bearing org runtime" in msg


def test_allows_declared_write_in_worktree(tmp_path: Path) -> None:
    checkout, wt = _build_checkout(tmp_path, touches=["scripts/allowed.py"])
    code, _ = _decide_write(wt, str(wt / "scripts" / "allowed.py"))
    assert code == 0


# --------------------------------------------------------------------------
# ADR 0028 step 4b hazard #2 — logical vs physical
# --------------------------------------------------------------------------

def test_refuses_write_outside_worktree_reached_via_logical_alias_of_checkout(tmp_path: Path) -> None:
    """The write target is spelled through a symlink alias of the PARENT
    checkout (stands in for the OLD /Users/gob/Projects/Agents path once it
    becomes a compat symlink after the move) — must be refused exactly like
    the physical form, since real_target and real_parent both resolve
    through realpath before comparison."""
    checkout, wt = _build_checkout(tmp_path, touches=["scripts/allowed.py"])
    logical_checkout = tmp_path / "logical-checkout-alias"
    logical_checkout.symlink_to(checkout)

    target_physical = str(checkout / "lib" / "foo.py")
    target_logical = str(logical_checkout / "lib" / "foo.py")

    code_physical, msg_physical = _decide_write(wt, target_physical)
    code_logical, msg_logical = _decide_write(wt, target_logical)

    assert code_physical == 2
    assert code_logical == 2
    assert "OUTSIDE this worktree into the live checkout" in msg_physical
    assert "OUTSIDE this worktree into the live checkout" in msg_logical


def test_same_verdict_when_cwd_is_a_logical_alias_of_the_checkout(tmp_path: Path) -> None:
    """Mirror case: the SESSION's own cwd is reported through a symlink alias
    of the checkout ROOT (the real shape a compat symlink takes: it replaces
    exactly the top segment — /Users/gob/Projects/Agents -> .../Core — never
    the `worktrees/task-XXXXXXXX` segments beneath it, so worktree_root()'s
    literal "parent dir is named 'worktrees'" check still fires through it).
    classify() must reach the same verdict as an unaliased cwd."""
    checkout, wt = _build_checkout(tmp_path, touches=["scripts/allowed.py"])
    logical_checkout = tmp_path / "logical-checkout-alias"
    logical_checkout.symlink_to(checkout)
    logical_wt = logical_checkout / "worktrees" / wt.name

    code_physical, _ = _decide_write(wt, str(wt / "lib" / "bad.py"))
    code_logical, _ = _decide_write(logical_wt, str(logical_wt / "lib" / "bad.py"))

    assert code_physical == 2
    assert code_logical == 2


def test_declared_write_still_allowed_through_logical_checkout_alias(tmp_path: Path) -> None:
    checkout, wt = _build_checkout(tmp_path, touches=["scripts/allowed.py"])
    logical_checkout = tmp_path / "logical-checkout-alias"
    logical_checkout.symlink_to(checkout)
    logical_wt = logical_checkout / "worktrees" / wt.name

    code, _ = _decide_write(logical_wt, str(logical_wt / "scripts" / "allowed.py"))
    assert code == 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
