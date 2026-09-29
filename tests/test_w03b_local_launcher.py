"""Org Mesh W0.3b (task-26988fe3): a Linux hub delegating a codex/agy task to ITSELF.

`delegate_task` used to send `resolved_host == self_host()` to `_spawn_local`,
which starts Claude only. On Contabo a codex or agy run needs the launcher's own
runner blocks (tmux, launch.sh, commit + push of the branch), so that case now
runs `scripts/spawn-worker-remote.sh` with plain `bash` — no ssh — and parses
its output exactly as it does over ssh.

  1. linux + host==self + codex   -> `bash <checkout>/scripts/spawn-worker-remote.sh ...`
  2. linux + host==self + agy     -> same
  3. linux + host==self + claude  -> `_spawn_local` (unchanged)
  4. darwin + host==self + agy    -> `_spawn_local` (unchanged: the Mac's own agy runner)
  5. linux + host==other          -> the ssh path (unchanged)
  6. launcher output parsing      -> one code path, both transports
  + --dry-run prints the local bash command, no `ssh` in it

No real tasks.db, no Postgres, no ssh, no network, no codex/agy/claude:
`subprocess.run` is faked for the launcher call, and the one real bash run is
the launcher's own `--dry-run`, which exits before touching anything.
"""
from __future__ import annotations

import asyncio
import base64
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.config as config  # noqa: E402
import lib.db as db_mod  # noqa: E402
import tools.delegate as delegate  # noqa: E402

_REAL_RUN = subprocess.run

LAUNCHER = str(ROOT / "scripts" / "spawn-worker-remote.sh")
CONTABO_WORKTREES = "/opt/MoonieXHQ/Agents/Core/worktrees"
SPAWNED = f"SPAWNED pid=4242 session=mooniex-task-w03b worktree={CONTABO_WORKTREES}/x\n"


class _Result:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.fixture()
def temp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    db_mod.init()
    return db_mod


@pytest.fixture(autouse=True)
def _clear_self_host_cache():
    config.self_host.cache_clear()
    yield
    config.self_host.cache_clear()


@pytest.fixture(autouse=True)
def _plenty_of_disk(monkeypatch):
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 999.0)


def _hub(monkeypatch, *, host: str, platform: str) -> None:
    """Play a hub whose own host key is `host`, on `platform`."""
    monkeypatch.setattr(delegate, "self_host", lambda: host)
    monkeypatch.setattr(sys, "platform", platform)


def _new_task(db, runner: str | None) -> str:
    return db.create_task(project="mooniex-agents", role="developer", title="w03b",
                          description="d", owner_cto="test-owner", runner=runner)


class _Calls:
    """Everything the spawn paths ran, recorded."""

    def __init__(self):
        self.argv: list[list[str]] = []
        self.kwargs: list[dict] = []
        self.spawn_local: list[str] = []


@pytest.fixture()
def calls(temp_db, monkeypatch):
    """Fake the launcher's subprocess and stub the pieces around it.

    The launcher call answers with `rec.answer` (default: a clean SPAWNED line);
    any other subprocess (there should be none) is recorded and answers empty.
    `_spawn_local` is replaced so a test can tell which path was taken.
    """
    rec = _Calls()
    rec.answer = _Result(0, SPAWNED)

    def fake_run(argv, *a, **kw):
        argv = [str(x) for x in argv]
        rec.argv.append(argv)
        rec.kwargs.append(kw)
        is_launcher = argv[0] == "bash" or (argv[0] == "ssh" and "spawn-worker-remote.sh" in argv[-1])
        return rec.answer if is_launcher else _Result(0)

    async def fake_spawn_local(task, proj, *, kickoff=None, touches=()):
        rec.spawn_local.append(task["id"])
        return temp_db.get_task(task["id"])

    monkeypatch.setattr(delegate.subprocess, "run", fake_run)
    monkeypatch.setattr(delegate, "_spawn_local", fake_spawn_local)
    monkeypatch.setattr(delegate, "_warn_if_stale_code", lambda: None)
    monkeypatch.setattr(delegate, "create_worktree", lambda project, role, tid, sparse=False: {
        "project": project, "task_id": tid, "role": role, "branch": f"agent/{role}-{tid}",
        "worktree": f"/nowhere/{tid}", "base": "main", "repo": "/nowhere", "provisioned": []})
    # the ssh path's deploy check is its own ssh/scp traffic — not under test here
    monkeypatch.setattr(delegate, "_ensure_remote_deploy_linux", lambda *a, **k: [])
    return rec


