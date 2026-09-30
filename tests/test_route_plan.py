"""Tests for route.plan, plan_line, and pick_runner with forecast integration.

Covers:
- plan() ordering: ok candidates first, will_hit last
- claude weekly 0.67 daily 0.08 (will_hit 5h 8% < min 30%) and agy-gemini 0.987/0.975 (ok)
- plan_line formatting for ok and will_hit
- pick_runner fallback prefixing "no ok candidate, fallback: " when all candidates will_hit
- unmapped role returns []
- CLI --plan prints plan lines and projections
"""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.quota import Quota
import tools.route as route
from tools.route import Plan, Choice, plan, plan_line, pick_runner


@pytest.fixture
def mock_cfg():
    return {
        "providers": {
            "anthropic": {"runner": "claude"},
            "google": {"runner": "agy"},
        },
        "buckets": {
            "claude": {"provider": "anthropic", "match": ["claude:"]},
            "agy-gemini": {"provider": "google", "match": ["agy:gemini-"]},
        },
        "roles": {
            "dev_general": ["claude:claude-sonnet-5-5", "agy:gemini-3.8-flash-high"],
        },
        "role_classes": {
            "developer": "dev_general",
        },
        "router": {
            "tie_points": 5,
            "min_samples": 5,
        },
    }


@pytest.fixture
def default_limits():
    return {
        "claude": {"plan_usd": 20, "reserve_pct": 50, "min_5h_pct": 30},
        "agy-gemini": {"plan_usd": 100, "reserve_pct": 10, "min_5h_pct": 10},
    }


def test_plan_claude_will_hit_5h_and_agy_ok(mock_cfg, default_limits, monkeypatch):
    monkeypatch.setattr(route, "_host_runners", lambda host: ["claude", "agy"])

    quotas = {
        "claude": Quota(provider="claude", weekly_remaining=0.67, daily_remaining=0.08),
        "agy-gemini": Quota(provider="agy-gemini", weekly_remaining=0.987, daily_remaining=0.975),
    }

    plans = plan(
        "developer",
        size="M",
        host="mac",
        cfg=mock_cfg,
        quotas=quotas,
        skill={},
        limits=default_limits,
    )

    assert len(plans) == 2

    # agy is ok first, even though roles listed claude first
    p_agy = plans[0]
    assert p_agy.choice.runner == "agy"
    assert p_agy.choice.model == "gemini-3.8-flash-high"
    assert p_agy.verdict == "ok"
    assert p_agy.why == "reserve 10% ok"
    assert p_agy.after == pytest.approx(0.977)

    # claude is will_hit last with 5h 8% < min 30%
    p_claude = plans[1]
    assert p_claude.choice.runner == "claude"
    assert p_claude.choice.model == "claude-sonnet-5-5"
    assert p_claude.verdict == "will_hit"
    assert p_claude.why == "5h 8% < min 30%"
    assert p_claude.after == pytest.approx(0.59)

    # Check plan_line formatting
    agy_line = plan_line(p_agy)
    assert agy_line == "agy gemini-3.8-flash-high · bucket agy-gemini 98.7%→97.7% (M ≈1%) reserve 10% ok"

    claude_line = plan_line(p_claude)
    assert claude_line == "claude claude-sonnet-5-5 · bucket claude 67%→59% (M ≈8%) will_hit: 5h 8% < min 30%"


def test_pick_runner_fallback_when_all_will_hit(mock_cfg, default_limits, monkeypatch):
    monkeypatch.setattr(route, "_host_runners", lambda host: ["claude", "agy"])

    # Both will hit reserve: claude after 42% < 50%, agy after 5% < 10%
    quotas = {
        "claude": Quota(provider="claude", weekly_remaining=0.50, daily_remaining=0.50),
        "agy-gemini": Quota(provider="agy-gemini", weekly_remaining=0.06, daily_remaining=0.50),
    }

    plans = plan(
        "developer",
        size="M",
        host="mac",
        cfg=mock_cfg,
        quotas=quotas,
        skill={},
        limits=default_limits,
    )
    assert len(plans) == 2
    assert all(p.verdict == "will_hit" for p in plans)

    choice = pick_runner(
        "developer",
        "mac",
        size="M",
        cfg=mock_cfg,
        quotas=quotas,
        skill={},
        limits=default_limits,
    )
    assert choice is not None
    assert choice.runner == "claude"
    assert choice.reason.startswith("no ok candidate, fallback: ")


def test_plan_unmapped_role_returns_empty(mock_cfg):
    assert plan("unmapped_role", cfg=mock_cfg) == []


def test_cli_plan(mock_cfg, default_limits, monkeypatch, capsys):
    monkeypatch.setattr(route, "_host_runners", lambda host: ["claude", "agy"])
    monkeypatch.setattr(route, "load_plans", lambda path=None: mock_cfg)
    quotas = {
        "claude": Quota(provider="claude", weekly_remaining=0.67, daily_remaining=0.08),
        "agy-gemini": Quota(provider="agy-gemini", weekly_remaining=0.987, daily_remaining=0.975),
    }
    monkeypatch.setattr(route, "cached_quotas", lambda cfg: quotas)
    monkeypatch.setattr(route, "load_skill_scores", lambda: {})
    monkeypatch.setattr(route.limits_mod, "load_limits", lambda path=None: default_limits)

    monkeypatch.setattr(sys, "argv", ["route.py", "--plan", "dev_general", "--size", "M", "--host", "mac"])
    route.main()

    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) >= 2
    assert out[0].startswith("1. agy gemini-3.8-flash-high")
    assert "reserve 10% ok" in out[0]
    assert out[1].startswith("2. claude claude-sonnet-5-5")
    assert "will_hit: 5h 8% < min 30%" in out[1]
