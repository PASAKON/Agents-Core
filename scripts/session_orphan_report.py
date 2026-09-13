#!/usr/bin/env python3
"""See the workers that belong to no database (W4, task-91650ee0 / ADR 0024).

`lib/db.py` resolves its DB_PATH from its own file location, so every git
checkout is its own database, but every host in config/hosts.yaml ssh's into
the same shared machines (e.g. both the Mac and Contabo drive winbox). A
worker spawned by the *other* box's database is invisible to this one: no
row, no pid, nothing to reap. See org:decisions/0024-split-brain-task-
database.md (ADR 0024) for the full write-up, including why the fix is a
CEO-level infra decision and not something this tool should attempt.

This tool only looks. It never kills a process, never writes to any
database, never releases a lock. For every host in config/hosts.yaml that
has an `ssh` alias, it lists that host's live Claude Code worker processes
over SSH and classifies each one:

  known     - a task id is in the command line AND a row for it exists in
              this box's local tasks.db. Printed with its status.
  orphan    - a task id is in the command line but no local row exists.
              These are the interesting ones -- printed with pid, start
              time, and a pointer to ADR 0024. NEVER a kill suggestion.
  not-ours  - no task id in the command line at all (e.g. a human's own
              interactive Claude Code session and its children). Counted
              and left alone -- never placed in the orphan bucket.

Exit code: 0 only when every host was reachable AND zero orphans were
found. 1 if at least one host was unreachable (unproven, not "clean") or at
least one orphan exists -- so a human or the watchdog can use this as a
pass/fail check without reading the output.

Usage:
    scripts/session_orphan_report.py                # every host with an ssh alias
    scripts/session_orphan_report.py --host winbox
    scripts/session_orphan_report.py --json
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.config import hosts as get_hosts

ADR_POINTER = "org:decisions/0024-split-brain-task-database.md"
SSH_TIMEOUT_S = 25
TASK_ID_RE = re.compile(r"task-[0-9a-f]{8}")
_CLAUDE_MATCH = re.compile(r"claude", re.IGNORECASE)

# Verified live 2026-09-11 against winbox. Sent as -EncodedCommand
# (UTF-16LE base64), never as a quoted string -- PowerShell quoting through
# ssh is a known trap in this repo. Do not re-derive; if it needs to change,
# re-verify against a real box first.
_WIN_PS_QUERY = r"""
$rows = Get-CimInstance Win32_Process -Filter "Name = 'claude.exe'" |
  ForEach-Object {
    $cl = $_.CommandLine
    $m  = [regex]::Match([string]$cl, 'task-[0-9a-f]{8}')
    [pscustomobject]@{
      Pid  = $_.ProcessId
      Task = $(if ($m.Success) { $m.Value } else { '<none>' })
      Started = $_.CreationDate
    }
  }
