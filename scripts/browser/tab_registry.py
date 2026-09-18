#!/usr/bin/env python3
"""Who owns which Chrome tab.

The problem this solves, measured 2026-09-04: about twenty-five Higgsfield tabs
had accumulated in one Chrome window because every browser_operator opens its
own tab and nothing has ever told one to close it. That is not only clutter —
the stale-@Video-binding bug documented in higgsfield-video-ref-fire.js happens
specifically in tabs that have touched more than one video asset, and a pile of
abandoned tabs is exactly that condition.

The rule it enforces: OWNERSHIP IS PROVABLE FROM DISK, NEVER FROM MEMORY.
A tab is yours only if its id is written in YOUR task's file. A tab in another
live task's file is untouchable. A tab in no file at all is an orphan and is
safe to close.

    tab_registry.py claim   <task-id> <tab-id> [url]
    tab_registry.py release <task-id> <tab-id>
    tab_registry.py done    <task-id>            # release all, drop the file
    tab_registry.py owner   <tab-id>             # who holds it, and are they alive
    tab_registry.py orphans <tab-id> [tab-id...] # of these, which are safe to close
    tab_registry.py list                         # every claim, with liveness

Exit codes: 0 fine, 1 the answer is "do not touch it".
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

def _repo_root() -> Path:
    """The MAIN checkout, not whatever worktree this copy happens to sit in.

    Every worker runs from `<repo>/worktrees/<project>__<role>__<task>/`, which
    is its own checkout WITHOUT the shared state directory. Resolving the root
    as parents[2] therefore pointed at the worktree, `state/tasks.db` did not
    exist there, and liveness silently answered "no tasks db" for every claim —
    which the registry then reported as safe-to-close. That is the precise
    failure this tool exists to prevent, so it is worth the extra lines.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if parent.name == "worktrees":          # cut back over the worktree
            return parent.parent
    for parent in here.parents:                 # otherwise find the real state dir
        if (parent / "state" / "tasks.db").exists():
            return parent
    return here.parents[2]


ROOT = _repo_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib import db as db_lib  # noqa: E402

REG = ROOT / "state" / "browser-tabs"
LIVE = ("pending", "in_progress")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _path(task_id: str) -> Path:
    return REG / f"{task_id}.json"


def _load(task_id: str) -> dict:
    p = _path(task_id)
    if not p.exists():
        return {"task_id": task_id, "tabs": []}
    return json.loads(p.read_text())


def _save(rec: dict) -> None:
    REG.mkdir(parents=True, exist_ok=True)
    _path(rec["task_id"]).write_text(json.dumps(rec, indent=2) + "\n")


def _task_alive(task_id: str) -> tuple[bool, str]:
    """Alive means the row says so AND the process is actually there.

    A DB row on its own has proved insufficient several times — workers have
    died with their parent session while the row still read in_progress — so
    the pid is checked too.
    """
    # FAIL SAFE, not fail open. If liveness cannot be established the
    # honest answer is "unknown", and unknown must mean hands off — the
    # cost of wrongly keeping a dead tab is a stale tab; the cost of
    # wrongly closing a live one is half an hour of somebody's staged work.
    try:
        with db_lib.get_conn(readonly=True, timeout=10) as conn:
            row = conn.execute(
                "select status, pid from tasks where id=?", (task_id,)
            ).fetchone()
    except Exception as exc:
        return True, f"UNKNOWN — cannot read tasks db ({exc}), treating as live"
    if not row:
        return False, "no such task"
    status, pid = row
    if status not in LIVE:
        return False, f"status={status}"
    if pid:
        try:
            os.kill(int(pid), 0)
        except (OSError, ValueError):
            return False, f"status={status} but pid {pid} is gone"
    return True, f"status={status} pid={pid}"


def _claims() -> dict[str, str]:
    """tab_id -> task_id, across every registry file."""
    out: dict[str, str] = {}
    if not REG.exists():
        return out
    for p in sorted(REG.glob("*.json")):
        rec = json.loads(p.read_text())
        for t in rec.get("tabs", []):
            out[str(t["tab_id"])] = rec["task_id"]
    return out


def cmd_claim(task_id: str, tab_id: str, url: str = "") -> int:
    rec = _load(task_id)
    if not any(str(t["tab_id"]) == str(tab_id) for t in rec["tabs"]):
        rec["tabs"].append({"tab_id": str(tab_id), "url": url, "opened_at": _now()})
        _save(rec)
    print(f"claimed tab {tab_id} for {task_id} ({len(rec['tabs'])} held)")
    return 0


