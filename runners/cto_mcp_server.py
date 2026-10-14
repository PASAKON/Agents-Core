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

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP

from lib import db
from lib import org_tools_registry as reg
from lib import telegram_out
from lib.logger import get_logger
# Re-exported for scripts/test_org_tools_registry.py and
# scripts/test_owner_cto_routing.py, which patch/call these directly as
# module attributes of this file — not used by the stubs below anymore
# (registry.py owns the real calls into them).
from lib.task_ownership import is_mine as _is_mine, foreign_msg as _foreign_msg  # noqa: F401
from tools.delegate import delegate_task as do_delegate, delegate_parallel  # noqa: F401
from tools.worker_reap import close_dev as do_close_dev  # noqa: F401
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
    host: str = "",
    needs: str = "",
) -> str:
    return reg.dispatch_sync(
        "create_task", project=project, role=role, title=title,
        description=description, depends_on=depends_on, touches=touches,
        host=host, needs=needs,
    )


@mcp.tool(description=reg.BY_NAME["check_collisions"].description)
def check_collisions(project: str, touches: str) -> str:
    return reg.dispatch_sync("check_collisions", project=project, touches=touches)


@mcp.tool(description=reg.BY_NAME["delegate_task"].description)
async def delegate_task(task_id: str, host: str = "") -> str:
    return await reg.dispatch("delegate_task", task_id=task_id, host=host)


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


@mcp.tool(description=reg.BY_NAME["send_to_cxo"].description)
def send_to_cxo(role: str, message: str, spawn: bool = False, subject: str = "",
                kind: str = "", prio: str = "") -> str:
    return reg.dispatch_sync("send_to_cxo", role=role, message=message, spawn=spawn,
                             subject=subject, kind=kind, prio=prio)


@mcp.tool(description=reg.BY_NAME["report_to_ceo"].description)
def report_to_ceo(order_id: int, status: str, detail: str) -> str:
    return reg.dispatch_sync("report_to_ceo", order_id=order_id,
                             status=status, detail=detail)


@mcp.tool()
def send_media_to_ceo(path: str, caption: str = "") -> str:
    """Upload a photo, video, or other file to the CEO's real Telegram chat
    as an actual file — never a link (task-ed9e5b9a, CEO order #38).

    Picks sendPhoto/sendVideo/sendDocument by probing the file's real
    content, not its extension. Verifies the bot is @SSomPongBot before
    sending — a wrong token still comes back "ok": true from Telegram while
    the message never reaches the CEO (2026-08-16 incident). Files over
    Telegram's 50 MB cap are refused outright, never sent as a link.

    Not wired through org_tools_registry — this tool has no cross-CTO
    ownership concern, so it calls lib/telegram_out.py directly.

    Returns a JSON string: {"ok": bool, "reason": str|None}.
    """
    try:
        result = telegram_out.send_media_to_ceo(path, caption=caption)
    except Exception as e:  # thin wrapper contract: never raise
        result = {"ok": False, "reason": f"unexpected error: {e}"}
    return json.dumps(result)


@mcp.tool()
def send_media_batch_to_ceo(paths: str, caption: str = "") -> str:
    """Upload multiple files to the CEO's real Telegram chat in one call
    (task-68be2c26, CEO orders #42/#43). `paths` is a JSON array string or
    comma-separated list of local file paths.

    Each file is routed independently by its own size: anything that fits
    under Telegram's 50 MB cap always goes out as a real file, never a
    link — photos and videos share an album (sendMediaGroup, up to 10 per
    album, more sent as further albums), documents go one at a time since
    Telegram won't let a document share an album with a photo/video. A
    file over 50 MB goes to the CEO's Google Drive `Desktop Cloud` folder
    instead — verified by a fresh folder listing before it's ever reported
    as done — and the CEO is told why, by name, size, and link. That is the
    only case that ever produces a link (order #38 still stands for
    everything that fits).

    Not wired through org_tools_registry's dispatch — same reasoning as
    send_media_to_ceo above (no cross-CTO ownership concern) — it parses
    `paths` and calls lib/telegram_out.py directly.

    Returns a JSON string: {"ok": bool, "results": [{"path", "status",
    "reason", "link"}]}. Never raises.
    """
    try:
        path_list = reg._parse_list_arg(paths)
        result = telegram_out.send_media_batch_to_ceo(path_list, caption=caption)
    except Exception as e:  # thin wrapper contract: never raise
        result = {"ok": False, "reason": f"unexpected error: {e}"}
    return json.dumps(result)


