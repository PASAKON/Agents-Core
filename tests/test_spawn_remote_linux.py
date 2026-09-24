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


def _fake_disk_probe_ok(cmd) -> bool:
    """True if `cmd` is the disk-floor's `df -Pk /` probe (task-a5c0549d
    host-awareness fix) — distinct from the main spawn ssh call, which
    carries the rendered `bash .../spawn-worker-remote.sh ...` command."""
    return len(cmd) >= 3 and cmd[2] == "df"


def test_linux_spawn_success_parses_pid_and_tmux_session(temp_db, no_deploy, monkeypatch):
    def fake_run(cmd, **kwargs):
        if cmd[0] == "osascript":
            return _Result(0)
        assert cmd[0] == "ssh" and cmd[1] == "mooniex-vps"
        if _fake_disk_probe_ok(cmd):
            # POSIX `df -Pk /` shape: header line + one data line, avail
            # (4th field) comfortably above the 5 GB orange floor.
            return _Result(0, "Filesystem 1024-blocks Used Available Capacity Mounted\n"
                              "/dev/sda1 10000000 1000000 8000000 12% /\n")
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
        if _fake_disk_probe_ok(cmd):
            return _Result(0, "Filesystem 1024-blocks Used Available Capacity Mounted\n"
                              "/dev/sda1 10000000 1000000 8000000 12% /\n")
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
        if _fake_disk_probe_ok(cmd):
            return _Result(0, "Filesystem 1024-blocks Used Available Capacity Mounted\n"
                              "/dev/sda1 10000000 1000000 8000000 12% /\n")
        return _Result(0, "some unexpected line with no SPAWNED marker\n")
    monkeypatch.setattr(delegate.subprocess, "run", fake_run)
    tid = temp_db.create_task(
        project="mooniex-agents", role="developer", title="t", description="d",
        owner_cto="test-owner", host="contabo",
    )
    result = asyncio.run(delegate.delegate_task(tid, host="contabo"))
    assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# 5b. Disk-floor host-awareness (CTO 2026-09-24 review, task-a5c0549d): the
#     gate must check the disk that will actually hold the worktree — a
#     contabo-bound spawn was refused/queued for the MAC's disk although
#     Contabo's own disk was fine (task-43b6514d, live on the real box:
#     "queued for disk — 3.9 GB free" while the Mac, not Contabo, was low).
# ---------------------------------------------------------------------------

def test_disk_floor_checks_the_spoke_not_the_mac_when_spoke_is_healthy(temp_db, no_deploy, monkeypatch):
    """Mac critically low, Contabo fine -- the spawn must still proceed."""
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 1.0)
    monkeypatch.setattr(delegate, "_remote_free_gb", lambda ssh_alias: 50.0)

    def fake_run(cmd, **kwargs):
        if cmd[0] == "osascript":
            return _Result(0)
        return _Result(0, "SPAWNED pid=9001 session=mooniex-task-df01 "
                          "worktree=/opt/MoonieXHQ/Agents/Core/worktrees/y\n")
    monkeypatch.setattr(delegate.subprocess, "run", fake_run)

    tid = temp_db.create_task(
        project="mooniex-agents", role="developer", title="t", description="d",
        owner_cto="test-owner", host="contabo",
    )
    result = asyncio.run(delegate.delegate_task(tid, host="contabo"))
    assert result["status"] == "in_progress"
    assert "disk" not in (result.get("delegate_log") or "")


def test_disk_floor_queues_when_the_spoke_itself_is_low(temp_db, no_deploy, monkeypatch):
    """Mac fine, Contabo critically low -- the spawn must be queued, and the
    message must name contabo, not the Mac."""
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 50.0)
    monkeypatch.setattr(delegate, "_remote_free_gb", lambda ssh_alias: 1.0)

    def _boom(*a, **k):
        raise AssertionError("must not reach ssh once the floor refuses")
    monkeypatch.setattr(delegate.subprocess, "run", _boom)

    tid = temp_db.create_task(
        project="mooniex-agents", role="developer", title="t", description="d",
        owner_cto="test-owner", host="contabo",
    )
    result = asyncio.run(delegate.delegate_task(tid, host="contabo"))
    assert result["status"] == "pending"  # unchanged, per ADR 0030
    assert "disk red on contabo" in result["delegate_log"]
    assert "1.0" in result["delegate_log"]


def test_disk_floor_fails_open_when_spoke_probe_unreachable(temp_db, no_deploy, monkeypatch):
    """An unreachable/broken disk probe must never become a false floor
    that blocks every remote spawn (fail-open, same shape as
    runners/branch_poller.remote_pid_alive)."""
    monkeypatch.setattr(delegate, "_remote_free_gb", lambda ssh_alias: None)

    def fake_run(cmd, **kwargs):
        if cmd[0] == "osascript":
            return _Result(0)
        return _Result(0, "SPAWNED pid=9002 session=mooniex-task-df02 "
                          "worktree=/opt/MoonieXHQ/Agents/Core/worktrees/z\n")
    monkeypatch.setattr(delegate.subprocess, "run", fake_run)

    tid = temp_db.create_task(
        project="mooniex-agents", role="developer", title="t", description="d",
        owner_cto="test-owner", host="contabo",
    )
    result = asyncio.run(delegate.delegate_task(tid, host="contabo"))
    assert result["status"] == "in_progress"


def test_disk_floor_skips_remote_probe_during_dry_run(temp_db, monkeypatch):
    """dry_run's own contract ('print the exact ssh command instead of
    running it') must hold even for the disk-floor gate -- a real ssh probe
    during dry-run would be exactly the network call dry_run promises not
    to make."""
    def _boom(ssh_alias):
        raise AssertionError("dry-run must never probe a spoke's disk over ssh")
    monkeypatch.setattr(delegate, "_remote_free_gb", _boom)

    tid = temp_db.create_task(
        project="mooniex-agents", role="developer", title="t", description="d",
        owner_cto="test-owner", host="contabo",
    )
    result = asyncio.run(delegate.delegate_task(tid, host="contabo", dry_run=True))
    assert result["status"] == "pending"
    assert "[dry-run]" in (result.get("delegate_log") or "")


def test_remote_free_gb_parses_df_output():
    def fake_run(cmd, **kwargs):
        assert cmd == ["ssh", "some-host", "df", "-Pk", "/"]
        return _Result(0, "Filesystem 1024-blocks Used Available Capacity Mounted\n"
                          "/dev/sda1 10000000 1000000 8388608 12% /\n")
    import unittest.mock as mock
    with mock.patch.object(delegate.subprocess, "run", fake_run):
        free_gb = delegate._remote_free_gb("some-host")
    assert free_gb == pytest.approx(8.0, abs=0.01)


def test_remote_free_gb_returns_none_on_unreachable_host():
    def fake_run(cmd, **kwargs):
        return _Result(255, "", "ssh: connect to host some-host port 22: timed out")
    import unittest.mock as mock
    with mock.patch.object(delegate.subprocess, "run", fake_run):
        assert delegate._remote_free_gb("some-host") is None


def test_remote_free_gb_returns_none_on_unparseable_output():
    def fake_run(cmd, **kwargs):
        return _Result(0, "not df output at all\n")
    import unittest.mock as mock
    with mock.patch.object(delegate.subprocess, "run", fake_run):
        assert delegate._remote_free_gb("some-host") is None


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
