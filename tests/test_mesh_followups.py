"""Org Mesh follow-ups (task-3bf2da7c) from the W2.7 and W4.4 reviews.

1. queued_remote retry cap: a row whose host never answers is failed at
   ORG_MESH_MAX_ATTEMPTS (default 12), its path locks released, the owner told
   once. The attempt count is per task and exact, not a window over the ledger.
2. deliver_letter timeout: long enough for the Windows wake
   (agent_transport.wake_windows_tab, ~30 s worst case) plus the write, so a
   slow wake is not read as an unreachable host for a letter already on disk.

(3, runner_claude on macOS, lives in tests/test_w44_probe_provides.py.)

Fakes only. mesh.dispatch is a scripted stand-in (no ssh leaves this process),
lib.db points at a tmp_path SQLite ledger, and the owner letter and the
notifier are recorders.

Run:  .venv/bin/python -m pytest tests/test_mesh_followups.py
"""
from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import config, mesh  # noqa: E402
from lib import db as db_mod  # noqa: E402
from lib import notify as notify_mod  # noqa: E402
import runners.watchdog as watchdog  # noqa: E402
from tools import agent_transport  # noqa: E402
from tools import delegate  # noqa: E402
from tools import send_to_cto  # noqa: E402

PROJECT = "mooniex-agents"
TOUCH = ["lib/mesh.py"]


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setenv("ORG_HOST", "mac")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv(mesh.ENV_FLAG, "1")
    monkeypatch.delenv("ORG_MESH_MAX_ATTEMPTS", raising=False)
    # error()/warn() would run osascript on the Mac: record, never notify.
    monkeypatch.setattr(notify_mod, "notify", lambda *a, **kw: None)
    config.self_host.cache_clear()
    yield
    config.self_host.cache_clear()


class Letters:
    """send_to_cto.send, recorded: the owner mailbox is never really written."""

    def __init__(self) -> None:
        self.calls: list[tuple[tuple, dict]] = []

    def __call__(self, *a, **kw):
        self.calls.append((a, kw))
        return True


@pytest.fixture()
def letters(monkeypatch) -> Letters:
    rec = Letters()
    monkeypatch.setattr(send_to_cto, "send", rec)
    return rec


