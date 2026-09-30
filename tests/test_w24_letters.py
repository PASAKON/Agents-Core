"""Org Mesh W2.4 (docs/design/org-mesh.md, W2/C4): cross-host letters.

`tools.send_to_cxo.send` turns a message for a C-level session on ANOTHER host
into a `letters` row plus a `deliver_letter` verb; `runners.watchdog._retry_letters`
retries the rows whose host gave no answer. All behind ORG_MESH_DISPATCH (default
off): with the flag off every path is today's, and these tests assert it by making
lib.mesh's dispatch/ssh entry points explode.

Fakes only. mesh.dispatch is a recorder (no ssh ever leaves this process),
subprocess.run explodes, lib.db points at a tmp_path SQLite ledger (ADR 0021), the
mailbox and the lock dir are tmp_path too. self is pinned to "mac"; the remote is
"contabo" (config/hosts.yaml is read as-is).

Run:  .venv/bin/python -m pytest tests/test_w24_letters.py
"""
from __future__ import annotations

import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import config, mailbox, mesh  # noqa: E402
from lib import db as db_mod  # noqa: E402
from lib import notify as notify_mod  # noqa: E402
import runners.watchdog as watchdog  # noqa: E402
from tools import send_to_cxo as sc  # noqa: E402
from tools import send_to_worker as sw  # noqa: E402

SID = "aaaa1111"


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    locks = tmp_path / "locks"
    locks.mkdir()
    monkeypatch.setattr(sc, "LOCKS_DIR", locks)
    monkeypatch.setattr(mailbox, "INBOX_ROOT", tmp_path / "inbox")
    monkeypatch.setenv("ORG_HOST", "mac")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv(mesh.ENV_FLAG, raising=False)
    for var in ("CXO_ROLE", "CXO_SESSION_ID", "CTO_SESSION_ID",
                "WORKER_TASK_ID", "WORKER_ROLE"):
        monkeypatch.delenv(var, raising=False)
    # info()/warn() would run osascript on the Mac: silence the notifier.
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
    return {"ok": True, "verb": verb, "result": {"delivered": True}}


def _refused(host, verb, args):
    return {"ok": False, "verb": verb, "error": "letter 1 not delivered: no live session cmo-aaaa1111 on this host"}


def _install(monkeypatch, script) -> FakeMesh:
    fake = FakeMesh(script)
    monkeypatch.setattr(mesh, "dispatch", fake)
    return fake


def _no_mesh(monkeypatch) -> None:
    """Every way out of this process explodes: the flag-off proof."""
    def boom(*a, **kw):
        raise AssertionError(f"lib.mesh must not be used: {a}")
    monkeypatch.setattr(mesh, "dispatch", boom)
    monkeypatch.setattr(mesh, "build_argv", boom)

    def no_ssh(argv, **kw):
        raise AssertionError(f"subprocess must not run: {argv}")
    monkeypatch.setattr(subprocess, "run", no_ssh)


def _remote_session(role: str = "cmo", sid: str = SID, host: str = "contabo") -> None:
    db_mod.register_cxo_session(role, sid, host=host)


def _local_session(role: str = "cmo", sid: str = "bbbb2222") -> None:
    (sc.LOCKS_DIR / f"{role}-active").write_text(sid)


def _letter(host: str = "contabo", body: str = "hello", **kw) -> int:
    kw.setdefault("to_session", SID)
    return db_mod.create_letter(host, "cmo", body, **kw)


def _letters() -> list[dict]:
    with db_mod.get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM letters ORDER BY id").fetchall()]


# ---------------------------------------------------------------------------
# send_to_cxo, flag on, target on another host
# ---------------------------------------------------------------------------

def test_cross_host_writes_a_row_and_dispatches(monkeypatch, flag_on):
    _remote_session()
    fake = _install(monkeypatch, _ok)
    sc.send("cmo", "budget question")
    [row] = _letters()
    assert (row["to_host"], row["to_role"], row["to_session"]) == ("contabo", "cmo", SID)
    assert row["body"] == "budget question"
    assert (row["from_role"], row["from_session"]) == ("ceo", "ceo")
    assert fake.calls == [("contabo", "deliver_letter", (str(row["id"]),))]


