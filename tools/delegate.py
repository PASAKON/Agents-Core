"""CTO delegates to DEV: opens an iTerm tab running a live Claude Code TUI.

Replaces the old headless subprocess model. Each DEV becomes its own
visible tab so the user can watch the work in real time, identical UI to
the CTO chat. The CTO blocks on a DB poll until the DEV calls the
`submit_report` MCP tool (status → 'review') or fails.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
from datetime import datetime, timezone
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


def _owner_window_id(owner_cto: str | None,
                     owner_role: str | None = None) -> str | None:
    """Read the iTerm window id that the spawning C-level recorded at boot.

    cto-claude.sh / cxo-claude.sh write `state/locks/<role>-<id>.winid`
    containing the integer window id of the iTerm window owning that
    session — `cto-<id>.winid` for a CTO session, `cfo-<id>.winid` for a
    CFO session, etc. `owner_role` selects the prefix; defaults to "cto"
    for legacy rows created before `owner_role` was stamped (previously
    this always assumed "cto", so CFO/CMO/CGO delegates never found their
    own window and fell through to the generic fallback).
    Returns the digits as a string, or None if the file is missing or
    unreadable. Matching by id is immune to the session-name flicker
    that makes name-based AppleScript matches misroute DEV tabs, and
    (since the id is a unique uuid4-hex8 per session) works correctly
    with multiple CTO — or multiple CFO/CMO/CGO — sessions open at once.
    """
    if not owner_cto:
        return None
    role_prefix = owner_role or "cto"
    p = ROOT / "state" / "locks" / f"{role_prefix}-{owner_cto}.winid"
    try:
        raw = p.read_text().strip()
    except OSError:
        return None
    return raw if raw.isdigit() else None


def _build_spawn_applescript(cmd: str, task_id: str,
                              owner_cto: str | None,
                              owner_role: str | None = None,
                              owner_winid: str | None = None) -> str:
    """Compose the AppleScript that picks the right window and tab.

    Resolution order:
      1. Any iTerm tab title contains `(<task_id>)` already → select it
         and emit `reused`. No new tab, no command typed.
      2. Window whose id matches `owner_winid` (recorded at boot by
         cto-claude.sh / cxo-claude.sh) → immune to title flicker.
      3. Window owning `<DISPLAY> Chat #<owner_cto>` / `<DISPLAY> #<owner_cto>`
         (legacy and live-summary title formats, IRON-RULES §32), where
         `<DISPLAY>` is CTO/CFO/CMO/CGO per `owner_role` — every C-level's
         spawns (any worker role: dev/qa/devops/designer/...) cluster
         under ITS OWN window, not just CTO's. The session id in the
         match is what keeps multiple concurrent sessions of the same
         role (e.g. two CTOs open at once) from crossing into each
         other's window.
      4. Any tab whose title contains `<DISPLAY> Chat #` or `<DISPLAY> #`
         — keeps single-session setups working when owner_cto is unset.
      5. Current window, or a fresh window if none exist.

    Built in Python so tests can grep the literal strings without
    invoking osascript.
    """
    display = display_for(owner_role) if owner_role else "CTO"
    owner_match = f"{display} Chat #{owner_cto}" if owner_cto else ""
    owner_match_new = f"{display} #{owner_cto}" if owner_cto else ""
    # iTerm has two title surfaces per tab: `name of t` (the tab title,
    # which holds the OSC-set name stickily) and `name of current
    # session of t` (the session badge, which flickers to the running
    # process name e.g. "node" until the next OSC is emitted). We check
    # both so a flicker during DEV spawn doesn't push the tab into the
    # wrong CTO window.
    return f'''
set frontApp to ""
try
  tell application "System Events" to set frontApp to name of first application process whose frontmost is true
end try
tell application "iTerm"
  -- Record where the user's focus currently sits so spawning a DEV tab
  -- does NOT yank the cursor away mid-keystroke. A freshly created tab
  -- steals foreground by default, which dropped CEO keystrokes into the
  -- DEV shell and killed dev_init before it could claim. Restored below.
  -- priorWin/priorTab restore iTerm's own window order; frontApp (captured
  -- above via System Events) restores the frontmost *application* — the
  -- iTerm-internal restore alone never returned focus to a different app
  -- (e.g. the CEO's chat window), which is why the steal kept recurring.
  set priorWin to missing value
  set priorTab to missing value
  try
    set priorWin to current window
    set priorTab to current tab of priorWin
  end try
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
          if (tabName contains "{owner_match}") or (sessName contains "{owner_match}") or (tabName contains "{owner_match_new}") or (sessName contains "{owner_match_new}") then
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
          if (tabName contains "{display} Chat #") or (sessName contains "{display} Chat #") or (tabName contains "{display} #") or (sessName contains "{display} #") then
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
        write text (ASCII character 21) newline NO
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
      -- Ctrl-U (ASCII 21) clears any stray keystrokes the CEO leaked into
      -- this tab while it briefly held focus, so the kickoff command runs
      -- on a clean prompt instead of becoming e.g. "ทดprintf: not found"
      -- (which silently killed dev_init — CEO report 2026-06-14).
      write text (ASCII character 21) newline NO
      write text "{cmd}"
    end tell
  end tell
  -- Restore the user's prior focus so the DEV tab lands in the background
  -- instead of stealing the foreground (the keystroke-eating bug).
  try
    if priorWin is not missing value then
      tell priorWin to select
      if priorTab is not missing value then
        tell priorTab to select
      end if
    end if
  end try
  -- App-level focus restore: bring the CEO's prior application back to the
  -- front so the DEV tab lands in the background. Best-effort: if System
  -- Events automation is unauthorized, frontApp is "" and this no-ops.
  try
    if frontApp is not "" and frontApp is not "iTerm" and frontApp is not "iTerm2" then
      tell application frontApp to activate
    end if
  end try
  return "spawned"
end tell
'''


def _spawn_iterm_tab(role: str, task_id: str, *,
                     tmux_attach: str | None = None,
                     owner_cto: str | None = None,
                     owner_role: str | None = None) -> str:
    """Open or reuse an iTerm tab for this DEV task.

    Returns `"reused"` when an existing tab matching `(<task_id>)` was
    found (no new tab, no command sent); `"spawned"` otherwise.

    With `tmux_attach=<session>`: tab attaches to a pre-existing tmux
    session that is already running dev_init. The pty lives in tmux —
    closing the tab does NOT kill the agent, and a browser (ttyd) can
    attach the same session simultaneously for two-way realtime sync.

    `owner_cto` + `owner_role`: stamped into env WORKER_CTO_ID and used to
    pick the owning C-level's window (CTO/CFO/CMO/CGO, per `owner_role`)
    so spawns of ANY worker role cluster under their spawning session,
    not just under CTO. With multiple sessions of the same role open
    (e.g. two CTOs), the session id prevents tabs landing in the wrong
    window.
    """
    display = display_for(role)
    tab_title = f"{display} ({task_id})"
    cto_env = f"export WORKER_CTO_ID='{owner_cto}' && " if owner_cto else ""
    if tmux_attach:
        cmd = (
            f"printf '\\\\033]1;{tab_title}\\\\007' && "
            f"{cto_env}tmux attach -t {tmux_attach}"
        )
    else:
        # Print ANSI title escape from inside the shell so zsh's precmd
        # doesn't immediately overwrite the iTerm session name.
        # Double-escape: AppleScript string parses `\\` → `\`, leaving
        # `\033`/`\007` for bash printf to interpret as ESC/BEL.
        #
        # Trailing `; exit $?` (GH mooniex-agents#27): no-op on the happy
        # path — dev_init.py's os.execvpe replaces this shell with claude
        # before ever reaching here. Only fires when dev_init.py exits
        # early (claim failed, task not found, worktree missing), so the
        # shell/tab closes immediately instead of falling to an idle
        # prompt whose title a zsh precmd hook can silently repaint,
        # leaving an untraceable zombie tab.
        cmd = (
            f"printf '\\\\033]1;{tab_title}\\\\007' && "
            f"{cto_env}cd '{ROOT}' && source .venv/bin/activate && "
            f"python -m runners.worker_init {role} {task_id}; exit $?"
        )
    owner_winid = _owner_window_id(owner_cto, owner_role)
    script = _build_spawn_applescript(cmd, task_id, owner_cto,
                                      owner_role=owner_role,
                                      owner_winid=owner_winid)
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
    via `tools.send_to_worker.send`. Warns on failure but never blocks the
    delegate path — the spawn already succeeded.
    """
    from tools.send_to_worker import send as send_to_worker_send

    try:
        await asyncio.sleep(KICKOFF_DELAY_S)
        result = await asyncio.to_thread(send_to_worker_send, task_id, message)
        info(f"kickoff task={task_id}: {result}")
    except Exception as e:
        warn(f"kickoff failed task={task_id}: {e}")


