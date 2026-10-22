"""P4a contract tests: fake snapshots, clock, DB and spawn; no live hub."""
import asyncio
import contextlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest

from lib import portfolio
from tools import budget_queue, route, usage_budget
from tools.quota import Quota

NOW = datetime(2026, 10, 22, 16, 59, tzinfo=timezone.utc)
BUCKETS = ("agy-gemini", "codex", "claude")


@pytest.fixture
def routing(monkeypatch, tmp_path):
    cfg = {"roles": {"analysis": ["agy:test", "codex:", "claude:test"]},
           "role_classes": {"analysis": "analysis"}, "router": {"order": "budget"},
           "buckets": {b: {"match": [r + ":"], "provider": p} for b, r, p in
                       zip(BUCKETS, ("agy", "codex", "claude"), ("google", "openai", "anthropic"))}}
    monkeypatch.setattr(route, "_host_runners", lambda host: ["agy", "codex", "claude"])
    monkeypatch.setattr(route.forecast, "burn_rate", lambda *a, **kw: None)
    monkeypatch.setattr(route.forecast, "cost_for", lambda *a, **kw: (.01, "test"))
    monkeypatch.setattr(usage_budget, "SNAPSHOT", tmp_path / "budget.json")
    monkeypatch.setattr(budget_queue, "QUEUE_PATH", tmp_path / "queue.jsonl")
    monkeypatch.setattr(budget_queue.disk_queue.db, "now_iso", lambda: NOW.isoformat())
    return dict(cfg=cfg, quotas={b: Quota(b, weekly_remaining=.8, daily_remaining=1) for b in BUCKETS},
                limits={b: {"reserve_pct": 0, "min_5h_pct": 0} for b in BUCKETS},
                skill={}, size="M", now=NOW)


def snapshot(states, *, ts=NOW, day=None):
    usage_budget.SNAPSHOT.write_text(json.dumps({"ts": ts.isoformat(),
        "day": day or ts.astimezone(usage_budget.THAI).date().isoformat(),
        "rows": {b: {"bucket": b, "state": s} for b, s in zip(BUCKETS, states)}}))


@pytest.mark.parametrize("tier", [None, "critical", "normal", "low"])
@pytest.mark.parametrize("states", [("under", "under", "under"), ("over", "under", "under"),
                                    ("over", "over", "over")])
def test_tier_matrix(routing, tier, states):
    snapshot(states)
    choice = route.pick_runner("analysis", "test", tier=tier, **routing)
    deferred = tier == "low" and "over" in states or tier == "normal" and states[:2] == ("over", "over")
    assert choice.defer == deferred
    if deferred:
        budget_queue.enqueue("task-test", "ph", tier=tier)
        assert budget_queue.is_queued("task-test")
    else:
        assert choice.runner in ("agy", "codex")
    if tier in (None, "critical"):
        assert choice == route.pick_runner("analysis", "test", **routing)


def test_critical_can_fall_back_to_claude(routing):
    snapshot(("over", "over", "over"))
    for b in BUCKETS[:2]:
        routing["quotas"][b].weekly_remaining = 0
    assert route.pick_runner("analysis", "test", tier="critical", **routing).runner == "claude"
    assert route.pick_runner("analysis", "test", tier="normal", **routing).defer


@pytest.mark.parametrize("mode", ["missing", "stale", "unknown", "yesterday"])
def test_gate_fails_open(routing, mode):
    if mode != "missing":
        snapshot(("over", "over", "unknown" if mode == "unknown" else "over"),
                 ts=NOW - timedelta(minutes=31) if mode == "stale" else NOW,
                 day="2026-10-21" if mode == "yesterday" else None)
    assert not route.pick_runner("analysis", "test", tier="low", **routing).defer


@pytest.fixture
def registry(monkeypatch):
    rows = [{"tier": "low", "ph_session": "abcd", "repos": ["repo"]},
            {"tier": "critical", "ph_session": "efgh", "repos": '["repo"]'}]
    conn = Mock()
    conn.execute.return_value.fetchall.return_value = rows
    monkeypatch.setattr(portfolio, "_tx", lambda *a: contextlib.nullcontext(conn))
    return conn


