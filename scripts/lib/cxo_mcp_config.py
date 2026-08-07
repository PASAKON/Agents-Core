#!/usr/bin/env python3
"""Generate the per-role MCP config for a C-level (CXO) Claude session.

Single source of truth for cto-claude.sh and cxo-claude.sh, which used to
carry two drifting copies: cto-claude.sh built a temp config inline, while
cxo-claude.sh read the committed config/cto.mcp.json with Mac paths baked
in (that file breaks on Contabo, ROOT=/opt/mooniex-agents).

Why this exists at all: without --strict-mcp-config a CXO session inherits
every MCP server it can see — Agents/.mcp.json, ~/.claude.json, and every
enabled plugin — roughly 13 servers, ~1.5 GB of phys_footprint on an 8 GB
box, for a role whose tool allowlist only covers org + lungnote. Emitting
an explicit per-role set and launching with --strict-mcp-config keeps the
servers a role actually calls and drops the rest.

A server is emitted only when its command/script is actually present, so
the same launcher works on a box where LungNote or the Supabase CLI was
never installed instead of spawning a server that fails its handshake.

It also emits the matching --allowed-tools list (--print-allowed), because a
server that loads but whose tools are not on the allowlist is the worst of
both worlds: it pays the process + schema cost every launch, then prompts on
every call. Deriving both from this one file makes that pair impossible to
desync — the launchers no longer carry a hand-copied tool string.

Usage:
    python3 scripts/lib/cxo_mcp_config.py --role cto --root "$ROOT" \
        --out /tmp/cto-mcp-XXXX.json
    python3 scripts/lib/cxo_mcp_config.py --role cto --root "$ROOT" \
        --print-allowed                       # space-separated tool names
    python3 scripts/lib/cxo_mcp_config.py --servers meigen --root "$ROOT" \
        --out /tmp/borrow.json                # explicit set, ignores roles

Env overrides (no code edit needed):
    CXO_EXTRA_MCP=meigen,meta-ads-135   add servers to this role
    CXO_SKIP_MCP=supabase               drop servers from this role
    CXO_SUPABASE_WRITE=1                drop --read-only from the supabase server
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Optional server locations. Overridable so a non-Mac box can point
# elsewhere without touching this file.
LUNGNOTE_MCP_JS = os.environ.get(
    "LUNGNOTE_MCP_JS", "/Users/gob/LungNote Projects/mcp/index.js"
)
MOONIEX_COORD_MCP_JS = os.environ.get(
    "MOONIEX_COORD_MCP_JS",
    str(Path.home() / ".claude" / "mcp" / "mooniex-coord" / "index.mjs"),
)

# Primary Supabase project (webapp + claudeflow share it; the CFO tiles read
# webapp_cfo_* from here). The other three refs in Agents/.mcp.json were
# called once each in 6,478 logged MCP calls, so they stay opt-in via
# CXO_EXTRA_MCP rather than loading in every session.
SUPABASE_PROJECT_REF = os.environ.get(
    "CXO_SUPABASE_PROJECT_REF", "tlokhyqpthvxabweekps"
)

# Which servers each role gets. Derived from a usage audit over 199
# transcripts / 6,478 MCP calls (2026-04-23..2026-08-06): org 852,
# lungnote 285, meigen 43, supabase 28, meta-ads-135 14, mooniex-coord 2.
#
# mooniex-coord is deliberately NOT in BASE despite being cross-role: 2 calls
# out of 6,478 does not earn a process + tool schemas in every session on
# every box. Sessions that actually need agent-to-agent messaging opt in with
# CXO_EXTRA_MCP=mooniex-coord (or borrow it, see scripts/mcp-borrow.sh).
BASE_SERVERS = ("org", "lungnote")
ROLE_SERVERS: dict[str, tuple[str, ...]] = {
    "cto": BASE_SERVERS + ("supabase",),
    "cfo": BASE_SERVERS + ("supabase",),
    "cgo": BASE_SERVERS + ("supabase", "meta-ads-135"),
    "cmo": BASE_SERVERS + ("meta-ads-135", "meigen"),
}

# Tools each server contributes to --allowed-tools, WITHOUT the mcp__<server>__
# prefix. Only names listed here are pre-approved; anything a server exposes
# beyond this still works but goes through the normal permission prompt, which
# is how write-shaped tools stay gated. `org` is filled from the registry at
# import time so a new org tool cannot go missing from the launchers again
# (same guarantee test_tool_parity.py gives the three Python surfaces).
SERVER_TOOLS: dict[str, tuple[str, ...]] = {
    "org": (),  # populated below from lib.org_tools_registry
    "lungnote": (
        "list_todos",
        "add_todo",
        "complete_todo",
        "list_recent",
        "read_note",
        "create_note",
        "append_note",
        "search_notes",
    ),
    # execute_sql is safe to pre-approve only because the server itself runs
    # with --read-only (see _build). apply_migration is omitted on purpose:
    # prod DDL goes through the Supabase SQL Editor / db push, never a chat.
    "supabase": ("list_tables", "list_migrations", "list_extensions", "execute_sql"),
    "mooniex-coord": (
        "read_inbox",
        "send_message",
        "list_active_agents",
        "directory",
        "read_thread",
        "claim_message",
    ),
    # generate_image / generate_video are deliberately absent: they spend real
    # money, and MoonieX generates through Fal.ai, never MeiGen (CEO 2026-07-13).
    # MeiGen is here for the free prompt/reference tools only.
    "meigen": ("search_gallery", "enhance_prompt", "get_inspiration", "list_models"),
    # meta-ads-mcp exposes 134 tools, 68 of them read-shaped. Pre-approving all
    # of them would just move the bloat; this is the read set the CGO/CMO jobs
    # actually need (how did it perform, what did it cost). Every create/update/
    # delete tool stays off the list on purpose — those spend budget, so they
    # should cost a deliberate approval.
    "meta-ads-135": (
        "list_ad_accounts",
        "get_ad_account",
        "get_account_insights",
        "list_campaigns",
        "get_campaign_insights",
        "list_adsets",
        "get_adset_insights",
        "list_ads",
        "get_ad_insights",
    ),
}

# Built-in (non-MCP) tools every C-level session gets.
BUILTIN_TOOLS = ("Read", "Grep", "Glob", "Bash")


def _org_tool_names(root: str) -> tuple[str, ...]:
    """org's tool names, straight from the registry that defines them.

    Resolved in a subprocess under the venv interpreter, not by importing
    here: the launchers invoke this file with the system `python3`, and
    lib.org_tools_registry imports lib.config which needs PyYAML. A direct
    import therefore raises ModuleNotFoundError on exactly the path that
    matters. Guessing the names instead is not an option — a wrong list is
    a session whose org tools silently prompt — so this raises on failure.
    """
    venv = Path(root) / ".venv" / "bin" / "python"
    code = (
        "import sys; sys.path.insert(0, %r);"
        "from lib.org_tools_registry import REGISTRY;"
        "print(' '.join(s.name for s in REGISTRY))" % str(root)
    )
    proc = subprocess.run(
        [str(venv) if venv.exists() else sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=root,
    )
    names = tuple(proc.stdout.split())
    if proc.returncode != 0 or not names:
        raise RuntimeError(
            "cxo_mcp_config: cannot read org tool names from "
            f"lib.org_tools_registry: {proc.stderr.strip().splitlines()[-1:] or ['no output']}"
        )
    return names


def _build(name: str, root: str) -> dict | None:
    """Return the MCP entry for `name`, or None when it isn't installed here."""
    if name == "org":
        python = Path(root) / ".venv" / "bin" / "python"
        if not python.exists():
            return None
        return {
            "command": str(python),
            "args": ["-m", "runners.cto_mcp_server"],
            "cwd": root,
            "env": {"PYTHONUNBUFFERED": "1"},
        }

    if name == "lungnote":
        if not Path(LUNGNOTE_MCP_JS).is_file():
            return None
        return {
            "type": "stdio",
            "command": "node",
            "args": [LUNGNOTE_MCP_JS],
            "env": {},
        }

    if name == "mooniex-coord":
        if not Path(MOONIEX_COORD_MCP_JS).is_file():
            return None
        return {
            "type": "stdio",
            "command": "node",
            "args": [MOONIEX_COORD_MCP_JS],
            "env": {},
        }

    if name == "supabase":
        if not shutil.which("mcp-server-supabase"):
            return None
        # --read-only is what makes execute_sql safe to pre-approve in
        # SERVER_TOOLS: the server refuses writes, so the guarantee is
        # enforced server-side instead of by prompt fatigue. A session that
        # genuinely needs to write sets CXO_SUPABASE_WRITE=1, which drops the
        # flag AND (because execute_sql is then a write vector) should be
        # paired with a deliberate look at what it is about to run.
        args = [f"--project-ref={SUPABASE_PROJECT_REF}", "--features=database"]
        if os.environ.get("CXO_SUPABASE_WRITE") != "1":
            args.append("--read-only")
        # Token left unexpanded on purpose — Claude Code resolves ${VAR} against
        # the session env, which is where .claude/settings.local.json puts the PAT.
        return {
            "command": "mcp-server-supabase",
            "args": args,
            "env": {"SUPABASE_ACCESS_TOKEN": "${SUPABASE_ACCESS_TOKEN}"},
        }

    if name == "meta-ads-135":
        if not shutil.which("meta-ads-mcp"):
            return None
        return {
            "type": "stdio",
            "command": "meta-ads-mcp",
            "args": [],
            "env": {
                "META_ADS_ACCESS_TOKEN": "${META_ADS_ACCESS_TOKEN}",
                "META_AD_ACCOUNT_ID": "1374787969502492",
            },
        }

    if name == "meigen":
        if not shutil.which("npx"):
            return None
        return {"command": "npx", "args": ["-y", "meigen@1.3.3"]}

    return None


