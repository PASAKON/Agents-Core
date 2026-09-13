"""CTO delegates to DEV: opens an iTerm tab running a live Claude Code TUI.

Replaces the old headless subprocess model. Each DEV becomes its own
visible tab so the user can watch the work in real time, identical UI to
the CTO chat. The CTO blocks on a DB poll until the DEV calls the
`submit_report` MCP tool (status → 'review') or fails.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import shlex
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from lib import db
from lib.config import (
    display_for, get_project, host as get_host,
    project_path_for_host, role as get_role,
    worker_session_name as get_worker_session_name,
)
from lib.notify import info, success, error, warn
from tools import tmux_session as tmux
from tools.worktree import branch_name, create_worktree

ROOT = Path(__file__).resolve().parent.parent

# How a worker is started, held as a STABLE path rather than as the command
# itself. This is the root-cause fix for a failure that recurred across
# several sessions: the MCP server runs in-process with a C-level session and
# imports this module once, so every literal here is frozen for that session's
# entire life and the session cannot reload itself. When
# `runners/dev_init.py` became `runners/worker_init.py` (df01c33), sessions
# older than the rename went on spawning a module that no longer existed --
# dying in under a second, invisibly, with the org log still reporting
# success, and only a restart could fix it.
#
# Keeping only this path in memory moves the volatile part (which module, which
# interpreter, which venv) onto disk, where it is read fresh at spawn time. A
# future rename inside runners/ is then picked up immediately by every running
# session, stale or not, with no restart. Keep the script's path and argument
# contract stable and let the churn live inside the script.
WORKER_LAUNCHER = f"bash '{ROOT / 'scripts' / 'spawn-worker.sh'}'"

POLL_INTERVAL_S = 2.0
DEFAULT_TIMEOUT_S = 30 * 60  # 30 min per DEV task
TERMINAL_STATUSES = {"review", "done", "failed", "cancelled"}

# ADDENDUM 3 (CTO 2026-09-07): statuses a browser_operator counts as "live"
# for the per-host Chrome cap — mirrors db.ACTIVE_STATUSES minus 'pending'
# and 'conflict' (a pending/conflicted operator holds no Chrome tab yet).
_BROWSER_OPERATOR_ACTIVE_STATUSES = ("in_progress", "rate_limited", "stalled")


def _operator_counts_as_live(task: dict, resolved_host: str) -> bool:
    """Does this browser_operator row still hold a Chrome tab, as far as the cap is concerned?

    A row with no pid yet is a spawn in flight — count it. A row whose recorded pid is
    provably gone on THIS machine holds nothing — do not count it. The watchdog deliberately
    leaves 'stalled' rows alone (CEO 2026-09-07: stalled is a suspicion, not a verdict), so
    by 2026-09-09 fourteen dead-since-August 'stalled' operators were counted as 14/2 live on
    the Mac and no operator could be spawned at all. Remote hosts cannot be pid-checked from
    here, so their rows keep counting.
    """
    pid = task.get("pid")
    if not pid or resolved_host != "mac":
        return True
    try:
        os.kill(int(pid), 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except (TypeError, ValueError, OSError):
        return True

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
    # Callers pass the session id either bare ("eab87266") or already
    # role-qualified ("cto-eab87266"); the qualified form used to build a
    # doubled path and silently fall through to the current window.
    ident = owner_cto
    if ident.startswith(f"{role_prefix}-"):
        ident = ident[len(role_prefix) + 1:]
    p = ROOT / "state" / "locks" / f"{role_prefix}-{ident}.winid"
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
        # Trailing `; exit $?` (ADDENDUM 2, CTO 2026-09-07 — CEO rule:
        # ending a worker must close its window, never just the process).
        # Without it, when the tmux session dies the tab drops to a bare
        # shell prompt and stays open — iTerm's "Close Sessions On End" is
        # on, but the shell itself never ends, so it never fires. Mirrors
        # the non-tmux branch below, which has carried this since GH #27.
        cmd = (
            f"printf '\\\\033]1;{tab_title}\\\\007' && "
            f"{cto_env}tmux attach -t {tmux_attach}; exit $?"
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
            f"{cto_env}{WORKER_LAUNCHER} {role} {task_id}; exit $?"
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
# as dead. worker_init claims within ~2-3s of shell start (venv + import +
# one UPDATE), so 25s of pending+unclaimed means the process never ran
# (0-byte-log silent death) or the "reused" tab was a leftover dead shell.
CLAIM_VERIFY_DELAY_S = 25.0

# Everything the spawn path executes. A C-level session imports these ONCE,
# at startup; a later commit changes them on disk but not in the running
# process, and the session cannot reload itself. That gap is invisible and
# total: on 2026-08-15 a rename (runners/dev_init -> runners/worker_init)
# landed 3h into a session, and every delegate after it spawned a module
# that no longer existed -- dying in under a second while the org log
# printed "DEV spawned" each time.
_SPAWN_PATH_FILES = (
    Path(__file__),
    ROOT / "runners" / "worker_init.py",
    ROOT / "runners" / "worker_resume.py",
    ROOT / "tools" / "tmux_session.py",
)
_IMPORTED_AT = time.time()


def _warn_if_stale_code() -> None:
    """Warn when a spawn-path file changed after this process imported it.

    Cheap mtime check, no git. The session keeps working -- this is advice,
    not a gate -- but it turns "delegate mysteriously fails forever" into
    one line telling the operator to restart.
    """
    stale = [p.name for p in _SPAWN_PATH_FILES
             if p.is_file() and p.stat().st_mtime > _IMPORTED_AT]
    if stale:
        warn(f"this session imported {', '.join(stale)} before it changed on "
             f"disk — it is still running the OLD code and cannot reload "
             f"itself. Restart the session to pick the change up.")

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
                          kickoff_text: str, attempt: int = 1,
                          tmux_sess: str | None = None) -> None:
    """Watchdog for the silent-death modes: the worker process dies before
    claiming, or the tab-reuse path selected a dead tab. One automatic
    close+respawn on the iTerm backend, then a loud error for the CTO.

    On the tmux backend there is no respawn: a worker that died before
    claiming means the spawn path itself is broken, and respawning into a
    broken path just loops. It captures the dead pane instead and fails the
    task with the real error text -- that text is the only thing naming the
    cause, and tmux discards it the instant the session's command exits."""
    await asyncio.sleep(CLAIM_VERIFY_DELAY_S)
    t = db.get_task(task_id)
    if not t or t["status"] != "pending" or t.get("assigned_agent"):
        return  # claimed (or moved on) — the normal path

    if tmux_sess:
        pane = ""
        try:
            pane = await asyncio.to_thread(tmux.capture, tmux_sess)
        except Exception as e:  # never fail while reporting a failure
            warn(f"pane capture failed for {task_id}: {e}")
        detail = pane.strip().splitlines()[-12:] if pane.strip() else []
        why = "\n".join(detail) if detail else (
            "no pane output — session already torn down. Reproduce with "
            "`tmux set-option -g remain-on-exit on` to retain it."
        )
        error(f"task {task_id} never claimed {CLAIM_VERIFY_DELAY_S:.0f}s after "
              f"spawn — the worker died before claiming. Pane said:\n{why}")
        db.update_status(
            task_id, "failed",
            delegate_log=f"worker died before claiming (tmux {tmux_sess}):\n{why}",
            actor="cto")
        return
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


