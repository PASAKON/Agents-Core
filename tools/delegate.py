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


def _owner_window_id(owner_cto: str | None) -> str | None:
    """Read the iTerm window id that the spawning CTO recorded at boot.

    cto-claude.sh writes `state/locks/cto-<id>.winid` containing the
    integer window id of the iTerm window owning that CTO's session.
    Returns the digits as a string, or None if the file is missing or
    unreadable. Matching by id is immune to the session-name flicker
    that makes name-based AppleScript matches misroute DEV tabs.
    """
    if not owner_cto:
        return None
    p = ROOT / "state" / "locks" / f"cto-{owner_cto}.winid"
    try:
        raw = p.read_text().strip()
    except OSError:
        return None
    return raw if raw.isdigit() else None


def _build_spawn_applescript(cmd: str, task_id: str,
                              owner_cto: str | None,
                              owner_winid: str | None = None) -> str:
    """Compose the AppleScript that picks the right window and tab.

    Resolution order:
      1. Any iTerm tab title contains `(<task_id>)` already → select it
         and emit `reused`. No new tab, no command typed.
      2. Window owning `CTO Chat #<owner_cto>` exactly → new tab there
         so DEVs cluster under their spawning CTO (fixes multi-CTO
         routing).
      3. Any tab whose title contains `CTO Chat #` — keeps single-CTO
         setups working when owner_cto is unset.
      4. Current window, or a fresh window if none exist.

    Built in Python so tests can grep the literal strings without
    invoking osascript.
    """
    owner_match = f"CTO Chat #{owner_cto}" if owner_cto else ""
    # iTerm has two title surfaces per tab: `name of t` (the tab title,
    # which holds the OSC-set name stickily) and `name of current
    # session of t` (the session badge, which flickers to the running
    # process name e.g. "node" until the next OSC is emitted). We check
    # both so a flicker during DEV spawn doesn't push the tab into the
    # wrong CTO window.
    return f'''
tell application "iTerm"
  repeat with w in windows
    repeat with t in tabs of w
      try
        set tabName to ""
        try
          set tabName to name of t
        end try
        set sessName to ""
        try
          set sessName to name of current session of t
        end try
        if (tabName contains "({task_id})") or (sessName contains "({task_id})") then
          tell w to select
          tell t to select
          return "reused"
        end if
      end try
    end repeat
  end repeat
  set targetWin to missing value
  -- 1. Prefer matching by iTerm window id (recorded by cto-claude.sh
  -- at boot). Immune to session-name flicker.
  if "{owner_winid or ''}" is not "" then
    try
      set targetWin to (first window whose id is ({owner_winid or 0}))
    end try
  end if
  if (targetWin is missing value) and "{owner_match}" is not "" then
    repeat with w in windows
      repeat with t in tabs of w
        try
          set tabName to ""
          try
            set tabName to name of t
          end try
          set sessName to ""
          try
            set sessName to name of current session of t
          end try
          if (tabName contains "{owner_match}") or (sessName contains "{owner_match}") then
            set targetWin to w
            exit repeat
          end if
        end try
      end repeat
      if targetWin is not missing value then exit repeat
    end repeat
  end if
  if targetWin is missing value then
    repeat with w in windows
      repeat with t in tabs of w
        try
          set tabName to ""
          try
            set tabName to name of t
          end try
          set sessName to ""
          try
            set sessName to name of current session of t
          end try
          if (tabName contains "CTO Chat #") or (sessName contains "CTO Chat #") then
            set targetWin to w
            exit repeat
          end if
        end try
      end repeat
      if targetWin is not missing value then exit repeat
    end repeat
  end if
  if targetWin is missing value then
    if (count of windows) = 0 then
      set targetWin to (create window with default profile)
      tell current session of current tab of targetWin
        write text "{cmd}"
      end tell
      return "spawned"
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
  return "spawned"
end tell
'''


