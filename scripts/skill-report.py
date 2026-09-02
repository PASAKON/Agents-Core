#!/usr/bin/env python3
"""scripts/skill-report.py — skill usage dashboard.

Reads state/skill-usage.log (TSV: ts \t skill_name \t session_id \t role,
legacy 3-field lines pad role to "-") plus every worker-stranded
worktrees/*/state/skill-usage.log (ADR 0022 §5 — belt-and-suspenders in
case the ~/.claude/settings.json hook registration ever regresses), and
prints a portfolio dashboard:

  - top 20 most used skills (fires, fires/wk since first fire, sessions,
    last modified, open/total objections, last fired)
  - never-used skills (available on disk but no log entry)
  - stale skills (used but last fire > 30 days ago)
  - cold skills (used once long ago, no follow-up)

"use=0" is NOT evidence a skill is bad — it's absence of evidence either
way (Hermes' own curator's rule, adopted here). Never-used skills get their
own informational section; they are never mixed into stale/cold, and
--brief never mentions them (see _print_dashboard).

Usage:
  python scripts/skill-report.py             # full dashboard
  python scripts/skill-report.py --json      # machine-readable
  python scripts/skill-report.py --unused    # only the never-used list
  python scripts/skill-report.py --brief     # one line, or nothing at all
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "state" / "skill-usage.log"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _skill_locations() -> dict[str, Path]:
    """skill name -> its SKILL.md's parent dir, across every location a
    session can see a skill from. Single source of truth for path
    resolution — `_discover_skills()` below derives its name set from this,
    and tools/skill_objection.py reuses it (dynamic import, same trick
    scripts/skill-curator.py uses for this file) for author lookup instead
    of re-walking these same three trees.

    Plugin skills under ~/.claude/plugins/marketplaces/<plugin>/skills/<name>/
    are exposed as '<plugin>:<name>' in the runtime, so record them that way.
    """
    found: dict[str, Path] = {}

    user_dir = Path.home() / ".claude" / "skills"
    if user_dir.is_dir():
        for child in user_dir.iterdir():
            if child.is_dir() and (child / "SKILL.md").is_file():
                found[child.name] = child

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
                    found[f"{prefix}:{skill.name}"] = skill

    project_dir = ROOT / ".claude" / "skills"
    if project_dir.is_dir():
        for child in project_dir.iterdir():
            if child.is_dir() and (child / "SKILL.md").is_file():
                found[child.name] = child

    return found


def _discover_skills() -> set[str]:
    """The set of available skill names — see _skill_locations() for paths."""
    return set(_skill_locations().keys())


def _git_updated_at(skill_md: Path) -> datetime | None:
    """`git log -1 --format=%cI -- <path>` — last commit that touched this
    SKILL.md, or None if it isn't (or isn't yet) tracked by any repo.

    `cwd=skill_md.parent` on purpose, same as skill-curator.py's
    `_git_added_at`: when the skill dir is itself a symlink (e.g.
    ~/.claude/skills/browser-operator -> this repo), chdir follows it to the
    real repo before git ever runs, which is what makes this resolve
    correctly through the external symlinks (measured, ADR 0022 §5).
    """
    try:
        proc = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", str(skill_md)],
            cwd=str(skill_md.parent), capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    line = (proc.stdout or "").strip()
    if not line:
        return None
    try:
        ts = datetime.fromisoformat(line)
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def _objection_summary(days: int = 30) -> dict[str, dict]:
    """tools/skill_objection.py's per-skill open/total + last conflict, for
    the `obj` column. Swallows a missing/uninitialized state/tasks.db (no
    events table yet) rather than crashing the whole dashboard over it —
    skill-report.py must still render when no worker has ever objected."""
    try:
        from tools.skill_objection import summary as _summary
        return _summary(days=days)
    except Exception:
        return {}


def _worktree_logs() -> list[Path]:
    """The worktree copies to fold in. Its own function so a test can stub the
    filesystem read out — globbing the real tree from inside _iter_log_lines()
    made every caller's result depend on how many worktrees happened to exist
    on the machine, which is not a property any test should assert against.
    """
    return sorted(ROOT.glob("worktrees/*/state/skill-usage.log"))


def _iter_log_lines() -> list[str]:
    """Every line from state/skill-usage.log plus any
    worktrees/*/state/skill-usage.log (ADR 0022 §5 — folded in so a
    regression of the ~/.claude/settings.json hook registration only
    strands fires, never hides them from this report). Deduped by raw line
    so a line present in both the main log and a worktree copy (e.g. after
    someone runs Wave 0's one-off recovery cat) is not double-counted.
    """
    lines: list[str] = []
    seen: set[str] = set()
    for src in [LOG, *_worktree_logs()]:
        if not src.is_file():
            continue
        for line in src.read_text().splitlines():
            if line and line not in seen:
                seen.add(line)
                lines.append(line)
    return lines


def _load_log() -> list[tuple[datetime, str, str, str]]:
    """Parse the folded log (see _iter_log_lines).

    Tolerant of legacy 3-field lines (ts, skill, session) written before the
    role column existed — those pad role to "-", same as a hook fire with no
    WORKER_ROLE/CXO_ROLE set.
    """
    out: list[tuple[datetime, str, str, str]] = []
    for line in _iter_log_lines():
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
    """(count, last, sessions) — unchanged 3-tuple shape (an external caller,
    scripts/test_hook_skill_log.py, unpacks exactly this). `/wk` needs each
    skill's FIRST fire too; that lives in the separate `_first_fires()`
    below rather than growing this tuple, so this signature never has to
    change again for a future column."""
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


def _first_fires(entries: list[tuple[datetime, str, str, str]]) -> dict[str, datetime]:
    """skill -> its own earliest fire — the denominator `/wk` measures from,
    per skill, not from the log's global start."""
    first: dict[str, datetime] = {}
    for ts, skill, _session, _role in entries:
        if skill not in first or ts < first[skill]:
            first[skill] = ts
    return first


def _fires_per_week(count: int, first_fire: datetime, now: datetime) -> float:
    """Fires/week measured from THIS skill's own first fire, not the log's
    start — a skill added last week must not look dead next to one added in
    June. Floored at a 1-week denominator so a skill fired 3 times an hour
    after being added doesn't report an absurd instantaneous rate."""
    weeks = max((now - first_fire).total_seconds() / (7 * 86400), 1.0)
    return count / weeks


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
    locations = _skill_locations()
    entries = _load_log()
    count, last, sessions = _summarize(entries)
    first = _first_fires(entries)
    used = set(count.keys())
    never_used = sorted(available - used)
    now = datetime.now(timezone.utc)

    stale_cutoff = now - timedelta(days=30)
    stale = [s for s, ts in last.items() if ts < stale_cutoff]
    objections = _objection_summary(days=30)
    open_objections = sum(rec["open"] for rec in objections.values())

    if "--brief" in args:
        # Zero bytes on a quiet day (CEO proposal C) — never-used skills are
        # NOT part of "quiet": silence alone is not a signal (§4.4/rule), so
        # they never trigger --brief output on their own.
        if not stale and not open_objections:
            return 0
        bits = []
        if stale:
            bits.append(f"{len(stale)} stale")
        if open_objections:
            bits.append(f"{open_objections} open skill objection"
                        + ("s" if open_objections != 1 else ""))
        print(f"  skill-report: {', '.join(bits)} — run scripts/skill-report.py for detail")
        return 0

    if "--json" in args:
        payload = {
            "totals": {
                "available": len(available),
                "used": len(used),
                "never_used": len(never_used),
                "total_fires": sum(count.values()),
                "stale": len(stale),
                "open_objections": open_objections,
            },
            "top_used": [
                {
                    "skill": s,
                    "count": c,
                    "fires_per_week": round(_fires_per_week(c, first[s], now), 2),
                    "last_fire": last[s].isoformat(),
                    "session_count": len(sessions[s]),
                    "updated": (
                        u.isoformat() if (loc := locations.get(s)) is not None
                        and (u := _git_updated_at(loc / "SKILL.md")) is not None else None
                    ),
                    "objections": objections.get(s, {"open": 0, "total": 0}),
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
          f"  total_fires={sum(count.values())}  stale={len(stale)}"
          f"  open_objections={open_objections}")
    print()

    print("  Top used")
    print(f"  {'#':>3}  {'skill':<40}  {'fires':>5}  {'/wk':>5}  {'sessions':>8}"
          f"  {'updated':<9}  {'obj':>5}  last")
    print(f"  {'-'*3}  {'-'*40}  {'-'*5}  {'-'*5}  {'-'*8}  {'-'*9}  {'-'*5}  ----")
    for i, (skill, c) in enumerate(count.most_common(20), 1):
        loc = locations.get(skill)
        updated_ts = _git_updated_at(loc / "SKILL.md") if loc is not None else None
        updated_str = _fmt_age(updated_ts, now) if updated_ts else "-"
        obj = objections.get(skill, {"open": 0, "total": 0})
        print(f"  {i:>3}  {skill[:40]:<40}  {c:>5}  {_fires_per_week(c, first[skill], now):>5.1f}"
              f"  {len(sessions[skill]):>8}  {updated_str:<9}  {obj['open']:>2}/{obj['total']:<2}"
              f"  {_fmt_age(last[skill], now)}")

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
        print(f"  Never used  ({len(never_used)} skills — NOT evidence of low value, just no data yet)")
        print("  Run with --unused for the full list, or:")
        print("    python scripts/skill-report.py --unused | head -20")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(_print_dashboard(sys.argv[1:]))