# How long a spawned DEV gets to claim its task before we treat the tab
# as dead. dev_init claims within ~2-3s of shell start (venv + import +
# one UPDATE), so 25s of pending+unclaimed means the process never ran
# (0-byte-log silent death) or the "reused" tab was a leftover dead shell.
CLAIM_VERIFY_DELAY_S = 25.0

# Strong references to fire-and-forget background coroutines.
#
# The event loop only holds a *weak* reference to what create_task() returns,
# so a task nothing else references can be garbage-collected mid-await. That
# is what silenced _verify_claimed (GH #64): it sleeps 25s before it checks
# anything, so it was collected long before it could fire and its
# warn/respawn/error path never ran once. Symptom: delegate logs "DEV
# spawned", the row stays pending forever, and no error appears anywhere —
# observed 4 times in a row on task-08c30235.
#
# Discarding on completion keeps the set from growing without bound.
_BACKGROUND_TASKS: set[asyncio.Task] = set()


def _spawn_background(coro) -> asyncio.Task:
    """create_task() + hold a strong reference until the task finishes."""
    t = asyncio.create_task(coro)
    _BACKGROUND_TASKS.add(t)
    t.add_done_callback(_BACKGROUND_TASKS.discard)
    return t


def _pid_alive(pid: int | None) -> bool:
    """True if `pid` names a live OS process. `dev_init.py` stamps its own
    pid the instant it claims a task (before os.execvpe replaces it with
    claude), so a live pid on an in_progress row means a DEV is genuinely
    running — used by the W4 re-delegate guard to avoid resetting/clobbering
    it. os.kill(pid, 0) sends no signal, just probes existence."""
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True  # exists but owned by another user — still alive
    return True


