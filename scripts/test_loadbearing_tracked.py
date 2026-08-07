"""Regression guard for the ".claude/ blanket gitignore" incident.

.gitignore used to have a bare `.claude/` line, which silently swallowed
every skill/hook added after the initial 11 tracked skills (gdrive-filing,
seedance-scene-prompt, the repo-local .claude/settings.json, and the two
hook scripts it wires up all went untracked with no error). Narrowing the
ignore rule fixes today's snapshot but does nothing to stop it recurring
the next time someone adds a skill or a hook — this test is the part that
actually prevents recurrence: it FAILS the moment a load-bearing file goes
untracked again, regardless of *how* it happened (gitignore regression,
forgot to `git add`, etc).

Two independent checks, both derived at runtime (never hand-copy a list
here — that rots exactly like the thing it's guarding against):

  1. Every real (non-symlink) directory under `.claude/skills/` must have
     its `SKILL.md` tracked in git.
  2. Every repo-local script path referenced by a Claude Code
     `settings.json`'s hooks (checked at `~/.claude/settings.json`, the
     repo-local `.claude/settings.json`, and `.claude/settings.local.json`)
     must be tracked in git. Missing/unreadable settings files are skipped
     with a message, not a failure — this must not break on a machine that
     doesn't have one of them.

Run via:  python scripts/test_loadbearing_tracked.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_failures = 0

# Directories not worth walking when indexing repo-local script files:
# large, vendored, or generated — never where a hook script would live.
_WALK_SKIP = {
    ".git", ".venv", "node_modules", "worktrees", "__pycache__",
    ".agents", "state", "knowledge", "output", "external",
}

_PATH_RE = re.compile(r'(/[^\s"\']+\.(?:py|sh|js|mjs))')


def _mark(ok: bool, msg: str) -> None:
    global _failures
    if not ok:
        _failures += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def _tracked_files() -> set[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True,
    )
    return set(out.stdout.splitlines())


def _repo_basename_index() -> dict[str, list[Path]]:
    """basename -> list of repo-relative paths, for resolving hook commands
    that reference a repo-local script by absolute path (which may not
    match this ROOT if the settings.json was written on a different
    checkout, e.g. the canonical machine path vs. a worktree)."""
    index: dict[str, list[Path]] = {}
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if any(part in _WALK_SKIP for part in p.relative_to(ROOT).parts):
            continue
        index.setdefault(p.name, []).append(p.relative_to(ROOT))
    return index


def check_skills_tracked(tracked: set[str]) -> None:
    skills_dir = ROOT / ".claude" / "skills"
    if not skills_dir.is_dir():
        print(f"  SKIP: {skills_dir} not present on this machine")
        return

    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir() or entry.is_symlink():
            continue  # symlinked skills (e.g. externally-sourced) are out of scope
        skill_md = entry / "SKILL.md"
        rel = skill_md.relative_to(ROOT).as_posix()
        exists = skill_md.is_file()
        is_tracked = rel in tracked
        _mark(
            exists and is_tracked,
            f"{rel} tracked"
            + ("" if exists else " (MISSING ON DISK)")
            + ("" if is_tracked else " (UNTRACKED)"),
        )


def _iter_hook_commands(settings: dict) -> list[str]:
    commands: list[str] = []
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return commands
    for groups in hooks.values():
        if not isinstance(groups, list):
            continue
        for group in groups:
            for h in group.get("hooks", []) if isinstance(group, dict) else []:
                cmd = h.get("command") if isinstance(h, dict) else None
                if isinstance(cmd, str):
                    commands.append(cmd)
    return commands


def check_hook_scripts_tracked(tracked: set[str]) -> None:
    candidates = [
        Path.home() / ".claude" / "settings.json",
        ROOT / ".claude" / "settings.json",
        ROOT / ".claude" / "settings.local.json",
    ]

    basename_index: dict[str, list[Path]] | None = None
    seen: set[str] = set()  # dedupe repo-relative paths already checked

    for settings_path in candidates:
        if not settings_path.is_file():
            print(f"  SKIP: {settings_path} not present on this machine")
            continue
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"  SKIP: {settings_path} unreadable ({exc})")
            continue

        for cmd in _iter_hook_commands(settings):
            for match in _PATH_RE.findall(cmd):
                p = Path(match)
                if basename_index is None:
                    basename_index = _repo_basename_index()
                hits = basename_index.get(p.name, [])
                if not hits:
                    continue  # not a repo-local file (e.g. ~/.claude/hooks/*, a plugin path)
                # Prefer a hit whose relative path also appears as a suffix
                # of the absolute command path, to disambiguate same-named
                # files in different dirs; fall back to the first hit.
                rel = next(
                    (h for h in hits if match.endswith(h.as_posix())), hits[0]
                )
                rel_str = rel.as_posix()
                if rel_str in seen:
                    continue
                seen.add(rel_str)
                _mark(
                    rel_str in tracked,
                    f"{rel_str} tracked (referenced by {settings_path})"
                    + ("" if rel_str in tracked else " (UNTRACKED)"),
                )


def main() -> int:
    tracked = _tracked_files()

    print("Checking .claude/skills/**/SKILL.md ...")
    check_skills_tracked(tracked)

    print("Checking repo-local scripts referenced by settings.json hooks ...")
    check_hook_scripts_tracked(tracked)

    print(f"\n{'ALL PASS' if _failures == 0 else f'{_failures} FAILURE(S)'}")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
