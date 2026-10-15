"""Org restructure P3-C: the heartbeat hook, its fold, and the publisher's call to it.

ADR 0021: tmp_path only, never state/ of this checkout and never a real hub. The hook
runs as a subprocess with ORG_ROOT pointed at tmp_path. The fold runs its real SQL
against an in-memory SQLite (the statements are written to run unchanged on Postgres
and SQLite); the last test runs it against the real P3-A tables and self-skips unless
ORG_TEST_DB_URL is set, like tests/test_portfolio_schema.py.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import heartbeat_fold as hf  # noqa: E402
from tools import live_sessions as ls  # noqa: E402

HOOK = ROOT / "scripts" / "hook-heartbeat.py"
PH = "7cf528f0"
T0 = datetime(2026, 10, 15, 1, 0, 0, tzinfo=timezone.utc)
NOW = T0 + timedelta(hours=1)


# ---------------------------------------------------------------------------
# the hook
# ---------------------------------------------------------------------------

def _hook(root, stdin=b"{}", **env):
    base = {"PATH": os.environ.get("PATH", ""), "ORG_ROOT": str(root)}
    return subprocess.run([sys.executable, str(HOOK)], input=stdin, env={**base, **env},
                          capture_output=True, timeout=15)


def _lines(root):
    f = Path(root) / "state" / "reports" / "heartbeat.jsonl"
    return [json.loads(x) for x in f.read_text().splitlines()] if f.exists() else []


def _stamp(root, key):
    return Path(root) / "state" / "reports" / "heartbeat.d" / key


def test_hook_writes_one_line_and_then_at_most_one_a_minute(tmp_path):
    p = _hook(tmp_path, CXO_SESSION_ID=PH)
    assert (p.returncode, p.stdout, p.stderr) == (0, b"", b"")
    [line] = _lines(tmp_path)
    assert line["session_id"] == PH and line["task_id"] is None
    assert abs(datetime.strptime(line["ts"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
               - datetime.now(timezone.utc)) < timedelta(seconds=30)

    assert _hook(tmp_path, CXO_SESSION_ID=PH).returncode == 0
    assert len(_lines(tmp_path)) == 1                      # inside the minute: nothing

    old = time.time() - 59                                  # still inside
    os.utime(_stamp(tmp_path, PH), (old, old))
    _hook(tmp_path, CXO_SESSION_ID=PH)
    assert len(_lines(tmp_path)) == 1

    old = time.time() - 61                                  # the minute is up
    os.utime(_stamp(tmp_path, PH), (old, old))
    _hook(tmp_path, CXO_SESSION_ID=PH)
    assert len(_lines(tmp_path)) == 2


def test_a_stamp_from_the_future_does_not_silence_the_session(tmp_path):
    _hook(tmp_path, CXO_SESSION_ID=PH)
    future = time.time() + 3600
    os.utime(_stamp(tmp_path, PH), (future, future))
    _hook(tmp_path, CXO_SESSION_ID=PH)
    assert len(_lines(tmp_path)) == 2


def test_a_worker_beats_under_its_own_name_and_stamp(tmp_path):
    _hook(tmp_path, CXO_SESSION_ID=PH, WORKER_TASK_ID="task-05e48a39")
    _hook(tmp_path, CXO_SESSION_ID=PH)                      # the PH itself, same minute
    worker, ph = _lines(tmp_path)
    assert (worker["session_id"], worker["task_id"]) == ("worker-task-05e48a39", "task-05e48a39")
    assert (ph["session_id"], ph["task_id"]) == (PH, None)
    _hook(tmp_path, WORKER_TASK_ID="task-aaaa1111")         # a worker with no CXO_SESSION_ID
    assert _lines(tmp_path)[-1]["session_id"] == "worker-task-aaaa1111"


@pytest.mark.parametrize("bad", ["../../evil", "a/b", "a b", "x" * 65, "é1", "-lead", "a\nb", "   "])
def test_a_bad_id_writes_nothing_anywhere(tmp_path, bad):
    root = tmp_path / "root"
    root.mkdir()
    for env in ({"CXO_SESSION_ID": bad}, {"WORKER_TASK_ID": bad}):
        p = _hook(root, **env)
        assert (p.returncode, p.stdout, p.stderr) == (0, b"", b"")
    assert list(tmp_path.rglob("*")) == [root]              # no state/, no stamp, no escape


def test_no_session_env_writes_nothing(tmp_path):
    p = _hook(tmp_path)
    assert (p.returncode, p.stdout, p.stderr) == (0, b"", b"")
    assert list(tmp_path.iterdir()) == []


def test_an_unwritable_root_is_silent(tmp_path):
    """Root can write through chmod, so make the path itself impossible: ORG_ROOT is
    a file, then state/ is a file."""
    not_a_dir = tmp_path / "file"
    not_a_dir.write_text("x")
    p = _hook(not_a_dir, CXO_SESSION_ID=PH)
    assert (p.returncode, p.stdout, p.stderr) == (0, b"", b"")
    (tmp_path / "r2").mkdir()
    (tmp_path / "r2" / "state").write_text("x")
    p = _hook(tmp_path / "r2", CXO_SESSION_ID=PH)
    assert (p.returncode, p.stdout, p.stderr) == (0, b"", b"")
    assert (tmp_path / "r2" / "state").read_text() == "x"


def test_a_big_or_missing_stdin_is_fine(tmp_path):
    assert _hook(tmp_path, stdin=b"x" * 3_000_000, CXO_SESSION_ID=PH).returncode == 0
    assert len(_lines(tmp_path)) == 1
    p = subprocess.run([sys.executable, str(HOOK)], stdin=subprocess.DEVNULL, capture_output=True,
                       env={"PATH": os.environ.get("PATH", ""), "ORG_ROOT": str(tmp_path / "b"),
                            "CXO_SESSION_ID": PH}, timeout=15)
    assert (p.returncode, p.stdout, p.stderr) == (0, b"", b"")


# ---------------------------------------------------------------------------
# the fold
# ---------------------------------------------------------------------------

class Hub:
    """SQLite standing in for the hub: only the columns the fold touches. Records
    every statement, so "touches nothing" can be asserted."""

    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.executescript(
            "CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT NOT NULL, last_active TEXT);"
            "CREATE TABLE session_heartbeats (session_id TEXT PRIMARY KEY, project_id TEXT REFERENCES projects(id),"
            " at TEXT NOT NULL);"
            "CREATE TABLE tasks (id TEXT PRIMARY KEY, owner_cto TEXT, owner_role TEXT);")
        self.sql, self.commits, self.rollbacks, self.fail_on = [], 0, 0, None

    def execute(self, sql, params=()):
        self.sql.append(sql)
        if self.fail_on and self.fail_on in sql:
            raise RuntimeError("hub went away")
        return self.db.execute(sql, tuple(
            p.astimezone(timezone.utc).isoformat(timespec="seconds") if isinstance(p, datetime) else p
            for p in params))

    def commit(self):
        self.commits += 1
        self.db.commit()

    def rollback(self):
        self.rollbacks += 1
        self.db.rollback()

    def project(self, pid, name, last_active=None):
        self.db.execute("INSERT INTO projects VALUES (?, ?, ?)", (pid, name, last_active))

    def task(self, tid, owner_cto, owner_role="project_head"):
        self.db.execute("INSERT INTO tasks VALUES (?, ?, ?)", (tid, owner_cto, owner_role))

    def beats(self):
        return dict((r[0], (r[1], r[2])) for r in
                    self.db.execute("SELECT session_id, project_id, at FROM session_heartbeats"))

    def active(self):
        return dict(self.db.execute("SELECT id, last_active FROM projects"))


def iso(minutes):
    return (T0 + timedelta(minutes=minutes)).isoformat(timespec="seconds")


@pytest.fixture
def hub():
    h = Hub()
    h.project("org-restructure", "OrgRestructure")
    return h


@pytest.fixture
def root(tmp_path):
    (tmp_path / "state" / "reports").mkdir(parents=True)
    (tmp_path / "state" / "locks").mkdir(parents=True)
    (tmp_path / "state" / "locks" / f"project_head-{PH}.project").write_text("OrgRestructure")
    return tmp_path


def line(session, minutes, task=None, ts=None):
    ts = ts or (T0 + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return json.dumps({"session_id": session, "task_id": task, "ts": ts}) + "\n"


def put(root, *lines, mode="a"):
    with open(root / "state" / "reports" / "heartbeat.jsonl", mode) as fh:
        fh.write("".join(lines))


def run(hub, root):
    return hf.fold(hub, root, now=NOW)


def test_a_project_head_line_goes_to_its_project(hub, root):
    put(root, line(PH, 1), line(PH, 3), line(PH, 2))
    out = run(hub, root)
    assert out["read"] == 3 and out["folded"] == 3 and out["unknown"] == 0 and out["bad"] == 0
    assert hub.beats() == {PH: ("org-restructure", iso(3))}
    assert hub.active() == {"org-restructure": iso(3)}
    assert hub.commits == 1


@pytest.mark.parametrize("label,pid,name", [
    ("org-restructure", "org-restructure", "Org Restructure"),     # the id, exactly
    ("Org Restructure", "p1", "Org Restructure"),                  # the name, exactly
    ("org restructure", "p1", "ORG RESTRUCTURE"),                  # the name, any case
    ("OrgRestructure", "org-restructure", "Org restructure P3"),   # id with punctuation ignored
    ("OrgRestructure", "p1", "ORG-restructure"),                   # name with punctuation ignored
])
def test_the_lock_label_matches_the_project_id_or_name(root, label, pid, name):
    h = Hub()
    h.project(pid, name)
    (root / "state" / "locks" / f"project_head-{PH}.project").write_text(label + "\n")
    put(root, line(PH, 1))
    assert run(h, root)["folded"] == 1
    assert h.beats() == {PH: (pid, iso(1))}


def test_a_worker_line_goes_to_its_owner_phs_project(hub, root):
    hub.task("task-aaaa1111", PH)
    put(root, line("worker-task-aaaa1111", 5, task="task-aaaa1111"))
    out = run(hub, root)
    assert out["folded"] == 1
    assert hub.beats() == {"worker-task-aaaa1111": ("org-restructure", iso(5))}
    assert hub.active() == {"org-restructure": iso(5)}


def test_unknown_projects_are_skipped_counted_and_do_not_stop_the_rest(hub, root):
    hub.task("task-owned-by-cto", PH, owner_role="cto")             # owner id has a lock, owner role is not a PH
    hub.task("task-ph-no-lock", "11111111")
    put(root,
        line("e106b78b", 1),                                        # a C-level: no PH lock file
        line("worker-task-owned-by-cto", 2, task="task-owned-by-cto"),
        line("worker-task-ph-no-lock", 3, task="task-ph-no-lock"),
        line("worker-task-missing", 4, task="task-missing"),        # no such task row
        line(PH, 5))
    out = run(hub, root)
    assert (out["read"], out["unknown"], out["folded"]) == (5, 4, 1)
    assert list(hub.beats()) == [PH]


def test_a_label_that_matches_two_projects_is_unknown_not_a_guess(hub, root):
    hub.project("org-restructure-2", "Org-Restructure")             # same loose key as the first
    (root / "state" / "locks" / f"project_head-{PH}.project").write_text("org restructure")
    put(root, line(PH, 1))
    out = run(hub, root)
    assert (out["unknown"], out["folded"]) == (1, 0) and hub.beats() == {}


def test_only_an_eight_hex_session_id_is_looked_up_as_a_ph_lock(hub, root):
    locks = root / "state" / "locks"
    for stray in ("zzzzzzzz", "abc.def", "12345"):                  # valid tokens, not PH ids
        (locks / f"project_head-{stray}.project").write_text("OrgRestructure")
    (root / "state" / "secret.project").write_text("OrgRestructure")
    put(root, line("zzzzzzzz", 1), line("abc.def", 2), line("12345", 3), line("../secret", 4))
    out = run(hub, root)
    assert (out["unknown"], out["bad"], out["folded"]) == (3, 1, 0) and hub.beats() == {}


def test_running_twice_changes_nothing_and_a_replay_changes_nothing(hub, root):
    put(root, line(PH, 1), line(PH, 2))
    run(hub, root)
    snapshot = (hub.beats(), hub.active())
    stmts = len(hub.sql)
    again = run(hub, root)
    assert (again["read"], again["folded"]) == (0, 0)
    assert len(hub.sql) == stmts and (hub.beats(), hub.active()) == snapshot   # no SQL at all

    (root / "state" / "reports" / "heartbeat.offset").write_text("0\n")        # replay from the top
    assert run(hub, root)["folded"] == 2
    assert (hub.beats(), hub.active()) == snapshot


def test_new_lines_are_picked_up_from_the_saved_offset(hub, root):
    put(root, line(PH, 1))
    run(hub, root)
    put(root, line(PH, 7))
    out = run(hub, root)
    assert out["read"] == 1 and hub.beats() == {PH: ("org-restructure", iso(7))}
    size = (root / "state" / "reports" / "heartbeat.jsonl").stat().st_size
    assert out["offset"] == size
    assert (root / "state" / "reports" / "heartbeat.offset").read_text().split()[0] == str(size)


def test_a_half_written_last_line_waits_for_the_next_run(hub, root):
    whole = line(PH, 1)
    second = line(PH, 2)
    put(root, whole, second[:20])
    out = run(hub, root)
    assert out["read"] == 1 and out["offset"] == len(whole)
    put(root, second[20:])
    assert run(hub, root)["folded"] == 1
    assert hub.beats() == {PH: ("org-restructure", iso(2))}


def test_a_truncated_file_is_read_from_the_start(hub, root):
    put(root, line(PH, 1), line(PH, 2), line(PH, 3))
    run(hub, root)
    put(root, line(PH, 9), mode="w")                                # shorter than the saved offset
    out = run(hub, root)
    assert out["read"] == 1 and hub.beats() == {PH: ("org-restructure", iso(9))}


def test_a_rotated_file_is_read_from_the_start_even_when_it_is_longer(hub, root):
    put(root, line(PH, 1))
    run(hub, root)
    reports = root / "state" / "reports"
    old_size = (reports / "heartbeat.jsonl").stat().st_size
    new = reports / "heartbeat.jsonl.new"
    new.write_text("".join(line(PH, m) for m in (10, 11, 12, 13)))
    assert new.stat().st_size > old_size            # past the saved offset: only the inode tells
    os.replace(new, reports / "heartbeat.jsonl")
    out = run(hub, root)
    assert out["read"] == 4 and hub.beats() == {PH: ("org-restructure", iso(13))}


def test_a_missing_file_or_offset_garbage_is_not_an_error(hub, root):
    assert run(hub, root)["read"] == 0 and hub.sql == []            # no file: no SQL, no offset file
    assert not (root / "state" / "reports" / "heartbeat.offset").exists()
    put(root, line(PH, 1))
    (root / "state" / "reports" / "heartbeat.offset").write_text("not a number")
    assert run(hub, root)["folded"] == 1


def test_last_active_and_the_session_row_only_move_forward(hub, root):
    hub.db.execute("UPDATE projects SET last_active = ?", (iso(50),))
    put(root, line(PH, 5))
    run(hub, root)
    assert hub.active() == {"org-restructure": iso(50)}             # an older beat does not lower it
    assert hub.beats() == {PH: ("org-restructure", iso(5))}

    put(root, line(PH, 60))
    run(hub, root)
    assert hub.active() == {"org-restructure": iso(60)}
    put(root, line(PH, 20))                                         # a late, older line
    run(hub, root)
    assert hub.active() == {"org-restructure": iso(60)}
    assert hub.beats() == {PH: ("org-restructure", iso(60))}


def test_an_older_line_does_not_move_a_session_to_another_project(hub, root):
    hub.project("other", "Other")
    put(root, line(PH, 30))
    run(hub, root)
    (root / "state" / "locks" / f"project_head-{PH}.project").write_text("Other")
    put(root, line(PH, 10))
    run(hub, root)
    assert hub.beats() == {PH: ("org-restructure", iso(30))}


def test_bad_lines_are_counted_and_the_good_ones_still_fold(hub, root):
    far = (NOW + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    put(root,
        "not json\n", "[1, 2]\n", '{"session_id": "x"}\n', "\n",
        line(PH, 1, task=5), line("bad id", 1), line(PH, 1, ts="yesterday"),
        line(PH, 1, ts=far),                                        # a clock far ahead must not freeze last_active
        line(PH, 4))
    out = run(hub, root)
    assert (out["read"], out["bad"], out["folded"]) == (8, 7, 1)
    assert hub.active() == {"org-restructure": iso(4)}


def test_a_hub_error_leaves_the_offset_where_it_was(hub, root):
    put(root, line(PH, 1))
    hub.fail_on = "INSERT INTO session_heartbeats"
    with pytest.raises(RuntimeError):
        run(hub, root)
    assert not (root / "state" / "reports" / "heartbeat.offset").exists()
    hub.fail_on = None
    assert run(hub, root)["folded"] == 1                            # nothing was lost
    assert hub.beats() == {PH: ("org-restructure", iso(1))}


# ---------------------------------------------------------------------------
# the publisher loop
# ---------------------------------------------------------------------------

class _Conn:
    def __init__(self):
        self.sql, self.closed, self.rollbacks = [], False, 0

    def execute(self, sql, params=()):
        self.sql.append(sql)
        return type("R", (), {"fetchall": lambda s: [], "fetchone": lambda s: None})()

    def commit(self):
        pass

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


def _loop(tmp_path, monkeypatch, fold_fn, steps=30):
    conn, clock = _Conn(), {"t": 1000.0}
    monkeypatch.setattr(ls.time, "monotonic", lambda: clock["t"])
    reported = []

    class Stop(threading.Event):
        n = 0

        def wait(self, timeout=None):
            Stop.n += 1
            clock["t"] += timeout
            if Stop.n == steps:
                self.set()
            return self.is_set()

    pub = ls.Publisher("postgresql://x", "contabo", [tmp_path / "none"], stop=Stop(),
                       lock_path=tmp_path / "l", connect=lambda url: conn, on_error=reported.append,
                       fold_fn=fold_fn, fold_path=tmp_path / "heartbeat_fold.py")
    pub._hold()
    return conn, reported


def test_the_publisher_folds_once_a_minute(tmp_path, monkeypatch):
    calls = []
    _loop(tmp_path, monkeypatch, lambda conn: calls.append(conn), steps=30)    # 30 polls x 5 s = 150 s
    assert len(calls) == 3                                                      # t=0, 60, 120


def test_a_fold_that_raises_is_reported_rolled_back_and_publishing_goes_on(tmp_path, monkeypatch):
    def boom(conn):
        raise RuntimeError("relation does not exist")

    conn, reported = _loop(tmp_path, monkeypatch, boom, steps=30)
    assert reported == ["heartbeat fold RuntimeError"] * 3          # the class name only, never the message
    assert conn.rollbacks == 3
    published = [s for s in conn.sql if s.startswith("INSERT INTO live_hosts")]
    assert len(published) >= 3 and conn.closed                      # the loop ran to its end


def test_the_loop_ends_when_the_fold_module_changes_on_disk(tmp_path):
    code = tmp_path / "heartbeat_fold.py"
    code.write_text("v1")
    pub = ls.Publisher("postgresql://x", "contabo", [tmp_path], lock_path=tmp_path / "l",
                       fold_path=code)
    assert pub._done() is False
    ns = code.stat().st_mtime_ns + 5_000_000_000
    os.utime(code, ns=(ns, ns))
    assert pub._done() is True       # a git pull of the fold: leave, the next hook respawns the loop


# ---------------------------------------------------------------------------
# the real tables (CI: a postgres:16 service container)
# ---------------------------------------------------------------------------

ORG_TEST_DB_URL = os.environ.get("ORG_TEST_DB_URL", "").strip()


@pytest.mark.skipif(not ORG_TEST_DB_URL, reason="ORG_TEST_DB_URL not set (local Postgres 16)")
def test_the_fold_runs_against_the_real_p3a_tables(root, monkeypatch):
    import lib.db as db_mod
    import lib.db_pg as db_pg
    tables = ("projects", "project_events", "milestones", "ceo_gos", "resource_locks",
              "post_ledger", "session_heartbeats")

    def drop():
        c = db_pg.connect(ORG_TEST_DB_URL, timeout=10)
        try:
            for t in reversed(tables):
                c.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
            c.execute("DROP FUNCTION IF EXISTS project_events_append_only() CASCADE")
            c.commit()
        finally:
            c.close()

    monkeypatch.setenv("ORG_DB_URL", ORG_TEST_DB_URL)
    for v in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE", "ORG_CHARTER_GATE"):
        monkeypatch.delenv(v, raising=False)
    drop()
    db_mod.init()
    conn = db_pg.connect(ORG_TEST_DB_URL, timeout=10)
    try:
        conn.execute("INSERT INTO projects (id, name, lane, last_active) VALUES (?, ?, ?, ?)",
                     ("org-restructure", "OrgRestructure", "cto", T0 + timedelta(minutes=50)))
        conn.commit()
        put(root, line(PH, 5), line(PH, 60), line(PH, 7))
        assert hf.fold(conn, root, now=NOW)["folded"] == 3
        (root / "state" / "reports" / "heartbeat.offset").write_text("0\n")
        assert hf.fold(conn, root, now=NOW)["folded"] == 3                       # replay
        got = conn.execute("SELECT project_id, at FROM session_heartbeats WHERE session_id = ?",
                           (PH,)).fetchone()
        assert (got[0], got[1]) == ("org-restructure", T0 + timedelta(minutes=60))
        la = conn.execute("SELECT last_active FROM projects WHERE id = ?", ("org-restructure",)).fetchone()
        assert la[0] == T0 + timedelta(minutes=60)
    finally:
        conn.rollback()
        conn.close()
        drop()
