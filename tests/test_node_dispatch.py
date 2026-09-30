"""Org Mesh W2.2 (docs/design/org-mesh.md W2): tools/node_dispatch.py, the one
command an `org_dispatch` ssh key may run on a host.

SQLite only, same convention as tests/test_db_hosts_letters.py -- point lib.db
at a tmp_path ledger via monkeypatch, never the real state/tasks.db (ADR 0021).
Every backend (delegate, close_dev, mailbox wake, tmux, git push) is replaced by
a recorder; a refused call must leave `calls` empty.

Run:  .venv/bin/python -m pytest tests/test_node_dispatch.py
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from lib import config as config_mod
from lib import db as db_mod
from lib import mailbox
from tools import delegate, send_to_cxo, session_status, tmux_session, worker_reap
from tools import node_dispatch as nd

ROOT = Path(nd.ROOT)
UUID = "12345678-1234-1234-1234-123456789abc"


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    for var in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE",
                "SSH_ORIGINAL_COMMAND", "SSH_CLIENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setattr(config_mod, "self_host", lambda: "mac")
    monkeypatch.setattr(mailbox, "INBOX_ROOT", tmp_path / "inbox")
    monkeypatch.setattr(nd, "SPAWN_PROMPT_DELAY_S", 0)
    monkeypatch.setattr(nd, "_worktrees_root", lambda: tmp_path / "worktrees")


def _update(tid: str, **cols) -> None:
    if not cols:
        return
    sets = ", ".join(f"{k}=?" for k in cols)
    with db_mod.get_conn() as conn:
        conn.execute(f"UPDATE tasks SET {sets} WHERE id=?", (*cols.values(), tid))


def _mk_task(**cols) -> str:
    tid = db_mod.create_task("projA", "developer", "t", "d")
    _update(tid, **cols)
    return tid


def _dispatch_events() -> list[dict]:
    rows = [r for r in db_mod.recent_events(limit=200) if r["actor"] == nd.ACTOR]
    for r in rows:
        r["payload"] = json.loads(r["payload"])
    return rows


class Recorder:
    """Every effectful backend, replaced. `calls` is what reached one."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.push_rc = 0
        self.script_rc = 0
        self.script_out = "spawned iTerm window id=abcd1234 (logs at x)"
        self.close_result: dict | None = None
        self.wake_raises = False
        self.session_live = True

    def run(self, argv, **kw):
        self.calls.append(("run", list(argv), kw))
        if argv[:2] == ["git", "push"]:
            return subprocess.CompletedProcess(argv, self.push_rc, "", "remote: boom")
        if argv[0] == "bash":
            return subprocess.CompletedProcess(argv, self.script_rc, self.script_out, "err")
        return subprocess.CompletedProcess(argv, 0, "", "")


def _counting(fn, r: Recorder, name: str):
    def wrapper(*a, **kw):
        r.calls.append((name, a, kw))
        return fn(*a, **kw)
    return wrapper


@pytest.fixture
def rec(monkeypatch) -> Recorder:
    r = Recorder()

    async def fake_delegate(task_id, **kw):
        r.calls.append(("delegate", task_id, kw))
        _update(task_id, status="in_progress", pid=4242,
                branch=f"agent/developer-{task_id}", host="mac")

    def fake_close_dev(task_id, *, reason):
        r.calls.append(("close_dev", task_id, reason))
        return r.close_result or {"task_id": task_id, "refused": None, "reason": reason}

    def fake_wake(role, sid, label):
        r.calls.append(("wake", role, sid, label))
        if r.wake_raises:
            raise RuntimeError("wake exploded")

    def fake_create(name, cwd, cmd):
        r.calls.append(("tmux_create", name, str(cwd), cmd))

    monkeypatch.setattr(subprocess, "run", r.run)
    monkeypatch.setattr(delegate, "delegate_task", fake_delegate)
    monkeypatch.setattr(worker_reap, "close_dev", fake_close_dev)
    monkeypatch.setattr(send_to_cxo, "attempt_wake", fake_wake)
    monkeypatch.setattr(tmux_session, "create", fake_create)
    monkeypatch.setattr(tmux_session, "has_session", lambda name: r.session_live)
    monkeypatch.setattr(mailbox, "send", _counting(mailbox.send, r, "mailbox_send"))
    monkeypatch.setattr(db_mod, "upsert_host",
                        _counting(db_mod.upsert_host, r, "upsert_host"))
    return r


