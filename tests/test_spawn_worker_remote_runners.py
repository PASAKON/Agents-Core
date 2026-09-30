"""Tests for Contabo spoke runner support (claude|codex|agy) in scripts/spawn-worker-remote.sh.

Docs: docs/briefs/AGY-contabo-lane.md, docs/ops/agent-runners.md
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.delegate as delegate  # noqa: E402
from lib.config import host as get_host  # noqa: E402

SCRIPT = ROOT / "scripts" / "spawn-worker-remote.sh"
BASH3 = "/bin/bash"


def _run_dry_run(runner: str, task: str = "task-dry01", **extra_flags: str) -> subprocess.CompletedProcess:
    args = [
        BASH3,
        str(SCRIPT),
        "--dry-run",
        "--task",
        task,
        "--project",
        "mooniex-agents",
        "--role",
        "developer",
        "--branch",
        f"agent/developer-{task}",
        "--base",
        "main",
        "--repo-url",
        "git@github.com:PASAKON/mooniex-agents.git",
        "--repo-path",
        "/opt/MoonieXHQ/Agents/Core",
        "--worktree-root",
        "/opt/MoonieXHQ/Agents/Core/worktrees",
        "--claude-args",
        "--model claude-sonnet-5 --effort high --allowed-tools Read,Write",
        "--model",
        "claude-sonnet-5",
        "--effort",
        "high",
        "--session-name",
        f"CONTABO Developer #{task} (test)",
        "--runner",
        runner,
    ]
    for k, v in extra_flags.items():
        flag = "--" + k.replace("_", "-")
        args.extend([flag, v])
    return subprocess.run(args, capture_output=True, text=True)


def test_script_exists_and_is_executable():
    assert SCRIPT.is_file()
    assert SCRIPT.stat().st_mode & 0o111, "spawn-worker-remote.sh must be executable"


def test_script_passes_bash_syntax_check():
    r = subprocess.run([BASH3, "-n", str(SCRIPT)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_claude_dry_run_output_unchanged_from_today():
    """Claude dry-run output must be unchanged from today: same fixed strings,
    no cmd= line invented for claude, and <launch.sh running claude> in would."""
    r = _run_dry_run("claude", task="task-flagcheck")
    assert r.returncode == 0, r.stderr
    out = r.stdout

    for expected in (
        "task=task-flagcheck",
        "project=mooniex-agents",
        "role=developer",
        "branch=agent/developer-task-flagcheck",
        "base=main",
        "repo_url=git@github.com:PASAKON/mooniex-agents.git",
        "repo_path=/opt/MoonieXHQ/Agents/Core",
        "worktree=/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-flagcheck",
        "tmux_session=mooniex-task-flagcheck",
        "model=claude-sonnet-5",
        "effort=high",
        "runner=claude",
        "claude_args=--model claude-sonnet-5 --effort high --allowed-tools Read,Write",
        "session_name=CONTABO Developer #task-flagcheck (test)",
        "roles_dir=",
        "<launch.sh running claude>",
    ):
        assert expected in out, f"missing {expected!r} in dry-run output: {out}"

    # Claude dry-run does not output cmd=
    assert "cmd=" not in out


def test_codex_dry_run_prints_runner_command():
    """Codex dry-run must print the runner's command line and mention launch.sh running codex."""
    task_id = "task-codex01"
    r = _run_dry_run("codex", task=task_id)
    assert r.returncode == 0, r.stderr
    out = r.stdout

    assert "runner=codex" in out
    assert "[dry-run] cmd=" in out

    wt = f"/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__{task_id}"
    launch_dir = f"{ROOT}/.launch-{task_id}"
    expected_cmd = (
        f'codex exec "$(cat TASK.md)" -C "{wt}" -s workspace-write '
        f'--skip-git-repo-check --json -o {launch_dir}/codex-final.txt '
        f'> {launch_dir}/codex-events.jsonl 2>&1'
    )
    assert expected_cmd in out
    assert "<launch.sh running codex>" in out


def test_agy_dry_run_prints_runner_command():
    """Agy dry-run must print the runner's command line and mention launch.sh running agy."""
    task_id = "task-agy01"
    r = _run_dry_run("agy", task=task_id)
    assert r.returncode == 0, r.stderr
    out = r.stdout

    assert "runner=agy" in out
    assert "[dry-run] cmd=" in out

    wt = f"/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__{task_id}"
    launch_dir = f"{ROOT}/.launch-{task_id}"
    expected_cmd = (
        f'/root/.local/bin/agy -p "$(cat TASK.md)" --model gemini-3.8-flash-high '
        f'--mode accept-edits --add-dir "{wt}" < /dev/null '
        f'>> {launch_dir}/agy-events.log 2>&1'
    )
    assert expected_cmd in out
    assert "<launch.sh running agy>" in out


def test_unknown_runner_rejected():
    """An unknown runner must exit non-zero and print the refusal to stderr."""
    r = _run_dry_run("nonexistent_runner")
    assert r.returncode != 0
    assert "nonexistent_runner" in r.stderr
    assert "not supported" in r.stderr


def test_hosts_yaml_contabo_lists_all_three_runners():
    """config/hosts.yaml contabo host must declare runners: [claude, codex, agy]."""
    cfg = get_host("contabo")
    assert set(cfg.get("runners", [])) == {"claude", "codex", "agy"}


def test_delegate_validates_all_three_runners_on_contabo():
    """delegate._validate_runner must succeed for claude, codex, and agy on contabo."""
    delegate._validate_runner("claude", "contabo")
    delegate._validate_runner("codex", "contabo")
    delegate._validate_runner("agy", "contabo")

    with pytest.raises(ValueError, match="unknown runner"):
        delegate._validate_runner("nonexistent", "contabo")


def test_script_source_checks_commit_logic():
    """Check spawn-worker-remote.sh script source for required runner handling."""
    code = SCRIPT.read_text(encoding="utf-8")

    # Codex commit logic
    assert "git diff --cached --quiet" in code
    assert "codex: task $TASK" in code
    assert "git push" in code

    # Agy commit logic
    assert "/root/.local/bin/agy" in code
    assert "gemini-3.8-flash-high" in code
    assert "accept-edits" in code
    assert "agy-worker" in code
    assert "git reset -q --" in code or "git reset" in code
    assert "REPORT.md" in code

    # Dangerous flags must NEVER be present
    assert "--dangerously-skip-permissions" not in code
    assert "--dangerously-bypass-approvals-and-sandbox" not in code
