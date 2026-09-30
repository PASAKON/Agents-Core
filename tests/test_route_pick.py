"""Tests for route.pick_runner and route.cached_quotas.

Covers:
- agy weekly 0.99, claude weekly 0.50 -> runner == "agy"
- agy weekly 0.0 (exhausted), claude 0.50 -> runner == "claude"
- both weekly 0.0 -> None
- role "browser_operator" (not in role_classes) -> None, and rank is never called
- rank raising -> None (no exception escapes)
- _host_runners returning ["claude"] only -> runner == "claude"
- cached_quotas TTL behaviour and cache reset
- CLI --pick flag output
"""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.quota
from tools.quota import Quota
import tools.route as route
from tools.route import Choice, cached_quotas, pick_runner


@pytest.fixture
def mock_cfg():
    return {
        "providers": {
            "anthropic": {"runner": "claude"},
            "google": {"runner": "agy"},
            "openai": {"runner": "codex"},
        },
        "buckets": {
            "claude": {"provider": "anthropic", "match": ["claude:"]},
            "codex": {"provider": "openai", "match": ["codex:"]},
            "agy-gemini": {"provider": "google", "match": ["agy:gemini-"]},
            "agy-claude": {"provider": "google", "match": ["agy:claude-", "agy:gpt-"]},
        },
        "roles": {
            "dev_general": ["agy:gemini-3.8-flash-high", "claude:claude-sonnet-5"],
        },
        "role_classes": {
            "developer": "dev_general",
        },
        "router": {
            "tie_points": 5,
            "min_samples": 5,
        },
    }


def test_pick_runner_agy_beats_claude(mock_cfg, monkeypatch):
    monkeypatch.setattr(route, "_host_runners", lambda host: ["claude", "agy"])
    quotas = {
        "agy-gemini": Quota(provider="agy-gemini", weekly_remaining=0.99, daily_remaining=0.90),
        "claude": Quota(provider="claude", weekly_remaining=0.50, daily_remaining=0.50),
    }
    choice = pick_runner("developer", "mac", cfg=mock_cfg, quotas=quotas, skill={})
    assert choice is not None
    assert choice.runner == "agy"
    assert choice.model == "gemini-3.8-flash-high"
    assert choice.bucket == "agy-gemini"


def test_pick_runner_agy_exhausted_claude_selected(mock_cfg, monkeypatch):
    monkeypatch.setattr(route, "_host_runners", lambda host: ["claude", "agy"])
    quotas = {
        "agy-gemini": Quota(provider="agy-gemini", weekly_remaining=0.0, daily_remaining=0.50),
        "claude": Quota(provider="claude", weekly_remaining=0.50, daily_remaining=0.50),
    }
    choice = pick_runner("developer", "mac", cfg=mock_cfg, quotas=quotas, skill={})
    assert choice is not None
    assert choice.runner == "claude"
    assert choice.model == "claude-sonnet-5"
    assert choice.bucket == "claude"


def test_pick_runner_both_exhausted_returns_none(mock_cfg, monkeypatch):
    monkeypatch.setattr(route, "_host_runners", lambda host: ["claude", "agy"])
    quotas = {
        "agy-gemini": Quota(provider="agy-gemini", weekly_remaining=0.0, daily_remaining=0.50),
        "claude": Quota(provider="claude", weekly_remaining=0.0, daily_remaining=0.50),
    }
    choice = pick_runner("developer", "mac", cfg=mock_cfg, quotas=quotas, skill={})
    assert choice is None


def test_pick_runner_unmapped_role_never_calls_rank(mock_cfg, monkeypatch):
    monkeypatch.setattr(route, "_host_runners", lambda host: ["claude", "agy"])

    def bad_rank(*args, **kwargs):
        raise AssertionError("rank should never be called for an unmapped role")

    monkeypatch.setattr(route, "rank", bad_rank)
    choice = pick_runner("browser_operator", "mac", cfg=mock_cfg, quotas={}, skill={})
    assert choice is None


def test_pick_runner_rank_exception_returns_none(mock_cfg, monkeypatch):
    monkeypatch.setattr(route, "_host_runners", lambda host: ["claude", "agy"])

    def bad_rank(*args, **kwargs):
        raise RuntimeError("simulated rank crash")

    monkeypatch.setattr(route, "rank", bad_rank)
    choice = pick_runner("developer", "mac", cfg=mock_cfg, quotas={}, skill={})
    assert choice is None


