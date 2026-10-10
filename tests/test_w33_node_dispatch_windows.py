"""Org Mesh W3.3 (docs/design/org-mesh.md): tools/node_dispatch.py on Windows,
and letters that reach a worker.

Nothing here touches PowerShell, Task Scheduler, tmux or a real worktree. The
platform is faked at `node_dispatch._is_windows`, `subprocess.run` is a recorder
(and `Popen` explodes), lib.db is a tmp_path SQLite ledger (ADR 0021), and the
mailbox, the lock dir and the worktree root are tmp_path too. The live run on
winbox is W3.4.

Run:  .venv/bin/python -m pytest tests/test_w33_node_dispatch_windows.py
"""
from __future__ import annotations

import ast
import base64
import ctypes
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import config as config_mod  # noqa: E402
from lib import db as db_mod  # noqa: E402
from lib import mailbox, mesh, proc  # noqa: E402
from tools import agent_transport, delegate, send_to_cxo, session_status, tmux_session  # noqa: E402
from tools import send_to_worker as sw  # noqa: E402
from tools import node_dispatch as nd  # noqa: E402

UUID = "12345678-1234-1234-1234-123456789abc"
_TID = "task-1234abcd"


class Runs:
    """subprocess.run, replaced. `calls` is every argv that reached it."""

    def __init__(self) -> None:
        self.calls: list[tuple[list, dict]] = []
        self.rc = 0
        self.out = "STARTED Running\r\n"
        self.err = ""

    def __call__(self, argv, **kw):
        self.calls.append((list(argv), kw))
        return subprocess.CompletedProcess(argv, self.rc, self.out, self.err)


def _boom(*a, **kw):
    raise AssertionError("must not be reached")


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    for var in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE",
                "SSH_ORIGINAL_COMMAND", "SSH_CLIENT", "ORG_WIN_WAKE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setattr(config_mod, "self_host", lambda: "winbox")
    monkeypatch.setattr(mailbox, "INBOX_ROOT", tmp_path / "inbox")
    locks = tmp_path / "locks"
    locks.mkdir()
    monkeypatch.setattr(send_to_cxo, "LOCKS_DIR", locks)
    monkeypatch.setattr(nd, "_worktrees_root", lambda: tmp_path / "worktrees")
    (tmp_path / "worktrees").mkdir()
    # W2.7 F3b: the spawn gate reads free disk; these tests are about the launch, not the box.
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 100.0)


@pytest.fixture
def runs(monkeypatch) -> Runs:
    r = Runs()
    monkeypatch.setattr(subprocess, "run", r)
    monkeypatch.setattr(subprocess, "Popen", _boom)
    return r


@pytest.fixture
def win(monkeypatch, runs):
    """This process is winbox: platform faked, no tmux, wake and os.kill explode."""
    monkeypatch.setattr(nd, "_is_windows", lambda: True)
    monkeypatch.setattr(tmux_session, "has_session", _boom)
    monkeypatch.setattr(send_to_cxo, "attempt_wake", _boom)
    monkeypatch.setattr(agent_transport, "attempt_wake", _boom)
    monkeypatch.setattr(nd.os, "kill", _boom)
    return runs


def _update(tid: str, **cols) -> None:
    sets = ", ".join(f"{k}=?" for k in cols)
    with db_mod.get_conn() as conn:
        conn.execute(f"UPDATE tasks SET {sets} WHERE id=?", (*cols.values(), tid))


def _mk_task(**cols) -> str:
    tid = db_mod.create_task("projA", "developer", "t", "d")
    if cols:
        _update(tid, **cols)
    return tid


def _script_of(argv: list) -> str:
    """The PowerShell text behind a `powershell.exe ... -EncodedCommand <b64>` argv."""
    return base64.b64decode(argv[argv.index("-EncodedCommand") + 1]).decode("utf-16-le")


def _task_argument(script: str) -> str:
    return re.search(r"-Argument '([^']*)'", script).group(1)


# ---------------------------------------------------------------------------
# pid_alive
# ---------------------------------------------------------------------------

def test_pid_alive_on_windows_goes_through_lib_proc_and_never_signals(monkeypatch, runs):
    seen = []

    def fake_win_alive(pid, denied_is_alive):
        seen.append((pid, denied_is_alive))
        return pid == 4242

    monkeypatch.setattr(nd.os, "kill", _boom)  # os.kill(pid, 0) sends Ctrl-C on Windows
    monkeypatch.setattr(proc, "_win_pid_alive", fake_win_alive)
    live = _mk_task(host="winbox", pid=4242)
    gone = _mk_task(host="winbox", pid=4243)
    with monkeypatch.context() as m:
        m.setattr(sys, "platform", "win32")
        assert nd.dispatch("pid_alive", [live])["result"] == {
            "task_id": live, "pid": 4242, "alive": True}
        assert nd.dispatch("pid_alive", [gone])["result"]["alive"] is False
    assert seen == [(4242, True), (4243, True)]  # access denied means alive


def test_pid_alive_on_windows_still_refuses_another_host_and_a_null_host(win):
    for host in ("contabo", None):
        tid = _mk_task(**({"host": host} if host else {}))
        out, code = nd._run("pid_alive", [tid])
        assert code == 2 and out["ok"] is False


