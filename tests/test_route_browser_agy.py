"""GH #188 step 6: a browser_operator runs on agy only when its brief uses
tools/agy_browse.py and carries the Browser Home CDP URL. Every other browser
task stays on Claude (no routing at all)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.route as route  # noqa: E402
from tools.quota import Quota, load_plans  # noqa: E402

AGY_BRIEF = (
    "Read the champa page state. Browser Home: http://127.0.0.1:9280 (champa). "
    "Use only `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python tools/agy_browse.py --port 9280 <verb>`."
)


@pytest.fixture
def cfg():
    return {
        "providers": {"anthropic": {"runner": "claude"}, "google": {"runner": "agy"}},
        "buckets": {
            "claude": {"provider": "anthropic", "match": ["claude:"]},
            "agy-gemini": {"provider": "google", "match": ["agy:gemini-"]},
        },
        "roles": {
            "dev_general": ["agy:gemini-3.8-flash-high", "claude:claude-sonnet-5-5"],
            "browser_agy": ["agy:gemini-3.8-flash-high"],
        },
        "role_classes": {"developer": "dev_general"},
        "router": {"tie_points": 5, "min_samples": 5},
    }


@pytest.fixture
def quotas():
    return {
        "agy-gemini": Quota(provider="agy-gemini", weekly_remaining=0.9, daily_remaining=0.9),
        "claude": Quota(provider="claude", weekly_remaining=0.5, daily_remaining=0.5),
    }


@pytest.mark.parametrize("brief,expected", [
    (AGY_BRIEF, "browser_agy"),
    ("Log in with claude-in-chrome and read the page.", None),
    ("Use tools/agy_browse.py (the Home URL will follow).", None),         # no CDP URL
    ("Browser Home http://127.0.0.1:9280, drive it with claude-in-chrome.", None),
    ("See mytools/agy_browse.py and http://127.0.0.1:9280", None),          # not the repo tool
    (None, None),
])
def test_class_for_browser_operator(cfg, brief, expected):
    assert route.class_for("browser_operator", brief, cfg) == expected


def test_other_browser_roles_never_route(cfg):
    assert route.class_for("web_designer", AGY_BRIEF, cfg) is None


def test_developer_is_unchanged(cfg):
    assert route.class_for("developer", None, cfg) == "dev_general"


def test_pick_runner_sends_an_agy_browse_brief_to_agy(cfg, quotas, monkeypatch):
    monkeypatch.setattr(route, "_host_runners", lambda host: ["claude", "agy"])
    choice = route.pick_runner("browser_operator", "mac", brief=AGY_BRIEF, cfg=cfg, quotas=quotas, skill={})
    assert choice is not None and choice.runner == "agy" and choice.model == "gemini-3.8-flash-high"


def test_pick_runner_leaves_a_plain_browser_brief_on_claude(cfg, quotas, monkeypatch):
    monkeypatch.setattr(route, "_host_runners", lambda host: ["claude", "agy"])
    assert route.pick_runner("browser_operator", "mac", brief="use claude-in-chrome", cfg=cfg,
                             quotas=quotas, skill={}) is None


def test_real_plans_yaml_has_the_class_and_keeps_browser_roles_out_of_role_classes():
    real = load_plans()
    assert real["roles"]["browser_agy"] == ["agy:gemini-3.8-flash-high"]
    assert "browser_operator" not in (real.get("role_classes") or {})
