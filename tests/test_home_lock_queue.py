"""Tests for tools/home_lock.py FIFO wait queue with fake lock transport and fake clock."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone

import pytest

from tools import home_lock as hl

KEY = "home:winbox:9224"


class FakeEnv:
    def __init__(self, queue_dir):
        self.queue_dir = queue_dir
        self.now = 1000.0
        self.locks: dict[str, dict] = {}
        self.acquire_calls: list[tuple[float, str, str]] = []
        self.alive_pids: set[int] = {os.getpid()}
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._sleeping = 0
        self._tick = 0
        self.auto_advance_sleep = True

    def clock(self) -> float:
        with self._lock:
            return self.now

    def pid_alive(self, pid: int) -> bool:
        with self._lock:
            return pid in self.alive_pids

    def _purge_expired_locked(self) -> None:
        expired = [k for k, lk in self.locks.items() if lk["_expires_ts"] <= self.now]
        for k in expired:
            del self.locks[k]

    def transport(self, method: str, op: str, body: dict | None = None) -> tuple[int, dict]:
        with self._lock:
            self._purge_expired_locked()
            if method == "GET" and op == "":
                public = [
                    {k: v for k, v in lk.items() if not k.startswith("_")}
                    for lk in self.locks.values()
                ]
                return 200, {"locks": public}
            if method == "POST" and op == "acquire":
                assert body is not None
                key, owner = body["key"], body["owner"]
                ttl = int(body.get("ttl") or hl.TTL_DEFAULT_S)
                purpose = body.get("purpose") or ""
                self.acquire_calls.append((self.now, key, owner))
                cur = self.locks.get(key)
                if cur and cur["owner"] != owner:
                    holder = {k: v for k, v in cur.items() if not k.startswith("_")}
                    return 409, {"ok": False, "holder": holder}
                exp_ts = self.now + ttl
                exp_iso = datetime.fromtimestamp(exp_ts, timezone.utc).isoformat()
                lock = {
                    "key": key,
                    "owner": owner,
                    "expiresAt": exp_iso,
                    "_expires_ts": exp_ts,
                }
                if purpose:
                    lock["purpose"] = purpose
                self.locks[key] = lock
                public_lock = {k: v for k, v in lock.items() if not k.startswith("_")}
                return 200, {"ok": True, "lock": public_lock, "renewed": bool(cur)}
            if method == "POST" and op == "release":
                assert body is not None
                key, owner = body["key"], body["owner"]
                cur = self.locks.get(key)
                released = bool(cur and cur["owner"] == owner)
                if released:
                    del self.locks[key]
                return 200, {"ok": True, "released": released}
            return 404, {}

    def sleep(self, seconds: float) -> None:
        with self._cond:
            if self.auto_advance_sleep:
                self.now += max(0.0, float(seconds))
                return
            my_tick = self._tick
            self._sleeping += 1
            self._cond.notify_all()
            while self._tick == my_tick:
                self._cond.wait()
            self._sleeping -= 1
            self._cond.notify_all()

    def wait_for_sleepers(self, count: int) -> None:
        with self._cond:
            while self._sleeping < count:
                self._cond.wait(timeout=2.0)

    def step_clock(self, dt: float, expected_sleepers: int) -> None:
        with self._cond:
            while self._sleeping < expected_sleepers:
                self._cond.wait(timeout=2.0)
            self.now += dt
            self._tick += 1
            self._cond.notify_all()


@pytest.fixture
def env(monkeypatch, tmp_path):
    fe = FakeEnv(tmp_path / "home-queue")
    monkeypatch.setattr(hl, "QUEUE_DIR", fe.queue_dir)
    monkeypatch.setattr(hl, "_clock", fe.clock)
    monkeypatch.setattr(hl, "_sleep", fe.sleep)
    monkeypatch.setattr(hl, "_pid_alive", fe.pid_alive)
    monkeypatch.setattr(hl, "_poll_delay", lambda: 12.0)
    monkeypatch.setattr(hl, "_transport", fe.transport)
    for var in ("LEASE_DB_URL", "LEASE_OWNER_SESSION", "WORKER_TASK_ID", "CXO_ROLE", "CXO_SESSION_ID", "CTO_SESSION_ID", "ORG_SESSION_ID"):
        monkeypatch.delenv(var, raising=False)
    return fe


def test_three_waiters_get_lock_in_arrival_order(env, capsys):
    env.auto_advance_sleep = False
    hl.acquire(KEY, "holder-0", ttl=600, purpose="initial login")

    granted_order: list[str] = []
    errors: list[Exception] = []

    def run_waiter(owner: str, purpose: str) -> None:
        try:
            lock = hl.acquire(KEY, owner, ttl=300, purpose=purpose, wait_s=180)
            assert lock["owner"] == owner
            granted_order.append(owner)
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    t1 = threading.Thread(target=run_waiter, args=("waiter-1", "job-1"), daemon=True)
    t2 = threading.Thread(target=run_waiter, args=("waiter-2", "job-2"), daemon=True)
    t3 = threading.Thread(target=run_waiter, args=("waiter-3", "job-3"), daemon=True)

    t1.start()
    env.wait_for_sleepers(1)

    with env._lock:
        env.now += 1.0
    t2.start()
    env.wait_for_sleepers(2)

    with env._lock:
        env.now += 1.0
    t3.start()
    env.wait_for_sleepers(3)

    # Check queue status and CLI output while all 3 waiters are queued behind holder-0
    assert hl.main(["queue", KEY]) == 0
    out = capsys.readouterr().out
    assert "holder: holder-0" in out
    assert "1. waiter-1  waited 2s  (job-1)" in out
    assert "2. waiter-2  waited 1s  (job-2)" in out
    assert "3. waiter-3  waited 0s  (job-3)" in out

    # Only waiter-1 (first in line) attempted initial POST /acquire after holder-0
    assert [owner for _, _, owner in env.acquire_calls] == ["holder-0", "waiter-1"]

    # One poll tick while holder-0 still holds the lock: nobody retries POST /acquire
    env.step_clock(12.0, expected_sleepers=3)
    env.wait_for_sleepers(3)
    assert [owner for _, _, owner in env.acquire_calls] == ["holder-0", "waiter-1"]

    # holder-0 releases -> waiter-1 acquires first
    assert hl.release(KEY, "holder-0") is True
    env.step_clock(12.0, expected_sleepers=3)
    t1.join(timeout=2.0)
    assert not t1.is_alive()
    assert granted_order == ["waiter-1"]
    env.wait_for_sleepers(2)

    # waiter-1 releases -> waiter-2 acquires second
    assert hl.release(KEY, "waiter-1") is True
    env.step_clock(12.0, expected_sleepers=2)
    t2.join(timeout=2.0)
    assert not t2.is_alive()
    assert granted_order == ["waiter-1", "waiter-2"]
    env.wait_for_sleepers(1)

    # waiter-2 releases -> waiter-3 acquires third
    assert hl.release(KEY, "waiter-2") is True
    env.step_clock(12.0, expected_sleepers=1)
    t3.join(timeout=2.0)
    assert not t3.is_alive()
    assert not errors
    assert granted_order == ["waiter-1", "waiter-2", "waiter-3"]
    assert hl.queue_status(KEY)["waiters"] == []


def test_dead_waiter_is_skipped(env):
    hl.acquire(KEY, "holder-0", ttl=600)

    # Enqueue two waiters ahead of waiter-live:
    # 1) waiter-dead-pid whose PID disappears
    # 2) waiter-stale-hb whose heartbeat is >120 s old
    env.alive_pids.add(777001)
    env.alive_pids.add(777002)
    hl._enqueue_or_touch(KEY, "waiter-dead-pid", "dead-proc", now=env.now, pid=777001)
    hl._enqueue_or_touch(KEY, "waiter-stale-hb", "hung-proc", now=env.now - 125.0, pid=777002)

    # Kill 777001 before waiter-live polls
    env.alive_pids.remove(777001)

    # Schedule holder-0 to release on the first sleep tick
    real_sleep = env.sleep

    def release_then_sleep(seconds: float) -> None:
        real_sleep(seconds)
        hl.release(KEY, "holder-0")

    env.sleep = release_then_sleep  # type: ignore[method-assign]
    lock = hl.acquire(KEY, "waiter-live", ttl=300, purpose="live-job", wait_s=30)
    assert lock["owner"] == "waiter-live"
    assert hl.queue_status(KEY)["waiters"] == []


def test_timeout_message_and_exit_code(env, capsys):
    hl.acquire(KEY, "holder-0", ttl=1800, purpose="long task")

    # Put waiter-1 at position 1 and keep its heartbeat fresh as fake clock advances
    hl._enqueue_or_touch(KEY, "waiter-1", "first-waiter", now=env.now)
    base_sleep = env.sleep

    def sleep_keep_w1_alive(seconds: float) -> None:
        base_sleep(seconds)
        hl._enqueue_or_touch(KEY, "waiter-1", "first-waiter", now=env.now)

    env.sleep = sleep_keep_w1_alive  # type: ignore[method-assign]

    # waiter-2 is at position 2 behind holder-0 and times out after 25s
    rc = hl.main(["acquire", KEY, "--owner", "waiter-2", "--wait", "25"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "still queued behind holder-0, position 2" in err

    # waiter-2 was removed on timeout; waiter-1 is still at position 1
    waiters = hl.queue_status(KEY)["waiters"]
    assert [w["owner"] for w in waiters] == ["waiter-1"]

    # Now waiter-1 itself times out at position 1
    env.sleep = base_sleep  # type: ignore[method-assign]
    rc1 = hl.main(["acquire", KEY, "--owner", "waiter-1", "--wait", "25"])
    assert rc1 == 2
    err1 = capsys.readouterr().err
    assert "still queued behind holder-0, position 1" in err1
    assert hl.queue_status(KEY)["waiters"] == []


def test_no_wait_unchanged(env, capsys):
    hl.acquire(KEY, "holder-0", ttl=600, purpose="active")
    t0 = env.now
    with pytest.raises(hl.HomeLockHeld) as exc:
        hl.acquire(KEY, "waiter-nowait")
    assert exc.value.holder["owner"] == "holder-0"
    assert "still queued" not in str(exc.value)
    assert env.now == t0
    assert not (env.queue_dir / "home_winbox_9224.jsonl").exists()

    assert hl.main(["acquire", KEY, "--owner", "waiter-nowait"]) == 2
    assert "is held by holder-0" in capsys.readouterr().err
    assert not (env.queue_dir / "home_winbox_9224.jsonl").exists()


def test_context_manager_wait_s_and_expiry(env, capsys):
    # holder-0 takes a 60s lock; waiter uses home_lock(..., wait_s=90) and acquires once holder-0's TTL expires
    hl.acquire(KEY, "holder-0", ttl=60, purpose="short")
    with hl.home_lock(KEY, owner="waiter-ctx", purpose="after-expiry", wait_s=90) as held:
        assert held.lock["owner"] == "waiter-ctx"
        assert hl.main(["queue", KEY, "--json"]) == 0
        q_info = json.loads(capsys.readouterr().out)
        assert q_info["holder"]["owner"] == "waiter-ctx"
        assert q_info["waiters"] == []
    assert hl.list_locks() == []
