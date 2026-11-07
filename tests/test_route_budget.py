"""Budget is a soft partition over CEO ordering."""
import pytest
from datetime import datetime, timezone

from tools import route
from tools.quota import Quota


@pytest.fixture
def cfg():
    return {"roles": {"analysis": ["agy:gemini-test", "codex:", "claude:test"]},
            "buckets": {"agy-gemini": {"match": ["agy:"]}, "codex": {"match": ["codex:"]},
                        "claude": {"match": ["claude:"], "provider": "anthropic"}},
            "role_classes": {"analysis": "analysis"}, "router": {"order": "budget"}}


def quotas():
    return {b: Quota(b, weekly_remaining=.8, daily_remaining=1) for b in ("agy-gemini", "codex", "claude")}


def rows(states):
    return {b: {"bucket": b, "state": state, "used": .21, "target": .18}
            for b, state in zip(("agy-gemini", "codex", "claude"), states)}


@pytest.mark.parametrize("states,expected", [
    (("over", "under", "unknown"), ["codex", "agy", "claude"]),
    (("over", "under", "under"), ["codex", "agy", "claude"]),
    (("over", "over", "over"), ["agy", "codex", "claude"]),
])
def test_budget_order(cfg, states, expected):
    choices = route.rank("analysis", quotas(), {}, cfg=cfg, budget=rows(states))
    assert [c.runner for c in choices] == expected
    assert "over today's target (used 21% / 18%)" in next(c.reason for c in choices if c.runner == "agy")


def test_none_is_ceo_and_fullest_unaffected(cfg):
    ranked = route.rank("analysis", quotas(), {}, cfg=cfg)
    cfg["router"]["order"] = "ceo"
    assert ranked == route.rank("analysis", quotas(), {}, cfg=cfg)
    cfg["router"]["order"] = "fullest"
    assert route.rank("analysis", quotas(), {}, cfg=cfg) == route.rank(
        "analysis", quotas(), {}, cfg=cfg, budget=rows(("over", "under", "under")))


def test_exhausted_stays_last(cfg):
    qs = quotas()
    qs["codex"].weekly_remaining = 0
    choices = route.rank("analysis", qs, {}, cfg=cfg, budget=rows(("over", "under", "unknown")))
    assert [c.runner for c in choices] == ["agy", "claude", "codex"]


def test_plan_and_pick_use_budget_despite_pressure(cfg, monkeypatch):
    monkeypatch.setattr(route, "_host_runners", lambda host: ["agy", "codex", "claude"])
    monkeypatch.setattr(route.usage_budget, "load_rows", lambda **kw: rows(("over", "over", "under")))
    limits = {b: {"reserve_pct": 0, "min_5h_pct": 0} for b in quotas()}
    kwargs = dict(cfg=cfg, quotas=quotas(), skill={}, limits=limits, size="M")
    # AGY and Codex over target, Claude under: still an outside runner, never Claude (CEO item 4).
    assert route.plan("analysis", **kwargs)[0].choice.runner == "agy"
    assert route.pick_runner("analysis", "test", **kwargs).runner == "agy"
    monkeypatch.setattr(route.usage_budget, "load_rows", lambda **kw: rows(("over", "under", "under")))
    assert route.plan("analysis", **kwargs)[0].choice.runner == "codex"
    assert route.plan("analysis", **kwargs)[-1].choice.runner == "claude"


@pytest.mark.parametrize("tier,headroom,rate,deferred", [
    ("normal", -.017, .05, False),  # 78% left lasts beyond the November 13 reset.
    ("normal", -.20, .20, True),
    ("normal", -.20, .05, False),  # A holding forecast takes precedence.
    ("low", -.017, .05, True),
    ("low", -.20, .20, True),
    ("normal", None, None, False),
    ("normal", -.017, None, False),
    ("normal", -.05, None, False),
    ("normal", -.051, None, True),
])
def test_shell_tier_weekly_gate(cfg, monkeypatch, tier, headroom, rate, deferred):
    budget = rows(("over", "over", "under"))
    for row in budget.values():
        row["headroom"] = headroom
    monkeypatch.setattr(route, "_host_runners", lambda host: ["agy", "codex", "claude"])
    monkeypatch.setattr(route.usage_budget, "load_rows", lambda **kw: budget)
    monkeypatch.setattr(route.usage_budget, "load_gate_rows", lambda **kw: budget)
    monkeypatch.setattr(route.forecast, "burn_rate", lambda *a, **kw: rate)
    monkeypatch.setattr(route.forecast, "cost_for", lambda *a, **kw: (.01, "test"))
    qs = quotas()
    for q in qs.values():
        q.weekly_remaining = .78
        q.weekly_resets_at = "2026-11-13T00:00:00Z"
    choice = route.pick_runner(
        "analysis", "test", cfg=cfg, quotas=qs, skill={}, size="M", tier=tier,
        needs_shell=True, now=datetime(2026, 11, 7, tzinfo=timezone.utc),
        limits={b: {"reserve_pct": 0, "min_5h_pct": 0} for b in qs})
    assert choice is not None
    assert choice.defer == deferred
    if not deferred:
        assert choice.runner == "codex"
