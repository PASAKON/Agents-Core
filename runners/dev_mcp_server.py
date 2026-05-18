"""Stdio MCP server for DEV sessions running inside Claude Code TUI.

Reads DEV_TASK_ID + DEV_ROLE env to know which task it belongs to.
Exposes read-only wiki tools + submit_report (writes back to DB).

Registered in config/dev.mcp.json as server "org" — tools become
mcp__org__<tool_name> inside Claude Code.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP

from lib import db
from lib.logger import get_logger
from lib.notify import info
from tools import wiki as wiki_tools
from tools.gh_issue import create_issue as gh_create_issue

TASK_ID = os.environ.get("DEV_TASK_ID", "")
ROLE = os.environ.get("DEV_ROLE", "dev")
log = get_logger(ROLE, TASK_ID or None, stdout=False)

mcp = FastMCP("org")


@mcp.tool()
def wiki_read(path: str) -> str:
    """Read a wiki page from /Users/gob/Projects/LLMs/."""
    try:
        return wiki_tools.wiki_read(path)[:8000]
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def wiki_list(prefix: str = "") -> str:
    """List wiki pages under an optional prefix."""
    return "\n".join(wiki_tools.wiki_list(prefix)[:200])


@mcp.tool()
def wiki_search(query: str) -> str:
    """Grep wiki for a query string."""
    return json.dumps(wiki_tools.wiki_search(query), indent=2)


@mcp.tool()
def submit_report(report: str) -> str:
    """Submit final task report. Sets task status=review for CTO review.

    Call this exactly once when work on the task is complete. The report
    should follow the role's REQUIRED report format (files changed, tests
    run, blockers). After calling this the DEV session can be closed.
    """
    if not TASK_ID:
        return "ERROR: DEV_TASK_ID env var not set"
    db.update_status(TASK_ID, "review", report=report, actor=ROLE)
    summary_line = report.strip().splitlines()[0][:200] if report.strip() else "(empty)"
    info(f"submitted report — {summary_line}")
    log.info(f"REPORT submitted ({len(report)} chars)")
    return f"OK — task {TASK_ID} status=review. CTO will review and merge."


@mcp.tool()
def file_blocker_issue(title: str, body: str) -> str:
    """File a GitHub issue on the current project so a blocker is durable.

    MANDATORY any time you cannot proceed (missing secret, ambiguous spec,
    broken dependency, external service down). The issue lets work resume
    after a closed tab, sleeping mac, or dropped network — without it the
    blocker dies with the session.

    Body is auto-prefixed with task id + worktree path so a future agent
    can reattach. Returns the issue URL, which is also logged so the CTO
    sees it.
    """
    if not TASK_ID:
        return "ERROR: DEV_TASK_ID env var not set"
    task = db.get_task(TASK_ID)
    if not task:
        return f"ERROR: task {TASK_ID} not found"
    project_key = task["project"]
    worktree = task.get("worktree") or "(no worktree)"
    enriched_body = (
        f"**Task**: `{TASK_ID}`\n"
        f"**Role**: `{ROLE}`\n"
        f"**Worktree**: `{worktree}`\n"
        f"**Branch**: `{task.get('branch') or '(none)'}`\n\n"
        "---\n\n"
        f"{body}"
    )
    try:
        url = gh_create_issue(project_key, title, enriched_body,
                              labels=["blocker", "agent"])
    except Exception as e:
        info(f"file_blocker_issue FAILED: {e}")
        return f"ERROR: {e}"
    info(f"blocker issue filed: {url}")
    return url


@mcp.tool()
def dev_message(text: str) -> str:
    """Broadcast a short progress message to the CTO log (one line).

    Use sparingly to surface meaningful checkpoints — e.g. "reading wiki",
    "found N test failures", "blocker: missing API key". Each call appends
    one prefixed line to cto.log which the CTO surfaces in chat.

    NOT a replacement for submit_report — final hand-off must still use
    submit_report.
    """
    if not TASK_ID:
        return "ERROR: DEV_TASK_ID env var not set"
    info(text.strip().splitlines()[0][:300] if text.strip() else "(empty)")
    return "ack"


if __name__ == "__main__":
    db.init()
    mcp.run()
