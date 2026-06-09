"""CTO orchestrator. Reads CEO request, breaks into tasks, delegates, reviews, merges."""
from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
    create_sdk_mcp_server,
    tool,
)

import os

from lib import db
from lib.config import get_project, projects, role as get_role
from lib.db import register_cxo_session
from lib.logger import get_logger
from lib.notify import info, success, error, warn
from tools import wiki as wiki_tools
from tools.delegate import delegate_task as do_delegate, delegate_parallel
from tools.git_ops import merge_task as do_merge
from tools.worktree import diff_summary, diff_full

ROOT = Path(__file__).resolve().parent.parent
ROLE = "cto"
log = get_logger(ROLE)


# --- Tool definitions (Claude SDK MCP) ---

@tool("wiki_read", "Read a wiki page from /Users/gob/Projects/LLMs/", {"path": str})
async def t_wiki_read(args):
    try:
        text = wiki_tools.wiki_read(args["path"])
        return {"content": [{"type": "text", "text": text[:8000]}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"ERROR: {e}"}], "isError": True}


@tool("wiki_list", "List wiki pages under an optional prefix.", {"prefix": str})
async def t_wiki_list(args):
    pages = wiki_tools.wiki_list(args.get("prefix", ""))
    return {"content": [{"type": "text", "text": "\n".join(pages[:200])}]}


@tool("wiki_search", "Grep wiki for a query string.", {"query": str})
async def t_wiki_search(args):
    hits = wiki_tools.wiki_search(args["query"])
    return {"content": [{"type": "text", "text": json.dumps(hits, indent=2)}]}


@tool(
    "wiki_write",
    "Create or update a wiki page. CTO only. Auto-commits to wiki git repo.",
    {"path": str, "content": str, "message": str},
)
async def t_wiki_write(args):
    result = wiki_tools.wiki_write(
        args["path"], args["content"],
        role=ROLE, message=args.get("message") or None,
    )
    return {"content": [{"type": "text", "text": result}]}


@tool(
    "create_task",
    "Create a task. Returns task_id. depends_on=JSON array of task_ids "
    "(serialize work). touches=JSON array of repo-relative paths the task "
    "will modify (used for collision detection — delegate is blocked if "
    "another in-flight task already touches the same path).",
    {"project": str, "role": str, "title": str, "description": str,
     "depends_on": str, "touches": str},
)
async def t_create_task(args):
    deps = []
    raw = args.get("depends_on") or ""
    if raw:
        try:
            deps = json.loads(raw)
        except Exception:
            deps = [s.strip() for s in raw.split(",") if s.strip()]
    paths = []
    raw_t = args.get("touches") or ""
    if raw_t:
        try:
            paths = json.loads(raw_t)
        except Exception:
            paths = [s.strip() for s in raw_t.split(",") if s.strip()]
    tid = db.create_task(
        project=args["project"],
        role=args["role"],
        title=args["title"],
        description=args["description"],
        depends_on=deps,
        touches=paths,
    )
    info(f"task created {tid} → {args['role']} on {args['project']} touches={paths}")
    return {"content": [{"type": "text", "text": tid}]}


@tool(
    "check_collisions",
    "Preview path collisions before creating/delegating. Returns JSON list "
    "of in-flight tasks whose touches intersect the supplied paths. Empty "
    "list = safe to delegate.",
    {"project": str, "touches": str},
)
async def t_check_collisions(args):
    raw = args.get("touches") or ""
    try:
        paths = json.loads(raw)
    except Exception:
        paths = [s.strip() for s in raw.split(",") if s.strip()]
    hits = db.find_conflicts(args["project"], paths)
    return {"content": [{"type": "text", "text": json.dumps(hits, indent=2)}]}


@tool(
    "delegate_task",
    "Spawn a DEV subprocess to execute a task. Blocks until DEV reports back. Returns final task state JSON.",
    {"task_id": str},
)
async def t_delegate(args):
    result = await do_delegate(args["task_id"])
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)[:6000]}]}


@tool(
    "delegate_parallel",
    "Delegate multiple tasks concurrently (max 3 at once). task_ids is JSON array.",
    {"task_ids": str},
)
async def t_delegate_parallel(args):
    ids = json.loads(args["task_ids"])
    results = await delegate_parallel(ids, max_concurrent=3)
    return {"content": [{"type": "text", "text": json.dumps(results, indent=2, default=str)[:8000]}]}


@tool("get_task", "Read a task row including report.", {"task_id": str})
async def t_get_task(args):
    t = db.get_task(args["task_id"])
    return {"content": [{"type": "text", "text": json.dumps(t, indent=2, default=str)[:6000]}]}


