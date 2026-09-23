#!/usr/bin/env python3
"""scripts/hq_migrate_step4b.py — MoonieX HQ migration step 4b (ADR 0028): move
Agents-Core ITSELF — the org runtime every C-level session, every worker, the
watchdog and 3 launchd jobs run from — from /Users/gob/Projects/Agents to
/Users/gob/MoonieXHQ/Agents/Core. The last, riskiest row of the whole
migration: three C-level sessions can be live and attached inside it while
this runs.

The one atomic step (hazard #1, CTO 2026-09-23 03:3x): `atomic_move_and_link()`
does `os.rename(src, dst)` then `os.symlink(dst, src)` in the SAME Python call,
nothing in between — same APFS volume so the rename is O(1), every running
process's cwd (an inode, not a path string) stays valid across it, and any
open SQLite handle on state/tasks.db stays valid. Everything else (worktree
repair, launchd plists, repoint, hq.yaml, the Claude project slug alias, the
trust-dialog entry, verification) happens strictly AFTER the symlink exists.

HARD GATE (CTO, added before delegation): `--apply` itself queries
state/tasks.db and refuses (exit 1, nothing touched) while ANY task other
than the one performing this migration is `pending|in_progress|rate_limited
|blocked_human` — moving the runtime out from under another session's
(possibly paid) live run is forbidden (IRON §33). The rule lives here, not
in an operator's judgement.

Logical vs physical (hazard #2): a live session's $PWD/$CLAUDE_PROJECT_DIR
stays the OLD (now-symlinked) path while os.getcwd()/Path.resolve() return
the NEW physical one. This script's own path comparisons resolve both sides
(see `atomic_move_and_link`, `verify_after_move`) — the hooks audited for the
same hazard are scripts/hook-cwd-guard.py, scripts/hook-self-repo-guard.py,
scripts/browser/tab_guard.py and scripts/gateguard_categories.py (see their
own diffs / test files for what changed and why).

Reuses hq_migrate_step2 / step3 / step4a primitives by import (preflight,
push, Manifest, patch_yaml_row, compat symlinks, worktree repair+prune,
launchd plist rewrite, structured-file validation, the $PROJECTS-macro-aware
skills.txt rewrite) rather than re-implementing them.

  hq_migrate_step4b.py                       # --plan (default): prints, touches nothing
  hq_migrate_step4b.py --repoint             # rewrite this repo's own hardcoded old paths
  hq_migrate_step4b.py --apply               # do it for real (gated, see above)
  hq_migrate_step4b.py --rollback <manifest.json>

Every unit of work below is independently resumable: a phase whose target
state already holds (row already migrated, plist already rewritten, slug
alias already a symlink to the right place, trust entry already present) is
skipped, not re-attempted or treated as an error — including after a crash
mid-`--apply` (hq-filing field notes, 2026-09-23).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("hq_migrate_step4b.py needs PyYAML — run with /Users/gob/Projects/Agents/.venv/bin/python")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hq_migrate_step2 import (  # noqa: E402  (reuse, do not copy — task instruction)
    Manifest,
    _run,
    git_preflight,
    patch_yaml_row,
    push_current_branch,
)
from hq_migrate_step3 import (  # noqa: E402  (reuse, do not copy — task instruction)
    _validate_structured,
    append_compat_links,
    list_attached_worktrees,
    repair_worktree,
    rewrite_plist_paths,
)
from hq_migrate_step4a import (  # noqa: E402  (reuse, do not copy — task instruction)
    already_migrated,
    rewrite_skills_txt,
)

ROOT = Path(__file__).resolve().parent.parent
HQ_ROOT = Path(os.environ.get("HQ_ROOT", "/Users/gob/MoonieXHQ"))
STATE_DIR = Path(os.environ.get("HQ_STEP4B_STATE_DIR", str(ROOT / "state")))
HQ_PYTHON = os.environ.get("HQ_PYTHON", "/Users/gob/Projects/Agents/.venv/bin/python")
REPO_ROOT = Path(os.environ.get("HQ_STEP4B_REPO_ROOT", str(ROOT)))
TASKS_DB = Path(os.environ.get("HQ_STEP4B_TASKS_DB", str(ROOT / "state" / "tasks.db")))
LAUNCHD_DIR = Path(os.environ.get("HQ_STEP4B_LAUNCHD_DIR", str(Path.home() / "Library" / "LaunchAgents")))
CLAUDE_PROJECTS_DIR = Path(os.environ.get("HQ_STEP4B_CLAUDE_PROJECTS_DIR", str(Path.home() / ".claude" / "projects")))
CLAUDE_JSON = Path(os.environ.get("HQ_STEP4B_CLAUDE_JSON", str(Path.home() / ".claude.json")))

CORE_ROW_PATH = "Agents/Core"
PLIST_NAMES = ("com.mooniex.agents-watchdog.plist", "com.mooniex.cfo-claude-usage.plist", "com.mooniex.mac-agent.plist")
GATE_STATUSES = ("pending", "in_progress", "rate_limited", "blocked_human")
REMOVE_AT_STEP = 5  # matches step4a's convention for the other Agents/* rows

# task brief's own acceptance grep, verbatim (this file's boundary rule: the
# char right after "Agents" must be one of / " end-of-line or space — NEVER a
# naive substring match, which would also corrupt "Agents-Wikis",
# "Agents-Memory" etc. wherever they appear in a tracked file).
OLD_CORE_GIT_GREP_ERE = '/Users/gob/[Pp]rojects/Agents(/|"|$| )'
OLD_CORE_PY_RE = re.compile(r'/Users/gob/[Pp]rojects/Agents(?=[/"\s]|$)', re.MULTILINE)
DOC_EXCLUDE_PATHSPECS = [":!docs/reports", ":!docs/briefs", ":!docs/ops", ":!*.md"]
SELF_EXCLUDE_PATHSPECS = [
    ":!scripts/hq_migrate_step4b.py",
    ":!scripts/test_hq_migrate_step4b.py",
]


class GateBlocked(Exception):
    """--apply refused: another task is in flight, or the registry could not
    be read at all (fails CLOSED — a false block costs a re-run, a false
    allow can move the runtime out from under a live paid worker)."""


# ─────────────────────────── row lookup ──────────────────────────────────────

def load_yaml(hq_yaml: Path) -> dict:
    return yaml.safe_load(hq_yaml.read_text(encoding="utf-8"))


def core_row(data: dict) -> dict:
    for r in data["folders"]:
        if r["path"] == CORE_ROW_PATH:
            return r
    raise ValueError(f"row not found in hq.yaml: {CORE_ROW_PATH}")


# ─────────────────────────── the hard gate ───────────────────────────────────

def this_task_id(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    env = os.environ.get("ORG_TASK_ID", "").strip()
    if env:
        return env
    m = re.search(r"task-[0-9a-zA-Z]+", os.getcwd())
    return m.group(0) if m else None


def check_no_other_tasks_in_flight(db_path: Path, task_id: str | None,
                                   excluded: tuple[str, ...] = ()) -> None:
    """Raises GateBlocked if any task OTHER than `task_id` is in one of
    GATE_STATUSES, or if the registry cannot be read at all. `task_id=None`
    means no self-exclusion is possible (e.g. run outside any worktree) —
    every matching row is then treated as a blocker, which is the safe
    default: by the time nobody can name "this task" any more, this task
    should already be out of the gate statuses anyway."""
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    try:
        from lib import db as db_lib
    except Exception as exc:  # noqa: BLE001 — undecidable, refuse
        raise GateBlocked(f"cannot import lib.db to check the task registry: {exc}") from exc
    if not db_path.exists():
        raise GateBlocked(f"tasks.db not found at {db_path} — cannot verify the org is quiet, refusing")
    placeholders = ",".join("?" for _ in GATE_STATUSES)
    try:
        with db_lib.get_conn(path=db_path, readonly=True) as conn:
            rows = conn.execute(
                f"SELECT id, status, role, title FROM tasks WHERE status IN ({placeholders})",
                GATE_STATUSES,
            ).fetchall()
    except Exception as exc:  # noqa: BLE001 — undecidable, refuse
        raise GateBlocked(f"cannot read {db_path}: {exc}") from exc
    others = [dict(r) for r in rows if r["id"] != task_id and r["id"] not in excluded]
    for r in rows:
        if r["id"] in excluded:
            print(f"  gate: EXCLUDED by --ceo-override-idle: {r['id']} ({r['status']}) — {r['title']}")
    if others:
        listing = "; ".join(f"{t['id']} ({t['status']}, {t['role']}): {t['title']}" for t in others)
        raise GateBlocked(
            f"{len(others)} other task(s) in flight, refusing --apply (IRON §33): {listing}"
        )


# ─────────────────────────── the one atomic step ─────────────────────────────

def _same_device(a: Path, b: Path) -> bool:
    """Split out so tests can stub it without monkeypatching os.stat
    process-wide (that breaks pytest's own filesystem calls)."""
    return os.stat(a).st_dev == os.stat(b).st_dev


def atomic_move_and_link(src: Path, dst: Path) -> None:
    """os.rename then os.symlink, in the SAME call, nothing in between
    (hazard #1). Preflight (git status/sha, same-volume check) happens
    strictly BEFORE this is called; verification strictly AFTER."""
    if dst.exists() or dst.is_symlink():
        raise RuntimeError(f"move target already exists: {dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not _same_device(src, dst.parent):
        raise RuntimeError(
            f"{src} and {dst.parent} are on different volumes — os.rename would not "
            f"be O(1)/atomic, refusing the one-step move"
        )
    os.rename(str(src), str(dst))
    os.symlink(str(dst), str(src))


def verify_after_move(target: Path, expected_sha: str, expected_remotes: str) -> None:
    st = _run(["git", "-C", str(target), "status"])
    if st.returncode != 0:
        raise RuntimeError(f"git status failed after move to {target}: {st.stdout}{st.stderr}")
    sha_after = _run(["git", "-C", str(target), "rev-parse", "HEAD"]).stdout.strip()
    if sha_after != expected_sha:
        raise RuntimeError(f"HEAD sha changed after move: before={expected_sha} after={sha_after}")
    remotes_after = _run(["git", "-C", str(target), "remote", "-v"]).stdout.strip()
    if remotes_after != expected_remotes:
        raise RuntimeError(f"remotes changed after move: before={expected_remotes!r} after={remotes_after!r}")


# ─────────────────────────── claude project slug alias ──────────────────────

def slug_for(path: Path) -> str:
    """Claude Code's own (non-canonicalising) slug rule: '/' -> '-'."""
    return str(path).replace("/", "-")


def create_slug_alias(old_slug: Path, new_slug: Path, m: Manifest) -> str:
    """Best-effort — never fatal (item 3/4 of the task brief: a denial here
    is pasted verbatim and everything else still proceeds)."""
    try:
        if new_slug.is_symlink():
            if Path(os.readlink(new_slug)) == old_slug:
                m.note(f"claude project slug alias already in place: {new_slug} -> {old_slug}")
                return "already"
            return f"denied:{new_slug} is a symlink to something else"
        if new_slug.exists():
            return f"denied:{new_slug} already exists and is not the expected symlink"
        if not old_slug.is_dir():
            return f"denied:source slug directory does not exist: {old_slug}"
        new_slug.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(str(old_slug), str(new_slug))
        m.add(op="slug_alias", path=str(new_slug), target=str(old_slug))
        m.note(f"claude project slug alias created: {new_slug} -> {old_slug}")
        return "ok"
    except PermissionError as e:
        m.note(f"BLOCKER: claude project slug alias denied by the auto-mode classifier: {new_slug}: {e}")
        return f"denied:{e}"


# ─────────────────────────── ~/.claude.json trust entry ──────────────────────

def patch_claude_json_trust(claude_json: Path, old_key: str, new_key: str, ts: str, m: Manifest) -> str:
    """Surgical text insertion — never a full json.dumps() re-serialization
    of the whole file, which would reformat every other project's entry.
    Only bytes for the NEW key are inserted, right after the opening of the
    top-level "projects" object; every existing byte is untouched. Best-
    effort — never fatal."""
    try:
        if not claude_json.exists():
            return "denied:~/.claude.json not found"
        text = claude_json.read_text(encoding="utf-8")
        data = json.loads(text)
        projects = data.get("projects", {})
        if new_key in projects and projects[new_key].get("hasTrustDialogAccepted"):
            m.note(f"trust entry already present for {new_key}")
            return "already"
        old_row = projects.get(old_key, {}) or {}
        new_row: dict = {"hasTrustDialogAccepted": True}
        if "allowedTools" in old_row:
            new_row["allowedTools"] = old_row["allowedTools"]

        marker = '"projects": {'
        idx = text.find(marker)
        if idx == -1:
            return 'denied:no top-level "projects": { found in ~/.claude.json'
        insert_at = idx + len(marker)
        key_literal = json.dumps(new_key)
        value_literal = json.dumps(new_row)
        insertion = f'\n    {key_literal}: {value_literal},'
        new_text = text[:insert_at] + insertion + text[insert_at:]
        reparsed = json.loads(new_text)  # must still parse, and the new key must round-trip
        assert reparsed["projects"][new_key]["hasTrustDialogAccepted"] is True

        backup = STATE_DIR / f"hq-step4b-claude-json-backup-{ts}.json"
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_text(text, encoding="utf-8")
        m.add(op="claude_json_backup", from_=str(claude_json), to=str(backup))
        claude_json.write_text(new_text, encoding="utf-8")
        m.add(op="claude_json_edit", path=str(claude_json), key=new_key)
        m.note(f"trust dialog entry added for {new_key}")
        return "ok"
    except PermissionError as e:
        m.note(f"BLOCKER: ~/.claude.json trust edit denied by the auto-mode classifier: {e}")
        return f"denied:{e}"


# ─────────────────────────── repoint: this repo's own hardcoded paths ────────

def find_repoint_files(repo_root: Path) -> list[str]:
    r = _run(
        ["git", "grep", "-I", "-l", "-E", OLD_CORE_GIT_GREP_ERE, "--", ".",
         *DOC_EXCLUDE_PATHSPECS, *SELF_EXCLUDE_PATHSPECS],
        cwd=repo_root,
    )
    return [l for l in r.stdout.splitlines() if l.strip()]


def rewrite_repoint_files(repo_root: Path, new_core: str) -> list[str]:
    changed: list[str] = []
    for rel in find_repoint_files(repo_root):
        p = repo_root / rel
        text = p.read_text()
        new_text = OLD_CORE_PY_RE.sub(new_core, text)
        if new_text == text:
            continue
        _validate_structured(p, new_text)
        p.write_text(new_text)
        changed.append(rel)
    return changed


def repoint_files_clean(repo_root: Path) -> bool:
    return not find_repoint_files(repo_root)


def cmd_repoint(hq_root: Path, repo_root: Path) -> int:
    data = load_yaml(hq_root / "hq.yaml")
    row = core_row(data)
    new_core = str(hq_root / row["path"])
    changed = rewrite_repoint_files(repo_root, new_core)
    print(f"repoint — {len(changed)} file(s) rewritten:")
    for c in changed:
        print(f"  {c}")
    skills_changed = rewrite_skills_txt(
        repo_root / "claude-home" / "skills.txt",
        {"/Users/gob/Projects/Agents": new_core},
    )
    print(f"repoint — {len(skills_changed)} claude-home/skills.txt row(s) rewritten: {', '.join(skills_changed)}")
    clean = repoint_files_clean(repo_root)
    print("repoint: grep-clean" if clean else "repoint: STILL matches old paths — check")
    return 0 if clean else 1


# ─────────────────────────── plan ─────────────────────────────────────────────

def cmd_plan(hq_root: Path) -> int:
    hq_yaml = hq_root / "hq.yaml"
    data = load_yaml(hq_yaml)
    row = core_row(data)
    src = Path(row["current"])
    target = hq_root / row["path"]
    print("PLAN — Agents/Core (step 4b), nothing will change:\n")
    if already_migrated(src, target):
        print(f"  ALREADY MIGRATED  {src}  ->  {target}")
    else:
        info = git_preflight(src)
        push_note = ""
        if info["ahead"] and info["has_upstream"]:
            push_note = f"  PUSH NEEDED: branch {info['branch']} ahead {info['ahead']}"
        elif not info["has_upstream"]:
            push_note = "  NOT PUSHED: no upstream"
        print(f"  MOVE  {src}  ->  {target}   [{info['branch']} @ {info['sha'][:10]}, dirty={info['dirty']}]{push_note}")
        for wt in list_attached_worktrees(src):
            print(f"    WORKTREE (will repair): {wt}")
    print("\n  launchd plists to rewrite (existing only):")
    for name in PLIST_NAMES:
        p = LAUNCHD_DIR / name
        print(f"    {p}  {'(exists)' if p.exists() else '(missing, skip)'}")
    print(f"\n  claude project slug alias: {CLAUDE_PROJECTS_DIR / slug_for(target)}  ->  {CLAUDE_PROJECTS_DIR / slug_for(src)}")
    print(f"  ~/.claude.json trust entry: projects[{str(target)!r}].hasTrustDialogAccepted = true")
    try:
        check_no_other_tasks_in_flight(TASKS_DB, this_task_id(None))
        print("\n  gate: clear — no other task in flight")
    except GateBlocked as exc:
        print(f"\n  gate: WOULD BLOCK --apply — {exc}")
    print("\nplan only — no filesystem or yaml changes made.")
    return 0


# ─────────────────────────── apply ────────────────────────────────────────────

def cmd_apply(hq_root: Path, task_id_arg: str | None, excluded: tuple[str, ...] = ()) -> int:
    # ---- the hard gate, before anything else is even read ----
    task_id = this_task_id(task_id_arg)
    try:
        check_no_other_tasks_in_flight(TASKS_DB, task_id, excluded)
    except GateBlocked as exc:
        print(f"BLOCKED — {exc}")
        print("Nothing was touched. Re-run --apply once those tasks are no longer in flight.")
        return 1

    hq_yaml = hq_root / "hq.yaml"
    data = load_yaml(hq_yaml)
    row = core_row(data)
    orig_current = row["current"]
    src = Path(orig_current)
    target = hq_root / row["path"]

    already_done = already_migrated(src, target)
    # hq.yaml's own `current:` is the only on-disk record of the pre-move
    # path, and Phase G below overwrites it to `target` on the run that
    # completes the migration. On any LATER invocation `orig_current` reads
    # back as `target` itself — not a stale value, but a signal that Phase G
    # already ran to completion. Treat that as a full no-op: recomputing the
    # plist/slug/trust mapping from a self-referential "old" path would
    # corrupt them (a slug alias pointing at itself, a duplicated
    # compat_links entry) instead of leaving already-correct state alone.
    yaml_already_done = already_done and orig_current == str(target)

    ts = time.strftime("%Y%m%dT%H%M%S")
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    m = Manifest(ts)
    m.path = STATE_DIR / f"hq-step4b-migration-{ts}.json"

    if yaml_already_done:
        m.note(f"already fully migrated (hq.yaml already updated): {target} — nothing to do")
        print(f"\nmanifest: {m.path}  ({len(m.ops)} ops)")
        return 0

    if not already_done:
        # ---- Phase A: preflight + push. No moves yet. ----
        print("Phase A — preflight, push (no moves yet)\n")
        info = git_preflight(src)
        worktrees = list_attached_worktrees(src)
        m.add(op="preflight", row=row["path"], **{k: v for k, v in info.items() if k != "remotes"}, worktrees=worktrees)
        print(f"  {row['path']}: branch={info['branch']} sha={info['sha'][:10]} dirty={info['dirty']} ahead={info['ahead']} has_upstream={info['has_upstream']}")
        if info["has_upstream"] and info["ahead"] > 0:
            ok, out = push_current_branch(src)
            m.add(op="push", path=str(src), branch=info["branch"], ahead=info["ahead"], ok=ok, output=out)
            if not ok:
                m.note("APPLY STOPPED at Phase A validation — no repo moved, hq.yaml untouched")
                m.note(f"BLOCKER: git push failed for branch {info['branch']}: {out}")
                print(f"\nSTOP — push failed:\n  ✗ {out}\n\nmanifest: {m.path}")
                return 1
            m.note(f"pushed {src} branch {info['branch']} (+{info['ahead']})")
        elif not info["has_upstream"]:
            m.note(f"not pushed: no upstream — branch {info['branch']}")

        # ---- Phase B: the one atomic step ----
        print("\nPhase B — atomic move + symlink (same-volume, single call)\n")
        atomic_move_and_link(src, target)
        m.add(op="atomic_move_and_link", from_=str(src), to=str(target), sha=info["sha"])
        m.note(f"moved + symlinked atomically: {src} -> {target}")

        # ---- Phase C: verify (AFTER the link exists) ----
        verify_after_move(target, info["sha"], info["remotes"])
        m.note("verified: git status clean, HEAD unchanged, remotes unchanged")

        for wt in worktrees:
            repair_worktree(target, Path(wt))
            m.add(op="worktree_repair", worktree=wt, target=str(target), original_repo=str(src))
            m.note(f"worktree repaired: {wt} -> {target}")
    else:
        m.note(f"already migrated (symlink -> target already in place), skipping move: {src} -> {target}")

    # ---- Phase D: launchd plists (never launchctl'd — the compat symlink keeps them running) ----
    print("\nPhase D — launchd plists\n")
    mapping = {orig_current: str(target)}
    for name in PLIST_NAMES:
        rewrite_plist_paths(LAUNCHD_DIR / name, mapping, ts, m)

    # ---- Phase E: claude project slug alias ----
    print("\nPhase E — claude project slug alias\n")
    old_slug = CLAUDE_PROJECTS_DIR / slug_for(src)
    new_slug = CLAUDE_PROJECTS_DIR / slug_for(target)
    slug_result = create_slug_alias(old_slug, new_slug, m)

    # ---- Phase F: ~/.claude.json trust entry ----
    print("\nPhase F — ~/.claude.json trust entry\n")
    trust_result = patch_claude_json_trust(CLAUDE_JSON, orig_current, str(target), ts, m)

    # ---- Phase G: hq.yaml update ----
    print("\nPhase G — hq.yaml update\n")
    backup = STATE_DIR / f"hq-step4b-yaml-backup-{ts}.yaml"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(hq_yaml, backup)
    m.add(op="yaml_backup", from_=str(hq_yaml), to=str(backup))
    lines = hq_yaml.read_text(encoding="utf-8").splitlines(keepends=True)
    lines = patch_yaml_row(lines, row["path"], str(target), drop_duplicates=False)
    if f'path: "{orig_current}"' not in "".join(lines):
        lines = append_compat_links(lines, [{"path": orig_current, "target": str(target), "remove_at_step": REMOVE_AT_STEP}])
    else:
        m.note(f"compat_links entry already present for {orig_current}, not duplicating")
    new_text = "".join(lines)
    yaml.safe_load(new_text)  # must still parse
    hq_yaml.write_text(new_text, encoding="utf-8")
    m.add(op="yaml_edit", path=str(hq_yaml), row=row["path"])
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

    if slug_result.startswith("denied"):
        print(f"\nBlocker left for the CTO: claude project slug alias {slug_result}")
    if trust_result.startswith("denied"):
        print(f"\nBlocker left for the CTO: ~/.claude.json trust entry {trust_result}")

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
        elif kind == "slug_alias":
            p = Path(op["path"])
            if p.is_symlink():
                p.unlink()
                print(f"  unlinked slug alias {p}")
        elif kind == "claude_json_backup":
            shutil.copy2(op["to"], op["from_"])
            print(f"  restored ~/.claude.json from {op['to']}")
        elif kind == "atomic_move_and_link":
            src, dst = Path(op["from_"]), Path(op["to"])
            if src.is_symlink():
                src.unlink()
            if dst.exists():
                shutil.move(str(dst), str(src))
                print(f"  restored {src} <- {dst}")
        elif kind == "yaml_backup":
            shutil.copy2(op["to"], op["from_"])
            print(f"  restored hq.yaml from {op['to']}")
        elif kind == "plist_backup":
            shutil.copy2(op["to"], op["from_"])
            print(f"  restored plist {op['from_']}")
        elif kind == "push":
            if op.get("ok"):
                print(f"  NOTE: cannot un-push {op.get('path')} branch {op.get('branch')} (+{op.get('ahead')}) — revert on origin by hand if needed")
        # preflight / yaml_edit / plist_edit / claude_json_edit: informational, nothing to reverse directly

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
    ap.add_argument("--apply", action="store_true", help="perform the migration for real (gated)")
    ap.add_argument("--repoint", action="store_true", help="rewrite this repo's own hardcoded old paths")
    ap.add_argument("--rollback", type=Path, default=None, help="manifest json from a previous --apply")
    ap.add_argument("--task-id", default=None, help="override self-exclusion id for the --apply gate")
    ap.add_argument("--ceo-override-idle", action="append", default=[], metavar="TASK_ID",
                    help="exclude a task the CTO has verified IDLE (process at its prompt, report submitted) "
                         "from the gate, on the CEO's explicit word; printed loudly (CEO 2026-09-23)")
    a = ap.parse_args(argv)
    if a.rollback:
        return cmd_rollback(a.rollback)
    if a.repoint:
        return cmd_repoint(HQ_ROOT, REPO_ROOT)
    if a.apply:
        return cmd_apply(HQ_ROOT, a.task_id, tuple(a.ceo_override_idle))
    return cmd_plan(HQ_ROOT)


if __name__ == "__main__":
    sys.exit(main())