def test_node_dispatch_never_calls_os_kill():
    tree = ast.parse((ROOT / "tools" / "node_dispatch.py").read_text(encoding="utf-8"))
    kills = [n.lineno for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "kill" and isinstance(n.func.value, ast.Name)
             and n.func.value.id == "os"]
    assert kills == []


# ---------------------------------------------------------------------------
# probe
# ---------------------------------------------------------------------------

def _stub_machine(monkeypatch, *, ram=8 * 1024 ** 3):
    monkeypatch.setattr(nd, "_win_avail_phys_bytes", lambda: ram)
    monkeypatch.setattr(nd, "_git_version", lambda: "abc1234")
    monkeypatch.setattr(nd, "_installed_runners", lambda: ["claude"])
    monkeypatch.setattr(nd, "_measure_provides", lambda: (["windows"], []))  # W4.4: no real ffmpeg/node
    monkeypatch.setattr(nd.os, "cpu_count", lambda: 8)
    monkeypatch.delattr(nd.os, "getloadavg", raising=False)  # absent on Windows


def test_probe_answers_on_windows(win, monkeypatch):
    _stub_machine(monkeypatch)
    live = _mk_task(host="winbox", status="in_progress", pid=4242)
    _mk_task(host="winbox", status="in_progress", pid=4243)
    monkeypatch.setattr(nd.proc, "pid_alive", lambda pid: pid == 4242)

    out = nd.dispatch("probe", [])

    assert out["ok"] is True, out
    r = out["result"]
    assert (r["host"], r["os"], r["ram_free_gb"], r["cpus"], r["load_per_core"]) == (
        "winbox", "windows", 8.0, 8, None)
    assert r["running"] == 1, live  # the dead pid is not counted any more
    assert db_mod.get_host("winbox")["ram_free_gb"] == 8.0
    assert win.calls == []


def test_probe_on_windows_survives_a_missing_ram_call(win, monkeypatch):
    _stub_machine(monkeypatch)
    monkeypatch.setattr(nd, "_win_avail_phys_bytes", lambda: None)
    out = nd.dispatch("probe", [])
    assert out["ok"] is True and out["result"]["ram_free_gb"] is None


def test_ram_free_gb_off_windows_ctypes_is_not_a_crash(win):
    # On this box `ctypes.windll` does not exist: the real call raises
    # AttributeError and `_ram_free_gb` must turn that into None.
    if hasattr(ctypes, "windll"):
        pytest.skip("real Windows")
    assert nd._ram_free_gb() is None


def test_memory_status_struct_matches_the_win32_layout():
    assert ctypes.sizeof(nd._MemoryStatusEx) == 64


# ---------------------------------------------------------------------------
# start_clevel
# ---------------------------------------------------------------------------

def test_start_clevel_fresh_registers_one_interactive_one_shot_task(win):
    out, code = nd._run("start_clevel", ["cmo"])
    assert code == 0, out
    res = out["result"]
    assert set(res) == {"role", "via", "session_id", "task_name", "resumed_from"}
    assert (res["role"], res["via"], res["resumed_from"]) == ("cmo", "schtask", None)
    assert re.fullmatch(r"[0-9a-f]{8}", res["session_id"])
    assert res["task_name"] == f"mooniex-cxo-cmo-{res['session_id']}"

    (argv, kw), = win.calls  # one powershell call: no tmux, no bash, no ssh
    assert argv[:6] == ["powershell.exe", "-NoProfile", "-NonInteractive",
                        "-ExecutionPolicy", "Bypass", "-EncodedCommand"]
    assert kw.get("shell") is not True and isinstance(argv, list)
    script = _script_of(argv)
    for needle in ("New-ScheduledTaskPrincipal", "-LogonType Interactive",
                   "Register-ScheduledTask", "Start-ScheduledTask",
                   "Unregister-ScheduledTask", f"'{res['task_name']}'"):
        assert needle in script, needle
    assert _task_argument(script) == (
        f'-NoProfile -ExecutionPolicy Bypass -File "{ROOT / "windows" / "cxo-claude.ps1"}" '
        f"-Role cmo -Session {res['session_id']}")


def test_start_clevel_resume_passes_the_full_uuid_as_a_resume_flag(win, monkeypatch):
    monkeypatch.setattr(session_status, "get", lambda role, sid: {"host": nd._self_host()})
    monkeypatch.setattr(session_status, "resume_target", lambda role, sid: UUID)
    out, code = nd._run("start_clevel", ["cto", "--resume", "1234abcd"])
    assert code == 0, out
    assert out["result"]["resumed_from"] == "1234abcd"
    (argv, _), = win.calls
    argument = _task_argument(_script_of(argv))
    assert argument.endswith(f"-Role cto -Session {out['result']['session_id']} --resume {UUID}")
    assert " -r " not in argument  # PowerShell would bind -r as -Role / -RemainingArgs


@pytest.mark.parametrize("target", [None, "", "1234abcd", UUID + "; id", UUID + "\nid",
                                    UUID + "$(id)", UUID + "'; id; '"])
def test_start_clevel_resume_without_a_real_uuid_is_refused(win, monkeypatch, target):
    monkeypatch.setattr(session_status, "resume_target", lambda role, sid: target)
    _, code = nd._run("start_clevel", ["cto", "--resume", "1234abcd"])
    assert code == 2 and win.calls == []


