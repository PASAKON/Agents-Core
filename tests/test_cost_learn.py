"""Tests for tools/cost_learn.py (Q3b — cost learner).

Fixtures only: uses tmp_path, monkeypatch DEFAULT_HISTORY / COST_TABLE_PATH.
Never touches the real state/ directory or the real ledger.
All jobs are passed via jobs= kwarg.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.quota as quota_mod
from tools import cost_learn, forecast


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc(h: int = 0, m: int = 0) -> datetime:
    """Return a fixed UTC datetime at 2026-09-30 + h hours + m minutes."""
    return datetime(2026, 9, 30, 0, 0, 0, tzinfo=timezone.utc) + timedelta(hours=h, minutes=m)


def _history_file(tmp_path: Path, rows: list[dict]) -> Path:
    """Write rows as JSONL to tmp_path/quota-history.jsonl and return the path."""
    p = tmp_path / "quota-history.jsonl"
    lines = [json.dumps(r) for r in rows]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def _hist_row(bucket: str, ts: datetime, weekly: float) -> dict:
    return {
        "ts": ts.isoformat(),
        "provider": bucket,
        "weekly_remaining": weekly,
        "error": None,
    }


MINIMAL_CFG = {
    "buckets": {
        "agy-gemini": {"match": ["agy:gemini-"]},
        "agy-claude": {"match": ["agy:claude-"]},
        "codex": {"match": ["codex:"]},
        "claude": {"match": ["claude:"]},
    }
}

MINIMAL_LIMITS = {
    "agy-gemini": {"plan_usd": 100, "reserve_pct": 10, "min_5h_pct": 10},
    "agy-claude": {"plan_usd": 100, "reserve_pct": 10, "min_5h_pct": 10},
    "codex": {"plan_usd": 20, "reserve_pct": 20, "min_5h_pct": 0},
    "claude": {"plan_usd": 20, "reserve_pct": 50, "min_5h_pct": 30},
}


# ---------------------------------------------------------------------------
# Test: one job, simple delta
# ---------------------------------------------------------------------------

def test_one_job_simple_delta(tmp_path: Path, monkeypatch):
    """One job on agy-gemini, history 0.90 before and 0.88 after -> pct 2.0, n 1."""
    start = _utc(h=5)
    end = _utc(h=6)

    hist = _history_file(tmp_path, [
        _hist_row("agy-gemini", start - timedelta(minutes=5), 0.90),
        _hist_row("agy-gemini", end + timedelta(minutes=5), 0.88),
    ])
    monkeypatch.setattr(quota_mod, "DEFAULT_HISTORY", hist)

    job = {"id": "task-1", "bucket": "agy-gemini", "size": "M",
           "start": start, "end": end}

    table = cost_learn.learn(
        history_path=hist,
        jobs=[job],
        cfg=MINIMAL_CFG,
        limits=MINIMAL_LIMITS,
    )

    assert "agy-gemini" in table
    cell = table["agy-gemini"]["M"]
    assert cell["n"] == 1
    assert abs(cell["pct"] - 2.0) < 1e-6   # (0.90 - 0.88) * 100 = 2.0
    assert cell["plan_usd"] == 100.0


# ---------------------------------------------------------------------------
# Test: two overlapping jobs split the delta evenly
# ---------------------------------------------------------------------------

def test_two_overlapping_jobs_split_delta(tmp_path: Path, monkeypatch):
    """Two overlapping jobs on the same bucket share the delta evenly."""
    start_a = _utc(h=5)
    end_a = _utc(h=7)
    start_b = _utc(h=6)
    end_b = _utc(h=8)

    # History covers both windows.
    # before_a  = 5-5min=4:55  -> 0.90
    # after_a   = 7+5min=7:05  -> 0.80
    # before_b  = 6-5min=5:55  -> 0.87
    # after_b   = 8+5min=8:05  -> 0.78
    # delta_a = 0.90 - 0.80 = 0.10; delta_b = 0.87 - 0.78 = 0.09
    # overlap: a and b overlap each other -> split_count = 2
    # cost_a = 0.10 / 2 = 0.05; cost_b = 0.09 / 2 = 0.045
    hist = _history_file(tmp_path, [
        _hist_row("agy-gemini", _utc(h=4, m=55), 0.90),
        _hist_row("agy-gemini", _utc(h=5, m=55), 0.87),
        _hist_row("agy-gemini", _utc(h=7, m=5), 0.80),
        _hist_row("agy-gemini", _utc(h=8, m=5), 0.78),
    ])

    jobs = [
        {"id": "task-a", "bucket": "agy-gemini", "size": "M", "start": start_a, "end": end_a},
        {"id": "task-b", "bucket": "agy-gemini", "size": "M", "start": start_b, "end": end_b},
    ]

    table = cost_learn.learn(
        history_path=hist,
        jobs=jobs,
        cfg=MINIMAL_CFG,
        limits=MINIMAL_LIMITS,
    )

    assert "agy-gemini" in table
    cell = table["agy-gemini"]["M"]
    assert cell["n"] == 2
    # median of [0.05, 0.045] = 0.0475; pct = 4.75
    expected_pct = (0.05 + 0.045) / 2 * 100  # median of two = average of two
    assert abs(cell["pct"] - expected_pct) < 1e-4


# ---------------------------------------------------------------------------
# Test: reset inside window skips the job
# ---------------------------------------------------------------------------

def test_reset_inside_window_skips_job(tmp_path: Path, monkeypatch):
    """A weekly reset (rise > 0.02) between snapshots causes the job to be skipped."""
    start = _utc(h=5)
    end = _utc(h=7)

    # before=0.10, midpoint shows reset (rises to 0.95), after=0.93
    hist = _history_file(tmp_path, [
        _hist_row("agy-gemini", start - timedelta(minutes=5), 0.10),
        _hist_row("agy-gemini", _utc(h=6), 0.95),   # reset: 0.95 - 0.10 > 0.02
        _hist_row("agy-gemini", end + timedelta(minutes=5), 0.93),
    ])

    job = {"id": "task-1", "bucket": "agy-gemini", "size": "S",
           "start": start, "end": end}

    table = cost_learn.learn(
        history_path=hist,
        jobs=[job],
        cfg=MINIMAL_CFG,
        limits=MINIMAL_LIMITS,
    )

    # Job should be skipped entirely
    assert table == {}


# ---------------------------------------------------------------------------
# Test: claude-bucket jobs are never counted
# ---------------------------------------------------------------------------

def test_claude_bucket_never_counted(tmp_path: Path, monkeypatch):
    """Jobs on the claude bucket must be excluded."""
    start = _utc(h=5)
    end = _utc(h=6)

    hist = _history_file(tmp_path, [
        _hist_row("claude", start - timedelta(minutes=5), 0.80),
        _hist_row("claude", end + timedelta(minutes=5), 0.75),
    ])

    # Job explicitly on claude bucket
    job = {"id": "task-c", "bucket": "claude", "size": "M",
           "start": start, "end": end}

    table = cost_learn.learn(
        history_path=hist,
        jobs=[job],
        cfg=MINIMAL_CFG,
        limits=MINIMAL_LIMITS,
    )

    assert "claude" not in table
    assert table == {}


# ---------------------------------------------------------------------------
# Test: snapshot more than 20 min from window edge skips the job
# ---------------------------------------------------------------------------

def test_missing_snapshot_near_edge_skips_job(tmp_path: Path, monkeypatch):
    """When the nearest snapshot is > 20 min from the window edge, skip the job."""
    start = _utc(h=5)
    end = _utc(h=6)

    # "before" snapshot is 25 min before start -> too far
    hist = _history_file(tmp_path, [
        _hist_row("agy-gemini", start - timedelta(minutes=25), 0.90),
        _hist_row("agy-gemini", end + timedelta(minutes=5), 0.88),
    ])

    job = {"id": "task-1", "bucket": "agy-gemini", "size": "M",
           "start": start, "end": end}

    table = cost_learn.learn(
        history_path=hist,
        jobs=[job],
        cfg=MINIMAL_CFG,
        limits=MINIMAL_LIMITS,
    )

    assert table == {}


# ---------------------------------------------------------------------------
# Test: median over 5 jobs
# ---------------------------------------------------------------------------

def test_median_over_five_jobs(tmp_path: Path, monkeypatch):
    """Five jobs with different deltas produce the correct median pct."""
    # Costs (fraction): 0.01, 0.02, 0.03, 0.04, 0.05 -> median = 0.03 -> pct = 3.0
    jobs = []
    hist_rows = []
    for i, delta in enumerate([0.01, 0.02, 0.03, 0.04, 0.05]):
        base = _utc(h=i * 3)
        start = base
        end = base + timedelta(hours=1)
        jobs.append({
            "id": f"task-{i}",
            "bucket": "agy-gemini",
            "size": "M",
            "start": start,
            "end": end,
        })
        hist_rows.append(_hist_row("agy-gemini", start - timedelta(minutes=5), 0.90))
        hist_rows.append(_hist_row("agy-gemini", end + timedelta(minutes=5), round(0.90 - delta, 6)))

    hist = _history_file(tmp_path, hist_rows)

    table = cost_learn.learn(
        history_path=hist,
        jobs=jobs,
        cfg=MINIMAL_CFG,
        limits=MINIMAL_LIMITS,
    )

    assert "agy-gemini" in table
    cell = table["agy-gemini"]["M"]
    assert cell["n"] == 5
    assert abs(cell["pct"] - 3.0) < 1e-5  # median of [1,2,3,4,5]% = 3%


# ---------------------------------------------------------------------------
# Test: write_table round trip; forecast.cost_for returns "learned n=5"
# ---------------------------------------------------------------------------

def test_write_table_round_trip_and_cost_for(tmp_path: Path, monkeypatch):
    """write_table round trip, and tools.forecast.cost_for then returns source 'learned n=5'."""
    cost_table_path = tmp_path / "cost-table.json"
    monkeypatch.setattr(forecast, "COST_TABLE_PATH", cost_table_path)

    # Build a table with n=5 for agy-gemini/M at pct=2.5%
    table = {
        "agy-gemini": {
            "M": {"pct": 2.5, "n": 5, "plan_usd": 100.0}
        }
    }

    returned_path = cost_learn.write_table(table, path=cost_table_path)
    assert returned_path == cost_table_path
    assert cost_table_path.is_file()

    # Verify JSON round-trip
    loaded = json.loads(cost_table_path.read_text(encoding="utf-8"))
    assert loaded["agy-gemini"]["M"]["n"] == 5
    assert loaded["agy-gemini"]["M"]["pct"] == 2.5

    # forecast.cost_for should now use the learned cell
    limits = {"agy-gemini": {"plan_usd": 100, "reserve_pct": 10, "min_5h_pct": 10}}
    cost, source = forecast.cost_for("agy-gemini", "M", limits=limits)
    assert source == "learned n=5"
    assert abs(cost - 0.025) < 1e-9  # (2.5/100) * (100/100) = 0.025


# ---------------------------------------------------------------------------
# Test: --snapshot path keeps exit 0 when learn() raises
# ---------------------------------------------------------------------------

def test_snapshot_path_keeps_exit_0_when_learn_raises(
    tmp_path: Path,
    monkeypatch,
    capsys,
):
    """The --snapshot branch prints 'cost-learn skipped: ...' to stderr and exits 0 when learn() raises."""
    from tools.quota import Quota
    import tools.quota as quota_mod_ref

    snap_file = tmp_path / "snap.json"
    history_file = tmp_path / "hist.jsonl"

    four_buckets = {
        "agy-gemini": Quota(provider="agy-gemini", weekly_remaining=0.99, error=None),
        "agy-claude": Quota(provider="agy-claude", weekly_remaining=0.98, error=None),
        "codex": Quota(provider="codex", weekly_remaining=0.97, error=None),
        "claude": Quota(provider="claude", weekly_remaining=0.96, error=None),
    }

    monkeypatch.setattr(quota_mod_ref, "SNAPSHOT_PATH", snap_file)
    monkeypatch.setattr(quota_mod_ref, "DEFAULT_HISTORY", history_file)
    monkeypatch.setattr(quota_mod_ref, "load_plans", lambda path=None: {})
    monkeypatch.setattr(quota_mod_ref, "fetch_all_quotas", lambda cfg, now=None: four_buckets)
    monkeypatch.setattr(sys, "argv", ["quota.py", "--snapshot"])

    # Make cost_learn.learn raise an error
    def explode(*a, **kw):
        raise RuntimeError("simulated cost-learn failure")

    monkeypatch.setattr(cost_learn, "learn", explode)

    # Should not raise; should still exit cleanly
    quota_mod_ref.main()

    captured = capsys.readouterr()
    assert "snapshot:" in captured.out
    assert "cost-learn skipped:" in captured.err
    assert "simulated cost-learn failure" in captured.err
