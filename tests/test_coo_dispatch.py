"""Dispatcher tests for C-level respawn (CEO pick #18, 2026-10-26).

Covers all four refusal gates (a)-(d), fail-closed behavior when unsure, resume vs fresh
launch paths, detached tmux session naming (`<role>-<id8>`), and `coo_respawn_done` audit events.
No network, no real hub, no real tmux.
"""
from __future__ import annotations

import fcntl
import json
import os
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from lib import db as db_mod
from runners import coo_dispatch, coo_gate

SID = "cootest1"
SAMPLE_UUID = "d405e3e2-1111-2222-3333-a6f2f69c4825"


@pytest.mark.parametrize("rows,reason", [
    ([], "live_host_missing"),
    ([{"published_at": "2026-10-26T03:56:59Z", "error": ""}], "live_host_stale"),
    ([{"published_at": "2026-10-26T04:00:00Z", "error": "failed"}], "live_host_error"),
    ([{"published_at": "invalid", "error": None}], "live_host_stale"),
])
def test_host_health_refuses_empty_snapshot(monkeypatch, rows, reason):
    monkeypatch.setattr(coo_dispatch, "live_host_refusal", REAL_HOST_CHECK)
    original = coo_dispatch._rows
    monkeypatch.setattr(coo_dispatch, "_rows",
                        lambda sql, args=(): rows if "FROM live_hosts" in sql else original(sql, args))
    monkeypatch.setattr(coo_dispatch, "start_clevel", lambda *a, **k: pytest.fail("must refuse"))
    _queue_respawn()
    coo_dispatch.respawn_once(now="2026-10-26T04:00:00Z")
    assert _done_events()[-1]["reason"] == reason


def test_host_health_fresh_and_unreadable(monkeypatch):
    monkeypatch.setattr(coo_dispatch, "_rows", lambda *a: [
        {"published_at": "2026-10-26T03:59:00Z", "error": None}])
    assert REAL_HOST_CHECK("contabo", now="2026-10-26T04:00:00Z") is None
    def boom(*a, **kw):
        raise OSError("password=FAKE")
    monkeypatch.setattr(coo_dispatch, "live_host_refusal", boom)
    monkeypatch.setattr(coo_dispatch, "_done_respawn_request_ids", lambda: set())
    result = coo_dispatch._reserved_respawn(999, "cto", "contabo")
    assert result["reason"] == "respawn_error:OSError"
    assert "FAKE" not in json.dumps(result)


def test_proc_match_and_unreadable(monkeypatch, tmp_path):
    proc = tmp_path / "proc"
    pid = proc / "123"
    pid.mkdir(parents=True)
    (pid / "comm").write_bytes(b"bash\n")
    (pid / "cmdline").write_bytes(b"bash\0/opt/x/scripts/cxo-claude.sh\0--role\0cto\0")
    # The shared tmux server's argv names its first command; it never counts as a launcher.
    tmux = proc / "77"
    tmux.mkdir()
    (tmux / "comm").write_bytes(b"tmux: server\n")
    (tmux / "cmdline").write_bytes(b"tmux\0new-session\0bash scripts/cxo-claude.sh --role cmo\0")
    # A PH launched for the cto lane is not a cto C-level; an arg merely mentioning the script is not either.
    ph = proc / "88"
    ph.mkdir()
    (ph / "comm").write_bytes(b"bash\n")
    (ph / "cmdline").write_bytes(b"bash\0scripts/cxo-claude.sh\0--role\0project_head\0--lane\0cto\0")
    other = proc / "99"
    other.mkdir()
    (other / "comm").write_bytes(b"grep\n")
    (other / "cmdline").write_bytes(b"grep\0cxo-claude.sh --role cgo\0")
    assert REAL_PROC_CHECK("cto", proc) == "process_role_alive"
    assert REAL_PROC_CHECK("cmo", proc) is None
    assert REAL_PROC_CHECK("cgo", proc) is None
    assert not list(proc.glob("*/environ"))
    monkeypatch.setattr(coo_dispatch, "process_role_refusal", lambda role: REAL_PROC_CHECK(role, proc))
    _queue_respawn()
    coo_dispatch.respawn_once()
    assert _done_events()[-1]["reason"] == "process_role_alive"
    def unreadable(self):
        raise PermissionError("password=FAKE")
    monkeypatch.setattr(Path, "read_bytes", unreadable)
    assert REAL_PROC_CHECK("cto", proc) == "proc_read_error:PermissionError"
    monkeypatch.setattr(coo_dispatch, "_done_respawn_request_ids", lambda: set())
    result = coo_dispatch._reserved_respawn(999, "cto", "contabo")
    assert result["reason"] == "proc_read_error:PermissionError"
    assert REAL_PROC_CHECK("cto", tmp_path / "missing") == "proc_read_error:FileNotFoundError"


