#!/usr/bin/env python3
"""File edits for scripts/hub/cutover-mac.sh step 4 (docs/design/
tasks-db-hub.md §3.3): route the org MCP servers and the two launchd
daemons through scripts/hub/with-org-db-env.sh, which sources the hub's env
file (ORG_DB_URL) at process-spawn time.

Chosen approach: reference the wrapper's path from command/ProgramArguments,
rather than writing the literal ORG_DB_URL value into these files. Two of
them (config/cto.mcp.json, config/worker.mcp.json) are git-tracked -- the
connection string carries a password, so it must never land in a commit --
and using the same wrapper for the two (non-git-tracked) plists too means
rotating the password later means editing one env file, not four.

Modes:
    (default)  print a unified diff of what WOULD change, write nothing
    --apply    make the changes, print the same diff for the CTO to review
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
WRAPPER = str(ROOT / "scripts" / "hub" / "with-org-db-env.sh")

MCP_FILES = [ROOT / "config" / "cto.mcp.json", ROOT / "config" / "worker.mcp.json"]
PLISTS = [
    Path.home() / "Library" / "LaunchAgents" / "com.mooniex.agents-watchdog.plist",
    Path.home() / "Library" / "LaunchAgents" / "com.mooniex.mac-agent.plist",
]
CTO_CLAUDE_SH = ROOT / "scripts" / "cto-claude.sh"

# Exact text already in scripts/cto-claude.sh (verified by Read) -- anchor
# to insert the new sourcing block right after, matching the file's own
# convention for host-conditional exports (WIKI_ROOT_ORG/WIKI_ROOT_MOONIEX
# above it do the same `[ -z "${VAR:-}" ] && [ -e path ]` shape).
ANCHOR = (
    'if [ -z "${LUNGNOTE_MCP_NODE:-}" ] && [ -x /opt/node-v22/bin/node ]; then\n'
    "  export LUNGNOTE_MCP_NODE=/opt/node-v22/bin/node\n"
    "fi\n"
)

SOURCE_BLOCK_MARKER = "tasks-db-hub cutover"
SOURCE_BLOCK = (
    "\n"
    f"# {SOURCE_BLOCK_MARKER} (docs/design/tasks-db-hub.md \xa73.3 step 4): read\n"
    "# ORG_DB_URL from the env file the hub setup wrote -- never hard-code the\n"
    "# value here, this file is git-tracked. No-op until\n"
    "# scripts/hub/cutover-mac.sh --apply has run on this machine.\n"
    'if [ -z "${ORG_DB_URL:-}" ] && [ -f "$HOME/.config/mooniex/org-db.env" ]; then\n'
    "  set -a\n"
    "  # shellcheck disable=SC1091\n"
    '  source "$HOME/.config/mooniex/org-db.env"\n'
    "  set +a\n"
    "fi\n"
)


def _diff(label: str, before: str, after: str) -> str:
    return "".join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile=f"a/{label}", tofile=f"b/{label}"))


def _flip_mcp_json(path: Path, apply: bool) -> str:
    if not path.exists():
        print(f"SKIP {path}: not found")
        return ""
    before = path.read_text()
    data = json.loads(before)
    org = data.get("mcpServers", {}).get("org")
    if org is None:
        print(f"SKIP {path}: no mcpServers.org block found")
        return ""
    if org.get("command") == WRAPPER:
        print(f"OK   {path}: already flipped")
        return ""
    real_cmd = org["command"]
    real_args = org.get("args", [])
    org["args"] = [real_cmd, *real_args]
    org["command"] = WRAPPER
    after = json.dumps(data, indent=2) + "\n"
    diff = _diff(str(path.relative_to(ROOT)), before, after)
    if apply:
        path.write_text(after)
    return diff


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


def _flip_cto_claude_sh(path: Path, apply: bool) -> str:
    if not path.exists():
        print(f"SKIP {path}: not found")
        return ""
    before = path.read_text()
    if SOURCE_BLOCK_MARKER in before:
        print(f"OK   {path}: already flipped")
        return ""
    if ANCHOR not in before:
        print(f"SKIP {path}: anchor text not found -- edit by hand "
              f"(scripts/cto-claude.sh may have changed shape)")
        return ""
    after = before.replace(ANCHOR, ANCHOR + SOURCE_BLOCK, 1)
    diff = _diff(str(path.relative_to(ROOT)), before, after)
    if apply:
        path.write_text(after)
    return diff


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                     help="write the changes (default: print the diff only)")
    args = ap.parse_args(argv)

    print(f"wrapper: {WRAPPER}")
    print()

    any_diff = False
    for f in MCP_FILES:
        d = _flip_mcp_json(f, args.apply)
        if d:
            any_diff = True
            print(d)
    for p in PLISTS:
        d = _flip_plist(p, args.apply)
        if d:
            any_diff = True
            print(d)
    d = _flip_cto_claude_sh(CTO_CLAUDE_SH, args.apply)
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