def _launcher_calls(rec: _Calls) -> list[list[str]]:
    return [a for a in rec.argv if a[0] == "bash" or (a[0] == "ssh" and "spawn-worker-remote.sh" in a[-1])]


def _flag(argv: list[str], name: str) -> str:
    return argv[argv.index(name) + 1]


# ---------------------------------------------------------------------------
# 1 + 2. linux + host==self + codex/agy -> the launcher over a local bash
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("runner", ["codex", "agy"])
def test_linux_self_host_codex_and_agy_run_the_launcher_with_local_bash(calls, temp_db, monkeypatch, runner):
    _hub(monkeypatch, host="contabo", platform="linux")
    tid = _new_task(temp_db, runner)

    row = asyncio.run(delegate.delegate_task(tid))

    launches = _launcher_calls(calls)
    assert len(launches) == 1, calls.argv
    argv = launches[0]
    assert argv[0] == "bash" and argv[1] == LAUNCHER, argv
    assert not any(a[0] in ("ssh", "scp") for a in calls.argv), "a spawn on the box itself must never ssh"
    assert calls.spawn_local == [], "codex/agy on a Linux hub must not fall into _spawn_local (Claude only)"

    assert _flag(argv, "--task") == tid
    assert _flag(argv, "--project") == "mooniex-agents"
    assert _flag(argv, "--role") == "developer"
    assert _flag(argv, "--runner") == runner
    assert _flag(argv, "--branch") == f"agent/{runner}-{tid}"
    assert _flag(argv, "--base") == "main"
    assert _flag(argv, "--worktree-root") == CONTABO_WORKTREES
    assert _flag(argv, "--repo-path") == "/opt/MoonieXHQ/Agents/Core"
    assert _flag(argv, "--claude-args") == "", "codex/agy take no claude flags"
    assert "--session-name" in argv and "--model" in argv and "--effort" in argv
    meta = json.loads(base64.b64decode(_flag(argv, "--task-meta-b64")))
    assert meta["task_id"] == tid and meta["host"] == "contabo"

    # the rendered prompt travels on the launcher's stdin, as it does over ssh
    prompt = calls.kwargs[0]["input"]
    assert tid in prompt and calls.kwargs[0]["text"] is True

    # the row ends the way a remote spawn's does
    assert row["status"] == "in_progress"
    assert row["host"] == "contabo" and row["runner"] == runner
    assert row["pid"] == 4242 and row["tmux_session"] == "mooniex-task-w03b"
    assert row["worktree"] == f"{CONTABO_WORKTREES}/x"
    assert row["branch"] == f"agent/{runner}-{tid}"


def test_local_launcher_is_the_checkouts_own_script_never_a_deployed_copy(calls, temp_db, monkeypatch):
    _hub(monkeypatch, host="contabo", platform="linux")

    def boom(*a, **k):
        raise AssertionError("the local transport must not copy the launcher into .launch/")

    monkeypatch.setattr(delegate, "_ensure_remote_deploy_linux", boom)
    tid = _new_task(temp_db, "codex")

    asyncio.run(delegate.delegate_task(tid))

    argv = _launcher_calls(calls)[0]
    assert argv[1] == LAUNCHER and ".launch/" not in " ".join(argv)


