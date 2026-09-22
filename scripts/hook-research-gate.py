#!/usr/bin/env python3
"""PreToolUse hook — no web search before the research cache is checked.

ADR 0028 §6 (session cto-0e8d80b8, 2026-09-22): `Agents/Wikis/research/`
(today `/Users/gob/MoonieXHQ/Agents/Wikis/research/`, contract in its README) is where
every answered question lives, dated with `refresh_after`. An agent must
search it BEFORE any web search, and write the file after. Prose alone did
not stop sessions re-searching the internet — memory said "put the rule in
the tool, not the doc" (feedback_put_the_rule_in_the_tool_not_the_doc.md).

Arms (creates ~/.gateguard/research-gate-<session>.ok) when the session:
  - calls mcp__org__wiki_search (any query — it greps every namespace), OR
  - Reads/Greps a path containing "/research/" or "RESEARCH-INDEX.md", OR
  - runs a Bash command whose text mentions "research/" or "RESEARCH-INDEX".
Stays armed 12 hours, then re-arms — the cache changes daily.

Blocks (exit 2, message to the model) WebSearch/WebFetch while unarmed.
Passes every other call through silently (exit 0) — those tool calls only
ever arm the gate here, never trip it.

Escape hatch, for genuine repair only: RESEARCH_GATE=off.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ARMED_FOR_S = 12 * 3600
BLOCKED_TOOLS = {"WebSearch", "WebFetch"}


def _marker_path(sid: str) -> Path:
    return Path.home() / ".gateguard" / f"research-gate-{sid}.ok"


def _arms(tool: str, inp: dict) -> bool:
    if tool == "mcp__org__wiki_search":
        return True
    if tool in ("Read", "Grep"):
        path = str(inp.get("file_path") or inp.get("path") or "")
        return "/research/" in path or "RESEARCH-INDEX.md" in path
    if tool == "Bash":
        command = str(inp.get("command") or "")
        return "research/" in command or "RESEARCH-INDEX" in command
    return False


def main() -> int:
    try:
        ev = json.load(sys.stdin)
    except Exception:
        return 0
    if os.environ.get("RESEARCH_GATE", "").strip().lower() == "off":
        return 0

    sid = str(ev.get("session_id") or "nosession")
    tool = str(ev.get("tool_name") or "")
    inp = ev.get("tool_input") or {}
    marker = _marker_path(sid)

    if _arms(tool, inp):
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(str(time.time()))
        return 0

    if tool not in BLOCKED_TOOLS:
        return 0

    if marker.exists():
        try:
            armed_at = float(marker.read_text().strip() or 0)
        except ValueError:
            armed_at = 0.0
        if time.time() - armed_at < ARMED_FOR_S:
            return 0

    sys.stderr.write(
        "BLOCKED — research cache rule (ADR 0028 §6): check the cache before "
        "any web search.\n"
        "First: mcp__org__wiki_search (namespace mooniex:) on `research/`, or "
        "Read research/RESEARCH-INDEX.md. A fresh hit (refresh_after in the "
        "future) answers it — no web search needed.\n"
        "After you do web search: WRITE the answer as a research file per "
        "research/README.md (one question, one file, frontmatter incl. "
        "refresh_after). Then retry this exact call.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