class Dial:
    """mesh.dispatch: every call is recorded, then the host is silent."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def __call__(self, host, verb, *args, timeout=None):
        self.calls.append((host, verb, args))
        raise mesh.MeshUnreachable(f"{verb} on {host}: no route")


@pytest.fixture()
def dial(monkeypatch) -> Dial:
    d = Dial()
    monkeypatch.setattr(mesh, "dispatch", d)
    return d


def _task(touches=None, owner=("abcd1234", "cto")) -> str:
    tid = db_mod.create_task(PROJECT, "developer", "t", "d", touches=touches,
                             owner_cto=owner[0], owner_role=owner[1])
    if touches:
        ok, _, _ = db_mod.lock_paths(tid, PROJECT, touches)
        assert ok
    return tid


def _queued(tid: str, attempts: int, host: str = "contabo") -> None:
    """A row that has been unreachable `attempts` times: that many
    `status_queued_remote` events, exactly as mesh_spawn_worker writes them."""
    for _ in range(attempts):
        db_mod.update_status(tid, "queued_remote", host=host, actor="cto",
                             delegate_log="mesh spawn_worker unreachable")


def _lock_keys(tid: str) -> list[str]:
    with db_mod.get_conn() as conn:
        rows = conn.execute("SELECT key FROM locks WHERE owner=?", (tid,)).fetchall()
    return sorted(r["key"] for r in rows)


# ---------------------------------------------------------------------------
# 1. the cap: constant, env override, bad values
# ---------------------------------------------------------------------------

def test_the_default_cap_is_twelve_and_fits_the_watchdog_tick():
    assert mesh.MAX_ATTEMPTS == 12
    assert mesh.max_attempts() == 12
    # 12 attempts = the first at delegate time + 11 watchdog passes: about an
    # hour at the 300 s tick. Pinned so a change to either number is deliberate.
    assert watchdog.INTERVAL_S == 300
    assert (mesh.max_attempts() - 1) * watchdog.INTERVAL_S == 55 * 60


@pytest.mark.parametrize("value,expected", [
    ("3", 3), (" 5 ", 5), ("1", 1),
    ("0", 12), ("-4", 12), ("", 12), ("many", 12), ("2.5", 12),
])
def test_the_env_override_is_read_and_a_bad_value_never_means_unlimited(monkeypatch, value, expected):
    monkeypatch.setenv("ORG_MESH_MAX_ATTEMPTS", value)
    assert mesh.max_attempts() == expected


# ---------------------------------------------------------------------------
# 1. the cap, through the watchdog
# ---------------------------------------------------------------------------

def test_a_row_at_the_cap_is_failed_not_dialled_again(dial, letters):
    tid = _task(touches=TOUCH)
    _queued(tid, 12)
    assert delegate._queued_remote_attempts(tid) == 12

    out = watchdog._retry_queued_remote()

    assert out == [{"task": tid, "host": "contabo", "status": "failed"}]
    assert dial.calls == []  # the cap stops the dial, it does not spend one more
    row = db_mod.get_task(tid)
    assert row["status"] == "failed"
    assert "contabo" in row["delegate_log"] and "12" in row["delegate_log"]
    assert "ORG_MESH_MAX_ATTEMPTS" in row["delegate_log"]
    assert db_mod.list_tasks(status="queued_remote") == []


def test_a_row_under_the_cap_is_still_retried(dial, letters):
    tid = _task()
    _queued(tid, 11)
    out = watchdog._retry_queued_remote()
    assert dial.calls == [("contabo", "spawn_worker", (tid,))]
    assert out == [{"task": tid, "host": "contabo", "status": "queued_remote"}]
    assert db_mod.get_task(tid)["status"] == "queued_remote"
    assert letters.calls == []


def test_the_twelfth_failed_attempt_is_the_last_one(dial, letters):
    """End to end from attempt 1: 12 dials, then the next pass fails the row
    without a 13th."""
    tid = _task()
    _queued(tid, 1)  # attempt 1, at delegate time
    for _ in range(11):  # attempts 2..12
        assert watchdog._retry_queued_remote()[0]["status"] == "queued_remote"
    assert len(dial.calls) == 11
    assert delegate._queued_remote_attempts(tid) == 12
    assert watchdog._retry_queued_remote()[0]["status"] == "failed"
    assert len(dial.calls) == 11  # no 13th dial
    assert db_mod.get_task(tid)["status"] == "failed"


def test_the_env_override_moves_the_cap(monkeypatch, dial, letters):
    monkeypatch.setenv("ORG_MESH_MAX_ATTEMPTS", "3")
    tid = _task()
    _queued(tid, 3)
    assert watchdog._retry_queued_remote() == [
        {"task": tid, "host": "contabo", "status": "failed"}]
    assert dial.calls == []


def test_the_path_locks_are_released_like_a_failed_launcher_run(dial, letters):
    tid = _task(touches=TOUCH)
    _queued(tid, 12)
    assert _lock_keys(tid), "queued_remote must hold the path locks while it waits"
    assert db_mod.find_conflicts(PROJECT, TOUCH)  # a second task would be blocked

    watchdog._retry_queued_remote()

    assert _lock_keys(tid) == []
    assert db_mod.find_conflicts(PROJECT, TOUCH) == []  # free for the next task


def test_the_owner_hears_once_not_once_per_pass(dial, letters):
    tid = _task()
    _queued(tid, 12)
    watchdog._retry_queued_remote()
    watchdog._retry_queued_remote()
    watchdog._retry_queued_remote()
    assert len(letters.calls) == 1
    args, kw = letters.calls[0]
    assert args[0] == tid
    assert "contabo" in args[1] and "12" in args[1]
    assert kw["cto_id"] == "abcd1234" and kw["owner_role"] == "cto"


def test_a_failed_owner_letter_does_not_undo_the_failure(monkeypatch, dial):
    def boom(*a, **kw):
        raise OSError("disk full")
    monkeypatch.setattr(send_to_cto, "send", boom)
    tid = _task(touches=TOUCH)
    _queued(tid, 12)
    out = watchdog._retry_queued_remote()
    assert out[0]["status"] == "failed"
    assert _lock_keys(tid) == []


def test_the_failure_is_raised_through_the_error_path_once(monkeypatch, dial, letters):
    seen: list[str] = []
    monkeypatch.setattr(delegate, "error", lambda msg, *a, **kw: seen.append(msg))
    tid = _task()
    _queued(tid, 12)
    watchdog._retry_queued_remote()
    watchdog._retry_queued_remote()
    assert len(seen) == 1 and tid in seen[0] and "contabo" in seen[0]


def test_a_row_someone_else_already_moved_is_not_failed_or_announced(dial, letters):
    """Give-up only acts on a row still waiting. A far side that moved it (or a
    second watchdog that got there first) must not get a `failed` on top."""
    tid = _task()
    _queued(tid, 12)
    db_mod.update_status(tid, "in_progress", pid=4242, host="contabo", actor="test")
    row = delegate.give_up_queued_remote(tid, "contabo", 12)
    assert row["status"] == "in_progress"
    assert letters.calls == []


def test_one_row_at_the_cap_does_not_stop_the_others(dial, letters):
    capped = _task()
    _queued(capped, 12)
    fresh = _task()
    _queued(fresh, 1)
    out = watchdog._retry_queued_remote()
    assert {(o["task"], o["status"]) for o in out} == {
        (capped, "failed"), (fresh, "queued_remote")}
    assert dial.calls == [("contabo", "spawn_worker", (fresh,))]


# ---------------------------------------------------------------------------
# 1. the count is per task and exact
# ---------------------------------------------------------------------------

def test_the_attempt_count_ignores_other_tasks_however_busy_the_ledger(dial, letters):
    """recent_events(limit=500) over a busy ledger: 600 newer events from other
    tasks must not bury this task's attempts."""
    tid = _task()
    _queued(tid, 4)
    noisy = _task()
    for i in range(600):
        db_mod.set_fields(noisy, actor="noise", delegate_log=f"noise {i}")
    assert delegate._queued_remote_attempts(tid) == 4
    assert delegate._queued_remote_attempts(noisy) == 0


