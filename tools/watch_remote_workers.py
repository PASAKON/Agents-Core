#!/usr/bin/env python3
"""Watch remote (Contabo) workers until they finish, stall, or need a human.

Replaces the hand-written shell loops a CTO kept re-typing (2026-09-25):
one of them iterated `for T in $TS` in zsh, which does not word-split, so it
polled a single bogus session name, saw "gone", and reported four workers
finished one second after they started.

Per poll, for each task id:
  - pane gone                        -> "gone"
  - "Teach auto mode about your environment?" first-run prompt
                                     -> sends "3" (Don't show again), "prompt-cleared"
  - any other "Enter to confirm"     -> "DIALOG" (needs a human / the CTO)
  - the pane shows ORG_WORKER_FINISH -> "finished" (the remote worker's last line)
  - otherwise                        -> "running"; a pane that has not changed
    for --stall-min minutes is "STALLED"
Also records whether the task branch is on origin (`git ls-remote`).

Prints one line whenever any task's state changes. Exit codes:
  0  every task finished or gone
  2  a task needs attention (DIALOG or STALLED)
  3  --timeout-min reached

Usage:
  python3 tools/watch_remote_workers.py task-5d9ecc9e task-94eb699b \
      [--host mooniex-vps] [--interval 60] [--stall-min 30] [--timeout-min 180]
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import time

TEACH_PROMPT = "Teach auto mode"
DIALOG = "Enter to confirm"
FINISH_MARK = "ORG_WORKER_FINISH"


def classify(pane: str | None) -> str:
    """Pure: map one captured pane to a state (tested without ssh)."""
    if not pane:
        return "gone"
    if TEACH_PROMPT in pane:
        return "teach-prompt"
    if DIALOG in pane:
        return "DIALOG"
    if FINISH_MARK in pane:
        return "finished"
    return "running"


def _ssh(host: str, cmd: str, timeout: int = 20) -> str | None:
    try:
        r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", host, cmd],
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    return r.stdout if r.returncode == 0 else None


def capture(host: str, task: str) -> str | None:
    return _ssh(host, f"tmux capture-pane -p -t mooniex-{task} 2>/dev/null")


def branch_pushed(task: str) -> bool:
    r = subprocess.run(["git", "ls-remote", "--heads", "origin", f"*-{task}"],
                       capture_output=True, text=True, timeout=60)
    return bool(r.stdout.strip())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("tasks", nargs="+")
    ap.add_argument("--host", default="mooniex-vps")
    ap.add_argument("--interval", type=int, default=60)
    ap.add_argument("--stall-min", type=int, default=30)
    ap.add_argument("--timeout-min", type=int, default=180)
    a = ap.parse_args(argv)

    start = time.time()
    last_hash: dict[str, str] = {}
    last_change: dict[str, float] = {t: start for t in a.tasks}
    shown: dict[str, str] = {}
    while True:
        now = time.time()
        states: dict[str, str] = {}
        for t in a.tasks:
            pane = capture(a.host, t)
            st = classify(pane)
            if st == "teach-prompt":
                _ssh(a.host, f"tmux send-keys -t mooniex-{t} 3")
                st = "prompt-cleared"
            h = hashlib.sha1((pane or "").encode()).hexdigest()
            if h != last_hash.get(t):
                last_hash[t], last_change[t] = h, now
            if st == "running" and now - last_change[t] > a.stall_min * 60:
                st = "STALLED"
            if st in ("finished", "gone") and branch_pushed(t):
                st += "+pushed"
            states[t] = st
        line = " ".join(f"{t.removeprefix('task-')}={s}" for t, s in states.items())
        if states != shown:
            print(f"{time.strftime('%H:%M:%S')} {line}", flush=True)
            shown = dict(states)
        if any(s in ("DIALOG", "STALLED") for s in states.values()):
            return 2
        if all(s.split("+")[0] in ("finished", "gone") for s in states.values()):
            return 0
        if now - start > a.timeout_min * 60:
            print(f"TIMEOUT {line}", flush=True)
            return 3
        time.sleep(a.interval)


if __name__ == "__main__":
    sys.exit(main())
