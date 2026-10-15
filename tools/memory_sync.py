"""Sync the C-level auto-memory dir with its git repo (`PASAKON/Agents-Memory`).

task-8d37c0f1. Auto-memory (``~/.claude/projects/<slug>/memory``) used to live
only on the Mac — Contabo had a stale rsync snapshot, winbox had nothing. The
CTO split it into its own private repo and, on the Mac, replaced the real
`memory/` directory with a symlink into a sibling checkout
(``/Users/gob/MoonieXHQ/Agents/Memory``). This module is the sync half: pull it
fresh before a C-level session reads `MEMORY.md` into context, push it before
one ends so the next session (on ANY host) sees what this one learned.
This module owns Agents-Memory sync: commit session edits and merge a moved
remote at session close, with best-effort merges at spawn.

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
import contextlib
import os
import re
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parent.parent

_NOT_A_SLUG_CHAR = re.compile(r"[^A-Za-z0-9]")
_GITATTRIBUTES_RULE = "MEMORY.md merge=union"


class _LockBusy(Exception):
    """Another memory_sync process holds the repo lock past the wait."""


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
# the launcher's ~20s foreground budget for the two network calls on divergence.
GIT_TIMEOUT_SECONDS = 8.0


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=GIT_TIMEOUT_SECONDS,
            env={**os.environ, "LC_ALL": "C"},
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=["git", "-C", str(repo), *args], returncode=124,
            stdout="", stderr=f"timed out after {GIT_TIMEOUT_SECONDS}s",
        )


@contextlib.contextmanager
def _repo_lock(repo: Path):
    """Serialize memory_sync operations on a shared checkout (e.g. Contabo).

    Concurrent ``git pull``/``git fetch`` processes on the same repo both
    append for-merge lines to ``.git/FETCH_HEAD`` after their network round-
    trip, which makes ``git pull --ff-only`` fail with ``fatal: Cannot
    fast-forward to multiple branches``. Locking ``.git/memory_sync.lock``
    prevents concurrent fetches and merges from racing.
    """
    git_dir = repo / ".git"
    if fcntl is None or not git_dir.is_dir():
        yield
        return
    lock_path = git_dir / "memory_sync.lock"
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
    except OSError:
        yield
        return
    try:
        # Bounded wait: pull runs at spawn and must never block it (module doc).
        deadline = time.monotonic() + GIT_TIMEOUT_SECONDS
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    print("[memory_sync] another memory_sync holds the repo lock — skipping")
                    raise _LockBusy() from None
                time.sleep(0.5)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(fd)


def _ensure_gitattributes(repo: Path, *, write_worktree: bool = True) -> bool:
    """Ensure ``MEMORY.md merge=union`` is configured in ``repo``.

    Writes ``.git/info/attributes`` so Git's built-in ``union`` merge driver is
    active during ``git merge`` even before ``.gitattributes`` is committed,
    and (when ``write_worktree=True``) ensures ``.gitattributes`` in the
    working tree contains ``MEMORY.md merge=union`` so the rule travels with
    the repo. Returns True if ``.gitattributes`` was created or updated.
    """
    info_dir = repo / ".git" / "info"
    if info_dir.is_dir():
        info_attr = info_dir / "attributes"
        existing_info = info_attr.read_text() if info_attr.exists() else ""
        if _GITATTRIBUTES_RULE not in [
            line.strip() for line in existing_info.splitlines()
        ]:
            prefix = "\n" if existing_info and not existing_info.endswith("\n") else ""
            info_attr.write_text(f"{existing_info}{prefix}{_GITATTRIBUTES_RULE}\n")

    if not write_worktree:
        return False

    attr_path = repo / ".gitattributes"
    existing = attr_path.read_text() if attr_path.exists() else None
    if existing is not None and _GITATTRIBUTES_RULE in [
        line.strip() for line in existing.splitlines()
    ]:
        return False
    prefix = "\n" if existing and not existing.endswith("\n") else ""
    attr_path.write_text(f"{existing or ''}{prefix}{_GITATTRIBUTES_RULE}\n")
    return True


def _resolve_upstream(repo: Path) -> tuple[str, str]:
    """Return ``(remote, remote_branch)`` and repair multi-branch config.

    If ``branch.<branch>.merge`` or ``branch.<branch>.remote`` has multiple
    values in ``.git/config`` (which causes ``git pull --ff-only`` to abort
    with ``fatal: Cannot fast-forward to multiple branches``), collapse it in
    place with ``git config --replace-all``.
    """
    head_ref = _git(repo, "symbolic-ref", "--short", "-q", "HEAD")
    branch = head_ref.stdout.strip() if head_ref.returncode == 0 else ""

    if branch:
        remote_cfg = _git(repo, "config", "--get-all", f"branch.{branch}.remote")
        remotes = [r.strip() for r in remote_cfg.stdout.splitlines() if r.strip()]
        remote = remotes[0] if remotes else "origin"
        if len(remotes) > 1:
            _git(repo, "config", "--replace-all", f"branch.{branch}.remote", remote)

        merge_cfg = _git(repo, "config", "--get-all", f"branch.{branch}.merge")
        merge_refs = [m.strip() for m in merge_cfg.stdout.splitlines() if m.strip()]
        if len(merge_refs) > 1:
            preferred = (
                f"refs/heads/{branch}"
                if f"refs/heads/{branch}" in merge_refs
                else merge_refs[0]
            )
            _git(repo, "config", "--replace-all", f"branch.{branch}.merge", preferred)
            merge_refs = [preferred]

        if merge_refs:
            ref = merge_refs[0]
            remote_branch = (
                ref[len("refs/heads/"):] if ref.startswith("refs/heads/") else ref
            )
        else:
            remote_branch = branch
        return remote, remote_branch

    return "origin", "main"


def _fetch_upstream(repo: Path) -> tuple[subprocess.CompletedProcess, str | None]:
    """Fetch the single upstream branch and return ``(fetch_result, target_ref)``."""
    remote, remote_branch = _resolve_upstream(repo)
    fetched = _git(repo, "fetch", remote, remote_branch)
    if fetched.returncode != 0:
        return fetched, None

    tracking_ref = f"refs/remotes/{remote}/{remote_branch}"
    rev = _git(repo, "rev-parse", "--verify", "-q", tracking_ref)
    if rev.returncode == 0 and rev.stdout.strip():
        return fetched, f"{remote}/{remote_branch}"

    fh = _git(repo, "rev-parse", "--verify", "-q", "FETCH_HEAD")
    if fh.returncode == 0 and fh.stdout.strip():
        return fetched, fh.stdout.splitlines()[0].strip()

    return fetched, f"{remote}/{remote_branch}"


def _commit_with_fallback(repo: Path, *commit_args: str) -> subprocess.CompletedProcess:
    """Run ``git commit`` with a fallback identity if the host has none configured."""
    commit = _git(repo, "commit", *commit_args)
    if commit.returncode != 0 and any(
        phrase in commit.stderr.lower()
        for phrase in ("unable to auto-detect email address", "please tell me who you are")
    ):
        commit = _git(
            repo,
            "-c", "user.name=memory_sync",
            "-c", "user.email=memory_sync@local",
            "commit", *commit_args,
        )
    return commit


def _commit_dirty(repo: Path) -> subprocess.CompletedProcess | None:
    """Commit any uncommitted working-tree or index changes before merging.

    Mirrors ``push``'s own stage+commit step so ``pull`` never hits
    ``Please commit your changes or stash them before you merge`` or skips
    ``_merge_remote`` when a crashed/concurrent session left dirty files.
    """
    status = _git(repo, "status", "--porcelain")
    if status.returncode != 0 or not status.stdout.strip():
        return None

    _ensure_gitattributes(repo, write_worktree=True)
    add = _git(repo, "add", "-A")
    if add.returncode != 0:
        return add

    staged = _git(repo, "diff", "--cached", "--quiet")
    if staged.returncode == 0:
        return None

    msg = f"memory: {_session_label()} {date.today().isoformat()}"
    return _commit_with_fallback(repo, "-m", msg)


def _is_ahead_of_upstream(repo: Path) -> bool:
    ahead = _git(repo, "rev-list", "--count", "@{u}..HEAD")
    if ahead.returncode == 0:
        try:
            return int(ahead.stdout.strip()) > 0
        except ValueError:
            return False
    return False


def _theirs_filename(rel_path: str, shortsha: str) -> str:
    """Return ``<name>.theirs-<shortsha>.md`` next to ``rel_path``."""
    p = Path(rel_path)
    suffix = p.suffix or ".md"
    stem = p.stem if p.suffix else p.name
    return str(p.with_name(f"{stem}.theirs-{shortsha}{suffix}"))


def _union_lines(ours: str, theirs: str) -> str:
    """Line-by-line union preserving order (ours first, then unseen lines from theirs)."""
    result: list[str] = []
    seen: set[str] = set()
    for text in (ours, theirs):
        for line in text.splitlines(keepends=True):
            normalized = line if line.endswith("\n") else f"{line}\n"
            if normalized not in seen:
                result.append(normalized)
                seen.add(normalized)
    return "".join(result)


def _merge_remote(
    repo: Path, command: str, upstream_ref: str | None = None,
) -> subprocess.CompletedProcess:
    """Merge the remote branch into ``HEAD``, resolving conflicts without losing data.

    - ``MEMORY.md`` merges by line union (via ``.gitattributes`` /
      ``.git/info/attributes`` ``MEMORY.md merge=union``, plus an explicit
      fallback for add/add conflicts).
    - Any other conflicting file keeps ours at ``<name>`` and writes theirs
      next to it as ``<name>.theirs-<shortsha>.md``, then commits the merge.
    - Prints only file names, never memory file contents.
    """
    if upstream_ref is None:
        fetched, upstream_ref = _fetch_upstream(repo)
        if fetched.returncode != 0 or not upstream_ref:
            return fetched

    _ensure_gitattributes(repo, write_worktree=False)
    result = _git(repo, "merge", "--no-edit", upstream_ref)
    if result.returncode == 0:
        _ensure_gitattributes(repo, write_worktree=True)
        attr_status = _git(repo, "status", "--porcelain", "--", ".gitattributes")
        if attr_status.returncode == 0 and attr_status.stdout.strip():
            _git(repo, "add", "--", ".gitattributes")
            # A separate commit, never --amend: after a fast-forward HEAD is the
            # remote's own commit, and rewriting it would re-diverge the repo.
            _commit_with_fallback(repo, "-m", "memory: add .gitattributes (MEMORY.md merge=union)")
        return result

    conflicts = _git(repo, "diff", "--name-only", "--diff-filter=U")
    conflict_files = [
        line.strip() for line in conflicts.stdout.splitlines() if line.strip()
    ]
    if conflict_files:
        sha_proc = _git(repo, "rev-parse", "--short", "MERGE_HEAD")
        shortsha = sha_proc.stdout.strip()
        if not shortsha:
            shortsha = (
                _git(repo, "rev-parse", "--short", upstream_ref).stdout.strip()
                or "remote"
            )

        for rel_path in conflict_files:
            ours = _git(repo, "show", f":2:{rel_path}")
            theirs = _git(repo, "show", f":3:{rel_path}")
            if rel_path == "MEMORY.md":
                merged_text = _union_lines(
                    ours.stdout if ours.returncode == 0 else "",
                    theirs.stdout if theirs.returncode == 0 else "",
                )
                (repo / rel_path).write_text(merged_text)
                _git(repo, "add", "--", rel_path)
            elif rel_path == ".gitattributes":
                merged_text = _union_lines(
                    ours.stdout if ours.returncode == 0 else "",
                    theirs.stdout if theirs.returncode == 0 else "",
                )
                (repo / rel_path).write_text(merged_text)
                _ensure_gitattributes(repo, write_worktree=True)
                _git(repo, "add", "--", rel_path)
            elif ours.returncode == 0 and theirs.returncode == 0:
                (repo / rel_path).write_text(ours.stdout)
                theirs_rel = _theirs_filename(rel_path, shortsha)
                (repo / theirs_rel).parent.mkdir(parents=True, exist_ok=True)
                (repo / theirs_rel).write_text(theirs.stdout)
                _git(repo, "add", "--", rel_path, theirs_rel)
                print(
                    f"[memory_sync] {command}: merge conflict in {rel_path} "
                    f"— kept ours, wrote theirs to {theirs_rel}"
                )
            elif ours.returncode == 0:
                (repo / rel_path).write_text(ours.stdout)
                _git(repo, "add", "--", rel_path)
                print(
                    f"[memory_sync] {command}: merge conflict in {rel_path} — kept ours"
                )
            elif theirs.returncode == 0:
                (repo / rel_path).write_text(theirs.stdout)
                _git(repo, "add", "--", rel_path)
                print(
                    f"[memory_sync] {command}: merge conflict in {rel_path} — kept theirs"
                )

        _ensure_gitattributes(repo, write_worktree=True)
        _git(repo, "add", "--", ".gitattributes")

        remaining = _git(repo, "diff", "--name-only", "--diff-filter=U")
        if not remaining.stdout.strip():
            committed = _commit_with_fallback(repo, "--no-edit")
            if committed.returncode != 0:
                committed = _commit_with_fallback(
                    repo, "-m", f"memory: merge {upstream_ref} ({_session_label()})"
                )
            if committed.returncode == 0:
                return subprocess.CompletedProcess(
                    result.args, 0, stdout="merged remote changes\n", stderr=""
                )

        aborted = _git(repo, "merge", "--abort")
        # Do not print merge output: memory file contents must stay private.
        detail = (
            "merge conflict; merge aborted"
            if aborted.returncode == 0
            else "merge conflict; abort failed"
        )
        return subprocess.CompletedProcess(result.args, 1, stdout="", stderr=detail)

    return result


def pull(memory_dir: Path | None = None) -> int:
    try:
        return _pull(memory_dir)
    except _LockBusy:
        return 0  # never blocks or fails a spawn


def _pull(memory_dir: Path | None = None) -> int:
    """Sync and reconcile the memory repo from upstream. Always exits 0 — never blocks a spawn.

    Uncommitted local edits are committed first; fast-forward is attempted
    against the single resolved upstream branch; divergence is merged with
    ``MEMORY.md`` union-merged and any conflicting topic file preserved on
    both sides (``<name>`` + ``<name>.theirs-<shortsha>.md``).
    """
    memory_dir = memory_dir or default_memory_dir()

    if not memory_dir.is_symlink():
        print(_NOT_WIRED_MSG.format(dir=memory_dir))
        return 0

    repo = resolve_repo_path(memory_dir)
    if repo is None or not repo.is_dir():
        print(f"[memory_sync] pull: symlink target {repo} is missing — skipping")
        return 0

    with _repo_lock(repo):
        if (repo / ".git" / "MERGE_HEAD").exists():
            _git(repo, "merge", "--abort")

        _resolve_upstream(repo)
        _commit_dirty(repo)

        fetched, upstream_ref = _fetch_upstream(repo)
        if fetched.returncode != 0 or not upstream_ref:
            result = fetched
        else:
            result = _git(repo, "merge", "--ff-only", upstream_ref)
            if (
                result.returncode != 0
                and "not possible to fast-forward" in result.stderr.lower()
            ):
                result = _merge_remote(repo, "pull", upstream_ref)

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
    try:
        return _push(memory_dir)
    except _LockBusy:
        print("[memory_sync] push: FAILED — repo lock busy; edits stay committed locally")
        return 1


def _push(memory_dir: Path | None = None) -> int:
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

    with _repo_lock(repo):
        if (repo / ".git" / "MERGE_HEAD").exists():
            _git(repo, "merge", "--abort")

        _resolve_upstream(repo)

        status = _git(repo, "status", "--porcelain")
        if status.returncode == 0 and status.stdout.strip():
            _ensure_gitattributes(repo, write_worktree=True)

        add = _git(repo, "add", "-A")
        if add.returncode != 0:
            print(f"[memory_sync] push: FAILED to stage changes in {repo}")
            print(f"[memory_sync] push:   {add.stderr.strip()}")
            return 1

        msg = f"memory: {_session_label()} {date.today().isoformat()}"
        staged = _git(repo, "diff", "--cached", "--quiet")
        if staged.returncode != 0:
            commit = _commit_with_fallback(repo, "-m", msg)
            if commit.returncode != 0:
                print(f"[memory_sync] push: FAILED to commit in {repo}")
                print(f"[memory_sync] push:   {commit.stderr.strip()}")
                return 1
        elif not _is_ahead_of_upstream(repo):
            return 0  # nothing changed — quiet success

        pushed = _git(repo, "push")
        if pushed.returncode != 0 and any(
            reason in pushed.stderr
            for reason in ("(fetch first)", "(non-fast-forward)")
        ):
            merged = _merge_remote(repo, "push")
            pushed = _git(repo, "push") if merged.returncode == 0 else merged
        if pushed.returncode != 0:
            print(
                f"[memory_sync] push: FAILED to push {repo} — memory stays local-only"
            )
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
