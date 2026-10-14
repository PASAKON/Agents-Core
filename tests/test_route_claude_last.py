from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import db
from tools import forecast, gc_stale_tasks, quota_handoff, route, worker_reap


def _cfg() -> dict:
    return {
        "buckets": {
            "agy-gemini": {
                "provider": "google",
                "runner": "agy",
                "models": ["gemini-4-argon-high", "gemini-3.8-flash-high"],
            },
            "agy-claude": {
                "provider": "anthropic",
                "runner": "agy",
                "models": ["claude-sonnet-5-5-high"],
            },
            "codex": {
                "provider": "openai",
                "runner": "codex",
                "models": [""],
            },
            "claude": {
                "provider": "anthropic",
                "runner": "claude",
                "models": ["claude-sonnet-5-5"],
            },
        },
        "shell_runners": ["claude", "codex"],
        "roles": {
            "dev_general": [
                "agy:gemini-4-argon-high",
                "agy:gemini-3.8-flash-high",
                "agy:claude-sonnet-5-5-high",
                "codex:",
                "claude:claude-sonnet-5-5",
            ],
        },
        "role_classes": {"developer": "dev_general"},
        "router": {"tie_points": 5, "min_samples": 5},
    }


def _snap(*, agy_gemini_rem=50.0, agy_claude_rem=80.0, codex_rem=50.0, claude_rem=80.0) -> dict:
    buckets = {}
    if agy_gemini_rem is not None:
        buckets["agy-gemini"] = {"weekly_rem": agy_gemini_rem, "daily_rem": agy_gemini_rem, "stale": False}
    if agy_claude_rem is not None:
        buckets["agy-claude"] = {"weekly_rem": agy_claude_rem, "daily_rem": agy_claude_rem, "stale": False}
    if codex_rem is not None:
        buckets["codex"] = {"weekly_rem": codex_rem, "daily_rem": codex_rem, "stale": False}
    if claude_rem is not None:
        buckets["claude"] = {"weekly_rem": claude_rem, "daily_rem": claude_rem, "stale": False}
    return {"buckets": buckets}


def test_pressure_rule_on_ranks_outside_will_hit_and_unknown_before_ok_claude():
    cfg = _cfg()
    # agy-gemini is low (5% rem) -> will_hit (cost 20% > 5% rem)
    # codex has no snapshot -> unknown
    # agy-claude and claude have 80% rem -> ok
    snap = _snap(agy_gemini_rem=5.0, agy_claude_rem=80.0, codex_rem=None, claude_rem=80.0)
    cost_by = {
        "agy-gemini": {"cost": 20.0, "n": 5, "basis": "runner=agy"},
        "codex": {"cost": 10.0, "n": 5, "basis": "runner=codex"},
        "agy-claude": {"cost": 10.0, "n": 5, "basis": "runner=agy"},
        "claude": {"cost": 10.0, "n": 5, "basis": "runner=claude"},
    }
    with patch.object(forecast, "estimate_cost", side_effect=lambda **kw: cost_by[kw["bucket"]]):
        plans = route.plan(
            "dev_general",
            cfg=cfg,
            snap=snap,
            scores={},
            needs_shell=False,
            needs_claude_tool=False,
            pressure_rule=True,
        )

    by_bucket_verdict = [(p.bucket, p.verdict, route._is_claude(p, cfg)) for p in plans]
    # All outside candidates (unknown codex, will_hit agy-gemini) must precede ok Claude candidates
    first_claude_idx = next(i for i, (_, _, is_c) in enumerate(by_bucket_verdict) if is_c)
    outside_indices = [i for i, (_, _, is_c) in enumerate(by_bucket_verdict) if not is_c]
    assert max(outside_indices) < first_claude_idx

    codex_idx = next(i for i, (b, v, _) in enumerate(by_bucket_verdict) if b == "codex" and v == "unknown")
    agy_gem_idx = next(i for i, (b, v, _) in enumerate(by_bucket_verdict) if b == "agy-gemini" and v == "will_hit")
    assert codex_idx < agy_gem_idx < first_claude_idx


def test_cannot_outside_ranks_after_every_claude_candidate():
    cfg = _cfg()
    snap = _snap(agy_gemini_rem=80.0, agy_claude_rem=5.0, codex_rem=80.0, claude_rem=5.0)
    cost_by = {
        "agy-gemini": {"cost": 10.0, "n": 5, "basis": "runner=agy"},
        "codex": {"cost": 10.0, "n": 5, "basis": "runner=codex"},
        "agy-claude": {"cost": 20.0, "n": 5, "basis": "runner=agy"},
        "claude": {"cost": 20.0, "n": 5, "basis": "runner=claude"},
    }
    # needs_shell=True -> agy candidates (including agy-gemini) are `cannot`, while codex is ok_outside
    # and claude is will_hit_claude. Wait: with needs_claude_tool=True, ALL non-claude (agy-gemini, codex)
    # get verdict='cannot' and must rank after every Claude candidate (even will_hit Claude).
    with patch.object(forecast, "estimate_cost", side_effect=lambda **kw: cost_by[kw["bucket"]]):
        plans = route.plan(
            "dev_general",
            cfg=cfg,
            snap=snap,
            scores={},
            needs_shell=False,
            needs_claude_tool=True,
            pressure_rule=True,
        )

    claude_indices = [i for i, p in enumerate(plans) if route._is_claude(p, cfg)]
    cannot_outside_indices = [
        i for i, p in enumerate(plans) if not route._is_claude(p, cfg) and p.verdict == "cannot"
    ]
    assert claude_indices and cannot_outside_indices
    assert max(claude_indices) < min(cannot_outside_indices)
    for idx in cannot_outside_indices:
        assert plans[idx].why == f"needs a Claude-only tool; {plans[idx].runner} has none"