def _spawn_iterm_tab(role: str, task_id: str, *,
                     tmux_attach: str | None = None,
                     owner_cto: str | None = None) -> str:
    """Open or reuse an iTerm tab for this DEV task.

    Returns `"reused"` when an existing tab matching `(<task_id>)` was
    found (no new tab, no command sent); `"spawned"` otherwise.

    With `tmux_attach=<session>`: tab attaches to a pre-existing tmux
    session that is already running dev_init. The pty lives in tmux —
    closing the tab does NOT kill the agent, and a browser (ttyd) can
    attach the same session simultaneously for two-way realtime sync.

    `owner_cto`: stamped into env DEV_CTO_ID and used to pick the CTO
    window so DEVs cluster under their spawning CTO. With two CTOs
    open, this prevents tabs landing in the wrong window.
    """
    display = display_for(role)
    tab_title = f"{display} ({task_id})"
    cto_env = f"export DEV_CTO_ID='{owner_cto}' && " if owner_cto else ""
    if tmux_attach:
        cmd = (
            f"printf '\\\\033]0;{tab_title}\\\\007' && "
            f"{cto_env}tmux attach -t {tmux_attach}"
        )
    else:
        # Print ANSI title escape from inside the shell so zsh's precmd
        # doesn't immediately overwrite the iTerm session name.
        # Double-escape: AppleScript string parses `\\` → `\`, leaving
        # `\033`/`\007` for bash printf to interpret as ESC/BEL.
        cmd = (
            f"printf '\\\\033]0;{tab_title}\\\\007' && "
            f"{cto_env}cd '{ROOT}' && source .venv/bin/activate && "
            f"python -m runners.dev_init {role} {task_id}"
        )
    owner_winid = _owner_window_id(owner_cto)
    script = _build_spawn_applescript(cmd, task_id, owner_cto, owner_winid)
    result = subprocess.run(["osascript", "-e", script],
                            check=True, capture_output=True, text=True)
    return (result.stdout or "").strip() or "spawned"


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
        delegate_log=f"DEV timed out after {timeout_s:.0f}s without submit_report",
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
                delegate_log=f"path collision with in-flight tasks: {summary}",
                actor="cto",
            )
            return db.get_task(task_id)

        ok, _, blocking = db.lock_paths(task_id, project_key, touches)
        if not ok:
            warn(f"lock acquire failed task={task_id} blocking={blocking}")
            db.update_status(
                task_id, "conflict",
                delegate_log=f"path locks held by another task: {blocking}",
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
    elif task.get("status") != "pending":
        # Re-delegate of a task whose worktree already exists. dev_init's
        # claim_task only fires on status='pending' AND assigned_agent IS
        # NULL, so without this reset the respawned DEV cannot claim and
        # dies silently at a bare shell. 'pending' is not a releasing
        # status, so the path locks acquired just above stay held.
        db.update_status(task_id, "pending",
                         assigned_agent=None, pid=None, actor="cto")
        info(f"re-delegate: reset task={task_id} to pending for re-claim")

    info(f"delegate task={task_id} role={role_name} project={project_key}")

    backend = (proj.get("spawn_backend") or "iterm").lower()
    tmux_sess: str | None = None
    ttyd_port: int | None = None
    ttyd_pid: int | None = None

    owner_cto = task.get("owner_cto")

    if backend == "tmux":
        tmux_sess = tmux.session_name_for(task_id)
        cto_env = f"export DEV_CTO_ID='{owner_cto}' && " if owner_cto else ""
        dev_cmd = (
            f"{cto_env}cd '{ROOT}' && source .venv/bin/activate && "
            f"python -m runners.dev_init {role_name} {task_id}"
        )
        try:
            tmux.create(tmux_sess, cwd=ROOT, cmd=dev_cmd)
            info(f"tmux session created: {tmux_sess}")
        except subprocess.CalledProcessError as e:
            error(f"tmux create failed for {task_id}: {e.stderr or e}")
            db.update_status(task_id, "failed",
                             delegate_log=f"tmux create failed: {e}", actor="cto")
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
        spawn_result = _spawn_iterm_tab(role_name, task_id,
                                        tmux_attach=tmux_sess,
                                        owner_cto=owner_cto)
    except subprocess.CalledProcessError as e:
        error(f"failed to spawn iTerm tab for {task_id}: {e}")
        db.update_status(task_id, "failed",
                         delegate_log=f"iTerm spawn failed: {e}", actor="cto")
        return db.get_task(task_id)
    except Exception as e:
        if touches:
            db.release_task_locks(task_id, project_key)
        raise

    if spawn_result == "reused":
        info(f"reused existing iTerm tab for task={task_id} "
             f"(skipping kickoff to avoid disturbing a running DEV)")

    kickoff_text = DEFAULT_KICKOFF if kickoff is None else kickoff
    if kickoff_text and role_name == "web_designer":
        # Worktree omits gitignored .od/; resolve the design ref from the
        # task description so the agent gets the concrete path. §9 / db guard.
        kickoff_text += db.designer_kickoff_suffix(task.get("description") or "")
    if kickoff_text and spawn_result != "reused":
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
