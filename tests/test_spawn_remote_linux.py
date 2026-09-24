"""Phase 2 — the Contabo spoke (docs/design/multi-host-workers.md §4,
task-a5c0549d): `delegate_task(host="contabo")` spawns a worker on Contabo
via `scripts/spawn-worker-remote.sh` instead of raising NotImplementedError.

Covers: the linux dry-run renders the exact ssh command (every flag present),
the winbox dry-run stays byte-identical (regression guard — the windows
branch of `_spawn_remote` was only re-indented, never rewritten), an
`os: freebsd` host still raises, the SPAWNED/SPAWN_REFUSED output contract is
parsed correctly, and the shell script itself parses every flag under
`bash -n` + `--dry-run` (run under the Mac's real bash 3.2, since the script
only ever EXECUTES on Contabo's newer bash — see the script's own header).

Run via:  pytest tests/test_spawn_remote_linux.py
(same convention as tests/test_multihost.py — not in pytest.ini's default
testpaths; run explicitly alongside the default `pytest` run.)
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import tools.delegate as delegate  # noqa: E402

SCRIPT = ROOT / "scripts" / "spawn-worker-remote.sh"


@pytest.fixture()
def temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    # owner_cto="test-owner" is synthetic with no c_level_sessions row.
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    db_mod.init()
    return db_mod


@pytest.fixture(autouse=True)
def _plenty_of_disk(monkeypatch):
    """ADR 0030's disk-floor gate reads the REAL Mac's free space and refuses
    every spawn below the orange floor — this suite must not depend on
    whatever this machine's disk happens to be at test time (established
    pattern: tests/test_delegate_disk_floor.py monkeypatches the same seam)."""
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 999.0)


def _new_task(db_mod_, *, host: str = "contabo") -> str:
    return db_mod_.create_task(
        project="mooniex-agents", role="developer",
        title="contabo spawn test", description="d",
        owner_cto="test-owner", host=host,
    )


# ---------------------------------------------------------------------------
# 1. dry-run renders the exact ssh command for host=contabo
# ---------------------------------------------------------------------------

def test_contabo_dry_run_renders_ssh_command_with_every_flag(temp_db):
    tid = _new_task(temp_db, host="contabo")
    result = asyncio.run(delegate.delegate_task(tid, host="contabo", dry_run=True))

    assert result["status"] == "pending"  # dry-run never advances status
    log = result["delegate_log"]
    assert "[dry-run] host=contabo ssh_cmd=" in log
    assert "ssh mooniex-vps" in log
    assert "bash /opt/MoonieXHQ/Agents/Core/scripts/spawn-worker-remote.sh" in log

    for flag, value in [
        ("--task", tid),
        ("--project", "mooniex-agents"),
        ("--role", "developer"),
        ("--base", "main"),
        ("--worktree-root", "/opt/MoonieXHQ/Agents/Core/worktrees"),
        ("--model", "claude-sonnet-5"),
        ("--effort", "xhigh"),
        ("--runner", "claude"),
    ]:
        assert f"{flag} {value}" in log, f"missing {flag} {value!r} in: {log}"

    assert "--branch agent/developer-" in log
    assert "--repo-url" in log and "--repo-path" in log
    assert "--claude-args" in log and "--allowed-tools" in log
    assert "--session-name" in log and "CONTABO Developer" in log
    # never the windows shape
    assert "powershell" not in log
    assert "spawn-worker.ps1" not in log


def test_contabo_dry_run_never_touches_network(temp_db, monkeypatch):
    """dry-run must short-circuit before any subprocess call at all — same
    contract as winbox's dry-run path."""
    def _boom(*a, **k):
        raise AssertionError(f"unexpected subprocess call in dry-run: {a!r}")
    monkeypatch.setattr(delegate.subprocess, "run", _boom)
    tid = _new_task(temp_db, host="contabo")
    result = asyncio.run(delegate.delegate_task(tid, host="contabo", dry_run=True))
    assert result["status"] == "pending"


