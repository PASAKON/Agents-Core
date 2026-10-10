"""Spawn reliability regressions; all host services and config files are fakes."""
import asyncio
import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from tools import delegate as d
from tools import gc_stale_tasks as gc
from tools import worktree as wt


@pytest.fixture
def spawn(monkeypatch, tmp_path):
    task = dict(id="task-test", role="developer", project="test", status="pending",
                worktree=str(tmp_path / "wt"), owner_cto="abc", delegate_log="router: claude")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    (tmp_path / ".claude.json").write_text("{}")
    monkeypatch.setattr(d, "ROOT", tmp_path)
    monkeypatch.setattr(d.sys, "platform", "linux")
    monkeypatch.setattr(d, "self_host", lambda: "contabo")
    monkeypatch.setattr(d, "_write_task_sidecar", Mock())
    monkeypatch.setattr(d, "_work_dir_for", lambda *a: None)
    monkeypatch.setattr(d, "_spawn_background", lambda coro: coro.close())
    monkeypatch.setattr(d.db, "get_task", lambda *a: task)
    def fields(*a, **kw):
        task.update({k: v for k, v in kw.items() if k != "actor"})
    def status(tid, value, **kw):
        task["status"] = value
        fields(**kw)
    monkeypatch.setattr(d.db, "set_fields", fields)
    monkeypatch.setattr(d.db, "update_status", status)
    monkeypatch.setattr(d.db, "release_task_locks", Mock())
    for name in ("info", "warn", "error", "success"):
        monkeypatch.setattr(d, name, Mock())
    monkeypatch.setattr(d.tmux, "create", Mock())
    monkeypatch.setattr(d.tmux, "capture", Mock(return_value=""))
    monkeypatch.setattr(d, "_spawn_iterm_tab", Mock(return_value="spawned"))
    return task


@pytest.mark.parametrize("failure", [RuntimeError("not alive"), subprocess.CalledProcessError(1, "tmux")])
def test_dead_spawn_returns_failed_and_releases_locks(spawn, monkeypatch, failure):
    d.tmux.create.side_effect = failure
    row = asyncio.run(d._spawn_local(spawn, {}))
    assert row["status"] == "failed"
    assert str(failure) in row["delegate_log"]
    d.db.release_task_locks.assert_called_once_with("task-test", "test")
    d.success.assert_not_called()


def test_trust_is_written_before_spawn_and_preserves_settings(spawn):
    path = d._claude_config_path()
    key = str(Path(spawn["worktree"]).resolve())
    path.write_text(json.dumps({"other": 7, "projects": {"elsewhere": {"x": 1}, key: {"allowedTools": ["Read"]}}}))
    def create(*a, **kw):
        data = json.loads(path.read_text())
        assert data == {"other": 7, "projects": {"elsewhere": {"x": 1}, key: {"allowedTools": ["Read"], "hasTrustDialogAccepted": True}}}
    d.tmux.create.side_effect = create
    asyncio.run(d._spawn_local(spawn, {}))
    d.tmux.create.assert_called_once()


def test_atomic_write_failure_preserves_original(tmp_path, monkeypatch):
    path = tmp_path / "claude.json"
    path.write_text('{"keep": true}')
    monkeypatch.setattr(d.os, "replace", Mock(side_effect=OSError("race")))
    with pytest.raises(OSError):
        d._trust_worktree(str(tmp_path / "wt"), path)
    assert path.read_text() == '{"keep": true}'
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("claimed", [False, True])
def test_verify_detects_trust_even_after_claim(spawn, monkeypatch, claimed):
    monkeypatch.setattr(d, "CLAIM_VERIFY_DELAY_S", 0)
    if claimed:
        spawn.update(status="in_progress", assigned_agent="dev")
    d.tmux.capture.return_value = "No, exit\nYes, I trust this folder"
    asyncio.run(d._verify_claimed("task-test", "developer", "abc", kickoff_text="go", tmux_sess="wd-test"))
    assert spawn["status"] == "failed"
    assert "Yes, I trust this folder" in spawn["delegate_log"]
    d.db.release_task_locks.assert_called_once()


def test_kickoff_never_sends_at_trust_dialog(spawn, monkeypatch):
    from tools import send_to_worker
    send = Mock()
    monkeypatch.setattr(send_to_worker, "send", send)
    monkeypatch.setattr(d, "KICKOFF_DELAY_S", 0)
    spawn["tmux_session"] = "wd-test"
    d.tmux.capture.return_value = "Yes, I trust this folder"
    asyncio.run(d._auto_kickoff("task-test", "go"))
    send.assert_not_called()
    assert spawn["status"] == "failed"


@pytest.mark.parametrize("has_owner", [False, True])
def test_mac_owner_warning_is_appended(spawn, monkeypatch, has_owner):
    monkeypatch.setattr(d.sys, "platform", "darwin")
    if has_owner:
        locks = d.ROOT / "state" / "locks"
        locks.mkdir(parents=True)
        (locks / "cto-abc.winid").write_text("123")
    asyncio.run(d._spawn_local(spawn, {}))
    assert spawn["delegate_log"].startswith("router: claude")
    assert ("WARNING" in spawn["delegate_log"]) is (not has_owner)


