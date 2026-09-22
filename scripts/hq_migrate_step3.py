#!/usr/bin/env python3
"""scripts/hq_migrate_step3.py — MoonieX HQ migration step 3 (ADR 0028): move the
eleven `step: 3` rows of ~/MoonieXHQ/hq.yaml (ten MoonieX products + LinkReed/Webapp)
from their flat `/Users/gob/Projects/<name>` homes into ~/MoonieXHQ/Projects/<Brand>/<Suffix>.

Reuses hq_migrate_step2's git/manifest primitives (git_preflight, push_current_branch,
move_and_verify, patch_yaml_row, Manifest) rather than re-implementing them. Step 3 has
no umbrella dirs and no duplicate clones (unlike step 2) but adds three things step 2
never needed:

  1. worktree repair    — some of these repos have OTHER git worktrees attached
                           (claudeflow x2, console, scriptable) that must keep working
                           after the main repo moves.
  2. compat symlinks     — `/Users/gob/Projects/` itself is NOT moving this step, so
                           every old path becomes a symlink to the new location
                           (recorded in hq.yaml `compat_links:`, judged by hq.py doctor).
  3. launchd plists       — 2 of the 3 named plists hard-code an old path; rewritten
                           in place (text edit + `plutil -lint`), never `launchctl`'d.

  hq_migrate_step3.py                       # --plan (default): prints, touches nothing
  hq_migrate_step3.py --apply               # do it for real
  hq_migrate_step3.py --repoint             # rewrite this repo's own hardcoded old paths
  hq_migrate_step3.py --rollback <manifest.json>

Validation (preflight + push) runs for ALL step-3 rows BEFORE any move happens, same
"nothing half-moved" guarantee as step 2. There are no duplicate clones this step.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("hq_migrate_step3.py needs PyYAML — run with /Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hq_migrate_step2 import (  # noqa: E402  (reuse, do not copy — task instruction)
    Manifest,
    _run,
    git_preflight,
    move_and_verify,
    patch_yaml_row,
    push_current_branch,
)

ROOT = Path(__file__).resolve().parent.parent
HQ_ROOT = Path(os.environ.get("HQ_ROOT", "/Users/gob/MoonieXHQ"))
STATE_DIR = Path(os.environ.get("HQ_STEP3_STATE_DIR", str(ROOT / "state")))
HQ_PYTHON = os.environ.get("HQ_PYTHON", "/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python")
REPO_ROOT = Path(os.environ.get("HQ_STEP3_REPO_ROOT", str(ROOT)))

_DEFAULT_PLISTS = ":".join(str(Path.home() / "Library" / "LaunchAgents" / n) for n in (
    "com.mooniex.console-mac.plist",
    "com.mooniex.claude-usage-sync.plist",
    "com.mooniex.webapp.autopull.plist",
))
LAUNCHD_PLISTS = [Path(p) for p in os.environ.get("HQ_STEP3_PLISTS", _DEFAULT_PLISTS).split(":") if p]

DOC_EXCLUDE_PATHSPECS = [":!docs/reports", ":!docs/briefs", ":!docs/ops", ":!*.md"]


# ─────────────────────────── rows / mapping ──────────────────────────────────

def step3_rows(hq_yaml: Path) -> list[dict]:
    data = yaml.safe_load(hq_yaml.read_text(encoding="utf-8"))
    return [r for r in data["folders"] if r.get("step") == 3 and r.get("current")]


def build_path_mapping(hq_root: Path, rows: list[dict]) -> dict[str, str]:
    """old `current` path -> new `hq_root/path` target, for every step-3 row.
    Read BEFORE hq.yaml's `current` fields are rewritten — that's the only time
    the old path is still recoverable from the map."""
    return {r["current"]: str(hq_root / r["path"]) for r in rows}


# ─────────────────────────── worktree repair ─────────────────────────────────

def list_attached_worktrees(path: Path) -> list[str]:
    """Every OTHER worktree attached to the repo at `path` that still exists on
    disk (excludes the repo itself, and excludes a dangling/prunable entry —
    e.g. a scratch review checkout under /tmp that was already deleted without
    `git worktree remove`; there is nothing to repair there, `repair` just
    errors "not a valid path". `git worktree prune` clears the stale entry."""
    r = _run(["git", "-C", str(path), "worktree", "list", "--porcelain"])
    all_paths = [line[len("worktree "):].strip() for line in r.stdout.splitlines() if line.startswith("worktree ")]
    main = str(path.resolve())
    live = [p for p in all_paths if str(Path(p).resolve()) != main]
    missing = [p for p in live if not Path(p).exists()]
    if missing:
        _run(["git", "-C", str(path), "worktree", "prune"])
    return [p for p in live if Path(p).exists()]


def repair_worktree(new_repo: Path, worktree_path: Path) -> None:
    r = _run(["git", "-C", str(new_repo), "worktree", "repair", str(worktree_path)])
    if r.returncode != 0:
        raise RuntimeError(f"worktree repair failed for {worktree_path} against {new_repo}: {r.stdout}{r.stderr}")
    st = _run(["git", "-C", str(worktree_path), "status"])
    if st.returncode != 0:
        raise RuntimeError(f"git status failed in repaired worktree {worktree_path}: {st.stdout}{st.stderr}")
    gd = _run(["git", "-C", str(worktree_path), "rev-parse", "--git-dir"]).stdout.strip()
    gd_path = Path(gd)
    if not gd_path.is_absolute():
        gd_path = (worktree_path / gd_path).resolve()
    else:
        gd_path = gd_path.resolve()
    expected_prefix = str((new_repo / ".git" / "worktrees").resolve())
    if not str(gd_path).startswith(expected_prefix):
        raise RuntimeError(f"worktree {worktree_path} git-dir {gd_path} not inside {expected_prefix}")


# ─────────────────────────── compat symlinks ─────────────────────────────────

def create_compat_symlink(old_path: Path, new_path: Path) -> None:
    if old_path.exists() or old_path.is_symlink():
        raise RuntimeError(f"compat symlink target already occupied: {old_path}")
    old_path.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(str(new_path), str(old_path))


# ─────────────────────────── hq.yaml compat_links ────────────────────────────

def append_compat_links(lines: list[str], entries: list[dict]) -> list[str]:
    if not entries:
        return lines
    block = [f'  - {{path: "{e["path"]}", target: "{e["target"]}", remove_at_step: {e["remove_at_step"]}}}\n' for e in entries]
    out: list[str] = []
    inserted = False
    for line in lines:
        out.append(line)
        if not inserted and line.startswith("compat_links:"):
            out.extend(block)
            inserted = True
    if not inserted:
        out.append("compat_links:\n")
        out.extend(block)
    return out


# ─────────────────────────── launchd plists ──────────────────────────────────

def rewrite_plist_paths(plist_path: Path, mapping: dict[str, str], ts: str, m: Manifest) -> bool:
    if not plist_path.exists():
        m.note(f"plist missing, skipped: {plist_path}")
        return False
    original = plist_path.read_text()
    text = original
    for old, new in mapping.items():
        text = text.replace(old, new)
    if text == original:
        m.note(f"plist unchanged (no literal path match — compat symlink keeps it running): {plist_path}")
        return False
    backup = STATE_DIR / f"hq-step3-plist-backup-{ts}-{plist_path.name}"
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_text(original)
    m.add(op="plist_backup", from_=str(plist_path), to=str(backup))
    tmp = plist_path.with_suffix(plist_path.suffix + ".tmp")
    tmp.write_text(text)
    lint = _run(["plutil", "-lint", str(tmp)])
    if lint.returncode != 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"plutil -lint failed for {plist_path}: {lint.stdout}{lint.stderr}")
    shutil.move(str(tmp), str(plist_path))
    m.add(op="plist_edit", path=str(plist_path))
    m.note(f"plist rewritten: {plist_path}")
    return True


# ─────────────────────────── repoint: this repo's own hardcoded paths ────────

def _repoint_pattern(mapping: dict[str, str]) -> str:
    return "(" + "|".join(re.escape(k) for k in mapping) + ")"


def find_repoint_files(repo_root: Path, mapping: dict[str, str]) -> list[str]:
    if not mapping:
        return []
    r = _run(["git", "grep", "-I", "-l", "-E", _repoint_pattern(mapping), "--", ".", *DOC_EXCLUDE_PATHSPECS], cwd=repo_root)
    return [l for l in r.stdout.splitlines() if l.strip()]


def _validate_structured(path: Path, text: str) -> None:
    if path.suffix in (".yaml", ".yml"):
        yaml.safe_load(text)
    elif path.suffix == ".json":
        json.loads(text)


def rewrite_repoint_files(repo_root: Path, mapping: dict[str, str]) -> list[str]:
    changed: list[str] = []
    for rel in find_repoint_files(repo_root, mapping):
        p = repo_root / rel
        text = p.read_text()
        new_text = text
        for old, new in mapping.items():
            new_text = new_text.replace(old, new)
        if new_text == text:
            continue
        _validate_structured(p, new_text)
        p.write_text(new_text)
        changed.append(rel)
    return changed


def repoint_files_clean(repo_root: Path, mapping: dict[str, str]) -> bool:
    return not find_repoint_files(repo_root, mapping)


def cmd_repoint(hq_root: Path, repo_root: Path) -> int:
    hq_yaml = hq_root / "hq.yaml"
    rows = step3_rows(hq_yaml)
    mapping = build_path_mapping(hq_root, rows)
    changed = rewrite_repoint_files(repo_root, mapping)
    print(f"repoint — {len(changed)} file(s) rewritten:")
    for c in changed:
        print(f"  {c}")
    clean = repoint_files_clean(repo_root, mapping)
    print("repoint: grep-clean" if clean else "repoint: STILL matches old paths — check")
    return 0 if clean else 1


# ─────────────────────────── plan / apply ────────────────────────────────────

def cmd_plan(hq_root: Path) -> int:
    hq_yaml = hq_root / "hq.yaml"
    rows = step3_rows(hq_yaml)
    print(f"PLAN — {len(rows)} step-3 row(s), nothing will change:\n")
    for r in rows:
        target = hq_root / r["path"]
        src = Path(r["current"])
        if src.resolve() == target.resolve():
            print(f"  ALREADY MIGRATED  {src}  ->  {target}  (compat symlink already in place)")
            continue
        info = git_preflight(src)
        wts = list_attached_worktrees(src)
        push_note = ""
        if info["ahead"] and info["has_upstream"]:
            push_note = f"  PUSH NEEDED: branch {info['branch']} ahead {info['ahead']}"
        elif not info["has_upstream"]:
            push_note = "  NOT PUSHED: no upstream"
        print(f"  MOVE  {src}  ->  {target}   [{info['branch']} @ {info['sha'][:10]}, dirty={info['dirty']}]{push_note}")
        for wt in wts:
            print(f"    WORKTREE (will repair): {wt}")
    print("\nlaunchd plists to rewrite:")
    for p in LAUNCHD_PLISTS:
        print(f"  {p}")
    print("\nplan only — no filesystem or yaml changes made.")
    return 0


def cmd_apply(hq_root: Path) -> int:
    hq_yaml = hq_root / "hq.yaml"
    rows = step3_rows(hq_yaml)
    ts = time.strftime("%Y%m%dT%H%M%S")
    STATE_DIR.mkdir(parents=True, exist_ok=True)  # Manifest._flush() mkdirs step2's own
    m = Manifest(ts)                              # module-level STATE_DIR, not self.path.parent
    m.path = STATE_DIR / f"hq-step3-migration-{ts}.json"

    # capture the old->new mapping BEFORE hq.yaml's `current` fields move
    mapping = build_path_mapping(hq_root, rows)

    # ---- Phase A: preflight + push. No moves yet. ----
    print("Phase A — preflight, push (no moves yet)\n")
    problems: list[str] = []
    preflights: dict[str, dict] = {}
    worktrees: dict[str, list[str]] = {}
    already_done: set[str] = set()
    for r in rows:
        src = Path(r["current"])
        target = hq_root / r["path"]
        # resumability: a prior --apply may have already moved+symlinked this
        # row (crashed on a LATER row) — `src` then resolves straight through
        # the compat symlink to `target`. Nothing left to do for it here.
        if src.resolve() == target.resolve():
            already_done.add(r["path"])
            m.note(f"already migrated (symlink -> target already in place), skipping: {r['path']}")
            print(f"  {r['path']}: already migrated, skipping")
            continue
        info = git_preflight(src)
        preflights[r["path"]] = info
        worktrees[r["path"]] = list_attached_worktrees(src)
        m.add(op="preflight", row=r["path"], **{k: v for k, v in info.items() if k != "remotes"}, worktrees=worktrees[r["path"]])
        print(f"  {r['path']}: branch={info['branch']} sha={info['sha'][:10]} dirty={info['dirty']} ahead={info['ahead']} has_upstream={info['has_upstream']}")
        if not info["has_upstream"]:
            m.note(f"not pushed: no upstream — {r['path']} branch {info['branch']}")
            continue
        if info["ahead"] > 0:
            ok, out = push_current_branch(src)
            m.add(op="push", row=r["path"], path=str(src), branch=info["branch"], ahead=info["ahead"], ok=ok, output=out)
            if not ok:
                problems.append(f"{r['path']}: git push failed for branch {info['branch']}: {out}")
                continue
            m.note(f"pushed {src} branch {info['branch']} (+{info['ahead']})")

    if problems:
        print("\nSTOP — validation failed, nothing moved:\n")
        for p in problems:
            print(f"  ✗ {p}")
        m.note("APPLY STOPPED at Phase A validation — no repo moved, hq.yaml untouched")
        for p in problems:
            m.note(f"BLOCKER: {p}")
        print(f"\nmanifest (pushes made so far, if any): {m.path}")
        return 1

    print("\nPhase A clean. Phase B — moving repos, repairing worktrees, compat symlinks\n")

    # ---- Phase B: move + worktree repair + compat symlink, per row ----
    moved_rows: list[dict] = []
    for r in rows:
        src = Path(r["current"])
        target = hq_root / r["path"]

        if r["path"] not in already_done:
            info = preflights[r["path"]]
            move_and_verify(src, target, info["sha"], info["remotes"])
            m.add(op="move", from_=str(src), to=str(target), sha=info["sha"])
            m.note(f"moved: {src} -> {target}")

            for wt in worktrees[r["path"]]:
                repair_worktree(target, Path(wt))
                m.add(op="worktree_repair", row=r["path"], worktree=wt, target=str(target), original_repo=str(src))
                m.note(f"worktree repaired: {wt} -> {target}")

            create_compat_symlink(src, target)
            m.add(op="symlink", path=str(src), target=str(target))
            m.note(f"compat symlink: {src} -> {target}")

        # already-done rows still need their hq.yaml current/compat_links
        # recorded — a prior crashed run never reached Phase D for them.
        r["_target"] = target
        r["_orig_current"] = r["current"]
        moved_rows.append(r)

    # ---- Phase C: launchd plists ----
    print("\nPhase C — launchd plists\n")
    for plist in LAUNCHD_PLISTS:
        rewrite_plist_paths(plist, mapping, ts, m)

    # ---- Phase D: hq.yaml update (current: + compat_links:) ----
    print("\nPhase D — hq.yaml update\n")
    backup = STATE_DIR / f"hq-step3-yaml-backup-{ts}.yaml"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(hq_yaml, backup)
    m.add(op="yaml_backup", from_=str(hq_yaml), to=str(backup))
    lines = hq_yaml.read_text(encoding="utf-8").splitlines(keepends=True)
    compat_entries: list[dict] = []
    for r in moved_rows:
        lines = patch_yaml_row(lines, r["path"], str(r["_target"]), drop_duplicates=False)
        compat_entries.append({"path": r["_orig_current"], "target": str(r["_target"]), "remove_at_step": 4})
    lines = append_compat_links(lines, compat_entries)
    new_text = "".join(lines)
    yaml.safe_load(new_text)  # must still parse
    hq_yaml.write_text(new_text, encoding="utf-8")
    m.add(op="yaml_edit", path=str(hq_yaml), rows=[r["path"] for r in moved_rows])
    m.note(f"hq.yaml updated for {len(moved_rows)} row(s); backup at {backup}")

    # ---- hq.py map + doctor (best-effort — must never crash a completed migration) ----
    hq_py = hq_root / "scripts" / "hq.py"
    if hq_py.exists():
        print("\nhq.py map / doctor:\n")
        try:
            mo = _run([HQ_PYTHON, str(hq_py), "map"], cwd=hq_root)
            print(mo.stdout + mo.stderr)
            do = _run([HQ_PYTHON, str(hq_py), "doctor"], cwd=hq_root)
            print(do.stdout + do.stderr)
            m.note(f"hq doctor exit={do.returncode}: {do.stdout.strip().splitlines()[-1] if do.stdout.strip() else ''}")
        except OSError as e:
            m.note(f"hq.py map/doctor could not run (non-fatal, migration already completed): {e}")
            print(f"  WARN: hq.py map/doctor could not run: {e}")

    print(f"\nmanifest: {m.path}  ({len(m.ops)} ops)")
    return 0


def cmd_rollback(manifest_path: Path) -> int:
    data = json.loads(manifest_path.read_text())
    deferred_worktree_repairs: list[dict] = []
    for op in reversed(data["ops"]):
        kind = op.get("op")
        if kind == "worktree_repair":
            deferred_worktree_repairs.append(op)
        elif kind == "symlink":
            p = Path(op["path"])
            if p.is_symlink():
                p.unlink()
                print(f"  unlinked {p}")
        elif kind == "move":
            src, dst = Path(op["to"]), Path(op["from_"])
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                print(f"  restored {dst}")
        elif kind == "yaml_backup":
            shutil.copy2(op["to"], op["from_"])
            print(f"  restored hq.yaml from {op['to']}")
        elif kind == "plist_backup":
            shutil.copy2(op["to"], op["from_"])
            print(f"  restored plist {op['from_']}")
        elif kind == "push":
            if op.get("ok"):
                print(f"  NOTE: cannot un-push {op.get('path')} branch {op.get('branch')} (+{op.get('ahead')}) — revert on origin by hand if needed")
        # preflight / yaml_edit / plist_edit: informational only, nothing to reverse directly

    # worktrees can only be repointed back once their repo is back at its original
    # path — do that AFTER every "move" above has already been undone.
    for op in deferred_worktree_repairs:
        original_repo = op.get("original_repo")
        wt = op.get("worktree")
        if original_repo and wt:
            r = _run(["git", "-C", original_repo, "worktree", "repair", wt])
            print(f"  worktree repair (rollback) {wt} -> {original_repo}: rc={r.returncode}")

    print("rollback done")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true", help="default: print planned actions, change nothing")
    ap.add_argument("--apply", action="store_true", help="perform the migration for real")
    ap.add_argument("--repoint", action="store_true", help="rewrite this repo's own hardcoded old paths")
    ap.add_argument("--rollback", type=Path, default=None, help="manifest json from a previous --apply")
    a = ap.parse_args(argv)
    if a.rollback:
        return cmd_rollback(a.rollback)
    if a.repoint:
        return cmd_repoint(HQ_ROOT, REPO_ROOT)
    if a.apply:
        return cmd_apply(HQ_ROOT)
    return cmd_plan(HQ_ROOT)


if __name__ == "__main__":
    sys.exit(main())
