"""IRON §59 rule 8 (CEO 15 Oct): Claude runs out last.

With pressure_rule on, every usable outside candidate (ok, unknown, will_hit) ranks ahead of Claude; only a
`cannot` one falls behind it. Argon leads dev_general and doc_text, Flash leads a size-S dev job, the CMO text
roles route to doc_text, a brief that needs a Claude-only tool keeps outside runners off it, the Codex bonus
holds Codex at full until 7 Nov, and a run that stops on its limit is parked as rate_limited for the PH.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import forecast, quota_handoff  # noqa: E402
from tools.quota import (  # noqa: E402
    Quota, apply_bonuses, apply_limit_hit, load_plans, parse_codex, read_snapshot, write_snapshot,
)
import tools.route as route  # noqa: E402
from tools.route import pick_runner, plan  # noqa: E402

LIMITS = {
    "claude": {"plan_usd": 20, "reserve_pct": 50, "min_5h_pct": 30},
    "agy-gemini": {"plan_usd": 100, "reserve_pct": 10, "min_5h_pct": 10},
    "codex": {"plan_usd": 20, "reserve_pct": 20, "min_5h_pct": 0},
}


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
        "roles": {
            "dev_general": ["agy:gemini-4-argon-high", "agy:gemini-3.8-flash-high", "claude:claude-sonnet-5-5"],
            "doc_text": ["agy:gemini-4-argon-high", "agy:gemini-3.8-flash-high", "claude:claude-sonnet-5-5"],
        },
        "role_classes": {"developer": "dev_general", "script_writer": "doc_text"},
        "small_first": {"dev_general": "agy:gemini-3.8-flash-high"},
        "router": {"tie_points": 5, "min_samples": 5},
    }


@pytest.fixture(autouse=True)
def _hosts(monkeypatch):
    monkeypatch.setattr(route, "_host_runners", lambda host: ["claude", "agy", "codex"])


def _plan(cfg, quotas, role="developer", size="M", **kw):
    return plan(role, size=size, host="contabo", cfg=cfg, quotas=quotas, skill={}, limits=LIMITS, **kw)


def _runners(plans):
    return [f"{p.choice.runner}:{p.choice.model}:{p.verdict}" for p in plans]


def test_outside_will_hit_ranks_ahead_of_ok_claude(cfg):
    quotas = {"claude": Quota(provider="claude", weekly_remaining=1.0, daily_remaining=1.0),
              "agy-gemini": Quota(provider="agy-gemini", weekly_remaining=0.05, daily_remaining=0.5)}
    plans = _plan(cfg, quotas)
    assert [p.verdict for p in plans] == ["will_hit", "will_hit", "ok"], _runners(plans)
    assert plans[-1].choice.runner == "claude"
    choice = pick_runner("developer", "contabo", size="M", cfg=cfg, quotas=quotas, skill={}, limits=LIMITS)
    assert choice.runner == "agy"
    assert not choice.reason.startswith("no ok candidate")  # Claude itself is ok: no CEO alarm


def test_outside_unknown_ranks_ahead_of_ok_claude(cfg):
    quotas = {"claude": Quota(provider="claude", weekly_remaining=1.0, daily_remaining=1.0)}
    plans = _plan(cfg, quotas)
    assert plans[0].choice.runner == "agy" and plans[0].verdict == "unknown", _runners(plans)
    assert plans[-1].choice.runner == "claude"


def test_cannot_outside_ranks_after_claude(cfg):
    quotas = {"claude": Quota(provider="claude", weekly_remaining=1.0, daily_remaining=1.0),
              "agy-gemini": Quota(provider="agy-gemini", weekly_remaining=0.9, daily_remaining=0.9)}
    plans = _plan(cfg, quotas, needs_claude_tool=True)
    assert plans[0].choice.runner == "claude", _runners(plans)
    assert all(p.verdict == "cannot" for p in plans[1:])
    assert "needs a Claude-only tool" in plans[1].why


def test_pressure_rule_off_keeps_the_old_order(cfg):
    cfg["pressure_rule"] = False
    quotas = {"claude": Quota(provider="claude", weekly_remaining=1.0, daily_remaining=1.0),
              "agy-gemini": Quota(provider="agy-gemini", weekly_remaining=0.05, daily_remaining=0.5)}
    plans = _plan(cfg, quotas)
    assert plans[0].choice.runner == "claude" and plans[0].verdict == "ok", _runners(plans)


def test_argon_leads_m_and_flash_leads_s(cfg):
    quotas = {"claude": Quota(provider="claude", weekly_remaining=1.0, daily_remaining=1.0),
              "agy-gemini": Quota(provider="agy-gemini", weekly_remaining=0.9, daily_remaining=0.9)}
    assert _plan(cfg, quotas, size="M")[0].choice.model == "gemini-4-argon-high"
    assert _plan(cfg, quotas, size="L")[0].choice.model == "gemini-4-argon-high"
    assert _plan(cfg, quotas, size="S")[0].choice.model == "gemini-3.8-flash-high"
    # doc_text has no small_first entry: Argon first at every size
    assert _plan(cfg, quotas, role="script_writer", size="S")[0].choice.model == "gemini-4-argon-high"


@pytest.mark.parametrize("brief,want", [
    ("Capture the footage in Chrome and save the clips", True),
    ("Use mcp__claude-in-chrome__navigate to open the page", True),
    ("Generate image of the cover with Higgsfield", True),
    ("Write the EP62 script and the reply pack", False),
    ("Fix the browser compatibility bug in src/app.js", False),  # the product's browser, not the worker's
    ("edit-only: text only\n\nCapture the footage in Chrome", False),
    ("python3 tools/agy_browse.py --cdp http://x screenshot the page", False),
])
def test_needs_claude_tool(brief, want):
    assert forecast.needs_claude_tool(brief) is want


def test_live_plans_yaml():
    cfg = load_plans()
    assert cfg["roles"]["dev_general"][0] == "agy:gemini-4-argon-high"
    assert cfg["roles"]["doc_text"][0] == "agy:gemini-4-argon-high"
    assert cfg["roles"]["browser_agy"][0] == "agy:gemini-3.8-flash-high"
    assert cfg["small_first"]["dev_general"] == "agy:gemini-3.8-flash-high"
    assert cfg["role_classes"]["content_strategist"] == "doc_text"
    assert cfg["role_classes"]["script_writer"] == "doc_text"
    assert "prompt_engineer" not in cfg["role_classes"]


def test_codex_bonus_holds_codex_full_until_7_nov():
    bonuses = load_plans()["bonuses"]
    q = lambda: Quota(provider="codex", weekly_remaining=0.03, daily_remaining=0.03)  # noqa: E731
    assert apply_bonuses(q(), bonuses, datetime(2026, 10, 20, tzinfo=timezone.utc)).weekly_remaining == 1.0
    assert apply_bonuses(q(), bonuses, datetime(2026, 11, 6, 21, 0, tzinfo=timezone.utc)).weekly_remaining == 1.0
    assert apply_bonuses(q(), bonuses, datetime(2026, 11, 8, tzinfo=timezone.utc)).weekly_remaining == 0.03


def test_a_limit_stop_parks_the_task_for_the_ph(tmp_path, monkeypatch):
    launch = tmp_path / ".launch-task-x"
    launch.mkdir()
    (launch / "agy-events.log").write_text("step 1\nError: RESOURCE_EXHAUSTED: quota exceeded\n")
    task = {"id": "task-x", "runner": "agy", "review": json.dumps({"merge_sha": None, "keep": 1})}
    seen = {}
    monkeypatch.setattr(quota_handoff.db, "update_status",
                        lambda tid, status, **kw: seen.update(tid=tid, status=status, **kw))
    assert quota_handoff.record_limit_stop(task, launch_dir=launch) == "RESOURCE_EXHAUSTED"
    assert seen["tid"] == "task-x" and seen["status"] == "rate_limited"
    review = json.loads(seen["review"])
    assert review["quota_stop"] == "RESOURCE_EXHAUSTED" and review["keep"] == 1
    assert "quota_handoff.py task-x" in review["next"]


def test_no_limit_text_leaves_the_task_alone(tmp_path, monkeypatch):
    launch = tmp_path / ".launch-task-y"
    launch.mkdir()
    (launch / "agy-events.log").write_text("all done\n")
    monkeypatch.setattr(quota_handoff.db, "update_status", lambda *a, **k: pytest.fail("must not write"))
    assert quota_handoff.record_limit_stop({"id": "task-y", "runner": "agy"}, launch_dir=launch) is None
    assert quota_handoff.record_limit_stop({"id": "task-z", "runner": "claude"}, launch_dir=launch) is None


# --- The provider's own limit stop beats a configured bonus (CTO 15 Oct: Codex hit its weekly limit
# at 09:33 TH while the bonus still showed it full) ---------------------------------------------------

def _rl(used, resets=1792474078, limit_id="codex"):
    return json.dumps({"type": "event_msg", "payload": {"type": "token_count", "rate_limits": {
        "limit_id": limit_id, "primary": {"used_percent": used, "window_minutes": 10080, "resets_at": resets},
        "secondary": None}}})


_PREMIUM_NULL = json.dumps({"type": "event_msg", "payload": {"type": "token_count", "rate_limits": {
    "limit_id": "premium", "primary": None, "secondary": None}}})
_STOP = json.dumps({"type": "event_msg", "payload": {"type": "task_complete", "error": {
    "message": "You've hit your usage limit. ... try again at Oct 20th, 2026 7:27 AM.",
    "codex_error_info": "usage_limit_exceeded"}}})
_CLEAN = json.dumps({"type": "event_msg", "payload": {"type": "task_complete", "error": None}})
_BONUS = [{"provider": "openai", "from": "2026-10-15", "to": "2026-11-07T04:28:00+07:00", "note": "resets"}]


def test_window_at_100_is_a_limit_hit_and_a_null_premium_object_is_skipped():
    q = parse_codex([_rl(100.0), _PREMIUM_NULL])
    assert q.error is None and q.weekly_remaining == 0.0
    assert q.limit_hit and q.limit_until == "2026-10-20T05:27:58Z"


def test_usage_limit_stop_at_96_percent_zeroes_the_week():
    q = parse_codex([_rl(96.0), _STOP, _PREMIUM_NULL])
    assert q.limit_hit and q.weekly_remaining == 0.0 and q.limit_until == "2026-10-20T05:27:58Z"


def test_a_clean_turn_after_the_stop_clears_it():
    q = parse_codex([_rl(96.0), _STOP, _rl(5.0, resets=1793000000), _CLEAN])
    assert not q.limit_hit and q.weekly_remaining == 0.95


def test_limit_hit_beats_the_bonus_until_the_reset_then_the_bonus_applies():
    before = datetime(2026, 10, 18, tzinfo=timezone.utc)
    q = apply_bonuses(apply_limit_hit(parse_codex([_rl(100.0)]), before), _BONUS, before)
    assert q.weekly_remaining == 0.0 and "bonus ignored" in q.source

    after = datetime(2026, 10, 21, tzinfo=timezone.utc)
    q = apply_limit_hit(parse_codex([_rl(100.0)]), after)
    assert not q.limit_hit and q.weekly_remaining == 1.0
    assert apply_bonuses(q, _BONUS, after).weekly_remaining == 1.0


def test_a_limit_hit_codex_ranks_cannot(cfg):
    cfg["roles"]["dev_general"].insert(0, "codex:")
    now = datetime(2026, 10, 18, tzinfo=timezone.utc)
    quotas = {"claude": Quota(provider="claude", weekly_remaining=1.0, daily_remaining=1.0),
              "agy-gemini": Quota(provider="agy-gemini", weekly_remaining=0.9, daily_remaining=0.9),
              "codex": apply_bonuses(apply_limit_hit(parse_codex([_rl(100.0)]), now), _BONUS, now)}
    plans = _plan(cfg, quotas)
    codex = [p for p in plans if p.choice.runner == "codex"][0]
    assert codex.verdict == "cannot" and plans[-1] is codex, _runners(plans)


def test_snapshot_round_trips_the_limit_fields(tmp_path):
    q = parse_codex([_rl(100.0)])
    p = write_snapshot({"codex": q}, tmp_path / "snap.json")
    back = read_snapshot(p)["codex"]
    assert back.limit_hit and back.limit_until == q.limit_until


# --- A dead run ends failed --------------------------------------------------------------------------

def test_dead_run_fails_only_an_in_progress_row(monkeypatch):
    rows = {"t-a": {"id": "t-a", "status": "in_progress"}, "t-b": {"id": "t-b", "status": "review"}}
    seen = []
    monkeypatch.setattr(quota_handoff.db, "get_task", lambda tid: rows.get(tid))
    monkeypatch.setattr(quota_handoff.db, "update_status", lambda tid, st, **kw: seen.append((tid, st, kw)))
    assert quota_handoff.record_dead_run("t-a", "codex: no turn.completed") is True
    assert quota_handoff.record_dead_run("t-b", "codex: no turn.completed") is False
    assert seen == [("t-a", "failed", {"delegate_log": "dead run: codex: no turn.completed"})]


def test_check_stop_cli_prefers_rate_limited_over_failed(tmp_path, monkeypatch, capsys):
    launch = tmp_path / "launch"
    launch.mkdir()
    (launch / "agy-events.log").write_text("RESOURCE_EXHAUSTED\n")
    row = {"id": "t-c", "status": "in_progress", "runner": "agy"}
    seen = []
    monkeypatch.setattr(quota_handoff.db, "get_task", lambda tid: row)
    monkeypatch.setattr(quota_handoff.db, "update_status", lambda tid, st, **kw: seen.append(st))
    quota_handoff.main(["t-c", "--check-stop", "--runner", "agy", "--launch-dir", str(launch), "--dead", "x"])
    assert seen == ["rate_limited"]
    assert json.loads(capsys.readouterr().out)["dead_run_failed"] is False
