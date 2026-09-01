#!/usr/bin/env python3
"""scripts/skill-curator.py — skill lifecycle curator (ADR 0018).

Turns the read-only telemetry from scripts/skill-report.py into a lifecycle:
propose stale/archive transitions, and let a human apply them. Never runs
unattended (ADR 0017 — no daemon); a C-level invokes verbs by hand.

Verbs:
  status                  lifecycle table: name, created_by, state, use_count,
                           last_used, pinned. Read-only.
  propose                 what WOULD transition, and why. Mutates nothing.
  archive <name>          move a skill to the archive dir.
  restore <name>          bring an archived skill back.
  pin <name>              exempt a skill from every future transition.
  unpin <name>            undo pin.
  create <name>           author a brand-new org skill (ADR 0022 Wave 2 —
                           reverses ADR 0018 §6).
  history [--skill NAME]  git log --follow for one skill, or the whole
                           owned-skills tree. Read-only.
  undo <sha>               git revert a skill-curator commit.
  drift                   git status --porcelain over .claude/skills — a
                           skill hand-edited outside the curator. Read-only.

Five invariants (non-negotiable, ADR 0018 §4):
  1. Never deletes — archive is restorable via `restore`.
  2. Only touches created_by: agent — human-authored skills (including every
     skill with no created_by field — absent means human) are read-only.
  3. Refuses any path that resolves through a symlink escaping
     .claude/skills/ — this is what keeps the curator out of external/*.
  4. Pinned skills are exempt from every transition and from archive itself.
  5. Backs up before any mutation — a timestamped copy under
     state/skill-curator-backups/, independent of `restore`'s own move-back.

ADR 0022 Wave 2 — git is the ledger, not a bespoke store. Every mutating verb
(archive/restore/pin/unpin/create) ends by committing the skill dir(s) it
touched, with a `Skill-Actor: <role>/<session-id>` trailer. `undo <sha>` is
`git revert`; `history` is `git log --follow`; `drift` is `git status`. There
is no more state/skill-usage.json sidecar — it was never written (verified
before deleting), and `pinned`/`lifecycle`/`archived_at` now live in each
skill's own SKILL.md frontmatter instead. The filesystem (which dir a skill's
SKILL.md is actually under) stays the ground truth for archived-vs-active,
same as before; the frontmatter fields are a record for `git log`/`git show`
to read, not a second source consulted for that decision.

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


def _pinned(skill_dir: Path) -> bool:
    """`pinned` from frontmatter — ADR 0022 Wave 2 moved this out of the
    state/skill-usage.json sidecar (deleted; it was never written — verified
    before deletion) and into the skill's own SKILL.md."""
    return bool(_read_frontmatter(skill_dir).get("pinned", False))


def _patch_frontmatter(skill_md: Path, updates: dict) -> None:
    """Set/remove top-level scalar frontmatter keys in place, leaving every
    other line — including multi-line block scalars like `description:` or
    `scope:` — byte-for-byte untouched. `updates[key] = None` removes the
    key if present; any other value is written verbatim as `key: value`
    (the caller is responsible for YAML-safe formatting).

    Line-level, not a full YAML re-dump, on purpose: `yaml.safe_dump` would
    re-flow every key including hand-formatted block scalars, which is far
    more blast radius than a lifecycle-field patch needs. Only an unindented
    line (`line[0]` not whitespace) is ever treated as a key candidate, so an
    indented continuation line of a block scalar is never mistaken for one.
    This is what lets `restore` delete `lifecycle`/`archived_at` again and
    get back the exact pre-archive bytes.
    """
    text = skill_md.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise CuratorError(f"{skill_md}: no frontmatter block to patch")
    lines = parts[1].split("\n")
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        key = line.split(":", 1)[0] if line and not line[0].isspace() and ":" in line else None
        if key is not None and key in updates:
            seen.add(key)
            value = updates[key]
            if value is not None:
                out.append(f"{key}: {value}")
            continue  # None -> drop the line (delete the key)
        out.append(line)
    additions = [f"{k}: {v}" for k, v in updates.items() if k not in seen and v is not None]
    if additions:
        if out and out[-1] == "":
            out = out[:-1] + additions + [""]
        else:
            out = out + additions
    skill_md.write_text("---" + "\n".join(out) + "---" + parts[2], encoding="utf-8")


