"""What a COO (SomPong) may hand to a worker -- one list, enforced in code.

CEO card Q-20261013-1948-4a33 (option 1, 2026-10-13 20:01Z): SomPong may create and
delegate its own research workers -- researcher, data_analyst, browser_operator --
and never a code role ("CTO ไว้ดูแลเรื่อง Coding ในองค์กรอย่างเดียว").

Enforced at three places, each of which refuses on its own:
  1. runners/coo_gate.py -- the only process that holds the COO's hub credential; its
     create_task and delegate_task ops call check_role() before touching the hub, and the
     root dispatcher (runners/coo_dispatch.py) checks again before it starts a worker.
  2. lib.db.create_task -- every Python path that inserts a task row (the org MCP
     registry, runners/cto.py, the COO gate) calls check_role() first.
  3. deploy/coo-gate/org_coo_role.sql -- the org_coo_guard trigger refuses any tasks row
     the Postgres role org_coo writes unless owner_role='coo' and role is in this list.
Keep this tuple and the SQL list identical (tests/test_coo_gate.py checks it).
"""
from __future__ import annotations

COO_ROLE = "coo"
COO_WORKER_ROLES = ("researcher", "data_analyst", "browser_operator")


class CooRoleRefused(PermissionError):
    """A COO-owned task asked for a role outside COO_WORKER_ROLES."""


def check_role(owner_role: str | None, role: str) -> None:
    """Raise CooRoleRefused when a coo-owned task names any other role.

    Other owners pass untouched: this guard narrows the COO, nobody else."""
    if (owner_role or "").strip().lower() != COO_ROLE:
        return
    if role not in COO_WORKER_ROLES:
        raise CooRoleRefused(
            f"role {role!r} refused for a coo task: SomPong may delegate only "
            f"{', '.join(COO_WORKER_ROLES)} (CEO card Q-20261013-1948-4a33). "
            f"Code work goes to a CTO: SendMessage it the brief.")
