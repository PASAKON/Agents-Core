#!/usr/bin/env python3
"""scripts/hq_migrate_step4a.py — MoonieX HQ migration step 4a (ADR 0028): move
everything under ~/Projects EXCEPT Agents/ (Agents-Core, the runtime itself —
that is step 4b, later, with its own rehearsal) into ~/MoonieXHQ.

What moves, in one --apply:
  1. Four `step: 4` rows of hq.yaml (Agents/Rules, Agents/Wikis, Agents/Memory,
     Agents/Skills — NOT Agents/Core, which this script never touches):
     /Users/gob/Projects/{Agents-Wikis,LLMs,Agents-Memory,mooniex-claude-skills}
     -> ~/MoonieXHQ/Agents/{Rules,Wikis,Memory,Skills}, each getting a compat
     symlink at its old path immediately after the move.
  2. The 7 clones under /Users/gob/Projects/external/* (the `External` row's
     items whose `current` sits there) -> ~/MoonieXHQ/External/<same name>.
     Unlike (1), these get ONE compat symlink for the whole directory
     (/Users/gob/Projects/external -> ~/MoonieXHQ/External), not one per clone —
     a symlink that points INTO a moved repo (the ~/.claude/skills/* links, and
     `paperclip` below) resolves fine through it (hq-filing field note,
     2026-09-23, task-b5f61b47).
  3. `paperclip` (nested inside mooniex-nohuman as its own git clone, gitignored
     by the parent) -> ~/MoonieXHQ/External/paperclip. No compat symlink: its
     old parent directory is being deleted (2), not kept as a symlink.
  4. The rest of mooniex-nohuman: brand/ is verified byte-identical to a FRESH
     `git clone --depth 1` of its own GitHub origin (never trusting the local
     .git alone) before the whole directory is trashed to
     ~/.Trash/hq-step4a-<ts>/ (never `rm`). Any diff -> that one op is skipped
     (recorded as a blocker) and everything else still proceeds.
  5. mooniex-school (3 loose PDF/PPTX files, not a repo) ->
     ~/MoonieXHQ/UNKNOWN/mooniex-school.

Beyond the move itself: `--repoint` rewrites every file this task's own grep
found naming an old path (config/wikis.yaml, the CLAUDE.md wiki table +
Contabo rsync lines, the settings.json SessionStart hook, the office-*.mjs /
mooniex-coord CWD-detection hooks, hook-research-gate.py, research-file.py,
their tests, claude_home_migrate.py's one-time typo-fix) plus
claude-home/skills.txt (uses a $PROJECTS macro the grep's absolute-path regex
can't see, so it is handled separately — target rewritten to a literal
/Users/gob/MoonieXHQ/... path per this task's own instruction, so
scripts/install-claude-home.sh's expand() needs no $HQ addition).

`tools/memory_sync.py` has no hardcoded path to edit — `default_memory_dir()`
computes `~/.claude/projects/<slug>/memory` and reads whatever that symlink
points at via `os.readlink`, so repointing the live symlink IS its new
default; `--apply` does that (best-effort — a PermissionError under ~/.claude
is recorded as a blocker, never fatal to the rest of the run).

Reuses hq_migrate_step2 / hq_migrate_step3 primitives by import (preflight,
push, move+verify, Manifest, patch_yaml_row, worktree repair, compat
symlinks, structured-file validation) rather than re-implementing them.

  hq_migrate_step4a.py                       # --plan (default): prints, touches nothing
  hq_migrate_step4a.py --apply               # do it for real
  hq_migrate_step4a.py --repoint             # rewrite this repo's own hardcoded old paths
  hq_migrate_step4a.py --rollback <manifest.json>

Validation (preflight + push for the 4 owned repos) runs BEFORE any move,
same "nothing half-moved" guarantee as step 2/3. Every unit of work
(a repo, an external clone, paperclip, mooniex-school) is independently
resumable: if its old path already resolves to its target (directly, or
transitively through a parent compat symlink from a prior partial run), it is
skipped, not re-attempted or treated as an error.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("hq_migrate_step4a.py needs PyYAML — run with /Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hq_migrate_step2 import (  # noqa: E402  (reuse, do not copy — task instruction)
    TRASH_ROOT,
    Manifest,
    _run,
    git_preflight,
    move_and_verify,
    patch_yaml_row,
    push_current_branch,
)
from hq_migrate_step3 import (  # noqa: E402  (reuse, do not copy — task instruction)
    _validate_structured,
    append_compat_links,
    create_compat_symlink,
    list_attached_worktrees,
    repair_worktree,
)

ROOT = Path(__file__).resolve().parent.parent
HQ_ROOT = Path(os.environ.get("HQ_ROOT", "/Users/gob/MoonieXHQ"))
STATE_DIR = Path(os.environ.get("HQ_STEP4A_STATE_DIR", str(ROOT / "state")))
HQ_PYTHON = os.environ.get("HQ_PYTHON", "/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python")
REPO_ROOT = Path(os.environ.get("HQ_STEP4A_REPO_ROOT", str(ROOT)))
MEMORY_LINK = Path(os.environ.get(
    "HQ_STEP4A_MEMORY_LINK",
    str(Path.home() / ".claude" / "projects" / "-Users-gob-Projects-Agents" / "memory"),
))

STEP4A_EXCLUDE_ROW_PATHS = {"Agents/Core"}  # step 4b, later, with its own rehearsal — never touched here
EXTERNAL_DIR_DEFAULT = os.environ.get("HQ_STEP4A_EXTERNAL_DIR", "/Users/gob/Projects/external")
REMOVE_AT_STEP = 5  # this task's instruction (step 2/3 used 4; Agents/Core is the last step)

DOC_EXCLUDE_PATHSPECS = [":!docs/reports", ":!docs/briefs", ":!docs/ops"]  # *.md IS in scope this step


# ─────────────────────────── rows (every `step: 4` row EXCEPT Agents/Core) ───

def step4a_rows(hq_yaml: Path) -> list[dict]:
    data = yaml.safe_load(hq_yaml.read_text(encoding="utf-8"))
    return [r for r in data["folders"]
            if r.get("step") == 4 and r.get("current") and r["path"] not in STEP4A_EXCLUDE_ROW_PATHS]


def load_yaml(hq_yaml: Path) -> dict:
    return yaml.safe_load(hq_yaml.read_text(encoding="utf-8"))


def find_row(data: dict, path: str) -> dict:
    for r in data["folders"]:
        if r["path"] == path:
            return r
    raise ValueError(f"row not found: {path}")


def external_clone_items(external_row: dict, external_dir: str = EXTERNAL_DIR_DEFAULT) -> list[dict]:
    prefix = external_dir.rstrip("/") + "/"
    return [it for it in external_row.get("items", []) or []
            if it.get("current") and str(it["current"]).startswith(prefix)]


def find_item(row: dict, name: str) -> dict | None:
    for it in row.get("items", []) or []:
        if it.get("name") == name:
            return it
    return None


# ─────────────────────────── generic move for non-"own-repo" units ──────────

def already_migrated(old: Path, new: Path) -> bool:
    """True when this unit of work is already done — either `old` (directly,
    or transitively through an already-created parent compat symlink)
    resolves to `new`, or `old` is simply gone and `new` already holds the
    content (an external clone, paperclip or mooniex-school: no per-item
    compat symlink is ever created for these, only their SHARED parent
    eventually becomes one — so between "this clone moved" and "the parent
    became a symlink" the old per-item path is just absent, not a symlink)."""
    if old.exists() or old.is_symlink():
        return old.resolve() == new.resolve()
    return new.exists()


def move_verified(src: Path, dst: Path) -> None:
    """Move a directory, verifying git HEAD is unchanged when `src` is a git
    repo. Unlike hq_migrate_step2.move_and_verify this does not require a
    remote (External clones are read-only pinned checkouts; some — arb-refs,
    mooniex-school — have no .git at all)."""
    if dst.exists():
        raise RuntimeError(f"move target already exists: {dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    is_git = (src / ".git").exists()
    sha_before = _run(["git", "-C", str(src), "rev-parse", "HEAD"]).stdout.strip() if is_git else None
    shutil.move(str(src), str(dst))
    if is_git:
        sha_after = _run(["git", "-C", str(dst), "rev-parse", "HEAD"]).stdout.strip()
        if sha_after != sha_before:
            raise RuntimeError(f"HEAD sha changed after move of {dst}: before={sha_before} after={sha_after}")


def trash4a(path: Path, ts: str) -> Path:
    dest = TRASH_ROOT / f"hq-step4a-{ts}" / path.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(dest))
    return dest


# ─────────────────────────── nohuman brand/ verification ────────────────────

def verify_nohuman_brand(nohuman_path: Path) -> tuple[bool, list[str]]:
    """brand/ must match a FRESH clone of the repo's own GitHub origin —
    never trust the local .git alone (this task's own instruction)."""
    origin = _run(["git", "-C", str(nohuman_path), "remote", "get-url", "origin"]).stdout.strip()
    if not origin:
        return False, ["no origin remote configured — cannot verify against GitHub HEAD"]
    scratch = Path(tempfile.mkdtemp(prefix="hq-step4a-nohuman-verify-"))
    try:
        clone_dir = scratch / "clone"
        r = _run(["git", "clone", "--depth", "1", origin, str(clone_dir)])
        if r.returncode != 0:
            return False, [f"git clone of {origin} failed: {(r.stdout + r.stderr).strip()}"]
        d = _run(["diff", "-rq", "--exclude=.git", str(clone_dir / "brand"), str(nohuman_path / "brand")])
        diffs = [l for l in d.stdout.splitlines() if l.strip()]
        return (len(diffs) == 0), diffs
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# ─────────────────────────── hq.yaml item-field edits ────────────────────────

def patch_item_field(lines: list[str], name_marker: str, old: str, new: str) -> list[str]:
    """Rewrite `old` -> `new` on the single flow-style item line carrying
    `name: <name_marker>,` (every items: entry in hq.yaml is one physical
    line). Raises if the item or the old value isn't found — a silent no-op
    here would leave hq.yaml pointing at a path that no longer exists."""
    marker = f"name: {name_marker},"
    out: list[str] = []
    found = False
    for line in lines:
        if marker in line and old in line:
            line = line.replace(old, new)
            found = True
        out.append(line)
    if not found:
        raise ValueError(f"item line not found or missing {old!r}: name={name_marker}")
    return out


def patch_nohuman_archive(lines: list[str], ts: str) -> list[str]:
    marker = "name: NoHumanCompany,"
    out: list[str] = []
    found = False
    for line in lines:
        if marker in line:
            indent = line[: len(line) - len(line.lstrip(" "))]
            action = (
                f"deleted local {ts} — brand/ diff-verified clean against a fresh clone of "
                f"origin HEAD, paperclip moved to External/paperclip first, trashed to "
                f"~/.Trash/hq-step4a-{ts}/"
            )
            out.append(
                f'{indent}- {{name: NoHumanCompany, repo: PASAKON/MoonieX-NoHumanCompany, '
                f'current: null, action: "{action}", status: retired}}\n'
            )
            found = True
        else:
            out.append(line)
    if not found:
        raise ValueError("NoHumanCompany archive item not found")
    return out


# ─────────────────────────── repoint: this repo's own hardcoded paths ────────

def build_code_repoint_mapping(hq_root: Path, data: dict) -> dict[str, str]:
    """old absolute path -> new HQ path, for every category this task's grep
    can see (literal `/Users/gob/[Pp]rojects/...` text). A parent-directory
    key (External) also fixes any nested reference beneath it, since the new
    tree mirrors the old one path-segment for path-segment."""
    rows = {r["path"]: r for r in data["folders"]
            if r.get("step") == 4 and r.get("current") and r["path"] not in STEP4A_EXCLUDE_ROW_PATHS}
    m: dict[str, str] = {}
    for path, r in rows.items():
        m[r["current"]] = str(hq_root / path)
    m[EXTERNAL_DIR_DEFAULT] = str(hq_root / "External")
    m[EXTERNAL_DIR_DEFAULT.replace("Projects", "projects")] = str(hq_root / "External")  # lowercase Desk-pattern typo, same target
    ext_row = find_row(data, "External")
    pc = find_item(ext_row, "paperclip")
    if pc and pc.get("current"):
        m[pc["current"]] = str(hq_root / "External" / "paperclip")
    unk = find_row(data, "UNKNOWN")
    school = find_item(unk, "mooniex-school")
    if school and school.get("current"):
        m[school["current"]] = str(hq_root / "UNKNOWN" / "mooniex-school")
    # the one lowercase Desk-pattern typo this task's grep also catches (case-insensitive on "projects")
    llms = rows.get("Agents/Wikis")
    if llms:
        m[llms["current"].replace("Projects", "projects")] = str(hq_root / "Agents" / "Wikis")
    return m


def find_repoint_files(repo_root: Path, mapping: dict[str, str]) -> list[str]:
    if not mapping:
        return []
    import re
    pattern = "(" + "|".join(re.escape(k) for k in mapping) + ")"
    r = _run(["git", "grep", "-I", "-l", "-E", pattern, "--", ".", *DOC_EXCLUDE_PATHSPECS], cwd=repo_root)
    return [l for l in r.stdout.splitlines() if l.strip()]


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


def rewrite_skills_txt(skills_txt: Path, mapping: dict[str, str]) -> list[str]:
    """claude-home/skills.txt targets use a `$PROJECTS` macro the code-repoint
    grep can't see. Rewritten to a literal /Users/gob/MoonieXHQ/... absolute
    path (this task's own instruction), so install-claude-home.sh's expand()
    needs no new $HQ macro."""
    if not skills_txt.exists():
        return []
    lines = skills_txt.read_text().splitlines(keepends=True)
    changed: list[str] = []
    out: list[str] = []
    for line in lines:
        stripped = line.rstrip("\n")
        if not stripped or stripped.startswith("#") or "\t" not in stripped:
            out.append(line)
            continue
        name, target = stripped.split("\t", 1)
        expanded = target.replace("$PROJECTS", "/Users/gob/Projects")
        new_target = expanded
        for old, new in mapping.items():
            if expanded == old or expanded.startswith(old + "/"):
                new_target = new + expanded[len(old):]
                break
        if new_target != expanded:
            out.append(f"{name}\t{new_target}\n")
            changed.append(name)
        else:
            out.append(line)
    skills_txt.write_text("".join(out))
    return changed


def skills_txt_mapping(hq_root: Path) -> dict[str, str]:
    return {
        EXTERNAL_DIR_DEFAULT: str(hq_root / "External"),
        "/Users/gob/Projects/mooniex-claude-skills": str(hq_root / "Agents" / "Skills"),
    }


def cmd_repoint(hq_root: Path, repo_root: Path) -> int:
    data = load_yaml(hq_root / "hq.yaml")
    mapping = build_code_repoint_mapping(hq_root, data)
    changed = rewrite_repoint_files(repo_root, mapping)
    print(f"repoint — {len(changed)} code file(s) rewritten:")
    for c in changed:
        print(f"  {c}")
    skills_changed = rewrite_skills_txt(repo_root / "claude-home" / "skills.txt", skills_txt_mapping(hq_root))
    print(f"repoint — {len(skills_changed)} claude-home/skills.txt row(s) rewritten: {', '.join(skills_changed)}")
    clean = repoint_files_clean(repo_root, mapping)
    print("repoint: grep-clean" if clean else "repoint: STILL matches old paths — check")
    return 0 if clean else 1


# ─────────────────────────── memory symlink repoint ──────────────────────────

def repoint_memory_symlink(link: Path, new_target: Path, m: Manifest) -> str:
    """Best-effort — never fatal. Returns 'ok' | 'already' | 'not-a-symlink' | 'denied:<msg>'."""
    try:
        if not link.is_symlink():
            m.note(f"memory symlink repoint skipped — not a symlink: {link}")
            return "not-a-symlink"
        old_target = os.readlink(link)
        if old_target == str(new_target):
            m.note(f"memory symlink already points at {new_target}")
            return "already"
        link.unlink()
        os.symlink(str(new_target), str(link))
        m.add(op="memory_symlink_repoint", path=str(link), old_target=old_target, new_target=str(new_target))
        m.note(f"memory symlink repointed: {link} -> {new_target} (was {old_target})")
        return "ok"
    except PermissionError as e:
        m.note(f"BLOCKER: memory symlink repoint denied by the auto-mode classifier: {link}: {e}")
        return f"denied:{e}"


# ─────────────────────────── plan ─────────────────────────────────────────────

def cmd_plan(hq_root: Path) -> int:
    hq_yaml = hq_root / "hq.yaml"
    data = load_yaml(hq_yaml)
    rows = step4a_rows(hq_yaml)
    print(f"PLAN — {len(rows)} owned repo row(s), 7 external clone(s), paperclip, nohuman, mooniex-school:\n")
    for r in rows:
        target = hq_root / r["path"]
        src = Path(r["current"])
        if already_migrated(src, target):
            print(f"  ALREADY MIGRATED  {src}  ->  {target}")
            continue
        info = git_preflight(src)
        push_note = f"  PUSH NEEDED: branch {info['branch']} ahead {info['ahead']}" if (info["ahead"] and info["has_upstream"]) else ("  NOT PUSHED: no upstream" if not info["has_upstream"] else "")
        print(f"  MOVE  {src}  ->  {target}   [{info['branch']} @ {info['sha'][:10]}, dirty={info['dirty']}]{push_note}")
        for wt in list_attached_worktrees(src):
            print(f"    WORKTREE (will repair): {wt}")

    ext_row = find_row(data, "External")
    print(f"\n  external clones -> {hq_root / 'External'}:")
    for it in external_clone_items(ext_row):
        old = Path(it["current"])
        new = hq_root / "External" / it["name"]
        tag = "ALREADY MIGRATED" if already_migrated(old, new) else "MOVE"
        print(f"    {tag}  {old}  ->  {new}")
    print(f"    then ONE compat symlink: {EXTERNAL_DIR_DEFAULT}  ->  {hq_root / 'External'}")

    pc = find_item(ext_row, "paperclip")
    if pc:
        old = Path(pc["current"])
        new = hq_root / "External" / "paperclip"
        tag = "ALREADY MIGRATED" if already_migrated(old, new) else "MOVE"
        print(f"\n  {tag}  {old}  ->  {new}")

    nh_item = find_item(find_row(data, "Archive"), "NoHumanCompany")
    if nh_item and nh_item.get("current"):
        nh_path = Path(nh_item["current"])
        if nh_path.exists():
            clean, diffs = verify_nohuman_brand(nh_path)
            print(f"\n  NOHUMAN  {nh_path}  -> trash  [brand/ diff vs origin HEAD: {'clean' if clean else f'{len(diffs)} difference(s) — STOP'}]")
        else:
            print(f"\n  ALREADY TRASHED  {nh_path}")

    school = find_item(find_row(data, "UNKNOWN"), "mooniex-school")
    if school and school.get("current"):
        old = Path(school["current"])
        new = hq_root / "UNKNOWN" / "mooniex-school"
        tag = "ALREADY MIGRATED" if already_migrated(old, new) else "MOVE"
        print(f"\n  {tag}  {old}  ->  {new}")

    print("\nplan only — no filesystem or yaml changes made.")
    return 0


# ─────────────────────────── apply ────────────────────────────────────────────

def cmd_apply(hq_root: Path) -> int:
    hq_yaml = hq_root / "hq.yaml"
    data = load_yaml(hq_yaml)
    rows = step4a_rows(hq_yaml)
    ts = time.strftime("%Y%m%dT%H%M%S")
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    m = Manifest(ts)
    m.path = STATE_DIR / f"hq-step4a-migration-{ts}.json"

    # ---- Phase A: preflight + push the 4 owned repos. No moves yet. ----
    print("Phase A — preflight, push the 4 owned repos (no moves yet)\n")
    problems: list[str] = []
    preflights: dict[str, dict] = {}
    worktrees: dict[str, list[str]] = {}
    already_done_rows: set[str] = set()
    for r in rows:
        src = Path(r["current"])
        target = hq_root / r["path"]
        if already_migrated(src, target):
            already_done_rows.add(r["path"])
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

    print("\nPhase A clean. Phase B — moving repos, external clones, paperclip, nohuman, mooniex-school\n")

    # ---- Phase B1: the 4 owned repos — move, repair worktrees, symlink immediately ----
    moved_rows: list[dict] = []
    for r in rows:
        src = Path(r["current"])
        target = hq_root / r["path"]
        if r["path"] not in already_done_rows:
            info = preflights[r["path"]]
            move_and_verify(src, target, info["sha"], info["remotes"])
            m.add(op="move", from_=str(src), to=str(target), sha=info["sha"])
            m.note(f"moved: {src} -> {target}")
            create_compat_symlink(src, target)  # immediately after mv (hq-filing field note)
            m.add(op="symlink", path=str(src), target=str(target))
            m.note(f"compat symlink: {src} -> {target}")
            for wt in worktrees[r["path"]]:
                repair_worktree(target, Path(wt))
                m.add(op="worktree_repair", row=r["path"], worktree=wt, target=str(target), original_repo=str(src))
                m.note(f"worktree repaired: {wt} -> {target}")
        r["_target"] = target
        r["_orig_current"] = r["current"]
        moved_rows.append(r)

    # ---- Phase B2: external clones (own moves, no per-clone symlink), then ONE symlink ----
    ext_row = find_row(data, "External")
    ext_items = external_clone_items(ext_row)
    ext_new_current: dict[str, str] = {}
    external_dir = Path(EXTERNAL_DIR_DEFAULT)
    for it in ext_items:
        old = Path(it["current"])
        new = hq_root / "External" / it["name"]
        if already_migrated(old, new):
            m.note(f"external clone already migrated, skipping: {it['name']}")
        else:
            move_verified(old, new)
            m.add(op="move", from_=str(old), to=str(new))
            m.note(f"external clone moved: {old} -> {new}")
        ext_new_current[it["name"]] = str(new)

    if external_dir.is_symlink():
        m.note(f"external compat symlink already in place: {external_dir}")
    elif external_dir.is_dir():
        leftovers = sorted(p.name for p in external_dir.iterdir())
        if leftovers:
            m.note(f"BLOCKER: {external_dir} not empty after moving clones — leftovers: {leftovers} — symlink skipped")
        else:
            external_dir.rmdir()
            create_compat_symlink(external_dir, hq_root / "External")
            m.add(op="symlink", path=str(external_dir), target=str(hq_root / "External"))
            m.note(f"compat symlink: {external_dir} -> {hq_root / 'External'}")
    elif not external_dir.exists():
        m.note(f"{external_dir} already gone — nothing to symlink (a prior run finished this)")

    # ---- Phase B3: paperclip ----
    pc = find_item(ext_row, "paperclip")
    pc_new_current = None
    if pc and pc.get("current"):
        old = Path(pc["current"])
        new = hq_root / "External" / "paperclip"
        if already_migrated(old, new):
            m.note("paperclip already migrated, skipping")
        elif old.exists():
            move_verified(old, new)
            m.add(op="move", from_=str(old), to=str(new))
            m.note(f"paperclip moved: {old} -> {new}")
        pc_new_current = str(new)

    # ---- Phase B4: mooniex-nohuman — verify brand/, then trash (never rm) ----
    nh_item = find_item(find_row(data, "Archive"), "NoHumanCompany")
    nohuman_trashed = False
    nohuman_blocked: str | None = None
    if nh_item and nh_item.get("current"):
        nh_path = Path(nh_item["current"])
        if not nh_path.exists():
            m.note(f"mooniex-nohuman already trashed, skipping: {nh_path}")
            nohuman_trashed = True  # already done in a prior run
        else:
            clean, diffs = verify_nohuman_brand(nh_path)
            m.add(op="nohuman_brand_verify", path=str(nh_path), clean=clean, diff_sample=diffs[:10])
            if not clean:
                nohuman_blocked = f"brand/ differs from origin HEAD in {len(diffs)} line(s) — NOT trashed: {diffs[:5]}"
                m.note(f"BLOCKER: {nohuman_blocked}")
            else:
                dest = trash4a(nh_path, ts)
                m.add(op="trash", from_=str(nh_path), to=str(dest))
                m.note(f"mooniex-nohuman trashed (brand/ verified clean): {nh_path} -> {dest}")
                nohuman_trashed = True

    # ---- Phase B5: mooniex-school ----
    school = find_item(find_row(data, "UNKNOWN"), "mooniex-school")
    school_new_current = None
    if school and school.get("current"):
        old = Path(school["current"])
        new = hq_root / "UNKNOWN" / "mooniex-school"
        if already_migrated(old, new):
            m.note("mooniex-school already migrated, skipping")
        elif old.exists():
            move_verified(old, new)
            m.add(op="move", from_=str(old), to=str(new))
            m.note(f"mooniex-school moved: {old} -> {new}")
        school_new_current = str(new)

    # ---- Phase C: the ~/.claude/projects/.../memory symlink (best-effort) ----
    print("\nPhase C — memory symlink repoint\n")
    memory_result = repoint_memory_symlink(MEMORY_LINK, hq_root / "Agents" / "Memory", m)

    # ---- Phase D: hq.yaml update ----
    print("\nPhase D — hq.yaml update\n")
    backup = STATE_DIR / f"hq-step4a-yaml-backup-{ts}.yaml"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(hq_yaml, backup)
    m.add(op="yaml_backup", from_=str(hq_yaml), to=str(backup))
    lines = hq_yaml.read_text(encoding="utf-8").splitlines(keepends=True)

    compat_entries: list[dict] = []
    for r in moved_rows:
        lines = patch_yaml_row(lines, r["path"], str(r["_target"]), drop_duplicates=False)
        compat_entries.append({"path": r["_orig_current"], "target": str(r["_target"]), "remove_at_step": REMOVE_AT_STEP})
    if external_dir.is_symlink():
        compat_entries.append({"path": str(external_dir), "target": str(hq_root / "External"), "remove_at_step": REMOVE_AT_STEP})
    lines = append_compat_links(lines, compat_entries)

    for it in ext_items:
        lines = patch_item_field(lines, it["name"], it["current"], ext_new_current[it["name"]])
    if pc and pc_new_current and pc.get("current") != pc_new_current:
        lines = patch_item_field(lines, "paperclip", pc["current"], pc_new_current)
    if nohuman_trashed and not nohuman_blocked and nh_item and nh_item.get("current"):
        lines = patch_nohuman_archive(lines, ts)
    if school and school_new_current and school.get("current") != school_new_current:
        lines = patch_item_field(lines, "mooniex-school", school["current"], school_new_current)

    new_text = "".join(lines)
    yaml.safe_load(new_text)  # must still parse
    hq_yaml.write_text(new_text, encoding="utf-8")
    m.add(op="yaml_edit", path=str(hq_yaml))
    m.note(f"hq.yaml updated; backup at {backup}")

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

    if nohuman_blocked:
        print(f"\nBlocker left for the CTO: {nohuman_blocked}")
    if memory_result.startswith("denied"):
        print(f"\nBlocker left for the CTO: memory symlink repoint {memory_result}")

    print(f"\nmanifest: {m.path}  ({len(m.ops)} ops)")
    return 0


# ─────────────────────────── rollback ────────────────────────────────────────

def cmd_rollback(manifest_path: Path) -> int:
    data = json.loads(manifest_path.read_text())
    deferred_worktree_repairs: list[dict] = []
    for op in reversed(data["ops"]):
        kind = op.get("op")
        if kind == "worktree_repair":
            deferred_worktree_repairs.append(op)
        elif kind == "memory_symlink_repoint":
            p = Path(op["path"])
            if p.is_symlink():
                p.unlink()
            os.symlink(op["old_target"], str(p))
            print(f"  memory symlink restored: {p} -> {op['old_target']}")
        elif kind == "symlink":
            p = Path(op["path"])
            if p.is_symlink():
                p.unlink()
                print(f"  unlinked {p}")
        elif kind in ("move", "trash"):
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
        # preflight / yaml_edit / nohuman_brand_verify: informational only, nothing to reverse

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