@pytest.mark.parametrize("rc, out", [(1, ""), (0, ""), (0, "state Ready")])
def test_start_clevel_a_task_that_did_not_start_is_a_failure(win, rc, out):
    win.rc, win.out, win.err = rc, out, "boom"
    result, code = nd._run("start_clevel", ["cfo"])
    assert code == 1 and result["ok"] is False


def test_start_clevel_powershell_that_cannot_run_is_a_failure(win, monkeypatch):
    def gone(*a, **kw):
        raise FileNotFoundError("powershell.exe")

    monkeypatch.setattr(subprocess, "run", gone)
    _, code = nd._run("start_clevel", ["cto"])
    assert code == 1


def test_start_clevel_a_repo_path_powershell_could_act_on_is_refused(win, monkeypatch, tmp_path):
    hostile = tmp_path / "x'; calc; '"
    (hostile / "windows").mkdir(parents=True)
    (hostile / "windows" / "cxo-claude.ps1").write_text("")
    monkeypatch.setattr(nd, "ROOT", hostile)
    _, code = nd._run("start_clevel", ["cto"])
    assert code == 2 and win.calls == []


@pytest.mark.parametrize("value", ["a'b", "a`b", "a$b", "a\nb", "a;b", "a&b", "a(b)"])
def test_the_task_script_builder_refuses_what_could_break_out(value):
    with pytest.raises(nd.Refusal):
        nd._one_shot_task_script("mooniex-cxo-cto-abcd1234", f"-File {value}")
    with pytest.raises(nd.Refusal):
        nd._one_shot_task_script(f"name-{value}", "-File x")


# ---------------------------------------------------------------------------
# spawn_worker
# ---------------------------------------------------------------------------

_WORKTREE_ROOT = "C:\\Users\\passg\\mooniex\\worktrees"  # config/hosts.yaml winbox.worktrees


class SpawnRuns(Runs):
    """Runs that also keeps what was in the brief file while PowerShell ran."""

    def __init__(self, repo: Path) -> None:
        super().__init__()
        self.repo = repo
        self.brief: dict[str, str] = {}
        self.out = "GITHUB_SSH_ROUTE=ok\r\nlaunched via interactive scheduled task x\r\n4321\r\n"

    def __call__(self, argv, **kw):
        for f in (self.repo / "state").glob(".remote-task-*.md"):
            self.brief[f.name] = f.read_text(encoding="utf-8")
        return super().__call__(argv, **kw)


@pytest.fixture
def spawn(monkeypatch, tmp_path):
    """A Windows box with a repo checkout at tmp_path/repo. `delegate_task` and
    tmux explode: the win32 path must reach neither."""
    repo = tmp_path / "repo"
    (repo / "windows").mkdir(parents=True)
    (repo / "windows" / "spawn-worker.ps1").write_text("")
    r = SpawnRuns(repo)
    monkeypatch.setattr(subprocess, "run", r)
    monkeypatch.setattr(subprocess, "Popen", _boom)
    monkeypatch.setattr(nd, "_is_windows", lambda: True)
    monkeypatch.setattr(nd, "ROOT", repo)
    monkeypatch.setattr(tmux_session, "has_session", _boom)
    monkeypatch.setattr(tmux_session, "create", _boom)
    from tools import delegate
    monkeypatch.setattr(delegate, "delegate_task", _boom)
    return r


def _spawn_task(**cols) -> str:
    tid = db_mod.create_task("mooniex-agents", "developer", "Fix the thing", "do it")
    _update(tid, **{"host": "winbox", **cols})
    return tid


def _row(tid: str) -> dict:
    return db_mod.get_task(tid)


def _launcher_call(spawn_runs: Runs) -> str:
    (argv, kw), = spawn_runs.calls
    assert argv[:6] == ["powershell.exe", "-NoProfile", "-NonInteractive",
                        "-ExecutionPolicy", "Bypass", "-EncodedCommand"]
    assert isinstance(argv, list) and kw.get("shell") is not True
    return _script_of(argv)


def test_spawn_worker_on_windows_runs_the_launcher_and_writes_the_row(spawn):
    tid = _spawn_task()
    out, code = nd._run("spawn_worker", [tid])
    assert code == 0, out
    assert out["result"] == {"id": tid, "status": "in_progress", "pid": 4321,
                             "branch": f"agent/developer-{tid}"}
    script = _launcher_call(spawn)
    repo = spawn.repo
    assert script.startswith(f"& '{repo / 'windows' / 'spawn-worker.ps1'}' -Task '{tid}' "
                             "-Project 'mooniex-agents' -Role 'developer' ")
    assert script.endswith("; exit $LASTEXITCODE")
    for needle in (f"-Branch 'agent/developer-{tid}'", "-Base 'main'",
                   "-RepoUrl 'git@github.com:PASAKON/mooniex-agents.git'",
                   "-RepoPath 'C:\\Users\\passg\\mooniex\\repo\\MoonieX-Agents'",
                   f"-WorktreeRoot '{_WORKTREE_ROOT}'", "-ClaudeArgs '--model ",
                   "--allowed-tools ", "-SessionName 'WINDOWS Developer #", "(Fix the thing)",
                   f"-TaskFile '{repo / 'state' / f'.remote-task-{tid}.md'}'",
                   "-Runner 'claude'", f"-AgentsRoot '{repo}'"):
        assert needle in script, needle
    assert "-RunnerModel" not in script
    row = _row(tid)
    assert (row["status"], row["pid"], row["host"], row["assigned_agent"], row["runner"]) == (
        "in_progress", 4321, "winbox", "developer", "claude")
    assert row["worktree"] == f"{_WORKTREE_ROOT}\\mooniex-agents__developer__{tid}"
    assert row["branch"] == f"agent/developer-{tid}"
    assert row["spawned_at"]