def test_pick_runner_host_runners_claude_only(mock_cfg, monkeypatch):
    monkeypatch.setattr(route, "_host_runners", lambda host: ["claude"])
    quotas = {
        "agy-gemini": Quota(provider="agy-gemini", weekly_remaining=0.99, daily_remaining=0.90),
        "claude": Quota(provider="claude", weekly_remaining=0.50, daily_remaining=0.50),
    }
    choice = pick_runner("developer", "mac", cfg=mock_cfg, quotas=quotas, skill={})
    assert choice is not None
    assert choice.runner == "claude"
    assert choice.model == "claude-sonnet-5"
    assert choice.bucket == "claude"


def test_cached_quotas_ttl(mock_cfg, monkeypatch, tmp_path):
    monkeypatch.setattr(tools.quota, "SNAPSHOT_PATH", tmp_path / "nonexistent.json")
    route._quota_cache.clear()
    fetch_count = 0

    def mock_fetch(cfg):
        nonlocal fetch_count
        fetch_count += 1
        return {
            "claude": Quota(provider="claude", weekly_remaining=0.50),
            "codex": Quota(provider="codex", weekly_remaining=0.70),
            "agy-gemini": Quota(provider="agy-gemini", weekly_remaining=0.99),
            "agy-claude": Quota(provider="agy-claude", weekly_remaining=1.0),
        }

    monkeypatch.setattr(route, "fetch_all_quotas", mock_fetch)

    # Initial fetch at now=100.0: should fetch once
    res1 = cached_quotas(mock_cfg, now=100.0)
    assert fetch_count == 1
    assert res1["agy-gemini"].weekly_remaining == 0.99

    # Cache hit within TTL (300s): 399.0 - 100.0 = 299.0 < 300
    res2 = cached_quotas(mock_cfg, now=399.0)
    assert fetch_count == 1
    assert res2 is res1

    # Cache expired after TTL: 401.0 - 100.0 = 301.0 >= 300
    res3 = cached_quotas(mock_cfg, now=401.0)
    assert fetch_count == 2


def test_cached_quotas_failed_read_expires_in_retry_window(mock_cfg, monkeypatch, tmp_path):
    monkeypatch.setattr(tools.quota, "SNAPSHOT_PATH", tmp_path / "nonexistent.json")
    route._quota_cache.clear()
    fetch_count = 0

    def mock_fetch(cfg):
        nonlocal fetch_count
        fetch_count += 1
        return {
            "claude": Quota(provider="claude", weekly_remaining=0.50),
            "codex": Quota(provider="codex", weekly_remaining=0.70),
            "agy-gemini": Quota(provider="agy-gemini", error="timed out after 30 seconds"),
            "agy-claude": Quota(provider="agy-claude", error="timed out after 30 seconds"),
        }

    monkeypatch.setattr(route, "fetch_all_quotas", mock_fetch)

    cached_quotas(mock_cfg, now=100.0)
    cached_quotas(mock_cfg, now=100.0 + route.QUOTA_RETRY_S - 1)
    assert fetch_count == 1
    cached_quotas(mock_cfg, now=100.0 + route.QUOTA_RETRY_S + 1)
    assert fetch_count == 2


def test_cli_pick_success(mock_cfg, monkeypatch, capsys):
    monkeypatch.setattr(route, "_host_runners", lambda host: ["claude", "agy"])
    monkeypatch.setattr(route, "load_plans", lambda path=None: mock_cfg)
    quotas = {
        "agy-gemini": Quota(provider="agy-gemini", weekly_remaining=0.99, daily_remaining=0.90),
        "claude": Quota(provider="claude", weekly_remaining=0.50, daily_remaining=0.50),
    }
    monkeypatch.setattr(route, "cached_quotas", lambda cfg: quotas)
    monkeypatch.setattr(route, "load_skill_scores", lambda: {})
    monkeypatch.setattr(sys, "argv", ["route.py", "--pick", "developer", "--host", "mac"])
    route.main()
    out = capsys.readouterr().out.strip()
    assert out.startswith("runner=agy model=gemini-3.8-flash-high reason=")


def test_cli_pick_none(mock_cfg, monkeypatch, capsys):
    monkeypatch.setattr(route, "load_plans", lambda path=None: mock_cfg)
    monkeypatch.setattr(sys, "argv", ["route.py", "--pick", "browser_operator", "--host", "mac"])
    route.main()
    out = capsys.readouterr().out.strip()
    assert out == "runner=none (stay on claude)"