def test_resolution_order(registry):
    task = {"description": "title\ntier: normal\n\ntier: critical", "owner_cto": "abcd", "project": "repo"}
    assert portfolio.tier_for(task) == "normal"
    task["description"] = "title\n\ntier: critical"
    assert portfolio.tier_for(task) == "low"
    task["owner_cto"] = "other"
    assert portfolio.tier_for(task) == "critical"
    task["project"] = "missing"
    assert portfolio.tier_for(task) == "normal"
    registry.execute.side_effect = RuntimeError("offline")
    assert portfolio.tier_for(task) == "normal"
    task["description"] = "tier: low"
    assert portfolio.tier_for(task) == "low"


def test_set_tier_validates_and_logs(registry):
    registry.execute.return_value.fetchone.side_effect = [{"tier": "normal"}, {"tier": "low"}]
    assert portfolio.set_tier("p", "low", actor="test", why="wait", go="Q-1", conn=registry)["tier"] == "low"
    calls = registry.execute.call_args_list
    event = next(c.args[1] for c in calls if c.args[0].startswith("INSERT INTO project_events"))
    assert event[2] == "tier"
    assert json.loads(event[4]) == {"from": "normal", "to": "low", "why": "wait", "go": "Q-1"}
    with pytest.raises(portfolio.PortfolioError):
        portfolio.set_tier("p", "urgent", actor="test", why="wait", conn=registry)


def test_queue_gc_and_thai_reset(routing, monkeypatch):
    from tools import gc_stale_tasks as gc
    from runners import watchdog
    snapshot(("over", "over", "over"))
    monkeypatch.setattr(usage_budget, "load_gate_rows", lambda **kw: {b: {"state": "over"} for b in BUCKETS})
    budget_queue.enqueue("task-test", "ph", tier="low")
    entry = budget_queue.all_entries()[0]
    assert not budget_queue.ready(entry, now=NOW)
    assert budget_queue.ready(entry, now=NOW + timedelta(minutes=2))
    task = {"id": "task-test", "status": "pending", "description": "tier: low",
            "created_at": "2020-01-01T00:00:00Z", "updated_at": "2020-01-01T00:00:00Z"}
    monkeypatch.setattr(gc.db, "list_tasks", lambda **kw: [task] if kw.get("status") == "pending" else [])
    monkeypatch.setattr(gc, "is_local_row", lambda t: True)
    monkeypatch.setattr(gc, "release_terminal_task_locks", lambda **kw: [])
    monkeypatch.setattr(gc.disk_queue, "QUEUE_PATH", budget_queue.QUEUE_PATH.with_name("disk.jsonl"))
    assert gc.gc_stale_tasks() == []
    monkeypatch.setattr(watchdog.db, "get_task", lambda t: task)
    original_ready = budget_queue.ready
    monkeypatch.setattr(budget_queue, "ready", lambda e: original_ready(e, now=NOW + timedelta(minutes=2)))
    calls = []
    async def spawn(t):
        calls.append(t)
        return {"status": "in_progress"}
    monkeypatch.setattr(watchdog.delegate, "delegate_task", spawn)
    watchdog._drain_budget_queue()
    assert calls == ["task-test"]
    assert not budget_queue.is_queued("task-test")


def test_migration_is_repeatable():
    sql = (Path(__file__).resolve().parents[1] / "lib/db_pg.py").read_text()
    assert "ADD COLUMN IF NOT EXISTS tier TEXT NOT NULL DEFAULT 'normal'" in sql
    assert "DROP CONSTRAINT IF EXISTS project_events_kind_check" in sql
    assert "ADD CONSTRAINT project_events_kind_check" in sql


def test_spawn_registry_and_brief(monkeypatch, tmp_path):
    from tools import spawn_ph, send_to_cxo
    from lib import portfolio as pf
    conn = Mock()
    conn.execute.return_value.fetchone.return_value = {"id": "p", "tier": "normal"}
    monkeypatch.setattr(pf, "_tx", lambda: contextlib.nullcontext(conn))
    set_tier = Mock()
    monkeypatch.setattr(pf, "set_tier", set_tier)
    monkeypatch.setattr(spawn_ph, "BRIEFS_DIR", tmp_path)
    monkeypatch.setattr(spawn_ph, "LOCKS_DIR", tmp_path)
    monkeypatch.setattr(send_to_cxo, "record_spawn", lambda *a: None)
    plan = {"project": "p", "tier": "low", "lane": "cto", "owner": "cto-abcd",
            "session_id": "1234", "tmux_session": "project_head-1234", "brief": str(tmp_path / "brief.md")}
    spawn_ph._write_claim(plan, "tier: critical\nWork\n\nBody")
    assert (tmp_path / "brief.md").read_text().startswith("tier: low\nWork")
    assert set_tier.call_args.args == ("p", "low")