$rows | Sort-Object Task | ForEach-Object { "{0}`t{1}`t{2}" -f $_.Pid, $_.Task, $_.Started }
"""


def _run_ssh(alias: str, remote_cmd: list[str], timeout: int = SSH_TIMEOUT_S):
    """ssh <alias> <remote_cmd...>, decoded with errors="replace".

    A worker's CommandLine is tens of KB of prompt text and can carry bytes
    (e.g. 0xae) that are not valid UTF-8 -- Windows writes CommandLine in the
    console's ANSI code page, not UTF-8. `text=True` alone decodes strict
    UTF-8 and raises UnicodeDecodeError; no mock can emit an invalid byte, so
    this only shows up against the real box. errors="replace" avoids it, and
    the broad except below is a second net in case some other layer still
    raises -- either way, any failure here means "couldn't ask this host",
    never "this host has no workers". Returns None on any failure.
    """
    try:
        return subprocess.run(
            ["ssh", "-o", "ConnectTimeout=15", alias, *remote_cmd],
            capture_output=True, text=True, errors="replace", timeout=timeout,
        )
    except Exception:
        return None


def _parse_win_output(stdout: str) -> list[dict]:
    procs = []
    for line in stdout.splitlines():
        parts = line.strip().split("\t")
        if len(parts) < 2:
            continue
        pid, task = parts[0].strip(), parts[1].strip()
        started = parts[2].strip() if len(parts) > 2 else ""
        procs.append({"pid": pid, "task": task, "started": started})
    return procs


def _parse_linux_ps(stdout: str) -> list[dict]:
    """Parse `ps -eo pid=,lstart=,args=` output, filtered to claude
    processes only. Unfiltered, `ps -eo ...` lists the whole process table
    (sshd, cron, bash, ...) -- the Windows query narrows with
    `-Filter "Name = 'claude.exe'"`; this is the Linux equivalent so the
    not-ours bucket means "a Claude Code process with no task id", not
    "every process on the box"."""
    procs = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 6)  # pid, 5 lstart tokens, then args
        if len(parts) < 7:
            continue
        pid, args = parts[0], parts[6]
        if not _CLAUDE_MATCH.search(args):
            continue
        started = " ".join(parts[1:6])
        m = TASK_ID_RE.search(args)
        procs.append({"pid": pid, "task": m.group(0) if m else "<none>",
                     "started": started})
    return procs


def fetch_windows_workers(alias: str, run_ssh=_run_ssh) -> tuple[list[dict], bool]:
    """Returns (procs, reachable)."""
    enc = base64.b64encode(_WIN_PS_QUERY.encode("utf-16-le")).decode()
    r = run_ssh(alias, [f"powershell -NoProfile -EncodedCommand {enc}"])
    if r is None or r.returncode != 0:
        return [], False
    return _parse_win_output(r.stdout), True


def fetch_linux_workers(alias: str, run_ssh=_run_ssh) -> tuple[list[dict], bool]:
    """Returns (procs, reachable)."""
    r = run_ssh(alias, ["ps", "-eo", "pid=,lstart=,args="])
    if r is None or r.returncode != 0:
        return [], False
    return _parse_linux_ps(r.stdout), True


def gather_host(host_name: str, host_cfg: dict, run_ssh=_run_ssh) -> dict:
    alias = host_cfg["ssh"]
    if host_cfg.get("os") == "windows":
        procs, reachable = fetch_windows_workers(alias, run_ssh)
    else:
        procs, reachable = fetch_linux_workers(alias, run_ssh)
    return {"host": host_name, "reachable": reachable, "procs": procs}


def local_db_path() -> Path:
    """Canonical local tasks.db for this box -- never a worktree's own
    stray copy.

    lib/db.py resolves DB_PATH from its own file location (ADR 0024): a
    tool that just imports lib.db and happens to run from inside a git
    worktree ends up asking a *different*, usually-empty database whether a
    task id exists -- the exact split-brain this report exists to catch.
    This script lives at .../<org-root>/worktrees/<name>/scripts/... when
    run from a worktree (as it is here) or .../<org-root>/scripts/... from
    the canonical checkout; either way, walk back up to <org-root> so
    "local" always means this box's one real database.
    """
    here = Path(__file__).resolve()
    parts = here.parts
    if "worktrees" in parts:
        org_root = Path(*parts[: parts.index("worktrees")])
    else:
        org_root = here.parent.parent
    return org_root / "state" / "tasks.db"


def read_local_tasks(db_path: Path) -> dict[str, str] | None:
    """id -> status for every row in the local tasks.db. None if the file
    doesn't exist or can't be read -- never raises. Opened read-only
    (mirrors lib/db.py's own resolve_od_project helper) so this report can
    never create or modify a database as a side effect of looking."""
    if not db_path.exists():
        return None
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
        rows = con.execute("SELECT id, status FROM tasks").fetchall()
        con.close()
    except Exception:
        return None
    return {r[0]: r[1] for r in rows}


def classify(procs: list[dict], local_tasks: dict[str, str] | None) -> dict:
    """Bucket processes into known / orphan / not_ours.

    If the local db itself couldn't be read, a task-id-bearing process
    cannot be proven known -- it is bucketed as orphan out of caution
    (visible and non-destructive) rather than silently dropped."""
    known: list[dict] = []
    orphan: list[dict] = []
    not_ours: list[dict] = []
    for p in procs:
        task_id = p.get("task")
        if not task_id or task_id == "<none>":
            not_ours.append(p)
        elif local_tasks is not None and task_id in local_tasks:
            known.append({**p, "status": local_tasks[task_id]})
        else:
            orphan.append(p)
    return {"known": known, "orphan": orphan, "not_ours": not_ours}


def build_report(host_filter: str | None = None, run_ssh=_run_ssh) -> dict:
    db_path = local_db_path()
    local_tasks = read_local_tasks(db_path)
    all_hosts = get_hosts()

    if host_filter:
        cfg = all_hosts.get(host_filter)
        if cfg is None:
            raise ValueError(f"unknown host: {host_filter!r}. Known: {list(all_hosts)}")
        if not cfg.get("ssh"):
            raise ValueError(
                f"host {host_filter!r} has no ssh alias (it's a local host) "
                "-- nothing to check remotely"
            )
        names = [host_filter]
    else:
        names = [n for n, c in all_hosts.items() if c.get("ssh")]

    host_reports = []
    for name in names:
        g = gather_host(name, all_hosts[name], run_ssh=run_ssh)
        if not g["reachable"]:
            host_reports.append({"host": name, "reachable": False})
            continue
        host_reports.append({
            "host": name, "reachable": True,
            **classify(g["procs"], local_tasks),
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "adr": ADR_POINTER,
        "local_db": str(db_path),
        "local_db_readable": local_tasks is not None,
        "hosts": host_reports,
    }


def compute_exit_code(report: dict) -> int:
    """0 only if every host was reachable and zero orphans were found."""
    for h in report["hosts"]:
        if not h.get("reachable", False):
            return 1
        if h.get("orphan"):
            return 1
    return 0


def print_human(report: dict) -> None:
    print(f"session_orphan_report -- {report['generated_at']}")
    if report["local_db_readable"]:
        print(f"local db: {report['local_db']}")
    else:
        print(f"local db: UNREADABLE ({report['local_db']}) "
              "-- every task id below is bucketed as orphan out of caution")
    print(f"see {report['adr']} (ADR 0024) -- this tool only looks, it never "
          "kills or suggests killing anything")
    print()

    for h in report["hosts"]:
        name = h["host"]
        if not h.get("reachable", False):
            print(f"== {name}: UNREACHABLE (ssh failed or timed out) ==")
            print("   unknown, not proven safe -- not the same as 'no workers'")
            print()
            continue
        known, orphan, not_ours = h["known"], h["orphan"], h["not_ours"]
        print(f"== {name} -- known={len(known)} orphan={len(orphan)} not_ours={len(not_ours)} ==")
        for p in known:
            print(f"  known   pid={p['pid']:<8} {p['task']:16s} status={p['status']}")
        for p in orphan:
            print(f"  ORPHAN  pid={p['pid']:<8} {p['task']:16s} "
                  f"started={p.get('started', '')}")
        if orphan:
            print(f"          -- belong to a second tasks.db on another host; "
                  f"see {ADR_POINTER}. CEO ruling 2026-09-11: "
                  '"ปล่อยไว้ก่อน ทำระบบให้ตรวจจับได้" -- leave running.')
        if not_ours:
            print(f"  not-ours: {len(not_ours)} process(es), no task id in argv "
                  "(e.g. a human's own Claude Code session + children) -- untouched")
        print()


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "List remote Claude Code worker processes per config/hosts.yaml "
            "host and classify each as known / orphan / not-ours. Read-only: "
            "never kills a process, never writes to any database. Exit 0 "
            "only when every host was reachable and zero orphans were found; "
            "exit 1 if any host was unreachable (unproven, not 'clean') or "
            "at least one orphan was found."
        )
    )
    ap.add_argument("--host", help="limit to one host (config/hosts.yaml key)")
    ap.add_argument("--json", action="store_true", help="machine-readable JSON output")
    args = ap.parse_args()

    try:
        report = build_report(host_filter=args.host)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_human(report)
    return compute_exit_code(report)


if __name__ == "__main__":
    sys.exit(main())
