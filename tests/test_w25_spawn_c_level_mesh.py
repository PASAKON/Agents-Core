"""Org Mesh W2.5 (docs/design/org-mesh.md, W2): the secretary relay's `spawn_c_level`
starts a C-level on any host through `mesh.dispatch(host, "start_clevel", ...)`, behind
ORG_MESH_DISPATCH (lib/mesh.enabled(), default off). With the flag off the relay is the
one it was: contabo starts tmux here, mac goes to relay_queue, winbox is refused.

Fakes only. `mesh.dispatch` is a recorder in most tests; a few run the real
`lib.mesh.dispatch` with `subprocess.run` recorded (no ssh leaves this process) and
`tools.node_dispatch.dispatch` standing in for the in-process self path. The relay queue
and the audit trail are redirected to tmp_path / a list. config/hosts.yaml is read as-is:
mac (ssh: null), winbox (ssh: winbox), contabo (ssh: mooniex-vps).

Run:  .venv/bin/python -m pytest tests/test_w25_spawn_c_level_mesh.py
"""
from __future__ import annotations

import inspect
import json
import subprocess
import sys
import threading
from collections import deque
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import config, mesh  # noqa: E402
from runners import mac_agent  # noqa: E402
from runners import relay_mcp_server as rms  # noqa: E402
from tools import node_dispatch as nd  # noqa: E402

SID = "abcdef12"


@pytest.fixture(autouse=True)
def relay(monkeypatch, tmp_path):
    """Relay queue in tmp_path, audit into a list, mac_status stubbed, self = contabo
    (where the secretary runs), both env switches unset."""
    monkeypatch.setattr(rms, "QUEUE_DB_PATH", tmp_path / "relay_queue.db")
    monkeypatch.setattr(rms, "_mac_status_dict", lambda: {
        "state": "online", "reachable": True, "summary_th": "ok-th"})
    audits: list[tuple] = []
    monkeypatch.setattr(rms, "_audit", lambda *a: audits.append(a))
    monkeypatch.setenv("ORG_HOST", "contabo")
    monkeypatch.setenv("HOME", str(tmp_path))  # the org_dispatch key path expands from it
    monkeypatch.delenv(mesh.ENV_FLAG, raising=False)
    monkeypatch.delenv(rms.MESH_PARALLEL_ENV, raising=False)
    monkeypatch.setattr(rms, "_spawn_times", deque())  # the per-caller rate limit (W2.7 F10)
    config.self_host.cache_clear()
    yield audits
    config.self_host.cache_clear()


@pytest.fixture()
def flag_on(monkeypatch):
    monkeypatch.setenv(mesh.ENV_FLAG, "1")


@pytest.fixture()
def parallel_on(monkeypatch):
    monkeypatch.setenv(rms.MESH_PARALLEL_ENV, "1")


# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------

class FakeDispatch:
    """Stands in for mesh.dispatch: records (host, verb, *args), answers `reply`
    (a dict) or raises it (an exception)."""

    def __init__(self, reply=None) -> None:
        self.reply = reply if reply is not None else {
            "ok": True, "verb": "start_clevel",
            "result": {"role": "cto", "via": "tmux", "session_id": SID,
                       "tmux_session": f"cto-{SID}", "resumed_from": None,
                       "prompt_dismissed": True}}
        self.calls: list[tuple] = []

    def __call__(self, host, verb, *args, timeout=None):
        self.calls.append((host, verb, *args))
        if isinstance(self.reply, BaseException):
            raise self.reply
        return self.reply


@pytest.fixture()
def fake_mesh(monkeypatch):
    fake = FakeDispatch()
    monkeypatch.setattr(mesh, "dispatch", fake)
    return fake


class FakeRun:
    """subprocess.run, recorded: what the real lib.mesh.dispatch would have sent over ssh."""

    def __init__(self, stdout: str = "", returncode: int = 0, stderr: str = "") -> None:
        self.stdout, self.returncode, self.stderr = stdout, returncode, stderr
        self.calls: list[list[str]] = []

    def __call__(self, argv, **kw):
        self.calls.append(list(argv))
        return subprocess.CompletedProcess(argv, self.returncode, self.stdout, self.stderr)


