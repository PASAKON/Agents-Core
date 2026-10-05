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
    import shlex
    command = out.split("[dry-run] cmd=", 1)[1].splitlines()[0]
    argv = shlex.split(command)
    assert argv[:3] == ['codex', 'exec', '$(cat TASK.md)']
    assert argv[argv.index('-C') + 1] == wt
    assert argv[argv.index('-s') + 1] == 'workspace-write'
    assert argv[argv.index('-o') + 1] == f'{launch_dir}/codex-final.txt'
    assert '--add-dir' not in argv  # no WORK_DIR here, and never a root under .git (task-2f1a8586)
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


@pytest.mark.parametrize("work_dir", [None, "/tmp/Work folder/task's output", r"C:\Work folder\task"])
def test_codex_writable_dirs(tmp_path, work_dir):
    import shlex
    repo = tmp_path / "repo with spaces"
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    flags = {"repo_path": str(repo)}
    if work_dir is not None:
        flags["work_dir"] = work_dir
    else:
        flags["work_dir"] = ""  # do not inherit the test process's WORK_DIR
    result = _run_dry_run("codex", **flags)
    assert result.returncode == 0, result.stderr
    command = result.stdout.split("[dry-run] cmd=", 1)[1].splitlines()[0]
    args = shlex.split(command)
    dirs = [args[i + 1] for i, arg in enumerate(args) if arg == "--add-dir"]
    assert dirs == ([work_dir] if work_dir else [])  # never a root under .git (task-2f1a8586)
    assert "danger-full-access" not in result.stdout
    assert "dangerously-bypass" not in result.stdout
    source = SCRIPT.read_text()
    assert source.count('emit_codex_command') == 3  # definition, dry-run, real launch
    assert 'git-common-dir' not in source


@pytest.mark.parametrize("runner", ["codex", "agy"])
def test_heartbeat_body_cleanup_executes(tmp_path, runner):
    result = _run_dry_run(runner)
    body = result.stdout.split("heartbeat_pid=\n", 1)[1]
    body = "heartbeat_pid=\n" + body.replace("CLI_RC=$?; cleanup_heartbeat", "sleep 0.1; CLI_RC=$?; cleanup_heartbeat")
    # Execute only the generated supervisor fragment, never a worker or tmux.
    process = subprocess.run(["bash", "-c", body], cwd=tmp_path,
                             capture_output=True, text=True, timeout=5)
    assert process.returncode == 0, process.stderr
    assert 'kill "$heartbeat_pid"' in body
    assert 'wait "$heartbeat_pid"' in body
    assert 'sleep 60 &' in body
    assert 'trap cleanup_runner EXIT' in body
    assert re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\n', (tmp_path / 'HEARTBEAT').read_text())


@pytest.mark.parametrize('exit_mode', ['exit 7', 'kill -TERM $$'])
def test_heartbeat_cleanup_on_exit(tmp_path, exit_mode):
    source = SCRIPT.read_text()
    body = source.split("cat <<'HEARTBEAT_START'\n", 1)[1].split('\nHEARTBEAT_START', 1)[0]
    script = body + '\nprintf "%s" "$heartbeat_pid" > heartbeat.pid\nsleep 0.1\n' + exit_mode
    result = subprocess.run(['bash', '-c', script], cwd=tmp_path, timeout=5)
    assert result.returncode in (7, 143)
    import os
    with pytest.raises(ProcessLookupError):
        os.kill(int((tmp_path / 'heartbeat.pid').read_text()), 0)


def test_codex_linked_worktree_gets_no_git_root(tmp_path):
    import shlex
    repo = tmp_path / 'common repo'
    trees = tmp_path / 'work trees'
    subprocess.run(['git', 'init', str(repo)], check=True, capture_output=True)
    subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Test',
                    '-c', 'user.email=test@example.invalid', 'commit',
                    '--allow-empty', '-m', 'fixture'], check=True, capture_output=True)
    wt = trees / 'mooniex-agents__developer__task-linked'
    subprocess.run(['git', '-C', str(repo), 'worktree', 'add', '-b', 'fixture', str(wt)],
                   check=True, capture_output=True)
    result = _run_dry_run('codex', task='task-linked', repo_path=str(repo),
                          worktree_root=str(trees), work_dir='')
    args = shlex.split(result.stdout.split('[dry-run] cmd=', 1)[1].splitlines()[0])
    assert '--add-dir' not in args  # codex's bwrap sandbox fails to start with a root under .git
    assert args[args.index('-C') + 1] == str(wt)


