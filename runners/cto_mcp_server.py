"""Standalone stdio MCP server exposing CTO org tools to Claude Code CLI.

Run via:
    python -m runners.cto_mcp_server

Registered in config/cto.mcp.json as server "org" — tools become
mcp__org__<tool_name> inside Claude Code.

Every tool below is a thin @mcp.tool() stub: arg parsing, response
formatting, the cross-CTO ownership gate and error handling all live once
in lib/org_tools_registry.py (registry.dispatch/dispatch_sync). Each stub
keeps its own real Python signature (name, param names/types/defaults,
sync-vs-async) — FastMCP derives the JSON schema by introspecting that
signature (see mcp.server.fastmcp.utilities.func_metadata), so there's no
way around a per-tool function existing; the description text itself is
NOT duplicated here, it's pulled from the registry at decoration time.
"""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP

from lib import db
from lib import org_tools_registry as reg
from lib.logger import get_logger
# Re-exported for scripts/test_org_tools_registry.py and
# scripts/test_owner_cto_routing.py, which patch/call these directly as
# module attributes of this file — not used by the stubs below anymore
# (registry.py owns the real calls into them).
from lib.task_ownership import is_mine as _is_mine, foreign_msg as _foreign_msg  # noqa: F401
from tools.delegate import delegate_task as do_delegate, delegate_parallel  # noqa: F401
from tools.dev_reap import close_dev as do_close_dev  # noqa: F401
from tools.git_ops import merge_task as do_merge  # noqa: F401

ROLE = "cto"
log = get_logger(ROLE, stdout=False)

mcp = FastMCP("org")


@mcp.tool(description=reg.BY_NAME["wiki_read"].description)
def wiki_read(path: str) -> str:
    return reg.dispatch_sync("wiki_read", path=path)


@mcp.tool(description=reg.BY_NAME["wiki_list"].description)
def wiki_list(prefix: str = "") -> str:
    return reg.dispatch_sync("wiki_list", prefix=prefix)


@mcp.tool(description=reg.BY_NAME["wiki_search"].description)
def wiki_search(query: str) -> str:
    return reg.dispatch_sync("wiki_search", query=query)


@mcp.tool(description=reg.BY_NAME["wiki_write"].description)
def wiki_write(path: str, content: str, message: str = "") -> str:
    return reg.dispatch_sync("wiki_write", path=path, content=content, message=message)


@mcp.tool(description=reg.BY_NAME["create_task"].description)
def create_task(
    project: str,
    role: str,
    title: str,
    description: str,
    depends_on: str = "",
    touches: str = "",
) -> str:
    return reg.dispatch_sync(
        "create_task", project=project, role=role, title=title,
        description=description, depends_on=depends_on, touches=touches,
    )


@mcp.tool(description=reg.BY_NAME["check_collisions"].description)
def check_collisions(project: str, touches: str) -> str:
    return reg.dispatch_sync("check_collisions", project=project, touches=touches)


@mcp.tool(description=reg.BY_NAME["delegate_task"].description)
async def delegate_task(task_id: str) -> str:
    return await reg.dispatch("delegate_task", task_id=task_id)


@mcp.tool(description=reg.BY_NAME["delegate_parallel_tasks"].description)
async def delegate_parallel_tasks(task_ids: str) -> str:
    return await reg.dispatch("delegate_parallel_tasks", task_ids=task_ids)


@mcp.tool(description=reg.BY_NAME["get_task"].description)
def get_task(task_id: str) -> str:
    return reg.dispatch_sync("get_task", task_id=task_id)


@mcp.tool(description=reg.BY_NAME["review_diff"].description)
def review_diff(task_id: str, full: bool = False) -> str:
    return reg.dispatch_sync("review_diff", task_id=task_id, full=full)


@mcp.tool(description=reg.BY_NAME["merge_task"].description)
def merge_task(task_id: str, override_touches_check: bool = False) -> str:
    return reg.dispatch_sync(
        "merge_task", task_id=task_id, override_touches_check=override_touches_check,
    )


@mcp.tool(description=reg.BY_NAME["close_dev"].description)
def close_dev(task_id: str, reason: str = "cto: manual close") -> str:
    return reg.dispatch_sync("close_dev", task_id=task_id, reason=reason)


@mcp.tool(description=reg.BY_NAME["reopen_task"].description)
def reopen_task(task_id: str, feedback: str) -> str:
    return reg.dispatch_sync("reopen_task", task_id=task_id, feedback=feedback)


@mcp.tool(description=reg.BY_NAME["list_projects"].description)
def list_projects() -> str:
    return reg.dispatch_sync("list_projects")


@mcp.tool(description=reg.BY_NAME["stats"].description)
def stats() -> str:
    return reg.dispatch_sync("stats")


@mcp.tool(description=reg.BY_NAME["recall"].description)
def recall(query: str, project: str = "", limit: int = 5) -> str:
    return reg.dispatch_sync("recall", query=query, project=project, limit=limit)


@mcp.tool(description=reg.BY_NAME["reflect"].description)
def reflect(days: int = 7, project: str = "") -> str:
    return reg.dispatch_sync("reflect", days=days, project=project)


@mcp.tool(description=reg.BY_NAME["revert_task_tool"].description)
async def revert_task_tool(task_id: str, force: bool = False) -> str:
    return await reg.dispatch("revert_task_tool", task_id=task_id, force=force)


if __name__ == "__main__":
    db.init()
    mcp.run()
