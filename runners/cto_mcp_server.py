"""Standalone stdio MCP server exposing CTO org tools to Claude Code CLI.

Run via:
    python -m runners.cto_mcp_server

Registered in config/cto.mcp.json as server "org" — tools become
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
from lib import recall as recall_lib
from lib import reflect as reflect_lib
from lib import toon
from lib.config import get_project, projects
from lib.logger import get_logger
from lib.notify import info, warn
from lib.task_ownership import is_mine as _is_mine, foreign_msg as _foreign_msg
from tools import wiki as wiki_tools
from tools.delegate import delegate_task as do_delegate, delegate_parallel
from tools.git_ops import merge_task as do_merge
from tools.worktree import diff_summary, diff_full

ROLE = "cto"
log = get_logger(ROLE, stdout=False)

mcp = FastMCP("org")


@mcp.tool()
def wiki_read(path: str) -> str:
    """Read a wiki page. Namespaced ("org:x.md") or unprefixed (default namespace)."""
    try:
        return wiki_tools.wiki_read(path)[:8000]
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def wiki_list(prefix: str = "") -> str:
    """List wiki pages under an optional prefix."""
    try:
        pages = wiki_tools.wiki_list(prefix)
        return toon.encode(pages[:200])
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def wiki_search(query: str) -> str:
    """Grep wiki for a query string."""
    try:
        hits = wiki_tools.wiki_search(query)
        return toon.encode(hits)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def wiki_write(path: str, content: str, message: str = "") -> str:
    """Create or update a wiki page. CTO only. Auto-commits to wiki git repo."""
    try:
        return wiki_tools.wiki_write(path, content, role=ROLE, message=message or None)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def create_task(
    project: str,
    role: str,
    title: str,
    description: str,
    depends_on: str = "",
    touches: str = "",
) -> str:
    """Create a task in the queue. Returns task_id.

    depends_on accepts JSON array string or comma-separated task_ids.
    touches accepts JSON array string or comma-separated repo-relative paths
    that this task is expected to modify. Used for collision detection: a
    delegate_task call with overlapping touches against an in-flight task is
    blocked and the task is marked status='conflict'.
    """
    deps: list[str] = []
    if depends_on:
        try:
            deps = json.loads(depends_on)
        except Exception:
            deps = [s.strip() for s in depends_on.split(",") if s.strip()]
    paths: list[str] = []
    if touches:
        try:
            paths = json.loads(touches)
        except Exception:
            paths = [s.strip() for s in touches.split(",") if s.strip()]
    tid = db.create_task(
        project=project,
        role=role,
        title=title,
        description=description,
        depends_on=deps,
        touches=paths,
        owner_cto=os.environ.get("CTO_SESSION_ID"),
    )
    info(f"task created {tid} → {role} on {project} touches={paths}")
    return tid


@mcp.tool()
def check_collisions(project: str, touches: str) -> str:
    """Preview path collisions before creating a task.

    touches accepts JSON array string or comma-separated paths. Returns JSON
    list of in-flight tasks (status pending/in_progress/rate_limited/conflict)
    whose touches intersect the supplied paths. Empty list = safe to delegate.
    """
    try:
        paths = json.loads(touches)
    except Exception:
        paths = [s.strip() for s in touches.split(",") if s.strip()]
    hits = db.find_conflicts(project, paths)
    return toon.encode(hits)


@mcp.tool()
async def delegate_task(task_id: str) -> str:
    """Spawn a DEV subprocess to execute a task. Blocks until DEV reports back."""
    t = db.get_task(task_id)
    if t and not _is_mine(t):
        return _foreign_msg(t)
    result = await do_delegate(task_id)
    return toon.encode(result)[:6000]


@mcp.tool()
async def delegate_parallel_tasks(task_ids: str) -> str:
    """Delegate multiple tasks concurrently (max 3 at once). task_ids is JSON array."""
    ids = json.loads(task_ids)
    results = await delegate_parallel(ids, max_concurrent=3)
    return toon.encode(results)[:8000]


@mcp.tool()
def get_task(task_id: str) -> str:
    """Read a task row. Includes both `report` (DEV completion summary) and
    `delegate_log` (runner-level collision/spawn errors)."""
    t = db.get_task(task_id)
    return toon.encode(t)[:6000]


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
def merge_task(task_id: str, override_touches_check: bool = False) -> str:
    """Merge a task's branch into project default branch + push. CTO only.

    If the task declared `touches`, files changed outside that declaration
    block the merge (result.touches_violation=true, branch/worktree kept,
    status set back to review) — inspect with review_diff, then retry with
    override_touches_check=True once you've confirmed the extra files are
    legitimate.
    """
    t = db.get_task(task_id)
    if t and not _is_mine(t):
        return _foreign_msg(t)
    result = do_merge(task_id, role=ROLE, override_touches_check=override_touches_check)
    return toon.encode(result)


@mcp.tool()
def reopen_task(task_id: str, feedback: str) -> str:
    """Mark a task pending again with feedback. Increments iteration counter."""
    t = db.get_task(task_id)
    if not t:
        return "not found"
    if not _is_mine(t):
        return _foreign_msg(t)
    new_desc = f"{t['description']}\n\n## CTO Feedback (iter {t['iteration']+1})\n{feedback}"
    db.update_status(
        task_id,
        "pending",
        description=new_desc,
        iteration=t["iteration"] + 1,
        assigned_agent=None,
        actor="cto",
        force=True,  # reopen is an intentional resurrection (may target done)
    )
    warn(f"reopened {task_id} (iter {t['iteration']+1})")
    return "reopened"


@mcp.tool()
def list_projects() -> str:
    """List all known projects from config."""
    return toon.encode(list(projects().values()))


@mcp.tool()
def stats() -> str:
    """Get task counts by status."""
    return toon.encode(db.stats())


@mcp.tool()
def recall(query: str, project: str = "", limit: int = 5) -> str:
    """Recall relevant PAST org work for a free-text query.

    Ranks prior tasks by term overlap and returns a compact digest of each
    match — final status, merge sha, branch, and a gist of the DEV report —
    read back from the task/event log (which is otherwise write-only). Call
    this BEFORE planning or creating tasks to avoid relighting work already
    done. Read-only. Optionally scope to one project key."""
    return recall_lib.recall_text(query, project=project or None, limit=limit)


@mcp.tool()
def reflect(days: int = 7, project: str = "") -> str:
    """Reflect on recent org state — what merged, what's open/stuck, and any
    recurring failure signal over the last `days`. Read-side companion to
    recall(): recall answers 'what did we do about X', reflect answers 'where
    do things stand now'. Call at session start for situational awareness.
    Read-only; surfaces patterns for you to judge, never auto-acts."""
    return reflect_lib.reflect_text(days=days, project=project or None)


@mcp.tool()
async def revert_task_tool(task_id: str, force: bool = False) -> str:
    """Revert a previously merged task. CTO only.

    Refuses if task status is not merged/done. Refuses if merge SHA is
    >RVR_DEPTH_LIMIT commits behind HEAD unless force=True.

    Re-fires auto_deploy on success if the project has it enabled and
    not requires_ceo_ack.
    """
    t = db.get_task(task_id)
    if t and not _is_mine(t):
        return _foreign_msg(t)
    from tools.revert_task import revert_task
    return toon.encode(revert_task(task_id, force=force))


if __name__ == "__main__":
    db.init()
    mcp.run()