def test_spawn_worker_on_windows_writes_the_brief_for_the_launcher_and_removes_it(spawn):
    tid = _spawn_task()
    _, code = nd._run("spawn_worker", [tid])
    assert code == 0
    (name, text), = spawn.brief.items()
    assert name == f".remote-task-{tid}.md"
    assert tid in text and f"agent/developer-{tid}" in text and "do it" in text
    assert list((spawn.repo / "state").glob(".remote-task-*.md")) == []


def test_spawn_worker_on_windows_takes_a_codex_runner_and_its_model(spawn):
    tid = _spawn_task(runner="codex", runner_model="gpt-5.2-codex")
    out, code = nd._run("spawn_worker", [tid])
    assert code == 0, out
    script = _launcher_call(spawn)
    assert f"-Branch 'agent/codex-{tid}'" in script and "-ClaudeArgs ''" in script
    assert "-Runner 'codex'" in script and "-RunnerModel 'gpt-5.2-codex'" in script
    assert _row(tid)["runner"] == "codex"


def test_spawn_worker_on_windows_a_title_cannot_reach_the_script(spawn):
    tid = _spawn_task(title="x'; calc; $(id) `k` & \n" + "y" * 80)
    out, code = nd._run("spawn_worker", [tid])
    assert code == 0, out
    name = re.search(r"-SessionName '([^']*)'", _launcher_call(spawn)).group(1)
    assert re.fullmatch(r"[A-Za-z0-9_.#() -]+", name), name
    assert len(name) < 100


def test_spawn_worker_on_windows_a_dead_github_route_blocks_the_host_and_kills_the_leaked_pid(spawn):
    tid = _spawn_task()
    spawn.out = "GITHUB_SSH_ROUTE=unreachable (both port 22 and 443 probes failed)\r\n555\r\n"
    out, code = nd._run("spawn_worker", [tid])
    assert code == 1 and out["ok"] is False
    assert [c[0] for c in spawn.calls][1] == ["taskkill", "/PID", "555", "/T", "/F"]
    row = _row(tid)
    assert row["status"] == "blocked_host"
    assert "unreachable" in row["delegate_log"] and "killed leaked pid 555" in row["delegate_log"]
    assert list((spawn.repo / "state").glob(".remote-task-*.md")) == []


def test_spawn_worker_on_windows_a_refusal_from_the_launcher_is_a_conflict(spawn):
    tid = _spawn_task()
    spawn.rc = 1
    spawn.out = "SPAWN_REFUSED=dirty-worktree C:\\x\r\n"
    _, code = nd._run("spawn_worker", [tid])
    assert code == 1
    row = _row(tid)
    assert row["status"] == "conflict" and "dirty-worktree" in row["delegate_log"]


@pytest.mark.parametrize("rc, out, err", [(1, "partial\r\n", "boom"), (0, "", ""),
                                          (0, "no pid here\r\n", "")])
def test_spawn_worker_on_windows_a_launcher_that_failed_fails_the_row(spawn, rc, out, err):
    tid = _spawn_task()
    spawn.rc, spawn.out, spawn.err = rc, out, err
    _, code = nd._run("spawn_worker", [tid])
    assert code == 1
    assert _row(tid)["status"] == "failed"
    assert list((spawn.repo / "state").glob(".remote-task-*.md")) == []


def test_spawn_worker_on_windows_powershell_that_cannot_run_fails_the_row(spawn, monkeypatch):
    def gone(*a, **kw):
        raise FileNotFoundError("powershell.exe")

    monkeypatch.setattr(subprocess, "run", gone)
    tid = _spawn_task()
    _, code = nd._run("spawn_worker", [tid])
    assert code == 1 and _row(tid)["status"] == "failed"
    assert list((spawn.repo / "state").glob(".remote-task-*.md")) == []


def test_spawn_worker_on_windows_still_wants_a_pending_task_on_this_host(spawn):
    for cols in ({"status": "in_progress"}, {"status": "review"}, {"host": "contabo"}):
        tid = _spawn_task(**cols)
        _, code = nd._run("spawn_worker", [tid])
        assert code == 2, cols
    assert spawn.calls == []


@pytest.mark.parametrize("cols", [
    {"project": "mooniex-agents;calc"}, {"project": "x'y"}, {"project": "no-such-project"},
    {"role": "dev'eloper"}, {"role": "no_such_role"}, {"role": "developer&calc"},
    {"runner": "codex; calc"}, {"runner": "nope"}, {"runner": "$(id)"},
    {"runner_model": "gpt'; calc; '"}, {"runner_model": "a\nb"}, {"runner_model": "a`b"},
])
def test_spawn_worker_on_windows_a_hostile_row_is_refused_before_anything_runs(spawn, cols):
    tid = _spawn_task(**cols)
    _update(tid, status="pending")
    out, code = nd._run("spawn_worker", [tid])
    assert code == 2 and out["ok"] is False, (cols, out)
    assert spawn.calls == [] and spawn.brief == {}
    assert not (spawn.repo / "state").exists() or list((spawn.repo / "state").iterdir()) == []
    row = _row(tid)
    assert row["status"] == "pending" and not row["spawned_at"]