# ---------------------------------------------------------------------------
# parser fuzz: refused with exit 2, never reaches a backend
# ---------------------------------------------------------------------------

_TID = "task-1234abcd"
_ONE_TASK_VERBS = ("pid_alive", "spawn_worker", "kill_worker", "publish_branch")

_FUZZ = [
    "",
    "   ",
    "nosuchverb",
    "PROBE",
    "probe extra",
    f"probe {_TID}",
    "рrobe",                                  # Cyrillic er
    "deliver_letter",
    "deliver_letter 1 2",
    "deliver_letter -1",
    "deliver_letter 1.0",
    "deliver_letter 1234567890123",                # 13 digits
    "deliver_letter １２",                 # fullwidth digits
    "deliver_letter '1;id'",
    "start_clevel",
    "start_clevel ceo",
    "start_clevel nobody",
    "start_clevel cto --resume",
    "start_clevel cto --resume abc",
    "start_clevel cto --resume 1234abcd extra",
    "start_clevel cto -x 1234abcd",
    "start_clevel cto --resume 1234ABCD",
    "start_clevel cto --resume '1234abcd;id'",
    f"pid_alive {_TID}; id",                       # 3 tokens
    f"pid_alive '{_TID}; id'",                     # 1 token, fails the pattern
    "pid_alive $(id)",
    "pid_alive `id`",
    "pid_alive ${HOME}",
    f"pid_alive {_TID}\nprobe",
    f"pid_alive {_TID}\rprobe",
    f"pid_alive {_TID}\x00",
    f"pid_alive {_TID}\tprobe",
    f"pid_alive '{_TID}",                          # shlex cannot parse
    f"pid_alive {_TID} 'x",
    "pid_alive tаsk-1234abcd",                # Cyrillic a
    "pid_alive task-１２３４abcd",
    "pid_alive task-1234ABCD",
    "pid_alive ../../etc/passwd",
    "pid_alive task-1234abcd/../x",
    "spawn_worker -",
    "publish_branch agent/developer-task-1234abcd",
    "kill_worker http://evil.example/x",
    "x" * 257,
    f"pid_alive {'x' * 300}",
]
for _v in _ONE_TASK_VERBS:
    _FUZZ += [_v, f"{_v} {_TID} {_TID}", f"{_v} {_TID} extra"]


@pytest.mark.parametrize("raw", _FUZZ, ids=lambda s: repr(s)[:50])
def test_fuzz_refused_and_never_reaches_a_backend(raw, rec):
    out, code = nd.run_command(raw)
    assert code == 2, out
    assert out["ok"] is False and out["error"]
    assert rec.calls == []
    rows = _dispatch_events()
    assert len(rows) == 1
    assert rows[0]["kind"] == "dispatch"
    assert rows[0]["payload"]["ok"] is False


def test_refusal_that_cannot_parse_logs_the_raw_string_truncated(rec):
    raw = "pid_alive " + "x" * 400
    _, code = nd.run_command(raw)
    assert code == 2
    payload = _dispatch_events()[0]["payload"]
    assert payload["verb"] is None
    assert payload["raw"] == raw[:256]
    assert len(payload["raw"]) == 256


def test_argv_element_with_newline_is_refused(rec, capsys):
    assert nd.main(["pid_alive", f"{_TID}\nprobe"]) == 2
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False and out["verb"] is None
    assert rec.calls == []


def test_dispatch_refuses_non_string_args(rec):
    assert nd.dispatch("pid_alive", [1234])["ok"] is False
    assert nd.dispatch("pid_alive", "task-1234abcd")["ok"] is False
    assert nd.dispatch(None, [])["ok"] is False
    assert rec.calls == []


def test_unknown_verb_error_is_bounded(rec):
    out = nd.dispatch("v" * 500, [])
    assert out["ok"] is False
    assert len(out["verb"]) == 64
    assert len(out["error"]) < 300


# ---------------------------------------------------------------------------
# probe
# ---------------------------------------------------------------------------