def test_reservation_held_and_through_done(monkeypatch):
    path = coo_dispatch.LOCKS_DIR / "coo-respawn-cto.lock"
    _queue_respawn()
    with path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        coo_dispatch.respawn_once()
    assert _done_events()[-1]["reason"].startswith("reservation_busy:")
    monkeypatch.setattr(coo_dispatch, "_done_respawn_request_ids", lambda: set())
    monkeypatch.setattr(coo_dispatch, "latest_session_id", lambda *a: None)
    monkeypatch.setattr(coo_dispatch, "start_clevel", lambda *a, **kw: (True, "ok"))
    original = coo_dispatch._event
    def checked_event(*args):
        with path.open("a") as other:
            with pytest.raises(BlockingIOError):
                fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return original(*args)
    monkeypatch.setattr(coo_dispatch, "_event", checked_event)
    coo_dispatch._reserved_respawn(999, "cto", "contabo")


@pytest.mark.parametrize("secret", ["host=db user=x password=FAKE dbname=y",
                                  "postgresql://x:FAKE@db/y"])
def test_dispatch_exception_does_not_leak(monkeypatch, secret):
    def fail(*a):
        raise RuntimeError(secret)
    monkeypatch.setattr(coo_dispatch, "live_hub_rows", fail)
    _queue_respawn()
    coo_dispatch.respawn_once()
    result = _done_events()[-1]
    assert result["reason"] == "live_sessions_read_error:RuntimeError"
    assert "FAKE" not in json.dumps(result) and "password" not in json.dumps(result)


def test_delayed_request_counts_actual_start(monkeypatch):
    from lib import coo_policy
    with db_mod.get_conn() as conn:
        db_mod.log_event(conn, None, "coo_dispatch", "coo_respawn_done",
                        {"role": "cto", "request_id": 900, "started": True})
    now = coo_policy.datetime.now(coo_policy.timezone.utc)
    with db_mod.get_conn() as conn:
        conn.execute("INSERT INTO events (actor, kind, payload, ts) VALUES (?, ?, ?, ?)",
                     ("coo_gate", "coo_respawn_request",
                      json.dumps({"role": "cto", "host": "contabo", "by_session": SID}),
                      "2020-01-01T00:00:00Z"))
    monkeypatch.setattr(coo_dispatch, "start_clevel", lambda *a, **kw: pytest.fail("must refuse"))
    coo_dispatch.respawn_once(now=now)
    assert "10 minutes" in _done_events()[-1]["reason"]
REAL_HOST_CHECK = coo_dispatch.live_host_refusal
REAL_PROC_CHECK = coo_dispatch.process_role_refusal


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch, tmp_path):
    monkeypatch.delenv("ORG_DB_URL", raising=False)
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    with db_mod.get_conn() as conn:
        conn.execute("CREATE VIEW coo_respawn_events AS SELECT id, kind, payload, ts "
                     "FROM events WHERE kind IN ('coo_respawn_request', 'coo_respawn_done')")
    with db_mod.get_conn() as conn:
        conn.execute("CREATE TABLE live_sessions (host TEXT, uuid TEXT, sid TEXT, role TEXT, "
                     "name TEXT, address TEXT, status TEXT, pid INTEGER, seen_at TEXT, verified INTEGER)")
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setenv("ORG_HOST", "contabo")
    db_mod.register_cxo_session("coo", SID, "contabo")
    locks_dir = tmp_path / "locks"
    locks_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(coo_dispatch, "LOCKS_DIR", locks_dir)
    monkeypatch.setattr(coo_dispatch, "tmux_sessions", lambda: ["sompong"])
    monkeypatch.setattr(coo_dispatch, "live_host_refusal", lambda host, **kw: None)
    monkeypatch.setattr(coo_dispatch, "process_role_refusal", lambda role: None)