# ---------------------------------------------------------------------------
# .media-allow gate tests (scripts/spawn-worker-remote.sh emit_report_commit_push)
# ---------------------------------------------------------------------------

def _generate_report_step_script(task: str = "task-media01", branch: str = "agent/developer-task-media01",
                                base: str = "main", runner: str = "codex") -> str:
    script_text = SCRIPT.read_text(encoding="utf-8")
    sh_quote_idx = script_text.index("sh_quote() {")
    eof_idx = script_text.index("REPORT_STEP_EOF\n}") + len("REPORT_STEP_EOF\n}")
    fn_text = script_text[sh_quote_idx:eof_idx]
    generator = f"""
TASK={task!r}
BRANCH={branch!r}
BASE={base!r}
GIT_RESET_GUARD='.worker.pid TASK.md'
{fn_text}
emit_report_commit_push {runner} "" "" "" "{runner}: task {task}"
"""
    res = subprocess.run([BASH3, "-c", generator], capture_output=True, text=True, check=True)
    return res.stdout


def _setup_media_test_repo(tmp_path: Path, origin_media_allow: str | None = None, task: str = "task-media01"):
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)

    seed = tmp_path / "seed"
    subprocess.run(["git", "init", "-q", str(seed)], check=True)
    subprocess.run(["git", "-C", str(seed), "checkout", "-q", "-b", "main"], check=True)
    (seed / "README.md").write_text("seed\n", encoding="utf-8")
    if origin_media_allow is not None:
        (seed / ".media-allow").write_text(origin_media_allow, encoding="utf-8")
    subprocess.run(["git", "-C", str(seed), "add", "-A"], check=True)
    subprocess.run([
        "git", "-C", str(seed),
        "-c", "user.name=test", "-c", "user.email=test@example.invalid",
        "commit", "-q", "-m", "seed"
    ], check=True)
    subprocess.run(["git", "-C", str(seed), "remote", "add", "origin", str(origin)], check=True)
    subprocess.run(["git", "-C", str(seed), "push", "-q", "origin", "main"], check=True)

    wt = tmp_path / "wt"
    subprocess.run(["git", "clone", "-q", str(origin), str(wt)], check=True)
    branch = f"agent/developer-{task}"
    subprocess.run(["git", "-C", str(wt), "checkout", "-q", "-b", branch, "origin/main"], check=True)
    subprocess.run(["git", "-C", str(wt), "config", "user.name", "test"], check=True)
    subprocess.run(["git", "-C", str(wt), "config", "user.email", "test@example.invalid"], check=True)

    return origin, wt, branch


def _run_report_step(wt: Path, script_body: str) -> subprocess.CompletedProcess:
    script_path = wt / "run_report.sh"
    script_path.write_text(script_body, encoding="utf-8")
    return subprocess.run([BASH3, str(script_path)], cwd=wt, capture_output=True, text=True)


def test_media_allow_allowed_png_is_kept(tmp_path):
    task = "task-kept01"
    origin, wt, branch = _setup_media_test_repo(
        tmp_path, origin_media_allow="# allow Minecraft textures\n\ntextures/**\n", task=task
    )
    (wt / "textures").mkdir()
    (wt / "textures" / "pack.png").write_bytes(b"pack data")
    (wt / "code.py").write_text("print(1)\n", encoding="utf-8")

    script = _generate_report_step_script(task=task, branch=branch)
    res = _run_report_step(wt, script)
    assert res.returncode == 0, f"script failed: {res.stderr}\nstdout: {res.stdout}"

    tree = subprocess.run(
        ["git", "-C", str(origin), "ls-tree", "-r", "--name-only", branch],
        capture_output=True, text=True, check=True
    ).stdout.splitlines()

    assert "textures/pack.png" in tree
    assert "code.py" in tree
    assert f"docs/reports/{task}/REPORT.md" in tree

    report_content = subprocess.run(
        ["git", "-C", str(origin), "show", f"{branch}:docs/reports/{task}/REPORT.md"],
        capture_output=True, text=True, check=True
    ).stdout
    assert "media kept: textures/pack.png" in report_content
    assert "Blockers" not in report_content

    log_body = subprocess.run(
        ["git", "-C", str(origin), "log", "-1", "--format=%B", branch],
        capture_output=True, text=True, check=True
    ).stdout
    assert "media kept: textures/pack.png" in log_body


