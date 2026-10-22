"""Budget is a soft partition over CEO ordering."""
import pytest

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
