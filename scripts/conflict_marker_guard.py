"""Fail when a tracked text file still holds git conflict markers.

A merge that was committed unresolved left `<<<<<<< HEAD` / `>>>>>>> agent/…`
blocks in docs/prompts/absence/CHECKLIST.md on main (found 2026-10-01); every
machine pushes to main, so nothing caught it. CI runs this on every push and
pull request. A file counts only when it has BOTH an opening and a closing
marker at the start of a line (`=======` alone is a Markdown heading rule).

    python scripts/conflict_marker_guard.py [--repo PATH]

Exit 0 when clean, 1 with one `path:line` per marker otherwise.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

OPEN = re.compile(r"^<<<<<<< ")
CLOSE = re.compile(r"^>>>>>>> ")


def find_markers(repo: Path) -> dict[str, list[int]]:
    r = subprocess.run(
        ["git", "grep", "-n", "-I", "-z", "-E", "^(<<<<<<<|>>>>>>>) "],
        cwd=repo, capture_output=True,
    )
    if r.returncode not in (0, 1):  # 1 = no match
        raise RuntimeError(r.stderr.decode("utf-8", "replace"))
    hits: dict[str, dict[str, list[int]]] = {}
    for rec in r.stdout.decode("utf-8", "replace").splitlines():
        parts = rec.split("\0", 2)
        if len(parts) != 3:
            continue
        path, line, text = parts
        kind = "open" if OPEN.match(text) else "close" if CLOSE.match(text) else None
        if kind:
            hits.setdefault(path, {"open": [], "close": []})[kind].append(int(line))
    return {p: sorted(k["open"] + k["close"]) for p, k in hits.items()
            if k["open"] and k["close"]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    args = ap.parse_args(argv)
    found = find_markers(args.repo)
    for path, lines in sorted(found.items()):
        for ln in lines:
            print(f"{path}:{ln}: unresolved merge conflict marker")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
