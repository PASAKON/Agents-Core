"""Sync the C-level auto-memory dir with its git repo (`PASAKON/Agents-Memory`).

task-8d37c0f1. Auto-memory (``~/.claude/projects/<slug>/memory``) used to live
only on the Mac — Contabo had a stale rsync snapshot, winbox had nothing. The
CTO split it into its own private repo and, on the Mac, replaced the real
`memory/` directory with a symlink into a sibling checkout
(``/Users/gob/MoonieXHQ/Agents/Memory``). This module is the sync half: pull it
fresh before a C-level session reads `MEMORY.md` into context, push it before
one ends so the next session (on ANY host) sees what this one learned.

Two hard constraints shape every function here:

- **`pull` must never block or fail a spawn.** The harness loads `MEMORY.md`
  into context at process start, before any skill can run — so the pull has
  to happen in the launcher itself, synchronously, with a short timeout. A
  crashed session's unpushed local commit (can't fast-forward) or a flaky
  network must degrade to "stale memory, spawn anyway", never to "spawn
  refused".
- **`push` is the thing session-close/session-save gate on.** A silent
  failure there is a lost lesson forever (the in-memory context is gone the
  moment the process ends) — so unlike `pull`, `push` reports failure loudly
  via a non-zero exit.

Host-agnostic by construction (CEO ruling, project brief): the repo path is
never hardcoded. It is read from the memory symlink itself
(``os.readlink``), the same "ask the filesystem, not a hardcoded Mac path"
principle ``tools/session_reconcile.py``'s ``_this_host()`` uses for the host
key. A machine that has not been wired up yet (memory dir is a real
directory, not a symlink — see ``docs/memory-repo.md``) is a no-op on both
commands, not an error.

Usage:
    python3 -m tools.memory_sync pull
    python3 -m tools.memory_sync push
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_NOT_A_SLUG_CHAR = re.compile(r"[^A-Za-z0-9]")


def _claude_project_slug(path: Path) -> str:
    """Claude Code's ``~/.claude/projects/<slug>`` name for an absolute path.

    Every character outside ``[A-Za-z0-9]`` becomes ``-`` (verified against
    this repo's own real project dirs, e.g. ``/Users/gob/Projects/Agents`` ->
    ``-Users-gob-Projects-Agents``, and a worktree path's ``__`` -> ``--``).
    """
    return _NOT_A_SLUG_CHAR.sub("-", str(path))


def default_memory_dir() -> Path:
    """``~/.claude/projects/<this repo's slug>/memory`` — real path, this host."""
    return Path.home() / ".claude" / "projects" / _claude_project_slug(ROOT) / "memory"


_NOT_WIRED_MSG = (
    "[memory_sync] {dir} is a plain directory, not a symlink into the "
    "Agents-Memory git repo — this machine hasn't been connected yet. "
    "See docs/memory-repo.md to wire it up. Skipping (no-op)."
)


def resolve_repo_path(memory_dir: Path) -> Path | None:
    """The git repo a memory-dir symlink points at, or None if not a symlink.

    Reads the link target with ``os.readlink`` (not ``.resolve()``) so a
    relative target is joined against the symlink's own parent directory
    rather than silently assuming an absolute Mac path.
    """
    if not memory_dir.is_symlink():
        return None
    target = Path(os.readlink(memory_dir))
    if not target.is_absolute():
        target = (memory_dir.parent / target).resolve()
    return target


def _session_label() -> str:
    """``<role>-<session_id>`` for the commit message, best-effort.

    Mirrors the SID convention [[session-close]]/[[session-save]] use for
    LungNote tags. Falls back to the plain Claude Code session id (session-
    save's own fallback) and finally to "unknown" rather than raising —
    a commit message is not worth blocking a push over.
    """
    role = os.environ.get("CXO_ROLE") or (
        "cto" if os.environ.get("CTO_SESSION_ID") else None
    )
    sid = os.environ.get("CXO_SESSION_ID") or os.environ.get("CTO_SESSION_ID")
    if role and sid:
        return f"{role}-{sid}"
    claude_sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if claude_sid:
        return f"claude-{claude_sid[-8:]}"
    return "unknown"


# Per-command bound so a hung network call (dead remote, no route) can never
# hold a spawn open — the launcher relies on this instead of the shell's own
# `timeout`/`gtimeout`, which this box doesn't have (IRON-RULES §12: BSD
# userland, verify before assuming a GNU coreutil exists). Comfortably under
# the launcher's ~20s foreground budget even if pull needs two git calls.
GIT_TIMEOUT_SECONDS = 8.0


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=["git", "-C", str(repo), *args], returncode=124,
            stdout="", stderr=f"timed out after {GIT_TIMEOUT_SECONDS}s",
        )


