"""Disk floor guard (ADR 0030, task-bfa778ab) — tools/delegate.py delegate_task.

The Mac hit 0 bytes free on 2026-09-23 and every tool died. delegate_task
now measures free space on "/" before spawning; below `gauge.orange` GB
(config/storage-policy.yaml) it refuses the spawn, leaves the task's status
untouched, writes a delegate_log line, and returns the task row dict (same
shape as every other delegate_task refusal path — a bare string here would
break lib/org_tools_registry.py:196's `_slim_task(await do_delegate(...))`
and delegate_parallel_tasks' gather, per CTO reopen feedback iter1). Above
the floor, behaviour is unchanged.

`tools.delegate._free_gb` is the injection seam (module-level function,
not an env var — an env var could disable the guard in prod) tests
monkeypatch to fake free-space readings, never real disk state.

Run via:  pytest tests/test_delegate_disk_floor.py
(collected by the default `pytest` run — pytest.ini `testpaths` now
includes `tests` alongside `scripts lib`.)
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import tools.delegate as delegate  # noqa: E402


@pytest.fixture()
def temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    # owner_cto="test-owner" below is synthetic with no c_level_sessions row.
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    # Storage scope (CEO 2026-09-23): "test-owner" is in scope for every
    # ADR 0030 feature this file exercises (disk_floor, sparse_worktree,
    # work_dir), mirroring the old single pilot_owner_cto list's effect
    # before the per-feature scope map replaced it.
    monkeypatch.setattr(delegate, "_scope_owners", lambda feature: ["test-owner"])
    db_mod.init()
    return db_mod


def _new_task(db_mod_, owner: str = "test-owner") -> str:
    return db_mod_.create_task(
        project="mooniex-agents", role="developer",
        title="disk floor test", description="d",
        owner_cto=owner,
    )


# ---------------------------------------------------------------------------
# Below the floor: refused, status unchanged, delegate_log written, error
# string returned.
# ---------------------------------------------------------------------------

def test_low_disk_refuses_spawn_and_leaves_status_unchanged(temp_db, monkeypatch):
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 4.0)
    tid = _new_task(temp_db)
    before = temp_db.get_task(tid)
    assert before["status"] == "pending"

    result = asyncio.run(delegate.delegate_task(tid))

    assert isinstance(result, dict)  # task row dict, not a bare string
    assert result["id"] == tid
    assert result["status"] == "pending"  # unchanged, per ADR 0030
    assert "disk red" in result["delegate_log"]
    assert "4.0" in result["delegate_log"]
    assert "5.0" in result["delegate_log"]  # gauge.orange floor from config/storage-policy.yaml

    after = temp_db.get_task(tid)
    assert after["status"] == "pending"  # unchanged, per ADR 0030
    assert "disk red" in (after["delegate_log"] or "")


def test_low_disk_never_calls_the_spawn_step(temp_db, monkeypatch):
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 4.0)

    def _boom(*a, **k):
        raise AssertionError("spawn step must not be reached below the disk floor")

    monkeypatch.setattr(delegate, "_spawn_iterm_tab", _boom)
    monkeypatch.setattr(delegate, "create_worktree", _boom)

    tid = _new_task(temp_db)
    asyncio.run(delegate.delegate_task(tid))  # raises via monkeypatch if reached


# ---------------------------------------------------------------------------
# Above the floor: behaviour unchanged — proceeds to the spawn step (stubbed
# here so the test never opens a real iTerm tab).
# ---------------------------------------------------------------------------

def test_sufficient_disk_proceeds_to_spawn_step(temp_db, monkeypatch, tmp_path):
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 6.0)

    fake_project = {
        "path": "/tmp/does-not-matter",
        "default_branch": "main",
        "agents_allowed": ["developer"],
        "spawn_backend": "iterm",
        "web_ui": "off",
    }
    monkeypatch.setattr(delegate, "get_project", lambda key: fake_project)

    created = {}

    def fake_create_worktree(project_key, role, task_id, sparse=False):
        created["sparse"] = sparse
        info = {
            "project": project_key, "task_id": task_id, "role": role,
            "branch": f"agent/{role}-{task_id}",
            "worktree": f"/tmp/fake-worktree-{task_id}",
            "base": "main", "repo": fake_project["path"], "provisioned": [],
        }
        created["worktree_info"] = info
        return info

    monkeypatch.setattr(delegate, "create_worktree", fake_create_worktree)

    spawn_calls = []
    spawn_kwargs = []

    def fake_spawn_iterm_tab(role, task_id, **kw):
        spawn_calls.append((role, task_id))
        spawn_kwargs.append(kw)
        return "spawned"

    monkeypatch.setattr(delegate, "_spawn_iterm_tab", fake_spawn_iterm_tab)

    tid = _new_task(temp_db)  # owner_cto="test-owner" -> pilot-scoped (this file's temp_db fixture)
    result = asyncio.run(delegate.delegate_task(tid))

    assert "worktree_info" in created, "create_worktree (the spawn step) was never reached"
    assert len(spawn_calls) == 1
    # ADR 0030 / task-36aaa3c4 iter1: this task's owner is pilot-scoped, so
    # delegate_task must have created a Work/ folder and passed WORK_DIR
    # through to the spawn step -- and it must land under this test's own
    # tmp_path (conftest.py's autouse `_isolate_workdir_root`), never the
    # real ~/MoonieXHQ/Work/.
    work_dir = spawn_kwargs[0].get("work_dir")
    assert work_dir is not None
    assert Path(work_dir).is_relative_to(tmp_path)
    assert Path(work_dir).is_dir()
    assert isinstance(result, dict)  # normal path still returns the task row
    assert result["worktree"] == created["worktree_info"]["worktree"]
    assert created["sparse"] is True  # pilot owner → sparse worktree


def test_low_disk_does_not_refuse_another_sessions_task(temp_db, monkeypatch):
    """Scope (CEO 2026-09-23: "Scope เฉพาะงานตัวเองก่อน"): a task owned by a
    CTO session outside the `disk_floor`/`sparse_worktree` scope is never
    refused by the floor and gets a full (non-sparse) checkout."""
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 1.0)
    monkeypatch.setattr(delegate, "get_project", lambda key: {
        "path": "/tmp/does-not-matter", "default_branch": "main",
        "agents_allowed": ["developer"], "spawn_backend": "iterm", "web_ui": "off"})
    seen = {}

    def fake_create_worktree(project_key, role, task_id, sparse=False):
        seen["sparse"] = sparse
        return {"project": project_key, "task_id": task_id, "role": role,
                "branch": f"agent/{role}-{task_id}", "worktree": f"/tmp/fake-{task_id}",
                "base": "main", "repo": "/tmp/does-not-matter", "provisioned": []}

    monkeypatch.setattr(delegate, "create_worktree", fake_create_worktree)
    monkeypatch.setattr(delegate, "_spawn_iterm_tab", lambda role, task_id, **kw: "spawned")

    tid = _new_task(temp_db, owner="someone-else")
    result = asyncio.run(delegate.delegate_task(tid))

    assert "disk red" not in (result.get("delegate_log") or "")
    assert seen.get("sparse") is False


def test_missing_scope_key_applies_to_nobody(monkeypatch, tmp_path):
    p = tmp_path / "policy.yaml"
    p.write_text("gauge: {orange: 5}\n")  # no `scope` key at all
    monkeypatch.setattr(delegate, "STORAGE_POLICY", p)
    assert delegate._scope_owners("disk_floor") is None
    assert delegate._scope_applies("disk_floor", "0e8d80b8") is False


def test_scope_present_but_feature_missing_applies_to_nobody(monkeypatch, tmp_path):
    """`scope` exists but doesn't mention this feature — same fail-closed
    result as no `scope` key at all. This would fail if `_scope_owners`
    defaulted a missing feature to "all" or to the first entry it finds."""
    p = tmp_path / "policy.yaml"
    p.write_text("scope: {reclaim: all}\n")  # disk_floor absent
    monkeypatch.setattr(delegate, "STORAGE_POLICY", p)
    assert delegate._scope_owners("disk_floor") is None
    assert delegate._scope_applies("disk_floor", "any-owner") is False


def test_scope_all_covers_every_owner_including_none(monkeypatch, tmp_path):
    """This fails if `_scope_applies` were changed to require a truthy
    owner_cto even under "all" — "all" must cover a C-level's own
    ownerless task too, not just named CTO sessions."""
    p = tmp_path / "policy.yaml"
    p.write_text("scope: {disk_floor: all}\n")
    monkeypatch.setattr(delegate, "STORAGE_POLICY", p)
    assert delegate._scope_applies("disk_floor", "0e8d80b8") is True
    assert delegate._scope_applies("disk_floor", "some-random-owner") is True
    assert delegate._scope_applies("disk_floor", None) is True


def test_scope_list_covers_members_only(monkeypatch, tmp_path):
    """This fails if `_scope_applies` fell back to "applies to everyone"
    for a list scope, or matched a falsy owner_cto against the list."""
    p = tmp_path / "policy.yaml"
    p.write_text("scope: {disk_floor: ['owner-a', 'owner-b']}\n")
    monkeypatch.setattr(delegate, "STORAGE_POLICY", p)
    assert delegate._scope_applies("disk_floor", "owner-a") is True
    assert delegate._scope_applies("disk_floor", "owner-c") is False
    assert delegate._scope_applies("disk_floor", None) is False