_GOOD = {
    "Task": _TID, "Project": "mooniex-agents", "Role": "developer",
    "Branch": f"agent/developer-{_TID}", "Base": "main",
    "RepoUrl": "git@github.com:PASAKON/mooniex-agents.git",
    "RepoPath": "C:\\Users\\passg\\repo", "WorktreeRoot": "C:\\Users\\passg\\wt",
    "ClaudeArgs": "--model claude-sonnet-5-5 --allowed-tools Read,Write,Bash",
    "Model": "claude-sonnet-5-5", "Effort": "high", "SessionName": "WINDOWS Developer #1234abcd (t)",
    "TaskFile": "C:\\r\\state\\.remote-task-x.md", "Runner": "claude", "RunnerModel": "",
    "AgentsRoot": "C:\\r",
}


def test_the_spawn_script_builder_takes_a_good_set():
    script = nd._spawn_worker_script("C:\\r\\windows\\spawn-worker.ps1", dict(_GOOD))
    assert script.startswith("& 'C:\\r\\windows\\spawn-worker.ps1' -Task 'task-1234abcd' ")
    # One quoted value: PowerShell cannot bind a leading `--model` as a parameter.
    assert "-ClaudeArgs '--model claude-sonnet-5-5 --allowed-tools Read,Write,Bash' -Model " in script


@pytest.mark.parametrize("hostile", ["'", ";", "&", "`", "$(id)", "\n", '"', "\u2018", "\u2019"])
@pytest.mark.parametrize("name", sorted(_GOOD))
def test_the_spawn_script_builder_refuses_a_hostile_value_in_every_parameter(name, hostile):
    if name == "RunnerModel":
        values = {**_GOOD, name: "gpt" + hostile}
    else:
        values = {**_GOOD, name: _GOOD[name] + hostile}
    with pytest.raises(nd.Refusal):
        nd._spawn_worker_script("C:\\r\\windows\\spawn-worker.ps1", values)


@pytest.mark.parametrize("launcher", ["C:\\r'; calc; '\\x.ps1", "C:\\r\\$(id).ps1", "a\nb", ""])
def test_the_spawn_script_builder_refuses_a_hostile_launcher_path(launcher):
    with pytest.raises(nd.Refusal):
        nd._spawn_worker_script(launcher, dict(_GOOD))


@pytest.mark.parametrize("runner", ["", "CLAUDE", "gemini", None, 7])
def test_the_spawn_script_builder_refuses_a_runner_that_is_not_known(runner):
    with pytest.raises(nd.Refusal):
        nd._spawn_worker_script("C:\\r\\x.ps1", {**_GOOD, "Runner": runner})


def test_spawn_worker_off_windows_still_goes_through_delegate_task(monkeypatch):
    seen = []

    async def fake(task_id, host=None, **kw):
        seen.append((task_id, host))
        _update(task_id, status="in_progress", pid=7)

    from tools import delegate
    monkeypatch.setattr(delegate, "delegate_task", fake)
    monkeypatch.setattr(nd, "_is_windows", lambda: False)
    monkeypatch.setattr(nd, "_spawn_worker_windows", _boom)
    tid = _spawn_task()
    out, code = nd._run("spawn_worker", [tid])
    assert code == 0, out
    assert seen == [(tid, "winbox")]


# ---------------------------------------------------------------------------
# deliver_letter: a C-level session
# ---------------------------------------------------------------------------

def _letter(**kw) -> int:
    args = dict(to_session="abcd1234", from_role="cmo", from_session="1234abcd")
    args.update(kw)
    return db_mod.create_letter(args.pop("to_host", "winbox"), args.pop("to_role", "cto"),
                                args.pop("body", "hello"), **args)


def _lock(tmp_path, role="cto", sid="abcd1234", text="4242"):
    (tmp_path / "locks" / f"{role}-{sid}.lock").write_text(text)


def test_deliver_letter_to_a_clevel_on_windows_writes_the_inbox_and_does_not_wake(
        win, monkeypatch, tmp_path):
    _lock(tmp_path)
    monkeypatch.setattr(nd.proc, "pid_alive", lambda pid: pid == 4242)
    lid = _letter()

    out, code = nd._run("deliver_letter", [str(lid)])

    assert code == 0, out
    assert out["result"] == {"letter_id": lid, "delivered": True, "to": "cto-abcd1234",
                             "woke": False}
    assert [(m["body"], m["from"]["role"]) for m in mailbox.peek("cto", "abcd1234")] == [
        ("hello", "cmo")]
    row = db_mod.get_letter(lid)
    assert row["status"] == "delivered" and row["delivered_at"]
    assert win.calls == []  # tmux, wake and subprocess were never consulted