def _ssh_reply(**result) -> str:
    return json.dumps({"ok": True, "verb": "start_clevel", "result": result}) + "\n"


def _no_subprocess(monkeypatch) -> None:
    def boom(argv, **kw):
        raise AssertionError(f"nothing may be dialled: {argv}")
    monkeypatch.setattr(subprocess, "run", boom)


def _no_mesh(monkeypatch) -> None:
    def boom(*a, **kw):
        raise AssertionError(f"lib.mesh must not be used: {a}")
    monkeypatch.setattr(mesh, "dispatch", boom)


def _spawn(*args, **kw) -> dict:
    return json.loads(rms.spawn_c_level(*args, **kw))


def _rows() -> list[dict]:
    return rms._queue_list_pending()


# ---------------------------------------------------------------------------
# flag on: a remote host is dispatched, with the exact args
# ---------------------------------------------------------------------------

def test_flag_on_remote_host_dispatches_start_clevel_with_exact_args(flag_on, fake_mesh, relay):
    result = _spawn("cto", "winbox")
    assert fake_mesh.calls == [("winbox", "start_clevel", "cto")]
    assert result["status"] == "spawned"
    assert result["host"] == "winbox" and result["role"] == "cto"
    assert result["transport"] == "mesh"
    assert result["session_id"] == SID and result["tmux_session"] == f"cto-{SID}"
    assert result["result"]["via"] == "tmux"
    assert _rows() == []
    assert ("spawn_c_level", "cto", "spawned",
            f"host=winbox transport=mesh session_id={SID} tmux=cto-{SID}") in relay


def test_flag_on_accepts_every_host_in_the_hosts_config(flag_on, fake_mesh):
    for h in config.hosts():
        assert _spawn("cfo", h)["status"] == "spawned"
    assert [c[0] for c in fake_mesh.calls] == list(config.hosts())
    assert {"mac", "contabo", "winbox"} <= set(config.hosts())
    assert all(c[1:] == ("start_clevel", "cfo") for c in fake_mesh.calls)


def test_flag_on_resume_passes_resume_and_the_sid(flag_on, fake_mesh):
    result = _spawn("cmo", "winbox", resume_session_id=SID)
    assert fake_mesh.calls == [("winbox", "start_clevel", "cmo", "--resume", SID)]
    assert result["status"] == "spawned"


def test_flag_on_remote_really_dials_the_org_dispatch_ssh_command(flag_on, monkeypatch, tmp_path):
    run = FakeRun(stdout=_ssh_reply(role="cto", session_id=SID, tmux_session=f"cto-{SID}"))
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(nd, "dispatch", lambda *a: pytest.fail("a remote host is not in-process"))

    result = _spawn("cto", "winbox")
    assert result["status"] == "spawned" and result["session_id"] == SID
    assert len(run.calls) == 1
    argv = run.calls[0]
    assert argv[0] == "ssh" and argv[1:3] == ["-i", str(tmp_path / ".ssh" / "org_dispatch")]
    assert argv[-2:] == ["winbox", "start_clevel cto"]

    run.calls.clear()
    _spawn("cto", "winbox", resume_session_id=SID)
    assert run.calls[0][-2:] == ["winbox", f"start_clevel cto --resume {SID}"]


def test_flag_on_self_host_runs_in_process_and_dials_nothing(flag_on, monkeypatch):
    _no_subprocess(monkeypatch)
    seen: list[tuple] = []

    def fake_nd(verb, args):
        seen.append((verb, args))
        return {"ok": True, "verb": verb, "result": {
            "role": args[0], "via": "tmux", "session_id": SID, "tmux_session": f"{args[0]}-{SID}"}}

    monkeypatch.setattr(nd, "dispatch", fake_nd)
    result = _spawn("cto", "contabo")  # self is contabo
    assert seen == [("start_clevel", ["cto"])]
    assert result["status"] == "spawned" and result["host"] == "contabo"
    assert _rows() == []


