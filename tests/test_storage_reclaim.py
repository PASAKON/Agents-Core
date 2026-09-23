"""tools/storage_reclaim.py plan()/apply() + tools/delegate.py orange/red
trigger (ADR 0030 §2/§8, task-44963fee).

Every fixture writes only under tmp_path -- no test here may touch the real
tasks.db, the real worktrees dir, or ~/MoonieXHQ/Work/ (the root conftest.py
autouse fixtures already isolate ORG_ROOT and workdir's default root; this
file additionally never calls apply() without an explicit tmp_path-based
ledger_path).

`_has_live_dev_process` is stubbed to False for every test in this file --
the "no live dev process" half of the dormancy test shells out to ps/lsof,
which is slow and depends on what else happens to be running on the box;
only the file-mtime half is exercised here (which is what the brief's test
list actually asks for).

Run via:  pytest tests/test_storage_reclaim.py
(not in pytest.ini's default testpaths [scripts, lib] -- run explicitly,
same convention as tests/test_delegate_disk_floor.py.)
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import tools.delegate as delegate  # noqa: E402
import tools.storage_reclaim as storage_reclaim  # noqa: E402

OLD_MTIME = time.time() - 20 * 86400   # older than the 14-day dormancy window
RECENT_MTIME = time.time()


@pytest.fixture(autouse=True)
def _stub_live_dev_process(monkeypatch):
    monkeypatch.setattr(storage_reclaim, "_has_live_dev_process", lambda worktree: False)


def _mkfile(path: Path, mtime: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x")
    os.utime(path, (mtime, mtime))


def _policy() -> dict:
    return {
        "gauge": {"green": 20, "yellow": 10, "orange": 5, "red": 0},
        "tiers": {
            "HOT": [], "NEVER": [], "COLD": [],
            "REBUILD": [
                {"glob": "**/node_modules", "rebuild": "npm ci", "dormancy": True},
                {"glob": "**/.venv", "rebuild": "uv sync", "dormancy": True},
                {"glob": "**/__pycache__", "rebuild": "python re-imports"},
            ],
        },
    }


@pytest.fixture()
def temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    db_mod.init()
    return db_mod


def _mk_task(db_mod_, worktree: Path, owner: str) -> str:
    tid = db_mod_.create_task(
        project="mooniex-agents", role="developer",
        title="storage reclaim test", description="d",
        owner_cto=owner,
    )
    db_mod_.set_fields(tid, worktree=str(worktree))
    return tid


# --------------------------------------------------------------------- plan

def test_plan_only_touches_pilot_owned_worktrees(temp_db, tmp_path):
    pilot_wt = tmp_path / "worktrees" / "pilot-task"
    _mkfile(pilot_wt / "src" / "main.py", OLD_MTIME)
    _mkfile(pilot_wt / "node_modules" / "pkg" / "index.js", OLD_MTIME)
    _mkfile(pilot_wt / "__pycache__" / "a.pyc", OLD_MTIME)

    other_wt = tmp_path / "worktrees" / "other-task"
    _mkfile(other_wt / "src" / "main.py", OLD_MTIME)
    _mkfile(other_wt / "node_modules" / "pkg" / "index.js", OLD_MTIME)

    _mk_task(temp_db, pilot_wt, "pilot-owner")
    _mk_task(temp_db, other_wt, "someone-else")

    items = storage_reclaim.plan(str(temp_db.DB_PATH), _policy(), ["pilot-owner"])

    paths = {i["path"] for i in items}
    assert str(pilot_wt / "node_modules") in paths
    assert str(pilot_wt / "__pycache__") in paths
    assert not any(str(other_wt) in p for p in paths), (
        "a non-pilot worktree's node_modules must never appear in the plan"
    )


def test_non_pilot_worktrees_node_modules_survives_apply(temp_db, tmp_path):
    """The non-pilot task's node_modules is never even planned, so applying
    the plan can never touch it either."""
    other_wt = tmp_path / "worktrees" / "other-task"
    _mkfile(other_wt / "node_modules" / "pkg" / "index.js", OLD_MTIME)
    _mk_task(temp_db, other_wt, "someone-else")

    items = storage_reclaim.plan(str(temp_db.DB_PATH), _policy(), ["pilot-owner"])
    storage_reclaim.apply(items, ledger_path=tmp_path / "ledger.jsonl")

    assert (other_wt / "node_modules").is_dir()
    assert (other_wt / "node_modules" / "pkg" / "index.js").exists()


def test_dormancy_entry_with_recent_file_survives(temp_db, tmp_path):
    wt = tmp_path / "worktrees" / "pilot-recent"
    _mkfile(wt / "src" / "main.py", RECENT_MTIME)  # recent activity elsewhere
    _mkfile(wt / "node_modules" / "pkg" / "index.js", OLD_MTIME)
    _mkfile(wt / "__pycache__" / "a.pyc", OLD_MTIME)

    _mk_task(temp_db, wt, "pilot-owner")

    items = storage_reclaim.plan(str(temp_db.DB_PATH), _policy(), ["pilot-owner"])

    paths = {i["path"] for i in items}
    assert str(wt / "node_modules") not in paths, "recent file anywhere in the worktree must gate dormancy entries"
    assert str(wt / "__pycache__") in paths, "a non-dormancy entry is unaffected by the dormancy gate"


def test_dormancy_ignores_recent_files_inside_excluded_dirs(temp_db, tmp_path):
    """A file freshly written INSIDE node_modules/.venv/.git (e.g. npm
    touching its own tree) must not itself count as 'recent activity' --
    the dormancy test explicitly excludes those subtrees."""
    wt = tmp_path / "worktrees" / "pilot-npm-churn"
    _mkfile(wt / "src" / "main.py", OLD_MTIME)
    _mkfile(wt / "node_modules" / "pkg" / "index.js", RECENT_MTIME)

    _mk_task(temp_db, wt, "pilot-owner")

    items = storage_reclaim.plan(str(temp_db.DB_PATH), _policy(), ["pilot-owner"])
    paths = {i["path"] for i in items}
    assert str(wt / "node_modules") in paths


def test_symlinked_node_modules_is_skipped(temp_db, tmp_path):
    wt = tmp_path / "worktrees" / "pilot-symlink"
    real_target = tmp_path / "real_node_modules"
    _mkfile(real_target / "pkg" / "index.js", OLD_MTIME)
    _mkfile(wt / "src" / "main.py", OLD_MTIME)
    os.symlink(real_target, wt / "node_modules")

    _mk_task(temp_db, wt, "pilot-owner")

    items = storage_reclaim.plan(str(temp_db.DB_PATH), _policy(), ["pilot-owner"])
    assert not any(i["path"] == str(wt / "node_modules") for i in items)

    # Belt-and-suspenders: even handed the symlink path directly, apply()
    # must refuse to rmtree it.
    fake_item = {"path": str(wt / "node_modules"), "bytes": 0, "reason": "npm ci",
                 "task": "task-00000000", "owner": "pilot-owner"}
    deleted = storage_reclaim.apply([fake_item], ledger_path=tmp_path / "ledger.jsonl")
    assert deleted == []
    assert real_target.is_dir()
    assert (real_target / "pkg" / "index.js").exists()


# -------------------------------------------------------------------- apply

def test_apply_writes_ledger_lines(tmp_path):
    target = tmp_path / "reclaim-me"
    _mkfile(target / "file.txt", OLD_MTIME)
    item = {"path": str(target), "bytes": 123, "reason": "npm ci",
            "task": "task-aaaaaaaa", "owner": "pilot-owner"}
    ledger = tmp_path / "state" / "storage" / "reclaim.jsonl"

    deleted = storage_reclaim.apply([item], ledger_path=ledger)

    assert deleted == [item]
    assert not target.exists()

    lines = ledger.read_text().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["path"] == str(target)
    assert entry["bytes"] == 123
    assert entry["task"] == "task-aaaaaaaa"
    assert entry["owner"] == "pilot-owner"
    parsed = datetime.fromisoformat(entry["ts"])
    assert parsed.utcoffset() is not None, "ts must carry a UTC offset"


def test_apply_appends_without_truncating(tmp_path):
    ledger = tmp_path / "reclaim.jsonl"
    t1 = tmp_path / "one"
    t2 = tmp_path / "two"
    _mkfile(t1 / "f.txt", OLD_MTIME)
    _mkfile(t2 / "f.txt", OLD_MTIME)

    storage_reclaim.apply(
        [{"path": str(t1), "bytes": 1, "reason": "r", "task": "task-1", "owner": "o"}],
        ledger_path=ledger,
    )
    storage_reclaim.apply(
        [{"path": str(t2), "bytes": 2, "reason": "r", "task": "task-2", "owner": "o"}],
        ledger_path=ledger,
    )

    lines = ledger.read_text().splitlines()
    assert len(lines) == 2


# --------------------------------------------------- delegate.py trigger

@pytest.fixture()
def delegate_db(monkeypatch, tmp_path):
    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setattr(delegate, "_storage_pilot_owners", lambda: ["test-owner"])
    db_mod.init()
    return db_mod


def _new_delegate_task(db_mod_, owner: str = "test-owner") -> str:
    return db_mod_.create_task(
        project="mooniex-agents", role="developer",
        title="storage reclaim trigger test", description="d",
        owner_cto=owner,
    )


def _stub_spawn_path(monkeypatch):
    fake_project = {
        "path": "/tmp/does-not-matter", "default_branch": "main",
        "agents_allowed": ["developer"], "spawn_backend": "iterm", "web_ui": "off",
    }
    monkeypatch.setattr(delegate, "get_project", lambda key: fake_project)

    def fake_create_worktree(project_key, role, task_id, sparse=False):
        return {"project": project_key, "task_id": task_id, "role": role,
                "branch": f"agent/{role}-{task_id}", "worktree": f"/tmp/fake-{task_id}",
                "base": "main", "repo": fake_project["path"], "provisioned": []}

    monkeypatch.setattr(delegate, "create_worktree", fake_create_worktree)
    monkeypatch.setattr(delegate, "_spawn_iterm_tab", lambda role, task_id, **kw: "spawned")


def test_delegate_runs_reclaim_when_pilot_and_orange(delegate_db, monkeypatch):
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 8.0)  # orange: 5 <= 8 < 10
    calls: list[int] = []
    monkeypatch.setattr(delegate, "_run_storage_reclaim", lambda: (calls.append(1), (0, 0))[1])
    _stub_spawn_path(monkeypatch)

    tid = _new_delegate_task(delegate_db)
    asyncio.run(delegate.delegate_task(tid))

    assert calls == [1]


def test_delegate_runs_reclaim_when_pilot_and_red(delegate_db, monkeypatch):
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 2.0)  # red: < 5
    calls: list[int] = []
    monkeypatch.setattr(delegate, "_run_storage_reclaim", lambda: (calls.append(1), (0, 0))[1])

    tid = _new_delegate_task(delegate_db)
    result = asyncio.run(delegate.delegate_task(tid))

    assert calls == [1]
    assert "disk red" in (result.get("delegate_log") or ""), "floor check must still run after reclaim"


def test_delegate_skips_reclaim_when_green(delegate_db, monkeypatch):
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 25.0)  # green: >= 20
    calls: list[int] = []
    monkeypatch.setattr(delegate, "_run_storage_reclaim", lambda: (calls.append(1), (0, 0))[1])
    _stub_spawn_path(monkeypatch)

    tid = _new_delegate_task(delegate_db)
    asyncio.run(delegate.delegate_task(tid))

    assert calls == []


def test_delegate_skips_reclaim_for_non_pilot_task(delegate_db, monkeypatch):
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 2.0)  # red, but not pilot-owned
    calls: list[int] = []
    monkeypatch.setattr(delegate, "_run_storage_reclaim", lambda: (calls.append(1), (0, 0))[1])
    _stub_spawn_path(monkeypatch)

    tid = _new_delegate_task(delegate_db, owner="someone-else")
    result = asyncio.run(delegate.delegate_task(tid))

    assert calls == []
    assert "disk red" not in (result.get("delegate_log") or "")


def test_delegate_reclaim_failure_does_not_block_spawn(delegate_db, monkeypatch):
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 8.0)  # orange, above the 5 GB floor

    def _explode():
        raise RuntimeError("boom")

    monkeypatch.setattr(delegate, "_run_storage_reclaim", _explode)
    _stub_spawn_path(monkeypatch)

    tid = _new_delegate_task(delegate_db)
    result = asyncio.run(delegate.delegate_task(tid))

    assert result["worktree"] == f"/tmp/fake-{tid}", "spawn must proceed despite the reclaim exception"