def cmd_release(task_id: str, tab_id: str) -> int:
    rec = _load(task_id)
    before = len(rec["tabs"])
    rec["tabs"] = [t for t in rec["tabs"] if str(t["tab_id"]) != str(tab_id)]
    _save(rec)
    print(f"released {before - len(rec['tabs'])} tab(s); {len(rec['tabs'])} still held by {task_id}")
    return 0


def cmd_done(task_id: str) -> int:
    rec = _load(task_id)
    n = len(rec["tabs"])
    _path(task_id).unlink(missing_ok=True)
    print(f"{task_id} released {n} tab(s) — close them in Chrome before you report")
    return 0


def all_claims() -> dict[str, str]:
    """tab_id -> task_id across every registry file — the full claim map.

    Public sibling of the private `_claims()` this module already used
    internally, for a caller outside this file (task-92118d4e's watchdog
    sweep) that needs to know which live Chrome tabs are anybody's claim at
    all, not just one task's.
    """
    return _claims()


def tabs_for(task_id: str) -> list[dict]:
    """Every tab this task currently claims, as recorded on disk.

    Programmatic sibling of `list`/`owner` for a caller (task-92118d4e's
    close_dev) that needs the raw claim rather than a printed report.
    """
    return _load(task_id)["tabs"]


def clear(task_id: str) -> list[str]:
    """Release every tab task_id claims and drop its registry file.

    Silent sibling of cmd_done: no stdout, so a caller like close_dev (whose
    own output the watchdog sweep logs) doesn't get registry chatter mixed
    into it. Returns the tab_ids that were released.
    """
    rec = _load(task_id)
    ids = [str(t["tab_id"]) for t in rec["tabs"]]
    _path(task_id).unlink(missing_ok=True)
    return ids


def cmd_owner(tab_id: str) -> int:
    owner = _claims().get(str(tab_id))
    if not owner:
        print(f"tab {tab_id}: UNCLAIMED — orphan, safe to close")
        return 0
    alive, why = _task_alive(owner)
    if alive:
        sess = f"wd-{owner.replace('task-', '')}"
        print(f"tab {tab_id}: OWNED by {owner}, ALIVE ({why})")
        print("DO NOT CLOSE OR REFRESH IT. Tell the owner first, on the channel that works:")
        print(f'  tmux send-keys -t {sess} C-u; tmux send-keys -t {sess} "[CTO] I need to refresh Chrome. '
              f'Save your composer state and reply when it is safe."; tmux send-keys -t {sess} Enter')
        print("  then wait for that worker to answer in its own pane before touching anything.")
        return 1
    print(f"tab {tab_id}: claimed by {owner} but that task is NOT alive ({why}) — stale claim, safe to close")
    return 0


def cmd_orphans(tab_ids: list[str]) -> int:
    claims = _claims()
    safe, keep = [], []
    for t in tab_ids:
        owner = claims.get(str(t))
        if owner and _task_alive(owner)[0]:
            keep.append((t, owner))
        else:
            safe.append(t)
    print(f"SAFE TO CLOSE ({len(safe)}): {' '.join(safe) if safe else '-'}")
    for t, owner in keep:
        print(f"KEEP {t} — live owner {owner}")
    return 0


def cmd_list() -> int:
    if not REG.exists() or not any(REG.glob("*.json")):
        print("no tab claims on record")
        return 0
    for p in sorted(REG.glob("*.json")):
        rec = json.loads(p.read_text())
        alive, why = _task_alive(rec["task_id"])
        mark = "LIVE " if alive else "STALE"
        print(f"{mark} {rec['task_id']}  {len(rec['tabs'])} tab(s)  [{why}]")
        for t in rec["tabs"]:
            print(f"      {t['tab_id']}  {t.get('opened_at','?')}  {t.get('url','')[:70]}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd, rest = argv[1], argv[2:]
    if cmd == "claim" and len(rest) >= 2:
        return cmd_claim(rest[0], rest[1], rest[2] if len(rest) > 2 else "")
    if cmd == "release" and len(rest) == 2:
        return cmd_release(rest[0], rest[1])
    if cmd == "done" and len(rest) == 1:
        return cmd_done(rest[0])
    if cmd == "owner" and len(rest) == 1:
        return cmd_owner(rest[0])
    if cmd == "orphans" and rest:
        return cmd_orphans(rest)
    if cmd == "list":
        return cmd_list()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
