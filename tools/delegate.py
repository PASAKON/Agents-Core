"""CTO delegates to DEV: opens an iTerm tab running a live Claude Code TUI.

Replaces the old headless subprocess model. Each DEV becomes its own
visible tab so the user can watch the work in real time, identical UI to
the CTO chat. The CTO blocks on a DB poll until the DEV calls the
`submit_report` MCP tool (status → 'review') or fails.
"""
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

from lib import db
from lib.config import display_for, get_project
from lib.notify import info, success, error, warn
from tools.worktree import create_worktree

ROOT = Path(__file__).resolve().parent.parent

POLL_INTERVAL_S = 2.0
DEFAULT_TIMEOUT_S = 30 * 60  # 30 min per DEV task
TERMINAL_STATUSES = {"review", "done", "failed", "cancelled"}


def _spawn_iterm_tab(role: str, task_id: str) -> None:
    """Open a new iTerm tab in the frontmost window running dev_init."""
    display = display_for(role)
    tab_title = f"{display} ({task_id})"
    # Print ANSI title escape from inside the shell so zsh's precmd
    # doesn't immediately overwrite the iTerm session name.
    # Double-escape: AppleScript string parses `\\` → `\`, leaving
    # `\033`/`\007` for bash printf to interpret as ESC/BEL.
    cmd = (
        f"printf '\\\\033]0;{tab_title}\\\\007' && "
        f"cd '{ROOT}' && source .venv/bin/activate && "
        f"python -m runners.dev_init {role} {task_id}"
    )
    # Prefer the window that owns the CTO chat tab so DEV tabs cluster
    # in the same window as the CTO instead of whichever window happened
    # to be focused. Fall back to current/new window if CTO tab not found.
    script = f'''
tell application "iTerm"
  activate
  set targetWin to missing value
  repeat with w in windows
    repeat with t in tabs of w
      try
        set tabName to name of current session of t
        if tabName contains "CTO" then
          set targetWin to w
          exit repeat
        end if
      end try
    end repeat
    if targetWin is not missing value then exit repeat
  end repeat
  if targetWin is missing value then
    if (count of windows) = 0 then
      set targetWin to (create window with default profile)
      tell current session of current tab of targetWin
        write text "{cmd}"
      end tell
      return
    else
      set targetWin to current window
    end if
  end if
  tell targetWin
    set newTab to (create tab with default profile)
    tell current session of newTab
      write text "{cmd}"
    end tell
  end tell
end tell
'''
    subprocess.run(["osascript", "-e", script], check=True)


async def _wait_for_terminal(task_id: str, timeout_s: float) -> dict:
    """Poll DB until task reaches a terminal status or times out."""
    elapsed = 0.0
    while elapsed < timeout_s:
        await asyncio.sleep(POLL_INTERVAL_S)
        elapsed += POLL_INTERVAL_S
        t = db.get_task(task_id)
        if not t:
            raise RuntimeError(f"task {task_id} disappeared")
        if t["status"] in TERMINAL_STATUSES:
            return t
    warn(f"task {task_id} timed out after {timeout_s:.0f}s")
    db.update_status(
        task_id, "failed",
        report=f"DEV timed out after {timeout_s:.0f}s without submit_report",
        actor="cto",
    )
    return db.get_task(task_id)


async def delegate_task(task_id: str, *, wait: bool = False,
                         timeout_s: float = DEFAULT_TIMEOUT_S) -> dict:
    """Open DEV in a new iTerm tab. Fire-and-forget by default.

    With the Stop-hook relay + cto.log auto-inject + DB poll, the CTO no
    longer needs to block waiting for the DEV to finish. Pass wait=True
    to restore the legacy blocking behavior (rarely useful)."""
    task = db.get_task(task_id)
    if not task:
        raise ValueError(f"task not found: {task_id}")

    role_name = task["role"]
    project_key = task["project"]

    proj = get_project(project_key)
    if role_name not in proj["agents_allowed"]:
        raise PermissionError(f"role {role_name} not allowed on project {project_key}")

    if not task.get("worktree"):
        wt_info = create_worktree(project_key, role_name, task_id)
        db.update_status(task_id, "pending",
                         worktree=wt_info["worktree"],
                         branch=wt_info["branch"],
                         actor="cto")
        info(f"worktree ready: {wt_info['worktree']}")

    info(f"delegate task={task_id} role={role_name} project={project_key}")

    try:
        _spawn_iterm_tab(role_name, task_id)
    except subprocess.CalledProcessError as e:
        error(f"failed to spawn iTerm tab for {task_id}: {e}")
        db.update_status(task_id, "failed",
                         report=f"iTerm spawn failed: {e}", actor="cto")
        return db.get_task(task_id)

    if not wait:
        success(f"DEV spawned task={task_id} (fire-and-forget)")
        return db.get_task(task_id)

    final = await _wait_for_terminal(task_id, timeout_s)
    if final["status"] == "failed":
        error(f"DEV task={task_id} failed")
    else:
        success(f"DEV done task={task_id} status={final['status']}")
    return final


async def delegate_parallel(task_ids: list[str], max_concurrent: int = 3,
                             *, wait: bool = False) -> list[dict]:
    """Delegate multiple tasks. Fire-and-forget by default; pass wait=True
    to block until every task hits a terminal status."""
    sem = asyncio.Semaphore(max_concurrent)

    async def _run(tid):
        async with sem:
            return await delegate_task(tid, wait=wait)

    return await asyncio.gather(*[_run(t) for t in task_ids])