# ---------------------------------------------------------------------------
# 2. Regression guard: the winbox dry-run shape is unchanged by adding linux
# ---------------------------------------------------------------------------

def test_winbox_dry_run_shape_unchanged(temp_db):
    tid = _new_task(temp_db, host="winbox")
    result = asyncio.run(delegate.delegate_task(tid, host="winbox", dry_run=True))

    assert result["status"] == "pending"
    log = result["delegate_log"]
    assert "[dry-run] host=winbox ssh_cmd=" in log
    # shlex.quote wraps the whole remote command in single quotes since it
    # contains spaces -- this is the exact shape _spawn_remote has always
    # produced for winbox, unchanged by adding the linux branch.
    assert "ssh winbox 'powershell -NoProfile -ExecutionPolicy Bypass -File" in log
    assert "spawn-worker.ps1" in log

    for flag in ("-Task", "-Project", "-Role", "-Branch", "-Base", "-RepoUrl",
                "-RepoPath", "-WorktreeRoot", "-ClaudeArgs", "-Model",
                "-Effort", "-TaskFile", "-SessionName", "-Runner"):
        assert flag in log, f"missing {flag} in: {log}"

    # never the linux shape
    assert "spawn-worker-remote.sh" not in log
    assert not log.split("ssh_cmd=", 1)[1].startswith("bash")


# ---------------------------------------------------------------------------
# 3. An os the launcher doesn't know still raises, loudly, before any ssh
# ---------------------------------------------------------------------------

def test_unknown_os_host_raises_not_implemented(temp_db, monkeypatch):
    fake_hosts = {
        "freebsd-box": {"os": "freebsd", "ssh": "freebsd-box",
                        "agents_root": "/opt/agents", "worktrees": "/opt/agents/wt"},
    }
    monkeypatch.setattr(delegate, "get_host", lambda name: fake_hosts[name])

    def _boom(*a, **k):
        raise AssertionError("must not reach ssh for an unsupported os")
    monkeypatch.setattr(delegate.subprocess, "run", _boom)

    task = {"id": "task-fbsd0001", "role": "developer", "project": "mooniex-agents"}
    with pytest.raises(NotImplementedError, match="freebsd"):
        asyncio.run(delegate._spawn_remote(task, "freebsd-box", dry_run=True))


# ---------------------------------------------------------------------------
# 4. SPAWNED / SPAWN_REFUSED output contract, parsed by _spawn_remote
# ---------------------------------------------------------------------------

class _Result:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.fixture()
def no_deploy(monkeypatch):
    """Skip the real deploy-check (its own ssh/scp calls) -- out of scope
    here, covered by the dry-run tests above (deploy is a no-op there too)."""
    monkeypatch.setattr(delegate, "_ensure_remote_deploy_linux", lambda *a, **k: [])


def test_linux_spawn_success_parses_pid_and_tmux_session(temp_db, no_deploy, monkeypatch):
    def fake_run(cmd, **kwargs):
        if cmd[0] == "osascript":
            return _Result(0)
        assert cmd[0] == "ssh" and cmd[1] == "mooniex-vps"
        assert kwargs.get("input")  # the prompt travels over stdin
        return _Result(0, "SPAWNED pid=4242 session=mooniex-task-lx01 "
                          "worktree=/opt/MoonieXHQ/Agents/Core/worktrees/x\n")

    monkeypatch.setattr(delegate.subprocess, "run", fake_run)
    tid = temp_db.create_task(
        project="mooniex-agents", role="developer", title="t", description="d",
        owner_cto="test-owner", host="contabo",
    )
    result = asyncio.run(delegate.delegate_task(tid, host="contabo"))

    assert result["status"] == "in_progress"
    assert result["pid"] == 4242
    assert result["host"] == "contabo"
    assert result["tmux_session"] == "mooniex-task-lx01"
    assert result["worktree"] == "/opt/MoonieXHQ/Agents/Core/worktrees/x"