def test_pressure_rule_off_keeps_order_unchanged():
    cfg = _cfg()
    snap = _snap(agy_gemini_rem=5.0, agy_claude_rem=80.0, codex_rem=None, claude_rem=80.0)
    cost_by = {
        "agy-gemini": {"cost": 20.0, "n": 5, "basis": "runner=agy"},
        "codex": {"cost": 10.0, "n": 5, "basis": "runner=codex"},
        "agy-claude": {"cost": 10.0, "n": 5, "basis": "runner=agy"},
        "claude": {"cost": 10.0, "n": 5, "basis": "runner=claude"},
    }
    with patch.object(forecast, "estimate_cost", side_effect=lambda **kw: cost_by[kw["bucket"]]):
        plans_off = route.plan(
            "dev_general",
            cfg=cfg,
            snap=snap,
            scores={},
            needs_shell=False,
            needs_claude_tool=False,
            pressure_rule=False,
        )

    # Without pressure_rule, rank() order is preserved (ok buckets with 80% rem beat 5% rem / unknown)
    assert [f"{p.runner}:{p.model}" for p in plans_off[:2]] == [
        "agy:claude-sonnet-5-5-high",
        "claude:claude-sonnet-5-5",
    ]


def test_needs_claude_tool():
    assert forecast.needs_claude_tool("capture the footage in Chrome") is True
    assert forecast.needs_claude_tool("write the script") is False
    assert forecast.needs_claude_tool("edit-only: the PH runs the tests\ncapture the footage in Chrome") is False
    assert (
        forecast.needs_claude_tool(
            "Use tools/agy_browse.py against http://127.0.0.1:9222 to capture a screenshot in browser"
        )
        is False
    )


def test_plans_yaml_roles_and_role_classes():
    cfg = route.load_config(ROOT / "config" / "plans.yaml")
    role_classes = cfg["role_classes"]
    assert role_classes.get("content_strategist") == "doc_text"
    assert role_classes.get("script_writer") == "doc_text"
    assert "prompt_engineer" not in role_classes
    assert cfg["roles"]["dev_general"][0] == "agy:gemini-4-argon-high"


def test_quota_stop_sets_rate_limited_and_gc_skips_it(tmp_path, monkeypatch):
    task_id = "task-1234abcd"
    launch_dir = tmp_path / f".launch-{task_id}"
    launch_dir.mkdir()
    (launch_dir / "agy-events.log").write_text("step 1\nError: RESOURCE_EXHAUSTED: quota exceeded\n")

    task_row = {
        "id": task_id,
        "project": "mooniex-agents",
        "role": "developer",
        "title": "Test quota stop",
        "status": "in_progress",
        "runner": "agy",
        "runner_model": "gemini-4-argon-high",
        "branch": f"worker/{task_id}",
        "review": None,
        "retry_after_ts": None,
        "updated_at": "2026-10-14T00:00:00+00:00",
        "pid": None,
    }

    def fake_get_task(tid):
        return task_row if tid == task_id else None

    def fake_update_status(tid, status, **kwargs):
        assert tid == task_id
        task_row["status"] = status
        if "review" in kwargs:
            task_row["review"] = kwargs["review"]
        if "retry_after_ts" in kwargs:
            task_row["retry_after_ts"] = kwargs["retry_after_ts"]

    monkeypatch.setattr(db, "get_task", fake_get_task)
    monkeypatch.setattr(db, "update_status", fake_update_status)

    reap_res = worker_reap.close_dev(task_id, reason="launcher exited", launch_dir=launch_dir)
    assert reap_res.get("quota_stop") == "RESOURCE_EXHAUSTED"
    assert task_row["status"] == "rate_limited"
    assert task_row["retry_after_ts"] is None
    rev = json.loads(task_row["review"])
    assert rev["quota_stop"] == "RESOURCE_EXHAUSTED"
    assert f"python3 tools/quota_handoff.py {task_id}" in rev["next"]

    # Now verify gc_stale_tasks skips this rate_limited row because review.quota_stop is set
    monkeypatch.setattr(
        db,
        "list_tasks",
        lambda status=None, limit=500: [task_row] if status == "rate_limited" else [],
    )
    monkeypatch.setattr(db, "list_stale_locks", lambda max_age_minutes=30: [])
    monkeypatch.setattr(gc_stale_tasks, "is_local_row", lambda t: True)
    monkeypatch.setattr(gc_stale_tasks, "_alive_for_gc", lambda t: False)

    cancelled = gc_stale_tasks.gc_stale_tasks(ratelimit_minutes=1)
    assert cancelled == []
    assert task_row["status"] == "rate_limited"