def test_probe_reports_facts_and_writes_probe_fields_only(monkeypatch):
    monkeypatch.setattr(nd, "_git_version", lambda: "abc1234")
    db_mod.upsert_host("mac", os="darwin", agents_root="/x", status="online",
                       max_workers=4)
    _mk_task(host="mac", status="in_progress", pid=os.getpid())
    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait()
    _mk_task(host="mac", status="in_progress", pid=dead.pid)
    _mk_task(host="winbox", status="in_progress", pid=os.getpid())

    out = nd.dispatch("probe", [])

    assert out["ok"] is True, out
    r = out["result"]
    assert r["host"] == "mac" and r["version"] == "abc1234"
    assert r["agents_root"] == str(ROOT)
    assert r["running"] == 1
    assert isinstance(r["free_gb"], float)
    assert r["os"] in ("darwin", "linux", "windows")
    h = db_mod.get_host("mac")
    assert h["version"] == "abc1234" and h["running"] == 1 and h["probed_at"]
    # identity fields and the join-state `status` are untouched
    assert (h["os"], h["agents_root"], h["status"], h["max_workers"]) == (
        "darwin", "/x", "online", 4)


def test_probe_takes_no_arguments(rec):
    assert nd.dispatch("probe", ["x"])["ok"] is False
    assert not [c for c in rec.calls if c[0] == "upsert_host"]


# ---------------------------------------------------------------------------
# pid_alive
# ---------------------------------------------------------------------------

def test_pid_alive_true_and_false():
    live = _mk_task(host="mac", pid=os.getpid())
    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait()
    gone = _mk_task(host="mac", pid=dead.pid)
    nopid = _mk_task(host="mac")
    assert nd.dispatch("pid_alive", [live])["result"]["alive"] is True
    assert nd.dispatch("pid_alive", [gone])["result"]["alive"] is False
    assert nd.dispatch("pid_alive", [nopid])["result"] == {
        "task_id": nopid, "pid": None, "alive": False}


def test_pid_alive_permission_error_means_alive(monkeypatch):
    tid = _mk_task(host="mac", pid=1)

    def deny(pid, sig):
        raise PermissionError

    monkeypatch.setattr(nd.os, "kill", deny)
    assert nd.dispatch("pid_alive", [tid])["result"]["alive"] is True


def test_pid_alive_never_signals_pid_zero_or_negative(monkeypatch):
    seen = []
    monkeypatch.setattr(nd.os, "kill", lambda pid, sig: seen.append(pid))
    for pid in (0, -1, None):
        tid = _mk_task(host="mac", **({} if pid is None else {"pid": pid}))
        assert nd.dispatch("pid_alive", [tid])["result"]["alive"] is False
    assert seen == []


def test_pid_alive_refuses_other_host_null_host_and_unknown_task():
    other = _mk_task(host="winbox", pid=os.getpid())
    unset = _mk_task(pid=os.getpid())
    for tid in (other, unset, "task-00000000"):
        out, code = nd.run_command(f"pid_alive {tid}")
        assert code == 2 and out["ok"] is False


# pid_alive on Windows (lib.proc, no os.kill): tests/test_w33_node_dispatch_windows.py


# ---------------------------------------------------------------------------
# spawn_worker
# ---------------------------------------------------------------------------

def test_spawn_worker_happy_path(rec):
    tid = _mk_task(status="pending", host="mac")
    out, code = nd.run_command(f"spawn_worker {tid}")
    assert code == 0, out
    assert out["result"] == {"id": tid, "status": "in_progress", "pid": 4242,
                             "branch": f"agent/developer-{tid}"}
    assert rec.calls == [("delegate", tid, {"host": "mac"})]


def test_spawn_worker_refusals_never_reach_delegate(rec):
    busy = _mk_task(host="mac", status="in_progress")
    other = _mk_task(host="winbox", status="pending")
    # W2.7 F2: a pending row the hub never routed (host NULL) is refused on
    # every OS; delegate.mesh_spawn_worker always names the host first.
    unrouted = _mk_task(status="pending")
    for tid in (busy, other, unrouted, "task-00000000"):
        _, code = nd.run_command(f"spawn_worker {tid}")
        assert code == 2
    assert rec.calls == []


def test_spawn_worker_queued_by_delegate_is_a_failure(rec, monkeypatch):
    async def queued(task_id, **kw):
        rec.calls.append(("delegate", task_id, kw))

    monkeypatch.setattr(delegate, "delegate_task", queued)
    tid = _mk_task(status="pending", host="mac")
    out, code = nd.run_command(f"spawn_worker {tid}")
    assert code == 1 and "pending" in out["error"]


