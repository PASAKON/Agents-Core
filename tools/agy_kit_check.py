#!/usr/bin/env python3
"""Check that an AGY room on this host sees every org skill (docs/design/cto-pair.md, 2026-11-19).

AGY loads `.agents/skills/*` first, then the paths in `.agents/skills.json`, under a context budget.
On 19 Nov 92 third-party finance skills in `.agents/skills` pushed 41 org skills in `.claude/skills`
out of that budget. This check fails when:
  - `.agents/skills.json` does not list `.claude/skills`;
  - `.agents/skills/` holds a skill that is not tracked in git (org skills belong in `.claude/skills`);
  - the total AGY would list is over the budget (default 180: 228 overflowed by 41 on 19 Nov).

Usage: python tools/agy_kit_check.py [--root DIR] [--budget N] [--json]   (exit 1 on a problem)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BUDGET = 180


def _skills(d: Path) -> list[str]:
    if not d.is_dir():
        return []
    return sorted(p.parent.name for p in d.glob("*/SKILL.md"))


def _tracked_agents_skills(root: Path) -> set[str]:
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files", ".agents/skills"],
                             capture_output=True, text=True, timeout=30, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return set()
    return {line.split("/")[2] for line in out.splitlines() if line.count("/") >= 3}


def check(root: Path = ROOT, budget: int = DEFAULT_BUDGET) -> dict:
    problems: list[str] = []
    cfg = root / ".agents" / "skills.json"
    paths: list[str] = []
    try:
        paths = [str(e.get("path", "")).rstrip("/") for e in json.loads(cfg.read_text()).get("entries", [])]
    except (OSError, ValueError, AttributeError):
        problems.append(f"{cfg.relative_to(root)} missing or unreadable")
    if ".claude/skills" not in paths:
        problems.append(".agents/skills.json does not list .claude/skills")
    agents = _skills(root / ".agents" / "skills")
    org = _skills(root / ".claude" / "skills")
    tracked = _tracked_agents_skills(root)
    stray = [s for s in agents if s not in tracked]
    if stray:
        problems.append(f".agents/skills holds {len(stray)} untracked skill(s) (move them to "
                        f".agents/parked-finance-skills/ or into .claude/skills): {', '.join(stray[:8])}")
    total = len(agents) + len(org)
    if total > budget:
        problems.append(f"AGY would list {total} skills, over the budget of {budget}")
    return {"ok": not problems, "org_skills": len(org), "agents_skills": len(agents),
            "untracked": stray, "total": total, "budget": budget, "problems": problems}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    r = check(a.root.resolve(), a.budget)
    if a.json:
        print(json.dumps(r, ensure_ascii=False))
    else:
        print(f"agy kit: {'OK' if r['ok'] else 'PROBLEM'} — org {r['org_skills']}, .agents {r['agents_skills']}, "
              f"total {r['total']}/{r['budget']}")
        for p in r["problems"]:
            print(f"  - {p}")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
