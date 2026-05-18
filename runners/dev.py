"""Generic DEV runner. Loads role prompt + task context, runs Claude SDK in worktree.

Invoked as: python -m runners.dev <role> <task_id>
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
    create_sdk_mcp_server,
    tool,
)

from lib import db
from lib.config import get_project, role as get_role
from lib.logger import get_logger
from lib.notify import info, error
from tools import wiki as wiki_tools

ROOT = Path(__file__).resolve().parent.parent


def _role_prompt(role: str) -> str:
    path = ROOT / "roles" / f"{role}.md"
    return path.read_text()


def _build_tools(role: str):
    """DEVs get read-only wiki + read-only project access. They write only in cwd (their worktree)."""

    @tool("wiki_read", "Read a wiki page.", {"path": str})
    async def t_wiki_read(args):
        try:
            text = wiki_tools.wiki_read(args["path"])
            return {"content": [{"type": "text", "text": text[:8000]}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"ERROR: {e}"}], "isError": True}

    @tool("wiki_list", "List wiki pages.", {"prefix": str})
    async def t_wiki_list(args):
        return {"content": [{"type": "text", "text": "\n".join(wiki_tools.wiki_list(args.get('prefix', ''))[:200])}]}

    @tool("wiki_search", "Grep wiki.", {"query": str})
    async def t_wiki_search(args):
        return {"content": [{"type": "text", "text": json.dumps(wiki_tools.wiki_search(args["query"]), indent=2)}]}

    return [t_wiki_read, t_wiki_list, t_wiki_search]


async def run(role: str, task_id: str) -> str:
    task = db.get_task(task_id)
    if not task:
        error(f"task {task_id} not found")
        sys.exit(2)

    log = get_logger(role, task_id)
    log.info(f"DEV {role} starting task={task_id}")

    if not db.claim_task(task_id, agent=role):
        error(f"could not claim task {task_id} (already taken or not pending)")
        sys.exit(3)

    worktree = task.get("worktree")
    if not worktree or not Path(worktree).exists():
        error(f"worktree missing for task {task_id}")
        db.update_status(task_id, "failed", report="worktree missing", actor=role)
        sys.exit(4)

    project = get_project(task["project"])
    log.info(f"worktree={worktree} branch={task['branch']}")

    user_prompt = f"""# Task {task_id}

Project: {project['name']} ({project['key']})
Stack: {', '.join(project.get('stack', []))}
Repo path (your worktree, work ONLY here): {worktree}
Branch: {task['branch']}
Default branch (do NOT touch): {project['default_branch']}

## Description

{task['description']}

---

## Instructions

1. Read your role doc (already in your system prompt).
2. Read relevant wiki pages (use wiki_read).
3. Inspect the codebase you've been given (your cwd is the worktree).
4. Implement the task incrementally with commits inside your worktree.
5. Run tests if patterns exist.
6. Produce the REQUIRED report format at the end of your turn.

Begin.
"""

    server = create_sdk_mcp_server(
        name=f"org-{role}",
        version="1.0.0",
        tools=_build_tools(role),
    )

    role_cfg = get_role(role)

    options = ClaudeAgentOptions(
        model=role_cfg["model"],
        system_prompt=_role_prompt(role),
        permission_mode="acceptEdits",
        cwd=worktree,
        mcp_servers={"org": server},
        allowed_tools=[
            f"mcp__org__wiki_read", f"mcp__org__wiki_list", f"mcp__org__wiki_search",
            "Read", "Write", "Edit", "Bash", "Glob", "Grep",
        ],
    )

    final = []
    async with ClaudeSDKClient(options=options) as client:
        await client.query(user_prompt)
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        log.info(f"{role}: {block.text[:500]}")
                        final.append(block.text)

    report = "\n".join(final)
    db.update_status(task_id, "review", report=report, actor=role)
    info(f"DEV {role} reported task={task_id}")
    return report


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: python -m runners.dev <role> <task_id>", file=sys.stderr)
        sys.exit(1)
    role = sys.argv[1]
    task_id = sys.argv[2]
    asyncio.run(run(role, task_id))