def test_spawn_worker_backend_exception_is_a_failure(rec, monkeypatch):
    async def boom(task_id, **kw):
        raise ValueError("already merged")

    monkeypatch.setattr(delegate, "delegate_task", boom)
    tid = _mk_task(status="pending", host="mac")
    out, code = nd.run_command(f"spawn_worker {tid}")
    assert code == 1 and "already merged" in out["error"]


# ---------------------------------------------------------------------------
# kill_worker
# ---------------------------------------------------------------------------

def test_kill_worker_happy_path(rec, monkeypatch):
    monkeypatch.setenv("SSH_CLIENT", "100.64.0.9 50000 22")
    tid = _mk_task(host="mac", status="review")
    out, code = nd.run_command(f"kill_worker {tid}")
    assert code == 0 and out["result"]["task_id"] == tid
    assert rec.calls == [("close_dev", tid, "node_dispatch kill_worker from 100.64.0.9")]


def test_kill_worker_keeps_close_dev_refusal_rules(rec):
    rec.close_result = {"task_id": "x", "refused": "status in_progress is not reapable"}
    tid = _mk_task(host="mac", status="in_progress")
    out, code = nd.run_command(f"kill_worker {tid}")
    assert code == 2 and "not reapable" in out["error"]


def test_kill_worker_refuses_other_host(rec):
    tid = _mk_task(host="contabo", status="review")
    _, code = nd.run_command(f"kill_worker {tid}")
    assert code == 2 and rec.calls == []


# ---------------------------------------------------------------------------
# start_clevel
# ---------------------------------------------------------------------------

def test_start_clevel_darwin_uses_the_existing_launchers(rec, monkeypatch):
    monkeypatch.setattr(nd, "_os_name", lambda: "darwin")
    cxo = str(ROOT / "scripts" / "spawn-cxo.sh")
    cto = str(ROOT / "scripts" / "spawn-cto.sh")

    out, code = nd.run_command("start_clevel cmo")
    assert code == 0 and out["result"]["session_id"] == "abcd1234"
    nd.run_command("start_clevel cto")
    nd.run_command("start_clevel cfo --resume 1234abcd")

    argvs = [c[1] for c in rec.calls if c[0] == "run"]
    assert argvs == [
        ["bash", cxo, "--role", "cmo"],
        ["bash", cto],
        ["bash", cxo, "--role", "cfo", "--resume", "1234abcd"],
    ]
    assert all(c[2].get("shell") is not True for c in rec.calls)


def test_start_clevel_darwin_script_failure_is_a_failure(rec, monkeypatch):
    monkeypatch.setattr(nd, "_os_name", lambda: "darwin")
    rec.script_rc = 1
    out, code = nd.run_command("start_clevel cmo")
    assert code == 1 and "exit 1" in out["error"]


def test_start_clevel_linux_spawns_cxo_claude_in_tmux(rec, monkeypatch):
    monkeypatch.setattr(nd, "_os_name", lambda: "linux")
    out, code = nd.run_command("start_clevel cmo")
    assert code == 0, out
    (_, name, cwd, cmd), = [c for c in rec.calls if c[0] == "tmux_create"]
    sid = out["result"]["session_id"]
    assert name == f"cmo-{sid}" and cwd == str(ROOT)
    assert cmd == (f"export CXO_SESSION_ID={sid} && exec bash "
                   f"{shlex.quote(str(ROOT / 'scripts' / 'cxo-claude.sh'))} --role cmo")
    # the "new MCP servers" prompt is dismissed, argv list, no shell
    last_run = [c for c in rec.calls if c[0] == "run"][-1]
    assert last_run[1] == ["tmux", "send-keys", "-t", name, "Escape"]
    assert out["result"]["prompt_dismissed"] is True


def test_start_clevel_linux_resume_passes_a_full_uuid(rec, monkeypatch):
    monkeypatch.setattr(nd, "_os_name", lambda: "linux")
    monkeypatch.setattr(session_status, "resume_target", lambda role, sid: UUID)
    out, code = nd.run_command("start_clevel cto --resume 1234abcd")
    assert code == 0, out
    cmd = [c for c in rec.calls if c[0] == "tmux_create"][0][3]
    assert cmd.endswith(f"--role cto -r {UUID}")