def test_local_launcher_never_inherits_the_hubs_secrets(calls, temp_db, monkeypatch):
    # Over ssh the launcher starts from a fresh sshd environment. Run locally
    # it must not carry the hub's ORG_DB_URL / session ids into a codex/agy
    # worker (a launcher that starts the first tmux server hands its env on).
    # ORG_DB_URL itself would switch this test's own lib.db to Postgres, so
    # a stand-in secret carries the check: anything off the allow-list goes.
    _hub(monkeypatch, host="contabo", platform="linux")
    monkeypatch.setenv("MOONIEX_TEST_SECRET", "REDACTED")
    monkeypatch.setenv("CTO_SESSION_ID", "cto-00000000")
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    monkeypatch.setenv("HOME", "/root")
    tid = _new_task(temp_db, "codex")

    asyncio.run(delegate.delegate_task(tid))

    env = calls.kwargs[0]["env"]
    assert env is not None, "a local launcher run must get an explicit env"
    assert "MOONIEX_TEST_SECRET" not in env and "CTO_SESSION_ID" not in env
    assert "ORG_DB_URL" not in delegate._LOCAL_LAUNCHER_ENV_KEYS
    assert env["PATH"] == "/usr/bin:/bin" and env["HOME"] == "/root"
    assert set(env) <= set(delegate._LOCAL_LAUNCHER_ENV_KEYS)


def test_ssh_transport_env_is_left_alone(calls, temp_db, monkeypatch):
    _hub(monkeypatch, host="mac", platform="darwin")
    tid = _new_task(temp_db, "codex")

    asyncio.run(delegate.delegate_task(tid, host="contabo"))

    assert _launcher_calls(calls)[0][0] == "ssh"
    assert calls.kwargs[0].get("env") is None


def test_dry_run_prints_the_local_bash_command_with_no_ssh(calls, temp_db, monkeypatch):
    _hub(monkeypatch, host="contabo", platform="linux")
    tid = _new_task(temp_db, "codex")

    row = asyncio.run(delegate.delegate_task(tid, dry_run=True))

    log = row["delegate_log"]
    assert log.startswith(f"[dry-run] host=contabo local_cmd=bash {LAUNCHER} "), log
    assert "ssh" not in log
    assert f"--task {tid}" in log and "--runner codex" in log and f"--branch agent/codex-{tid}" in log
    assert row["status"] == "pending", "a dry-run never advances the row"
    assert calls.argv == [], f"a dry-run must run nothing at all: {calls.argv}"


def test_local_argv_is_accepted_by_the_real_launcher(calls, temp_db, monkeypatch):
    """Hand the exact argv the hub built to the real script, with only --dry-run
    added: it must parse every flag and echo them back. The script's dry-run
    branch exits before any git/tmux/file work, so nothing is spawned."""
    _hub(monkeypatch, host="contabo", platform="linux")
    seen: list[subprocess.CompletedProcess] = []

    def run_launcher_dry(argv, *a, **kw):
        assert argv[0] == "bash"
        r = _REAL_RUN([*argv, "--dry-run"], *a, **kw)
        seen.append(r)
        return _Result(r.returncode, SPAWNED)  # the hub still needs a SPAWNED line to finish

    monkeypatch.setattr(delegate.subprocess, "run", run_launcher_dry)
    tid = _new_task(temp_db, "agy")

    asyncio.run(delegate.delegate_task(tid))

    assert len(seen) == 1 and seen[0].returncode == 0, seen[0].stderr
    out = seen[0].stdout
    assert f"task={tid}" in out and "runner=agy" in out
    assert f"worktree={CONTABO_WORKTREES}/mooniex-agents__developer__{tid}" in out
    assert f"tmux_session=mooniex-{tid}" in out
    assert "agy -p" in out, "the agy runner block, not claude's"


# ---------------------------------------------------------------------------
# 3 + 4. the cases that must NOT change
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("runner", ["claude", None])
def test_linux_self_host_claude_still_goes_to_spawn_local(calls, temp_db, monkeypatch, runner):
    _hub(monkeypatch, host="contabo", platform="linux")
    tid = _new_task(temp_db, runner)

    asyncio.run(delegate.delegate_task(tid))

    assert calls.spawn_local == [tid]
    assert _launcher_calls(calls) == []


