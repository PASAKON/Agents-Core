"""Cross-CTO-window ownership guard.

A task stamped with `owner_cto` belongs to the CTO session that created it.
Without this check, a second CTO window (a different CTO_SESSION_ID) could
mutate a task it doesn't own via delegate/merge/reopen/revert, stomping the
owning CTO's in-flight work.

Shared by runners/cto_mcp_server.py (stdio MCP path) and runners/cto.py
(one-shot main.py path + cto_chat.py REPL path) so the guard only exists
once. Extracted from cto_mcp_server.py, which had the only copy.
"""
from __future__ import annotations

import os


def my_cto_id() -> str | None:
    return os.environ.get("CTO_SESSION_ID") or None


def is_mine(task: dict | None) -> bool:
    """May this CTO session mutate the task?

    Unrestricted when the session has no id (legacy/single-CTO) or the
    task has no owner (pre-owner_cto rows, CXO-created tasks)."""
    if not task:
        return True
    mine = my_cto_id()
    owner = task.get("owner_cto")
    return not mine or not owner or owner == mine


def foreign_msg(task: dict) -> str:
    return (
        f"Refusing cross-CTO mutation: task {task.get('id')} belongs to "
        f"CTO #{task.get('owner_cto')} (you are CTO #{my_cto_id() or 'unset'}). "
        f"Coordinate via tools.send_to_cxo or let the owning CTO act."
    )