@pytest.mark.parametrize("target", [None, "", "1234abcd", UUID + "; id"])
def test_start_clevel_linux_resume_without_a_real_uuid_is_refused(rec, monkeypatch, target):
    monkeypatch.setattr(nd, "_os_name", lambda: "linux")
    monkeypatch.setattr(session_status, "resume_target", lambda role, sid: target)
    _, code = nd.run_command("start_clevel cto --resume 1234abcd")
    assert code == 2
    assert not [c for c in rec.calls if c[0] == "tmux_create"]


# start_clevel on Windows (one-shot scheduled task): tests/test_w33_node_dispatch_windows.py


# ---------------------------------------------------------------------------
# deliver_letter
# ---------------------------------------------------------------------------

def _letter(**kw) -> int:
    args = dict(to_session="abcd1234", from_role="cmo", from_session="1234abcd")
    args.update(kw)
    return db_mod.create_letter(args.pop("to_host", "mac"), args.pop("to_role", "cto"),
                                args.pop("body", "hello"), **args)


def _sent(rec) -> list:
    return [c for c in rec.calls if c[0] == "mailbox_send"]


def test_deliver_letter_writes_wakes_and_marks_delivered(rec):
    lid = _letter()
    out, code = nd.run_command(f"deliver_letter {lid}")
    assert code == 0, out
    assert out["result"] == {"letter_id": lid, "delivered": True, "to": "cto-abcd1234"}
    letters = mailbox.peek("cto", "abcd1234")
    assert [(l["body"], l["from"]["role"]) for l in letters] == [("hello", "cmo")]
    assert ("wake", "cto", "abcd1234", "CMO") in rec.calls
    row = db_mod.get_letter(lid)
    assert row["status"] == "delivered" and row["delivered_at"]


def test_deliver_letter_twice_writes_nothing_the_second_time(rec):
    lid = _letter()
    assert nd.run_command(f"deliver_letter {lid}")[1] == 0
    calls_after_first = list(rec.calls)
    delivered_at = db_mod.get_letter(lid)["delivered_at"]

    out, code = nd.run_command(f"deliver_letter {lid}")

    assert code == 0
    assert out["result"] == {"letter_id": lid, "already_delivered": True}
    assert rec.calls == calls_after_first
    assert len(mailbox.peek("cto", "abcd1234")) == 1
    assert db_mod.get_letter(lid)["delivered_at"] == delivered_at


def test_deliver_letter_without_to_session_uses_the_active_session(rec, monkeypatch):
    monkeypatch.setattr(send_to_cxo, "_active_session_id", lambda role: "deadbeef")
    lid = _letter(to_session=None)
    out, code = nd.run_command(f"deliver_letter {lid}")
    assert code == 0 and out["result"]["to"] == "cto-deadbeef"
    assert len(mailbox.peek("cto", "deadbeef")) == 1


def test_deliver_letter_for_another_host_is_refused(rec):
    lid = _letter(to_host="contabo")
    out, code = nd.run_command(f"deliver_letter {lid}")
    assert code == 2 and "contabo" in out["error"]
    assert _sent(rec) == []
    assert db_mod.get_letter(lid)["attempts"] == 0


def test_deliver_letter_unknown_id_is_refused(rec):
    _, code = nd.run_command("deliver_letter 99999")
    assert code == 2 and _sent(rec) == []


def test_deliver_letter_dead_session_fails_and_records_the_attempt(rec):
    rec.session_live = False
    lid = _letter()
    out, code = nd.run_command(f"deliver_letter {lid}")
    assert code == 1 and "no live session" in out["error"]
    row = db_mod.get_letter(lid)
    assert row["status"] == "pending" and row["attempts"] == 1
    assert "no live session" in row["last_error"]
    assert _sent(rec) == []


def test_deliver_letter_flips_to_failed_after_five_attempts(rec):
    rec.session_live = False
    lid = _letter()
    for _ in range(5):
        assert nd.run_command(f"deliver_letter {lid}")[1] == 1
    assert db_mod.get_letter(lid)["status"] == "failed"