def test_cross_host_writes_nothing_into_this_hosts_mailbox(monkeypatch, flag_on, tmp_path):
    _remote_session()
    _install(monkeypatch, _ok)
    sc.send("cmo", "budget question")
    assert not (tmp_path / "inbox").exists()


def test_delivered_marks_the_letter_and_says_so(monkeypatch, flag_on):
    _remote_session()
    _install(monkeypatch, _ok)
    out = sc.send("cmo", "budget question")
    [row] = _letters()
    assert row["status"] == "delivered" and row["delivered_at"]
    assert row["attempts"] == 0
    assert out.startswith(f"delivered to CMO #{SID} on contabo")
    assert "budget question" in out


def test_unreachable_counts_an_attempt_and_returns_queued_not_an_error(monkeypatch, flag_on):
    _remote_session()
    _install(monkeypatch, _down)
    out = sc.send("cmo", "budget question")
    [row] = _letters()
    assert row["status"] == "pending"
    assert row["attempts"] == 1 and "no route" in row["last_error"]
    assert out.startswith("queued for contabo")
    assert "budget question" in out


def test_a_refusal_counts_an_attempt_and_returns_queued(monkeypatch, flag_on):
    _remote_session()
    _install(monkeypatch, _refused)
    out = sc.send("cmo", "budget question")
    [row] = _letters()
    assert row["status"] == "pending"
    assert row["attempts"] == 1 and "no live session" in row["last_error"]
    assert out.startswith("queued for contabo")


def test_a_failure_the_far_side_already_counted_is_not_counted_twice(monkeypatch, flag_on):
    """Shared ledger: verb_deliver_letter records its own failed attempt before
    it answers ok=False. The sender must not add a second one."""
    _remote_session()

    def far_side_counts(host, verb, args):
        db_mod.record_letter_attempt(int(args[0]), "OSError: disk full")
        return _refused(host, verb, args)

    _install(monkeypatch, far_side_counts)
    sc.send("cmo", "budget question")
    [row] = _letters()
    assert row["attempts"] == 1 and row["last_error"] == "OSError: disk full"


def test_an_unknown_host_in_the_row_is_a_counted_refusal_not_a_crash(monkeypatch, flag_on):
    lid = _letter(host="nowhere")
    assert sc.dispatch_letter(lid) == "refused"
    row = db_mod.get_letter(lid)
    assert row["attempts"] == 1 and "nowhere" in row["last_error"]


def test_the_routing_guard_still_applies_to_a_remote_target(monkeypatch, flag_on):
    """authorize() runs on the resolved remote session, before any row exists."""
    _remote_session(sid=SID)
    fake = _install(monkeypatch, _ok)
    level2 = sc.Identity("cxo", "cfo", "cccc3333")
    monkeypatch.setattr(sc, "current_identity", lambda: level2)
    (sc.LOCKS_DIR / "cfo-cccc3333.spawned_by").write_text("cxo:cto:dddd4444")
    with pytest.raises(PermissionError):
        sc.send("cmo", "not my owner")
    assert _letters() == [] and fake.calls == []


# ---------------------------------------------------------------------------
# send_to_cxo, everything that stays today's path
# ---------------------------------------------------------------------------

def test_same_host_session_uses_todays_mailbox_path(monkeypatch, flag_on, tmp_path):
    _local_session("cmo", "bbbb2222")
    _remote_session()  # a cmo on another host too: the local one wins
    fake = _install(monkeypatch, _ok)
    out = sc.send("cmo", "hello")
    assert out.startswith("queued to CMO #bbbb2222")
    assert [l["body"] for l in mailbox.peek("cmo", "bbbb2222")] == ["hello"]
    assert fake.calls == [] and _letters() == []


def test_flag_off_uses_todays_path_and_never_touches_mesh(monkeypatch):
    _no_mesh(monkeypatch)
    _local_session("cmo", "bbbb2222")
    out = sc.send("cmo", "hello")
    assert out.startswith("queued to CMO #bbbb2222")
    assert [l["body"] for l in mailbox.peek("cmo", "bbbb2222")] == ["hello"]
    assert _letters() == []


