"""CTO delegates to DEV: opens an iTerm tab running a live Claude Code TUI.

Replaces the old headless subprocess model. Each DEV becomes its own
visible tab so the user can watch the work in real time, identical UI to
the CTO chat. The CTO blocks on a DB poll until the DEV calls the
`submit_report` MCP tool (status → 'review') or fails.
"""
from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path

from lib import db
from lib.config import display_for, get_project
from lib.notify import info, success, error, warn
from tools import tmux_session as tmux
from tools.worktree import create_worktree

ROOT = Path(__file__).resolve().parent.parent

POLL_INTERVAL_S = 2.0
DEFAULT_TIMEOUT_S = 30 * 60  # 30 min per DEV task
TERMINAL_STATUSES = {"review", "done", "failed", "cancelled"}

# IRON-RULES §29: every spawn must ship a visible kickoff ping. Sleep
# lets the claude TUI in the new tab finish booting before keystrokes
# land — otherwise the message types into a still-loading shell.
KICKOFF_DELAY_S = 5.0
DEFAULT_KICKOFF = (
    "kickoff — เริ่มได้เลย อ่าน TASK.md + รายงานผ่าน submit_report เมื่อเสร็จ"
)


def _spawn_iterm_tab(role: str, task_id: str, *,
                     tmux_attach: str | None = None) -> None:
    """Open a new iTerm tab in the frontmost window.

    Default: runs `python -m runners.dev_init <role> <task_id>` directly
    (legacy 1-tab-1-pty model).

    With `tmux_attach=<session>`: tab attaches to a pre-existing tmux
    session that is already running dev_init. The pty lives in tmux —
    closing the tab does NOT kill the agent, and a browser (ttyd) can
    attach the same session simultaneously for two-way realtime sync.
    """
    display = display_for(role)
    tab_title = f"{display} ({task_id})"
    if tmux_attach:
        cmd = (
            f"printf '\\\\033]0;{tab_title}\\\\007' && "
            f"tmux attach -t {tmux_attach}"
        )
    else:
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


async def _auto_kickoff(task_id: str, message: str) -> None:
    """Fire-and-forget kickoff ping after a spawn. IRON-RULES §29.

    Waits for the new tab's claude TUI to boot, then types `[CTO]: …`
    via `tools.send_to_dev.send`. Warns on failure but never blocks the
    delegate path — the spawn already succeeded.
    """
    from tools.send_to_dev import send as send_to_dev_send

    try:
        await asyncio.sleep(KICKOFF_DELAY_S)
        result = await asyncio.to_thread(send_to_dev_send, task_id, message)
        info(f"kickoff task={task_id}: {result}")
    except Exception as e:
        warn(f"kickoff failed task={task_id}: {e}")