def _queue_respawn(role: str = "cto", host: str = "contabo") -> int:
    out = coo_gate.handle(
        {"op": "respawn_clevel", "session_id": SID, "role": role, "host": host},
        994,
    )
    assert out["ok"] is True, out
    return int(out["request_id"])


def _done_events() -> list[dict]:
    with db_mod.get_conn() as conn:
        rows = conn.execute(
            "SELECT id, payload, ts FROM events WHERE kind='coo_respawn_done' ORDER BY id ASC"
        ).fetchall()
    return [json.loads(r["payload"]) if isinstance(r["payload"], str) else r["payload"] for r in rows]


def _insert_live_row(
    *,
    host: str = "contabo",
    uuid: str = "u-1",
    sid: str = "",
    role: str = "",
    name: str = "",
    address: str = "",
    verified: int = 1,
) -> None:
    with db_mod.get_conn() as conn:
        conn.execute(
            "INSERT INTO live_sessions (host, uuid, sid, role, name, address, status, pid, seen_at, verified) "
            "VALUES (?, ?, ?, ?, ?, ?, 'alive', 1234, '2026-10-26T08:00:00Z', ?)",
            (host, uuid, sid, role, name, address, verified),
        )


# --------------------------------------------------------------------------- (a) live hub rows

@pytest.mark.parametrize("row_kwargs", [
    {"role": "cto", "name": "🟢 CTO (Somchai)", "verified": 1},
    {"role": "cto", "name": "🟢 CTO (Somchai)", "verified": 0},   # name-only (unverified) still blocks
    {"role": "", "name": "CTO (Somchai) - reviewing PR", "verified": 0},
    {"role": "", "name": "🟢 CTO (Somchai)", "verified": 0},
    {"role": "", "name": "CONTABO CTO (Somchai) #a1b2c3d4", "verified": 0},
    {"role": "", "name": "unknown", "address": "cto-a1b2c3d4", "verified": 0},
    {"role": "", "name": "unknown", "sid": "cto-a1b2c3d4", "verified": 0},
])
def test_dispatch_refuses_when_live_hub_row_claims_role(monkeypatch, row_kwargs):
    _insert_live_row(**row_kwargs)
    monkeypatch.setattr(
        coo_dispatch, "start_clevel",
        lambda *a, **kw: pytest.fail("start_clevel must not run when a live row claims the role"),
    )
    req_id = _queue_respawn("cto")
    coo_dispatch.respawn_once()
    done = _done_events()
    assert len(done) == 1
    assert done[0]["request_id"] == req_id
    assert done[0]["ok"] is False
    assert done[0]["mode"] is None and done[0]["sid"] is None
    assert "live hub row" in done[0]["reason"]


def test_dispatch_refuses_when_live_sessions_read_fails(monkeypatch):
    def boom(*_a, **_kw):
        raise RuntimeError("hub connection lost")

    monkeypatch.setattr(coo_dispatch, "live_hub_rows", boom)
    req_id = _queue_respawn("cto")
    coo_dispatch.respawn_once()
    done = _done_events()
    assert len(done) == 1
    assert done[0]["request_id"] == req_id
    assert done[0]["ok"] is False
    assert done[0]["reason"] == "live_sessions_read_error:RuntimeError"


def test_dispatch_ignores_live_rows_for_other_roles_ph_or_other_hosts(monkeypatch):
    _insert_live_row(host="contabo", uuid="u-cmo", role="cmo", name="🟢 CMO (Ploy)", verified=1)
    _insert_live_row(host="contabo", uuid="u-ph", role="project_head", name="🟢 PH#abc (CTO) - Core", verified=1)
    _insert_live_row(host="mac", uuid="u-mac", role="cto", name="🍎 CTO (Somchai)", verified=1)

    started = []
    monkeypatch.setattr(coo_dispatch, "resolve_resume_uuid", lambda role, sid: None)
    monkeypatch.setattr(
        coo_dispatch, "start_clevel",
        lambda role, *, mode, sid, resume_uuid=None: started.append((role, mode, sid, resume_uuid)) or (True, "ok"),
    )
    _queue_respawn("cto")
    coo_dispatch.respawn_once()
    assert len(started) == 1 and started[0][0] == "cto"


