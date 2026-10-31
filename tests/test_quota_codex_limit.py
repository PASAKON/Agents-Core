"""Tests for Codex quota handling when usage limit is hit without payload.rate_limits."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.quota import Quota, parse_codex
from tools.route import rank


def test_usage_limit_no_rate_limits_zeroes_and_hits_limit():
    """usage-limit task_complete with no rate_limits -> limit_hit True, remaining 0, no raise.

    Must fail on base code (where it raised ValueError and returned error/None remaining).
    """
    lines = [
        json.dumps({"payload": {"type": "session_init"}}),
        json.dumps({
            "payload": {
                "type": "task_complete",
                "error": {
                    "message": "You've hit your usage limit. ... try again at Oct 20th, 2026 7:27 AM.",
                    "codex_error_info": "usage_limit_exceeded",
                },
            }
        }),
    ]
    q = parse_codex(lines, source="test-session")
    assert q.error is None
    assert q.limit_hit is True
    assert q.weekly_remaining == 0.0
    assert q.daily_remaining == 0.0
    assert q.limit_until is None
    assert q.weekly_resets_at is None
    assert q.daily_resets_at is None
    assert q.source == "test-session"


def test_usage_limit_no_rate_limits_with_parseable_iso_reset():
    """If the error text carries an ISO reset time the code can parse, set limit_until from it."""
    lines = [
        json.dumps({
            "payload": {
                "type": "task_complete",
                "error": {
                    "message": "You've hit your usage limit. Try again at 2026-10-20T05:27:58Z",
                    "codex_error_info": "usage_limit_exceeded",
                },
            }
        }),
    ]
    q = parse_codex(lines)
    assert q.error is None
    assert q.limit_hit is True
    assert q.weekly_remaining == 0.0
    assert q.daily_remaining == 0.0
    assert q.limit_until == "2026-10-20T05:27:58Z"
    assert q.weekly_resets_at == "2026-10-20T05:27:58Z"


def test_usage_limit_no_rate_limits_with_resets_at_field():
    """If the error dict carries resets_at (epoch seconds), set limit_until from it."""
    lines = [
        json.dumps({
            "payload": {
                "type": "task_complete",
                "error": {
                    "message": "You've hit your usage limit.",
                    "codex_error_info": "usage_limit_exceeded",
                    "resets_at": 1792474078,
                },
            }
        }),
    ]
    q = parse_codex(lines)
    assert q.error is None
    assert q.limit_hit is True
    assert q.weekly_remaining == 0.0
    assert q.daily_remaining == 0.0
    assert q.limit_until == "2026-10-20T05:27:58Z"
    assert q.weekly_resets_at == "2026-10-20T05:27:58Z"


def test_neither_rate_limits_nor_usage_limit_stop_raises():
    """When neither rate_limits nor a usage-limit stop is present, keep raising."""
    lines = [
        json.dumps({"payload": {"type": "session_init"}}),
        json.dumps({"payload": {"type": "message", "text": "hello"}}),
    ]
    q = parse_codex(lines)
    assert q.error is not None
    assert "no payload.rate_limits" in q.error
    assert q.weekly_remaining is None
    assert q.daily_remaining is None
    assert q.limit_hit is False


def test_clean_task_complete_no_rate_limits_raises():
    """A clean task_complete with no rate_limits still raises."""
    lines = [
        json.dumps({"payload": {"type": "session_init"}}),
        json.dumps({"payload": {"type": "task_complete", "error": None}}),
    ]
    q = parse_codex(lines)
    assert q.error is not None
    assert "no payload.rate_limits" in q.error
    assert q.limit_hit is False


def test_other_error_task_complete_no_rate_limits_raises():
    """A non-usage-limit task_complete error with no rate_limits still raises."""
    lines = [
        json.dumps({
            "payload": {
                "type": "task_complete",
                "error": {"message": "syntax error", "codex_error_info": "other_error"},
            }
        }),
    ]
    q = parse_codex(lines)
    assert q.error is not None
    assert "no payload.rate_limits" in q.error
    assert q.limit_hit is False


def test_clean_task_complete_after_usage_limit_clears_stop():
    """A clean task_complete after a usage limit stop clears stopped; without rate_limits it still raises."""
    lines = [
        json.dumps({
            "payload": {
                "type": "task_complete",
                "error": {
                    "message": "You've hit your usage limit.",
                    "codex_error_info": "usage_limit_exceeded",
                },
            }
        }),
        json.dumps({
            "payload": {
                "type": "task_complete",
                "error": None,
            }
        }),
    ]
    q = parse_codex(lines)
    assert q.error is not None
    assert "no payload.rate_limits" in q.error
    assert q.limit_hit is False


def test_rate_limits_present_and_usage_limit_stop_unchanged():
    """When rate_limits are present along with usage-limit stop, behaviour is unchanged."""
    lines = [
        json.dumps({
            "payload": {
                "type": "token_count",
                "rate_limits": {
                    "primary": {"used_percent": 96.0, "window_minutes": 10080, "resets_at": 1792474078},
                    "secondary": None,
                },
            }
        }),
        json.dumps({
            "payload": {
                "type": "task_complete",
                "error": {
                    "message": "You've hit your usage limit. ... try again at Oct 20th, 2026 7:27 AM.",
                    "codex_error_info": "usage_limit_exceeded",
                },
            }
        }),
    ]
    q = parse_codex(lines)
    assert q.error is None
    assert q.limit_hit is True
    assert q.weekly_remaining == 0.0
    assert q.limit_until == "2026-10-20T05:27:58Z"


def test_router_treats_quota_without_rate_limits_as_exhausted():
    """Router (tools/route.py) treats codex with limit_hit and 0.0 remaining as exhausted."""
    lines = [
        json.dumps({
            "payload": {
                "type": "task_complete",
                "error": {
                    "message": "You've hit your usage limit.",
                    "codex_error_info": "usage_limit_exceeded",
                },
            }
        }),
    ]
    q_codex = parse_codex(lines)
    assert q_codex.limit_hit is True
    assert q_codex.weekly_remaining == 0.0

    cfg = {
        "buckets": {
            "claude": {"provider": "anthropic", "match": ["claude:"]},
            "codex": {"provider": "openai", "match": ["codex:"]},
            "agy-gemini": {"provider": "google", "match": ["agy:gemini-"]},
        },
        "roles": {
            "dev_general": ["codex:", "agy:gemini-3.8-flash-high"],
        },
        "router": {
            "tie_points": 5,
            "min_samples": 5,
        },
    }
    quotas = {
        "codex": q_codex,
        "agy-gemini": Quota(provider="agy-gemini", weekly_remaining=0.50, daily_remaining=0.50),
    }
    choices = rank("dev_general", quotas, {}, None, cfg)
    assert len(choices) == 2
    assert choices[0].candidate == "agy:gemini-3.8-flash-high"
    assert choices[-1].candidate == "codex:"
    assert choices[-1].reason == "exhausted"
