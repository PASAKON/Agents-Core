#!/usr/bin/env python3
"""Call one MCP tool directly over stdio — no model, no tokens.

Why this exists: the model-mediated borrow (scripts/mcp-borrow.sh without
--raw) spends a whole Claude turn on questions that have exactly one right
answer. Worse, it can spend it and still be wrong — the bench that motivated
this file asked "how many open todos" and collected 50, 53, 7 and 193 from
two models over two runs, when the answer was flatly 193 and a direct call
returns it in ~2s for zero tokens.

So: if the question is "what does this tool return", speak the protocol.
Reserve the model for questions that actually need judgment (pick the best
reference image, summarize this thread), where a plausible-but-wrong answer
is a known cost of the task rather than a defect.

The server's command/args/env come from cxo_mcp_config._build(), so a raw
call runs the same binary with the same flags and the same guards a role
launch would give it — including supabase's --read-only.

Exit code caveat: a nonzero exit means the *protocol* failed (server missing,
timeout, JSON-RPC error, or an MCP `isError` result). Some servers instead
report failures as ordinary content — the supabase one returns
{"error": {...}} text with no isError — so exit 0 means "the server answered",
not "the call succeeded". Read the payload.

Usage:
    python3 scripts/lib/mcp_call.py --server lungnote --root "$ROOT" \
        --tool list_todos --args '{"include_done": false, "limit": 500}'
    python3 scripts/lib/mcp_call.py --server supabase --root "$ROOT" --list
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cxo_mcp_config import _build  # noqa: E402

PROTOCOL_VERSION = "2024-11-05"


def _env_for(entry: dict) -> dict[str, str]:
    """Server env with ${VAR} resolved, the way Claude Code resolves it.

    The config keeps secrets as unexpanded placeholders on purpose (see
    cxo_mcp_config), so they have to be expanded here against the calling
    shell's env. Values are only ever handed to the child process.
    """
    env = os.environ.copy()
    for key, raw in (entry.get("env") or {}).items():
        env[key] = os.path.expandvars(raw)
    return env


def call(server: str, root: str, tool: str | None, args: dict, timeout: int) -> int:
    entry = _build(server, root)
    if entry is None:
        print(
            f"mcp_call: server '{server}' is not installed on this box "
            "(cxo_mcp_config found no command for it)",
            file=sys.stderr,
        )
        return 3

    want_list = tool is None
    msgs: list[dict] = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "mcp-borrow", "version": "1"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list" if want_list else "tools/call",
            "params": {} if want_list else {"name": tool, "arguments": args},
        },
    ]

    try:
        proc = subprocess.run(
            [entry["command"], *entry.get("args", [])],
            input="\n".join(json.dumps(m) for m in msgs) + "\n",
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=entry.get("cwd") or root,
            env=_env_for(entry),
        )
    except subprocess.TimeoutExpired:
        print(f"mcp_call: '{server}' did not answer within {timeout}s", file=sys.stderr)
        return 4

    # Servers are free to log to stdout around the protocol, so find the frame
    # answering id=2 instead of assuming the last line is it.
    reply = None
    for line in proc.stdout.splitlines():
        try:
            frame = json.loads(line)
        except ValueError:
            continue
        if frame.get("id") == 2:
            reply = frame
            break

    if reply is None:
        detail = proc.stderr.strip()[:400]
        print(
            f"mcp_call: no response frame from '{server}'"
            + (f" — stderr: {detail}" if detail else ""),
            file=sys.stderr,
        )
        return 5

    if "error" in reply:
        print(
            f"mcp_call: {server} returned an error: {json.dumps(reply['error'])}",
            file=sys.stderr,
        )
        return 6

    result = reply.get("result") or {}
    if want_list:
        for t in result.get("tools", []):
            print(t.get("name", "?"))
        return 0

    # A tool result is a content array; text blocks are the payload. Non-text
    # blocks (images) are named rather than dumped as bytes.
    for block in result.get("content", []):
        if block.get("type") == "text":
            print(block.get("text", ""))
        else:
            print(f"<{block.get('type', 'unknown')} block omitted>")
    return 7 if result.get("isError") else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--tool", default="")
    ap.add_argument("--args", default="{}", help="JSON object of tool arguments")
    ap.add_argument("--list", action="store_true", help="list the server's tools and exit")
    ap.add_argument("--timeout", type=int, default=120)
    a = ap.parse_args()
    if not a.list and not a.tool:
        ap.error("one of --tool or --list is required")
    try:
        args = json.loads(a.args)
    except ValueError as exc:
        print(f"mcp_call: --args is not valid JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(args, dict):
        print("mcp_call: --args must be a JSON object", file=sys.stderr)
        return 2
    return call(a.server, a.root, None if a.list else a.tool, args, a.timeout)


if __name__ == "__main__":
    sys.exit(main())
