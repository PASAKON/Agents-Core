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

Usage:
    python3 scripts/lib/cxo_mcp_config.py --role cto --root "$ROOT" \
        --out /tmp/cto-mcp-XXXX.json

Env overrides (no code edit needed):
    CXO_EXTRA_MCP=meigen,meta-ads-135   add servers to this role
    CXO_SKIP_MCP=supabase               drop servers from this role
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
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
BASE_SERVERS = ("org", "lungnote", "mooniex-coord")
ROLE_SERVERS: dict[str, tuple[str, ...]] = {
    "cto": BASE_SERVERS + ("supabase",),
    "cfo": BASE_SERVERS + ("supabase",),
    "cgo": BASE_SERVERS + ("supabase", "meta-ads-135"),
    "cmo": BASE_SERVERS + ("meta-ads-135", "meigen"),
}


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
        # Left unexpanded on purpose — Claude Code resolves ${VAR} against the
        # session env, which is where .claude/settings.local.json puts the PAT.
        return {
            "command": "mcp-server-supabase",
            "args": [
                f"--project-ref={SUPABASE_PROJECT_REF}",
                "--features=database",
            ],
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


def _names_for(role: str) -> list[str]:
    names = list(ROLE_SERVERS.get(role, BASE_SERVERS))
    for extra in os.environ.get("CXO_EXTRA_MCP", "").split(","):
        extra = extra.strip()
        if extra and extra not in names:
            names.append(extra)
    skip = {s.strip() for s in os.environ.get("CXO_SKIP_MCP", "").split(",") if s.strip()}
    return [n for n in names if n not in skip]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    servers: dict[str, dict] = {}
    missing: list[str] = []
    for name in _names_for(args.role):
        entry = _build(name, args.root)
        if entry is None:
            missing.append(name)
        else:
            servers[name] = entry

    if "org" not in servers:
        print(
            f"cxo_mcp_config: org MCP server unavailable "
            f"({args.root}/.venv/bin/python missing) — refusing to launch",
            file=sys.stderr,
        )
        return 1

    Path(args.out).write_text(json.dumps({"mcpServers": servers}, indent=2) + "\n")
    print(
        f"cxo_mcp_config: role={args.role} servers={','.join(servers)}"
        + (f" skipped(not installed)={','.join(missing)}" if missing else ""),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