def test_linux_spawn_refused_sets_conflict(temp_db, no_deploy, monkeypatch):
    def fake_run(cmd, **kwargs):
        if cmd[0] == "osascript":
            return _Result(0)
        return _Result(1, "SPAWN_REFUSED=dirty-worktree /opt/x/wt\n")
    monkeypatch.setattr(delegate.subprocess, "run", fake_run)
    tid = temp_db.create_task(
        project="mooniex-agents", role="developer", title="t", description="d",
        owner_cto="test-owner", host="contabo",
    )
    result = asyncio.run(delegate.delegate_task(tid, host="contabo"))
    assert result["status"] == "conflict"
    assert "dirty-worktree" in result["delegate_log"]


def test_linux_spawn_unparseable_output_sets_failed(temp_db, no_deploy, monkeypatch):
    def fake_run(cmd, **kwargs):
        if cmd[0] == "osascript":
            return _Result(0)
        return _Result(0, "some unexpected line with no SPAWNED marker\n")
    monkeypatch.setattr(delegate.subprocess, "run", fake_run)
    tid = temp_db.create_task(
        project="mooniex-agents", role="developer", title="t", description="d",
        owner_cto="test-owner", host="contabo",
    )
    result = asyncio.run(delegate.delegate_task(tid, host="contabo"))
    assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# 5. The shell script itself: bash -n (real syntax check) + --dry-run (real
#    flag parsing) -- both run under /bin/bash, the Mac's real bash 3.2, on
#    purpose (the script's own header: it only EXECUTES on Contabo's newer
#    bash, but must stay parseable under the older one these tests use).
# ---------------------------------------------------------------------------

BASH3 = "/bin/bash"


def test_script_exists_and_is_executable():
    assert SCRIPT.is_file()
    assert SCRIPT.stat().st_mode & 0o111, "spawn-worker-remote.sh must be executable"


def test_script_passes_bash_syntax_check():
    r = subprocess.run([BASH3, "-n", str(SCRIPT)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_script_dry_run_parses_every_flag():
    r = subprocess.run(
        [BASH3, str(SCRIPT), "--dry-run",
         "--task", "task-flagcheck", "--project", "proj1", "--role", "developer",
         "--branch", "agent/developer-task-flagcheck", "--base", "main",
         "--repo-url", "git@github.com:PASAKON/proj1.git",
         "--repo-path", "/opt/proj1", "--worktree-root", "/opt/proj1/worktrees",
         "--claude-args", "--model claude-sonnet-5 --effort high --allowed-tools Read,Write",
         "--model", "claude-sonnet-5", "--effort", "high",
         "--session-name", "CONTABO Developer #flagcheck (test)",
         "--runner", "claude"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    out = r.stdout
    for expected in (
        "task=task-flagcheck", "project=proj1", "role=developer",
        "branch=agent/developer-task-flagcheck", "base=main",
        "repo_url=git@github.com:PASAKON/proj1.git", "repo_path=/opt/proj1",
        "worktree=/opt/proj1/worktrees/proj1__developer__task-flagcheck",
        "tmux_session=mooniex-task-flagcheck",
        "model=claude-sonnet-5", "effort=high", "runner=claude",
        "session_name=CONTABO Developer #flagcheck (test)",
    ):
        assert expected in out, f"missing {expected!r} in dry-run output: {out}"


def test_script_dry_run_missing_required_flag_exits_nonzero():
    r = subprocess.run(
        [BASH3, str(SCRIPT), "--dry-run", "--task", "task-x"],
        capture_output=True, text=True,
    )
    assert r.returncode != 0


def test_script_rejects_unsupported_runner():
    r = subprocess.run(
        [BASH3, str(SCRIPT), "--dry-run",
         "--task", "t", "--project", "p", "--role", "developer",
         "--branch", "b", "--base", "main", "--repo-url", "u",
         "--repo-path", "/tmp/p", "--worktree-root", "/tmp/wt",
         "--claude-args", "", "--model", "m", "--effort", "high",
         "--session-name", "S", "--runner", "codex"],
        capture_output=True, text=True,
    )
    assert r.returncode != 0
    assert "codex" in r.stderr
