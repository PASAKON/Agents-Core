"""tests/test_spoke_touches_sidecar.py — GH #180 (task-378523bb).

Covers scripts/hook-self-repo-guard.py's new sidecar path: a worktree's own
<root>/.org-task.json (written at spawn time by
tools/delegate.py::_spawn_remote's linux branch, decoded by
scripts/spawn-worker-remote.sh) lets the guard decide without a matching row
in the worktree's own state/tasks.db — the gap that blocked every
Edit/Write/write-flagged Bash of a mooniex-agents task spawned on Contabo
(that box's tasks.db is an unsynced snapshot of the Mac hub, task-a5c0549d
finding, docs/design/multi-host-workers.md §7b).

Run:  pytest tests/test_spoke_touches_sidecar.py
(also picked up by a plain `pytest` — testpaths includes `tests`.)
"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK_SRC = ROOT / "scripts" / "hook-self-repo-guard.py"


def _load_hook():
    spec = importlib.util.spec_from_file_location(
        "hook_self_repo_guard_sidecar_test", HOOK_SRC)
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


def _build_checkout(tmp_path: Path, *, db_touches: dict[str, list[str]] | None = None,
                     task_id: str = "task-aaaaaaaa") -> tuple[Path, Path]:
    """A fake `<checkout>/worktrees/mooniex-agents__developer__<task_id>`
    with a real `<checkout>/lib/` (protected, ADR 0020) and a
    `<checkout>/state/tasks.db` carrying only the rows in `db_touches` — an
    empty dict simulates a spoke's unsynced snapshot missing this task's row
    entirely (GH #180). Returns (checkout, worktree)."""
    checkout = tmp_path / "checkout"
    (checkout / "lib").mkdir(parents=True)
    (checkout / "lib" / "foo.py").write_text("x = 1\n")
    worktrees_dir = checkout / "worktrees"
    worktrees_dir.mkdir()
    wt = worktrees_dir / f"mooniex-agents__developer__{task_id}"
    (wt / "scripts").mkdir(parents=True)
    (wt / "lib").mkdir()
    (wt / "prototypes").mkdir()

    state_dir = checkout / "state"
    state_dir.mkdir()
    db_path = state_dir / "tasks.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    for tid, touches in (db_touches or {}).items():
        conn.execute(
            "INSERT INTO tasks (id, project, role, status, title, description, "
            "touches, created_at, updated_at) VALUES "
            "(?,'mooniex-agents','developer','in_progress','t','d',?,'2026-01-01','2026-01-01')",
            (tid, json.dumps(touches)),
        )
    conn.commit()
    conn.close()
    return checkout, wt


def _write_sidecar(wt: Path, *, task_id: str, touches: list[str]) -> None:
    (wt / MOD.SIDECAR_NAME).write_text(json.dumps({
        "task_id": task_id, "project": "mooniex-agents", "role": "developer",
        "host": "contabo", "owner_cto": "test-owner", "touches": touches,
    }))


def _decide_write(cwd: Path, file_path: str) -> tuple[int, str]:
    event = {"tool_name": "Write", "tool_input": {"file_path": file_path}}
    return MOD.decide(event, cwd=str(cwd))


# ---------------------------------------------------------------------------
# 1. A sidecar with no matching db row: the whole point of GH #180 — the
#    guard must still decide, using the sidecar alone.
# ---------------------------------------------------------------------------

def test_sidecar_accepts_declared_path_with_no_db_row(tmp_path: Path) -> None:
    checkout, wt = _build_checkout(tmp_path, db_touches={})
    _write_sidecar(wt, task_id="task-aaaaaaaa", touches=["prototypes/contabo-smoke/**"])
    code, _ = _decide_write(wt, str(wt / "prototypes" / "contabo-smoke" / "composition.html"))
    assert code == 0


def test_sidecar_refuses_undeclared_path_with_no_db_row(tmp_path: Path) -> None:
    checkout, wt = _build_checkout(tmp_path, db_touches={})
    _write_sidecar(wt, task_id="task-aaaaaaaa", touches=["prototypes/contabo-smoke/**"])
    code, msg = _decide_write(wt, str(wt / "lib" / "bad.py"))
    assert code == 2
    assert "load-bearing org runtime" in msg


# ---------------------------------------------------------------------------
# 2. A sidecar left by a PRIOR occupant of this worktree path (spawn-worker-
#    remote.sh reuses paths, GH #151-style hazard) must be ignored.
# ---------------------------------------------------------------------------

def test_sidecar_with_mismatched_task_id_is_ignored(tmp_path: Path) -> None:
    checkout, wt = _build_checkout(tmp_path, db_touches={})
    _write_sidecar(wt, task_id="task-STALE001", touches=["lib/**"])  # a stale, over-broad grant
    code, msg = _decide_write(wt, str(wt / "lib" / "bad.py"))
    # falls back to the (empty) db -> no row -> refused undecidable, never
    # trusting the stale sidecar's lib/** grant
    assert code == 2
    assert "STALE001" not in msg


# ---------------------------------------------------------------------------
# 3. The Mac path (db row, no sidecar at all) is completely unchanged.
# ---------------------------------------------------------------------------

def test_mac_path_unchanged_without_sidecar(tmp_path: Path) -> None:
    checkout, wt = _build_checkout(
        tmp_path, db_touches={"task-aaaaaaaa": ["scripts/allowed.py"]},
    )
    code_ok, _ = _decide_write(wt, str(wt / "scripts" / "allowed.py"))
    code_bad, msg = _decide_write(wt, str(wt / "lib" / "bad.py"))
    assert code_ok == 0
    assert code_bad == 2
    assert "load-bearing org runtime" in msg


# ---------------------------------------------------------------------------
# 4. The sidecar file is itself protected — a worker cannot edit its own
#    grant to escalate what it may touch, even when the guard is otherwise
#    deciding purely from the sidecar (no db row at all).
# ---------------------------------------------------------------------------

def test_sidecar_file_itself_is_protected(tmp_path: Path) -> None:
    checkout, wt = _build_checkout(tmp_path, db_touches={})
    _write_sidecar(wt, task_id="task-aaaaaaaa", touches=["prototypes/contabo-smoke/**"])
    code, msg = _decide_write(wt, str(wt / MOD.SIDECAR_NAME))
    assert code == 2
    assert "load-bearing org runtime" in msg


# ---------------------------------------------------------------------------
# 5. Unit-level coverage of the new helpers directly.
# ---------------------------------------------------------------------------

def test_load_touches_from_sidecar_missing_file_returns_none(tmp_path: Path) -> None:
    checkout, wt = _build_checkout(tmp_path, db_touches={})
    assert MOD.load_touches_from_sidecar(wt, "task-aaaaaaaa") is None


def test_load_touches_from_sidecar_malformed_json_returns_none(tmp_path: Path) -> None:
    checkout, wt = _build_checkout(tmp_path, db_touches={})
    (wt / MOD.SIDECAR_NAME).write_text("{not json")
    assert MOD.load_touches_from_sidecar(wt, "task-aaaaaaaa") is None


def test_load_touches_for_falls_back_to_db_when_no_sidecar(tmp_path: Path) -> None:
    checkout, wt = _build_checkout(
        tmp_path, db_touches={"task-aaaaaaaa": ["scripts/allowed.py"]},
    )
    assert MOD.load_touches_for(wt, "task-aaaaaaaa") == ["scripts/allowed.py"]


def test_load_touches_for_prefers_sidecar_over_db(tmp_path: Path) -> None:
    checkout, wt = _build_checkout(
        tmp_path, db_touches={"task-aaaaaaaa": ["scripts/allowed.py"]},
    )
    _write_sidecar(wt, task_id="task-aaaaaaaa", touches=["prototypes/contabo-smoke/**"])
    assert MOD.load_touches_for(wt, "task-aaaaaaaa") == ["prototypes/contabo-smoke/**"]
