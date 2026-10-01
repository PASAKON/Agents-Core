#!/usr/bin/env python3
"""Emit the org hooks as a --settings file for a session whose cwd is another repo.

Why: Agents-Core's hooks live in <root>/.claude/settings.json and are written as
"${CLAUDE_PROJECT_DIR:-$PWD}/scripts/hook-*.py". Claude Code only reads that file
for a session whose project is Agents-Core. SomPong (the COO) runs with cwd =
the SomPong repo, so none of them load there: no mailbox drain (`send_to_cxo`
letters would pile up unread), no secret-env guard, no browser/research gates.
Measured 2026-10-01 with claude 2.1.285: `--settings <file>` hooks do run, and
CLAUDE_PROJECT_DIR is the session cwd, so the placeholder would point at the
SomPong repo. This script rewrites it to the absolute Agents-Core root and keeps
only the `hooks` key — permissions, env and the rest stay the launcher's call.

The session still loads its own project settings (SomPong's family-gate hook);
Claude Code merges hooks from every source, it does not replace them.

Usage:
    cxo_hooks_settings.py --root /opt/MoonieXHQ/Agents/Core --out /tmp/x.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PLACEHOLDER = "${CLAUDE_PROJECT_DIR:-$PWD}"


def hooks_settings(settings: dict, root: str) -> dict:
    """{"hooks": ...} with the project-dir placeholder replaced by `root`."""
    text = json.dumps(settings.get("hooks") or {})
    # json.dumps(root)[1:-1] = the root as it must read inside a JSON string.
    return {"hooks": json.loads(text.replace(PLACEHOLDER, json.dumps(root)[1:-1]))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    src = Path(args.root) / ".claude" / "settings.json"
    try:
        settings = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"cxo_hooks_settings: cannot read {src}: {exc}", file=sys.stderr)
        return 1
    out = hooks_settings(settings, args.root)
    if not out["hooks"]:
        print(f"cxo_hooks_settings: {src} has no hooks — refusing to emit an empty file", file=sys.stderr)
        return 1
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    n = sum(len(v) for v in out["hooks"].values())
    print(f"cxo_hooks_settings: {n} hook groups across {len(out['hooks'])} events -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
