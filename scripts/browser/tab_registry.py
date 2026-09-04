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
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REG = ROOT / "state" / "browser-tabs"
DB = ROOT / "state" / "tasks.db"
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
    if not DB.exists():
        return False, "no tasks db"
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    row = con.execute("select status, pid from tasks where id=?", (task_id,)).fetchone()
    con.close()
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