async def delegate_task(task_id: str, *, wait: bool = False,
                         timeout_s: float = DEFAULT_TIMEOUT_S,
                         kickoff: str | None = None) -> dict:
    """Open DEV in a new iTerm tab. Fire-and-forget by default.

    With the Stop-hook relay + cto.log auto-inject + DB poll, the CTO no
    longer needs to block waiting for the DEV to finish. Pass wait=True
    to restore the legacy blocking behavior (rarely useful).

    `kickoff`: text typed into the new tab after spawn (IRON-RULES §29).
    Defaults to `DEFAULT_KICKOFF`. Pass an explicit string to override,
    or `""` (empty) to suppress — empty is discouraged outside tests."""
    task = db.get_task(task_id)
    if not task:
        raise ValueError(f"task not found: {task_id}")

    role_name = task["role"]
    project_key = task["project"]

    proj = get_project(project_key)
    if role_name not in proj["agents_allowed"]:
        raise PermissionError(f"role {role_name} not allowed on project {project_key}")

    try:
        touches = json.loads(task.get("touches") or "[]")
    except Exception:
        touches = []

    if touches:
        conflicts = db.find_conflicts(project_key, touches, exclude_task=task_id)
        if conflicts:
            summary = "; ".join(
                f"{c['task_id']}({c['role']},{c['status']}) overlap={c['overlap']}"
                for c in conflicts
            )
            warn(f"collision blocked task={task_id}: {summary}")
            db.update_status(
                task_id, "conflict",
                report=f"path collision with in-flight tasks: {summary}",
                actor="cto",
            )
            return db.get_task(task_id)

        ok, _, blocking = db.lock_paths(task_id, project_key, touches)
        if not ok:
            warn(f"lock acquire failed task={task_id} blocking={blocking}")
            db.update_status(
                task_id, "conflict",
                report=f"path locks held by another task: {blocking}",
                actor="cto",
            )
            return db.get_task(task_id)
        info(f"locked {len(touches)} path(s) for task={task_id}")

    if not task.get("worktree"):
        wt_info = create_worktree(project_key, role_name, task_id)
        db.update_status(task_id, "pending",
                         worktree=wt_info["worktree"],
                         branch=wt_info["branch"],
                         actor="cto")
        info(f"worktree ready: {wt_info['worktree']}")

    info(f"delegate task={task_id} role={role_name} project={project_key}")

    backend = (proj.get("spawn_backend") or "iterm").lower()
    tmux_sess: str | None = None
    ttyd_port: int | None = None
    ttyd_pid: int | None = None

    if backend == "tmux":
        tmux_sess = tmux.session_name_for(task_id)
        dev_cmd = (
            f"cd '{ROOT}' && source .venv/bin/activate && "
            f"python -m runners.dev_init {role_name} {task_id}"
        )
        try:
            tmux.create(tmux_sess, cwd=ROOT, cmd=dev_cmd)
            info(f"tmux session created: {tmux_sess}")
        except subprocess.CalledProcessError as e:
            error(f"tmux create failed for {task_id}: {e.stderr or e}")
            db.update_status(task_id, "failed",
                             report=f"tmux create failed: {e}", actor="cto")
            return db.get_task(task_id)

        web_ui = (proj.get("web_ui") or "off").lower()
        if web_ui in ("true", "auto", "on"):
            try:
                ttyd_port = tmux.pick_free_port()
                ttyd_pid = tmux.start_ttyd(tmux_sess, ttyd_port, writable=True)
                info(f"ttyd up pid={ttyd_pid} url={tmux.url_for(ttyd_port)}")
                # Best-effort open in default browser.
                subprocess.run(["open", tmux.url_for(ttyd_port)], check=False)
            except Exception as e:
                warn(f"ttyd start failed (continuing without web UI): {e}")
                ttyd_port = None
                ttyd_pid = None

        db.update_status(
            task_id, "pending", actor="cto",
            tmux_session=tmux_sess,
            ttyd_port=ttyd_port,
            ttyd_pid=ttyd_pid,
        )

    try:
        _spawn_iterm_tab(role_name, task_id, tmux_attach=tmux_sess)
    except subprocess.CalledProcessError as e:
        error(f"failed to spawn iTerm tab for {task_id}: {e}")
        db.update_status(task_id, "failed",
                         report=f"iTerm spawn failed: {e}", actor="cto")
        return db.get_task(task_id)
    except Exception as e:
        if touches:
            db.release_task_locks(task_id, project_key)
        raise

    kickoff_text = DEFAULT_KICKOFF if kickoff is None else kickoff
    if kickoff_text:
        asyncio.create_task(_auto_kickoff(task_id, kickoff_text))

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
                             *, wait: bool = False,
                             kickoff: str | None = None) -> list[dict]:
    """Delegate multiple tasks. Fire-and-forget by default; pass wait=True
    to block until every task hits a terminal status.

    `kickoff`: shared kickoff text for every spawn (IRON-RULES §29).
    Default = `DEFAULT_KICKOFF`. Per-task overrides are not supported
    here — use `delegate_task` in a loop if you need different text per
    task."""
    sem = asyncio.Semaphore(max_concurrent)

    async def _run(tid):
        async with sem:
            return await delegate_task(tid, wait=wait, kickoff=kickoff)

    return await asyncio.gather(*[_run(t) for t in task_ids])