def test_flag_off_a_session_only_on_another_host_is_todays_no_session_error(monkeypatch):
    _no_mesh(monkeypatch)
    _remote_session()
    with pytest.raises(ValueError, match="no active CMO session"):
        sc.send("cmo", "hello")
    assert _letters() == []


@pytest.mark.parametrize("setup", ["none", "two_hosts", "closed", "no_host", "self_host"])
def test_flag_on_a_target_the_ledger_cannot_place_is_todays_no_session_error(monkeypatch, flag_on, setup):
    fake = _install(monkeypatch, _ok)
    if setup == "two_hosts":
        _remote_session(sid=SID, host="contabo")
        _remote_session(sid="eeee5555", host="winbox")
    elif setup == "closed":
        _remote_session()
        with db_mod.get_conn() as conn:
            conn.execute("UPDATE c_level_sessions SET status='closed'")
    elif setup == "no_host":
        db_mod.register_cxo_session("cmo", SID)
    elif setup == "self_host":
        _remote_session(host="mac")
    with pytest.raises(ValueError, match="no active CMO session"):
        sc.send("cmo", "hello")
    assert _letters() == [] and fake.calls == []


def test_two_open_sessions_on_the_one_other_host_pick_the_newest(monkeypatch, flag_on):
    _remote_session(sid="old00000")
    with db_mod.get_conn() as conn:
        conn.execute("UPDATE c_level_sessions SET spawned_at='2026-01-01T00:00:00+00:00'")
    _remote_session(sid="new11111")
    _install(monkeypatch, _ok)
    sc.send("cmo", "hello")
    assert _letters()[0]["to_session"] == "new11111"


def test_send_to_worker_is_not_changed_by_the_flag(monkeypatch, flag_on):
    """A DEV on another host still goes through today's _send_remote: node_dispatch's
    deliver_letter only writes to C-level boxes, so a worker letter could not land."""
    fake = _install(monkeypatch, _ok)
    tid = "task-" + uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db_mod.get_conn() as conn:
        conn.execute(
            "INSERT INTO tasks (id, project, role, status, title, description, depends_on, "
            "touches, host, worktree, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (tid, "p", "developer", "in_progress", "t", "d", "[]", "[]", "contabo",
             "/opt/MoonieXHQ/Agents/Core/worktrees/x", ts, ts),
        )
    with pytest.raises(NotImplementedError):
        sw.send(tid, "hello")
    assert fake.calls == [] and _letters() == []


# ---------------------------------------------------------------------------
# dispatch_letter
# ---------------------------------------------------------------------------

def test_a_delivered_letter_is_never_sent_again(monkeypatch, flag_on):
    fake = _install(monkeypatch, _ok)
    lid = _letter()
    assert sc.dispatch_letter(lid) == "delivered"
    assert sc.dispatch_letter(lid) == "skipped"
    assert len(fake.calls) == 1
    assert db_mod.get_letter(lid)["attempts"] == 0


def test_a_failed_or_missing_letter_is_skipped_and_not_counted(monkeypatch, flag_on):
    fake = _install(monkeypatch, _down)
    lid = _letter()
    with db_mod.get_conn() as conn:
        conn.execute("UPDATE letters SET status='failed', attempts=5 WHERE id=?", (lid,))
    assert sc.dispatch_letter(lid) == "skipped"
    assert sc.dispatch_letter(99999) == "skipped"
    assert fake.calls == [] and db_mod.get_letter(lid)["attempts"] == 5


# ---------------------------------------------------------------------------
# watchdog
# ---------------------------------------------------------------------------

def test_watchdog_retries_once_per_pass_two_passes_two_attempts(monkeypatch, flag_on):
    fake = _install(monkeypatch, _down)
    lid = _letter()
    first = watchdog._retry_letters()
    assert first == [{"letter": lid, "host": "contabo", "outcome": "unreachable"}]
    assert db_mod.get_letter(lid)["attempts"] == 1
    watchdog._retry_letters()
    assert db_mod.get_letter(lid)["attempts"] == 2
    assert fake.calls == [("contabo", "deliver_letter", (str(lid),))] * 2


