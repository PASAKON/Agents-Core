"""Work/<task_id>/ folder lifecycle — Work/RULES.md, ADR 0030 (task-36aaa3c4).

Pilot-scoped: applies only when `tools.delegate._storage_applies(owner_cto)`
is true for a task's owner. tools/delegate.py calls create() at spawn;
tools/git_ops.py's merge_task calls close() as a pre-merge gate. A task
outside the pilot scope never touches this module at all.

Layout: `Work/<task_id>/{in,tmp,out}` — `in/` = downloads/references (each
covered by a line in `in/SOURCES.txt`: `<file>\\t<url|local:path>\\t<sha256>`),
`tmp/` = intermediates (discarded at close, no questions asked), `out/` =
deliverables (filed to their home — Assets via hq-filing, or Drive via
gdrive-filing — by a human/CTO step outside this tool before close() can
succeed).

CLI:
    python tools/workdir.py create   task-abc12345
    python tools/workdir.py check    task-abc12345
    python tools/workdir.py close    task-abc12345 [--dry-run] [--archive]
    python tools/workdir.py orphans  [--db state/tasks.db]

--archive (task-abc20690, tools/work_archive.py) cold-archives whatever
close() would otherwise leave as unfiled — to Drive `BACKUP/`, md5-verified —
instead of keeping the folder around.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
STORAGE_POLICY = ROOT / "config" / "storage-policy.yaml"
DEFAULT_ROOT = "~/MoonieXHQ/Work"

TASK_ID_RE = re.compile(r"^task-[0-9a-f]{8}$")
LEDGER_NAME = "_ledger.jsonl"
SOURCES_NAME = "SOURCES.txt"
LAYOUT = ("in", "tmp", "out")

# Statuses whose Work folder is an orphan once the task lands there (rule
# 8). A task id absent from tasks.db entirely ("unknown") is handled
# separately in orphans() — it isn't in this set.
_ORPHAN_STATUSES = {"done", "merged", "cancelled", "failed"}


def _validate_task_id(task_id: str) -> None:
    if not TASK_ID_RE.match(task_id or ""):
        raise ValueError(
            f"invalid task id {task_id!r}: expected 'task-' + 8 hex chars"
        )


def _default_root() -> Path:
    """`work_dir.root` from config/storage-policy.yaml, ~-expanded.

    Reads the YAML directly rather than going through tools/storage_policy
    .load() — that loader validates the full gauge+tiers schema (J1,
    2026-09-23) and would reject a minimal fixture that only declares
    `work_dir`, which is exactly what test callers inject via `root=`.
    Mirrors tools/delegate.py's own private `_disk_orange_floor_gb` loader
    for the same reason."""
    try:
        data = yaml.safe_load(STORAGE_POLICY.read_text()) or {}
    except (OSError, yaml.YAMLError):
        data = {}
    root = ((data.get("work_dir") or {}).get("root")) or DEFAULT_ROOT
    return Path(root).expanduser()


def _resolve_root(root: str | Path | None) -> Path:
    return Path(root).expanduser() if root is not None else _default_root()


def _task_folder(task_id: str, root: str | Path | None) -> Path:
    _validate_task_id(task_id)
    return _resolve_root(root) / task_id


def folder_path(task_id: str, *, root: str | Path | None = None) -> Path:
    """Where Work/<task_id>/ would live, valid id or not created yet."""
    return _task_folder(task_id, root)


# --------------------------------------------------------------------- create

def create(task_id: str, *, root: str | Path | None = None) -> Path:
    """Work/<task_id>/{in,tmp,out} — rule 1. Idempotent: safe to call again
    on an already-created folder (a respawn after an unclaimed spawn hits
    this)."""
    folder = _task_folder(task_id, root)
    for sub in LAYOUT:
        (folder / sub).mkdir(parents=True, exist_ok=True)
    return folder


# ---------------------------------------------------------------------- check

def _parse_sources(sources_file: Path) -> set[str]:
    """`<file>\\t<url|local:path>\\t<sha256>` → the set of `<file>` entries
    (paths relative to in/, posix-separated). A missing file or a
    malformed/blank first field just covers nothing — no partial credit
    for a broken line; check()/close() then treat that input as unfiled."""
    covered: set[str] = set()
    if not sources_file.exists():
        return covered
    for line in sources_file.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        first = line.split("\t", 1)[0].strip()
        if first:
            covered.add(first)
    return covered


def _in_files(in_dir: Path) -> list[Path]:
    """Files under in/, recursive, excluding SOURCES.txt itself."""
    if not in_dir.exists():
        return []
    return sorted(
        p for p in in_dir.rglob("*")
        if p.is_file() and p.name != SOURCES_NAME
    )


def check(task_id: str, *, root: str | Path | None = None) -> list[str]:
    """Violations in Work/<task_id>/ — rules 1, 3, 10. Read-only."""
    folder = _task_folder(task_id, root)
    if not folder.is_dir():
        raise FileNotFoundError(f"no such Work folder: {folder}")

    violations: list[str] = []

    # Rule 1: only in/, tmp/, out/ at the folder root.
    for entry in sorted(folder.iterdir()):
        if entry.name not in LAYOUT:
            violations.append(f"unexpected entry at folder root: {entry.name}")

    # Rule 3: every in/ file needs one in/SOURCES.txt line.
    in_dir = folder / "in"
    covered = _parse_sources(in_dir / SOURCES_NAME)
    for f in _in_files(in_dir):
        rel = f.relative_to(in_dir).as_posix()
        if rel not in covered:
            violations.append(f"unfiled input (no SOURCES.txt line): in/{rel}")

    # Rule 10: no symlink, .git, .env* anywhere in the folder.
    # followlinks=False so a symlinked directory is reported, not walked
    # into (avoids a symlink loop back onto the folder itself).
    for dirpath, dirnames, filenames in os.walk(folder, followlinks=False):
        for name in dirnames + filenames:
            full = Path(dirpath) / name
            rel = full.relative_to(folder).as_posix()
            if full.is_symlink():
                violations.append(f"symlink: {rel}")
            elif name == ".git":
                violations.append(f"git repo: {rel}")
            elif name.startswith(".env"):
                violations.append(f"secret-like file: {rel}")

    return violations


# ---------------------------------------------------------------------- close

def _dir_size(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        if p.is_file() and not p.is_symlink():
            total += p.stat().st_size
    return total


def close(task_id: str, *, dry_run: bool = False,
          root: str | Path | None = None, by: str | None = None,
          archive: bool = False) -> dict:
    """Close Work/<task_id>/ — rule 6, narrowed to this tool's scope
    (task-36aaa3c4 brief): tmp/ is always deleted, and every in/ file
    covered by in/SOURCES.txt is always deleted (re-downloadable — nothing
    to keep), regardless of whether the close can complete. Filing an
    unfiled in/ file or an out/ deliverable to its home (Assets via
    hq-filing, or Drive via gdrive-filing) is a human/CTO step outside this
    tool — close() only removes the folder + appends the ledger line once
    nothing but tmp/(gone) and filed in/ files were ever in it.

    archive=True (task-abc20690) routes whatever's left — unsourced in/
    files and out/ files — through work_archive.archive(dry_run=False)
    instead of leaving them as unfiled: only once that comes back
    `verified: True` are they deleted and the close completed, and the
    ledger's `dest`/`md5` are filled from it. Without archive=True, close()
    behaves exactly as it did before this option existed.

    dry_run=True previews with zero filesystem changes: nothing deleted,
    no ledger write, no archive attempt.

    Returns `{"closed": True, "ledger": {...}}` on success, or
    `{"closed": False, "unfiled": [...]}` — the folder is left in place
    (with tmp/ and filed in/ files already gone on a real run)."""
    folder = _task_folder(task_id, root)
    if not folder.is_dir():
        raise FileNotFoundError(f"no such Work folder: {folder}")

    tmp_dir, in_dir = folder / "tmp", folder / "in"
    sources_path = in_dir / SOURCES_NAME
    covered = _parse_sources(sources_path)
    in_files = _in_files(in_dir)
    filed = [f for f in in_files if f.relative_to(in_dir).as_posix() in covered]
    filed_set = set(filed)

    tmp_bytes = _dir_size(tmp_dir) if tmp_dir.exists() else 0
    reclaimed = tmp_bytes + sum(f.stat().st_size for f in filed)

    if dry_run:
        unfiled = [
            p for p in folder.rglob("*")
            if p.is_file() and p != sources_path and p not in filed_set
            and not p.is_relative_to(tmp_dir)
        ]
        return {
            "closed": not unfiled,
            "dry_run": True,
            "would_delete_tmp": tmp_dir.exists(),
            "would_delete_in": [str(f) for f in filed],
            "unfiled": [str(p) for p in unfiled],
            "bytes": reclaimed,
        }

    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    for f in filed:
        f.unlink()

    remaining = [p for p in folder.rglob("*") if p.is_file() and p != sources_path]
    remaining_bytes = sum(p.stat().st_size for p in remaining)

    archived: dict | None = None
    if remaining and archive:
        from tools import work_archive  # lazy: avoids a workdir<->work_archive import cycle
        rel_paths = [p.relative_to(folder).as_posix() for p in remaining]
        archived = work_archive.archive(task_id, rel_paths, root=root, dry_run=False)
        if archived.get("verified"):
            for p in remaining:
                p.unlink()
            reclaimed += remaining_bytes
            remaining = []

    if remaining:
        result: dict = {"closed": False, "unfiled": [str(p) for p in remaining]}
        if archived is not None:
            result["archive_error"] = archived.get("error")
        return result

    if sources_path.exists():
        sources_path.unlink()
    shutil.rmtree(folder)

    entry = {
        "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
        "task": task_id,
        "bytes": reclaimed,
        # Populated from a verified work_archive.archive() above; otherwise
        # nothing archived by this close (only tmp/, discarded, and
        # re-downloadable in/ files already covered by SOURCES.txt were
        # removed), so dest/md5 stay empty.
        "dest": archived["dest"] if archived else "",
        "md5": archived["md5"] if archived else "",
        "by": by or os.environ.get("WORKER_CTO_ID") or getpass.getuser(),
    }
    root_dir = _resolve_root(root)
    root_dir.mkdir(parents=True, exist_ok=True)
    with (root_dir / LEDGER_NAME).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return {"closed": True, "ledger": entry}


# -------------------------------------------------------------------- orphans

def orphans(db: str | Path, *, root: str | Path | None = None,
            now: datetime | None = None) -> list[dict]:
    """Work/ folders whose task is done/merged/cancelled/failed or absent
    from `db` (a tasks.db sqlite path) — rule 8. Read-only; never touches a
    folder. Flags any folder whose task's updated_at is > 24h old, or whose
    task id isn't in `db` at all (nothing to measure age from, so it is
    always flagged)."""
    root_dir = _resolve_root(root)
    now = now or datetime.now(timezone.utc)

    status_by_id: dict[str, str] = {}
    updated_by_id: dict[str, str] = {}
    try:
        conn = sqlite3.connect(str(db))
        try:
            for tid, status, updated_at in conn.execute(
                "SELECT id, status, updated_at FROM tasks"
            ):
                status_by_id[tid] = status
                updated_by_id[tid] = updated_at
        finally:
            conn.close()
    except sqlite3.Error:
        pass  # unreadable/missing db -> every folder below reads as unknown

    results: list[dict] = []
    if not root_dir.is_dir():
        return results

    for folder in sorted(root_dir.iterdir()):
        if not folder.is_dir() or not TASK_ID_RE.match(folder.name):
            continue
        task_id = folder.name
        status = status_by_id.get(task_id)
        if status is not None and status not in _ORPHAN_STATUSES:
            continue  # active task — not an orphan

        updated_at = updated_by_id.get(task_id)
        age_hours: float | None = None
        if updated_at:
            try:
                dt = datetime.fromisoformat(updated_at)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                age_hours = (now - dt).total_seconds() / 3600
            except ValueError:
                age_hours = None

        results.append({
            "task": task_id,
            "status": status or "unknown",
            "updated_at": updated_at,
            "age_hours": age_hours,
            "flagged": age_hours is None or age_hours > 24,
        })

    return results


# ------------------------------------------------------------------------ CLI

def _print_json(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def _cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="tools/workdir.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_create = sub.add_parser("create", help="make Work/<task_id>/{in,tmp,out}")
    p_create.add_argument("task_id")
    p_create.add_argument("--root", default=None)

    p_check = sub.add_parser("check", help="list violations (read-only)")
    p_check.add_argument("task_id")
    p_check.add_argument("--root", default=None)

    p_close = sub.add_parser("close", help="close a task's Work folder")
    p_close.add_argument("task_id")
    p_close.add_argument("--dry-run", action="store_true")
    p_close.add_argument("--root", default=None)
    p_close.add_argument("--archive", action="store_true",
                         help="cold-archive unfiled in/out files to Drive BACKUP/ instead of leaving them")

    p_orphans = sub.add_parser("orphans", help="folders whose task is over (read-only)")
    p_orphans.add_argument("--db", default=None,
                           help="tasks.db path (default state/tasks.db)")
    p_orphans.add_argument("--root", default=None)

    args = parser.parse_args(argv)

    if args.cmd == "create":
        print(str(create(args.task_id, root=args.root)))
        return 0

    if args.cmd == "check":
        violations = check(args.task_id, root=args.root)
        if not violations:
            print("ok — no violations")
            return 0
        for v in violations:
            print(v)
        return 1

    if args.cmd == "close":
        result = close(args.task_id, dry_run=args.dry_run, root=args.root,
                       archive=args.archive)
        _print_json(result)
        return 0 if result.get("closed") else 1

    if args.cmd == "orphans":
        db_path = args.db or str(ROOT / "state" / "tasks.db")
        _print_json(orphans(db_path, root=args.root))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