def test_deliver_letter_on_windows_uses_the_active_session_when_none_is_named(
        win, monkeypatch, tmp_path):
    _lock(tmp_path, sid="deadbeef")
    monkeypatch.setattr(nd.proc, "pid_alive", lambda pid: True)
    monkeypatch.setattr(send_to_cxo, "_active_session_id", lambda role: "deadbeef")
    out, code = nd._run("deliver_letter", [str(_letter(to_session=None))])
    assert code == 0 and out["result"]["to"] == "cto-deadbeef"


@pytest.mark.parametrize("lock", [None, "4243", "not-a-pid", ""])
def test_deliver_letter_on_windows_to_a_session_that_is_not_running_is_a_failure(
        win, monkeypatch, tmp_path, lock):
    if lock is not None:
        _lock(tmp_path, text=lock)
    monkeypatch.setattr(nd.proc, "pid_alive", lambda pid: pid == 4242)
    lid = _letter()
    out, code = nd._run("deliver_letter", [str(lid)])
    assert code == 1 and "no live session" in out["error"]
    row = db_mod.get_letter(lid)
    assert row["status"] == "pending" and row["attempts"] == 1
    assert not (tmp_path / "inbox").exists()


# ---------------------------------------------------------------------------
# deliver_letter: a worker
# ---------------------------------------------------------------------------

def _worker(tmp_path, **over) -> tuple[str, Path]:
    tid = db_mod.create_task("projA", "developer", "t", "d")
    wt = tmp_path / "worktrees" / f"projA__developer__{tid}"
    wt.mkdir(parents=True)
    cols = dict(host="winbox", status="in_progress", worktree=str(wt))
    cols.update(over)
    _update(tid, **cols)
    return tid, wt


def _worker_letter(tid, **kw) -> int:
    kw.setdefault("to_host", config_mod.self_host())
    return _letter(to_role="developer", to_session=tid, **kw)


def test_worker_letter_on_windows_appends_one_verified_line_to_mailbox_md(win, tmp_path):
    tid, wt = _worker(tmp_path)
    lid = _worker_letter(tid, body="please push\nnow " + "\u0e2a\u0e27\u0e31\u0e2a\u0e14\u0e35")

    out, code = nd._run("deliver_letter", [str(lid)])

    assert code == 0, out
    assert out["result"] == {"letter_id": lid, "delivered": True,
                             "to": f"developer-{tid}", "woke": False}
    raw = (wt / "MAILBOX.md").read_bytes()
    assert raw.endswith(b"\r\n") and not raw.startswith(b"\xef\xbb\xbf")
    (line,) = raw.decode("utf-8").splitlines()
    assert re.fullmatch(
        r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ \| cmo-1234abcd \| "
        r"please push now \u0e2a\u0e27\u0e31\u0e2a\u0e14\u0e35", line), line
    assert db_mod.get_letter(lid)["status"] == "delivered"
    assert win.calls == [] and not (tmp_path / "inbox").exists()


def test_worker_letters_on_windows_append_and_never_overwrite(win, tmp_path):
    tid, wt = _worker(tmp_path)
    (wt / "MAILBOX.md").write_bytes(b"earlier line\r\n")
    for body in ("one", "two"):
        assert nd._run("deliver_letter", [str(_worker_letter(tid, body=body))])[1] == 0
    lines = (wt / "MAILBOX.md").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "earlier line"
    assert [ln.rsplit(" | ", 1)[1] for ln in lines[1:]] == ["one", "two"]


@pytest.mark.parametrize("over, kw", [
    ({"host": "contabo"}, {}),                       # not this host's task
    ({"host": None}, {}),
    ({"role": "tester"}, {}),                        # row says another role
    ({"worktree": None}, {}),
    ({"worktree": "OUTSIDE"}, {}),                   # not under the worktrees root
    ({"worktree": "MISSING"}, {}),                   # root is right, dir is gone
    ({}, {"from_role": "../x"}),
    ({}, {"from_session": "a b"}),
])
def test_worker_letter_on_windows_refuses_what_the_task_row_does_not_back(
        win, tmp_path, over, kw):
    over = dict(over)
    if over.get("worktree") == "OUTSIDE":
        outside = tmp_path / "elsewhere"
        outside.mkdir()
        over["worktree"] = str(outside)
    elif over.get("worktree") == "MISSING":
        over["worktree"] = str(tmp_path / "worktrees" / "gone")
    tid, wt = _worker(tmp_path, **over)
    lid = _worker_letter(tid, **kw)

    out, code = nd._run("deliver_letter", [str(lid)])

    assert code == 1, out
    assert not (wt / "MAILBOX.md").exists()
    assert not (tmp_path / "elsewhere" / "MAILBOX.md").exists()
    assert db_mod.get_letter(lid)["status"] == "pending"
    assert db_mod.get_letter(lid)["attempts"] == 1


@pytest.mark.parametrize("to_role, to_session", [
    ("developer", "abcd1234"),            # a session id, not a task id
    ("developer", None),
    ("developer", "task-1234abcd/../x"),
    ("developer", "task-00000000"),       # no such task
    ("ceo", "abcd1234"),
    ("../developer", _TID),
])
def test_worker_letter_needs_a_task_id_and_a_real_task(win, tmp_path, to_role, to_session):
    lid = _letter(to_role=to_role, to_session=to_session)
    _, code = nd._run("deliver_letter", [str(lid)])
    assert code == 1
    assert not (tmp_path / "inbox").exists()