@pytest.mark.parametrize("kw", [
    {"to_session": "../../etc"},
    {"to_session": "a/b"},
    {"from_role": "../x"},
    {"from_session": "a b"},
    {"to_role": "ceo"},
    {"to_role": "../cto"},
])
def test_deliver_letter_refuses_unsafe_row_values(rec, tmp_path, kw):
    lid = _letter(**kw)
    _, code = nd.run_command(f"deliver_letter {lid}")
    assert code == 1
    assert _sent(rec) == []
    assert not (tmp_path / "inbox").exists()
    assert db_mod.get_letter(lid)["attempts"] == 1


def test_deliver_letter_mailbox_exception_is_a_failure(rec, monkeypatch):
    def boom(*a, **kw):
        raise OSError("disk full")

    monkeypatch.setattr(mailbox, "send", boom)
    lid = _letter()
    out, code = nd.run_command(f"deliver_letter {lid}")
    assert code == 1 and "disk full" in out["error"]
    assert db_mod.get_letter(lid)["status"] == "pending"


def test_deliver_letter_wake_failure_never_fails_delivery(rec):
    rec.wake_raises = True
    lid = _letter()
    assert nd.run_command(f"deliver_letter {lid}")[1] == 0
    assert db_mod.get_letter(lid)["status"] == "delivered"


# ---------------------------------------------------------------------------
# publish_branch
# ---------------------------------------------------------------------------

def _review_task(tmp_path, **over) -> tuple[str, Path]:
    tid = db_mod.create_task("projA", "developer", "t", "d")
    wt = tmp_path / "worktrees" / f"wt-{tid}"
    wt.mkdir(parents=True)
    cols = dict(host="mac", status="review", branch=f"agent/developer-{tid}",
                worktree=str(wt))
    cols.update(over)
    _update(tid, **cols)
    return tid, wt


def test_publish_branch_pushes_the_branch_from_the_worktree(rec, tmp_path):
    tid, wt = _review_task(tmp_path)
    out, code = nd.run_command(f"publish_branch {tid}")
    assert code == 0, out
    assert out["result"] == {"task_id": tid, "branch": f"agent/developer-{tid}",
                             "pushed": True}
    (_, argv, kw), = rec.calls
    assert argv == ["git", "push", "origin", f"agent/developer-{tid}"]
    assert kw["cwd"] == str(wt.resolve())
    assert kw.get("shell") is not True
    assert not {"--force", "-f", "--force-with-lease", "--delete"} & set(argv)


@pytest.mark.parametrize("over", [
    {"status": "in_progress"},
    {"status": "done"},
    {"host": "winbox"},
    {"host": None},
    {"branch": "main"},
    {"branch": "master"},
    {"branch": "agent/developer-task-00000000"},   # another task's branch
    {"branch": "agent/developer-task-abcd1234; id"},
    {"branch": "agent/../main"},
    {"branch": None},
    {"worktree": None},
    {"worktree": "/tmp"},                           # outside the worktrees root
    {"worktree": "/nonexistent/worktrees/x"},
])
def test_publish_branch_refusals_never_push(rec, tmp_path, over):
    tid, _ = _review_task(tmp_path)
    _update(tid, **over)
    out, code = nd.run_command(f"publish_branch {tid}")
    assert code == 2, out
    assert rec.calls == []


def test_publish_branch_worktree_traversal_is_refused(rec, tmp_path):
    tid, wt = _review_task(tmp_path)
    (tmp_path / "elsewhere").mkdir()
    _update(tid, worktree=str(wt / ".." / ".." / "elsewhere"))
    _, code = nd.run_command(f"publish_branch {tid}")
    assert code == 2 and rec.calls == []


def test_publish_branch_missing_worktree_is_refused(rec, tmp_path):
    tid, _ = _review_task(tmp_path)
    _update(tid, worktree=str(tmp_path / "worktrees" / "gone"))
    _, code = nd.run_command(f"publish_branch {tid}")
    assert code == 2 and rec.calls == []


def test_publish_branch_push_failure_is_a_failure(rec, tmp_path):
    rec.push_rc = 1
    tid, _ = _review_task(tmp_path)
    out, code = nd.run_command(f"publish_branch {tid}")
    assert code == 1 and "remote: boom" in out["error"]


# ---------------------------------------------------------------------------
# events: one row per call, ok and refused
# ---------------------------------------------------------------------------