def test_the_attempt_count_survives_a_task_with_hundreds_of_other_events(dial, letters):
    """The same task logging 600 unrelated events after its attempts: a window
    of 500 would read 0 and a dead host would never hit the cap."""
    tid = _task()
    _queued(tid, 12)
    for i in range(600):
        db_mod.set_fields(tid, actor="noise", delegate_log=f"noise {i}")
    assert delegate._queued_remote_attempts(tid) == 12
    assert watchdog._retry_queued_remote()[0]["status"] == "failed"


# ---------------------------------------------------------------------------
# 2. deliver_letter timeout
# ---------------------------------------------------------------------------

def test_deliver_letter_has_its_own_timeout():
    assert "deliver_letter" in mesh.VERB_TIMEOUT_S


def test_deliver_letter_outlasts_the_windows_wake_plus_the_write():
    wake_worst = agent_transport.WAKE_WORST_CASE_S
    assert wake_worst >= 30  # schtasks /run 15 s + the result wait 15 s
    # the ssh dial, then the far side runs the wake, then the write
    assert mesh.VERB_TIMEOUT_S["deliver_letter"] > mesh.CONNECT_TIMEOUT_S + wake_worst
    assert mesh.VERB_TIMEOUT_S["deliver_letter"] > mesh.DEFAULT_TIMEOUT_S


def test_the_wake_worst_case_is_built_from_the_numbers_the_wake_really_uses(tmp_path):
    """WAKE_WORST_CASE_S is not a second copy of a number: the schtasks timeout
    and the result wait the wake runs with are the two terms of it."""
    seen = {}

    def run(argv, **kw):
        seen["timeout"] = kw.get("timeout")
        return subprocess.CompletedProcess(argv, 1, "", "no task")

    agent_transport.wake_windows_tab("cto-2c6b9f03", "CTO", wake_dir=tmp_path, run=run,
                                     sleep=lambda s: None)
    wait_default = inspect.signature(agent_transport.wake_windows_tab).parameters["wait_s"].default
    assert seen["timeout"] == agent_transport._WAKE_RUN_TIMEOUT_S
    assert wait_default == agent_transport._WAKE_WAIT_S
    assert agent_transport.WAKE_WORST_CASE_S == seen["timeout"] + wait_default


def test_mesh_dispatch_gives_deliver_letter_that_timeout(monkeypatch):
    calls = []

    def fake_run(argv, **kw):
        calls.append(kw)
        return subprocess.CompletedProcess(argv, 0, '{"ok": true, "verb": "deliver_letter"}\n', "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    mesh.dispatch("contabo", "deliver_letter", "42")
    assert calls[0]["timeout"] == mesh.VERB_TIMEOUT_S["deliver_letter"]


def test_a_slow_wake_inside_the_timeout_is_a_reply_not_an_unreachable_host(monkeypatch):
    """The far side took longer than the old 30 s default and answered: the
    caller gets the reply. (A TimeoutExpired is what the old default raised.)"""
    limit = mesh.VERB_TIMEOUT_S["deliver_letter"]
    took = agent_transport.WAKE_WORST_CASE_S + 1  # wake at its worst, plus the write

    def fake_run(argv, **kw):
        if took > kw["timeout"]:
            raise subprocess.TimeoutExpired(argv, kw["timeout"])
        return subprocess.CompletedProcess(argv, 0, '{"ok": true, "verb": "deliver_letter"}\n', "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert limit > took
    assert mesh.dispatch("contabo", "deliver_letter", "42")["ok"] is True
