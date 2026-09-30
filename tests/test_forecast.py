"""Tests for tools/forecast.py.

Covers:
- infer_size edges
- cost_for seed scaling with plan_usd changes (claude plan_usd 200 makes M 0.8%)
- cost_for learned cell with n=4 ignored and n=5 used
- verdict ok / will_hit on reserve / will_hit on 5h / unknown
- burn_rate across a reset (rise > 0.02)
- projection formatting and reset comparison
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

from tools import forecast
from tools.quota import Quota


def test_infer_size_edges():
    # S: len(touches) <= 2 and len(brief) < 1500
    assert forecast.infer_size(None, None) == "S"
    assert forecast.infer_size([], "") == "S"
    assert forecast.infer_size(["a", "b"], "x" * 1499) == "S"

    # M: touches <= 2 but brief == 1500
    assert forecast.infer_size(["a", "b"], "x" * 1500) == "M"

    # M: touches == 3 and brief < 1500
    assert forecast.infer_size(["a", "b", "c"], "x" * 500) == "M"

    # M boundary: touches == 6 and brief == 6000
    assert forecast.infer_size(["a"] * 6, "x" * 6000) == "M"

    # L: touches > 6
    assert forecast.infer_size(["a"] * 7, "short") == "L"

    # L: brief > 6000
    assert forecast.infer_size(["a"], "x" * 6001) == "L"

    # L: both > 6 and > 6000
    assert forecast.infer_size(["a"] * 8, "x" * 6500) == "L"


def test_seed_scaling_when_plan_usd_changes():
    # Base limits: claude plan_usd: 20
    limits_base = {"claude": {"plan_usd": 20, "reserve_pct": 50, "min_5h_pct": 30}}
    cost_m_base, src_base = forecast.cost_for("claude", "M", limits=limits_base, table={})
    assert src_base == "seed"
    # Seed M for claude is 8% -> 0.08
    assert cost_m_base == pytest.approx(0.08)

    # When plan_usd changes to 200: (8 / 100) * (20 / 200) = 0.008 (0.8%)
    limits_scaled = {"claude": {"plan_usd": 200, "reserve_pct": 50, "min_5h_pct": 30}}
    cost_m_scaled, src_scaled = forecast.cost_for("claude", "M", limits=limits_scaled, table={})
    assert src_scaled == "seed"
    assert cost_m_scaled == pytest.approx(0.008)
    assert forecast.fmt_pct(cost_m_scaled * 100) == "0.8%"

    # Unknown bucket
    cost_unknown, src_unknown = forecast.cost_for("unknown", "M", limits=limits_base)
    assert cost_unknown is None
    assert src_unknown == "no cost data"


def test_learned_cell_n4_ignored_n5_used(tmp_path, monkeypatch):
    limits = {"claude": {"plan_usd": 20, "reserve_pct": 50, "min_5h_pct": 30}}

    # Learned table with n=4: ignored, fallback to seed
    table_n4 = {
        "claude": {
            "M": {"pct": 12.0, "n": 4, "plan_usd": 20}
        }
    }
    cost, src = forecast.cost_for("claude", "M", limits=limits, table=table_n4)
    assert src == "seed"
    assert cost == pytest.approx(0.08)

    # Learned table with n=5: used
    table_n5 = {
        "claude": {
            "M": {"pct": 12.0, "n": 5, "plan_usd": 20}
        }
    }
    cost5, src5 = forecast.cost_for("claude", "M", limits=limits, table=table_n5)
    assert src5 == "learned n=5"
    assert cost5 == pytest.approx(0.12)

    # Read from COST_TABLE_PATH file
    cost_table_file = tmp_path / "cost-table.json"
    cost_table_file.write_text(json.dumps(table_n5), encoding="utf-8")
    monkeypatch.setattr(forecast, "COST_TABLE_PATH", cost_table_file)

    cost_file, src_file = forecast.cost_for("claude", "M", limits=limits)
    assert src_file == "learned n=5"
    assert cost_file == pytest.approx(0.12)

    # Missing or broken cost table file -> seeds only, never raises
    monkeypatch.setattr(forecast, "COST_TABLE_PATH", tmp_path / "broken.json")
    (tmp_path / "broken.json").write_text("invalid json...", encoding="utf-8")
    cost_broken, src_broken = forecast.cost_for("claude", "M", limits=limits)
    assert src_broken == "seed"
    assert cost_broken == pytest.approx(0.08)


def test_verdict_cases():
    limit_row = {"plan_usd": 20, "reserve_pct": 50, "min_5h_pct": 30}

    # 1. OK: weekly 0.98, cost 0.01, reserve 10%
    q_ok = Quota(provider="agy-gemini", weekly_remaining=0.987, daily_remaining=0.975)
    limit_ok = {"plan_usd": 100, "reserve_pct": 10, "min_5h_pct": 10}
    v, after, why = forecast.verdict(q_ok, 0.01, limit_ok)
    assert v == "ok"
    assert after == pytest.approx(0.977)
    assert why == "reserve 10% ok"

    # 2. will_hit on reserve: after 45% < reserve 50%
    q_res = Quota(provider="claude", weekly_remaining=0.53, daily_remaining=0.40)
    v_res, after_res, why_res = forecast.verdict(q_res, 0.08, limit_row)
    assert v_res == "will_hit"
    assert after_res == pytest.approx(0.45)
    assert why_res == "after 45% < reserve 50%"

    # 3. will_hit on 5h: daily 0.08 (8%) < min 30%
    q_5h = Quota(provider="claude", weekly_remaining=0.67, daily_remaining=0.08)
    v_5h, after_5h, why_5h = forecast.verdict(q_5h, 0.08, limit_row)
    assert v_5h == "will_hit"
    assert after_5h == pytest.approx(0.59)
    assert why_5h == "5h 8% < min 30%"

    # 4. Unknown cases: q is None, q.error, weekly is None, cost is None
    assert forecast.verdict(None, 0.05, limit_row)[0] == "unknown"
    assert forecast.verdict(Quota(provider="claude", error="network failure"), 0.05, limit_row)[0] == "unknown"
    assert forecast.verdict(Quota(provider="claude", weekly_remaining=None), 0.05, limit_row)[0] == "unknown"
    assert forecast.verdict(q_ok, None, limit_row)[0] == "unknown"


def test_burn_rate_across_reset(tmp_path):
    history_file = tmp_path / "quota-history.jsonl"
    now = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc)

    # 3 lines:
    # 1. 10 hours ago: 0.20
    # 2. 5 hours ago: 0.90 (rose by 0.70 > 0.02 -> reset point)
    # 3. now: 0.80 (5 hours after reset, drop of 0.10)
    t1 = now - timedelta(hours=10)
    t2 = now - timedelta(hours=5)
    t3 = now

    lines = [
        {"provider": "claude", "ts": t1.isoformat(), "weekly_remaining": 0.20, "error": None},
        {"provider": "claude", "ts": t2.isoformat(), "weekly_remaining": 0.90, "error": None},
        {"provider": "claude", "ts": t3.isoformat(), "weekly_remaining": 0.80, "error": None},
    ]
    history_file.write_text("\n".join(json.dumps(l) for l in lines) + "\n", encoding="utf-8")

    # Points kept should only be t2 and t3 (after the reset).
    # Drop is 0.90 - 0.80 = 0.10 over 5 hours.
    # Rate = 0.10 / 5 * 24 = 0.48 per day.
    rate = forecast.burn_rate("claude", history_path=history_file, now=now, window_h=24)
    assert rate == pytest.approx(0.48)

    # If span is < 1 hour: returns None
    short_file = tmp_path / "short.jsonl"
    short_lines = [
        {"provider": "claude", "ts": (now - timedelta(minutes=30)).isoformat(), "weekly_remaining": 0.90, "error": None},
        {"provider": "claude", "ts": now.isoformat(), "weekly_remaining": 0.89, "error": None},
    ]
    short_file.write_text("\n".join(json.dumps(l) for l in short_lines) + "\n", encoding="utf-8")
    assert forecast.burn_rate("claude", history_path=short_file, now=now) is None


def test_projection():
    now = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc)
    q = Quota(
        provider="claude",
        weekly_remaining=0.70,
        weekly_resets_at="2026-10-06T12:00:00+00:00",
    )

    # rate None or 0 -> None
    assert forecast.projection("claude", q, None, 50, now=now) is None
    assert forecast.projection("claude", q, 0.0, 50, now=now) is None

    # weekly 0.70, reserve 50% (0.50), rate 0.10/day -> days = 0.20 / 0.10 = 2 days
    # reach date: 2026-10-02 (before reset 10-06)
    proj1 = forecast.projection("claude", q, 0.10, 50, now=now)
    assert proj1 == "reaches reserve 2026-10-02, before reset 10-06"

    # weekly 0.70, reserve 50% (0.50), rate 0.02/day -> days = 0.20 / 0.02 = 10 days
    # reach date: 2026-10-10 (after reset 10-06)
    proj2 = forecast.projection("claude", q, 0.02, 50, now=now)
    assert proj2 == "holds past reset 10-06"
