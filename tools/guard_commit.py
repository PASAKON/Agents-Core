"""Launcher-owned commit gate. Metadata is captured before the worker starts."""
from __future__ import annotations

import base64
import fnmatch
import json
from pathlib import Path
import subprocess
import sys

GUARDS = (
    "tools/agy_browse.py", "tools/guard_commit.py", "tools/delegate.py",
    "config/agy-browse.yaml", "config/agy-settings-*.json", "windows/*",
    "scripts/spawn-worker*", "scripts/hook-*", ".claude/settings*.json", ".github/*",
)


def gate(repo: Path, report: Path, metadata_b64: str) -> list[str]:
    try:
        meta = json.loads(base64.b64decode(metadata_b64, validate=True)) if metadata_b64 else {}
        touches = meta.get("touches", [])
        if not isinstance(touches, list) or not all(isinstance(p, str) for p in touches):
            touches = []
    except (ValueError, TypeError, AttributeError):
        touches = []

    def git(*args):
        return subprocess.run(["git", "-C", str(repo), *args], check=True,
                              stdout=subprocess.PIPE).stdout

    reverted = []
    # No rename folding: both the removed source and added destination need checking.
    paths = git("diff", "--cached", "--no-renames", "--name-only", "-z").decode().split("\0")
    for path in filter(None, paths):
        if not any(fnmatch.fnmatchcase(path, pattern) for pattern in GUARDS):
            continue
        if any(path == p or path.startswith(p.rstrip("/") + "/")
               or fnmatch.fnmatchcase(path, p) for p in touches):
            continue
        tracked = subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"HEAD:{path}"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        if tracked:
            git("restore", "--source=HEAD", "--staged", "--worktree", "--", path)
        else:
            git("rm", "--cached", "-f", "--", path)
            (repo / path).unlink(missing_ok=True)
        reverted.append(path)
    if reverted:
        with report.open("a", encoding="utf-8") as out:
            for path in reverted:
                out.write(f"\nguard file reverted: {path}\n")
        git("add", "--", str(report))
    return reverted


if __name__ == "__main__":
    gate(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3])