def test_applescript_requires_tmux_and_creates_fallback_window():
    script = d._build_spawn_applescript("echo hello", "task-test", "abc")
    reuse = next(line for line in script.splitlines() if 'tabName contains "(task-test)"' in line)
    assert 'and ((tabName contains "(tmux)") or (sessName contains "(tmux)"))' in reuse
    assert "set targetWin to current window" not in script
    assert script.count("set targetWin to (create window with default profile)") == 2


@pytest.mark.parametrize("branch_exists", [False, True])
def test_restore_preserves_existing_branch(tmp_path, monkeypatch, branch_exists):
    monkeypatch.setattr(wt, "_repo_path", lambda *a: tmp_path)
    monkeypatch.setattr(wt.subprocess, "run", Mock(return_value=subprocess.CompletedProcess([], 0 if branch_exists else 1)))
    run = Mock()
    monkeypatch.setattr(wt, "_run", run)
    monkeypatch.setattr(wt, "provision_worktree", Mock())
    path = tmp_path / "checkout"
    result = wt.restore_worktree("test", "developer", "task-test", path=str(path), branch="agent/saved")
    if branch_exists:
        assert result == {"worktree": str(path), "branch": "agent/saved"}
        assert run.call_args_list[-1].args[0] == ["git", "worktree", "add", str(path), "agent/saved"]
    else:
        assert result is None
        run.assert_not_called()
    assert all("-D" not in call.args[0] for call in run.call_args_list)


@pytest.mark.parametrize("dry_run", [False, True])
def test_gc_clears_worktree_only_after_removal(spawn, monkeypatch, dry_run):
    path = Path(spawn["worktree"])
    path.mkdir()
    monkeypatch.setattr(gc, "_worktree_git_status", lambda *a: "")
    monkeypatch.setattr(gc, "remove_worktree", lambda *a: path.rmdir())
    result = gc._reclaim_worktree(spawn, dry_run=dry_run)
    assert result["action"] == ("would_remove" if dry_run else "removed")
    assert spawn["worktree"] == (str(path) if dry_run else None)


# Reuse the existing isolated DB and spawn fixture for the public entry point.
from test_w03_self_host_spawn import local_spawn, temp_db, _new_task


@pytest.mark.parametrize("recorded_path,existing_branch", [(True, True), (False, True), (True, False)])
def test_redelegate_restores_or_creates(local_spawn, temp_db, monkeypatch, tmp_path,
                                       recorded_path, existing_branch):
    monkeypatch.setattr(d, "self_host", lambda: "contabo")
    monkeypatch.setattr(d.sys, "platform", "linux")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    (tmp_path / ".claude.json").write_text("{}")
    tid = _new_task(temp_db)
    missing = str(tmp_path / "missing")
    temp_db.set_fields(tid, worktree=missing if recorded_path else None,
                      branch="agent/saved", actor="test")
    restored = {"worktree": str(local_spawn.worktree), "branch": "agent/saved"}
    restore = Mock(return_value=restored if existing_branch else None)
    create = Mock(wraps=d.create_worktree)
    monkeypatch.setattr(d, "restore_worktree", restore)
    monkeypatch.setattr(d, "create_worktree", create)
    info, success = Mock(), Mock()
    monkeypatch.setattr(d, "info", info)
    monkeypatch.setattr(d, "success", success)
    row = asyncio.run(d.delegate_task(tid))
    restore.assert_called_once_with("test-project", "developer", tid,
                                    path=missing if recorded_path else None, branch="agent/saved")
    assert create.call_count == (0 if existing_branch else 1)
    assert row["worktree"] == str(local_spawn.worktree)
    assert len(local_spawn.tmux_created) == 1
    assert any("spawn started" in call.args[0] for call in info.call_args_list)
    success.assert_not_called()


def test_bad_json_warns_and_spawn_continues(spawn):
    path = d._claude_config_path()
    original = '{"projects":'
    path.write_text(original)
    row = asyncio.run(d._spawn_local(spawn, {}))
    assert row["status"] == "pending"
    assert row["delegate_log"].startswith("router: claude\nWARNING: worktree trust setup failed:")
    assert len(row["delegate_log"].splitlines()) == 2
    assert path.read_text() == original
    d.tmux.create.assert_called_once()
    d.db.release_task_locks.assert_not_called()


def test_claude_config_dir_resolved_at_call_time(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    path = tmp_path / ".claude.json"
    path.write_text("{}")
    worktree = str(tmp_path / "wt")
    d._trust_worktree(worktree)
    assert json.loads(path.read_text())["projects"][worktree]["hasTrustDialogAccepted"] is True


def test_trust_preserves_unescaped_thai(tmp_path):
    path = tmp_path / "claude.json"
    path.write_text('{"label": "สวัสดี"}', encoding="utf-8")
    d._trust_worktree(str(tmp_path / "wt"), path)
    assert "สวัสดี" in path.read_text(encoding="utf-8")
    assert json.loads(path.read_text(encoding="utf-8"))["label"] == "สวัสดี"


def test_no_owner_window_uses_initial_session():
    script = d._build_spawn_applescript("echo hello", "task-test", "abc")
    fallback = script.split("    else\n      set targetWin to (create window with default profile)")[1].split("    end if")[0]
    assert "tell current session of current tab of targetWin" in fallback
    assert 'write text "echo hello"' in fallback
    assert 'return "spawned"' in fallback
    assert "create tab" not in fallback
