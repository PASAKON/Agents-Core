"""Repo-wide guard for the C-level two-layer tab boundary (commit e42212b).

    OSC 1 (\\033]1;) -> tab strip        — scripts/tab-title.sh + tools/itermtab.py
    OSC 2 (\\033]2;) -> window titlebar  — tools/maintab.py
    OSC 0 (\\033]0;) -> writes BOTH, so ANY use of it silently destroys one layer.

That boundary was, until this file, protected only by comments plus two
indirect assertions (scripts/test_tab_title.py asserts OSC 1,
scripts/test_maintab.py asserts OSC 2). Nothing stopped a future change — or
a new spawn path — from reintroducing OSC 0. It already happened once: six
callers were missed on the first pass (scripts/cto-claude.sh,
scripts/cxo-claude.sh, tools/delegate.py x2, tools/resume_dev.py,
runners/cto_chat.py — all fixed alongside this guard).

This test:
  1. Scans every *.py / *.sh in the repo for an OSC-0 terminal write, in every
     escaping variant used here, and FAILs listing file:line for any hit not
     on the explicit allow-list.
  2. Asserts the positive side too: the known OSC-1 / OSC-2 call sites are
     actually present, so the guard proves the layers are wired, not merely
     that OSC 0 is absent.

Run via:   python3 scripts/test_osc_surface_boundary.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Directories to skip entirely (never contain callers worth scanning, and
# state/output can be large/generated/binary-ish).
#
# `worktrees` matters most and is the easiest to miss: every delegated DEV
# task gets a full checkout there, frozen at whatever main looked like when
# the task was created. Scanning those reports long-fixed code as a live
# regression — 909 files scanned instead of ~60, nearly all of the noise from
# stale copies. A DEV writing this guard cannot see the problem, because from
# inside a worktree there is no nested worktrees/ directory to trip over.
SKIP_DIRS = {".venv", ".git", "node_modules", "state", "output", ".agents",
             "worktrees"}

# OSC-0 escaping variants actually used in this repo:
#   \033]0;    bash / python octal-escape form (scripts/*.sh, f-strings)
#   \x1b]0;    python hex-escape form
#   \e]0;      bash $'...'-style escape form
#   \\033]0;   AppleScript-embedded double-escape form (tools/delegate.py,
#              tools/resume_dev.py build `write text "printf '\\033]0;...'"`)
# The last variant is a superset of the first (it contains "\033]0;" as a
# substring) so it is already caught, but it's listed explicitly since it's
# the shape that actually slipped through on the first pass.
OSC0_PATTERNS = ("\\033]0;", "\\x1b]0;", "\\e]0;", "\\\\033]0;")

WHY_BANNED = (
    "WHY THIS FAILS: OSC 0 sets BOTH the tab-strip title (OSC 1, owned by "
    "scripts/tab-title.sh + tools/itermtab.py) AND the window titlebar "
    "(OSC 2, owned by tools/maintab.py). Writing it from anywhere silently "
    "destroys whichever of the two layers you didn't mean to touch. Use "
    "OSC 1 to rename a tab, OSC 2 only inside tools/maintab.py."
)

# Files that legitimately mention the OSC-0 literal ONLY to assert its
# ABSENCE. An explicit path set, not a broad "any test file" rule — so a
# real regression written inside a test still fails this scan.
ALLOWLIST = {
    (ROOT / "scripts" / "test_maintab.py").resolve(),
    # This file itself: it names the OSC-0 literal only to detect/describe
    # it (docstring + OSC0_PATTERNS), never to write it to a terminal.
    (ROOT / "scripts" / "test_osc_surface_boundary.py").resolve(),
}

# file, substring that must be present -> proves the OSC1/OSC2 layers are
# actually wired, not just absent-of-OSC0.
POSITIVE_ASSERTIONS = [
    ("scripts/tab-title.sh", "\\033]1;"),
    ("tools/itermtab.py", "\\033]1;"),
    ("tools/maintab.py", "\\033]2;"),
    ("scripts/cto-claude.sh", "\\033]1;"),
    ("scripts/cxo-claude.sh", "\\033]1;"),
]


def _mark(ok: bool, msg: str) -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def _iter_source_files():
    for path in ROOT.rglob("*"):
        if path.suffix not in (".py", ".sh"):
            continue
        if not path.is_file():
            continue
        rel_parts = path.relative_to(ROOT).parts[:-1]
        if any(part in SKIP_DIRS for part in rel_parts):
            continue
        yield path


def find_osc0_hits() -> list[str]:
    hits = []
    for path in _iter_source_files():
        if path.resolve() in ALLOWLIST:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if any(pat in line for pat in OSC0_PATTERNS):
                rel = path.relative_to(ROOT)
                hits.append(f"{rel}:{lineno}: {line.strip()}")
    return hits


def test_no_osc0_writes_outside_allowlist() -> tuple[bool, list[str]]:
    hits = find_osc0_hits()
    return (not hits, hits)


def test_layers_are_wired() -> tuple[bool, list[str]]:
    missing = []
    for rel, pattern in POSITIVE_ASSERTIONS:
        path = ROOT / rel
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            missing.append(f"{rel}: file not found")
            continue
        if pattern not in text:
            missing.append(f"{rel}: expected to find {pattern!r}, did not")
    return (not missing, missing)


def main() -> int:
    fails = 0

    ok, hits = test_no_osc0_writes_outside_allowlist()
    _mark(ok, "no OSC-0 terminal writes anywhere outside the allow-list "
              f"(scanned {sum(1 for _ in _iter_source_files())} .py/.sh files)")
    if not ok:
        fails += 1
        for h in hits:
            print(f"    {h}")
        print(f"    {WHY_BANNED}")

    ok, missing = test_layers_are_wired()
    _mark(ok, "OSC 1 (tab strip) + OSC 2 (Main Tab) layers are actually wired "
              "at every known call site")
    if not ok:
        fails += 1
        for m in missing:
            print(f"    {m}")

    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
