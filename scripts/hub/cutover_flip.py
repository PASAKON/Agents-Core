#!/usr/bin/env python3
"""File edits for scripts/hub/cutover-mac.sh step 4 (docs/design/
tasks-db-hub.md §3.3): route the two launchd daemons through
scripts/hub/with-org-db-env.sh, which sources the hub's env file
(ORG_DB_URL) at process-spawn time.

Chosen approach: reference the wrapper's path from ProgramArguments, rather
than writing the literal ORG_DB_URL value into the plists -- the connection
string carries a password. Routing the plists through the same wrapper the
MCP servers use means rotating the password later means editing one env file.

Only untracked files are edited here: the two launchd plists and the host's
node file (~/.config/mooniex/node.yaml). This script no longer edits
git-tracked files (Org Mesh W1.6): config/cto.mcp.json, config/worker.mcp.json
and scripts/cto-claude.sh used to be rewritten, and a tracked edit is dirty
state on every checkout, a conflict on every pull, and absent on a host that
never ran this script. The org MCP servers reach the hub through the
generators instead -- scripts/lib/cxo_mcp_config.py (C-level sessions) and
lib/worker_mcp_config.py (per-spawn worker config) start the org server
through the wrapper when the node file says `org_db: hub` and the env file
exists. The env file alone is not the switch: it predates the cutover, so
this script writes the node-file line, and only this script's --apply does.
Sessions and workers already running keep their old config until restart.

Modes:
    (default)   print a unified diff of what WOULD change, write nothing
    --apply     make the changes, print the same diff for the CTO to review
    --rollback  remove the `org_db:` line from the node file (with --apply;
                without it, print what would be removed). The plists are not
                touched: restoring them stays manual (cutover-mac.sh prints how).
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from cxo_mcp_config import node_yaml_path, set_org_db  # noqa: E402

WRAPPER = str(ROOT / "scripts" / "hub" / "with-org-db-env.sh")

PLISTS = [
    Path.home() / "Library" / "LaunchAgents" / "com.mooniex.agents-watchdog.plist",
    Path.home() / "Library" / "LaunchAgents" / "com.mooniex.mac-agent.plist",
]


def _diff(label: str, before: str, after: str) -> str:
    return "".join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile=f"a/{label}", tofile=f"b/{label}"))


_PROGRAM_ARGUMENTS_RE = re.compile(
    r"(<key>ProgramArguments</key>\s*<array>)(\r?\n)([ \t]*)(<string>)"
)


def _flip_plist(path: Path, apply: bool) -> str:
    """Text-level insert, not plistlib parse+rewrite: the real
    com.mooniex.agents-watchdog.plist has a `--loop` inside an XML comment
    (`<!-- ... runners.watchdog --loop, ... -->`), and a bare double-hyphen
    inside a comment is invalid XML -- launchd's own parser tolerates it,
    Python's strict expat one (what plistlib uses) does not, so
    plistlib.loads() raises ExpatError on this exact file (measured while
    testing this script). Inserting one <string> line as text avoids ever
    parsing the file, so it works on both the well-formed and the
    launchd-tolerated-but-technically-invalid case."""
    if not path.exists():
        print(f"SKIP {path}: not found")
        return ""
    before = path.read_text()
    if WRAPPER in before:
        print(f"OK   {path}: already flipped")
        return ""
    m = _PROGRAM_ARGUMENTS_RE.search(before)
    if not m:
        print(f"SKIP {path}: no <key>ProgramArguments</key><array> found")
        return ""
    prefix, newline, indent, first_string = m.groups()
    insertion = (f"{prefix}{newline}{indent}<string>{WRAPPER}</string>"
                 f"{newline}{indent}{first_string}")
    after = before[:m.start()] + insertion + before[m.end():]
    diff = _diff(path.name, before, after)
    if apply:
        path.write_text(after)
    return diff


def _flip_node_yaml(path: Path, apply: bool, rollback: bool = False) -> str:
    """Set (or, on rollback, remove) `org_db: hub` in the node file, keeping
    every other line -- `host:` above all -- as is. A missing file is created
    holding only the switch (lib.config treats a node file with no `host:` as
    having nothing to say). Idempotent: a second run changes nothing."""
    before = path.read_text() if path.exists() else ""
    after = set_org_db(before, None if rollback else "hub")
    if after == before:
        print(f"OK   {path}: org_db already {'absent' if rollback else 'hub'}")
        return ""
    diff = _diff(path.name, before, after)
    if apply:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(after)
    return diff


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                     help="write the changes (default: print the diff only)")
    ap.add_argument("--rollback", action="store_true",
                     help="remove org_db from the node file instead of setting it")
    args = ap.parse_args(argv)

    node = node_yaml_path()
    print(f"wrapper:   {WRAPPER}")
    print(f"node file: {node}")
    print()

    any_diff = False
    for p in [] if args.rollback else PLISTS:
        d = _flip_plist(p, args.apply)
        if d:
            any_diff = True
            print(d)
    # Last: the node-file line is the switch that makes new sessions use the hub.
    d = _flip_node_yaml(node, args.apply, args.rollback)
    if d:
        any_diff = True
        print(d)

    if not any_diff:
        print("no changes needed -- already flipped.")
    elif not args.apply:
        print("(dry-run -- pass --apply to write the above.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