# ---------------------------------------------------------------------------
# flag on: refused before dispatch
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("role", ["ceo", "", "CTO", "cto; rm -rf /", "cto --resume abcdef12", None])
def test_flag_on_bad_role_is_refused_before_dispatch(flag_on, fake_mesh, role):
    result = _spawn(role, "winbox")
    assert result["status"] == "rejected" and "unknown role" in result["reason"]
    assert fake_mesh.calls == [] and _rows() == []


@pytest.mark.parametrize("sid", [
    "abc", "ABCDEF12", "abcdef123", "abcdefg1", "../../etc", "abcdef12; id", "abcdef12\n",
    " abcdef12", "", "12345678901234567890123456789012",
])
def test_flag_on_bad_resume_sid_is_refused_before_dispatch(flag_on, fake_mesh, sid):
    result = _spawn("cto", "winbox", resume_session_id=sid)
    assert result["status"] == "rejected" and "resume_session_id" in result["reason"]
    assert fake_mesh.calls == [] and _rows() == []


def test_flag_on_unknown_host_is_refused_before_dispatch(flag_on, fake_mesh):
    result = _spawn("cto", "moon")
    assert result["status"] == "rejected"
    assert result["reason"] == f"unknown host 'moon'. Known: {', '.join(config.hosts())}"
    assert fake_mesh.calls == [] and _rows() == []


def test_resume_sid_pattern_is_the_one_node_dispatch_enforces():
    assert rms.RESUME_SESSION_ID_RE.pattern == nd.SESSION_ID_RE.pattern


# ---------------------------------------------------------------------------
# flag on: unreachable / refused / undecidable -- a clear answer, never a queue row
# ---------------------------------------------------------------------------

def test_flag_on_unreachable_says_so_and_queues_nothing(flag_on, fake_mesh, relay):
    fake_mesh.reply = mesh.MeshUnreachable("start_clevel on winbox: no reply in 180s")
    result = _spawn("cto", "winbox")
    assert result["status"] == "unreachable"
    assert result["reason"] == "host winbox unreachable"
    assert "no reply in 180s" in result["detail"]
    assert not rms.QUEUE_DB_PATH.exists()  # not even the table was created
    assert _rows() == []
    assert relay[-1][:3] == ("spawn_c_level", "cto", "unreachable")


def test_flag_on_mac_from_a_remote_relay_is_unreachable_not_queued(flag_on, monkeypatch):
    """The Mac has `ssh: null` (it dials out, nobody dials it): the real lib.mesh
    answers unreachable without ever running ssh, and no queue row follows."""
    _no_subprocess(monkeypatch)
    result = _spawn("cfo", "mac")
    assert result["status"] == "unreachable" and result["reason"] == "host mac unreachable"
    assert "no ssh alias" in result["detail"]
    assert _rows() == []


def test_flag_on_ssh_failure_is_unreachable_and_queues_nothing(flag_on, monkeypatch):
    monkeypatch.setattr(subprocess, "run", FakeRun(returncode=255, stderr="Connection refused"))
    result = _spawn("cto", "winbox")
    assert result["status"] == "unreachable" and "Connection refused" in result["detail"]
    assert _rows() == []


def test_flag_on_a_host_that_says_no_is_refused_not_unreachable(flag_on, fake_mesh):
    fake_mesh.reply = {"ok": False, "verb": "start_clevel",
                       "error": f"no resumable UUID for cto-{SID}"}
    result = _spawn("cto", "contabo", resume_session_id=SID)
    assert result["status"] == "refused"
    assert result["detail"] == f"no resumable UUID for cto-{SID}"
    assert _rows() == []


