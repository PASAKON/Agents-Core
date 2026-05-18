"""Standalone stdio MCP server exposing CTO org tools to Claude Code CLI.

Run via:
    python -m runners.cto_mcp_server

Registered in config/cto.mcp.json as server "org" — tools become
mcp__org__<tool_name> inside Claude Code.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP

from lib import db
from lib.config import get_project, projects
from lib.logger import get_logger
from lib.notify import info, warn
from tools import wiki as wiki_tools
from tools.delegate import delegate_task as do_delegate, delegate_parallel
from tools.git_ops import merge_task as do_merge
from tools.worktree import diff_summary, diff_full

ROLE = "cto"
log = get_logger(ROLE, stdout=False)

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
    pages = wiki_tools.wiki_list(prefix)
    return "\n".join(pages[:200])


@mcp.tool()
def wiki_search(query: str) -> str:
    """Grep wiki for a query string."""
    hits = wiki_tools.wiki_search(query)
    return json.dumps(hits, indent=2)


@mcp.tool()
def wiki_write(path: str, content: str, message: str = "") -> str:
    """Create or update a wiki page. CTO only. Auto-commits to wiki git repo."""
    return wiki_tools.wiki_write(path, content, role=ROLE, message=message or None)


@mcp.tool()
def create_task(
    project: str,
    role: str,
    title: str,
    description: str,
    depends_on: str = "",
) -> str:
    """Create a task in the queue. Returns task_id.

    depends_on accepts JSON array string or comma-separated task_ids.
    """
    deps: list[str] = []
    if depends_on:
        try:
            deps = json.loads(depends_on)
        except Exception:
            deps = [s.strip() for s in depends_on.split(",") if s.strip()]
    tid = db.create_task(
        project=project,
        role=role,
        title=title,
        description=description,
        depends_on=deps,
    )
    info(f"task created {tid} → {role} on {project}")
    return tid


@mcp.tool()
async def delegate_task(task_id: str) -> str:
    """Spawn a DEV subprocess to execute a task. Blocks until DEV reports back."""
    result = await do_delegate(task_id)
    return json.dumps(result, indent=2, default=str)[:6000]


@mcp.tool()
async def delegate_parallel_tasks(task_ids: str) -> str:
    """Delegate multiple tasks concurrently (max 3 at once). task_ids is JSON array."""
    ids = json.loads(task_ids)
    results = await delegate_parallel(ids, max_concurrent=3)
    return json.dumps(results, indent=2, default=str)[:8000]


@mcp.tool()
def get_task(task_id: str) -> str:
    """Read a task row including report."""
    t = db.get_task(task_id)
    return json.dumps(t, indent=2, default=str)[:6000]


@mcp.tool()
def review_diff(task_id: str, full: bool = False) -> str:
    """Get the diff of a task's worktree branch vs project default branch."""
    t = db.get_task(task_id)
    if not t or not t.get("worktree"):
        return "no worktree"
    base = get_project(t["project"])["default_branch"]
    out = diff_full(t["worktree"], base) if full else diff_summary(t["worktree"], base)
    return out[:8000]


@mcp.tool()
def merge_task(task_id: str) -> str:
    """Merge a task's branch into project default branch + push. CTO only."""
    result = do_merge(task_id, role=ROLE)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def reopen_task(task_id: str, feedback: str) -> str:
    """Mark a task pending again with feedback. Increments iteration counter."""
    t = db.get_task(task_id)
    if not t:
        return "not found"
    new_desc = f"{t['description']}\n\n## CTO Feedback (iter {t['iteration']+1})\n{feedback}"
    db.update_status(
        task_id,
        "pending",
        description=new_desc,
        iteration=t["iteration"] + 1,
        assigned_agent=None,
        actor="cto",
    )
    warn(f"reopened {task_id} (iter {t['iteration']+1})")
    return "reopened"


@mcp.tool()
def list_projects() -> str:
    """List all known projects from config."""
    return json.dumps(list(projects().values()), indent=2)


@mcp.tool()
def stats() -> str:
    """Get task counts by status."""
    return json.dumps(db.stats())


if __name__ == "__main__":
    db.init()
    mcp.run()
