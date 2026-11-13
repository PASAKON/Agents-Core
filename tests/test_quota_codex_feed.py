import json
from datetime import datetime, timedelta, timezone

import pytest
from tools import quota


@pytest.mark.parametrize("age", [0, 1790, 1800, 1801, None])
def test_feed_fresh_stale_missing(tmp_path, age):
    feed = tmp_path / "feed.json"
    rollout = tmp_path / "rollout.jsonl"
    rollout.write_text(json.dumps({"payload": {"rate_limits": {"primary": {
        "used_percent": 100, "window_minutes": 10080, "resets_at": 1900000000}}}}))
    if age is not None:
        feed.write_text(json.dumps({
            "observed_at": (datetime.now(timezone.utc) - timedelta(seconds=age)).isoformat(),
            "plan_type": "plus", "primary": {"utilization": 0,
            "window_minutes": 10080, "resets_at": "2026-11-20T07:00:00Z"}}))
    result = quota.fetch_codex({"quota_sources": {"codex": {
        "feed_path": str(feed), "sessions_glob": str(rollout)}}})
    fresh = age is not None and age < 1800
    assert result.weekly_remaining == (1 if fresh else 0)
    assert result.limit_hit is (not fresh)
    assert result.source == str(feed if fresh else rollout)
    if fresh:
        assert result.plan_type == "plus"
        assert result.weekly_resets_at == "2026-11-20T07:00:00Z"
