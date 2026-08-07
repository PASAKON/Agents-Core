"""How many C-level sessions may run at once, and what happens past that.

A session is a unit of the CEO's unfinished work, not a process to be reaped —
it legitimately stays open for days until the work behind it is actually done
(CEO 2026-08-07). So the cap is not about tidiness; it is about the box staying
under its memory ceiling while those sessions sit there.

Measured 2026-08-07: a session costs ~290 MB freshly spawned and grows with its
conversation, reaching ~600-1000 MB after a day. On Contabo — 7.9 GB total,
~1.5 GB of it OS plus production (claudeflow, option, n8n, LINE queue, console)
— five mature sessions is the largest number that still leaves production room
to breathe. A 4 GB swapfile added the same day turns an overshoot into
slowdown rather than the OOM killer taking out claudeflow, which is what makes
offering a grace slot safe at all.

The policy the CEO set:
  - up to CAP        : spawn silently.
  - CAP + 1          : allowed, but EVERY session's Main Tab carries a warning
                       until the count comes back down. One over is a nudge to
                       finish something, not a wall.
  - beyond CAP + 1   : refused. Close something first.

Used by tools/maintab.py, which renders the warning onto every session's
titlebar and onto the mirror file MoonieX Console reads for the phone, and by
scripts/spawn-cto.sh / spawn-cxo.sh, which enforce the refusal.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCKS = ROOT / "state" / "locks"

# CEO 2026-08-07. Raising this is a capacity decision, not a preference — check
# free memory on the box that actually runs the sessions first.
CAP = 5
# One over is tolerated so a session is never blocked at the exact moment the
# CEO needs one; two over is not.
GRACE = 1

ROLES = ("cto", "cmo", "cfo", "cxo")
_LOCK_RE = re.compile(rf"^({'|'.join(ROLES)})-(.+)$")


def _alive(pid: int) -> bool:
    """Signal 0 tests for existence without touching the process."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Exists, owned by someone else — still occupying the box.
        return True
    except OSError:
        return False
    return True


def live_sessions(locks_dir: Path | None = None) -> list[str]:
    """Session ids (`<role>-<sid>`) whose lock still points at a live process.

    `locks_dir` overrides the default so a caller counts sessions in the same
    root it is otherwise operating on. maintab passes its own `_LOCKS`, which
    its tests redirect at a throwaway dir — without that, the count would come
    from the real repo and a unit test's result would depend on how many
    sessions the machine happened to be running.

    Stale locks are left alone rather than reaped here: spawn-cto.sh owns that
    cleanup, and does it while holding the id it is about to claim. Counting
    stays a read-only concern.
    """
    out: list[str] = []
    try:
        locks = sorted((locks_dir or LOCKS).glob("*.lock"))
    except OSError:
        return out
    for lock in locks:
        if not _LOCK_RE.match(lock.stem):
            continue
        try:
            pid = int(lock.read_text().strip())
        except (OSError, ValueError):
            continue
        if _alive(pid):
            out.append(lock.stem)
    return out


def status(count: int | None = None,
           locks_dir: Path | None = None) -> tuple[int, bool, bool]:
    """(count, over_cap, at_hard_limit) for the current or a supplied count."""
    n = len(live_sessions(locks_dir)) if count is None else count
    return n, n > CAP, n >= CAP + GRACE


def warning(count: int | None = None, locks_dir: Path | None = None) -> str:
    """The banner every session shows while the org is over cap; '' when not.

    Deliberately short — it is prepended to a titlebar already carrying a goal,
    a progress bar and a clock, which the terminal truncates rather than wraps.
    """
    n, over, _ = status(count, locks_dir)
    if not over:
        return ""
    excess = n - CAP
    return f"⚠️ {n}/{CAP} เกิน {excess} — ปิดให้ได้ {excess} งาน"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--count", action="store_true", help="print the live count")
    ap.add_argument("--cap", action="store_true", help="print the cap")
    ap.add_argument("--list", action="store_true", help="print live session ids")
    ap.add_argument("--warning", action="store_true",
                    help="print the over-cap banner; empty when under cap")
    ap.add_argument("--check-spawn", action="store_true",
                    help="exit 0 = may spawn, 2 = would exceed cap+grace; "
                         "prints a human-readable reason either way")
    ap.add_argument("--locks-dir", type=Path, default=None,
                    help="count locks here instead of the default state/locks. "
                         "Callers that operate on a relocated root (the spawn "
                         "scripts under test) pass their own.")
    args = ap.parse_args(argv)

    live = live_sessions(args.locks_dir)
    n = len(live)

    if args.list:
        print("\n".join(live))
        return 0
    if args.count:
        print(n)
        return 0
    if args.cap:
        print(CAP)
        return 0
    if args.warning:
        print(warning(n))
        return 0
    if args.check_spawn:
        # n is the count BEFORE this spawn; the new session makes it n + 1.
        after = n + 1
        if after > CAP + GRACE:
            print(f"refuse: {n} sessions already live, cap is {CAP} "
                  f"(+{GRACE} grace). Close one before opening another.",
                  file=sys.stderr)
            return 2
        if after > CAP:
            print(f"warn: this makes {after} live against a cap of {CAP}. "
                  f"Allowed, but finish and close {after - CAP} soon — every "
                  f"session shows the warning until you do.", file=sys.stderr)
        return 0

    print(f"{n} live / cap {CAP} (+{GRACE} grace)")
    for s in live:
        print(f"  {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