def _posix_worker(monkeypatch, tmp_path, *, live=True, **over):
    """A worker letter on a non-Windows host: tmux answers, the wake is recorded."""
    monkeypatch.setattr(config_mod, "self_host", lambda: "contabo")
    monkeypatch.setattr(tmux_session, "has_session", lambda name: live)
    wakes = []
    monkeypatch.setattr(agent_transport, "attempt_wake",
                        lambda session, label, prefix, **kw: wakes.append((session, label, prefix)) or True)
    tid, _ = _worker(tmp_path, host="contabo", tmux_session="dev-abc", **over)
    return tid, wakes


def test_worker_letter_on_posix_goes_to_the_task_mailbox_and_wakes_its_tmux(
        monkeypatch, runs, tmp_path):
    tid, wakes = _posix_worker(monkeypatch, tmp_path)
    lid = _worker_letter(tid, body="status?")

    out, code = nd._run("deliver_letter", [str(lid)])

    assert code == 0, out
    assert out["result"] == {"letter_id": lid, "delivered": True, "to": f"developer-{tid}",
                             "woke": True}  # the tmux wake's own result (task-f9d23d0b)
    assert [(m["body"], m["from"]["role"]) for m in mailbox.peek("developer", tid)] == [
        ("status?", "cmo")]
    assert wakes == [("dev-abc", "CMO", "node_dispatch")]
    assert db_mod.get_letter(lid)["status"] == "delivered"
    assert runs.calls == []


def test_worker_letter_on_posix_refuses_a_tmux_session_that_is_not_live(
        monkeypatch, runs, tmp_path):
    tid, wakes = _posix_worker(monkeypatch, tmp_path, live=False)
    lid = _worker_letter(tid)
    out, code = nd._run("deliver_letter", [str(lid)])
    assert code == 1 and "no live tmux session" in out["error"]
    assert wakes == [] and not (tmp_path / "inbox").exists()
    assert db_mod.get_letter(lid)["attempts"] == 1


@pytest.mark.parametrize("tmux_name", [None, "", "a b", "x;id", "../x"])
def test_worker_letter_on_posix_refuses_a_missing_or_unsafe_tmux_name(
        monkeypatch, runs, tmp_path, tmux_name):
    tid, wakes = _posix_worker(monkeypatch, tmp_path)
    _update(tid, tmux_session=tmux_name)
    _, code = nd._run("deliver_letter", [str(_worker_letter(tid))])
    assert code == 1 and wakes == [] and not (tmp_path / "inbox").exists()


@pytest.mark.parametrize("over", [{"host": "winbox"}, {"role": "tester"}])
def test_worker_letter_on_posix_refuses_another_host_or_role(monkeypatch, runs, tmp_path, over):
    tid, wakes = _posix_worker(monkeypatch, tmp_path)
    _update(tid, **over)
    _, code = nd._run("deliver_letter", [str(_worker_letter(tid))])
    assert code == 1 and wakes == [] and not (tmp_path / "inbox").exists()


def test_worker_letter_wake_failure_never_fails_delivery(monkeypatch, runs, tmp_path):
    tid, _ = _posix_worker(monkeypatch, tmp_path)

    def broken(*a, **kw):
        raise RuntimeError("wake exploded")

    monkeypatch.setattr(agent_transport, "attempt_wake", broken)
    lid = _worker_letter(tid)
    assert nd._run("deliver_letter", [str(lid)])[1] == 0
    assert db_mod.get_letter(lid)["status"] == "delivered"


# ---------------------------------------------------------------------------
# hostile arguments: every verb, refused before anything runs
# ---------------------------------------------------------------------------

_HOSTILE = [";", "&", "`", "$(", "$(id)", "\n", '"', "'", "; calc", "& calc", "`calc`"]


def _hostile_calls():
    for h in _HOSTILE:
        for verb in ("pid_alive", "spawn_worker", "kill_worker", "publish_branch"):
            yield verb, [_TID + h]
            yield verb, [h + _TID]
            yield verb, [h]
        yield "deliver_letter", ["1" + h]
        yield "deliver_letter", [h]
        yield "start_clevel", ["cto" + h]
        yield "start_clevel", [h]
        yield "start_clevel", ["cto", "--resume", "1234abcd" + h]
        yield "start_clevel", ["cto", "--resume" + h, "1234abcd"]
        yield "start_clevel", ["cto", h, "1234abcd"]
        yield "probe", [h]
        yield "probe" + h, []


@pytest.mark.parametrize("verb, args", list(_hostile_calls()))
def test_hostile_arguments_are_refused_before_any_subprocess_on_windows(
        win, monkeypatch, verb, args):
    monkeypatch.setattr(nd, "_run_powershell", _boom)
    out, code = nd._run(verb, args)
    assert code == 2 and out["ok"] is False, (verb, args, out)
    assert win.calls == []


def test_hostile_argument_over_the_ssh_command_line_is_refused_on_windows(win, monkeypatch):
    monkeypatch.setattr(nd, "_run_powershell", _boom)
    for raw in (f"spawn_worker {_TID};calc", "start_clevel cto --resume 1234abcd$(id)",
                "start_clevel 'cto; calc'", f"pid_alive {_TID}&calc", "probe `id`"):
        out, code = nd.run_command(raw)
        assert code == 2, (raw, out)
    assert win.calls == []
    events = [json.loads(r["payload"]) for r in db_mod.recent_events(limit=50)
              if r["actor"] == nd.ACTOR]
    assert len(events) == 5 and not any(e["ok"] for e in events)


