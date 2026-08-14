"""Reconcile the two halves of a C-level session, report the drift, reap the dead.

A session is only real when BOTH halves agree — a live lock file whose pid is
still breathing AND a tmux session the CEO can actually attach. Anything else
is drift, and drift is how sessions go invisible (see tools/session_name for
the measured failure). This module is the read-only diagnostic plus a narrowly
scoped reaper; it never decides to kill a process or end a tmux session.

Three sets, computed by :func:`reconcile`:

  ``matched``
      a lock whose pid is alive AND whose stem is a running tmux session. The
      only entries that are unambiguously real.
  ``lock_only``
      a lock that is NOT matched — its pid is dead, OR its tmux session is
      gone. Reapable when the pid is dead; dangerous when the pid is still
      alive (the orphan: a process burning quota with no tmux to reach it).
  ``tmux_only``
      a running tmux session with no live lock backing it. The console
      legitimately creates these (a session that has not written its lock
      yet), so they are NEVER touched here — reaping one would destroy the
      CEO's live work. That fix belongs to the console side, not this reaper.

The dangerous case — a ``lock_only`` entry whose pid is still alive — is
carried in ``orphans`` (stem → pid) so a caller can report it loudly and
separately instead of deleting it silently. Deleting a stale lock is
recoverable; killing a live session is not, so this code only ever deletes
files, and only ever the dead ones.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCKS = ROOT / "state" / "locks"

from tools.session_name import LOCK_SUFFIXES, ROLE_RE  # noqa: E402
from tools.tmux_session import tmux_bin  # noqa: E402
# Signal-0 liveness is the canonical check the cap already uses; reuse it so
# the GC and the cap cannot disagree on what "alive" means.
from tools.session_cap import _alive  # noqa: E402


@dataclass
class Reconciliation:
    """The three drift sets from :func:`reconcile`, plus the orphan subset.

    ``matched`` / ``lock_only`` hold lock STEMS (``<role>-<id>``);
    ``tmux_only`` holds tmux session NAMES (also ``<role>-<id>``);
    ``orphans`` maps each live-pid ``lock_only`` stem to its pid — the entries
    a caller must NOT reap without a human looking first.
    """

    matched: set[str] = field(default_factory=set)
    lock_only: set[str] = field(default_factory=set)
    tmux_only: set[str] = field(default_factory=set)
    orphans: dict[str, int] = field(default_factory=dict)


def _read_pid(lock_path: Path) -> int | None:
    """The pid inside a .lock file, or None when it is missing/unreadable."""
    try:
        return int(lock_path.read_text().strip())
    except (OSError, ValueError):
        return None


def reconcile(
    locks_dir: Path,
    tmux_sessions: "set[str] | list[str] | tuple[str, ...]",
) -> Reconciliation:
    """Classify every lock half and tmux half into the three drift sets.

    Pure: reads the lock files and inspects process liveness (signal 0), but
    writes nothing. ``tmux_sessions`` is injected rather than shelled out so a
    test gets deterministic results without a running tmux server. Only names
    shaped ``<role>-<id>`` (see tools.session_name.ROLE_RE) are considered;
    a DEV pidfile or a non-C-level tmux session is neither half of a C-level
    session and is ignored.
    """
    tmux_set = {s for s in tmux_sessions if ROLE_RE.match(s)}

    rec = Reconciliation()
    try:
        locks = sorted(Path(locks_dir).glob("*.lock"))
    except OSError:
        return rec  # no locks dir is a clean (empty) reconciliation

    for lock in locks:
        stem = lock.stem
        if not ROLE_RE.match(stem):
            continue
        pid = _read_pid(lock)
        alive = _alive(pid) if pid is not None else False
        if alive and stem in tmux_set:
            rec.matched.add(stem)
        else:
            rec.lock_only.add(stem)
            if alive:
                # Live process, no tmux (or wrong tmux) — the orphan. Keep its
                # pid so a caller can show it and refuse to reap.
                rec.orphans[stem] = pid

    rec.tmux_only = tmux_set - rec.matched
    return rec


def live_pid(locks_dir: Path, stem: str) -> int | None:
    """Re-read a lock's pid and return it only if the process is alive.

    A separate predicate from :func:`reconcile` so the reaper re-checks
    liveness in the same breath it deletes — a process can die between the
    report and the reap, and the rule "never delete a live lock" is too
    important to trust to a stale classification.
    """
    lock = Path(locks_dir) / f"{stem}.lock"
    pid = _read_pid(lock)
    return pid if (pid is not None and _alive(pid)) else None


def sibling_paths(locks_dir: Path, stem: str) -> list[Path]:
    """Every file in this session's family that currently exists on disk."""
    base = Path(locks_dir) / stem
    return [Path(f"{base}{suf}") for suf in LOCK_SUFFIXES
            if Path(f"{base}{suf}").exists()]