def test_darwin_self_host_agy_still_goes_to_spawn_local(calls, temp_db, monkeypatch):
    _hub(monkeypatch, host="mac", platform="darwin")
    tid = _new_task(temp_db, "agy")

    asyncio.run(delegate.delegate_task(tid))

    assert calls.spawn_local == [tid]
    assert _launcher_calls(calls) == [], "the Mac's agy runs through _spawn_local, never the launcher"


# ---------------------------------------------------------------------------
# 5. linux + host==other -> ssh, as before
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("runner", ["codex", "claude"])
def test_linux_hub_to_another_host_still_uses_ssh(calls, temp_db, monkeypatch, runner):
    _hub(monkeypatch, host="mac", platform="linux")  # any hub that is not the target
    tid = _new_task(temp_db, runner)

    row = asyncio.run(delegate.delegate_task(tid, host="contabo"))

    launches = _launcher_calls(calls)
    assert len(launches) == 1
    argv = launches[0]
    assert argv[:2] == ["ssh", "mooniex-vps"], argv
    assert argv[2].startswith("bash /opt/MoonieXHQ/Agents/Core/.launch/spawn-worker-remote.sh "), argv[2]
    assert calls.spawn_local == []
    assert row["status"] == "in_progress" and row["host"] == "contabo"


def test_linux_hub_to_another_host_dry_run_is_still_the_ssh_command(calls, temp_db, monkeypatch):
    _hub(monkeypatch, host="mac", platform="linux")
    tid = _new_task(temp_db, "codex")

    row = asyncio.run(delegate.delegate_task(tid, host="contabo", dry_run=True))

    assert "[dry-run] host=contabo ssh_cmd=ssh mooniex-vps " in row["delegate_log"]
    assert "local_cmd" not in row["delegate_log"]


def test_local_transport_is_linux_only():
    with pytest.raises(NotImplementedError, match="linux-only"):
        asyncio.run(delegate._spawn_remote({"id": "t", "role": "developer", "project": "mooniex-agents"},
                                           "winbox", local=True))


# ---------------------------------------------------------------------------
# 6. one parser for both transports
# ---------------------------------------------------------------------------

def _transport(monkeypatch, name: str) -> dict:
    """Arrange the hub for `name` and return the delegate_task kwargs that reach it."""
    if name == "local":
        _hub(monkeypatch, host="contabo", platform="linux")
        return {}
    _hub(monkeypatch, host="mac", platform="linux")
    return {"host": "contabo"}


@pytest.mark.parametrize("transport", ["local", "ssh"])
@pytest.mark.parametrize("answer, status, needle", [
    (_Result(1, "SPAWN_REFUSED=dirty-worktree /opt/x/wt\n"), "conflict", "dirty-worktree"),
    (_Result(1, "SPAWN_REFUSED=codex-not-found (checked PATH)\n"), "conflict", "codex-not-found"),
    (_Result(0, "some unexpected line with no SPAWNED marker\n"), "failed", "failed"),
    (_Result(1, "", "git fetch failed"), "failed", "git fetch failed"),
    (_Result(0, "SPAWNED pid=notanumber session=s worktree=/w\n"), "failed", "unparseable SPAWNED line"),
    (_Result(0, SPAWNED), "in_progress", None),
])
def test_launcher_output_is_parsed_the_same_over_both_transports(calls, temp_db, monkeypatch,
                                                                 transport, answer, status, needle):
    kwargs = _transport(monkeypatch, transport)
    calls.answer = answer
    tid = _new_task(temp_db, "codex")

    row = asyncio.run(delegate.delegate_task(tid, **kwargs))

    assert len(_launcher_calls(calls)) == 1
    assert _launcher_calls(calls)[0][0] == ("bash" if transport == "local" else "ssh")
    assert row["status"] == status, row["delegate_log"]
    if needle:
        assert needle in row["delegate_log"]
    if status == "in_progress":
        assert row["pid"] == 4242 and row["tmux_session"] == "mooniex-task-w03b"
    else:
        assert not row["pid"], "a refused/failed launch leaves no pid on the row"
