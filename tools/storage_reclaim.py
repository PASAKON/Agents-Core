"""Reclaim REBUILD-tier disk space inside the pilot owner's own task
worktrees — ADR 0030 §2 (orange band: REBUILD deleted automatically) and
§8 (scope: only the pilot owner's own task worktrees, never another
session's node_modules/.venv, never a project under ~/MoonieXHQ/Projects).

`plan()` walks every pilot-owned task's `worktree` (from tasks.db) looking
for directories `tools/storage_policy.classify()` puts in REBUILD. A
REBUILD entry tagged `dormancy: true` (node_modules, .venv, .next) is only
included when the whole worktree passes the disk-hygiene "dormancy test"
(.claude/skills/disk-hygiene/SKILL.md §"The dormancy test, exactly") — no
file anywhere under the worktree (excluding node_modules/.venv/.git)
modified in the last 14 days, AND no `next dev|next-server|vite|uvicorn`
process whose cwd is inside it. Entries with no `dormancy` flag (caches,
__pycache__, .pytest_cache) are always included — same as the skill's
Green list, no asking.

`apply()` deletes with `shutil.rmtree` (never a shell `rm`) and appends one
JSON line per deleted item to state/storage/reclaim.jsonl.

CLI:
    python tools/storage_reclaim.py          # dry-run: list what would go
    python tools/storage_reclaim.py --apply  # delete it
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from tools import storage_policy
except ImportError:
    # `python tools/storage_reclaim.py` run directly only puts tools/ on
    # sys.path, not the repo root the `tools` package lives under.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import storage_policy

ROOT = Path(__file__).resolve().parent.parent
STORAGE_POLICY = ROOT / "config" / "storage-policy.yaml"
LEDGER_PATH = ROOT / "state" / "storage" / "reclaim.jsonl"

DORMANCY_WINDOW_DAYS = 14
_DORMANCY_EXCLUDED_DIRS = {"node_modules", ".venv", ".git"}
_LIVE_DEV_PROCESS_RE = re.compile(r"next dev|next-server|vite|uvicorn")


# --------------------------------------------------------------------- plan

def _pilot_tasks(db_path: str | Path, owners: list[str]) -> list[dict]:
    """Rows from `db_path`'s tasks table whose owner_cto is in `owners`."""
    if not owners:
        return []
    placeholders = ",".join("?" for _ in owners)
    try:
        conn = sqlite3.connect(str(db_path))
    except sqlite3.Error:
        return []
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"SELECT id, worktree, owner_cto FROM tasks WHERE owner_cto IN ({placeholders})",
            list(owners),
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()
    return [dict(r) for r in rows]


def _matching_rebuild_entry(path_str: str, policy: dict, home: str) -> dict | None:
    for entry in policy.get("tiers", {}).get("REBUILD", []):
        if storage_policy.match_path(path_str, entry["glob"], home):
            return entry
    return None


def _iter_rebuild_dirs(root: str, policy: dict, home: str):
    """Yield (path, entry) for every directory under `root` that
    classify() puts in REBUILD. Never descends into a symlink (os.walk's
    `followlinks=False` already refuses to, this also excludes the symlink
    itself from the result) or further into a directory already yielded
    (a REBUILD match is not re-scanned for nested REBUILD matches)."""
    for dirpath, dirnames, _filenames in os.walk(root, topdown=True, followlinks=False):
        keep = []
        for name in dirnames:
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                continue  # never include a symlink
            tier = storage_policy.classify(full, policy, home=Path(home))
            if tier == "REBUILD":
                entry = _matching_rebuild_entry(full, policy, home)
                if entry is not None:
                    yield full, entry
                continue  # prune: don't descend into a matched dir
            keep.append(name)
        dirnames[:] = keep


def _dir_size_bytes(path: str) -> int:
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path, followlinks=False):
        for name in filenames:
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                continue
            try:
                total += os.lstat(full).st_size
            except OSError:
                continue
    return total


def _has_recent_file(worktree: str, window_days: int = DORMANCY_WINDOW_DAYS) -> bool:
    cutoff = time.time() - window_days * 86400
    for dirpath, dirnames, filenames in os.walk(worktree, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in _DORMANCY_EXCLUDED_DIRS]
        for name in filenames:
            full = os.path.join(dirpath, name)
            try:
                mtime = os.path.getmtime(full)
            except OSError:
                continue
            if mtime >= cutoff:
                return True
    return False