def test_ok_call_writes_one_event_row(rec, monkeypatch):
    monkeypatch.setenv("SSH_CLIENT", "100.64.1.2 5555 22")
    tid = _mk_task(host="mac", pid=os.getpid())
    nd.run_command(f"pid_alive {tid}")
    (row,) = _dispatch_events()
    assert (row["actor"], row["kind"], row["task_id"]) == (nd.ACTOR, "dispatch", tid)
    assert row["payload"] == {"verb": "pid_alive", "args": [tid],
                              "caller": "100.64.1.2", "ok": True, "error": None}


def test_refused_call_writes_one_event_row(rec):
    nd.run_command("pid_alive $(id)")
    (row,) = _dispatch_events()
    p = row["payload"]
    assert row["kind"] == "dispatch" and row["task_id"] is None
    assert (p["verb"], p["args"], p["ok"]) == ("pid_alive", ["$(id)"], False)
    assert p["caller"] is None and "malformed" in p["error"]


def test_refused_task_call_carries_the_task_id(rec):
    tid = _mk_task(status="pending")
    nd.run_command(f"pid_alive {tid}")            # host is NULL: refused
    (row,) = _dispatch_events()
    assert row["payload"]["ok"] is False and row["task_id"] == tid


def test_forged_ssh_client_is_not_logged_as_an_address(rec, monkeypatch):
    monkeypatch.setenv("SSH_CLIENT", "1.2.3.4; rm -rf / 1 2")
    nd.run_command("probe extra")
    assert _dispatch_events()[0]["payload"]["caller"] is None


def test_audit_failure_does_not_change_the_result(rec, monkeypatch, capsys):
    def boom(*a, **kw):
        raise RuntimeError("hub down")

    tid = _mk_task(host="mac", pid=os.getpid())
    monkeypatch.setattr(db_mod, "log_event", boom)
    out, code = nd.run_command(f"pid_alive {tid}")
    assert code == 0 and out["ok"] is True
    assert "audit write failed" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# CLI wrapper
# ---------------------------------------------------------------------------

def test_cli_reads_ssh_original_command_over_argv(rec, monkeypatch, capsys):
    tid = _mk_task(host="mac", pid=os.getpid())
    monkeypatch.setenv("SSH_ORIGINAL_COMMAND", f"pid_alive {tid}")
    assert nd.main(["probe"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["verb"] == "pid_alive"


def _raises():
    raise RuntimeError("backend crashed")


def test_cli_falls_back_to_argv_and_exit_codes(rec, monkeypatch, capsys):
    tid = _mk_task(host="mac", pid=os.getpid())
    assert nd.main(["pid_alive", tid]) == 0
    assert nd.main(["pid_alive", "task-00000000"]) == 2
    monkeypatch.setattr(nd, "HANDLERS", {**nd.HANDLERS, "probe": _raises})
    assert nd.main(["probe"]) == 1
    outs = [json.loads(l) for l in capsys.readouterr().out.splitlines()]
    assert [o["ok"] for o in outs] == [True, False, False]
    assert outs[2]["error"].startswith("RuntimeError")


def test_cli_no_command_is_a_refusal(rec, capsys):
    assert nd.main([]) == 2
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_cli_output_is_ascii_json(rec, capsys):
    assert nd.main(["рrobe"]) == 2
    out = capsys.readouterr().out
    assert out.isascii() and json.loads(out)["ok"] is False


def test_cli_stdout_is_exactly_one_json_line_in_a_real_process(tmp_path):
    """A verb that prints, and a child that writes to fd 1, must not share
    stdout with the JSON line the ssh caller parses."""
    code = f"""
import os, sys
from pathlib import Path
from lib import db
db.DB_PATH = Path({str(db_mod.DB_PATH)!r})
from tools import node_dispatch as nd
def noisy():
    print("noise from a backend")
    os.write(1, b"noise from a child\\n")
    return {{"quiet": True}}
nd.HANDLERS["probe"] = noisy
sys.exit(nd.main(["probe"]))
"""
    env = {k: v for k, v in os.environ.items() if k != "SSH_ORIGINAL_COMMAND"}
    env["ORG_CHARTER_GATE"] = "off"
    r = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT), env=env,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    lines = r.stdout.splitlines()
    assert len(lines) == 1, r.stdout
    assert json.loads(lines[0]) == {"ok": True, "verb": "probe", "result": {"quiet": True}}
    assert "noise from a backend" in r.stderr and "noise from a child" in r.stderr