# --------------------------------------------------------------------------- (b) single-role flock

def test_dispatch_refuses_when_single_role_flock_is_held(monkeypatch):
    flock_file = coo_dispatch.LOCKS_DIR / ".single-cto.flock"
    fd = os.open(str(flock_file), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        monkeypatch.setattr(
            coo_dispatch, "start_clevel",
            lambda *a, **kw: pytest.fail("start_clevel must not run while .single-cto.flock is held"),
        )
        req_id = _queue_respawn("cto")
        coo_dispatch.respawn_once()
        done = _done_events()
        assert len(done) == 1
        assert done[0]["request_id"] == req_id
        assert done[0]["ok"] is False
        assert ".single-cto.flock" in done[0]["reason"]
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)

    # Once released, single_role_flock_held returns False and leaves the flock unlocked.
    assert coo_dispatch.single_role_flock_held("cto") is False
    assert coo_dispatch.single_role_flock_held("cto") is False


# --------------------------------------------------------------------------- (c) tmux session check

@pytest.mark.parametrize("tmux_list,expected_substr", [
    (["sompong", "cto-12345678"], "cto-12345678"),
    (["sompong", "cto-fresh"], "cto-fresh"),
    (None, "unsure"),
])
def test_dispatch_refuses_when_tmux_has_role_session_or_server_down(monkeypatch, tmux_list, expected_substr):
    monkeypatch.setattr(coo_dispatch, "tmux_sessions", lambda: tmux_list)
    monkeypatch.setattr(
        coo_dispatch, "start_clevel",
        lambda *a, **kw: pytest.fail("start_clevel must not run when tmux check fails"),
    )
    req_id = _queue_respawn("cto")
    coo_dispatch.respawn_once()
    done = _done_events()
    assert len(done) == 1
    assert done[0]["request_id"] == req_id
    assert done[0]["ok"] is False
    assert expected_substr in done[0]["reason"]


# --------------------------------------------------------------------------- (d) dispatcher rate limits

def test_dispatch_enforces_rate_limits_independently_of_gate(monkeypatch):
    now = "2026-10-26T04:00:00+00:00"
    with db_mod.get_conn() as conn:
        # Prior request 2 minutes ago, plus a second request that bypassed the gate.
        conn.execute(
            "INSERT INTO events (task_id, actor, kind, payload, ts) VALUES (NULL, 'coo_gate', 'coo_respawn_request', ?, ?)",
            (json.dumps({"role": "cto", "host": "contabo", "by_session": SID}), "2026-10-26T03:58:00+00:00"),
        )
        first_id = conn.execute("SELECT MAX(id) AS id FROM events").fetchone()["id"]
        db_mod.log_event(
            conn, None, "coo_dispatch", "coo_respawn_done",
            {"request_id": first_id, "role": "cto", "host": "contabo", "ok": True, "mode": "fresh",
             "sid": "11112222", "uuid": None, "reason": "ok"},
        )
        conn.execute(
            "INSERT INTO events (task_id, actor, kind, payload, ts) VALUES (NULL, 'coo_gate', 'coo_respawn_request', ?, ?)",
            (json.dumps({"role": "cto", "host": "contabo", "by_session": SID}), "2026-10-26T04:00:00+00:00"),
        )
        second_id = conn.execute("SELECT MAX(id) AS id FROM events").fetchone()["id"]

    coo_dispatch.respawn_once(now=now)
    done = [d for d in _done_events() if d.get("request_id") == second_id]
    assert len(done) == 1
    assert done[0]["ok"] is False and "10 min" in done[0]["reason"]


