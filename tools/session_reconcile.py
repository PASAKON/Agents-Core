"""Reconcile c_level_sessions: mark rows 'abandoned' whose tmux is dead.

task-9ff9263f. A c_level_sessions row can say status='open' long after the
underlying tmux session (and its claude process) actually died — nothing
before this ever walked every open row and asked "is this still alive?".
scripts/session_list.py's tmux_lock_live() already knows how to answer that
(tmux server session, or lock pid) for the display it builds; this module is
the one place that WRITES the answer back into the DB, reusing that exact
check so the two can never disagree.

Host-aware (c_level_sessions.host, added alongside this module): a row
spawned on another machine cannot be judged from here — this machine's tmux
server (and its state/locks/ directory) has no visibility into a Contabo or
winbox session's liveness. Only rows whose host matches THIS machine, or
predate the host column (NULL — legacy), are checked; every other-host row
is left completely untouched, counted separately.

Also normalizes tasks.owner_cto: some pre-migration rows carry a stale
'cto-<id>' prefix from before scripts/cto-claude.sh:67 started stripping it
at write time. No current code path writes that prefix any more, so this is
a one-time backfill — safe to re-run (idempotent, matches zero rows once
clean).

Usage:
  python3 -m tools.session_reconcile             # dry run (default, no writes)
  python3 -m tools.session_reconcile --apply      # write the changes
"""
from __future__ import annotations

import argparse
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.db import get_conn, now_iso  # noqa: E402
from scripts.session_list import tmux_lock_live  # noqa: E402


def _this_host() -> str:
    """config/hosts.yaml key for the machine running THIS process.

    Mirrors the MACHINE_LABEL/HOST_KEY case statement in scripts/cto-claude.sh
    and scripts/cxo-claude.sh verbatim so the two can't disagree. There is no
    shared Python helper for a C-level session's own host key today —
    runners.worker_init.current_host() answers the analogous question for a
    spawned DEV worker via the ORG_HOST env var, which the C-level launchers
    never set for themselves (they only pass --host to register_cxo).
    """
    system = platform.system()
    if system == "Darwin":
        return "mac"
    if system == "Linux":
        if Path("/opt/mooniex-agents").is_dir():
            return "contabo"
        return (platform.node().split(".")[0] or "linux").lower()
    if system == "Windows":
        return "winbox"
    return system.lower()


def reconcile(apply: bool = False) -> dict:
    """Walk every status='open' c_level_sessions row.

    Never touches a row whose host names a different machine. Idempotent — a
    row already flipped to 'abandoned' is no longer 'open', so a second run
    leaves it alone.

    Returns a summary dict: this_host, total_open, checked, marked (list of
    (role, session_id)), skipped_other_host (list of (role, session_id, host)).
    """
    this_host = _this_host()
    ts = now_iso()
    checked = 0
    marked: list[tuple[str, str]] = []
    skipped_other_host: list[tuple[str, str, str]] = []

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, session_id, host, note FROM c_level_sessions "
            "WHERE status='open'"
        ).fetchall()

        for row in rows:
            role, sid, host, note = (
                row["role"], row["session_id"], row["host"], row["note"],
            )
            if host is not None and host != this_host:
                skipped_other_host.append((role, sid, host))
                continue

            checked += 1
            if tmux_lock_live(role, sid):
                continue

            marked.append((role, sid))
            if apply:
                new_note = (
                    f"{note}; reconciled: tmux gone" if note
                    else "reconciled: tmux gone"
                )
                conn.execute(
                    "UPDATE c_level_sessions SET status='abandoned', "
                    "closed_at=?, note=? "
                    "WHERE role=? AND session_id=? AND status='open'",
                    (ts, new_note, role, sid),
                )

    return {
        "this_host": this_host,
        "total_open": len(rows),
        "checked": checked,
        "marked": marked,
        "skipped_other_host": skipped_other_host,
    }


def normalize_owner_cto(apply: bool = False) -> int:
    """Strip a stale 'cto-' prefix from tasks.owner_cto (idempotent).

    Returns the number of rows affected (or that would be, under dry-run).
    Touches no column but owner_cto.
    """
    with get_conn() as conn:
        if not apply:
            row = conn.execute(
                "SELECT COUNT(*) c FROM tasks WHERE owner_cto LIKE 'cto-%'"
            ).fetchone()
            return row["c"]
        cur = conn.execute(
            "UPDATE tasks SET owner_cto = substr(owner_cto, 5) "
            "WHERE owner_cto LIKE 'cto-%'"
        )
        return cur.rowcount


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="tools.session_reconcile",
        description="Mark dead c_level_sessions rows 'abandoned' + "
                     "normalize tasks.owner_cto. Dry-run by default.",
    )
    ap.add_argument("--apply", action="store_true",
                     help="write changes (default is dry-run, no writes)")
    args = ap.parse_args(argv)

    result = reconcile(apply=args.apply)
    prefixed = normalize_owner_cto(apply=args.apply)

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[session_reconcile] {mode} — this machine's host key: "
          f"{result['this_host']!r}")
    print(f"  open rows (before):    {result['total_open']}")
    print(f"  checked (this host):   {result['checked']}")
    verb = "marked" if args.apply else "would mark"
    print(f"  {verb} abandoned:{' ' * (10 - len(verb))}{len(result['marked'])}")
    for role, sid in result["marked"]:
        print(f"    - {role} #{sid}")
    print(f"  skipped (other host):  {len(result['skipped_other_host'])}")
    for role, sid, host in result["skipped_other_host"]:
        print(f"    - {role} #{sid} (host={host})")
    verb2 = "normalized" if args.apply else "would normalize"
    print(f"  owner_cto 'cto-' prefix rows {verb2}: {prefixed}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
