#!/usr/bin/env python3
"""scripts/skill-curator.py — skill lifecycle curator (ADR 0018).

Turns the read-only telemetry from scripts/skill-report.py into a lifecycle:
propose stale/archive transitions, and let a human apply them. Never runs
unattended (ADR 0017 — no daemon); a C-level invokes verbs by hand.

Verbs:
  status                  lifecycle table: name, created_by, state, use_count,
                           last_used, pinned. Read-only.
  propose                 what WOULD transition, and why. Mutates nothing.
  archive <name>          move a skill to the archive dir. The only mutating
                           verb that touches a skill's files.
  restore <name>          bring an archived skill back.
  pin <name>              exempt a skill from every future transition.
  unpin <name>            undo pin.

Five invariants (non-negotiable, ADR 0018 §4):
  1. Never deletes — archive is restorable via `restore`.
  2. Only touches created_by: agent — human-authored skills (including every
     skill with no created_by field — absent means human) are read-only.
  3. Refuses any path that resolves through a symlink escaping
     .claude/skills/ — this is what keeps the curator out of external/*.
  4. Pinned skills are exempt from every transition and from archive itself.
  5. Backs up before any mutation — a timestamped copy under
     state/skill-curator-backups/, independent of `restore`'s own move-back.

Usage discovery reuses scripts/skill-report.py's _discover_skills() (imported,
not duplicated) for the full ~/.claude/skills + plugins portfolio. The curator
itself may only ever mutate paths under .claude/skills/ in this repo.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

ROOT = Path(__file__).resolve().parent.parent

STALE_AFTER_DAYS = 30
ARCHIVE_AFTER_DAYS = 60  # stale for a further 30 days, per ADR 0018 §3

_SKILL_REPORT_PATH = Path(__file__).resolve().parent / "skill-report.py"


class CuratorError(Exception):
    """An invariant refused the requested action."""


def _load_skill_report():
    """Import scripts/skill-report.py by path (hyphenated filename).

    Reused, not duplicated, per the task brief: _discover_skills() is the
    single place that knows where skills live (~/.claude/skills, plugin
    marketplaces, and this repo's .claude/skills).
    """
    spec = importlib.util.spec_from_file_location("_skill_report", _SKILL_REPORT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@dataclass
class CuratorPaths:
    owned_skills_dir: Path
    log_path: Path
    state_path: Path
    archive_dir: Path
    backup_dir: Path
    # Full-portfolio views (status/propose) pull in ~/.claude/skills + plugins
    # via skill-report's discovery. Tests set this False to stay entirely
    # inside tmp_path — never touching ~/.claude/skills or the real log.
    merge_external: bool = True

    @classmethod
    def default(cls) -> "CuratorPaths":
        return cls(
            owned_skills_dir=ROOT / ".claude" / "skills",
            log_path=ROOT / "state" / "skill-usage.log",
            state_path=ROOT / "state" / "skill-usage.json",
            archive_dir=ROOT / ".claude" / "skills-archive",
            backup_dir=ROOT / "state" / "skill-curator-backups",
        )


# --------------------------------------------------------------------------
# Scope safety (invariant 3)
# --------------------------------------------------------------------------

def _resolve_within(name: str, base: Path) -> Path:
    """Resolve base/name and refuse if it is, or resolves through, a symlink
    escaping base. Never returns a path outside base.

    Raises CuratorError on any invalid or unsafe name.
    """
    if not name or "/" in name or "\\" in name or name in (".", ".."):
        raise CuratorError(f"invalid skill name: {name!r}")

    candidate = base / name
    if candidate.is_symlink():
        raise CuratorError(
            f"{name!r} is a symlink under {base} — refusing "
            "(invariant 3: no symlink may escape .claude/skills/)"
        )

    base_resolved = base.resolve()
    resolved = candidate.resolve()
    try:
        resolved.relative_to(base_resolved)
    except ValueError:
        raise CuratorError(
            f"{name!r} resolves to {resolved}, outside {base_resolved} — refusing "
            "(invariant 3: no symlink may escape .claude/skills/)"
        )
    return candidate


# --------------------------------------------------------------------------
# Frontmatter + usage log
# --------------------------------------------------------------------------

def _read_frontmatter(skill_dir: Path) -> dict:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return {}
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        data = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _created_by(skill_dir: Path) -> str:
    """created_by from frontmatter. Absent, unknown, or unreadable -> human.

    This default is the whole safety story for invariant 2: every skill that
    predates this field, or whose SKILL.md the curator can't parse, is
    protected rather than assumed fair game.

    A *present but invalid* value (e.g. `created_by: cto` -- a role, which
    belongs in `author:`, not here) used to coerce to "human" silently. That
    silence is what let a typo take a skill outside the curator's reach with
    no error and no log line (ADR 0022). The coercion itself is unchanged --
    still fail-closed to "human" -- but it is no longer silent: it prints to
    stderr naming the file and the bad value.
    """
    value = _read_frontmatter(skill_dir).get("created_by")
    if value is not None and value not in ("human", "agent"):
        print(
            f"WARNING: {skill_dir / 'SKILL.md'}: created_by={value!r} is not "
            "'human' or 'agent' -- coercing to 'human' (see ADR 0022 section 3: "
            "the role belongs in author:, never in created_by)",
            file=sys.stderr,
        )
    return value if value in ("human", "agent") else "human"


def _load_log_tsv(log_path: Path) -> list[tuple[datetime, str, str, str]]:
    """Local TSV reader for the merge_external=False (test) path — reads an
    arbitrary log_path rather than skill-report.py's hardcoded LOG constant.

    Tolerant of legacy 3-field lines (ts, skill, session) written before the
    role column existed — those pad role to "-".
    """
    if not log_path.is_file():
        return []
    out: list[tuple[datetime, str, str, str]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
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


def _aggregate_usage(entries: list[tuple[datetime, str, str, str]]) -> dict[str, dict]:
    agg: dict[str, dict] = {}
    for ts, skill, _session, _role in entries:
        rec = agg.setdefault(skill, {"use_count": 0, "first_seen_at": ts, "last_used_at": ts})
        rec["use_count"] += 1
        if ts < rec["first_seen_at"]:
            rec["first_seen_at"] = ts
        if ts > rec["last_used_at"]:
            rec["last_used_at"] = ts
    return agg


def _git_added_at(path: Path) -> Optional[datetime]:
    """When this file first entered git history, or None if unknowable.

    mtime cannot answer "how long has this skill existed": git rewrites it on
    every checkout, worktree creation, and rebase. Measured 2026-08-13 — the
    same SKILL.md read 17:33 in a fresh worktree and 03:54 in the main
    checkout, neither being when the skill was written. The first-commit date
    survives all of that.
    """
    try:
        proc = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%aI", "-1", "--", str(path)],
            cwd=str(path.parent), capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    lines = (proc.stdout or "").strip().splitlines()
    if not lines:
        return None
    try:
        ts = datetime.fromisoformat(lines[0].strip())
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def _idle_since_unused(
    skill_md: Path, observation_start: Optional[datetime]
) -> Optional[datetime]:
    """Idle clock for a skill the telemetry log has never seen fire.

    "Idle since" is the LATER of two facts, because either alone can call a
    skill stale when it is not:

      - when we started watching (`observation_start`, the log's earliest
        entry) — a skill cannot be judged over a period we were not recording
      - when the skill first existed (`_git_added_at`) — one added yesterday is
        not stale merely because the log is older than it

    None means "no basis to judge", and the caller then proposes nothing.
    """
    candidates = [
        c for c in (observation_start, _git_added_at(skill_md)) if c is not None
    ]
    return max(candidates) if candidates else None


def _scan_skill_dir(d: Path) -> set[str]:
    if not d.is_dir():
        return set()
    return {
        child.name
        for child in d.iterdir()
        if child.is_dir() and not child.is_symlink() and (child / "SKILL.md").is_file()
    }


# --------------------------------------------------------------------------
# Sidecar state (state/skill-usage.json) — read/write helpers
# --------------------------------------------------------------------------

def _load_state(state_path: Path) -> dict:
    if not state_path.is_file():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(state_path: Path, state: dict) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------
# Portfolio — the read-only merged view used by status/propose
# --------------------------------------------------------------------------

def build_portfolio(paths: CuratorPaths) -> dict[str, dict]:
    """Full projection: every known skill + its lifecycle state.

    Read-only — never writes state_path. Callers that want the decision
    persisted go through archive/restore/pin/unpin, which each do a
    read-modify-write on top of this same computation.
    """
    owned_names = _scan_skill_dir(paths.owned_skills_dir)
    archived_names = _scan_skill_dir(paths.archive_dir)
    names = set(owned_names) | set(archived_names)

    if paths.merge_external:
        skill_report = _load_skill_report()
        names |= skill_report._discover_skills()
        # skill-report.py's ROOT is derived from its own file location, which
        # inside a git worktree is NOT the real telemetry file (state/ is
        # gitignored per-worktree). Point it at our log_path so callers get
        # real numbers when they construct CuratorPaths against a real root.
        skill_report.LOG = paths.log_path
        entries = skill_report._load_log()
    else:
        entries = _load_log_tsv(paths.log_path)

    usage = _aggregate_usage(entries)
    # Earliest entry in the whole log = when telemetry started. A skill with
    # zero uses has been idle at least since then, and cannot be judged over
    # any period before it.
    observation_start = min((e[0] for e in entries), default=None)
    existing_state = _load_state(paths.state_path)
    names |= set(existing_state.keys())

    now = datetime.now(timezone.utc)
    portfolio: dict[str, dict] = {}
    for name in sorted(names):
        prior = existing_state.get(name, {})

        if name in archived_names:
            skill_dir: Optional[Path] = paths.archive_dir / name
        elif name in owned_names:
            skill_dir = paths.owned_skills_dir / name
        else:
            skill_dir = None

        created_by = _created_by(skill_dir) if skill_dir is not None else prior.get("created_by", "human")

        u = usage.get(name)
        if u:
            use_count = u["use_count"]
            first_seen_at = u["first_seen_at"]
            last_used_at = u["last_used_at"]
        else:
            use_count = 0
            last_used_at = None
            first_seen_at = None
            if skill_dir is not None and (skill_dir / "SKILL.md").is_file():
                # Never invoked. mtime is NOT the idle clock — git rewrites it
                # on checkout/worktree/rebase, so every skill looks brand new
                # in a fresh worktree and nothing is ever proposed. See
                # _idle_since_unused for what replaces it.
                first_seen_at = _idle_since_unused(
                    skill_dir / "SKILL.md", observation_start
                )

        # The filesystem is ground truth for archived vs active; a stored
        # lifecycle only matters when it disagrees with what's on disk (e.g.
        # the JSON was edited by hand, or a skill was moved outside the CLI).
        if name in archived_names:
            lifecycle = "archived"
        else:
            lifecycle = prior.get("lifecycle") if prior.get("lifecycle") in ("active", "archived") else "active"
            if lifecycle == "archived" and name not in archived_names:
                lifecycle = "active"

        pinned = bool(prior.get("pinned", False))

        idle_reference = last_used_at or first_seen_at
        idle_days = (now - idle_reference).days if idle_reference else None

        display_state = lifecycle
        if pinned and lifecycle != "archived":
            display_state = "pinned"
        elif lifecycle == "active" and idle_days is not None and idle_days >= STALE_AFTER_DAYS:
            display_state = "stale"

        portfolio[name] = {
            "use_count": use_count,
            "first_seen_at": first_seen_at,
            "last_used_at": last_used_at,
            "lifecycle": lifecycle,
            "pinned": pinned,
            "created_by": created_by,
            "idle_days": idle_days,
            "display_state": display_state,
            "in_owned_scope": name in owned_names,
        }
    return portfolio


@dataclass
class Proposal:
    name: str
    action: str  # "stale" | "archived"
    reason: str
    actionable: bool  # True only if the curator could actually apply it


def compute_proposals(paths: CuratorPaths) -> list[Proposal]:
    """What WOULD transition, and why. Read-only — calls build_portfolio only."""
    portfolio = build_portfolio(paths)
    proposals: list[Proposal] = []
    for name, entry in portfolio.items():
        if entry["pinned"] or entry["lifecycle"] == "archived":
            continue
        idle_days = entry["idle_days"]
        if idle_days is None:
            continue
        if idle_days >= ARCHIVE_AFTER_DAYS:
            action = "archived"
        elif idle_days >= STALE_AFTER_DAYS:
            action = "stale"
        else:
            continue
        actionable = entry["created_by"] == "agent" and entry["in_owned_scope"]
        reason = f"idle {idle_days}d, created_by={entry['created_by']}"
        proposals.append(Proposal(name=name, action=action, reason=reason, actionable=actionable))
    return proposals


# --------------------------------------------------------------------------
# Mutating verbs — archive, restore, pin, unpin
# --------------------------------------------------------------------------

def _backup_skill(paths: CuratorPaths, name: str, skill_dir: Path) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    dest = paths.backup_dir / name / ts
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(skill_dir, dest)
    return dest


def archive_skill(paths: CuratorPaths, name: str) -> dict:
    """Move an agent-authored, unpinned, in-scope skill to the archive dir.

    Refuses (CuratorError) on: symlink/scope escape, created_by != agent,
    pinned, missing, or already archived. Backs up before moving.
    """
    safe_path = _resolve_within(name, paths.owned_skills_dir)
    if not safe_path.is_dir() or not (safe_path / "SKILL.md").is_file():
        raise CuratorError(f"{name!r} not found under {paths.owned_skills_dir}")

    created_by = _created_by(safe_path)
    if created_by != "agent":
        raise CuratorError(
            f"{name!r} is created_by={created_by!r} — human-authored skills are "
            "read-only to the curator (invariant 2)"
        )

    state = _load_state(paths.state_path)
    if state.get(name, {}).get("pinned"):
        raise CuratorError(f"{name!r} is pinned — unpin before archiving (invariant 4)")

    dest = paths.archive_dir / name
    if dest.exists():
        raise CuratorError(f"{name!r} already exists in {paths.archive_dir} — already archived?")

    _backup_skill(paths, name, safe_path)  # invariant 5: snapshot before any mutation

    paths.archive_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(safe_path), str(dest))

    entry = state.get(name, {})
    entry.update(
        {
            "created_by": created_by,
            "lifecycle": "archived",
            "pinned": False,
            "archived_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    state[name] = entry
    _save_state(paths.state_path, state)
    return entry


def restore_skill(paths: CuratorPaths, name: str) -> dict:
    """Bring an archived skill back to the owned skills dir (invariant 1)."""
    safe_path = _resolve_within(name, paths.archive_dir)
    if not safe_path.is_dir() or not (safe_path / "SKILL.md").is_file():
        raise CuratorError(f"{name!r} not found under {paths.archive_dir} — nothing to restore")

    dest = paths.owned_skills_dir / name
    if dest.exists():
        raise CuratorError(f"{name!r} already exists under {paths.owned_skills_dir} — refusing to overwrite")

    paths.owned_skills_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(safe_path), str(dest))

    state = _load_state(paths.state_path)
    entry = state.get(name, {})
    entry["lifecycle"] = "active"
    entry.pop("archived_at", None)
    state[name] = entry
    _save_state(paths.state_path, state)
    return entry


def _set_pinned(paths: CuratorPaths, name: str, pinned: bool) -> dict:
    owned = _scan_skill_dir(paths.owned_skills_dir)
    archived = _scan_skill_dir(paths.archive_dir)
    if name in owned:
        _resolve_within(name, paths.owned_skills_dir)
    elif name in archived:
        _resolve_within(name, paths.archive_dir)
    else:
        raise CuratorError(f"{name!r} not found under {paths.owned_skills_dir} or {paths.archive_dir}")

    state = _load_state(paths.state_path)
    entry = state.get(name, {})
    entry["pinned"] = pinned
    state[name] = entry
    _save_state(paths.state_path, state)
    return entry


def pin_skill(paths: CuratorPaths, name: str) -> dict:
    return _set_pinned(paths, name, True)


def unpin_skill(paths: CuratorPaths, name: str) -> dict:
    return _set_pinned(paths, name, False)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _fmt_dt(dt: Optional[datetime]) -> str:
    return dt.isoformat(timespec="seconds") if dt else "-"


def cmd_status(paths: CuratorPaths) -> int:
    portfolio = build_portfolio(paths)
    print()
    print(f"  Skill lifecycle  ({paths.state_path})")
    print(f"  {'name':<32} {'created_by':<10} {'state':<10} {'uses':>5}  {'last_used':<22} pinned")
    print(f"  {'-'*32} {'-'*10} {'-'*10} {'-'*5}  {'-'*22} ------")
    for name, e in sorted(portfolio.items()):
        print(
            f"  {name[:32]:<32} {e['created_by']:<10} {e['display_state']:<10} "
            f"{e['use_count']:>5}  {_fmt_dt(e['last_used_at']):<22} {e['pinned']}"
        )
    print()
    return 0


def cmd_propose(paths: CuratorPaths) -> int:
    proposals = compute_proposals(paths)
    actionable = sorted((p for p in proposals if p.actionable), key=lambda p: p.name)
    informational = sorted((p for p in proposals if not p.actionable), key=lambda p: p.name)

    print()
    print("  Proposed transitions — curator can act (created_by: agent, in scope)")
    if actionable:
        for p in actionable:
            print(f"  - {p.name}: propose {p.action}  ({p.reason})")
    else:
        print("  (none)")
    print()
    print("  Informational only — curator cannot act (human-authored or out of scope)")
    if informational:
        for p in informational:
            print(f"  - {p.name}: would be {p.action}  ({p.reason}) — read-only; 'archive' won't touch this")
    else:
        print("  (none)")
    print()
    print("  Nothing was changed. 'propose' never mutates.")
    print()
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="skill-curator.py", description="Skill lifecycle curator (ADR 0018)")
    sub = parser.add_subparsers(dest="verb", required=True)
    sub.add_parser("status", help="lifecycle table for the full skill portfolio")
    sub.add_parser("propose", help="what would transition, and why — mutates nothing")
    p_archive = sub.add_parser("archive", help="move a skill to the archive dir")
    p_archive.add_argument("name")
    p_restore = sub.add_parser("restore", help="bring an archived skill back")
    p_restore.add_argument("name")
    p_pin = sub.add_parser("pin", help="exempt a skill from every future transition")
    p_pin.add_argument("name")
    p_unpin = sub.add_parser("unpin", help="undo pin")
    p_unpin.add_argument("name")

    args = parser.parse_args(argv)
    paths = CuratorPaths.default()

    try:
        if args.verb == "status":
            return cmd_status(paths)
        if args.verb == "propose":
            return cmd_propose(paths)
        if args.verb == "archive":
            archive_skill(paths, args.name)
            print(f"archived {args.name!r} -> {paths.archive_dir / args.name}")
            return 0
        if args.verb == "restore":
            restore_skill(paths, args.name)
            print(f"restored {args.name!r} -> {paths.owned_skills_dir / args.name}")
            return 0
        if args.verb == "pin":
            pin_skill(paths, args.name)
            print(f"pinned {args.name!r}")
            return 0
        if args.verb == "unpin":
            unpin_skill(paths, args.name)
            print(f"unpinned {args.name!r}")
            return 0
    except CuratorError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1

    parser.error("unknown verb")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