def test_flag_on_cannot_tell_which_host_it_is_reports_an_error(flag_on, monkeypatch):
    monkeypatch.setattr(config, "_SELF_HOST_SOURCES", ())  # the real self_host() finds nothing
    config.self_host.cache_clear()
    result = _spawn("cto", "winbox")
    assert result["status"] == "error" and "cannot resolve self_host" in result["detail"]
    assert _rows() == []


# ---------------------------------------------------------------------------
# flag off: today's relay, mesh never touched
# ---------------------------------------------------------------------------

def test_flag_off_winbox_is_rejected_as_today(monkeypatch, relay):
    _no_mesh(monkeypatch)
    assert _spawn("cto", "winbox") == {
        "status": "rejected", "reason": "unknown host 'winbox'. Known: contabo, mac"}
    assert relay == [("spawn_c_level", "cto", "rejected", "unknown host 'winbox'")]
    assert _rows() == []


def test_flag_off_mac_still_enqueues_exactly_as_today(monkeypatch, relay):
    _no_mesh(monkeypatch)
    _no_subprocess(monkeypatch)
    result = rms.spawn_c_level("cfo", "mac")
    assert result == ('{"status": "queued", "role": "cfo", "host": "mac", "queue_id": 1, '
                      '"mac_reachable": true, "mac_state": "online", "mac_summary_th": "ok-th"}')
    assert relay == [("spawn_c_level", "cfo", "queued", "queue_id=1 mac_state=online")]
    rows = _rows()
    assert len(rows) == 1 and rows[0]["kind"] == "spawn" and rows[0]["target_role"] == "cfo"


def test_flag_off_unknown_role_is_rejected_as_today(monkeypatch, relay):
    _no_mesh(monkeypatch)
    assert _spawn("ceo", "mac") == {
        "status": "rejected", "reason": "unknown role 'ceo'. Known: cto, cmo, cgo, cfo"}
    assert relay == [("spawn_c_level", "ceo", "rejected", "unknown role, host=mac")]


def test_flag_off_contabo_still_starts_tmux_here(monkeypatch, relay):
    _no_mesh(monkeypatch)
    created, sent = {}, []
    monkeypatch.setattr(rms.tmux_session, "create",
                        lambda session, cwd, cmd: created.update(session=session, cmd=cmd))
    monkeypatch.setattr(rms, "SPAWN_PROMPT_DELAY_S", 0)
    monkeypatch.setattr(rms.subprocess, "run", lambda argv, *a, **k: sent.append(list(argv)))

    result = _spawn("cmo", "contabo")
    assert result["status"] == "spawned" and result["host"] == "contabo"
    assert set(result) == {"status", "role", "host", "tmux_session", "session_id"}
    assert created["session"] == result["tmux_session"]
    assert "cxo-claude.sh" in created["cmd"] and "--role cmo" in created["cmd"]
    assert sent[-1] == ["tmux", "send-keys", "-t", result["tmux_session"], "Escape"]
    assert _rows() == []


def test_flag_off_resume_is_rejected_never_silently_dropped(monkeypatch, relay):
    """A fresh session answering a resume request is the `claude -r <short id>` trap."""
    _no_mesh(monkeypatch)
    result = _spawn("cto", "mac", resume_session_id=SID)
    assert result["status"] == "rejected" and "ORG_MESH_DISPATCH" in result["reason"]
    assert _rows() == []


def test_flag_off_ignores_the_parallel_switch(monkeypatch, parallel_on):
    _no_mesh(monkeypatch)
    assert _spawn("cfo", "mac")["status"] == "queued"
    assert "mesh" not in _spawn("cfo", "mac")
    assert len(_rows()) == 2  # one row per call, never two


@pytest.mark.parametrize("value", ["0", "off", "false", "", "no"])
def test_flag_values_that_are_not_on_leave_the_relay_as_it_was(monkeypatch, value):
    monkeypatch.setenv(mesh.ENV_FLAG, value)
    _no_mesh(monkeypatch)
    assert _spawn("cto", "winbox")["status"] == "rejected"
    assert _spawn("cfo", "mac")["status"] == "queued"


