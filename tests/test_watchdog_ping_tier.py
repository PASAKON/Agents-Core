"""UsageBudget P4b: the watchdog's "status check" ping to a silent worker is paced by the
usage budget and the task's tier (lib/wake_backoff.wake_interval). Stall detection is not.

The tier comes from the task's `tier:` header line (lib/portfolio.tier_for reads it before it
touches the hub), the budget from a json file under tmp_path; nothing else is real.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

import runners.watchdog as watchdog
from lib import wake_backoff

pytestmark = pytest.mark.usefixtures("pinned_mac_host")


def _iso(minutes_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def _row(silent_min, tier):
    return {"id": "task-ping0001", "host": None, "status": "in_progress", "pid": None,
            "updated_at": _iso(silent_min), "review": None,
            "description": f"tier: {tier}\n\nbody"}


@pytest.fixture
def scan(monkeypatch, tmp_path):
    """scan_once over one in_progress row, every other pass stubbed; returns (pings, stalls)."""
    pings, stalls = [], []
    monkeypatch.setattr(watchdog, "gc_stale_tasks", lambda: [])
    monkeypatch.setattr(watchdog, "sweep_terminal_surfaces", lambda: [])
    monkeypatch.setattr(watchdog, "_drain_disk_queue", lambda: None)
    monkeypatch.setattr(watchdog.work_watch, "watch",
                        lambda: {"alerted": [], "lungnote_filed": [], "green": []})
    monkeypatch.delenv("ORG_WATCHDOG_BRANCH_POLL", raising=False)
    monkeypatch.setattr(watchdog, "_pid_alive", lambda pid: False)
    monkeypatch.setattr(watchdog, "_mac_surfaces", lambda: False)
    monkeypatch.setattr(watchdog, "_file_stalled_issue", lambda t, s: "issue-url")
    monkeypatch.setattr(watchdog, "_cleanup_tmux_ttyd", lambda t: {"tmux_killed": False})
    monkeypatch.setattr(watchdog, "_send_ping", lambda tid, msg: pings.append(tid) or True)
    monkeypatch.setattr(watchdog.db, "update_status",
                        lambda tid, status, **kw: stalls.append((tid, status)))
    monkeypatch.setattr(wake_backoff, "BUDGET_PATH", tmp_path / "usage-budget.json")

    def run(row, states=None, age_s=0):
        if states is not None:
            ts = (datetime.now(timezone.utc) - timedelta(seconds=age_s)).isoformat()
            (tmp_path / "usage-budget.json").write_text(json.dumps(
                {"ts": ts, "rows": {p: {"state": s} for p, s in
                                    zip(("agy", "chatgpt", "claude"), states)}}))
        monkeypatch.setattr(watchdog.db, "list_tasks",
                            lambda status=None, limit=0: [row] if status == "in_progress" else [])
        watchdog.scan_once()
        return pings, stalls
    return run


UNDER, ONE, ALL = ("under",) * 3, ("over", "under", "under"), ("over",) * 3


@pytest.mark.parametrize("tier,states,silent_min,pings", [
    # critical: 10 min, x2 one provider over, x4 all over (40 min is past the 30-min stall)
    ("critical", UNDER, 11, True),
    ("critical", ONE, 11, False),
    ("critical", ONE, 21, True),
    ("critical", ALL, 29, False),
    # normal: x2 more while over
    ("normal", UNDER, 11, True),
    ("normal", ONE, 21, False),
    ("normal", ONE, 29, False),
    ("normal", ALL, 29, False),
    # low: no timed ping at all
    ("low", UNDER, 11, False),
    ("low", UNDER, 29, False),
    ("low", None, 29, False),
    # no budget file: base interval for every tier but low
    ("critical", None, 11, True),
    ("normal", None, 11, True),
])
def test_the_ping_waits_budget_x_tier(scan, tier, states, silent_min, pings):
    got, stalls = scan(_row(silent_min, tier), states)
    assert (got == ["task-ping0001"]) is pings
    assert stalls == []


def test_a_stale_budget_does_not_slow_the_ping(scan):
    got, _ = scan(_row(11, "critical"), ALL, age_s=1801)
    assert got == ["task-ping0001"]


@pytest.mark.parametrize("tier", ["critical", "normal", "low"])
@pytest.mark.parametrize("states", [UNDER, ALL])
def test_stall_detection_is_never_slowed_or_tiered(scan, tier, states):
    got, stalls = scan(_row(31, tier), states)
    assert got == []
    assert stalls == [("task-ping0001", "stalled")]
