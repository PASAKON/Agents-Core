"""router.order: ceo (CEO 16 Oct): Argon until its quota is spent, then Codex (ChatGPT), Claude last.

With order "ceo" the roles list order decides, not the weekly quota left. A candidate is passed over only
when its bucket is exhausted or the job would take it under its reserve (verdict will_hit); Claude stays
last through the pressure rule. Order "fullest" (the default) keeps the old most-quota-left-first rule.
"""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.quota import Quota, load_plans  # noqa: E402
import tools.route as route  # noqa: E402
from tools.route import pick_runner, plan  # noqa: E402

LIMITS = {
    "claude": {"plan_usd": 20, "reserve_pct": 50, "min_5h_pct": 30},
    "agy-gemini": {"plan_usd": 100, "reserve_pct": 10, "min_5h_pct": 10},
    "codex": {"plan_usd": 20, "reserve_pct": 20, "min_5h_pct": 0},
}
ARGON, CODEX, SONNET = "agy:gemini-4-argon-high", "codex:", "claude:claude-sonnet-5-5"


@pytest.fixture
def cfg():
    return {
        "pressure_rule": True,
        "shell_runners": ["claude", "codex"],
        "buckets": {
            "claude": {"provider": "anthropic", "match": ["claude:"]},
            "codex": {"provider": "openai", "match": ["codex:"]},
            "agy-gemini": {"provider": "google", "match": ["agy:gemini-"]},
        },
        "roles": {"analysis": [ARGON, CODEX, SONNET]},
        "role_classes": {"data_analyst": "analysis"},
        "router": {"order": "ceo", "tie_points": 5, "min_samples": 5},
    }


@pytest.fixture(autouse=True)
def _hosts(monkeypatch):
    monkeypatch.setattr(route, "_host_runners", lambda host: ["claude", "agy", "codex"])


def _quotas(agy, codex=1.0, claude=1.0):
    return {"claude": Quota(provider="claude", weekly_remaining=claude, daily_remaining=1.0),
            "codex": Quota(provider="codex", weekly_remaining=codex, daily_remaining=1.0),
            "agy-gemini": Quota(provider="agy-gemini", weekly_remaining=agy, daily_remaining=1.0)}


def _order(cfg, quotas):
    plans = plan("data_analyst", size="M", host="contabo", cfg=cfg, quotas=quotas, skill={}, limits=LIMITS)
    return [p.choice.runner for p in plans]


def test_argon_first_while_codex_has_more_left(cfg):
    assert _order(cfg, _quotas(agy=0.42, codex=1.0)) == ["agy", "codex", "claude"]
    choice = pick_runner("data_analyst", "contabo", size="M", cfg=cfg, quotas=_quotas(agy=0.42), skill={},
                         limits=LIMITS)
    assert choice.runner == "agy", choice.reason
    assert route.rank("analysis", _quotas(agy=0.42), {}, host="contabo", cfg=cfg)[0].reason.startswith("CEO order #1")


def test_codex_once_argon_is_spent(cfg):
    assert _order(cfg, _quotas(agy=0.0))[:2] == ["codex", "claude"]
    assert _order(cfg, _quotas(agy=0.05))[0] == "codex"  # this job would take Argon under its reserve


def test_claude_last_even_when_fullest(cfg):
    assert _order(cfg, _quotas(agy=0.3, codex=0.3, claude=1.0))[-1] == "claude"


def test_fullest_keeps_the_old_rule(cfg):
    cfg["router"]["order"] = "fullest"
    assert _order(cfg, _quotas(agy=0.42, codex=1.0))[0] == "codex"


def test_live_plans_yaml_runs_argon_codex_claude():
    cfg = load_plans()
    assert cfg["router"]["order"] == "ceo"
    for cls in ("tests_edit", "analysis", "doc_text"):
        cands = cfg["roles"][cls]
        assert cands[0] == ARGON, cls
        assert cands.index(CODEX) < cands.index(SONNET) == len(cands) - 1, cls