@mcp.tool(description=reg.BY_NAME["decide"].description)
def decide(site: str, state: str, provider: str = "") -> str:
    return reg.dispatch_sync("decide", site=site, state=state, provider=provider)


@mcp.tool(description=reg.BY_NAME["start_clevel_remote"].description)
async def start_clevel_remote(host: str, role: str, resume_session_id: str = "") -> str:
    return await reg.dispatch("start_clevel_remote", host=host, role=role,
                              resume_session_id=resume_session_id)


@mcp.tool(description=reg.BY_NAME["ask_run"].description)
async def ask_run(
    host: str,
    why: str,
    script: str = "",
    args: list[str] | None = None,
    command: str = "",
    expected: str = "",
    risk: str = "amber",
    timeout_s: int = 300,
    expects_input: bool = False,
    shell: str = "",
    cwd: str = "",
    env_keys: list[str] | None = None,
    session: str = "",
    role: str = "",
    task: str = "",
    dry_run: bool = False,
) -> str:
    return await reg.dispatch(
        "ask_run", host=host, why=why, script=script, args=args, command=command,
        expected=expected, risk=risk, timeout_s=timeout_s, expects_input=expects_input,
        shell=shell, cwd=cwd, env_keys=env_keys, session=session, role=role, task=task,
        dry_run=dry_run,
    )


@mcp.tool(description=reg.BY_NAME["ask_ceo"].description)
async def ask_ceo(
    question: str = "",
    options: list[str] | None = None,
    why: str = "",
    recommended: int = 0,
    free_text: bool = True,
    expires_h: float = 24.0,
    session: str = "",
    role: str = "",
    host: str = "",
    task: str = "",
    dry_run: bool = False,
    questions: list[dict] | None = None,
) -> str:
    return await reg.dispatch(
        "ask_ceo", question=question, options=options, why=why, recommended=recommended,
        free_text=free_text, expires_h=expires_h, session=session, role=role, host=host,
        task=task, dry_run=dry_run, questions=questions,
    )


@mcp.tool(description=reg.BY_NAME["ask_run_wait"].description)
async def ask_run_wait(
    id: str, max_wait_s: float = 600.0, interval_s: float = 5.0, tail_lines: int = 40,
) -> str:
    return await reg.dispatch(
        "ask_run_wait", id=id, max_wait_s=max_wait_s, interval_s=interval_s,
        tail_lines=tail_lines,
    )


# Envelope mail (org restructure P1): the two letter readers are served only
# when ORG_MAIL_ENVELOPE is on in this server's env, so with the flag off a
# session's tool list is what it was. Defined either way, so the registry
# parity check (scripts/test_org_tools_registry.py) still finds them.
def read_letter(id: str) -> str:
    return reg.dispatch_sync("read_letter", id=id)


def list_letters(unread_only: bool = False, limit: int = 20) -> str:
    return reg.dispatch_sync("list_letters", unread_only=unread_only, limit=limit)


from lib import mailbox as _mailbox  # noqa: E402
from lib import roles as _org_roles  # noqa: E402

if _mailbox.envelope_on():
    for _fn in (read_letter, list_letters):
        assert _fn.__name__ in reg.ENVELOPE_TOOLS
        mcp.tool(description=reg.BY_NAME[_fn.__name__].description)(_fn)


# Org restructure P2 (plan §3.2): a Project Head session is served only
# reg.PH_TOOLS, including any tool registered here outside the registry;
# registry dispatch refuses the rest for it as well.
if _org_roles.is_project_head(reg.caller_role()):
    _served = set(reg.served_names())
    for _name in sorted({_t.name for _t in mcp._tool_manager.list_tools()} - _served):
        mcp.remove_tool(_name)


if __name__ == "__main__":
    db.init()
    mcp.run()