# ---------------------------------------------------------------------------
# send_to_worker: a worker on another host
# ---------------------------------------------------------------------------

class FakeMesh:
    """Stands in for lib.mesh.dispatch. `script(host, verb, args)` answers."""

    def __init__(self, script) -> None:
        self.script, self.calls = script, []

    def __call__(self, host, verb, *args, timeout=None):
        self.calls.append((host, verb, args))
        return self.script(host, verb, args)


def _ok(host, verb, args):
    return {"ok": True, "verb": verb, "result": {"delivered": True}}


def _down(host, verb, args):
    raise mesh.MeshUnreachable(f"{verb} on {host}: no route")


def _refused(host, verb, args):
    return {"ok": False, "verb": verb, "error": "letter not delivered: no live tmux session"}


def _letters() -> list[dict]:
    with db_mod.get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM letters ORDER BY id").fetchall()]


@pytest.fixture
def sender(monkeypatch):
    """This process is the Mac hub sending to a worker elsewhere."""
    monkeypatch.setattr(sw, "self_host", lambda: "mac")
    for var in ("WORKER_TASK_ID", "WORKER_ROLE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv(mesh.ENV_FLAG, raising=False)


@pytest.fixture
def flag_on(sender, monkeypatch):
    monkeypatch.setenv(mesh.ENV_FLAG, "1")


def _install(monkeypatch, script) -> FakeMesh:
    fake = FakeMesh(script)
    monkeypatch.setattr(mesh, "dispatch", fake)
    return fake


def test_send_to_a_remote_worker_flag_on_is_one_letter_and_one_verb(flag_on, monkeypatch, runs):
    fake = _install(monkeypatch, _ok)
    monkeypatch.setattr(sw, "_send_remote", _boom)
    tid = _mk_task(host="contabo", worktree="/opt/x/wt")

    out = sw.send(tid, "please push")

    assert out == f"delivered to Developer ({tid}) on contabo: [CEO] : please push"
    (letter,) = _letters()
    assert (letter["to_host"], letter["to_role"], letter["to_session"], letter["from_host"],
            letter["body"], letter["status"]) == (
        "contabo", "developer", tid, "mac", "please push", "delivered")
    assert fake.calls == [("contabo", "deliver_letter", (str(letter["id"]),))]
    assert runs.calls == []  # no ssh, no scp


@pytest.mark.parametrize("script, attempts", [(_down, 1), (_refused, 1)])
def test_send_to_a_remote_worker_that_does_not_answer_queues_and_does_not_raise(
        flag_on, monkeypatch, script, attempts):
    _install(monkeypatch, script)
    tid = _mk_task(host="contabo", worktree="/opt/x/wt")

    out = sw.send(tid, "hello")

    (letter,) = _letters()
    assert out == f"queued for contabo: Developer ({tid}) (letter {letter['id']}): [CEO] : hello"
    assert (letter["status"], letter["attempts"]) == ("pending", attempts)


def test_send_to_a_worker_on_this_host_never_touches_the_mesh(flag_on, monkeypatch):
    fake = _install(monkeypatch, _ok)
    for host in (None, "mac"):
        tid = _mk_task(**({"host": host} if host else {}))
        assert sw.send(tid, "hello").startswith(f"queued to Developer ({tid})")
        assert [m["body"] for m in mailbox.peek("developer", tid)] == ["hello"]
    assert fake.calls == [] and _letters() == []


def test_flag_off_a_remote_worker_takes_todays_ssh_path_and_never_touches_the_mesh(
        sender, monkeypatch, runs):
    def no_mesh(*a, **kw):
        raise AssertionError(f"lib.mesh must not be used: {a}")

    for name in ("dispatch", "build_argv", "_node_dispatch"):
        monkeypatch.setattr(mesh, name, no_mesh)
    monkeypatch.setattr(send_to_cxo, "dispatch_letter", no_mesh)
    seen = []
    monkeypatch.setattr(sw, "_send_remote",
                        lambda task, message, **kw: seen.append((task["id"], message)) or "ssh path")
    tid = _mk_task(host="contabo", worktree="/opt/x/wt")

    assert sw.send(tid, "hello") == "ssh path"
    assert seen == [(tid, "hello")] and _letters() == [] and runs.calls == []


def test_a_worker_letter_travels_from_send_to_worker_to_mailbox_md_on_windows(
        flag_on, monkeypatch, win, tmp_path):
    """Both ends in one process: the hub side sends, node_dispatch on 'winbox' writes."""
    tid, wt = _worker(tmp_path, host="winbox")
    _install(monkeypatch, lambda host, verb, args: nd.dispatch(verb, list(args)))

    out = sw.send(tid, "stop and push")

    assert out.startswith(f"delivered to Developer ({tid}) on winbox")
    (line,) = (wt / "MAILBOX.md").read_text(encoding="utf-8").splitlines()
    assert line.endswith(" | ceo-ceo | stop and push")
    assert _letters()[0]["status"] == "delivered"
