"""Tests for quota buckets, parse_agy group selection, and bucket-based routing."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.quota import Quota, bucket_for, parse_agy
import tools.route as route
from tools.route import Choice, rank


def test_parse_agy_both_groups():
    fixture = {
        "command": {
            "data": {
                "groups": [
                    {
                        "name": "Gemini Models",
                        "buckets": [
                            {"window": "weekly", "remaining_fraction": 0.99, "reset_time": "2026-10-06T00:05:38Z"},
                            {"window": "5h", "remaining_fraction": 0.966, "reset_time": "2026-09-30T12:00:00Z"},
                        ],
                    },
                    {
                        "name": "Claude and GPT models",
                        "buckets": [
                            {"window": "weekly", "remaining_fraction": 1.0, "reset_time": "2026-10-06T00:05:38Z"},
                            {"window": "5h", "remaining_fraction": 1.0, "reset_time": "2026-09-30T12:00:00Z"},
                        ],
                    },
                ]
            }
        }
    }

    q_gemini = parse_agy(fixture, group="Gemini Models")
    assert q_gemini.provider == "agy-gemini"
    assert q_gemini.weekly_remaining == 0.99
    assert q_gemini.daily_remaining == 0.966
    assert q_gemini.error is None

    # Default group is Gemini Models
    q_default = parse_agy(fixture)
    assert q_default.provider == "agy-gemini"
    assert q_default.weekly_remaining == 0.99

    q_claude = parse_agy(fixture, group="Claude and GPT models")
    assert q_claude.provider == "agy-claude"
    assert q_claude.weekly_remaining == 1.0
    assert q_claude.daily_remaining == 1.0
    assert q_claude.error is None


def test_bucket_for_candidates():
    cfg = {
        "buckets": {
            "claude": {"provider": "anthropic", "match": ["claude:"]},
            "codex": {"provider": "openai", "match": ["codex:"]},
            "agy-gemini": {"provider": "google", "match": ["agy:gemini-"]},
            "agy-claude": {"provider": "google", "match": ["agy:claude-", "agy:gpt-"]},
        }
    }

    assert bucket_for("agy:gemini-3.8-flash-high", cfg) == "agy-gemini"
    assert bucket_for("agy:claude-sonnet-4-6", cfg) == "agy-claude"
    assert bucket_for("agy:gpt-oss-120b-medium", cfg) == "agy-claude"
    assert bucket_for("claude:claude-sonnet-5-5", cfg) == "claude"
    assert bucket_for("codex:sol:xhigh", cfg) == "codex"
    assert bucket_for("foo:bar", cfg) is None


def test_rank_picks_agy_claude_over_agy_gemini(monkeypatch):
    monkeypatch.setattr(route, "_host_runners", lambda host: ["agy"])
    cfg = {
        "buckets": {
            "claude": {"provider": "anthropic", "match": ["claude:"]},
            "codex": {"provider": "openai", "match": ["codex:"]},
            "agy-gemini": {"provider": "google", "match": ["agy:gemini-"]},
            "agy-claude": {"provider": "google", "match": ["agy:claude-", "agy:gpt-"]},
        },
        "roles": {
            "test_role": ["agy:gemini-3.8-flash-high", "agy:claude-sonnet-4-6"],
        },
        "router": {
            "tie_points": 5,
            "min_samples": 5,
        },
    }
    quotas = {
        "agy-gemini": Quota(provider="agy-gemini", weekly_remaining=0.50),
        "agy-claude": Quota(provider="agy-claude", weekly_remaining=0.90),
    }

    choices = rank("test_role", quotas, {}, "mac", cfg)
    assert len(choices) == 2
    assert choices[0].candidate == "agy:claude-sonnet-4-6"
    assert choices[0].bucket == "agy-claude"
    assert choices[0].weekly == 0.90
    assert choices[1].candidate == "agy:gemini-3.8-flash-high"
    assert choices[1].bucket == "agy-gemini"
    assert choices[1].weekly == 0.50
    assert "highest weekly remaining" in choices[0].reason
    assert "90.0% agy-claude vs 50.0% agy-gemini" in choices[0].reason
