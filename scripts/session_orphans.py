#!/usr/bin/env python3
"""Find Claude sessions that are still running with nothing attached to them.

Closing an iTerm tab does not end the session inside it. iTerm2 starts each
session under `iTermServer`, whose whole job is to keep the process alive so
the tab can be restored later, so the close sends no SIGHUP and the process
keeps its tty. Measured 2026-08-30 on four sessions that had been resident
since 2026-08-28 14:46:

    claude(2929) <- zsh(2919) <- login(2918) <- iTermServer-3.6.11(654) <- iTerm2(496)

Nothing in the repo could see them. `session_list.py` decides what is live by
asking iTerm which tabs are open, so a session whose tab is gone reads as
not-live while its process still burns quota. `session-kill.sh` ends a session
with `tmux kill-session`, which cannot touch one that was never in tmux.
`cleanup-zombies.sh` works from the lock files under state/locks, and a session
started by hand as a plain tab never wrote one. Three tools, three different
reasons, same blind spot.

A session spawned through scripts/spawn-cto.sh is not affected: it lives in
tmux, and killing the tmux session takes the process with it.

Liveness here is decided by the tty, never by a tab's name. iTerm is asked for
the tty of every session it currently shows; a claude process whose tty is not
in that set, and which has no tmux ancestor, has nothing attached to it. Naming
was rejected deliberately -- a hand-started tab need not carry a session id in
its title, and misreading one of those as abandoned would make --reap kill a
session someone is sitting in front of.

Usage:
    scripts/session_orphans.py            # report only
    scripts/session_orphans.py --reap     # also end the orphans (asks first)
    scripts/session_orphans.py --reap --yes
"""
from __future__ import annotations

import argparse
import os
import re
import signal
import subprocess
import sys
import time

RESUME_RE = re.compile(r"--resume\s+([0-9a-fA-F-]{8,})")


def _run(cmd: list[str], timeout: int = 15) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout
    except Exception:
        return ""