# ---------------------------------------------------------------------------
# the parallel run: ORG_MESH_PARALLEL_MAC_AGENT=1 keeps the mac_agent queue leg
# ---------------------------------------------------------------------------

def test_parallel_mac_enqueues_beside_the_mesh_call(flag_on, parallel_on, fake_mesh, relay):
    fake_mesh.reply = {"ok": True, "verb": "start_clevel",
                       "result": {"role": "cfo", "via": "spawn-cxo.sh", "session_id": SID,
                                  "resumed_from": None}}
    result = _spawn("cfo", "mac")
    assert fake_mesh.calls == [("mac", "start_clevel", "cfo")]
    rows = _rows()
    assert len(rows) == 1 and rows[0]["kind"] == "spawn" and rows[0]["target_role"] == "cfo"
    assert rows[0]["payload"] == {}
    # today's queued answer, with the mesh outcome attached
    assert result["status"] == "queued" and result["queue_id"] == rows[0]["id"]
    assert result["host"] == "mac" and result["mac_state"] == "online"
    assert result["mesh"]["status"] == "spawned" and result["mesh"]["session_id"] == SID
    # both results are in the audit, keyed by the queue id
    assert ("spawn_c_level", "cfo", "parallel_mac_agent",
            f"queue_id={rows[0]['id']} mesh_status=spawned mesh_session_id={SID}") in relay


def test_parallel_mac_still_queues_when_the_mesh_leg_is_unreachable(flag_on, parallel_on,
                                                                    monkeypatch, relay):
    """From Contabo the Mac has no ssh alias, so this is the normal parallel-run answer
    until it gets one: the queue keeps the spawn working, the audit records the gap."""
    _no_subprocess(monkeypatch)
    result = _spawn("cfo", "mac")
    assert result["status"] == "queued"
    assert result["mesh"]["status"] == "unreachable"
    assert result["mesh"]["reason"] == "host mac unreachable"
    assert len(_rows()) == 1
    assert relay[-1] == ("spawn_c_level", "cfo", "parallel_mac_agent",
                         "queue_id=1 mesh_status=unreachable mesh_session_id=None")


def test_parallel_mac_queues_even_when_the_mesh_host_refuses(flag_on, parallel_on, fake_mesh):
    fake_mesh.reply = {"ok": False, "verb": "start_clevel", "error": "missing spawn-cxo.sh"}
    result = _spawn("cfo", "mac")
    assert result["status"] == "queued" and result["mesh"]["status"] == "refused"
    assert len(_rows()) == 1


@pytest.mark.parametrize("value", ["1", "true", "on", "ON", " 1 "])
def test_parallel_switch_accepts_the_same_values_as_the_mesh_flag(flag_on, fake_mesh,
                                                                  monkeypatch, value):
    monkeypatch.setenv(rms.MESH_PARALLEL_ENV, value)
    _spawn("cto", "mac")
    assert len(_rows()) == 1


@pytest.mark.parametrize("value", ["0", "off", "false", "", "no"])
def test_parallel_switch_off_values_queue_nothing(flag_on, fake_mesh, monkeypatch, value):
    monkeypatch.setenv(rms.MESH_PARALLEL_ENV, value)
    assert _spawn("cto", "mac")["status"] == "spawned"
    assert _rows() == []


def test_without_the_parallel_switch_mac_is_mesh_only(flag_on, fake_mesh):
    result = _spawn("cto", "mac")
    assert result["status"] == "spawned" and "queue_id" not in result
    assert _rows() == []


@pytest.mark.parametrize("host", ["winbox", "contabo"])
def test_parallel_switch_is_for_the_mac_only(flag_on, parallel_on, fake_mesh, host):
    assert _spawn("cto", host)["status"] == "spawned"
    assert _rows() == []


