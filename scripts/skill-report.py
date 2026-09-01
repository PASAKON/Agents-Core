#!/usr/bin/env python3
"""scripts/skill-report.py — skill usage dashboard.

Reads state/skill-usage.log (TSV: ts \t skill_name \t session_id) and
prints a portfolio dashboard:

  - top 20 most used skills (count + last fired)
  - never-used skills (available on disk but no log entry)
  - stale skills (used but last fire > 30 days ago)
  - cold skills (used once long ago, no follow-up)

Usage:
  python scripts/skill-report.py             # full dashboard
  python scripts/skill-report.py --json      # machine-readable
  python scripts/skill-report.py --unused    # only the never-used list
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "state" / "skill-usage.log"


def _discover_skills() -> set[str]:
    """Scan known skill dirs and return the set of available skill names.

    Plugin skills under ~/.claude/plugins/marketplaces/<plugin>/skills/<name>/SKILL.md
    are exposed as '<plugin>:<name>' in the runtime, so record them that way.
    """
    found: set[str] = set()

    user_dir = Path.home() / ".claude" / "skills"
    if user_dir.is_dir():
        for child in user_dir.iterdir():
            if child.is_dir() and (child / "SKILL.md").is_file():
                found.add(child.name)

    plugins_root = Path.home() / ".claude" / "plugins" / "marketplaces"
    if plugins_root.is_dir():
        for plugin_dir in plugins_root.iterdir():
            if not plugin_dir.is_dir():
                continue
            skills_dir = plugin_dir / "skills"
            if not skills_dir.is_dir():
                continue
            prefix = plugin_dir.name.split("@")[0]
            for skill in skills_dir.iterdir():
                if skill.is_dir() and (skill / "SKILL.md").is_file():
                    found.add(f"{prefix}:{skill.name}")

    project_dir = ROOT / ".claude" / "skills"
    if project_dir.is_dir():
        for child in project_dir.iterdir():
            if child.is_dir() and (child / "SKILL.md").is_file():
                found.add(child.name)

    return found


def _load_log() -> list[tuple[datetime, str, str, str]]:
    """Parse state/skill-usage.log.

    Tolerant of legacy 3-field lines (ts, skill, session) written before the
    role column existed — those pad role to "-", same as a hook fire with no
    WORKER_ROLE/CXO_ROLE set.
    """
    if not LOG.is_file():
        return []
    out: list[tuple[datetime, str, str, str]] = []
    for line in LOG.read_text().splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        try:
            ts = datetime.fromisoformat(parts[0])
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        skill = parts[1].strip()
        session = parts[2].strip() if len(parts) >= 3 else ""
        role = parts[3].strip() if len(parts) >= 4 and parts[3].strip() else "-"
        out.append((ts, skill, session, role))
    return out


def _summarize(entries: list[tuple[datetime, str, str, str]]):
    count: Counter[str] = Counter()
    last: dict[str, datetime] = {}
    sessions: dict[str, set[str]] = defaultdict(set)
    for ts, skill, session, _role in entries:
        count[skill] += 1
        if skill not in last or ts > last[skill]:
            last[skill] = ts
        if session:
            sessions[skill].add(session)
    return count, last, sessions


def _fmt_age(ts: datetime, now: datetime) -> str:
    delta = now - ts
    if delta < timedelta(hours=24):
        return f"{int(delta.total_seconds() // 3600)}h ago"
    if delta < timedelta(days=30):
        return f"{delta.days}d ago"
    if delta < timedelta(days=365):
        return f"{delta.days // 30}mo ago"
    return f"{delta.days // 365}y ago"


def _print_dashboard(args: list[str]) -> int:
    available = _discover_skills()
    entries = _load_log()
    count, last, sessions = _summarize(entries)
    used = set(count.keys())
    never_used = sorted(available - used)
    now = datetime.now(timezone.utc)

    if "--json" in args:
        payload = {
            "totals": {
                "available": len(available),
                "used": len(used),
                "never_used": len(never_used),
                "total_fires": sum(count.values()),
            },
            "top_used": [
                {
                    "skill": s,
                    "count": c,
                    "last_fire": last[s].isoformat(),
                    "session_count": len(sessions[s]),
                }
                for s, c in count.most_common(50)
            ],
            "never_used": never_used,
        }
        print(json.dumps(payload, indent=2))
        return 0

    if "--unused" in args:
        for skill in never_used:
            print(skill)
        return 0

    print()
    print(f"  Skill portfolio  ({LOG})")
    print(f"  available={len(available)}  used={len(used)}  never_used={len(never_used)}"
          f"  total_fires={sum(count.values())}")
    print()

    print("  Top used")
    print(f"  {'#':>3}  {'skill':<40}  {'fires':>5}  {'sessions':>8}  last")
    print(f"  {'-'*3}  {'-'*40}  {'-'*5}  {'-'*8}  ----")
    for i, (skill, c) in enumerate(count.most_common(20), 1):
        print(f"  {i:>3}  {skill[:40]:<40}  {c:>5}  {len(sessions[skill]):>8}"
              f"  {_fmt_age(last[skill], now)}")

    stale_cutoff = now - timedelta(days=30)
    stale = [s for s, ts in last.items() if ts < stale_cutoff]
    if stale:
        print()
        print("  Stale (last fire > 30d ago)")
        for skill in sorted(stale, key=lambda s: last[s]):
            print(f"  - {skill}  ({_fmt_age(last[skill], now)})")

    single_use = [s for s, c in count.items() if c == 1 and last[s] < now - timedelta(days=14)]
    if single_use:
        print()
        print("  Cold (used once, >14d ago — verify still useful)")
        for skill in sorted(single_use):
            print(f"  - {skill}")

    if never_used:
        print()
        print(f"  Never used  ({len(never_used)} skills)")
        print("  Run with --unused for the full list, or:")
        print("    python scripts/skill-report.py --unused | head -20")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(_print_dashboard(sys.argv[1:]))
