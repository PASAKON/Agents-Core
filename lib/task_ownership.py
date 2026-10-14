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

PH_ROLE = "project_head"  # lib/roles.PH_ROLE; kept literal so this module stays import-light


def _ph_session() -> str | None:
    """This process serves a Project Head: its session id ("" if unset), else None.
    A PH's launcher unsets CTO_SESSION_ID, so the CTO rule below would let it
    mutate every task (security review of f73fa02f)."""
    if (os.environ.get("CXO_ROLE") or "").strip().lower() != PH_ROLE:
        return None
    return (os.environ.get("CXO_SESSION_ID") or "").strip()


def my_cto_id() -> str | None:
    ph = _ph_session()
    if ph is not None:
        return ph or None
    return os.environ.get("CTO_SESSION_ID") or None


def is_mine(task: dict | None) -> bool:
    """May this CTO session mutate the task?

    Unrestricted when the session has no id (legacy/single-CTO) or the
    task has no owner (pre-owner_cto rows, CXO-created tasks).

    A Project Head (org restructure P2) is never unrestricted: only a task
    stamped with its own role and session id is its own."""
    if not task:
        return True
    ph = _ph_session()
    if ph is not None:
        return (bool(ph) and task.get("owner_cto") == ph
                and (task.get("owner_role") or "").strip().lower() == PH_ROLE)
    mine = my_cto_id()
    owner = task.get("owner_cto")
    return not mine or not owner or owner == mine


def _label(role: str | None) -> str:
    return "Project Head" if (role or "").strip().lower() == PH_ROLE else "CTO"


def foreign_msg(task: dict) -> str:
    return (
        f"Refusing cross-CTO mutation: task {task.get('id')} belongs to "
        f"{_label(task.get('owner_role'))} #{task.get('owner_cto')} (you are "
        f"{_label(PH_ROLE if _ph_session() is not None else '')} #{my_cto_id() or 'unset'}). "
        f"Coordinate via tools.send_to_cxo or let the owning CTO act."
    )