def test_dispatch_enforces_three_per_thai_day_limit(monkeypatch):
    now = "2026-10-26T05:00:00+00:00"
    with db_mod.get_conn() as conn:
        for ts in ("2026-10-26T01:00:00+00:00", "2026-10-26T02:00:00+00:00", "2026-10-26T03:00:00+00:00"):
            conn.execute(
                "INSERT INTO events (task_id, actor, kind, payload, ts) VALUES (NULL, 'coo_gate', 'coo_respawn_request', ?, ?)",
                (json.dumps({"role": "cfo", "host": "contabo", "by_session": SID}), ts),
            )
            rid = conn.execute("SELECT MAX(id) AS id FROM events").fetchone()["id"]
            db_mod.log_event(
                conn, None, "coo_dispatch", "coo_respawn_done",
                {"request_id": rid, "role": "cfo", "host": "contabo", "ok": True, "mode": "fresh",
                 "sid": "aaaaaaaa", "uuid": None, "reason": "ok"},
            )
        conn.execute(
            "INSERT INTO events (task_id, actor, kind, payload, ts) VALUES (NULL, 'coo_gate', 'coo_respawn_request', ?, ?)",
            (json.dumps({"role": "cfo", "host": "contabo", "by_session": SID}), "2026-10-26T05:00:00+00:00"),
        )
        fourth_id = conn.execute("SELECT MAX(id) AS id FROM events").fetchone()["id"]

    coo_dispatch.respawn_once(now=now)
    done = [d for d in _done_events() if d.get("request_id") == fourth_id]
    assert len(done) == 1
    assert done[0]["ok"] is False and "Thai day" in done[0]["reason"]


# --------------------------------------------------------------------------- resume vs fresh paths

def test_dispatch_resumes_most_recent_session_in_detached_tmux(monkeypatch):
    db_mod.register_cxo_session("cto", "old11111", "contabo")
    with db_mod.get_conn() as conn:
        conn.execute("UPDATE c_level_sessions SET spawned_at='2026-10-25T10:00:00+00:00' WHERE session_id='old11111'")
    db_mod.register_cxo_session("cto", "f69c4825", "contabo")
    with db_mod.get_conn() as conn:
        conn.execute(
            "UPDATE c_level_sessions SET spawned_at='2026-10-26T08:00:00+00:00', resume_uuid=? WHERE session_id='f69c4825'",
            (SAMPLE_UUID,),
        )

    resolved_calls = []

    def fake_resolve(role: str, session_id: str) -> str | None:
        resolved_calls.append((role, session_id))
        return SAMPLE_UUID

    tmux_calls = []

    def fake_run(argv, **kwargs):
        tmux_calls.append(argv)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(coo_dispatch, "resolve_resume_uuid", fake_resolve)
    monkeypatch.setattr(coo_dispatch.subprocess, "run", fake_run)

    req_id = _queue_respawn("cto")
    coo_dispatch.respawn_once()

    assert resolved_calls == [("cto", "f69c4825")]
    assert len(tmux_calls) == 1
    argv = tmux_calls[0]
    assert argv[:5] == [coo_dispatch.TMUX, "new-session", "-d", "-s", "cto-f69c4825"]
    assert f"scripts/cxo-claude.sh --role cto -r {SAMPLE_UUID}" in argv[-1]

    done = _done_events()
    assert len(done) == 1
    assert done[0] == {
        "request_id": req_id,
        "role": "cto",
        "host": "contabo",
        "ok": True,
        "mode": "resume",
        "started": True,
        "sid": "f69c4825",
        "uuid": SAMPLE_UUID,
        "reason": "resume session started in tmux cto-f69c4825",
    }

    # Second tick does not re-run an already-processed request.
    coo_dispatch.respawn_once()
    assert len(tmux_calls) == 1


def test_dispatch_starts_fresh_session_when_no_resume_uuid_resolves(monkeypatch):
    monkeypatch.setattr(coo_dispatch, "resolve_resume_uuid", lambda role, sid: None)
    tmux_calls = []

    def fake_run(argv, **kwargs):
        tmux_calls.append(argv)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(coo_dispatch.subprocess, "run", fake_run)

    req_id = _queue_respawn("cgo")
    coo_dispatch.respawn_once()

    assert len(tmux_calls) == 1
    argv = tmux_calls[0]
    done = _done_events()
    assert len(done) == 1
    sid = done[0]["sid"]
    assert re.fullmatch(r"[0-9a-f]{8}", sid)
    assert argv[:5] == [coo_dispatch.TMUX, "new-session", "-d", "-s", f"cgo-{sid}"]
    assert argv[-1].endswith("scripts/cxo-claude.sh --role cgo")
    assert " -r " not in argv[-1]
    assert done[0]["request_id"] == req_id
    assert done[0]["ok"] is True
    assert done[0]["mode"] == "fresh"
    assert done[0]["uuid"] is None