# ---------------------------------------------------------------------------
# Remote host spawn (winbox, Phase 1 — docs/design/multi-host-workers.md).
#
# Git is the only cross-machine channel (design doc §3 rule 2): a remote DEV
# is cloned in from git by windows/spawn-worker.ps1, and reports back by
# pushing a branch + REPORT.md, which runners/branch_poller.py (separate
# task deliverable) picks up. No stdio MCP over SSH, no shared filesystem.
# ---------------------------------------------------------------------------

REMOTE_SSH_TIMEOUT_S = 30
# The launcher step on a fresh box does a partial clone + worktree + spawn; 90 s
# marked a healthy spawn failed on 2026-09-07. Liveness is watched separately.
REMOTE_LAUNCH_TIMEOUT_S = 300

# (local path relative to ROOT, remote path relative to host agents_root).
# roles/<role>.md is appended per-spawn in _ensure_remote_deploy — it's the
# one file that depends on which task is being spawned.
_REMOTE_DEPLOY_FILES = (
    ("windows/spawn-worker.ps1", "spawn-worker.ps1"),
    ("roles/_worker_shared.md", "roles/_worker_shared.md"),
    ("roles/_worker_remote.md", "roles/_worker_remote.md"),
)


def _ps_quote(value: str) -> str:
    """Quote `value` as a single PowerShell double-quoted string literal.

    Used to build the ONE string handed to `ssh <host> <cmd>` — ssh does
    not preserve argv boundaries across the wire, it joins/re-sends a
    single command string that the remote shell re-parses with ITS OWN
    quoting rules, not Python's."""
    escaped = value.replace("`", "``").replace('"', '`"').replace("$", "`$")
    return f'"{escaped}"'


