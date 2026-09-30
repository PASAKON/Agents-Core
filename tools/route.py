"""Runner router (Phase 2, part 1).

Ranks candidate runners for a task based on host availability, provider quotas,
skill scores, and CEO role preference order.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import functools
import re
from datetime import datetime
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import forecast, limits as limits_mod, quota
from tools.delegate import _host_runners
from tools.quota import Quota, bucket_for, fetch_all_quotas, load_plans


@dataclass
class Choice:
    candidate: str
    runner: str
    model: str
    bucket: str | None
    weekly: float | None
    daily: float | None
    skill: float | None
    reason: str


@dataclass
class Plan:
    choice: Choice
    size: str
    cost: float | None
    cost_source: str
    after: float | None
    verdict: str
    why: str
    projection: str | None


class _CandidateItem:
    def __init__(
        self,
        idx: int,
        candidate: str,
        runner: str,
        model: str,
        bucket: str | None,
        weekly: float | None,
        daily: float | None,
        skill: float | None,
    ):
        self.idx = idx
        self.candidate = candidate
        self.runner = runner
        self.model = model
        self.bucket = bucket
        self.weekly = weekly
        self.daily = daily
        self.skill = skill


def load_skill_scores() -> dict[tuple[str, str], float | tuple[float, int] | None]:
    """Load skill scores per (runner, model), tolerating unavailable stats."""
    try:
        from tools import model_stats

        return model_stats.skill_scores(ROOT / "state" / "tasks.db", load_plans())
    except Exception:
        return {}


def _make_reason(
    item: _CandidateItem,
    rank_idx: int,
    all_active: list[_CandidateItem],
    tie_threshold: float,
    tie_points: int,
) -> str:
    if item.weekly is None:
        return "quota unknown"
    if item.weekly == 0.0 or (item.daily is not None and item.daily == 0.0):
        return "exhausted"

    w_pct = item.weekly * 100
    d_pct = item.daily * 100 if item.daily is not None else None
    item_b_str = f" {item.bucket}" if item.bucket else ""

    if len(all_active) <= 1:
        if d_pct is not None:
            return f"only candidate with a known quota on host with weekly {w_pct:.1f}%, daily {d_pct:.1f}%"
        return f"only candidate with a known quota on host with weekly {w_pct:.1f}%"

    if rank_idx == 0:
        other = all_active[1]
        other_w_pct = other.weekly * 100
        other_d_pct = other.daily * 100 if other.daily is not None else None
        other_b_str = f" {other.bucket}" if other.bucket else ""

        diff_w = item.weekly - other.weekly
        if abs(diff_w) > tie_threshold:
            return f"highest weekly remaining ({w_pct:.1f}%{item_b_str} vs {other_w_pct:.1f}%{other_b_str})"

        # Weekly tied within tie_points/100 -> check daily
        if item.daily is not None and other.daily is not None:
            diff_d = item.daily - other.daily
            if abs(diff_d) > tie_threshold:
                return (
                    f"weekly tie within {tie_points}pp ({w_pct:.1f}%{item_b_str} vs {other_w_pct:.1f}%{other_b_str}), "
                    f"higher daily ({d_pct:.1f}% vs {other_d_pct:.1f}%)"
                )
        elif item.daily is not None and other.daily is None:
            return f"weekly tie within {tie_points}pp ({w_pct:.1f}%{item_b_str} vs {other_w_pct:.1f}%{other_b_str}), daily remaining {d_pct:.1f}%"

        # Daily tied or both None -> check skill
        if item.skill is not None and other.skill is not None and item.skill != other.skill:
            return f"quota tie within {tie_points}pp, higher skill score ({item.skill:.2f} vs {other.skill:.2f})"
        elif item.skill is not None and other.skill is None:
            return f"quota tie within {tie_points}pp, higher skill score ({item.skill:.2f} vs unknown)"

        return f"tied within {tie_points}pp, preferred by CEO order"
    else:
        leader = all_active[0]
        leader_w_pct = leader.weekly * 100
        leader_d_pct = leader.daily * 100 if leader.daily is not None else None
        leader_b_str = f" {leader.bucket}" if leader.bucket else ""

        diff_w = leader.weekly - item.weekly
        if abs(diff_w) > tie_threshold:
            return f"lower weekly remaining ({w_pct:.1f}%{item_b_str} vs {leader_w_pct:.1f}%{leader_b_str})"

        if leader.daily is not None and item.daily is not None:
            diff_d = leader.daily - item.daily
            if abs(diff_d) > tie_threshold:
                return (
                    f"weekly tie within {tie_points}pp ({w_pct:.1f}%{item_b_str} vs {leader_w_pct:.1f}%{leader_b_str}), "
                    f"lower daily ({d_pct:.1f}% vs {leader_d_pct:.1f}%)"
                )
        elif leader.daily is not None and item.daily is None:
            return f"weekly tie within {tie_points}pp ({w_pct:.1f}%{item_b_str} vs {leader_w_pct:.1f}%{leader_b_str}), no daily quota data"

        if leader.skill is not None and item.skill is not None and leader.skill != item.skill:
            return f"quota tie within {tie_points}pp, lower skill score ({item.skill:.2f} vs {leader.skill:.2f})"
        elif leader.skill is not None and item.skill is None:
            return f"quota tie within {tie_points}pp, lower skill score (unknown vs {leader.skill:.2f})"

        return f"tied within {tie_points}pp, behind in CEO order"


def rank(
    role: str,
    quotas: dict[str, Quota],
    skill: dict[tuple[str, str], float | None],
    host: str | None = None,
    cfg: dict | None = None,
) -> list[Choice]:
    """Rank candidate runners for `role` on `host` based on quotas and skill."""
    if cfg is None:
        cfg = load_plans()

    roles_cfg = cfg.get("roles", {})
    raw_candidates = roles_cfg.get(role, [])
    if not raw_candidates:
        return []

    # Rule 1: Only candidates from roles[role] whose runner is in host's runners
    available_runners = set(_host_runners(host)) if host is not None else None

    min_samples = cfg.get("router", {}).get("min_samples", 5)
    tie_points = cfg.get("router", {}).get("tie_points", 5)
    tie_threshold = tie_points / 100.0

    filtered_items: list[_CandidateItem] = []
    for idx, cand_str in enumerate(raw_candidates):
        parts = cand_str.split(":")
        runner = parts[0]
        model = parts[1] if len(parts) > 1 else ""

        if available_runners is not None and runner not in available_runners:
            continue

        # Look up quota
        bucket = bucket_for(cand_str, cfg)
        q = quotas.get(bucket) if bucket else None

        weekly = q.weekly_remaining if (q and q.error is None) else None
        daily = q.daily_remaining if (q and q.error is None) else None

        # Look up skill score
        skill_val = skill.get((runner, model))
        if skill_val is None and len(parts) > 2:
            skill_val = skill.get((runner, ":".join(parts[1:])))

        if isinstance(skill_val, tuple):
            score, count = skill_val
            skill_score = float(score) if count >= min_samples else None
        elif skill_val is not None:
            skill_score = float(skill_val)
        else:
            skill_score = None

        filtered_items.append(
            _CandidateItem(
                idx=idx,
                candidate=cand_str,
                runner=runner,
                model=model,
                bucket=bucket,
                weekly=weekly,
                daily=daily,
                skill=skill_score,
            )
        )

    if not filtered_items:
        return []

    # Rule 2: Candidates whose provider quota is unknown (weekly None) go LAST
    known_items: list[_CandidateItem] = []
    unknown_items: list[_CandidateItem] = []
    for item in filtered_items:
        if item.weekly is None:
            unknown_items.append(item)
        else:
            known_items.append(item)

    # Rule 6: Weekly or daily == 0 -> candidate moves to the end, reason "exhausted"
    active_items: list[_CandidateItem] = []
    exhausted_items: list[_CandidateItem] = []
    for item in known_items:
        if item.weekly == 0.0 or (item.daily is not None and item.daily == 0.0):
            exhausted_items.append(item)
        else:
            active_items.append(item)

    # Sort active candidates by rules 3, 4, 5
    def compare_active(a: _CandidateItem, b: _CandidateItem) -> int:
        # Rule 3: weekly remaining, highest first
        diff = a.weekly - b.weekly
        if abs(diff) > tie_threshold:
            return -1 if diff > 0 else 1

        # Rule 4: If weekly differs by <= tie_points/100 -> compare daily remaining
        if a.daily is not None and b.daily is not None:
            d_diff = a.daily - b.daily
            if abs(d_diff) > tie_threshold:
                return -1 if d_diff > 0 else 1
        elif a.daily is not None and b.daily is None:
            return -1
        elif a.daily is None and b.daily is not None:
            return 1

        # Rule 5: Still tied -> higher skill score wins. None skill counts as lower than any number
        if a.skill is not None and b.skill is not None:
            if a.skill != b.skill:
                return -1 if a.skill > b.skill else 1
        elif a.skill is not None and b.skill is None:
            return -1
        elif a.skill is None and b.skill is not None:
            return 1

        # Still tied -> keep the CEO's order from roles
        return -1 if a.idx < b.idx else 1

    active_items.sort(key=functools.cmp_to_key(compare_active))

    # Keep CEO order within exhausted and unknown groups
    exhausted_items.sort(key=lambda x: x.idx)
    unknown_items.sort(key=lambda x: x.idx)

    # Build final list of choices: active first, then unknown (Rule 2) or exhausted (Rule 6 moved to end)
    # Notice: active -> unknown -> exhausted puts exhausted at the end, while unknown goes after active.
    # In both single-failure cases (unknown alone or exhausted alone), the problematic candidate is last.
    ranked_items = active_items + unknown_items + exhausted_items

    choices: list[Choice] = []
    for rank_idx, item in enumerate(ranked_items):
        reason = _make_reason(item, rank_idx, active_items, tie_threshold, tie_points)
        choices.append(
            Choice(
                candidate=item.candidate,
                runner=item.runner,
                model=item.model,
                bucket=item.bucket,
                weekly=item.weekly,
                daily=item.daily,
                skill=item.skill,
                reason=reason,
            )
        )

    return choices


QUOTA_TTL_S = 300
QUOTA_RETRY_S = 60

_quota_cache: dict = {"at": 0.0, "quotas": {}}
_QUOTA_CACHE = _quota_cache


def cached_quotas(
    cfg: dict,
    *,
    now: float | None = None,
    ttl: int = QUOTA_TTL_S,
) -> dict[str, Quota]:
    global _quota_cache
    current_time = time.monotonic() if now is None else now

    at = _quota_cache.get("at", 0.0)
    cached = _quota_cache.get("quotas")
    if cached and (current_time - at < ttl):
        return cached

    snapshot = quota.read_snapshot(quota.SNAPSHOT_PATH)
    if isinstance(snapshot, dict) and not any(q.error for q in snapshot.values()):
        _quota_cache["at"] = current_time
        _quota_cache["quotas"] = snapshot
        return snapshot

    quotas = fetch_all_quotas(cfg)
    # A failed read ranks its provider "quota unknown" (last). Keep it only
    # QUOTA_RETRY_S, not the full TTL: the agy /usage call timed out 1 read
    # in 3 on 2026-09-29, and a cached miss would send every delegate in the
    # next 5 minutes to the fallback runner.
    if any(q.error for q in quotas.values()):
        current_time -= max(ttl - QUOTA_RETRY_S, 0)
    _quota_cache["at"] = current_time
    _quota_cache["quotas"] = quotas
    return quotas


def plan(
    role: str,
    size: str | None = None,
    *,
    touches: list | tuple | None = None,
    brief: str | None = None,
    host: str | None = None,
    cfg: dict | None = None,
    quotas: dict[str, Quota] | None = None,
    skill: dict[tuple[str, str], float | None] | None = None,
    limits: dict[str, dict] | None = None,
    table: dict | None = None,
    now: datetime | None = None,
    needs_shell: bool | None = None,
) -> list[Plan]:
    """Plan candidate runners for role with quota forecasts and verdicts."""
    try:
        if cfg is None:
            cfg = load_plans()

        role_classes = cfg.get("role_classes") or {}
        roles = cfg.get("roles") or {}
        if role in role_classes:
            role_cls = role_classes[role]
        elif role in roles:
            role_cls = role
        else:
            return []

        if size is None:
            size = forecast.infer_size(touches, brief)

        if needs_shell is None:
            needs_shell = forecast.needs_shell(brief)

        shell_runners = cfg.get("shell_runners")
        if shell_runners is None:
            shell_runners = ["claude", "codex"]

        if quotas is None:
            quotas = cached_quotas(cfg)
        if skill is None:
            skill = load_skill_scores()
        if limits is None:
            limits = limits_mod.load_limits()

        choices = rank(role_cls, quotas, skill, host=host, cfg=cfg)
        plans: list[Plan] = []
        for c in choices:
            bucket = c.bucket
            q = quotas.get(bucket) if bucket else None
            limit_row = limits.get(bucket, {}) if (limits and bucket) else {}
            cost, cost_source = (
                forecast.cost_for(bucket, size, limits=limits, table=table)
                if (bucket and limits)
                else (None, "no cost data")
            )
            v, after, why = forecast.verdict(q, cost, limit_row)
            rate = forecast.burn_rate(bucket, now=now) if bucket else None
            reserve_pct = limit_row.get("reserve_pct", 0)
            proj = forecast.projection(bucket, q, rate, reserve_pct, now=now) if (bucket and q) else None
            if needs_shell and c.runner not in shell_runners:
                v = "cannot"
                why = f"needs shell; {c.runner} is edit-only"
            plans.append(
                Plan(
                    choice=c,
                    size=size,
                    cost=cost,
                    cost_source=cost_source,
                    after=after,
                    verdict=v,
                    why=why,
                    projection=proj,
                )
            )

        ok_plans = [p for p in plans if p.verdict == "ok"]
        unknown_plans = [p for p in plans if p.verdict == "unknown"]
        will_hit_plans = [p for p in plans if p.verdict == "will_hit"]
        cannot_plans = [p for p in plans if p.verdict == "cannot"]
        return ok_plans + unknown_plans + will_hit_plans + cannot_plans
    except Exception:
        return []


def plan_line(p: Plan) -> str:
    """Format a single plan entry into a concise summary line."""
    c = p.choice
    runner_model = f"{c.runner} {c.model}"
    bucket_part = f"bucket {c.bucket}" if c.bucket else "no bucket"

    if c.weekly is not None and p.after is not None:
        w_str = forecast.fmt_pct(c.weekly * 100)
        a_str = forecast.fmt_pct(p.after * 100)
        cost_str = f"≈{forecast.fmt_pct(p.cost * 100)}" if p.cost is not None else "cost unknown"
        bracket = f"({p.size} {cost_str})"
        stats_part = f"{w_str}→{a_str} {bracket}"
    else:
        stats_part = ""

    if p.verdict == "ok":
        verdict_part = p.why
    else:
        verdict_part = f"{p.verdict}: {p.why}"

    parts = [f"{runner_model} · {bucket_part}"]
    if stats_part:
        parts.append(stats_part)
    parts.append(verdict_part)
    return " ".join(parts)


# GH #188: a browser_operator task runs on agy only when its brief drives the
# Browser Home through tools/agy_browse.py AND names the Home's CDP URL. Any
# other browser task keeps the Claude-only tools and is never routed.
BROWSER_AGY_CLASS = "browser_agy"
_AGY_BROWSE_RE = re.compile(r"(?<![\w/])tools/agy_browse\.py\b")
_CDP_URL_RE = re.compile(r"\bhttp://127\.0\.0\.1:\d{4,5}\b")


def class_for(role: str, brief: str | None, cfg: dict) -> str | None:
    """The router class for a worker role, or None to stay on Claude."""
    cls = (cfg.get("role_classes") or {}).get(role)
    if cls:
        return cls
    if (role == "browser_operator" and brief
            and BROWSER_AGY_CLASS in (cfg.get("roles") or {})
            and _AGY_BROWSE_RE.search(brief) and _CDP_URL_RE.search(brief)):
        return BROWSER_AGY_CLASS
    return None


def pick_runner(
    role: str,
    host: str,
    *,
    touches: list | tuple | None = None,
    brief: str | None = None,
    size: str | None = None,
    cfg: dict | None = None,
    quotas: dict | None = None,
    skill: dict | None = None,
    limits: dict | None = None,
    table: dict | None = None,
    now: datetime | None = None,
    needs_shell: bool | None = None,
) -> Choice | None:
    try:
        cfg = cfg or load_plans()
        cls = class_for(role, brief, cfg)
        if not cls:
            return None
        quotas = quotas if quotas is not None else cached_quotas(cfg)
        skill = skill if skill is not None else load_skill_scores()

        plans = plan(
            cls,
            size=size,
            touches=touches,
            brief=brief,
            host=host,
            cfg=cfg,
            quotas=quotas,
            skill=skill,
            limits=limits,
            table=table,
            now=now,
            needs_shell=needs_shell,
        )

        for p in plans:
            if p.verdict == "ok":
                p.choice.reason = plan_line(p)
                return p.choice

        for p in plans:
            if p.verdict != "cannot" and "exhausted" not in p.choice.reason:
                p.choice.reason = f"no ok candidate, fallback: {p.choice.reason}"
                return p.choice
        return None
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Rank runner candidates by quota and skill")
    parser.add_argument("--role", default="dev_general", help="Job role (e.g. dev_general)")
    parser.add_argument("--host", default="mac", help="Host name (e.g. mac, winbox, contabo)")
    parser.add_argument("--dry-run", action="store_true", help="Dry run routing")
    parser.add_argument("--config", help="Path to plans.yaml")
    parser.add_argument("--pick", metavar="ROLE", help="Pick single runner for worker role (e.g. developer)")
    parser.add_argument("--plan", metavar="ROLE", help="Plan routing for worker role or class")
    parser.add_argument("--size", choices=["S", "M", "L"], help="Task size (S, M, L)")
    parser.add_argument("--needs-shell", action="store_true", help="Task requires arbitrary shell commands")
    args = parser.parse_args()

    cfg = load_plans(args.config)

    if args.plan:
        plans = plan(
            args.plan,
            size=args.size,
            host=args.host,
            cfg=cfg,
            needs_shell=True if args.needs_shell else None,
        )
        for i, p in enumerate(plans, 1):
            print(f"{i}. {plan_line(p)}")
            if p.projection:
                print(f"   {p.projection}")
        return

    if args.pick:
        choice = pick_runner(
            args.pick,
            args.host,
            cfg=cfg,
            needs_shell=True if args.needs_shell else None,
        )
        if choice is not None:
            print(f"runner={choice.runner} model={choice.model} reason={choice.reason}")
        else:
            print("runner=none (stay on claude)")
        return

    quotas = fetch_all_quotas(cfg)
    skill = load_skill_scores()

    choices = rank(args.role, quotas, skill, args.host, cfg)
    if not choices:
        print(f"No available candidates for role {args.role!r} on host {args.host!r}")
        return

    print(f"Ranked candidates for role {args.role!r} on host {args.host!r}:")
    for i, c in enumerate(choices, 1):
        w = f"{c.weekly * 100:.1f}%" if c.weekly is not None else "None"
        d = f"{c.daily * 100:.1f}%" if c.daily is not None else "None"
        s = f"{c.skill:.2f}" if c.skill is not None else "None"
        print(f"{i}. {c.candidate} [weekly: {w}, daily: {d}, skill: {s}] -> {c.reason}")


if __name__ == "__main__":
    main()