def _names_for(role: str, explicit: str = "") -> list[str]:
    """Server names for `role`, or exactly `explicit` when given.

    --servers is the borrow path (scripts/mcp-borrow.sh): one throwaway
    session gets one server and nothing else, so the role tables and the
    CXO_EXTRA/SKIP env pair are bypassed entirely — a borrow must be
    reproducible regardless of what the calling shell exports.
    """
    if explicit:
        return [n.strip() for n in explicit.split(",") if n.strip()]
    names = list(ROLE_SERVERS.get(role, BASE_SERVERS))
    for extra in os.environ.get("CXO_EXTRA_MCP", "").split(","):
        extra = extra.strip()
        if extra and extra not in names:
            names.append(extra)
    skip = {s.strip() for s in os.environ.get("CXO_SKIP_MCP", "").split(",") if s.strip()}
    return [n for n in names if n not in skip]


def _allowed_for(servers: list[str], root: str, builtins: bool = True) -> list[str]:
    """--allowed-tools entries for exactly the servers that got emitted."""
    tools: list[str] = []
    for name in servers:
        base = SERVER_TOOLS.get(name, ())
        if name == "org":
            base = _org_tool_names(root)
        tools += [f"mcp__{name}__{t}" for t in base]
    if builtins:
        tools += list(BUILTIN_TOOLS)
    return tools


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", default="")
    ap.add_argument("--servers", default="", help="explicit comma list; ignores --role")
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", default="")
    ap.add_argument(
        "--print-allowed",
        action="store_true",
        help="print the matching --allowed-tools list to stdout instead of writing --out",
    )
    ap.add_argument(
        "--no-builtins",
        action="store_true",
        help="with --print-allowed, omit Read/Grep/Glob/Bash (borrow sessions want MCP only)",
    )
    args = ap.parse_args()
    if not args.role and not args.servers:
        ap.error("one of --role or --servers is required")
    if not args.out and not args.print_allowed:
        ap.error("one of --out or --print-allowed is required")

    servers: dict[str, dict] = {}
    missing: list[str] = []
    for name in _names_for(args.role, args.servers):
        entry = _build(name, args.root)
        if entry is None:
            missing.append(name)
        else:
            servers[name] = entry

    # A role launch without org is a broken session; an explicit --servers
    # borrow has no such requirement (it may be meigen-only), but it must
    # still resolve to at least one real server rather than an empty config.
    if not args.servers and "org" not in servers:
        print(
            f"cxo_mcp_config: org MCP server unavailable "
            f"({args.root}/.venv/bin/python missing) — refusing to launch",
            file=sys.stderr,
        )
        return 1
    if not servers:
        print(
            f"cxo_mcp_config: none of the requested servers are installed here "
            f"({','.join(missing)})",
            file=sys.stderr,
        )
        return 1

    if args.print_allowed:
        print(" ".join(_allowed_for(list(servers), args.root, not args.no_builtins)))
        return 0

    Path(args.out).write_text(json.dumps({"mcpServers": servers}, indent=2) + "\n")
    print(
        f"cxo_mcp_config: role={args.role or args.servers} servers={','.join(servers)}"
        + (f" skipped(not installed)={','.join(missing)}" if missing else ""),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
