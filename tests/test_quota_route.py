"""Tests for quota reader and runner router (Phase 2, part 1).

Covers:
- Parser fixtures for all three runners (Claude, Codex, agy)
- Codex with primary weekly + secondary 300-min daily, and last rate_limits not on last line
- Broken input -> error set and fractions None
- Router cases:
  - weekly decides
  - weekly tie -> daily decides
  - full tie -> skill decides (and None skill counts as lower than any number)
  - unknown quota last ("quota unknown")
  - exhausted last ("exhausted" for weekly or daily == 0)
  - host without the runner excludes it
  - active bonus lifts weekly to 1.0
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.quota import (
    Quota,
    apply_bonuses,
    parse_agy,
    parse_claude,
    parse_codex,
)
from tools.route import Choice, rank


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

def test_parse_claude_valid():
    sample = {
        "five_hour": {"utilization": 17.0, "resets_at": "2026-09-29T03:10:00+00:00"},
        "seven_day": {"utilization": 98.0, "resets_at": "2026-09-29T10:00:00+00:00"},
    }
    q = parse_claude(sample)
    assert q.provider == "claude"
    assert q.weekly_remaining == 0.02
    assert q.daily_remaining == 0.83
    assert q.weekly_resets_at == "2026-09-29T10:00:00+00:00"
    assert q.daily_resets_at == "2026-09-29T03:10:00+00:00"
    assert q.error is None

    # Also parses from JSON string
    q_str = parse_claude(json.dumps(sample))
    assert q_str.weekly_remaining == 0.02
    assert q_str.daily_remaining == 0.83


def test_parse_claude_broken():
    q_bad_json = parse_claude("not valid json {[[")
    assert q_bad_json.weekly_remaining is None
    assert q_bad_json.daily_remaining is None
    assert q_bad_json.error is not None

    q_empty = parse_claude({})
    assert q_empty.weekly_remaining is None
    assert q_empty.daily_remaining is None
    assert q_empty.error is not None


def test_parse_codex_valid_primary_weekly_secondary_300m_daily():
    # primary is weekly (10080m), secondary is daily (300m)
    lines = [
        json.dumps({
            "payload": {
                "type": "token_count",
                "info": {"tokens": 500},
                "rate_limits": {
                    "primary": {"used_percent": 96.0, "window_minutes": 10080, "resets_at": 1790593204},
                    "secondary": {"used_percent": 10.0, "window_minutes": 300, "resets_at": 1790593204},
                },
            }
        })
    ]
    q = parse_codex(lines)
    assert q.provider == "codex"
    assert q.weekly_remaining == 0.04
    assert q.daily_remaining == 0.90
    assert q.weekly_resets_at is not None
    assert q.daily_resets_at is not None
    assert "T" in q.weekly_resets_at
    assert q.error is None


def test_parse_codex_label_by_window_minutes_not_key_name():
    # Reverse key names: primary is 300m daily, secondary is 10080m weekly
    lines = [
        json.dumps({
            "payload": {
                "type": "token_count",
                "rate_limits": {
                    "primary": {"used_percent": 25.0, "window_minutes": 300, "resets_at": 1790593204},
                    "secondary": {"used_percent": 50.0, "window_minutes": 10080, "resets_at": 1790593204},
                },
            }
        })
    ]
    q = parse_codex(lines)
    assert q.daily_remaining == 0.75
    assert q.weekly_remaining == 0.50
    assert q.error is None


def test_parse_codex_rate_limits_not_last_line():
    # File where the last rate_limits event is not the last line
    lines = [
        json.dumps({"payload": {"type": "session_init"}}),
        json.dumps({
            "payload": {
                "type": "token_count",
                "rate_limits": {
                    "primary": {"used_percent": 96.0, "window_minutes": 10080, "resets_at": 1790593204},
                    "secondary": None,
                },
            }
        }),
        json.dumps({"type": "tool_execution", "tool": "exec_command"}),
        json.dumps({"payload": {"type": "other_event", "info": {"status": "ok"}}}),
    ]
    q = parse_codex(lines)
    assert q.weekly_remaining == 0.04
    assert q.daily_remaining is None
    assert q.error is None


def test_parse_codex_broken():
    q_no_limits = parse_codex([
        json.dumps({"payload": {"type": "session_init"}}),
        json.dumps({"payload": {"type": "message", "text": "hello"}}),
    ])
    assert q_no_limits.weekly_remaining is None
    assert q_no_limits.daily_remaining is None
    assert q_no_limits.error is not None

    q_invalid_lines = parse_codex("just raw unparseable text")
    assert q_invalid_lines.weekly_remaining is None
    assert q_invalid_lines.daily_remaining is None
    assert q_invalid_lines.error is not None


def test_parse_agy_valid():
    sample = {
        "command": {
            "data": {
                "groups": [
                    {
                        "name": "Claude and GPT models",
                        "buckets": [
                            {"window": "weekly", "remaining_fraction": 0.2, "reset_time": "2026-10-06T00:05:38Z"},
                        ],
                    },
                    {
                        "name": "Gemini Models",
                        "buckets": [
                            {"window": "weekly", "remaining_fraction": 1.0, "reset_time": "2026-10-06T00:05:38Z"},
                            {"window": "5h", "remaining_fraction": 0.75, "reset_time": "2026-09-29T12:00:00Z"},
                        ],
                    },
                ]
            }
        }
    }
    q = parse_agy(sample)
    assert q.provider == "agy"
    assert q.weekly_remaining == 1.0
    assert q.daily_remaining == 0.75
    assert q.weekly_resets_at == "2026-10-06T00:05:38Z"
    assert q.daily_resets_at == "2026-09-29T12:00:00Z"
    assert q.error is None


def test_parse_agy_broken():
    q_missing_group = parse_agy({
        "command": {
            "data": {
                "groups": [
                    {"name": "Other Models", "buckets": []},
                ]
            }
        }
    })
    assert q_missing_group.weekly_remaining is None
    assert q_missing_group.daily_remaining is None
    assert q_missing_group.error is not None


# ---------------------------------------------------------------------------
# Router tests
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_cfg():
    return {
        "providers": {
            "anthropic": {"runner": "claude"},
            "google": {"runner": "agy"},
            "openai": {"runner": "codex"},
        },
        "bonuses": [],
        "roles": {
            "dev_general": ["agy:gemini-3.8-flash-high", "claude:claude-sonnet-5"],
            "complex": ["claude:claude-fable-5-1", "codex:astra:xhigh"],
            "c_level_openai": ["codex:sol:xhigh"],
        },
        "router": {
            "tie_points": 5,
            "min_samples": 5,
        },
    }


def test_router_weekly_decides(mock_cfg):
    # On winbox (supports claude, codex, agy)
    quotas = {
        "agy": Quota(provider="agy", weekly_remaining=0.80, daily_remaining=0.50),
        "claude": Quota(provider="claude", weekly_remaining=0.40, daily_remaining=0.90),
    }
    choices = rank("dev_general", quotas, {}, "winbox", mock_cfg)
    assert len(choices) == 2
    assert choices[0].candidate == "agy:gemini-3.8-flash-high"
    assert choices[1].candidate == "claude:claude-sonnet-5"
    assert "highest weekly remaining" in choices[0].reason
    assert "80.0%" in choices[0].reason
    assert "40.0%" in choices[0].reason


def test_router_weekly_tie_daily_decides(mock_cfg):
    # Weekly within tie_points (5pp): 0.82 vs 0.80 = 2pp diff
    # claude daily 0.70 beats agy daily 0.30
    quotas = {
        "agy": Quota(provider="agy", weekly_remaining=0.80, daily_remaining=0.30),
        "claude": Quota(provider="claude", weekly_remaining=0.82, daily_remaining=0.70),
    }
    choices = rank("dev_general", quotas, {}, "winbox", mock_cfg)
    assert choices[0].candidate == "claude:claude-sonnet-5"
    assert choices[1].candidate == "agy:gemini-3.8-flash-high"
    assert "weekly tie within 5pp" in choices[0].reason
    assert "higher daily" in choices[0].reason


def test_router_full_tie_skill_decides(mock_cfg):
    # Weekly and daily identical
    quotas = {
        "agy": Quota(provider="agy", weekly_remaining=0.80, daily_remaining=0.50),
        "claude": Quota(provider="claude", weekly_remaining=0.80, daily_remaining=0.50),
    }
    # claude skill 0.85 beats agy skill 0.40
    skill = {
        ("agy", "gemini-3.8-flash-high"): 0.40,
        ("claude", "claude-sonnet-5"): 0.85,
    }
    choices = rank("dev_general", quotas, skill, "winbox", mock_cfg)
    assert choices[0].candidate == "claude:claude-sonnet-5"
    assert choices[1].candidate == "agy:gemini-3.8-flash-high"
    assert "higher skill score" in choices[0].reason

    # None skill counts as lower than any number
    skill_none = {
        ("agy", "gemini-3.8-flash-high"): 0.20,
        ("claude", "claude-sonnet-5"): None,
    }
    choices2 = rank("dev_general", quotas, skill_none, "winbox", mock_cfg)
    assert choices2[0].candidate == "agy:gemini-3.8-flash-high"
    assert choices2[1].candidate == "claude:claude-sonnet-5"

    # Full tie with no skill -> preserves CEO order (agy first in dev_general)
    choices3 = rank("dev_general", quotas, {}, "winbox", mock_cfg)
    assert choices3[0].candidate == "agy:gemini-3.8-flash-high"
    assert choices3[1].candidate == "claude:claude-sonnet-5"


def test_router_unknown_quota_last(mock_cfg):
    quotas = {
        "agy": Quota(provider="agy", weekly_remaining=0.80, daily_remaining=0.50),
        "claude": Quota(provider="claude", weekly_remaining=None, daily_remaining=None, error="quota missing"),
    }
    choices = rank("dev_general", quotas, {}, "winbox", mock_cfg)
    assert choices[0].candidate == "agy:gemini-3.8-flash-high"
    assert choices[-1].candidate == "claude:claude-sonnet-5"
    assert choices[-1].weekly is None
    assert choices[-1].reason == "quota unknown"


def test_router_exhausted_last(mock_cfg):
    # Weekly == 0 is exhausted and moves to end
    quotas = {
        "agy": Quota(provider="agy", weekly_remaining=0.0, daily_remaining=0.50),
        "claude": Quota(provider="claude", weekly_remaining=0.40, daily_remaining=0.50),
    }
    choices = rank("dev_general", quotas, {}, "winbox", mock_cfg)
    assert choices[0].candidate == "claude:claude-sonnet-5"
    assert choices[-1].candidate == "agy:gemini-3.8-flash-high"
    assert choices[-1].reason == "exhausted"

    # Daily == 0 is also exhausted
    quotas_daily_0 = {
        "agy": Quota(provider="agy", weekly_remaining=0.90, daily_remaining=0.0),
        "claude": Quota(provider="claude", weekly_remaining=0.40, daily_remaining=0.50),
    }
    choices_d = rank("dev_general", quotas_daily_0, {}, "winbox", mock_cfg)
    assert choices_d[0].candidate == "claude:claude-sonnet-5"
    assert choices_d[-1].candidate == "agy:gemini-3.8-flash-high"
    assert choices_d[-1].reason == "exhausted"


def test_router_host_without_runner_excludes_it(mock_cfg):
    # contabo only supports [claude] in config/hosts.yaml
    quotas = {
        "agy": Quota(provider="agy", weekly_remaining=0.95, daily_remaining=0.95),
        "claude": Quota(provider="claude", weekly_remaining=0.10, daily_remaining=0.10),
    }
    choices = rank("dev_general", quotas, {}, "contabo", mock_cfg)
    # agy is excluded entirely from the contabo host
    assert len(choices) == 1
    assert choices[0].candidate == "claude:claude-sonnet-5"
    assert choices[0].runner == "claude"


def test_router_active_bonus_lifts_weekly_to_1_0(mock_cfg):
    bonuses = [
        {
            "provider": "anthropic",
            "from": "2026-09-01",
            "to": "2026-09-30",
            "note": "free grant bonus",
        }
    ]
    q_claude = Quota(provider="claude", weekly_remaining=0.10, daily_remaining=0.50, source="usage.json")
    apply_bonuses(q_claude, bonuses, now="2026-09-29T12:00:00Z")
    assert q_claude.weekly_remaining == 1.0
    assert "bonus: free grant bonus" in q_claude.source

    quotas = {
        "claude": q_claude,
        "agy": Quota(provider="agy", weekly_remaining=0.80, daily_remaining=0.50),
    }
    choices = rank("dev_general", quotas, {}, "winbox", mock_cfg)
    # Claude with 1.0 (via bonus) now beats agy's 0.80
    assert choices[0].candidate == "claude:claude-sonnet-5"
    assert choices[1].candidate == "agy:gemini-3.8-flash-high"
