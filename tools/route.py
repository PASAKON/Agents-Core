"""Runner router (Phase 2, part 1).

Ranks candidate runners for a task based on host availability, provider quotas,
skill scores, and CEO role preference order.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import functools
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.delegate import _host_runners
from tools.quota import Quota, fetch_all_quotas, load_plans, RUNNER_TO_PROVIDER


@dataclass
class Choice:
    candidate: str
    runner: str
    model: str
    weekly: float | None
    daily: float | None
    skill: float | None
    reason: str


class _CandidateItem:
    def __init__(
        self,
        idx: int,
        candidate: str,
        runner: str,
        model: str,
        weekly: float | None,
        daily: float | None,
        skill: float | None,
    ):
        self.idx = idx
        self.candidate = candidate
        self.runner = runner
        self.model = model
        self.weekly = weekly
        self.daily = daily
        self.skill = skill


def load_skill_scores() -> dict[tuple[str, str], float | None]:
    """Load skill scores per (runner, model). Stub for Phase 2."""
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

    if len(all_active) <= 1:
        if d_pct is not None:
            return f"only candidate on host with weekly {w_pct:.1f}%, daily {d_pct:.1f}%"
        return f"only candidate on host with weekly {w_pct:.1f}%"

    if rank_idx == 0:
        other = all_active[1]
        other_w_pct = other.weekly * 100
        other_d_pct = other.daily * 100 if other.daily is not None else None

        diff_w = item.weekly - other.weekly
        if abs(diff_w) > tie_threshold:
            return f"highest weekly remaining ({w_pct:.1f}% vs {other_w_pct:.1f}%)"

        # Weekly tied within tie_points/100 -> check daily
        if item.daily is not None and other.daily is not None:
            diff_d = item.daily - other.daily
            if abs(diff_d) > tie_threshold:
                return (
                    f"weekly tie within {tie_points}pp ({w_pct:.1f}% vs {other_w_pct:.1f}%), "
                    f"higher daily ({d_pct:.1f}% vs {other_d_pct:.1f}%)"
                )
        elif item.daily is not None and other.daily is None:
            return f"weekly tie within {tie_points}pp ({w_pct:.1f}% vs {other_w_pct:.1f}%), daily remaining {d_pct:.1f}%"

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

        diff_w = leader.weekly - item.weekly
        if abs(diff_w) > tie_threshold:
            return f"lower weekly remaining ({w_pct:.1f}% vs {leader_w_pct:.1f}%)"

        if leader.daily is not None and item.daily is not None:
            diff_d = leader.daily - item.daily
            if abs(diff_d) > tie_threshold:
                return (
                    f"weekly tie within {tie_points}pp ({w_pct:.1f}% vs {leader_w_pct:.1f}%), "
                    f"lower daily ({d_pct:.1f}% vs {leader_d_pct:.1f}%)"
                )
        elif leader.daily is not None and item.daily is None:
            return f"weekly tie within {tie_points}pp ({w_pct:.1f}% vs {leader_w_pct:.1f}%), no daily quota data"

        if leader.skill is not None and item.skill is not None and leader.skill != item.skill:
            return f"quota tie within {tie_points}pp, lower skill score ({item.skill:.2f} vs {leader.skill:.2f})"
        elif leader.skill is not None and item.skill is None:
            return f"quota tie within {tie_points}pp, lower skill score (unknown vs {leader.skill:.2f})"

        return f"tied within {tie_points}pp, behind in CEO order"


def rank(
    role: str,
    quotas: dict[str, Quota],
    skill: dict[tuple[str, str], float | None],
    host: str,
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
    available_runners = set(_host_runners(host))

    runner_to_provider = {
        v["runner"]: k for k, v in cfg.get("providers", {}).items() if isinstance(v, dict) and "runner" in v
    }
    runner_to_provider.update(RUNNER_TO_PROVIDER)

    min_samples = cfg.get("router", {}).get("min_samples", 5)
    tie_points = cfg.get("router", {}).get("tie_points", 5)
    tie_threshold = tie_points / 100.0

    filtered_items: list[_CandidateItem] = []
    for idx, cand_str in enumerate(raw_candidates):
        parts = cand_str.split(":")
        runner = parts[0]
        model = parts[1] if len(parts) > 1 else ""

        if runner not in available_runners:
            continue

        # Look up quota
        q = quotas.get(runner)
        if q is None:
            prov = runner_to_provider.get(runner)
            if prov:
                q = quotas.get(prov)
        if q is None:
            for cand_q in quotas.values():
                if cand_q.provider in (runner, runner_to_provider.get(runner)):
                    q = cand_q
                    break

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
                weekly=item.weekly,
                daily=item.daily,
                skill=item.skill,
                reason=reason,
            )
        )

    return choices


def main() -> None:
    parser = argparse.ArgumentParser(description="Rank runner candidates by quota and skill")
    parser.add_argument("--role", default="dev_general", help="Job role (e.g. dev_general)")
    parser.add_argument("--host", default="mac", help="Host name (e.g. mac, winbox, contabo)")
    parser.add_argument("--dry-run", action="store_true", help="Dry run routing")
    parser.add_argument("--config", help="Path to plans.yaml")
    args = parser.parse_args()

    cfg = load_plans(args.config)
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