def _pids_matching_dev_process() -> list[int] | None:
    """PIDs of processes whose command line matches next dev|next-server|
    vite|uvicorn, or None if `ps` could not be run (inconclusive)."""
    try:
        out = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    pids: list[int] = []
    for line in out.stdout.splitlines()[1:]:
        if not _LIVE_DEV_PROCESS_RE.search(line):
            continue
        cols = line.split(None, 10)
        if len(cols) < 2:
            continue
        try:
            pids.append(int(cols[1]))
        except ValueError:
            continue
    return pids


def _pid_cwd(pid: int) -> str | None:
    try:
        out = subprocess.run(["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"],
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    for line in out.stdout.splitlines():
        if line.startswith("n"):
            return line[1:]
    return None


def _has_live_dev_process(worktree: str) -> bool:
    """True if a next dev|next-server|vite|uvicorn process's cwd is inside
    `worktree`. Fails closed: if `ps`/`lsof` can't be run at all, treat as
    "yes, something's live" — a reclaim must never guess "nothing running"
    when it genuinely cannot check."""
    pids = _pids_matching_dev_process()
    if pids is None:
        return True
    root = Path(worktree).resolve()
    for pid in pids:
        cwd = _pid_cwd(pid)
        if not cwd:
            continue
        try:
            resolved = Path(cwd).resolve()
        except OSError:
            continue
        if resolved == root or root in resolved.parents:
            return True
    return False


def _is_dormant(worktree: str) -> bool:
    if _has_recent_file(worktree):
        return False
    if _has_live_dev_process(worktree):
        return False
    return True


def plan(db_path: str | Path, policy: dict, owners: list[str]) -> list[dict]:
    """[{path, bytes, reason, task, owner}] for every REBUILD directory
    inside a pilot-owned task's worktree, safe to delete right now."""
    home = str(Path.home())
    results: list[dict] = []
    for task in _pilot_tasks(db_path, owners):
        worktree = task.get("worktree")
        if not worktree or not os.path.isdir(worktree):
            continue
        # Fail closed: only a real task worktree (a direct child of a
        # `worktrees/` dir) is ever walked. A row whose worktree points at a
        # repo root or anywhere else is skipped, whatever tasks.db says.
        if os.path.islink(worktree) or Path(worktree).resolve().parent.name != "worktrees":
            continue
        dormant: bool | None = None
        for dirpath, entry in _iter_rebuild_dirs(worktree, policy, home):
            if entry.get("dormancy"):
                if dormant is None:
                    dormant = _is_dormant(worktree)
                if not dormant:
                    continue
            results.append({
                "path": dirpath,
                "bytes": _dir_size_bytes(dirpath),
                "reason": entry.get("rebuild", ""),
                "task": task.get("id"),
                "owner": task.get("owner_cto"),
            })
    return results


# -------------------------------------------------------------------- apply

def apply(items: list[dict], ledger_path: str | Path | None = None) -> list[dict]:
    """Delete every item's path with shutil.rmtree and append one JSON line
    per successfully-deleted item to the ledger. Returns the items actually
    deleted (skips anything that turned into a symlink or vanished since
    plan() ran, rather than raising)."""
    ledger = Path(ledger_path) if ledger_path is not None else LEDGER_PATH
    deleted: list[dict] = []
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as fh:
        for item in items:
            path = item["path"]
            if os.path.islink(path) or not os.path.isdir(path):
                continue
            try:
                shutil.rmtree(path)
            except OSError:
                continue
            deleted.append(item)
            line = {
                "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
                "path": path,
                "bytes": item.get("bytes", 0),
                "task": item.get("task"),
                "owner": item.get("owner"),
            }
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")
    return deleted


# ------------------------------------------------------------------------ CLI

def _default_db_path() -> Path:
    from lib import db as db_mod
    return db_mod.DB_PATH


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="delete instead of listing")
    parser.add_argument("--db", default=None, help="tasks.db path (default: lib.db.DB_PATH)")
    parser.add_argument("--policy", default=str(STORAGE_POLICY))
    args = parser.parse_args()

    try:
        policy = storage_policy.load(args.policy)
    except storage_policy.PolicyError as e:
        print(f"PolicyError: {e}")
        sys.exit(1)

    owners = policy.get("pilot_owner_cto") or []
    db_path = args.db or str(_default_db_path())

    items = plan(db_path, policy, owners)
    if not items:
        print("nothing to reclaim")
        return

    total = 0
    for item in items:
        total += item["bytes"]
        print(f"{item['bytes']:>14}  {item['path']}  ({item['reason']}, task={item['task']})")
    print(f"TOTAL: {total} bytes across {len(items)} item(s)")

    if args.apply:
        deleted = apply(items)
        print(f"deleted {len(deleted)} item(s)")


if __name__ == "__main__":
    main()