def test_media_allow_unallowed_png_is_reset(tmp_path):
    task = "task-reset01"
    origin, wt, branch = _setup_media_test_repo(
        tmp_path, origin_media_allow="textures/**\n", task=task
    )
    (wt / "unallowed.png").write_bytes(b"image data")
    (wt / "code.py").write_text("print(1)\n", encoding="utf-8")

    script = _generate_report_step_script(task=task, branch=branch)
    res = _run_report_step(wt, script)
    assert res.returncode == 0, f"script failed: {res.stderr}\nstdout: {res.stdout}"

    tree = subprocess.run(
        ["git", "-C", str(origin), "ls-tree", "-r", "--name-only", branch],
        capture_output=True, text=True, check=True
    ).stdout.splitlines()

    assert "unallowed.png" not in tree
    assert "code.py" in tree

    report_content = subprocess.run(
        ["git", "-C", str(origin), "show", f"{branch}:docs/reports/{task}/REPORT.md"],
        capture_output=True, text=True, check=True
    ).stdout
    assert "media not committed: unallowed.png" in report_content
    assert "media kept:" not in report_content


def test_media_allow_large_file_reset_without_bang_large_and_kept_with_it(tmp_path):
    task = "task-large01"
    # Part A: Without !large
    dir_a = tmp_path / "part_a"
    dir_a.mkdir()
    origin_a, wt_a, branch_a = _setup_media_test_repo(
        dir_a, origin_media_allow="textures/**\n", task=task
    )
    (wt_a / "textures").mkdir()
    (wt_a / "textures" / "big.png").write_bytes(b"x" * 1572864)  # 1.5 MB

    script_a = _generate_report_step_script(task=task, branch=branch_a)
    res_a = _run_report_step(wt_a, script_a)
    assert res_a.returncode == 0, res_a.stderr

    tree_a = subprocess.run(
        ["git", "-C", str(origin_a), "ls-tree", "-r", "--name-only", branch_a],
        capture_output=True, text=True, check=True
    ).stdout.splitlines()
    assert "textures/big.png" not in tree_a

    report_a = subprocess.run(
        ["git", "-C", str(origin_a), "show", f"{branch_a}:docs/reports/{task}/REPORT.md"],
        capture_output=True, text=True, check=True
    ).stdout
    assert re.search(r"media not committed: textures/big\.png \(1[.,]5 MB\)", report_a)
    assert "media kept:" not in report_a

    # Part B: With !large
    dir_b = tmp_path / "part_b"
    dir_b.mkdir()
    origin_b, wt_b, branch_b = _setup_media_test_repo(
        dir_b, origin_media_allow="textures/** !large\n", task=task
    )
    (wt_b / "textures").mkdir()
    (wt_b / "textures" / "big.png").write_bytes(b"x" * 1572864)  # 1.5 MB

    script_b = _generate_report_step_script(task=task, branch=branch_b)
    res_b = _run_report_step(wt_b, script_b)
    assert res_b.returncode == 0, res_b.stderr

    tree_b = subprocess.run(
        ["git", "-C", str(origin_b), "ls-tree", "-r", "--name-only", branch_b],
        capture_output=True, text=True, check=True
    ).stdout.splitlines()
    assert "textures/big.png" in tree_b

    report_b = subprocess.run(
        ["git", "-C", str(origin_b), "show", f"{branch_b}:docs/reports/{task}/REPORT.md"],
        capture_output=True, text=True, check=True
    ).stdout
    assert "media kept: textures/big.png" in report_b
    assert "Blockers" not in report_b

    log_b = subprocess.run(
        ["git", "-C", str(origin_b), "log", "-1", "--format=%B", branch_b],
        capture_output=True, text=True, check=True
    ).stdout
    assert "media kept: textures/big.png" in log_b


def test_media_allow_in_working_tree_only_is_ignored(tmp_path):
    task = "task-wt01"
    # No .media-allow in origin
    origin, wt, branch = _setup_media_test_repo(
        tmp_path, origin_media_allow=None, task=task
    )
    # Worker creates .media-allow in worktree only
    (wt / ".media-allow").write_text("textures/**\n", encoding="utf-8")
    (wt / "textures").mkdir()
    (wt / "textures" / "pack.png").write_bytes(b"pack data")

    script = _generate_report_step_script(task=task, branch=branch)
    res = _run_report_step(wt, script)
    assert res.returncode == 0, res.stderr

    tree = subprocess.run(
        ["git", "-C", str(origin), "ls-tree", "-r", "--name-only", branch],
        capture_output=True, text=True, check=True
    ).stdout.splitlines()

    assert "textures/pack.png" not in tree

    report = subprocess.run(
        ["git", "-C", str(origin), "show", f"{branch}:docs/reports/{task}/REPORT.md"],
        capture_output=True, text=True, check=True
    ).stdout
    assert "media not committed: textures/pack.png" in report
    assert "media kept:" not in report






