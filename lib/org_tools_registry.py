"""Single source of truth for the 17 CTO org tools' wiring.

Context: `runners/cto_mcp_server.py` (FastMCP, the real prod path via
`scripts/cto-claude.sh`) and `runners/cto.py` (claude_agent_sdk, used by
`main.py`'s one-shot mode and imported into `runners/cto_chat.py`'s REPL)
each hand-register the same 17 tools. The REAL business logic already lives
once, in shared modules (`lib/db.py`, `tools/delegate.py`, `tools/git_ops.py`,
`tools/wiki.py`, `lib/recall.py`, `lib/reflect.py`, `tools/revert_task.py`,
`lib/task_ownership.py`) — what was duplicated across the two runner files is
the TOOL REGISTRATION/WIRING boilerplate: arg parsing (JSON-array-or-CSV
decoding for `depends_on`/`touches`/`task_ids`), response formatting
(TOON vs plain-JSON vs prose), the cross-CTO ownership gate, and error
handling. That drift is audit finding W1
(`org:reference/2026-08-06-agents-system-audit.md`) — `cto_chat.py` fell
behind `cto_mcp_server.py` by 4 tools because there was no single place both
call-sites had to agree with.

This module is that single place: one `ToolSpec` per tool, holding enough
(name, description, arg schema, the core callable, the ownership-check flag,
the response-format rule) to drive BOTH a FastMCP `@mcp.tool()` registration
and a claude_agent_sdk `@tool(...)` registration, plus a `dispatch()` that
already runs the unified pipeline (ownership gate -> handler -> format ->
truncate -> uniform error wrapper) so the wiring can be exercised and proven
correct in isolation.

STEP 1 OF 2 (see wiki `org:reference/2026-08-06-agents-system-audit.md`,
Skill/Rule Recommendation #1). This module is NOT wired into
`runners/cto_mcp_server.py`, `runners/cto.py`, or `runners/cto_chat.py` yet —
that swap is a separate follow-up task once this registry is reviewed.

Descriptions are copied verbatim (content/wording, not incidental
docstring-indentation whitespace) from whichever of the two current files
had them; on the occasions the wording differs between the two files
(`create_task`, `check_collisions`, `get_task`, `merge_task`, `reopen_task`),
`runners/cto_mcp_server.py` wins, per the same "prod path is the correct
version" principle the task description applies to response formatting and
the `owner_cto` stamp. See the task's final report for the itemized list.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable

from lib import db
from lib import recall as recall_lib
from lib import reflect as reflect_lib
from lib import toon
from lib.config import get_project, projects
from lib.notify import info, warn
from lib.task_ownership import is_mine, foreign_msg
from tools import wiki as wiki_tools
from tools.delegate import delegate_task as do_delegate, delegate_parallel
from tools.worker_reap import close_dev as do_close_dev
from tools.git_ops import merge_task as do_merge
from tools.worktree import diff_summary, diff_full
from tools import send_to_cxo as send_to_cxo_mod

ROLE = "cto"

# Sentinel: a Param with this default has none — the caller must supply it.
_REQUIRED = object()


@dataclass(frozen=True)
class Param:
    name: str
    type: type
    default: Any = _REQUIRED

    @property
    def required(self) -> bool:
        return self.default is _REQUIRED


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    params: tuple[Param, ...]
    handler: Callable[..., Any]
    is_async: bool = False
    # task_id-keyed cross-CTO ownership gate (lib.task_ownership). Only
    # delegate_task/merge_task/reopen_task/revert_task_tool need it — the
    # rest are either read-only or don't mutate another CTO's task.
    needs_ownership_check: bool = False
    # reopen_task alone short-circuits on a missing task BEFORE the
    # ownership check (returns this literal, unformatted). The other three
    # ownership-gated tools have no such branch — a missing task falls
    # through to the handler, which raises/returns its own "not found"
    # shape (preserved faithfully, not homogenized).
    ownership_not_found_message: str | None = None
    # "toon" for list/dict-shaped data (matching cto_mcp_server.py's
    # existing pattern + the audit's token-efficiency recommendation,
    # ADR-0010); "text" for tools that already return human prose (wiki
    # page bodies, recall/reflect's pre-formatted digests, status strings).
    response_format: str = "toon"
    # Char cap applied to the FORMATTED string, matching cto_mcp_server.py's
    # current slicing exactly (None where cto_mcp_server.py doesn't slice).
    limit: int | None = None


def _parse_list_arg(raw: str) -> list:
    """JSON array string, or comma-separated string, -> list.

    Single shared implementation of the parsing that was previously
    hand-duplicated (identically) in both create_task and check_collisions,
    in both runner files.
    """
    if not raw:
        return []
    try:
        return json.loads(raw)
    except Exception:
        return [s.strip() for s in raw.split(",") if s.strip()]


# --- Handlers: arg-parsing + call into the shared business-logic modules ---
# (No business logic lives here — every handler is a thin call into
# lib.db / tools.* / lib.recall / lib.reflect, matching what each tool's
# body did in cto_mcp_server.py.)

def _h_wiki_read(*, path: str) -> str:
    return wiki_tools.wiki_read(path)


def _h_wiki_list(*, prefix: str = "") -> list[str]:
    return wiki_tools.wiki_list(prefix)[:200]


def _h_wiki_search(*, query: str) -> list[dict]:
    return wiki_tools.wiki_search(query)


def _h_wiki_write(*, path: str, content: str, message: str = "") -> str:
    return wiki_tools.wiki_write(path, content, role=ROLE, message=message or None)


def _h_create_task(*, project: str, role: str, title: str, description: str,
                    depends_on: str = "", touches: str = "") -> str:
    deps = _parse_list_arg(depends_on)
    paths = _parse_list_arg(touches)
    # The regression this must not reintroduce (task-78ef13b0 point 1):
    # cto.py's t_create_task called db.create_task(...) WITHOUT owner_cto=,
    # unlike cto_mcp_server.py. lib.db.create_task does independently fall
    # back to CTO_SESSION_ID/CXO_SESSION_ID env when owner_cto is omitted
    # (see lib/db.py:267-268, the 2026-06-12 issue #15 fix) — so the two
    # runners currently produce the SAME stamped owner_cto today. Stamping
    # explicitly here, matching cto_mcp_server.py, does not rely on that
    # internal fallback staying in place and is the behavior the task
    # explicitly calls "correct".
    tid = db.create_task(
        project=project, role=role, title=title, description=description,
        depends_on=deps, touches=paths,
        owner_cto=os.environ.get("CTO_SESSION_ID"),
    )
    info(f"task created {tid} → {role} on {project} touches={paths}")
    return tid


def _h_check_collisions(*, project: str, touches: str) -> list[dict]:
    paths = _parse_list_arg(touches)
    return db.find_conflicts(project, paths)


_SLIM_KEYS = (
    "id", "project", "role", "status", "title", "pid", "branch",
    "worktree", "iteration", "depends_on", "report", "review",
    "delegate_log",
)


def _slim_task(t: dict | None) -> dict | None:
    """Drop `description` from a task row before it crosses the MCP surface.

    The description is the brief the C-level wrote itself — often thousands of
    words — and every delegate/get call was echoing the whole thing straight
    back into its context. Measured on task-cda4f469 (2026-08-12): five
    delegate calls, five full copies. Internal callers keep using
    db.get_task() and still get the full row; only what the model sees is
    trimmed. Pass include_description=True on get_task when the text is
    genuinely needed.
    """
    if not t:
        return t
    return {k: t[k] for k in _SLIM_KEYS if k in t}


async def _h_delegate_task(*, task_id: str) -> dict:
    return _slim_task(await do_delegate(task_id))


async def _h_delegate_parallel_tasks(*, task_ids: str) -> list[dict]:
    ids = json.loads(task_ids)
    return await delegate_parallel(ids, max_concurrent=3)


def _h_get_task(*, task_id: str, include_description: bool = False) -> dict | None:
    t = db.get_task(task_id)
    return t if include_description else _slim_task(t)


def _h_review_diff(*, task_id: str, full: bool = False) -> str:
    t = db.get_task(task_id)
    if not t or not t.get("worktree"):
        return "no worktree"
    base = get_project(t["project"])["default_branch"]
    return diff_full(t["worktree"], base) if full else diff_summary(t["worktree"], base)


def _h_merge_task(*, task_id: str, override_touches_check: bool = False) -> dict:
    return do_merge(task_id, role=ROLE, override_touches_check=override_touches_check)


def _h_close_dev(*, task_id: str, reason: str = "cto: manual close") -> dict:
    return do_close_dev(task_id, reason=reason)


def _h_reopen_task(*, task_id: str, feedback: str) -> str:
    t = db.get_task(task_id)
    # Newest instruction first. Appending stacked contradictory versions:
    # task-cda4f469 (2026-08-12) reached iteration 3 with the original rule,
    # then two corrections to it, all live in one document, read top-down by
    # each respawned DEV — which acted on the stale rules twice before
    # reaching the current one.
    new_desc = (
        f"## CTO Feedback (iter {t['iteration']+1}) — supersedes everything below\n"
        f"{feedback}\n\n---\n\n{t['description']}"
    )
    db.update_status(
        task_id, "pending",
        description=new_desc,
        iteration=t["iteration"] + 1,
        assigned_agent=None,
        actor="cto",
        force=True,  # reopen is an intentional resurrection (may target done)
    )
    warn(f"reopened {task_id} (iter {t['iteration']+1})")
    return "reopened"


def _h_list_projects() -> list[dict]:
    return list(projects().values())


def _h_stats() -> dict:
    return db.stats()


def _h_recall(*, query: str, project: str = "", limit: int = 5) -> str:
    return recall_lib.recall_text(query, project=project or None, limit=limit)


def _h_reflect(*, days: int = 7, project: str = "") -> str:
    return reflect_lib.reflect_text(days=days, project=project or None)


async def _h_revert_task_tool(*, task_id: str, force: bool = False) -> dict:
    from tools.revert_task import revert_task
    return revert_task(task_id, force=force)


def _h_send_to_cxo(*, role: str, message: str, spawn: bool = False) -> str:
    if spawn:
        return send_to_cxo_mod.spawn(role, message)
    return send_to_cxo_mod.send(role, message)


REGISTRY: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="wiki_read",
        description=(
            'Read a wiki page. Namespaced ("org:x.md") or unprefixed '
            "(default namespace)."
        ),
        params=(Param("path", str),),
        handler=_h_wiki_read,
        response_format="text",
        limit=8000,
    ),
    ToolSpec(
        name="wiki_list",
        description="List wiki pages under an optional prefix.",
        params=(Param("prefix", str, ""),),
        handler=_h_wiki_list,
        response_format="toon",
    ),
    ToolSpec(
        name="wiki_search",
        description="Grep wiki for a query string.",
        params=(Param("query", str),),
        handler=_h_wiki_search,
        response_format="toon",
    ),
    ToolSpec(
        name="wiki_write",
        description=(
            "Create or update a wiki page. CTO only. Auto-commits to wiki "
            "git repo."
        ),
        params=(Param("path", str), Param("content", str), Param("message", str, "")),
        handler=_h_wiki_write,
        response_format="text",
    ),
    ToolSpec(
        name="create_task",
        description=(
            "Create a task in the queue. Returns task_id.\n\n"
            "depends_on accepts JSON array string or comma-separated task_ids.\n"
            "touches accepts JSON array string or comma-separated repo-relative "
            "paths that this task is expected to modify. Used for collision "
            "detection: a delegate_task call with overlapping touches against "
            "an in-flight task is blocked and the task is marked "
            "status='conflict'."
        ),
        params=(
            Param("project", str), Param("role", str), Param("title", str),
            Param("description", str), Param("depends_on", str, ""),
            Param("touches", str, ""),
        ),
        handler=_h_create_task,
        response_format="text",
    ),
    ToolSpec(
        name="check_collisions",
        description=(
            "Preview path collisions before creating a task.\n\n"
            "touches accepts JSON array string or comma-separated paths. "
            "Returns JSON list of in-flight tasks (status "
            "pending/in_progress/rate_limited/conflict) whose touches "
            "intersect the supplied paths. Empty list = safe to delegate."
        ),
        params=(Param("project", str), Param("touches", str)),
        handler=_h_check_collisions,
        response_format="toon",
    ),
    ToolSpec(
        name="delegate_task",
        description=(
            "Spawn a DEV subprocess to execute a task. Blocks until DEV "
            "reports back."
        ),
        params=(Param("task_id", str),),
        handler=_h_delegate_task,
        is_async=True,
        needs_ownership_check=True,
        response_format="toon",
        limit=6000,
    ),
    ToolSpec(
        name="delegate_parallel_tasks",
        description=(
            "Delegate multiple tasks concurrently (max 3 at once). task_ids "
            "is JSON array."
        ),
        params=(Param("task_ids", str),),
        handler=_h_delegate_parallel_tasks,
        is_async=True,
        response_format="toon",
        limit=8000,
    ),
    ToolSpec(
        name="get_task",
        description=(
            "Read a task row. Includes both `report` (DEV completion "
            "summary) and `delegate_log` (runner-level collision/spawn "
            "errors). The task `description` is omitted by default — it is "
            "the brief you wrote yourself and is often thousands of words; "
            "pass include_description=True only when you actually need it."
        ),
        params=(Param("task_id", str), Param("include_description", bool, False)),
        handler=_h_get_task,
        response_format="toon",
        limit=6000,
    ),
    ToolSpec(
        name="review_diff",
        description=(
            "Get the diff of a task's worktree branch vs project default "
            "branch."
        ),
        params=(Param("task_id", str), Param("full", bool, False)),
        handler=_h_review_diff,
        response_format="text",
        limit=8000,
    ),
    ToolSpec(
        name="merge_task",
        description=(
            "Merge a task's branch into project default branch + push. "
            "CTO only.\n\n"
            "If the task declared `touches`, files changed outside that "
            "declaration block the merge (result.touches_violation=true, "
            "branch/worktree kept, status set back to review) — inspect "
            "with review_diff, then retry with override_touches_check=True "
            "once you've confirmed the extra files are legitimate."
        ),
        params=(Param("task_id", str), Param("override_touches_check", bool, False)),
        handler=_h_merge_task,
        needs_ownership_check=True,
        response_format="toon",
    ),
    ToolSpec(
        name="close_dev",
        description=(
            "End a DEV whose task has reached review/done: terminate its "
            "process and close its iTerm tab. CTO only.\n\n"
            "This is the layer-1 decision path — normally merge_task calls "
            "this for you; call it directly when you're closing a task out "
            "without merging (e.g. rejected work). Refuses (without "
            "raising) unless status is review/done and a pid is recorded — "
            "never touches an in-progress or blocked task. Verifies the "
            "pid still belongs to this task before signalling it (a "
            "recycled pid is never signalled, only its tab is closed). "
            "Idempotent — safe to call twice on the same task."
        ),
        params=(Param("task_id", str), Param("reason", str, "cto: manual close")),
        handler=_h_close_dev,
        needs_ownership_check=True,
        response_format="toon",
    ),
    ToolSpec(
        name="reopen_task",
        description=(
            "Mark a task pending again with feedback. Increments iteration "
            "counter."
        ),
        params=(Param("task_id", str), Param("feedback", str)),
        handler=_h_reopen_task,
        needs_ownership_check=True,
        ownership_not_found_message="not found",
        response_format="text",
    ),
    ToolSpec(
        name="list_projects",
        description="List all known projects from config.",
        params=(),
        handler=_h_list_projects,
        response_format="toon",
    ),
    ToolSpec(
        name="stats",
        description="Get task counts by status.",
        params=(),
        handler=_h_stats,
        response_format="toon",
    ),
    ToolSpec(
        name="recall",
        description=(
            "Recall relevant PAST org work for a free-text query.\n\n"
            "Ranks prior tasks by term overlap and returns a compact digest "
            "of each match — final status, merge sha, branch, and a gist of "
            "the DEV report — read back from the task/event log (which is "
            "otherwise write-only). Call this BEFORE planning or creating "
            "tasks to avoid relighting work already done. Read-only. "
            "Optionally scope to one project key."
        ),
        params=(Param("query", str), Param("project", str, ""), Param("limit", int, 5)),
        handler=_h_recall,
        response_format="text",
    ),
    ToolSpec(
        name="reflect",
        description=(
            "Reflect on recent org state — what merged, what's open/stuck, "
            "and any recurring failure signal over the last `days`. "
            "Read-side companion to recall(): recall answers 'what did we "
            "do about X', reflect answers 'where do things stand now'. Call "
            "at session start for situational awareness. Read-only; "
            "surfaces patterns for you to judge, never auto-acts."
        ),
        params=(Param("days", int, 7), Param("project", str, "")),
        handler=_h_reflect,
        response_format="text",
    ),
    ToolSpec(
        name="revert_task_tool",
        description=(
            "Revert a previously merged task. CTO only.\n\n"
            "Refuses if task status is not merged/done. Refuses if merge "
            "SHA is >RVR_DEPTH_LIMIT commits behind HEAD unless force=True.\n\n"
            "Re-fires auto_deploy on success if the project has it enabled "
            "and not requires_ceo_ack."
        ),
        params=(Param("task_id", str), Param("force", bool, False)),
        handler=_h_revert_task_tool,
        is_async=True,
        needs_ownership_check=True,
        response_format="toon",
    ),
    ToolSpec(
        name="send_to_cxo",
        description=(
            "Send a message into another C-level's (cto/cmo/cgo/cfo) live "
            "chat tab -- e.g. CTO asking CFO for a budget approval, or CMO "
            "asking CGO for an attribution check. Sender is auto-detected "
            "from this session's role; a role-mismatched call is rejected. "
            "spawn=True opens a new ephemeral tab for that role instead of "
            "typing into its primary tab, when no session is running.\n\n"
            "Routing is ownership-gated, not free-form broadcast: you may "
            "message only the session that spawned you, or a session you "
            "spawned yourself (max 3 delegation hops counting the "
            "originator as level 1) -- refused otherwise, loudly, naming "
            "the whole chain. A primary (non-spawned) C-level session may "
            "always reach another primary C-level as a peer -- that is the "
            "routine cross-role request this tool exists for.\n\n"
            "You OWN the outcome of what you delegate here: if the C-level "
            "you ask gets it wrong, that is on you, not them -- asking "
            "someone else to do it never transfers accountability for it."
        ),
        params=(
            Param("role", str),
            Param("message", str),
            Param("spawn", bool, False),
        ),
        handler=_h_send_to_cxo,
        response_format="text",
    ),
)

BY_NAME: dict[str, ToolSpec] = {s.name: s for s in REGISTRY}

assert len(REGISTRY) == len(BY_NAME), (
    f"duplicate tool name in REGISTRY: {len(REGISTRY)} entries, "
    f"{len(BY_NAME)} unique names"
)


def _format(spec: ToolSpec, result: Any) -> str:
    if spec.response_format == "toon":
        out = toon.encode(result)
    else:
        out = "" if result is None else str(result)
    if spec.limit is not None:
        out = out[: spec.limit]
    return out


def _prepare(spec: ToolSpec, kwargs: dict) -> tuple[str | None, dict]:
    """Arg-merge + ownership gate, shared by dispatch() and dispatch_sync().

    Returns (short_circuit, merged). If the ownership gate fires,
    short_circuit is the final string the caller must return immediately
    (handler never runs); otherwise it's None and `merged` is the resolved
    handler kwargs.
    """
    merged = {
        p.name: kwargs[p.name] if p.name in kwargs else p.default
        for p in spec.params
        if p.name in kwargs or not p.required
    }

    if spec.needs_ownership_check:
        task_id = merged.get("task_id") or kwargs.get("task_id")
        t = db.get_task(task_id)
        if spec.ownership_not_found_message is not None and not t:
            return spec.ownership_not_found_message, merged
        if t and not is_mine(t):
            return foreign_msg(t), merged

    return None, merged


async def dispatch(name: str, **kwargs: Any) -> str:
    """Registry-driven dispatch: resolve args -> ownership gate -> call the
    handler -> format -> truncate, all behind ONE error-handling wrapper.

    This is the net-safety fix for Do-item #3: in the current code, only
    wiki_read/wiki_list/wiki_search/wiki_write/recall/reflect/
    revert_task_tool catch exceptions; create_task/delegate_task/get_task/
    stats/list_projects/check_collisions/review_diff/merge_task/reopen_task/
    delegate_parallel_tasks do not, so an unhandled exception in any of
    those currently propagates uncaught. Applying the wrapper uniformly
    here means every one of the 17 tools now returns a clean "ERROR: ..."
    string instead of raising into the client's response loop.

    `name` lookup itself is NOT inside the try — an unknown tool name is a
    wiring bug in the CALLER (dead tool name in allowed_tools, typo), not a
    runtime failure of a real tool call, and should fail loudly.
    """
    spec = BY_NAME[name]
    try:
        short_circuit, merged = _prepare(spec, kwargs)
        if short_circuit is not None:
            return short_circuit
        result = await spec.handler(**merged) if spec.is_async else spec.handler(**merged)
        return _format(spec, result)
    except Exception as e:  # noqa: BLE001 - intentional catch-all, see docstring
        return f"ERROR: {e}"


def dispatch_sync(name: str, **kwargs: Any) -> str:
    """Synchronous sibling of dispatch(), for tools whose handler is never
    async. Same pipeline (arg-merge -> ownership gate -> handler -> format
    -> truncate -> error wrap) minus the `await`.

    Exists because runners/cto_mcp_server.py's FastMCP tool stubs for the
    14 sync tools run inside FastMCP's OWN already-running asyncio event
    loop — `asyncio.run(dispatch(...))` there would raise "cannot run
    event loop while another loop is running". A plain sync call has no
    such constraint.
    """
    spec = BY_NAME[name]
    assert not spec.is_async, f"{name} handler is async — use dispatch() instead"
    try:
        short_circuit, merged = _prepare(spec, kwargs)
        if short_circuit is not None:
            return short_circuit
        result = spec.handler(**merged)
        return _format(spec, result)
    except Exception as e:  # noqa: BLE001 - intentional catch-all, see docstring
        return f"ERROR: {e}"