def claude_processes() -> list[dict]:
    """Every `claude --resume <uuid>` process this user owns."""
    out = _run(["ps", "-axo", "pid=,ppid=,tty=,lstart=,rss=,command="])
    found = []
    for line in out.splitlines():
        if "claude" not in line or "--resume" not in line:
            continue
        if "grep" in line or "session_orphans" in line:
            continue
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        pid, ppid, tty, rest = parts
        m = RESUME_RE.search(rest)
        if not m:
            continue
        uuid = m.group(1)
        # lstart is five whitespace-separated fields; rss and the command follow.
        tail = rest.split(None, 5)
        started = " ".join(tail[:5]) if len(tail) >= 5 else "?"
        rss_kb = tail[5].split()[0] if len(tail) > 5 else "0"
        found.append({
            "pid": int(pid), "ppid": int(ppid),
            "tty": tty if tty not in ("??", "?") else "",
            "uuid": uuid, "session_id": uuid[-8:].lower(),
            "started": started,
            "rss_mb": (int(rss_kb) // 1024) if rss_kb.isdigit() else 0,
        })
    return found


def has_tmux_ancestor(pid: int, limit: int = 8) -> bool:
    """Walk up the parent chain looking for a tmux server. A tmux-managed
    session is somebody else's job to end (session-kill.sh) and must never be
    reported here."""
    cur = pid
    for _ in range(limit):
        out = _run(["ps", "-o", "ppid=,comm=", "-p", str(cur)]).strip()
        if not out:
            return False
        ppid_s, _, comm = out.partition(" ")
        if "tmux" in comm:
            return True
        try:
            cur = int(ppid_s)
        except ValueError:
            return False
        if cur <= 1:
            return False
    return False


def iterm_live_ttys() -> tuple[set[str], bool]:
    """ttys of the sessions iTerm is showing right now.

    Returns (ttys, ok). ok=False when iTerm could not be asked -- the caller
    must then refuse to reap, because every session would look abandoned.
    """
    script = (
        'tell application "iTerm2"\n'
        '  set out to ""\n'
        '  repeat with w in windows\n'
        '    repeat with t in tabs of w\n'
        '      repeat with s in sessions of t\n'
        '        set out to out & (tty of s) & linefeed\n'
        '      end repeat\n'
        '    end repeat\n'
        '  end repeat\n'
        '  return out\n'
        'end tell'
    )
    try:
        r = subprocess.run(["osascript", "-e", script],
                           capture_output=True, text=True, timeout=20)
        if r.returncode != 0:
            return set(), False
        ttys = {line.strip().replace("/dev/", "")
                for line in r.stdout.splitlines() if line.strip()}
        return ttys, True
    except Exception:
        return set(), False


def classify(procs: list[dict], live_ttys: set[str]) -> list[dict]:
    for p in procs:
        if has_tmux_ancestor(p["pid"]):
            p["state"] = "tmux"
        elif p["tty"] and p["tty"] in live_ttys:
            p["state"] = "attached"
        else:
            p["state"] = "ORPHAN"
    return procs


def reap(orphans: list[dict]) -> None:
    """SIGTERM, a moment to exit cleanly, then SIGKILL what is left."""
    for p in orphans:
        try:
            os.kill(p["pid"], signal.SIGTERM)
            print(f"  TERM  pid {p['pid']}  #{p['session_id']}")
        except ProcessLookupError:
            print(f"  gone  pid {p['pid']}  #{p['session_id']} (exited already)")
        except PermissionError:
            print(f"  DENIED pid {p['pid']} -- not ours to kill")
    time.sleep(3)
    for p in orphans:
        try:
            os.kill(p["pid"], 0)
        except OSError:
            print(f"  dead  pid {p['pid']}  #{p['session_id']}")
            continue
        try:
            os.kill(p["pid"], signal.SIGKILL)
            print(f"  KILL  pid {p['pid']}  #{p['session_id']} (ignored TERM)")
        except OSError as e:
            print(f"  FAILED pid {p['pid']}: {e}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reap", action="store_true",
                    help="end the orphaned sessions, not only list them")
    ap.add_argument("--yes", action="store_true",
                    help="skip the confirmation prompt (for --reap)")
    args = ap.parse_args()

    procs = claude_processes()
    if not procs:
        print("no claude --resume processes running")
        return 0

    live_ttys, ok = iterm_live_ttys()
    if not ok:
        print("WARNING: could not ask iTerm which sessions are open.")
        print("Every session would look abandoned, so nothing is reported as")
        print("an orphan and --reap is refused. Is iTerm running?")
        return 2

    rows = classify(procs, live_ttys)
    width = max(len(r["session_id"]) for r in rows)
    print(f"{'STATE':9} {'PID':>7}  {'#id':<{width}}  {'TTY':8} {'MB':>5}  started")
    for r in sorted(rows, key=lambda r: (r["state"] != "ORPHAN", r["pid"])):
        print(f"{r['state']:9} {r['pid']:>7}  {r['session_id']:<{width}}  "
              f"{r['tty'] or '-':8} {r['rss_mb']:>5}  {r['started']}")

    orphans = [r for r in rows if r["state"] == "ORPHAN"]
    print()
    if not orphans:
        print("no orphans: every session is in tmux or has a tab attached")
        return 0

    mb = sum(r["rss_mb"] for r in orphans)
    print(f"{len(orphans)} orphan(s), {mb} MB resident, nothing attached to them.")
    if not args.reap:
        print("Run again with --reap to end them.")
        return 1

    if not args.yes:
        # An orphan is unattended, not necessarily unwanted -- it may hold a
        # conversation nobody has saved. Ending one is not reversible.
        try:
            answer = input(f"End {len(orphans)} session(s)? [y/N] ").strip().lower()
        except EOFError:
            answer = ""
        if answer != "y":
            print("nothing killed")
            return 1

    reap(orphans)
    return 0


if __name__ == "__main__":
    sys.exit(main())