@pytest.mark.parametrize("tier", ["normal", "low"])
def test_handoff_never_creates_claude_successor(monkeypatch, tier):
    from tools import quota_handoff
    monkeypatch.setattr(quota_handoff.db, "get_task", lambda t: {"description": f"tier: {tier}"})
    with pytest.raises(ValueError, match="tier_no_claude"):
        quota_handoff.handoff("task-test")


def test_non_routed_low_role_defers(routing):
    snapshot(("over", "under", "under"))
    assert route.pick_runner("unrouted", "test", tier="low", **routing).defer


def test_normal_no_claude_when_only_outside_candidate_is_over(routing):
    snapshot(("over", "under", "under"))
    routing["quotas"]["codex"].weekly_remaining = 0
    assert route.pick_runner("analysis", "test", tier="normal", **routing).defer


def test_pinned_low_cannot_bypass_gate(routing, monkeypatch):
    from tools import delegate
    monkeypatch.delenv("ORG_ROUTER", raising=False)
    monkeypatch.setattr(route, "check_override", lambda task: None)
    monkeypatch.setattr(usage_budget, "load_gate_rows", lambda **kw: {"codex": {"state": "over"}})
    task = {"id": "task-test", "runner": "codex", "description": "tier: low"}
    assert delegate._route_runner(task, "analysis", "test") == "defer"


def test_gate_returns_only_ok_under_outside_plans(routing):
    # CEO ordering can pick an over runner even when another runner is under.
    routing["cfg"]["router"]["order"] = "ceo"
    snapshot(("over", "under", "under"))
    plans = route.plan("analysis", tier="normal", **routing)
    assert [p.choice.runner for p in plans] == ["codex"]
    assert "tier_no_claude" in plans[0].why


def test_delegate_deferral_queues_without_spawning(routing, monkeypatch):
    from tools import delegate
    # Test the gate synchronously; executor wakeups are not part of its contract.
    async def inline(fn, *args, **kwargs):
        return fn(*args, **kwargs)
    monkeypatch.setattr(delegate.asyncio, "to_thread", inline)
    snapshot(("over", "over", "over"))
    task = {"id": "task-test", "status": "pending", "role": "analysis", "project": "repo",
            "description": "tier: low", "owner_cto": "ph"}
    monkeypatch.delenv("ORG_ROUTER", raising=False)
    monkeypatch.setattr(delegate.db, "get_task", lambda t: dict(task))
    monkeypatch.setattr(delegate.db, "set_fields", lambda t, **kw: task.update(kw))
    monkeypatch.setattr(delegate, "_ph_ownership_refusal", lambda t: None)
    monkeypatch.setattr(delegate, "_ph_release_slot", lambda t: None)
    monkeypatch.setattr(delegate, "_p2_spawn_refusal", lambda *a: None)
    monkeypatch.setattr(delegate, "_scope_applies", lambda *a: False)
    monkeypatch.setattr(delegate, "_free_gb", lambda: 100)
    monkeypatch.setattr(delegate, "_disk_orange_floor_gb", lambda: 5)
    monkeypatch.setattr(delegate, "self_host", lambda: "test")
    monkeypatch.setattr(delegate.host_router, "enabled", lambda: False)
    monkeypatch.setattr(delegate, "get_project", lambda p: {"agents_allowed": ["analysis"]})
    monkeypatch.setattr(route, "check_override", lambda t: None)
    original = route.pick_runner
    monkeypatch.setattr(route, "pick_runner", lambda role, host, **kw: original(role, host, **kw, **routing))
    result = asyncio.run(delegate.delegate_task(task["id"]))
    assert result["status"] == "pending"
    assert "queued for budget (0 ahead)" in result["delegate_log"]
    assert budget_queue.is_queued(task["id"])
    assert "runner" not in result