def _seconds_since(iso_ts: str | None) -> float | None:
    """Seconds elapsed since an `updated_at`-style ISO timestamp, or None
    if unparseable/absent."""
    if not iso_ts:
        return None
    try:
        then = datetime.fromisoformat(iso_ts)
    except ValueError:
        return None
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - then).total_seconds()


async def _verify_claimed(task_id: str, role_name: str,
                          owner_cto: str | None,
                          owner_role: str | None = None, *,
                          kickoff_text: str, attempt: int = 1) -> None:
    """Watchdog for the iTerm backend's two silent-death modes: the DEV
    process dies before claiming, or the tab-reuse path selected a dead
    tab. One automatic close+respawn, then a loud error for the CTO."""
    await asyncio.sleep(CLAIM_VERIFY_DELAY_S)
    t = db.get_task(task_id)
    if not t or t["status"] != "pending" or t.get("assigned_agent"):
        return  # claimed (or moved on) — the normal path
    if attempt > 1:
        error(f"task {task_id} still unclaimed after respawn — "
              f"DEV never started; investigate tab / dev_init manually")
        return
    warn(f"task {task_id} unclaimed {CLAIM_VERIFY_DELAY_S:.0f}s after spawn "
         f"— closing stale tab and respawning once")
    try:
        from tools.itermtab import close_tab
        # Re-check right before closing: a claim landing in this window
        # would make the tab live and the close wrong.
        t = db.get_task(task_id)
        if not t or t["status"] != "pending" or t.get("assigned_agent"):
            return
        await asyncio.to_thread(close_tab, task_id)
    except Exception as e:
        warn(f"stale-tab close failed for {task_id}: {e}")
    try:
        await asyncio.to_thread(_spawn_iterm_tab, role_name, task_id,
                                owner_cto=owner_cto, owner_role=owner_role)
    except Exception as e:
        error(f"respawn failed for {task_id}: {e}")
        db.update_status(task_id, "failed",
                         delegate_log=f"respawn after unclaimed spawn failed: {e}",
                         actor="cto")
        return
    if kickoff_text:
        _spawn_background(_auto_kickoff(task_id, kickoff_text))
    _spawn_background(_verify_claimed(task_id, role_name, owner_cto, owner_role,
                                        kickoff_text=kickoff_text,
                                        attempt=attempt + 1))


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
    if task["status"] in ("done", "merged"):
        # Re-delegating merged work would reset it toward an active status and
        # re-create the phantom-lock class fixed in issue #13. Reopen first.
        raise ValueError(
            f"task {task_id} already {task['status']} — refusing to re-delegate "
            f"merged work (use reopen_task if a redo is intended)"
        )

    role_name = task["role"]
    project_key = task["project"]

    proj = get_project(project_key)
    if role_name not in proj["agents_allowed"]:
        raise PermissionError(f"role {role_name} not allowed on project {project_key}")

    # W3 (audit 2026-08-06): depends_on was invisible to this pre-flight —
    # only a touches overlap with an ACTIVE task ever blocked a delegate, and
    # that overlap-based block silently evaporates the moment the dependency
    # reaches 'review' (locks release there) even though it isn't merged yet,
    # so the dependent started on a stale base. This check is independent of
    # touches and fires even when the two tasks don't share a single path.
    try:
        deps = json.loads(task.get("depends_on") or "[]")
    except Exception:
        deps = []
    if deps:
        unmet = db.unmet_dependencies(deps)
        if unmet:
            summary = "; ".join(f"{u['id']}({u['status']})" for u in unmet)
            warn(f"dependency blocked task={task_id}: {summary}")
            # Deliberately does NOT touch status (stays whatever it already
            # was, typically 'pending') — reusing 'conflict' here would make
            # this indistinguishable from a touches-collision at a glance.
            # delegate_log is the established channel for "why was this
            # refused" (same pattern as the collision/lock-failure messages
            # below); a caller can tell the two apart by status alone
            # ('pending' vs 'conflict') as well as by this text.
            db.set_fields(
                task_id,
                delegate_log=f"blocked by unfinished dependency: {summary}",
                actor="cto",
            )
            return db.get_task(task_id)

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
    elif task.get("status") == "pending" and not task.get("assigned_agent"):
        # W4 (audit 2026-08-06): worktree exists, never claimed. This combo
        # is reached both by a fresh spawn's own first pass through this
        # function (fine — falls through to spawn below) AND by a second,
        # wasted delegate_task call on the SAME task while the first spawn
        # is still booting (dev_init hasn't reached claim_task yet, so
        # pid/assigned_agent are still NULL and no branch above resets
        # anything). `pid` can't distinguish these two cases — it isn't
        # stamped until claim — so ask `spawned_at`, which is written at
        # exactly one place: the commit point of a genuine spawn, below.
        # A duplicate call inside the grace period `_verify_claimed`
        # watches (CLAIM_VERIFY_DELAY_S) means a spawn is already in
        # flight; refuse instead of opening a second tab. Past that window
        # the watchdog has given up (or this is a deliberate manual
        # re-delegate), so fall through and spawn.
        #
        # This used to read `updated_at`, on the stated assumption that the
        # row "was only touched by the worktree-creation write above, which
        # happens once per genuine spawn". That assumption was false and
        # cost six minutes of lockout on task-cda4f469 (2026-08-13 01:07).
        # reopen_task writes status+description; the watchdog writes
        # 'stalled'; and worst of all the refusal below writes delegate_log,
        # so every refusal reset the very clock it had just read and each
        # retry pushed the deadline further out. The normal recovery flow is
        # reopen → delegate, which therefore could never succeed on the
        # first try. See GH #51 and #53.
        #
        # NULL means no spawn on record — never read it as "long ago".
        since = _seconds_since(task.get("spawned_at"))
        if since is not None and since < CLAIM_VERIFY_DELAY_S:
            info(f"skip duplicate spawn task={task_id}: spawned {since:.0f}s "
                 f"ago, still within the {CLAIM_VERIFY_DELAY_S:.0f}s claim "
                 f"grace period")
            db.set_fields(
                task_id,
                delegate_log=(
                    f"duplicate delegate refused: spawn already issued "
                    f"{since:.0f}s ago, not yet claimed (grace period "
                    f"{CLAIM_VERIFY_DELAY_S:.0f}s) — wait for claim or the "
                    f"watchdog's automatic retry"
                ),
                actor="cto",
            )
            return db.get_task(task_id)
    elif task.get("status") != "pending":
        # Re-delegate of a task whose worktree already exists and which is
        # NOT sitting unclaimed-pending (e.g. in_progress, conflict, failed,
        # rate_limited). Before resetting — which would clear assigned_agent
        # and spawn a brand-new tab — check whether the pid dev_init stamped
        # at claim time is still alive. A live pid means a DEV is genuinely
        # running right now; resetting would orphan it from the row it's
        # using and spawn a redundant duplicate. A dead/absent pid means the
        # prior run crashed or never claimed, so the reset below is safe —
        # unchanged from the original behavior.
        pid = task.get("pid")
        if pid and _pid_alive(pid):
            warn(f"refusing re-delegate task={task_id}: pid={pid} still "
                 f"alive (status={task['status']})")
            db.set_fields(
                task_id,
                delegate_log=(
                    f"duplicate delegate refused: task already running "
                    f"under live pid={pid} (status={task['status']})"
                ),
                actor="cto",
            )
            return db.get_task(task_id)
        # dev_init's claim_task only fires on status='pending' AND
        # assigned_agent IS NULL, so without this reset the respawned DEV
        # cannot claim and dies silently at a bare shell. 'pending' is not a
        # releasing status, so the path locks acquired just above stay held.
        db.update_status(task_id, "pending",
                         assigned_agent=None, pid=None, actor="cto")
        info(f"re-delegate: reset task={task_id} to pending for re-claim")

    info(f"delegate task={task_id} role={role_name} project={project_key}")

    # The commit point of a genuine spawn: every refusal above has returned,
    # so from here a DEV process is going to be started. This is the ONLY
    # write to `spawned_at` in the codebase — that is what makes it able to
    # answer "how long ago was a DEV spawned", which `updated_at` never
    # could (GH #51, #53). Stamped before the spawn rather than after, so a
    # spawn that hangs partway still blocks a duplicate.
    db.set_fields(task_id, spawned_at=db.now_iso(), actor="cto")

    backend = (proj.get("spawn_backend") or "iterm").lower()
    tmux_sess: str | None = None
    ttyd_port: int | None = None
    ttyd_pid: int | None = None

    owner_cto = task.get("owner_cto")
    # Pre-migration rows have owner_cto but NULL owner_role → default "cto"
    # (mirrors runners/worker_init.py's WORKER_CTO_ROLE fallback for the same rows).
    owner_role = task.get("owner_role") or "cto"

    if backend == "tmux":
        tmux_sess = tmux.session_name_for(task_id)
        # Record the tmux session BEFORE the DEV process exists. The DEV
        # claims (pending → in_progress) within seconds of tmux.create; a
        # status write after that point would silently regress the claim.
        db.set_fields(task_id, tmux_session=tmux_sess, actor="cto")
        cto_env = f"export WORKER_CTO_ID='{owner_cto}' && " if owner_cto else ""
        dev_cmd = (
            f"{cto_env}cd '{ROOT}' && source .venv/bin/activate && "
            f"python -m runners.worker_init {role_name} {task_id}"
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

        if ttyd_port or ttyd_pid:
            db.set_fields(task_id, ttyd_port=ttyd_port, ttyd_pid=ttyd_pid,
                          actor="cto")

    try:
        spawn_result = _spawn_iterm_tab(role_name, task_id,
                                        tmux_attach=tmux_sess,
                                        owner_cto=owner_cto,
                                        owner_role=owner_role)
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
        _spawn_background(_auto_kickoff(task_id, kickoff_text))

    if backend != "tmux":
        # Catch both silent-death modes (dead reused tab / dev_init that
        # never claimed) — tmux backend is covered by runners.watchdog.
        _spawn_background(_verify_claimed(task_id, role_name, owner_cto, owner_role,
                                            kickoff_text=kickoff_text))

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