def test_watchdog_delivers_and_then_leaves_the_letter_alone(monkeypatch, flag_on):
    fake = _install(monkeypatch, _ok)
    lid = _letter()
    assert watchdog._retry_letters() == [{"letter": lid, "host": "contabo", "outcome": "delivered"}]
    assert db_mod.get_letter(lid)["status"] == "delivered"
    assert watchdog._retry_letters() == []
    assert len(fake.calls) == 1


def test_watchdog_stops_at_the_attempts_limit(monkeypatch, flag_on):
    fake = _install(monkeypatch, _down)
    lid = _letter()
    for _ in range(4):
        db_mod.record_letter_attempt(lid, "earlier")
    assert db_mod.get_letter(lid)["status"] == "pending"
    watchdog._retry_letters()  # the fifth attempt
    row = db_mod.get_letter(lid)
    assert row["attempts"] == 5 and row["status"] == "failed"
    assert watchdog._retry_letters() == []
    assert len(fake.calls) == 1


def test_a_host_that_does_not_answer_ends_its_turn_and_spares_the_rest(monkeypatch, flag_on):
    """One outage must not spend an attempt of every queued letter in the same pass."""
    fake = _install(monkeypatch, _down)
    first, second = _letter(body="one"), _letter(body="two")
    watchdog._retry_letters()
    assert db_mod.get_letter(first)["attempts"] == 1
    assert db_mod.get_letter(second)["attempts"] == 0
    assert fake.calls == [("contabo", "deliver_letter", (str(first),))]


def test_a_refusal_does_not_end_the_hosts_turn(monkeypatch, flag_on):
    fake = _install(monkeypatch, _refused)
    first, second = _letter(body="one"), _letter(body="two")
    watchdog._retry_letters()
    assert db_mod.get_letter(first)["attempts"] == 1
    assert db_mod.get_letter(second)["attempts"] == 1
    assert len(fake.calls) == 2


def test_watchdog_never_dials_this_host_or_reads_letters_for_it(monkeypatch, flag_on):
    fake = _install(monkeypatch, _ok)
    own = _letter(host="mac")
    assert watchdog._retry_letters() == []
    assert fake.calls == [] and db_mod.get_letter(own)["status"] == "pending"


def test_each_host_gets_its_own_letters(monkeypatch, flag_on):
    fake = _install(monkeypatch, _ok)
    a, b = _letter(host="contabo"), _letter(host="winbox")
    watchdog._retry_letters()
    assert sorted(fake.calls) == sorted([("contabo", "deliver_letter", (str(a),)),
                                         ("winbox", "deliver_letter", (str(b),))])


def test_flag_off_the_retry_pass_does_nothing(monkeypatch):
    _no_mesh(monkeypatch)

    def boom(*a, **kw):
        raise AssertionError("the ledger must not be read with the flag off")
    monkeypatch.setattr(db_mod, "pending_letters", boom)
    lid = _letter()
    assert watchdog._retry_letters() == []
    assert db_mod.get_letter(lid)["attempts"] == 0


def test_scan_once_runs_the_letter_pass_once(monkeypatch, flag_on):
    monkeypatch.setattr(watchdog, "gc_stale_tasks", lambda: [])
    monkeypatch.setattr(watchdog, "sweep_terminal_surfaces", lambda: [])
    monkeypatch.setattr(watchdog, "_drain_disk_queue", lambda: None)
    monkeypatch.setattr(watchdog.work_watch, "watch",
                        lambda: {"alerted": [], "lungnote_filed": [], "green": []})
    fake = _install(monkeypatch, _down)
    lid = _letter()
    watchdog.scan_once()
    watchdog.scan_once()
    assert fake.calls == [("contabo", "deliver_letter", (str(lid),))] * 2
    assert db_mod.get_letter(lid)["attempts"] == 2