# --------------------------------------------------------------------------
# Portfolio — the read-only merged view used by status/propose
# --------------------------------------------------------------------------

def build_portfolio(paths: CuratorPaths) -> dict[str, dict]:
    """Full projection: every known skill + its lifecycle state.

    Read-only. `pinned`/`created_by` come straight from each skill's own
    SKILL.md frontmatter (ADR 0022 Wave 2 — no more state/skill-usage.json
    sidecar to read-modify-write). `lifecycle` is derived from the
    filesystem alone (which dir the skill's SKILL.md is actually under) —
    it was never anything else even under the old sidecar, which only ever
    mirrored this same fact; a stale/hand-edited `lifecycle:` value in
    frontmatter is informational only and never consulted here. A skill this
    module has no dir for (external/plugin, known only via discovery) gets
    the same defaults an absent sidecar entry used to give: created_by
    human, unpinned.
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

    now = datetime.now(timezone.utc)
    portfolio: dict[str, dict] = {}
    for name in sorted(names):
        if name in archived_names:
            skill_dir: Optional[Path] = paths.archive_dir / name
        elif name in owned_names:
            skill_dir = paths.owned_skills_dir / name
        else:
            skill_dir = None

        created_by = _created_by(skill_dir) if skill_dir is not None else "human"
        pinned = _pinned(skill_dir) if skill_dir is not None else False

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

        lifecycle = "archived" if name in archived_names else "active"

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
# Git — the ledger (ADR 0022 Wave 2). Every mutating verb ends here.
# --------------------------------------------------------------------------

def _git_cwd(paths: CuratorPaths) -> Path:
    for candidate in (paths.owned_skills_dir, paths.archive_dir, paths.owned_skills_dir.parent):
        if candidate.exists():
            return candidate
    raise CuratorError("no directory to run git from — neither owned nor archive dir exists yet")


def _git(paths: CuratorPaths, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(_git_cwd(paths)), capture_output=True, text=True, timeout=15,
    )


def _agent_transport():
    """Lazy import of tools.agent_transport (ADR 0022 §4's identity source).

    Deferred, not a module-level import: scripts/test_skill_lint.py's own
    root-derivation test loads a *copy* of this file into a fake repo tree
    that has no tools/ dir at all, and merely importing this module must
    keep working there — only a verb that actually needs identity (create,
    or any mutating verb's commit) pays the import cost.
    """
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools import agent_transport
    return agent_transport


def _skill_actor() -> str:
    """`<role>/<session-id>` for the commit trailer, from whoever is calling
    right now — never anything the caller passes in (same rule
    tools.agent_transport.current_identity() itself follows)."""
    identity = _agent_transport().current_identity()
    return f"{identity.role}/{identity.session_id or '-'}"


def _commit_skill_mutation(paths: CuratorPaths, verb: str, name: str, touched: list[Path]) -> None:
    """Stage + commit whatever `touched` now looks like on disk, with a
    `Skill-Actor: <role>/<session-id>` trailer.

    `git add -A --` per path so a path that was just moved AWAY (e.g.
    archive's old owned-dir location) stages as a deletion instead of a
    missing-pathspec error — as long as git already had it tracked, which
    every real `.claude/skills/` entry does from Wave 0 onward. A path that
    was never tracked in the first place (only possible for a skill that
    never went through this ledger, e.g. a test fixture) has nothing to
    record as a deletion either, so that specific "did not match any files"
    outcome is treated as a no-op, not a failure. Scoped to `touched` only —
    never sweeps up unrelated staged/unstaged changes elsewhere in the repo.
    A no-op mutation (e.g. `unpin` on an already-unpinned skill) stages
    nothing and commits nothing — no empty commits.
    """
    usable: list[Path] = []
    for p in touched:
        add = _git(paths, "add", "-A", "--", str(p))
        if add.returncode != 0:
            if "did not match any files" in add.stderr and not p.exists():
                continue  # never tracked, and now gone -- nothing to stage or reference
            raise CuratorError(f"git add failed for {name!r} ({p}): {add.stderr.strip()}")
        usable.append(p)
    if not usable:
        return
    spec = [str(p) for p in usable]
    unchanged = _git(paths, "diff", "--cached", "--quiet", "--", *spec)
    if unchanged.returncode == 0:
        return
    message = f"skill-curator: {verb} {name}\n\nSkill-Actor: {_skill_actor()}"
    commit = _git(paths, "commit", "-m", message, "--", *spec)
    if commit.returncode != 0:
        raise CuratorError(f"git commit failed for {name!r}: {commit.stderr.strip()}")


# --------------------------------------------------------------------------
# Mutating verbs — archive, restore, pin, unpin, create
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
    pinned, missing, or already archived. Backs up before moving (invariant
    5 — still a live copytree this wave, independent of the git commit that
    follows it), then commits the move with a Skill-Actor trailer. `undo
    <sha>` is what reverses this from here on; `restore` (below) is the
    curator's own separate un-archive verb, not this commit's undo.
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

    if _pinned(safe_path):
        raise CuratorError(f"{name!r} is pinned — unpin before archiving (invariant 4)")

    dest = paths.archive_dir / name
    if dest.exists():
        raise CuratorError(f"{name!r} already exists in {paths.archive_dir} — already archived?")

    _backup_skill(paths, name, safe_path)  # invariant 5: snapshot before any mutation

    paths.archive_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(safe_path), str(dest))

    archived_at = datetime.now(timezone.utc).isoformat()
    _patch_frontmatter(dest / "SKILL.md", {"lifecycle": "archived", "archived_at": json.dumps(archived_at)})
    _commit_skill_mutation(paths, "archive", name, [safe_path, dest])
    return _read_frontmatter(dest)


def restore_skill(paths: CuratorPaths, name: str) -> dict:
    """Bring an archived skill back to the owned skills dir (invariant 1).

    Deletes `lifecycle`/`archived_at` from frontmatter rather than writing
    `lifecycle: active` — the same two lines `archive` added, removed again
    — so a restore round-trips the file byte-for-byte when nothing else
    changed in the meantime.
    """
    safe_path = _resolve_within(name, paths.archive_dir)
    if not safe_path.is_dir() or not (safe_path / "SKILL.md").is_file():
        raise CuratorError(f"{name!r} not found under {paths.archive_dir} — nothing to restore")

    dest = paths.owned_skills_dir / name
    if dest.exists():
        raise CuratorError(f"{name!r} already exists under {paths.owned_skills_dir} — refusing to overwrite")

    paths.owned_skills_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(safe_path), str(dest))

    _patch_frontmatter(dest / "SKILL.md", {"lifecycle": None, "archived_at": None})
    _commit_skill_mutation(paths, "restore", name, [safe_path, dest])
    return _read_frontmatter(dest)


def _set_pinned(paths: CuratorPaths, name: str, pinned: bool) -> dict:
    owned = _scan_skill_dir(paths.owned_skills_dir)
    archived = _scan_skill_dir(paths.archive_dir)
    if name in owned:
        skill_dir = _resolve_within(name, paths.owned_skills_dir)
    elif name in archived:
        skill_dir = _resolve_within(name, paths.archive_dir)
    else:
        raise CuratorError(f"{name!r} not found under {paths.owned_skills_dir} or {paths.archive_dir}")

    # Deletes the key on unpin rather than writing `pinned: false` -- absent
    # already means unpinned (_pinned()'s default), and it makes "unpin a
    # skill that was never pinned" a true no-op: nothing staged, no commit.
    _patch_frontmatter(skill_dir / "SKILL.md", {"pinned": "true" if pinned else None})
    _commit_skill_mutation(paths, "pin" if pinned else "unpin", name, [skill_dir])
    return _read_frontmatter(skill_dir)


def pin_skill(paths: CuratorPaths, name: str) -> dict:
    return _set_pinned(paths, name, True)


def unpin_skill(paths: CuratorPaths, name: str) -> dict:
    return _set_pinned(paths, name, False)


def create_skill(paths: CuratorPaths, name: str, *, description: str, audience: list[str]) -> Path:
    """Author a brand-new org skill (ADR 0022 Wave 2 — reverses ADR 0018
    §6, which put agent-authored skill creation out of scope). Stamps
    `created_by: agent` and `author: {role, date}` from the calling
    identity, so the skill is self-attributing from birth — unlike the 21
    Wave 1 legacy skills, which needed a lazy backfill. Commits the new dir
    with a Skill-Actor trailer, same as every other mutating verb here.

    Deliberately does not apply the audience-prefix naming convention (ADR
    0022 §4 / the `skill-author` skill) itself — that is the caller's job
    when it picks `name`; this verb only validates the name is safe and
    non-colliding, then writes a frontmatter that passes skill-lint.py on
    the first try.
    """
    safe_path = _resolve_within(name, paths.owned_skills_dir)
    if safe_path.exists():
        raise CuratorError(f"{name!r} already exists under {paths.owned_skills_dir}")

    identity = _agent_transport().current_identity()
    today = datetime.now(timezone.utc).date().isoformat()

    paths.owned_skills_dir.mkdir(parents=True, exist_ok=True)
    safe_path.mkdir(parents=True)
    frontmatter = "\n".join([
        "---",
        f"name: {name}",
        f"description: {json.dumps(description)}",
        "created_by: agent",
        f'author: {{role: {identity.role}, date: "{today}"}}',
        f"audience: [{', '.join(audience)}]",
        "---",
        "",
        f"# {name}",
        "",
        description,
        "",
    ])
    (safe_path / "SKILL.md").write_text(frontmatter, encoding="utf-8")

    _commit_skill_mutation(paths, "create", name, [safe_path])
    return safe_path


# --------------------------------------------------------------------------
# Read verbs — history, undo, drift (ADR 0022 §4.2). Thin wrappers over git;
# the ledger IS git, so these do no bookkeeping of their own.
# --------------------------------------------------------------------------

def history_skill(paths: CuratorPaths, name: Optional[str] = None) -> str:
    """`git log --follow -- .claude/skills/<name>`, or the whole owned-skills
    tree when `name` is omitted."""
    if name is not None:
        _resolve_within(name, paths.owned_skills_dir)  # validates the name shape only
        result = _git(paths, "log", "--follow", "--", str(paths.owned_skills_dir / name))
    else:
        result = _git(paths, "log", "--", str(paths.owned_skills_dir))
    return result.stdout


def undo_mutation(paths: CuratorPaths, sha: str) -> str:
    """`git revert` — the whole undo story (ADR 0022 §4). Raises
    CuratorError on failure (bad sha, conflict, dirty tree) rather than
    swallowing it — a silent failure here would be worse than no ledger."""
    result = _git(paths, "revert", "--no-edit", sha)
    if result.returncode != 0:
        raise CuratorError(f"git revert {sha!r} failed: {result.stderr.strip()}")
    return result.stdout


def detect_drift(paths: CuratorPaths) -> str:
    """`git status --porcelain` scoped to the owned skills tree — a skill
    hand-edited outside the curator, uncommitted. CEO rule 4 forbids the
    gate that would prevent this; this is the detection half."""
    result = _git(paths, "status", "--porcelain", "--", str(paths.owned_skills_dir))
    return result.stdout


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _fmt_dt(dt: Optional[datetime]) -> str:
    return dt.isoformat(timespec="seconds") if dt else "-"


def cmd_status(paths: CuratorPaths) -> int:
    portfolio = build_portfolio(paths)
    print()
    print(f"  Skill lifecycle  (git-tracked under {paths.owned_skills_dir})")
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
    p_create = sub.add_parser("create", help="author a brand-new org skill (ADR 0022 Wave 2)")
    p_create.add_argument("name")
    p_create.add_argument("--description", required=True)
    p_create.add_argument(
        "--audience", required=True,
        help="comma-separated audience tokens, e.g. cto,browser_operator or all",
    )
    p_history = sub.add_parser("history", help="git log --follow for one skill, or the whole tree")
    p_history.add_argument("--skill", default=None)
    p_undo = sub.add_parser("undo", help="git revert a skill-curator commit")
    p_undo.add_argument("sha")
    sub.add_parser("drift", help="git status --porcelain over .claude/skills")

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
        if args.verb == "create":
            audience = [tok.strip() for tok in args.audience.split(",") if tok.strip()]
            dest = create_skill(paths, args.name, description=args.description, audience=audience)
            print(f"created {args.name!r} -> {dest}")
            return 0
        if args.verb == "history":
            print(history_skill(paths, args.skill), end="")
            return 0
        if args.verb == "undo":
            print(undo_mutation(paths, args.sha), end="")
            return 0
        if args.verb == "drift":
            print(detect_drift(paths), end="")
            return 0
    except CuratorError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1

    parser.error("unknown verb")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