def pull(memory_dir: Path | None = None) -> int:
    """``git pull --ff-only`` the memory repo. Always exits 0 — never blocks a spawn.

    A non-fast-forward pull (a crashed prior session's local commit never
    pushed) or a network failure both just print a warning and fall through:
    the session runs with whatever memory is already on disk.
    """
    memory_dir = memory_dir or default_memory_dir()

    if not memory_dir.is_symlink():
        print(_NOT_WIRED_MSG.format(dir=memory_dir))
        return 0

    repo = resolve_repo_path(memory_dir)
    if repo is None or not repo.is_dir():
        print(f"[memory_sync] pull: symlink target {repo} is missing — skipping")
        return 0

    result = _git(repo, "pull", "--ff-only")
    if result.returncode == 0:
        print(f"[memory_sync] pull: {result.stdout.strip() or 'already up to date'}")
        return 0

    print(
        f"[memory_sync] pull: WARNING — could not fast-forward {repo} "
        "(likely a local commit from a crashed session not yet pushed, or a "
        "network issue). Continuing with memory as-is; spawn is not blocked."
    )
    detail = (result.stderr or result.stdout).strip()
    if detail:
        print(f"[memory_sync] pull:   {detail}")
    return 0


def push(memory_dir: Path | None = None) -> int:
    """``git add -A && commit && push`` the memory repo.

    Nothing changed -> exit 0, silent. A commit or push failure -> exit 1
    with a clear message, since session-close/session-save gate the 🏁 on
    this exit code (an unsynced memory repo is a lost lesson the moment the
    session ends).
    """
    memory_dir = memory_dir or default_memory_dir()

    if not memory_dir.is_symlink():
        print(_NOT_WIRED_MSG.format(dir=memory_dir))
        return 0

    repo = resolve_repo_path(memory_dir)
    if repo is None or not repo.is_dir():
        print(f"[memory_sync] push: symlink target {repo} is missing — skipping")
        return 0

    add = _git(repo, "add", "-A")
    if add.returncode != 0:
        print(f"[memory_sync] push: FAILED to stage changes in {repo}")
        print(f"[memory_sync] push:   {add.stderr.strip()}")
        return 1

    staged = _git(repo, "diff", "--cached", "--quiet")
    if staged.returncode == 0:
        return 0  # nothing changed — quiet success

    msg = f"memory: {_session_label()} {date.today().isoformat()}"
    commit = _git(repo, "commit", "-m", msg)
    if commit.returncode != 0:
        print(f"[memory_sync] push: FAILED to commit in {repo}")
        print(f"[memory_sync] push:   {commit.stderr.strip()}")
        return 1

    pushed = _git(repo, "push")
    if pushed.returncode != 0:
        print(f"[memory_sync] push: FAILED to push {repo} — memory stays local-only")
        detail = (pushed.stderr or pushed.stdout).strip()
        if detail:
            print(f"[memory_sync] push:   {detail}")
        return 1

    print(f"[memory_sync] push: committed + pushed ({msg!r})")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="tools.memory_sync",
        description="Sync the C-level auto-memory dir with its git repo.",
    )
    ap.add_argument("command", choices=["pull", "push"])
    args = ap.parse_args(argv)

    if args.command == "pull":
        return pull()
    return push()


if __name__ == "__main__":
    sys.exit(main())
