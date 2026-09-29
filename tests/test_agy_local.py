"""Tests for runners/agy_local.py (Mac runner lane for agy).

Pytest suite, no network, no real agy:
- uses tmp_path to create a git repo as worktree
- fake agy script creates files and/or REPORT.md, pointed to by AGY_BIN
- monkeypatches update_status that runners.agy_local uses to record calls
- Case 1: fake agy writes a file + REPORT.md -> return 0, one commit exists, last status 'review'
- Case 2: fake agy writes nothing and exits 0 -> return 6, last status 'failed', no commit
- Case 3: .agy-run.log is never in the commit
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from runners import agy_local


def _init_git_repo(path: Path) -> None:
    """Initialize a git repo with an initial commit so HEAD exists."""
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "test-init"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test-init@localhost"],
        check=True,
        capture_output=True,
    )
    init_file = path / ".gitkeep"
    init_file.touch()
    subprocess.run(
        ["git", "-C", str(path), "add", ".gitkeep"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "commit", "-m", "initial commit"],
        check=True,
        capture_output=True,
    )


def test_case1_fake_agy_writes_file_and_report(tmp_path, monkeypatch):
    """Case 1: fake agy writes a file + REPORT.md -> return 0, one commit exists, last status 'review'."""
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    _init_git_repo(worktree)

    init_rev_count = int(
        subprocess.check_output(
            ["git", "-C", str(worktree), "rev-list", "--count", "HEAD"],
            text=True,
        ).strip()
    )
    assert init_rev_count == 1

    fake_bin = tmp_path / "fake_agy.sh"
    fake_bin.write_text(
        "#!/bin/sh\n"
        "echo 'agy: working on task'\n"
        "echo 'hello world' > solution.py\n"
        "cat << 'EOF' > REPORT.md\n"
        "# REPORT\n\n"
        "## Files changed\n"
        "- solution.py\n\n"
        "## What was done\n"
        "- Implemented solution\n\n"
        "## Blockers\n"
        "None\n"
        "EOF\n"
        "echo 'agy: finished successfully'\n"
        "exit 0\n"
    )
    fake_bin.chmod(0o755)

    monkeypatch.setenv("AGY_BIN", str(fake_bin))

    recorded_calls = []

    def _fake_update_status(task_id: str, status: str, **kwargs):
        recorded_calls.append({"task_id": task_id, "status": status, **kwargs})
        return True

    monkeypatch.setattr(agy_local.db, "update_status", _fake_update_status)
    monkeypatch.setattr(agy_local, "update_status", _fake_update_status)

    task = {"id": "task-test01", "title": "Build feature X"}
    prompt = "Please build feature X"
    role = "developer"

    rc = agy_local.run_agy_task(task, str(worktree), prompt, role)

    # Return code must be 0
    assert rc == 0

    # Exactly one new commit exists (init commit + agy commit)
    new_rev_count = int(
        subprocess.check_output(
            ["git", "-C", str(worktree), "rev-list", "--count", "HEAD"],
            text=True,
        ).strip()
    )
    assert new_rev_count == 2

    # Commit message format: agy(<task_id>): <task title>
    commit_msg = subprocess.check_output(
        ["git", "-C", str(worktree), "log", "-1", "--pretty=%s"],
        text=True,
    ).strip()
    assert commit_msg == "agy(task-test01): Build feature X"

    # Status transitions: in_progress first with pid, review last with report
    assert len(recorded_calls) >= 2
    assert recorded_calls[0]["status"] == "in_progress"
    assert recorded_calls[0]["pid"] == os.getpid()
    assert recorded_calls[0]["actor"] == role

    assert recorded_calls[-1]["status"] == "review"
    assert recorded_calls[-1]["actor"] == role
    report_text = recorded_calls[-1]["report"]
    assert "## Files changed" in report_text
    assert "--- agy log tail ---" in report_text
    assert "agy: finished successfully" in report_text


def test_case2_fake_agy_writes_nothing_fails(tmp_path, monkeypatch):
    """Case 2: fake agy writes nothing and exits 0 -> return 6, last status 'failed', no commit."""
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    _init_git_repo(worktree)

    init_rev_count = int(
        subprocess.check_output(
            ["git", "-C", str(worktree), "rev-list", "--count", "HEAD"],
            text=True,
        ).strip()
    )

    fake_bin = tmp_path / "fake_agy_noop.sh"
    fake_bin.write_text(
        "#!/bin/sh\n"
        "echo 'agy: no files modified'\n"
        "exit 0\n"
    )
    fake_bin.chmod(0o755)

    monkeypatch.setenv("AGY_BIN", str(fake_bin))

    recorded_calls = []

    def _fake_update_status(task_id: str, status: str, **kwargs):
        recorded_calls.append({"task_id": task_id, "status": status, **kwargs})
        return True

    monkeypatch.setattr(agy_local.db, "update_status", _fake_update_status)
    monkeypatch.setattr(agy_local, "update_status", _fake_update_status)

    task = {"id": "task-test02", "title": "Empty task"}
    prompt = "Do something"
    role = "developer"

    rc = agy_local.run_agy_task(task, str(worktree), prompt, role)

    # Return code must be 6
    assert rc == 6

    # No new commit exists
    after_rev_count = int(
        subprocess.check_output(
            ["git", "-C", str(worktree), "rev-list", "--count", "HEAD"],
            text=True,
        ).strip()
    )
    assert after_rev_count == init_rev_count

    # Status transitions: in_progress first, failed last
    assert len(recorded_calls) >= 2
    assert recorded_calls[0]["status"] == "in_progress"
    assert recorded_calls[-1]["status"] == "failed"
    assert recorded_calls[-1]["actor"] == role
    fail_report = recorded_calls[-1]["report"]
    assert "agy produced no file changes (exit 0)" in fail_report
    assert "agy: no files modified" in fail_report


def test_case3_agy_log_never_in_commit(tmp_path, monkeypatch):
    """Case 3: .agy-run.log is never in the commit."""
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    _init_git_repo(worktree)

    fake_bin = tmp_path / "fake_agy_logging.sh"
    fake_bin.write_text(
        "#!/bin/sh\n"
        "echo 'verbose agy log line 1'\n"
        "echo 'verbose agy log line 2'\n"
        "echo 'created file' > created.txt\n"
        "cat << 'EOF' > REPORT.md\n"
        "## Files changed\n"
        "- created.txt\n\n"
        "## What was done\n"
        "- created created.txt\n\n"
        "## Blockers\n"
        "None\n"
        "EOF\n"
        "exit 0\n"
    )
    fake_bin.chmod(0o755)

    monkeypatch.setenv("AGY_BIN", str(fake_bin))

    recorded_calls = []

    def _fake_update_status(task_id: str, status: str, **kwargs):
        recorded_calls.append({"task_id": task_id, "status": status, **kwargs})
        return True

    monkeypatch.setattr(agy_local.db, "update_status", _fake_update_status)
    monkeypatch.setattr(agy_local, "update_status", _fake_update_status)

    task = {"id": "task-test03", "title": "Check log exclusion"}
    rc = agy_local.run_agy_task(task, str(worktree), "prompt", "developer")
    assert rc == 0

    # .agy-run.log must exist on disk
    log_file = worktree / ".agy-run.log"
    assert log_file.is_file()
    assert "verbose agy log line 1" in log_file.read_text(encoding="utf-8")

    # .agy-run.log must NOT be in the latest commit
    committed_files = subprocess.check_output(
        ["git", "-C", str(worktree), "log", "-1", "--name-only", "--pretty=format:"],
        text=True,
    ).splitlines()
    committed_files = [f.strip() for f in committed_files if f.strip()]
    assert ".agy-run.log" not in committed_files
    assert "created.txt" in committed_files
    assert "REPORT.md" not in committed_files  # read into the task row, never merged

    # .agy-run.log must NOT be tracked anywhere in the git tree
    tree_files = subprocess.check_output(
        ["git", "-C", str(worktree), "ls-tree", "-r", "--name-only", "HEAD"],
        text=True,
    ).splitlines()
    assert ".agy-run.log" not in tree_files


def test_contract_appended_to_prompt(tmp_path, monkeypatch):
    """Verify agy receives prompt with contract appended."""
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    _init_git_repo(worktree)

    captured_prompt_file = tmp_path / "captured_prompt.txt"
    fake_bin = tmp_path / "fake_agy_contract.sh"
    fake_bin.write_text(
        "#!/bin/sh\n"
        f"printf '%s' \"$2\" > '{captured_prompt_file}'\n"
        "echo 'done' > result.txt\n"
        "echo 'REPORT' > REPORT.md\n"
        "exit 0\n"
    )
    fake_bin.chmod(0o755)

    monkeypatch.setenv("AGY_BIN", str(fake_bin))
    monkeypatch.setattr(agy_local.db, "update_status", lambda *a, **kw: True)
    monkeypatch.setattr(agy_local, "update_status", lambda *a, **kw: True)

    task = {"id": "task-test04", "title": "Contract test"}
    rc = agy_local.run_agy_task(task, str(worktree), "Original prompt text", "developer")
    assert rc == 0

    captured = captured_prompt_file.read_text(encoding="utf-8")
    assert "Original prompt text" in captured
    expected_contract = (
        f"You can only edit files. Do not run shell commands. Work only inside {worktree}. "
        f"When finished, write REPORT.md at the worktree root with three headings: "
        f"Files changed, What was done, Blockers."
    )
    assert expected_contract in captured


def test_find_agy_binary_resolution(tmp_path, monkeypatch):
    """Test binary resolution order: AGY_BIN -> ~/.local/bin/agy -> PATH."""
    # 1. AGY_BIN set
    monkeypatch.setenv("AGY_BIN", "/custom/bin/agy")
    assert agy_local.find_agy_binary() == "/custom/bin/agy"

    # 2. AGY_BIN unset, ~/.local/bin/agy exists
    monkeypatch.delenv("AGY_BIN", raising=False)
    fake_home = tmp_path / "home"
    local_bin = fake_home / ".local" / "bin" / "agy"
    local_bin.parent.mkdir(parents=True)
    local_bin.touch()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    assert agy_local.find_agy_binary() == str(local_bin)

    # 3. AGY_BIN unset, ~/.local/bin/agy missing -> fallback to PATH or 'agy'
    local_bin.unlink()
    resolved = agy_local.find_agy_binary()
    assert resolved.endswith("agy")


def test_worker_init_codex_refusal(monkeypatch, tmp_path):
    """Test worker_init.py refuses codex with contabo message."""
    from runners import worker_init

    worktree = tmp_path / "worktree"
    worktree.mkdir()

    task = {
        "id": "task-codex",
        "runner": "codex",
        "worktree": str(worktree),
        "project": "core",
    }
    monkeypatch.setattr(worker_init.sys, "argv", ["worker_init.py", "developer", "task-codex"])
    monkeypatch.setattr(worker_init.db, "init", lambda: None)
    monkeypatch.setattr(worker_init.db, "get_task", lambda tid: task)
    monkeypatch.setattr(worker_init.db, "claim_task", lambda tid, agent: True)

    recorded_calls = []
    monkeypatch.setattr(
        worker_init.db,
        "update_status",
        lambda tid, status, **kw: recorded_calls.append((tid, status, kw)),
    )

    with pytest.raises(SystemExit) as exc:
        worker_init.main()

    assert exc.value.code == 5
    assert len(recorded_calls) == 1
    assert recorded_calls[0][1] == "failed"
    assert recorded_calls[0][2]["report"] == "runner='codex' not signed in on the Mac — use host contabo"


def test_worker_init_agy_dispatch(monkeypatch, tmp_path):
    """Test worker_init.py dispatches runner == 'agy' to agy_local.run_agy_task."""
    from runners import worker_init

    worktree = tmp_path / "worktree"
    worktree.mkdir()

    task = {
        "id": "task-agy",
        "runner": "agy",
        "worktree": str(worktree),
        "project": "core",
        "branch": "feat",
        "description": "desc",
    }
    monkeypatch.setattr(worker_init.sys, "argv", ["worker_init.py", "developer", "task-agy"])
    monkeypatch.setattr(worker_init.db, "init", lambda: None)
    monkeypatch.setattr(worker_init.db, "get_task", lambda tid: task)
    monkeypatch.setattr(worker_init.db, "claim_task", lambda tid, agent: True)
    monkeypatch.setattr(
        worker_init,
        "get_project",
        lambda p: {"name": "Core", "key": "core", "default_branch": "main", "stack": []},
    )

    called = []

    def fake_run_agy(t, wt, pr, r):
        called.append((t, wt, pr, r))
        return 0

    monkeypatch.setattr(worker_init.agy_local, "run_agy_task", fake_run_agy)

    with pytest.raises(SystemExit) as exc:
        worker_init.main()

    assert exc.value.code == 0
    assert len(called) == 1
    assert called[0][0]["id"] == "task-agy"
    assert called[0][1] == str(worktree)
    assert "Task task-agy" in called[0][2]
    assert called[0][3] == "developer"