def reap(
    locks_dir: Path,
    rec: Reconciliation | None = None,
    *,
    dry_run: bool = True,
    tmux_sessions: "set[str] | list[str] | tuple[str, ...] | None" = None,
) -> tuple[list[str], list[str]]:
    """Delete the dead-pid ``lock_only`` file groups.

    Returns ``(reaped, skipped)`` — stems whose family was removed (or would
    be, under dry-run) and stems spared because their pid was still alive.

    Never kills a process. Never touches a tmux session. ``tmux_only`` entries
    are not even considered: the console legitimately owns tmux sessions that
    have no lock yet, and deleting those would destroy live work. A live-pid
    ``lock_only`` lock (an orphan) is re-checked here and skipped no matter
    what ``dry_run`` says — ``--yes`` authorizes removing the dead, not the
    live. Reconciliation is recomputed when ``rec`` is None so a standalone
    reap sees current state instead of a stale snapshot.
    """
    if rec is None:
        rec = reconcile(locks_dir, tmux_sessions or set())

    reaped: list[str] = []
    skipped: list[str] = []
    for stem in sorted(rec.lock_only):
        if live_pid(locks_dir, stem) is not None:
            # Still alive at reap time — orphan. The rule is absolute.
            skipped.append(stem)
            continue
        if not dry_run:
            for p in sibling_paths(locks_dir, stem):
                try:
                    p.unlink()
                except OSError:
                    pass
        reaped.append(stem)
    return reaped, skipped


def _detect_tmux_sessions() -> list[str]:
    """Live tmux session names, or [] when tmux is absent / not running.

    Shelled out only here (never inside reconcile), so the pure core stays
    testable without a tmux server. Parses ``#{session_name}`` one per line;
    a missing server prints nothing to stdout and is not an error here.
    """
    try:
        out = subprocess.run(
            [tmux_bin(), "list-sessions", "-F", "#{session_name}"],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if out.returncode != 0:
        return []
    return [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]


def _print_report(locks_dir: Path, rec: Reconciliation) -> None:
    def _list(label: str, items: "set[str] | list[str]") -> None:
        print(f"{label}: {len(items)}")
        for s in sorted(items):
            tag = (f"  ORPHAN: pid {rec.orphans[s]} alive, no tmux"
                   if s in rec.orphans else f"  {s}")
            print(tag)

    _list("matched", rec.matched)
    _list("lock_only", rec.lock_only)
    _list("tmux_only", rec.tmux_only)
    if rec.orphans:
        print(f"orphans: {len(rec.orphans)} — NOT reaped (live process)")
    print(f"locks_dir: {locks_dir}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Reconcile C-level lock files against live tmux sessions.",
    )
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--report", action="store_true",
                      help="print the three drift sets and exit 0 (default)")
    mode.add_argument("--reap", action="store_true",
                      help="delete dead-pid lock_only file groups. Dry-run "
                           "unless --yes; live-pid orphans are never deleted.")
    ap.add_argument("--yes", action="store_true",
                    help="authorize --reap to actually delete (still never a "
                         "live pid or a tmux session)")
    ap.add_argument("--locks-dir", type=Path, default=LOCKS,
                    help="read locks here instead of the default state/locks")
    ap.add_argument("--quiet", action="store_true",
                    help="with --report: print nothing when there is no drift "
                         "(matched sessions are fine). Lets the spawn scripts "
                         "call this every launch without spamming a clean run.")
    args = ap.parse_args(argv)

    tmux_sessions = _detect_tmux_sessions()
    rec = reconcile(args.locks_dir, tmux_sessions)

    if args.reap:
        dry_run = not args.yes
        reaped, skipped = reap(args.locks_dir, rec, dry_run=dry_run)
        verb = "would delete" if dry_run else "deleted"
        for stem in reaped:
            fam = sibling_paths(args.locks_dir, stem)
            print(f"{verb}: {stem} ({len(fam)} file(s))")
        for stem in skipped:
            pid = rec.orphans.get(stem) or live_pid(args.locks_dir, stem)
            print(f"ORPHAN: {stem} — pid {pid} alive, no tmux; NOT reaped")
        if not reaped and not skipped:
            print("nothing to reap")
        if dry_run and reaped:
            print("dry-run only — re-run with --yes to delete")
        return 0

    # Default and explicit --report both land here.
    if args.quiet and not (rec.lock_only or rec.tmux_only or rec.orphans):
        return 0  # matched-only is not drift; stay silent
    _print_report(args.locks_dir, rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
