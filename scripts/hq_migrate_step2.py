#!/usr/bin/env python3
"""scripts/hq_migrate_step2.py — MoonieX HQ migration step 2 (ADR 0028): move the
LungNote and WarpClip brand umbrellas into ~/MoonieXHQ/Projects/<Brand>/<Suffix>.

Reads every `step: 2` row with a `current` from ~/MoonieXHQ/hq.yaml and, per row:
preflight (status/branch/sha/remote, push if ahead) -> duplicate-clone safety check
-> move -> umbrella leftovers -> hq.yaml update -> manifest. Reversible via
--rollback. Modeled on claude_home_migrate.py's plan/apply/manifest/rollback shape.

  hq_migrate_step2.py                       # --plan (default): prints, touches nothing
  hq_migrate_step2.py --apply               # do it for real
  hq_migrate_step2.py --rollback <manifest.json>

Validation (preflight + push + duplicate-safety check) runs for ALL step-2 rows
BEFORE any move happens. If any row fails validation, the whole run stops before
touching a single file — "nothing half-moved" (hq-filing skill rule 9 / this
task's own instruction). A duplicate clone is "safe" when every local branch's
sha is either an exact match of a live origin branch tip, or an ancestor of one
(already merged/superseded) — checked live via `git ls-remote --heads origin`,
never from possibly-stale local remote-tracking refs.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("hq_migrate_step2.py needs PyYAML — run with /Users/gob/Projects/Agents/.venv/bin/python")

ROOT = Path(__file__).resolve().parent.parent
HQ_ROOT = Path(os.environ.get("HQ_ROOT", "/Users/gob/MoonieXHQ"))
TRASH_ROOT = Path(os.environ.get("TRASH_ROOT", str(Path.home() / ".Trash")))
STATE_DIR = Path(os.environ.get("HQ_STEP2_STATE_DIR", str(ROOT / "state")))
HQ_PYTHON = os.environ.get("HQ_PYTHON", "/Users/gob/Projects/Agents/.venv/bin/python")

EXCLUDE_DIFF = ["node_modules", ".next", ".git", ".obsidian", ".DS_Store"]
UMBRELLA_SKIP_TOP = {".claude"}  # handled specially (stray worktree check)


# ─────────────────────────── git helpers ────────────────────────────────────

def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True)


def git_preflight(path: Path) -> dict:
    dirty = _run(["git", "-C", str(path), "status", "--porcelain"]).stdout
    dirty_count = len([l for l in dirty.splitlines() if l.strip()])
    branch = _run(["git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    sha = _run(["git", "-C", str(path), "rev-parse", "HEAD"]).stdout.strip()
    remotes = _run(["git", "-C", str(path), "remote", "-v"]).stdout.strip()
    up = _run(["git", "-C", str(path), "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"])
    has_upstream = up.returncode == 0
    ahead = behind = 0
    if has_upstream:
        cnt = _run(["git", "-C", str(path), "rev-list", "--left-right", "--count", f"{branch}...{branch}@{{upstream}}"])
        parts = cnt.stdout.split()
        if len(parts) == 2:
            ahead, behind = int(parts[0]), int(parts[1])
    return {
        "path": str(path), "dirty": dirty_count, "branch": branch, "sha": sha,
        "remotes": remotes, "has_upstream": has_upstream, "ahead": ahead, "behind": behind,
    }


def push_current_branch(path: Path) -> tuple[bool, str]:
    r = _run(["git", "-C", str(path), "push"])
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def check_duplicate_safe(dup_path: Path) -> tuple[bool, list[str]]:
    """Every local branch of dup_path must be an exact match of a LIVE origin
    branch tip, or an ancestor of one (already merged). Live = ls-remote, never
    cached remote-tracking refs (those can list branches origin no longer has)."""
    if not dup_path.exists():
        return True, [f"{dup_path}: already gone, nothing to check"]
    local = _run(["git", "-C", str(dup_path), "for-each-ref", "--format=%(refname:short) %(objectname)", "refs/heads"]).stdout.splitlines()
    heads = _run(["git", "-C", str(dup_path), "ls-remote", "--heads", "origin"]).stdout.splitlines()
    origin_shas = {line.split()[0] for line in heads if line.split()}
    notes: list[str] = []
    safe = True
    fetched = False
    for line in local:
        line = line.strip()
        if not line:
            continue
        name, sha = line.rsplit(" ", 1)
        if sha in origin_shas:
            notes.append(f"{name} {sha[:10]}: exact match on origin — safe")
            continue
        if not fetched:
            _run(["git", "-C", str(dup_path), "fetch", "origin", "--quiet"])
            fetched = True
        is_ancestor = any(
            _run(["git", "-C", str(dup_path), "merge-base", "--is-ancestor", sha, osha]).returncode == 0
            for osha in origin_shas
        )
        if is_ancestor:
            notes.append(f"{name} {sha[:10]}: ancestor of a current origin branch — already merged, safe")
        else:
            notes.append(f"{name} {sha[:10]}: MISSING from origin and NOT merged — UNSAFE, unpushed work")
            safe = False
    return safe, notes


def move_and_verify(src: Path, dst: Path, expected_sha: str, expected_remotes: str) -> None:
    if dst.exists():
        raise RuntimeError(f"move target already exists: {dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    st = _run(["git", "-C", str(dst), "status"])
    if st.returncode != 0:
        raise RuntimeError(f"git status failed after move of {src} -> {dst}: {st.stdout}{st.stderr}")
    sha_after = _run(["git", "-C", str(dst), "rev-parse", "HEAD"]).stdout.strip()
    if sha_after != expected_sha:
        raise RuntimeError(f"HEAD sha changed after move of {dst}: before={expected_sha} after={sha_after}")
    remotes_after = _run(["git", "-C", str(dst), "remote", "-v"]).stdout.strip()
    if remotes_after != expected_remotes:
        raise RuntimeError(f"remotes changed after move of {dst}: before={expected_remotes!r} after={remotes_after!r}")


def trash(path: Path, ts: str, subdir: str = "") -> Path:
    dest = TRASH_ROOT / f"hq-step2-{ts}" / subdir / path.name if subdir else TRASH_ROOT / f"hq-step2-{ts}" / path.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(dest))
    return dest


# ─────────────────────────── manifest ────────────────────────────────────────

class Manifest:
    def __init__(self, ts: str):
        self.ts = ts
        self.path = STATE_DIR / f"hq-step2-migration-{ts}.json"
        self.ops: list[dict] = []
        self.notes: list[str] = []

    def add(self, **op) -> None:
        self.ops.append(op)
        self._flush()

    def note(self, msg: str) -> None:
        self.notes.append(msg)
        print(f"  {msg}")
        self._flush()

    def _flush(self) -> None:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"ts": self.ts, "hq_root": str(HQ_ROOT), "ops": self.ops, "notes": self.notes}, indent=2))


# ─────────────────────────── diff / umbrella leftovers ──────────────────────

def _dir_diff(a: Path, b: Path) -> list[str]:
    if not a.exists() or not b.exists():
        return [f"{a if not a.exists() else b} does not exist"]
    cmd = ["diff", "-rq"] + [f"--exclude={e}" for e in EXCLUDE_DIFF] + [str(a), str(b)]
    r = _run(cmd)
    return [l for l in r.stdout.splitlines() if l.strip()]


def handle_umbrella_leftovers(umbrella_dir: Path, moved: dict[str, Path], target_brand_dir: Path, ts: str, m: Manifest) -> tuple[bool, list[str]]:
    """moved: {row_subdir_name -> new absolute Path}, e.g. {'webapp': .../Webapp}.
    Returns (fully_emptied, blockers)."""
    blockers: list[str] = []
    if not umbrella_dir.is_dir():
        return True, blockers

    stray_root = umbrella_dir / ".claude" / "worktrees"
    if stray_root.is_dir():
        for wt in sorted(stray_root.iterdir()):
            if not wt.is_dir():
                continue
            if _run(["git", "-C", str(wt), "status"]).returncode == 0:
                msg = f"{wt}: a real git worktree, not a stray copy — leave for normal worktree GC"
                blockers.append(msg)
                m.note(f"BLOCKER: {msg}")
                continue
            diffs: list[str] = []
            for sub in sorted(wt.iterdir()):
                if not sub.is_dir() or sub.name not in moved:
                    continue
                target = moved[sub.name]
                cmp_a = sub / "src" if (sub / "src").is_dir() and (target / "src").is_dir() else sub
                cmp_b = target / "src" if cmp_a.name == "src" else target
                diffs.extend(_dir_diff(cmp_a, cmp_b))
            if diffs:
                msg = f"{wt}: differs from the moved repo(s) in {len(diffs)} line(s) — CTO decides (sample: {diffs[:5]})"
                blockers.append(msg)
                m.note(f"BLOCKER: {msg}")
            else:
                dest = trash(wt, ts, subdir=umbrella_dir.name.replace(" ", "-"))
                m.add(op="move", from_=str(wt), to=str(dest))
                m.note(f"stray worktree identical to moved repos — trashed: {wt} -> {dest}")
        remaining = list(stray_root.iterdir()) if stray_root.is_dir() else []
        if not remaining and stray_root.is_dir():
            stray_root.rmdir()
        claude_dir = umbrella_dir / ".claude"
        if claude_dir.is_dir() and not any(claude_dir.iterdir()):
            claude_dir.rmdir()

    for entry in sorted(umbrella_dir.iterdir()) if umbrella_dir.is_dir() else []:
        if entry.name in UMBRELLA_SKIP_TOP or entry.name in moved:
            continue
        dest = trash(entry, ts, subdir=umbrella_dir.name.replace(" ", "-"))
        m.add(op="move", from_=str(entry), to=str(dest))
        m.note(f"umbrella leftover trashed: {entry} -> {dest}")

    if umbrella_dir.is_dir() and any(umbrella_dir.iterdir()):
        msg = f"{umbrella_dir}: not empty after cleanup — symlink skipped"
        blockers.append(msg)
        m.note(f"BLOCKER: {msg}")
        return False, blockers

    if umbrella_dir.is_dir():
        umbrella_dir.rmdir()
    target_brand_dir.mkdir(parents=True, exist_ok=True)
    os.symlink(str(target_brand_dir), str(umbrella_dir))
    m.add(op="symlink", path=str(umbrella_dir), target=str(target_brand_dir))
    m.note(f"compat symlink: {umbrella_dir} -> {target_brand_dir}")
    return True, blockers


# ─────────────────────────── hq.yaml textual edit ────────────────────────────

def patch_yaml_row(lines: list[str], row_path: str, new_current: str | None, drop_duplicates: bool) -> list[str]:
    out: list[str] = []
    i, n = 0, len(lines)
    marker = f"- path: {row_path}"
    found = False
    while i < n:
        line = lines[i]
        if line.strip() == marker:
            found = True
            out.append(line)
            base_indent = len(line) - len(line.lstrip(" "))
            i += 1
            while i < n:
                l2 = lines[i]
                stripped = l2.strip()
                cur_indent = len(l2) - len(l2.lstrip(" "))
                if stripped.startswith("- path:") and cur_indent <= base_indent:
                    break
                if stripped and cur_indent < base_indent:
                    break
                if new_current is not None and stripped.startswith("current:"):
                    indent = l2[: len(l2) - len(l2.lstrip(" "))]
                    out.append(f"{indent}current: {new_current}\n")
                    i += 1
                    continue
                if drop_duplicates and stripped.startswith("duplicates:"):
                    i += 1
                    continue
                out.append(l2)
                i += 1
            continue
        out.append(line)
        i += 1
    if not found:
        raise ValueError(f"row not found in hq.yaml: {row_path}")
    return out


def append_dropped(lines: list[str], entries: list[dict]) -> list[str]:
    if not entries:
        return lines
    out: list[str] = []
    inserted = False
    for line in lines:
        out.append(line)
        if not inserted and line.startswith("dropped:"):
            for e in entries:
                out.append(f'  - {{current: "{e["current"]}", why: {e["why"]}}}\n')
            inserted = True
    if not inserted:
        out.append("dropped:\n")
        for e in entries:
            out.append(f'  - {{current: "{e["current"]}", why: {e["why"]}}}\n')
    return out


# ─────────────────────────── plan / apply ────────────────────────────────────

def step2_rows(hq_yaml: Path) -> list[dict]:
    data = yaml.safe_load(hq_yaml.read_text(encoding="utf-8"))
    return [r for r in data["folders"] if r.get("step") == 2 and r.get("current")]


def brand_of(row_path: str) -> str:
    parts = row_path.split("/")
    return parts[1] if len(parts) > 1 else parts[0]


def cmd_plan(hq_root: Path) -> int:
    hq_yaml = hq_root / "hq.yaml"
    rows = step2_rows(hq_yaml)
    print(f"PLAN — {len(rows)} step-2 row(s), nothing will change:\n")
    for r in rows:
        target = hq_root / r["path"]
        info = git_preflight(Path(r["current"]))
        push_note = f"  PUSH NEEDED: branch {info['branch']} ahead {info['ahead']}" if info["ahead"] else ""
        print(f"  MOVE  {r['current']}  ->  {target}   [{info['branch']} @ {info['sha'][:10]}, dirty={info['dirty']}]{push_note}")
        for d in r.get("duplicates", []) or []:
            safe, notes = check_duplicate_safe(Path(d))
            tag = "TRASH (safe)" if safe else "STOP (unsafe)"
            print(f"    DUP {tag}: {d}")
            for note in notes:
                print(f"      - {note}")
    print("\nplan only — no filesystem or yaml changes made.")
    return 0


def cmd_apply(hq_root: Path) -> int:
    hq_yaml = hq_root / "hq.yaml"
    rows = step2_rows(hq_yaml)
    ts = time.strftime("%Y%m%dT%H%M%S")
    m = Manifest(ts)

    # ---- Phase A: validate everything, push ahead branches. No moves yet. ----
    print("Phase A — preflight, push, duplicate-safety check (no moves yet)\n")
    problems: list[str] = []
    preflights: dict[str, dict] = {}
    for r in rows:
        src = Path(r["current"])
        info = git_preflight(src)
        preflights[r["path"]] = info
        m.add(op="preflight", row=r["path"], **{k: v for k, v in info.items() if k != "remotes"})
        print(f"  {r['path']}: branch={info['branch']} sha={info['sha'][:10]} dirty={info['dirty']} ahead={info['ahead']}")
        if info["ahead"] > 0:
            if not info["has_upstream"]:
                problems.append(f"{r['path']}: branch {info['branch']} reports ahead but has no upstream — inconsistent, refusing to push")
                continue
            ok, out = push_current_branch(src)
            m.add(op="push", row=r["path"], path=str(src), branch=info["branch"], ahead=info["ahead"], ok=ok, output=out)
            if not ok:
                problems.append(f"{r['path']}: git push failed for branch {info['branch']}: {out}")
                continue
            m.note(f"pushed {src} branch {info['branch']} (+{info['ahead']})")
        for d in r.get("duplicates", []) or []:
            safe, notes = check_duplicate_safe(Path(d))
            print(f"    dup {d}: {'safe' if safe else 'UNSAFE'}")
            for note in notes:
                print(f"      - {note}")
            if not safe:
                problems.append(f"{r['path']} duplicate {d}: has branch(es) not on origin and not merged — {notes}")

    if problems:
        print("\nSTOP — validation failed, nothing moved:\n")
        for p in problems:
            print(f"  ✗ {p}")
        m.note("APPLY STOPPED at Phase A validation — no repo moved, no duplicate trashed, hq.yaml untouched")
        for p in problems:
            m.note(f"BLOCKER: {p}")
        print(f"\nmanifest (pushes made so far, if any): {m.path}")
        return 1

    print("\nPhase A clean. Phase B — trashing duplicates, moving repos\n")

    # ---- Phase B: duplicates + moves ----
    moved_rows: list[dict] = []
    for r in rows:
        for d in r.get("duplicates", []) or []:
            dp = Path(d)
            if dp.exists():
                dest = trash(dp, ts)
                m.add(op="move", from_=str(dp), to=str(dest))
                m.note(f"duplicate trashed: {dp} -> {dest}")
        src = Path(r["current"])
        target = hq_root / r["path"]
        info = preflights[r["path"]]
        move_and_verify(src, target, info["sha"], info["remotes"])
        m.add(op="move", from_=str(src), to=str(target), sha=info["sha"])
        m.note(f"moved: {src} -> {target}")
        r["_target"] = target
        r["_orig_current"] = r["current"]
        moved_rows.append(r)

    # ---- Phase C: umbrella leftovers, per brand, only if every row of that brand moved ----
    print("\nPhase C — umbrella leftovers\n")
    by_brand: dict[str, list[dict]] = {}
    for r in rows:
        by_brand.setdefault(brand_of(r["path"]), []).append(r)
    dropped_entries: list[dict] = []
    all_blockers: list[str] = []
    for brand, brand_rows in by_brand.items():
        if not all(r in moved_rows for r in brand_rows):
            all_blockers.append(f"{brand}: not all rows moved this run — umbrella leftovers left untouched")
            continue
        umbrella_dir = Path(brand_rows[0]["_orig_current"]).parent
        moved_map = {Path(r["_orig_current"]).name: r["_target"] for r in brand_rows}
        target_brand_dir = hq_root / "Projects" / brand
        ok, blockers = handle_umbrella_leftovers(umbrella_dir, moved_map, target_brand_dir, ts, m)
        all_blockers.extend(blockers)

    # ---- Phase D: hq.yaml update ----
    print("\nPhase D — hq.yaml update\n")
    backup = STATE_DIR / f"hq-step2-yaml-backup-{ts}.yaml"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(hq_yaml, backup)
    m.add(op="yaml_backup", from_=str(hq_yaml), to=str(backup))
    lines = hq_yaml.read_text(encoding="utf-8").splitlines(keepends=True)
    for r in moved_rows:
        lines = patch_yaml_row(lines, r["path"], str(r["_target"]), drop_duplicates=bool(r.get("duplicates")))
        dropped_entries.append({"current": r["_orig_current"], "why": f"moved to {r['_target']} (HQ step 2)"})
    lines = append_dropped(lines, dropped_entries)
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

    if all_blockers:
        print("\nBlockers left for the CTO:")
        for b in all_blockers:
            print(f"  ! {b}")

    print(f"\nmanifest: {m.path}  ({len(m.ops)} ops)")
    return 0


def cmd_rollback(manifest_path: Path) -> int:
    data = json.loads(manifest_path.read_text())
    for op in reversed(data["ops"]):
        kind = op.get("op")
        if kind == "symlink":
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
        elif kind == "push":
            if op.get("ok"):
                print(f"  NOTE: cannot un-push {op.get('path')} branch {op.get('branch')} (+{op.get('ahead')}) — revert on origin by hand if needed")
        # preflight / yaml_edit: informational only, nothing to reverse
    print("rollback done")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true", help="default: print planned actions, change nothing")
    ap.add_argument("--apply", action="store_true", help="perform the migration for real")
    ap.add_argument("--rollback", type=Path, default=None, help="manifest json from a previous --apply")
    a = ap.parse_args(argv)
    if a.rollback:
        return cmd_rollback(a.rollback)
    if a.apply:
        return cmd_apply(HQ_ROOT)
    return cmd_plan(HQ_ROOT)


if __name__ == "__main__":
    sys.exit(main())