@tool(
    "review_diff",
    "Get the diff of a task's worktree branch vs project default branch.",
    {"task_id": str, "full": bool},
)
async def t_review_diff(args):
    t = db.get_task(args["task_id"])
    if not t or not t.get("worktree"):
        return {"content": [{"type": "text", "text": "no worktree"}], "isError": True}
    base = get_project(t["project"])["default_branch"]
    if args.get("full"):
        out = diff_full(t["worktree"], base)
    else:
        out = diff_summary(t["worktree"], base)
    return {"content": [{"type": "text", "text": out[:8000]}]}


@tool(
    "merge_task",
    "Merge a task's branch into project default branch + push (if project.auto_push). CTO only.",
    {"task_id": str},
)
async def t_merge(args):
    result = do_merge(args["task_id"], role=ROLE)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}]}


@tool(
    "reopen_task",
    "Mark a task as pending again with feedback for the DEV. Increments iteration counter.",
    {"task_id": str, "feedback": str},
)
async def t_reopen(args):
    t = db.get_task(args["task_id"])
    if not t:
        return {"content": [{"type": "text", "text": "not found"}], "isError": True}
    new_desc = f"{t['description']}\n\n## CTO Feedback (iter {t['iteration']+1})\n{args['feedback']}"
    db.update_status(args["task_id"], "pending",
                     description=new_desc,
                     iteration=t["iteration"] + 1,
                     assigned_agent=None,
                     actor="cto")
    warn(f"reopened {args['task_id']} (iter {t['iteration']+1})")
    return {"content": [{"type": "text", "text": "reopened"}]}


@tool("list_projects", "List all known projects from config.", {})
async def t_list_projects(args):
    return {"content": [{"type": "text", "text": json.dumps(list(projects().values()), indent=2)}]}


@tool("stats", "Get task counts by status.", {})
async def t_stats(args):
    return {"content": [{"type": "text", "text": json.dumps(db.stats())}]}


# --- CTO entrypoint ---

def _system_prompt() -> str:
    return (ROOT / "roles" / "cto.md").read_text()


def _cleanup_zombies() -> None:
    script = ROOT / "scripts" / "cleanup-zombies.sh"
    try:
        r = subprocess.run(
            ["bash", str(script)], capture_output=True, text=True, timeout=10
        )
        log.info(r.stdout.strip() or "cleanup-zombies: no output")
    except Exception as exc:
        log.debug(f"cleanup-zombies skipped: {exc}")


async def run(ceo_request: str) -> str:
    log.info(f"CEO request: {ceo_request[:200]}")
    info(f"CTO received CEO request")
    _cleanup_zombies()
    _sid = os.environ.get("CXO_SESSION_ID") or os.environ.get("CTO_SESSION_ID", "")
    if _sid:
        try:
            register_cxo_session("cto", _sid)
        except Exception:
            pass

    server = create_sdk_mcp_server(
        name="org-cto",
        version="1.0.0",
        tools=[
            t_wiki_read, t_wiki_list, t_wiki_search, t_wiki_write,
            t_create_task, t_check_collisions, t_delegate, t_delegate_parallel,
            t_get_task, t_review_diff, t_merge, t_reopen,
            t_list_projects, t_stats,
        ],
    )

    options = ClaudeAgentOptions(
        model=get_role("cto")["model"],
        fallback_model=get_role("cto").get("fallback_model"),
        effort="max",
        system_prompt=_system_prompt(),
        permission_mode="acceptEdits",
        mcp_servers={"org": server},
        allowed_tools=[
            "mcp__org__wiki_read", "mcp__org__wiki_list", "mcp__org__wiki_search",
            "mcp__org__wiki_write", "mcp__org__create_task",
            "mcp__org__check_collisions",
            "mcp__org__delegate_task", "mcp__org__delegate_parallel",
            "mcp__org__get_task", "mcp__org__review_diff",
            "mcp__org__merge_task", "mcp__org__reopen_task",
            "mcp__org__list_projects", "mcp__org__stats",
            "Read", "Grep", "Glob",
        ],
        cwd=str(ROOT),
    )

    final = []
    async with ClaudeSDKClient(options=options) as client:
        await client.query(ceo_request)
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        log.info(f"CTO: {block.text[:500]}")
                        final.append(block.text)

    result = "\n".join(final)
    success("CTO done")
    return result


if __name__ == "__main__":
    import sys
    request = " ".join(sys.argv[1:]) or "list known projects and their git remotes"
    print(asyncio.run(run(request)))
