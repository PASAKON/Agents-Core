#!/usr/bin/env python3
"""scripts/claude_home_migrate.py — one-time move of org-owned ~/.claude content
into the repo (ADR 0027), reversible from the manifest it writes.

The CEO runs this by hand (the org's auto-mode classifier refuses to move
private config into a pushed repo on its own — 2026-09-22):

  python3 scripts/claude_home_migrate.py                 # migrate + legacy memory, write manifest
  python3 scripts/claude_home_migrate.py --rollback state/claude-home-migration-<ts>.json

What moves (measured 2026-09-22, nothing here had a copy anywhere else):
  ~/.claude/{CLAUDE.md, settings.json, hooks/, commands/, mcp/mooniex-coord/, tools/}
      -> claude-home/<same>           (settings.local.json is copied as .example, never linked)
  ~/.claude/skills/<12 real skill dirs>   -> .claude/skills/<name>
  ~/.claude/skills/hyperframes-media       -> claude-home/assets/hyperframes-media  (assets, not a skill)
  ~/.claude/projects/*/memory (real dirs)  -> COPIED to Agents-Memory/legacy/<slug>/ (originals untouched)
Every moved path is replaced by a symlink to its new home, so running sessions
keep resolving the same files. Anything overwritten is parked under
~/.claude/backups/claude-home-<ts>/. Left alone on purpose: daemons/ (dead
ClaudeFlow mesh listener, 2026-05-18), daemon/ (Claude Code's own cc-daemon
state), skills/synced + skills/learned (Claude's own), everything reinstallable
(plugins/, cache/, file-history/, ...).
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

ROOT = Path(__file__).resolve().parent.parent
HOME = Path(os.environ.get("CLAUDE_HOME", Path.home() / ".claude"))
SRC = Path(os.environ.get("CLAUDE_HOME_SRC", ROOT / "claude-home"))
SKILLS_DST = ROOT / ".claude" / "skills"
MEMORY_REPO = Path(os.environ.get("AGENTS_MEMORY", ROOT.parent / "Agents-Memory"))

TOP_ENTRIES = ["CLAUDE.md", "settings.json", "hooks", "commands", "mcp/mooniex-coord", "tools"]
TOOLS_SKIP = {"output-untracked-2026-09-05.lst", "worktree-audit-2026-09-05.txt", "winbox.pub"}
HOOKS_SKIP_SUFFIX = (".bak", ".bak.20260517")
REAL_SKILLS = [
    "character-reference-sheet", "content-idea-generator", "cookierun-labeling", "de-ai-ify",
    "homepage-audit", "marketing-principles", "mooniex-video-editor", "positioning-basics",
    "reel-editor-th", "social-card-gen", "video-ad-analysis", "voice-extractor",
]
ASSET_DIRS = ["hyperframes-media"]
OWNER_STAMPS = {"cookierun-labeling": "CTO", "mooniex-video-editor": "CMO", "reel-editor-th": "CTO"}


def _park(path: Path, ts_backup: Path, manifest: list, why: str) -> None:
    bak = ts_backup / why / path.name
    bak.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(bak))
    manifest.append({"op": "move", "from": str(path), "to": str(bak)})
    print(f"  parked ({why}) {path} -> {bak}")


def _move(src: Path, dst: Path, manifest: list, ts_backup: Path) -> None:
    if src.is_symlink():
        print(f"  skip (already a symlink -> {os.readlink(src)}): {src}")
        return
    if not src.exists():
        print(f"  skip (absent): {src}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        bak = ts_backup / "repo-side" / dst.relative_to(ROOT)
        bak.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(dst), str(bak))
        manifest.append({"op": "move", "from": str(dst), "to": str(bak)})
    shutil.move(str(src), str(dst))
    manifest.append({"op": "move", "from": str(src), "to": str(dst)})
    os.symlink(str(dst), str(src))
    manifest.append({"op": "link", "path": str(src), "target": str(dst)})
    print(f"  moved  {src}  ->  {dst}   (+ symlink back)")


def _stamp_owner(skill_dir: Path, owner: str) -> None:
    md = skill_dir / "SKILL.md"
    if not md.is_file():
        return
    s = md.read_text(encoding="utf-8")
    parts = s.split("---", 2)
    if len(parts) < 3 or "\nowner:" in parts[1]:
        return
    md.write_text(s.replace("---\n", f"---\nowner: {owner}\ncreated_by: human\norigin: mooniex-org\n", 1), encoding="utf-8")
    print(f"  stamped owner: {owner} on {skill_dir.name}")


def _freeze_reel_editor() -> None:
    re_dir = SKILLS_DST / "reel-editor-th"
    py = re_dir / ".venv" / "bin" / "python"
    if not py.exists():
        return
    out = subprocess.run([str(py), "-m", "pip", "freeze"], capture_output=True, text=True)
    if out.returncode == 0 and out.stdout.strip():
        (re_dir / "requirements.txt").write_text(out.stdout)
        print(f"  froze reel-editor-th/requirements.txt ({len(out.stdout.splitlines())} pins)")


def _legacy_memory(manifest: list) -> None:
    dst_root = MEMORY_REPO / "legacy"
    if not MEMORY_REPO.is_dir():
        print(f"  skip legacy memory: {MEMORY_REPO} not found")
        return
    n = 0
    for mem in sorted((HOME / "projects").glob("*/memory")):
        if mem.is_symlink() or not mem.is_dir():
            continue
        if not any(p.is_file() for p in mem.rglob("*")):
            continue
        slug = mem.parent.name
        dst = dst_root / slug
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copytree(mem, dst, dirs_exist_ok=True)
        manifest.append({"op": "copy", "from": str(mem), "to": str(dst)})
        n += 1
    (dst_root / "README.md").write_text(
        "# legacy/ — per-project auto-memory dirs copied out of ~/.claude/projects/*/memory\n\n"
        "One-time copy (ADR 0027): these were REAL dirs with no backup anywhere; only\n"
        "`-Users-gob-Projects-Agents/memory` was a symlink into this repo. Folder name = the\n"
        "Claude Code project slug (the cwd with `/` -> `-`). Most of these projects are\n"
        "retired; nothing here is loaded automatically. Read one if you resume that project,\n"
        "then move what still matters into a proper memory file at the repo root.\n"
    )
    print(f"  copied {n} legacy memory dirs -> {dst_root}  (commit + push Agents-Memory yourself)")


def migrate() -> int:
    ts = time.strftime("%Y%m%dT%H%M%S")
    ts_backup = HOME / "backups" / f"claude-home-{ts}"
    manifest: list = []
    print(f"claude-home migrate: HOME={HOME}  SRC={SRC}")
    SRC.mkdir(parents=True, exist_ok=True)

    for entry in TOP_ENTRIES:
        _move(HOME / entry, SRC / entry, manifest, ts_backup)

    live = HOME / "settings.local.json"
    if live.is_file():
        ex = SRC / "settings.local.json.example"
        shutil.copy2(live, ex)
        manifest.append({"op": "copy", "from": str(live), "to": str(ex)})
        print(f"  copied {live} -> {ex}")

    for name in TOOLS_SKIP:
        p = SRC / "tools" / name
        if p.exists():
            _park(p, ts_backup, manifest, "untracked-tools")
    if (SRC / "hooks").is_dir():
        for p in list((SRC / "hooks").iterdir()):
            if p.name.endswith(HOOKS_SKIP_SUFFIX):
                _park(p, ts_backup, manifest, "untracked-hooks")

    # cap-P rule (Projects/CLAUDE.md): the one lowercase path in the hooks
    sj = SRC / "settings.json"
    if sj.is_file():
        s = sj.read_text(); s2 = s.replace("/Users/gob/projects/LLMs", "/Users/gob/Projects/LLMs")
        if s2 != s:
            sj.write_text(s2); print("  settings.json: /Users/gob/projects/LLMs -> /Users/gob/Projects/LLMs")

    for name in REAL_SKILLS:
        _move(HOME / "skills" / name, SKILLS_DST / name, manifest, ts_backup)
        if name in OWNER_STAMPS:
            _stamp_owner(SKILLS_DST / name, OWNER_STAMPS[name])
    for name in ASSET_DIRS:
        _move(HOME / "skills" / name, SRC / "assets" / name, manifest, ts_backup)
    plist = Path.home() / "Library" / "LaunchAgents" / "com.gob.claude-prune-transcripts.plist"
    if plist.is_file():
        dst = SRC / "launchd" / plist.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(plist, dst)
        manifest.append({"op": "copy", "from": str(plist), "to": str(dst)})
        print(f"  copied {plist} -> {dst}   (launchd keeps running from ~/Library)")
    _freeze_reel_editor()
    _legacy_memory(manifest)

    out = ROOT / "state" / f"claude-home-migration-{ts}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"ts": ts, "home": str(HOME), "src": str(SRC), "ops": manifest}, indent=2))
    print(f"manifest: {out}  ({len(manifest)} ops)")
    print("next: bash scripts/install-claude-home.sh --check   then commit claude-home/ + .claude/skills/")
    return 0


def rollback(manifest_path: Path) -> int:
    data = json.loads(manifest_path.read_text())
    for op in reversed(data["ops"]):
        if op["op"] == "link":
            p = Path(op["path"])
            if p.is_symlink():
                p.unlink(); print(f"  unlinked {p}")
        elif op["op"] == "move":
            src, dst = Path(op["to"]), Path(op["from"])
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst)); print(f"  restored {dst}")
        elif op["op"] == "copy":
            pass  # copies are additive (example file, legacy memory) — left for git to judge
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rollback", type=Path, default=None, help="manifest written by a previous run")
    a = ap.parse_args(argv)
    return rollback(a.rollback) if a.rollback else migrate()


if __name__ == "__main__":
    sys.exit(main())