def _local_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _remote_sha256(ssh_alias: str, remote_path: str) -> str | None:
    """SHA256 of a file already on the box (uppercase hex), or None if the
    file is absent or the box is unreachable — never raises, a deploy check
    that can't confirm the remote state just re-copies the file."""
    check = (
        f"if (Test-Path {_ps_quote(remote_path)}) "
        f"{{ (Get-FileHash -Algorithm SHA256 {_ps_quote(remote_path)}).Hash }}"
    )
    try:
        r = subprocess.run(
            ["ssh", ssh_alias, "powershell", "-NoProfile", "-Command", check],
            capture_output=True, text=True, timeout=REMOTE_SSH_TIMEOUT_S,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    out = (r.stdout or "").strip().upper()
    return out or None


def _ensure_remote_deploy(host_cfg: dict, role_name: str, *,
                          dry_run: bool = False) -> list[str]:
    """scp spawn-worker.ps1 + the role docs a remote DEV needs, but only
    the files missing or whose content changed (sha256 compare) — so a
    routine delegate call is a no-op scp-wise once the box is warm. Returns
    the actions taken (or, in dry-run, that would be taken)."""
    ssh_alias = host_cfg["ssh"]
    agents_root = host_cfg["agents_root"]
    sep = "\\" if host_cfg.get("os") == "windows" else "/"
    files = list(_REMOTE_DEPLOY_FILES) + [(f"roles/{role_name}.md", f"roles/{role_name}.md")]

    actions: list[str] = []
    dirs_needed: set[str] = set()
    to_copy: list[tuple[Path, str]] = []
    for local_rel, remote_rel in files:
        local = ROOT / local_rel
        if not local.is_file():
            continue
        remote_abs = f"{agents_root}{sep}{remote_rel.replace('/', sep)}"
        if dry_run:
            actions.append(f"[dry-run] would check/deploy {local_rel} -> {ssh_alias}:{remote_abs}")
            continue
        if _remote_sha256(ssh_alias, remote_abs) == _local_sha256(local):
            continue
        to_copy.append((local, remote_abs))
        dirs_needed.add(remote_abs.rsplit(sep, 1)[0])

    if dry_run or not to_copy:
        return actions

    if dirs_needed:
        # No `| Out-Null` here — winbox's OpenSSH default shell is cmd.exe,
        # which splits an UNQUOTED `|` before powershell.exe ever sees it
        # (confirmed live 2026-09-07: `New-Item ... | Out-Null` breaks into
        # two cmd.exe commands, the second — `Out-Null` — fails as
        # "not recognized", and the directory is never created). New-Item's
        # own stdout is harmless; we already capture_output and ignore it.
        mkdirs = "; ".join(
            f"New-Item -ItemType Directory -Force -Path {_ps_quote(d)}"
            for d in dirs_needed
        )
        r = subprocess.run(["ssh", ssh_alias, "powershell", "-NoProfile", "-Command", mkdirs],
                           capture_output=True, text=True, timeout=REMOTE_SSH_TIMEOUT_S)
        if r.returncode != 0:
            raise RuntimeError(f"remote mkdir failed: {(r.stderr or r.stdout or '').strip()}")
    for local, remote_abs in to_copy:
        r = subprocess.run(["scp", str(local), f"{ssh_alias}:{remote_abs}"],
                           capture_output=True, text=True, timeout=REMOTE_SSH_TIMEOUT_S)
        if r.returncode != 0:
            raise RuntimeError(f"deploy scp failed for {local.name}: {r.stderr}")
        actions.append(f"deployed {local.name} -> {remote_abs}")
    return actions


def _ssh_remote_url(remote: str) -> str:
    """Normalize a project's `remote:` (HTTPS or SSH in config/projects.yaml
    — the file mixes both today) to the SSH form a remote spoke can clone
    with. A spoke like winbox authenticates via an SSH deploy key only; it
    has no HTTPS credential manager wired up (confirmed live 2026-09-07:
    `git clone https://...` on winbox failed with "Unable to persist
    credentials ... terminal prompts disabled")."""
    if remote.startswith("git@"):
        return remote
    m = re.match(r"^https://github\.com/([^/]+)/(.+?)(?:\.git)?/?$", remote)
    if not m:
        raise ValueError(f"cannot derive an SSH clone URL from remote {remote!r}")
    org, repo = m.group(1), m.group(2)
    return f"git@github.com:{org}/{repo}.git"


def _render_remote_claude_args(role_name: str, host_name: str) -> str:
    """Render the flags a remote spawn needs: model/effort (policies/
    agents.yaml) + the SAME allowed-tools/--chrome worker_tool_grants
    renders for a Mac spawn (runners/worker_init.py) — reused verbatim
    rather than hand-duplicated, minus what a remote box can't have (org
    MCP, hence no --mcp-config here at all) — plus --remote-control, which
    a remote worker carries when `host_name`'s `remote_control` flag in
    config/hosts.yaml allows it (ADDENDUM 1, CTO 2026-09-07) so it shows up
    in the CEO's Claude app session list, same as win-cto.ps1 already does
    for the Windows CTO session.

    --allowed-tools stays LAST with nothing after it (it is variadic and
    swallows every following argv element — see runners/worker_init.py's
    own comment on this), so --remote-control goes before the chrome flags,
    not after."""
    from runners.worker_init import remote_control_args, worker_tool_grants
    allowed, extra_flags = worker_tool_grants(role_name)
    role_cfg = get_role(role_name)
    model = role_cfg.get("model") or "claude-sonnet-5"
    effort = role_cfg.get("effort") or "high"
    parts = [
        "--model", model,
        "--effort", effort,
        "--permission-mode", "auto",
        "--strict-mcp-config",
        *remote_control_args(host_name),
        *extra_flags,
        "--allowed-tools", ",".join(allowed),
    ]
    return " ".join(parts)


async def _spawn_remote(task: dict, host_name: str, *,
                        dry_run: bool = False) -> dict:
    """Spawn a DEV on a remote spoke host (winbox today; a Contabo launcher
    is Phase 2, a non-goal of this task). No org MCP, no tmux, no iTerm —
    the worktree is cloned in from git by windows/spawn-worker.ps1, and the
    DEV reports back by pushing its branch + REPORT.md. This function's job
    ends at recording host/branch/worktree/pid on the task row;
    runners/branch_poller.py takes it from there."""
    from runners.worker_init import _build_prompt

    task_id = task["id"]
    role_name = task["role"]
    project_key = task["project"]

    host_cfg = get_host(host_name)  # raises ValueError if host_name is unknown
    if host_cfg.get("os") != "windows":
        raise NotImplementedError(
            f"host {host_name!r} (os={host_cfg.get('os')}) has no remote "
            f"launcher yet — only winbox is wired in Phase 1; a Contabo "
            f"launcher is Phase 2 (non-goal of this task)"
        )
    ssh_alias = host_cfg.get("ssh")
    if not ssh_alias:
        raise ValueError(f"host {host_name!r} has no ssh alias configured")

    proj = get_project(project_key)
    repo_url = proj.get("remote")
    if not repo_url:
        raise ValueError(f"project {project_key!r} has no `remote:` — cannot clone it onto {host_name}")
    repo_url = _ssh_remote_url(repo_url)
    repo_path = project_path_for_host(project_key, host_name)  # raises if not routable
    worktree_root = host_cfg["worktrees"]
    branch = branch_name(role_name, task_id)
    base = proj["default_branch"]
    remote_worktree = f"{worktree_root}\\{project_key}__{role_name}__{task_id}"

    claude_args = _render_remote_claude_args(role_name, host_name)
    role_cfg = get_role(role_name)
    model = role_cfg.get("model") or "claude-sonnet-5"
    effort = role_cfg.get("effort") or "high"
    # ADDENDUM 1 (CTO 2026-09-07): machine-prefixed session name, rendered
    # once here (single source of truth) and handed to the launcher rather
    # than recomputed in PowerShell.
    session_name = get_worker_session_name(host_name, role_name, task_id,
                                           task.get("title") or "")

    deploy_actions = _ensure_remote_deploy(host_cfg, role_name, dry_run=dry_run)

    prompt = _build_prompt(task, proj, remote_worktree)
    remote_task_file = f"{host_cfg['agents_root']}\\.task-{task_id}.md"
    remote_ps1 = f"{host_cfg['agents_root']}\\spawn-worker.ps1"

    remote_cmd = (
        f"powershell -NoProfile -ExecutionPolicy Bypass -File {_ps_quote(remote_ps1)} "
        f"-Task {_ps_quote(task_id)} -Project {_ps_quote(project_key)} "
        f"-Role {_ps_quote(role_name)} -Branch {_ps_quote(branch)} "
        f"-Base {_ps_quote(base)} -RepoUrl {_ps_quote(repo_url)} "
        f"-RepoPath {_ps_quote(repo_path)} -WorktreeRoot {_ps_quote(worktree_root)} "
        f"-ClaudeArgs {_ps_quote(claude_args)} -Model {_ps_quote(model)} "
        f"-Effort {_ps_quote(effort)} -TaskFile {_ps_quote(remote_task_file)} "
        f"-SessionName {_ps_quote(session_name)}"
    )
    cmd = ["ssh", ssh_alias, remote_cmd]

    if dry_run:
        printable = " ".join(shlex.quote(c) for c in cmd)
        info(f"[dry-run] task={task_id} host={host_name} deploy: {deploy_actions}")
        info(f"[dry-run] task={task_id} ssh command: {printable}")
        db.set_fields(
            task_id,
            delegate_log=f"[dry-run] host={host_name} ssh_cmd={printable}",
            actor="cto",
        )
        return db.get_task(task_id)

    # Local temp copy of the rendered prompt, scp'd to the box rather than
    # crossing the wire as ssh command-line text — it can be thousands of
    # words and contain quotes/non-ASCII the remote shell would re-mangle.
    tmp_task_md = ROOT / "state" / f".remote-task-{task_id}.md"
    tmp_task_md.parent.mkdir(parents=True, exist_ok=True)
    tmp_task_md.write_text(prompt, encoding="utf-8")
    try:
        r = subprocess.run(["scp", str(tmp_task_md), f"{ssh_alias}:{remote_task_file}"],
                           capture_output=True, text=True, timeout=REMOTE_SSH_TIMEOUT_S)
        if r.returncode != 0:
            raise RuntimeError(f"scp of TASK.md failed: {r.stderr}")
    finally:
        tmp_task_md.unlink(missing_ok=True)

    info(f"spawn remote task={task_id} host={host_name} role={role_name} deploy={deploy_actions}")
    r = subprocess.run(cmd, capture_output=True, text=True,
                       timeout=REMOTE_LAUNCH_TIMEOUT_S)
    lines = [ln for ln in (r.stdout or "").splitlines() if ln.strip()]
    if r.returncode != 0 or not lines:
        detail = (r.stderr or r.stdout or "").strip()[:1000]
        error(f"remote spawn failed task={task_id} host={host_name}: {detail}")
        db.update_status(task_id, "failed",
                         delegate_log=f"remote spawn ({host_name}) failed: {detail}",
                         actor="cto")
        return db.get_task(task_id)

    for ln in lines[:-1]:
        if ln.startswith("GITHUB_SSH_ROUTE="):
            info(f"task={task_id} host={host_name} {ln}")

    try:
        pid = int(lines[-1].strip())
    except ValueError:
        error(f"remote spawn task={task_id}: could not parse pid from last line: {lines[-1]!r}")
        db.update_status(task_id, "failed",
                         delegate_log=f"remote spawn ({host_name}): unparseable pid line {lines[-1]!r}",
                         actor="cto")
        return db.get_task(task_id)

    db.update_status(
        task_id, "in_progress",
        pid=pid, host=host_name, worktree=remote_worktree, branch=branch,
        assigned_agent=role_name, actor="cto",
    )
    success(f"remote DEV spawned task={task_id} host={host_name} pid={pid}")
    return db.get_task(task_id)


async def delegate_task(task_id: str, *, wait: bool = False,
                         timeout_s: float = DEFAULT_TIMEOUT_S,
                         kickoff: str | None = None,
                         host: str | None = None,
                         dry_run: bool = False) -> dict:
    """Open DEV in a new iTerm tab. Fire-and-forget by default.

    With the Stop-hook relay + cto.log auto-inject + DB poll, the CTO no
    longer needs to block waiting for the DEV to finish. Pass wait=True
    to restore the legacy blocking behavior (rarely useful).

    `kickoff`: text typed into the new tab after spawn (IRON-RULES §29).
    Defaults to `DEFAULT_KICKOFF`. Pass an explicit string to override,
    or `""` (empty) to suppress — empty is discouraged outside tests.

    `host`: which host (config/hosts.yaml key) to spawn on. Resolution is
    explicit arg > `tasks.host` (set by a prior spawn or create_task) >
    `'mac'`. A resolved host other than 'mac' skips every Mac-specific step
    below (iTerm, tmux, local worktree) and hands off entirely to
    `_spawn_remote` — see docs/design/multi-host-workers.md Phase 1.
    `dry_run`: for a remote host only — print the exact ssh command instead
    of running it. No-op for host='mac'."""
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

    # Host resolution (Phase 1): explicit arg > tasks.host > 'mac'. Computed
    # here (not just at the spawn branch below) because the browser cap
    # check right after this needs to know the TARGET host, not just
    # whether it's remote.
    resolved_host = host if host is not None else (task.get("host") or "mac")

    # ADDENDUM 3 (CTO 2026-09-07) — CEO rule: one browser_operator, one
    # Chrome tab, never a pile-up. Four operators sharing the Mac's Chrome
    # in one morning destroyed a tab group, caused a sign-out, and blocked
    # two runs. Same treatment as a touches collision below: status
    # 'conflict' + a delegate_log line, so the CTO's existing
    # "wait and re-delegate" loop handles it unchanged — no new status, no
    # new retry mechanism.
    if role_name == "browser_operator":
        cap = get_host(resolved_host).get("max_browser_operators")
        if cap is not None:
            live = sum(
                1
                for status in _BROWSER_OPERATOR_ACTIVE_STATUSES
                for t in db.list_tasks(status=status, role="browser_operator", limit=500)
                if (t.get("host") or "mac") == resolved_host
                and _operator_counts_as_live(t, resolved_host)
            )
            if live >= cap:
                warn(f"browser cap blocked task={task_id}: {live}/{cap} on {resolved_host}")
                db.update_status(
                    task_id, "conflict",
                    delegate_log=f"browser cap: {live}/{cap} operators live on {resolved_host}",
                    actor="cto",
                )
                return db.get_task(task_id)

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

    # Host routing (Phase 1): resolved_host was already computed above (the
    # browser cap check needed it too). Everything below this point
    # (worktree creation, iTerm/tmux, kickoff, the claim watchdog) is
    # Mac-only — a non-mac host hands off entirely to _spawn_remote, which
    # has its own worktree/spawn/report path over git.
    if resolved_host != "mac":
        db.set_fields(task_id, spawned_at=db.now_iso(), actor="cto")
        try:
            return await _spawn_remote(task, resolved_host, dry_run=dry_run)
        except Exception as e:
            if touches:
                db.release_task_locks(task_id, project_key)
            error(f"remote spawn setup failed task={task_id} host={resolved_host}: {e}")
            db.update_status(
                task_id, "failed",
                delegate_log=f"remote spawn setup failed ({resolved_host}): {e}",
                actor="cto",
            )
            return db.get_task(task_id)

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

    _warn_if_stale_code()
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
        dev_cmd = f"{cto_env}{WORKER_LAUNCHER} {role_name} {task_id}"
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

    # Catch the silent-death modes (dead reused tab / a worker that never
    # claimed). This used to be skipped for the tmux backend, on the theory
    # that runners.watchdog covered it. It does not cover it in time: the
    # watchdog reports minutes-to-half-an-hour later and to nobody in this
    # session, so a 100%-reproducible spawn failure read as success here and
    # stayed invisible for an hour (2026-08-15, `No module named
    # runners.dev_init` after a rename the running session had not loaded).
    # Verifying the CLAIM is what makes any spawn breakage self-reporting --
    # stale in-process code, a bad venv, a renamed module, an exhausted
    # quota all look identical from the outside and all surface here.
    _spawn_background(_verify_claimed(task_id, role_name, owner_cto, owner_role,
                                        kickoff_text=kickoff_text,
                                        tmux_sess=tmux_sess))

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