def test_parallel_mac_resume_gets_no_queue_leg(flag_on, parallel_on, fake_mesh, relay):
    """mac_agent's spawn cannot resume: enqueueing would start a fresh session."""
    result = _spawn("cto", "mac", resume_session_id=SID)
    assert fake_mesh.calls == [("mac", "start_clevel", "cto", "--resume", SID)]
    assert result["status"] == "spawned"
    assert result["queue_leg"] == "skipped: mac_agent cannot resume"
    assert _rows() == []
    assert relay[-1][2] == "parallel_mac_agent" and "queue_id=none" in relay[-1][3]


# ---------------------------------------------------------------------------
# the tool surface and the Mac agent
# ---------------------------------------------------------------------------

def test_spawn_c_level_signature_adds_one_optional_argument_and_no_free_form_one():
    params = inspect.signature(rms.spawn_c_level).parameters
    assert list(params) == ["role", "host", "resume_session_id"]
    assert params["resume_session_id"].default is None


def test_mac_agent_is_still_there_with_its_retirement_note():
    assert callable(mac_agent.do_spawn) and callable(mac_agent.fetch_pending)
    assert "RETIREMENT" in mac_agent.__doc__ and "24 h" in mac_agent.__doc__


# ---------------------------------------------------------------------------
# W2.7 F10: at most 3 spawn attempts per caller session per 10 minutes
# ---------------------------------------------------------------------------

def test_the_fourth_spawn_in_ten_minutes_is_rate_limited_and_dials_nothing(flag_on, fake_mesh, relay):
    for _ in range(3):
        assert _spawn("cto", "winbox")["status"] == "spawned"
    result = _spawn("cto", "winbox")
    assert result["status"] == "rate_limited"
    assert 0 < result["retry_after_s"] <= rms.SPAWN_RATE_WINDOW_S + 1
    assert len(fake_mesh.calls) == 3
    assert relay[-1][:3] == ("spawn_c_level", "cto", "rate_limited")


def test_flag_off_the_limit_holds_for_the_queue_and_tmux_paths_too(monkeypatch, relay):
    monkeypatch.setattr(rms.tmux_session, "create", lambda *a, **kw: None)
    monkeypatch.setattr(rms, "SPAWN_PROMPT_DELAY_S", 0)
    monkeypatch.setattr(rms.subprocess, "run", lambda *a, **kw: None)
    assert _spawn("cfo", "mac")["status"] == "queued"
    assert _spawn("cfo", "mac")["status"] == "queued"
    assert _spawn("cmo", "contabo")["status"] == "spawned"
    assert _spawn("cmo", "contabo")["status"] == "rate_limited"
    assert _spawn("cfo", "mac")["status"] == "rate_limited"
    assert len(_rows()) == 2


def test_a_call_rejected_before_any_spawn_takes_no_slot(flag_on, fake_mesh):
    for _ in range(5):
        assert _spawn("ceo", "winbox")["status"] == "rejected"
        assert _spawn("cto", "moon")["status"] == "rejected"
        assert _spawn("cto", "winbox", resume_session_id="XYZ")["status"] == "rejected"
    assert [_spawn("cto", "winbox")["status"] for _ in range(4)] == \
        ["spawned", "spawned", "spawned", "rate_limited"]


def test_a_slot_frees_when_the_window_has_passed(flag_on, fake_mesh, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(rms.time, "monotonic", lambda: clock[0])
    for _ in range(3):
        _spawn("cto", "winbox")
    clock[0] += rms.SPAWN_RATE_WINDOW_S - 1
    assert _spawn("cto", "winbox")["status"] == "rate_limited"
    clock[0] += 1
    assert _spawn("cto", "winbox")["status"] == "spawned"
    assert len(fake_mesh.calls) == 4


def test_concurrent_calls_get_exactly_three_slots(flag_on, fake_mesh):
    results: list[str] = []
    gate = threading.Barrier(12)

    def one():
        gate.wait()
        results.append(_spawn("cto", "winbox")["status"])

    threads = [threading.Thread(target=one) for _ in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert sorted(results) == ["rate_limited"] * 9 + ["spawned"] * 3
    assert len(fake_mesh.calls) == 3
