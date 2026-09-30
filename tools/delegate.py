"""CTO delegates to DEV: opens an iTerm tab running a live Claude Code TUI.

Replaces the old headless subprocess model. Each DEV becomes its own
visible tab so the user can watch the work in real time, identical UI to
the CTO chat. The CTO blocks on a DB poll until the DEV calls the
`submit_report` MCP tool (status → 'review') or fails.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from lib import db, mesh
from lib import router as host_router
from lib.config import (
    display_for, get_project, host as get_host,
    project_path_for_host, role as get_role,
    self_host, worker_session_name as get_worker_session_name,
)
from lib.notify import info, success, error, warn
from lib.proc import pid_alive
from tools import disk_queue
from tools import send_to_cto
from tools import storage_policy
from tools import tmux_session as tmux
from tools import workdir
from tools.worktree import _exclude_in_worktree, branch_name, create_worktree

# Every CLI the org knows how to drive a worker with (task-adbc6f43). Kept
# local to this module rather than lib/config.py — that file is not a
# declared `touches` path for this task (ADR 0020 self_repo_guard); adding a
# fourth runner means updating this tuple AND at least one host's
# `runners:` list in config/hosts.yaml, neither alone is enough to spawn one.
KNOWN_RUNNERS = ("claude", "codex", "agy")


def _host_runners(host_name: str) -> list[str]:
    """Runners `host_name` can spawn (config/hosts.yaml `runners:` list).

    Defaults to `['claude']` when a host declares no list at all — fails
    CLOSED (unlike remote_control_args' fail-open default), because an
    unlisted runner on an unverified host is exactly the "discovering it at
    spawn time" failure mode this column exists to prevent."""
    return list(get_host(host_name).get("runners") or ["claude"])


def _validate_runner(runner: str, host_name: str) -> None:
    """Raise ValueError (loud, before spawning) unless `runner` is known AND
    available on `host_name`. Two distinct messages on purpose — "codex
    doesn't exist" and "codex exists but not on this host" point at two
    different fixes."""
    if runner not in KNOWN_RUNNERS:
        raise ValueError(f"unknown runner: {runner!r}. Known: {list(KNOWN_RUNNERS)}")
    available = _host_runners(host_name)
    if runner not in available:
        raise ValueError(
            f"runner {runner!r} not available on host {host_name!r}. "
            f"Available there: {available}"
        )


def _runner_branch_name(runner: str, role_name: str, task_id: str) -> str:
    """Branch a worker pushes to. `claude` keeps today's role-based scheme
    (`agent/<role>-<task>`, unchanged — regression risk if renamed, every
    existing merge/poller path keys on it). An external runner (codex, agy)
    gets `agent/<runner>-<task>` instead (Hard Rule: "External runners push
    agent/<runner>-<task> only") — named by WHICH CLI produced it, since
    codex/agy are less trusted than our own WORKER.md-following claude
    (docs/ops/agent-runners.md §4: codex exits 0 after doing nothing)."""
    if runner == "claude":
        return branch_name(role_name, task_id)
    return f"agent/{runner}-{task_id}"


# ---------------------------------------------------------------------------
# Artefact gate (task-adbc6f43) — a runner is finished only when what it
# actually PRODUCED says so, never its own process exit code. `codex exec`
# returns exit 0 after writing nothing (docs/ops/agent-runners.md §4;
# upstream openai/codex#19309, #46246, #9091 are all open reports of the
# same). `agy` is more honest (non-zero + AGY_ERROR JSON on stderr) but gets
# the identical gate — no runner is trusted on its own word (Hard Rule).
#
# Kept in this module (not lib/) since lib/ is not a declared `touches` path
# for this task (ADR 0020 self_repo_guard) and tools/delegate.py already
# owns the rest of the runner machinery above. Read-only beyond git
# ls-remote/fetch/rev-list — never checks anything out, never merges, never
# runs `run_tests` itself beyond calling the injected callback. Wiring this
# into an automatic loop (branch_poller, merge_task) is a separate decision
# left to the caller: running an arbitrary repo's test suite unattended on
# every poll tick has its own safety/perf tradeoffs this function does not
# make for you.
# ---------------------------------------------------------------------------

class GateResult:
    """`bool(result)` is the pass/fail; `.reasons` is the ordered trail of
    every check that ran, so a failure log always says WHICH check failed,
    not just that one did."""

    def __init__(self, ok: bool, reasons: list[str] | None = None):
        self.ok = ok
        self.reasons = reasons or []

    def __bool__(self) -> bool:
        return self.ok

    def __repr__(self) -> str:
        return f"GateResult(ok={self.ok}, reasons={self.reasons!r})"


def _git(cmd: list[str], *, cwd: str | None = None,
        timeout: float = 20) -> subprocess.CompletedProcess:
    """subprocess.run that never raises — a bad/offline git remote must read
    as a clean gate failure, never an unhandled exception."""
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                              timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        return subprocess.CompletedProcess(cmd, 1, "", str(e))


def gate_commit_landed(repo_path: str, branch: str, base: str) -> tuple[bool, str]:
    """True iff `branch` exists on origin AND carries >=1 commit ahead of
    `base`. Fetches both refs first (read-only beyond that — never checks
    anything out)."""
    r = _git(["git", "ls-remote", "origin", f"refs/heads/{branch}"], cwd=repo_path)
    if r.returncode != 0 or not r.stdout.strip():
        return False, f"branch {branch!r} not found on origin"

    fr = _git(["git", "fetch", "origin", branch, base], cwd=repo_path)
    if fr.returncode != 0:
        return False, f"git fetch origin {branch} {base} failed: {(fr.stderr or '').strip()[:300]}"

    cr = _git(["git", "rev-list", "--count", f"origin/{base}..origin/{branch}"], cwd=repo_path)
    if cr.returncode != 0:
        return False, f"git rev-list failed: {(cr.stderr or '').strip()[:300]}"
    out = cr.stdout.strip()
    try:
        n = int(out) if out else 0
    except ValueError:
        return False, f"unparseable rev-list count: {out!r}"
    if n < 1:
        return False, f"branch {branch!r} has 0 commits ahead of {base!r}"
    return True, f"{n} commit(s) ahead of {base}"


def gate_codex_turn_completed(transcript_text: str | None) -> tuple[bool, str]:
    """Scan a codex --json JSONL transcript for a `turn.completed` event
    with no `turn.failed` seen before it. Never trusts codex's own process
    exit code — this is the honest signal instead (docs/ops/agent-runners.md
    §3-4). A missing/empty transcript is a failure, not "unknown": no
    transcript means no proof the run ever completed.

    Non-JSON lines (stderr noise interleaved into the same log file by
    spawn-worker.ps1's `*>` redirect) are skipped rather than treated as an
    error — the events are still JSONL even when other text surrounds them."""
    if not transcript_text or not transcript_text.strip():
        return False, "no codex --json transcript found"
    saw_failed = False
    for line in transcript_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        etype = event.get("type") or (event.get("msg") or {}).get("type")
        if etype == "turn.failed":
            saw_failed = True
        elif etype == "turn.completed":
            if saw_failed:
                return False, "turn.failed seen before turn.completed"
            return True, "turn.completed with no preceding turn.failed"
    return False, "no turn.completed event in transcript"


def artefact_gate(*, runner: str, repo_path: str, branch: str, base: str,
                  run_tests, codex_transcript: str | None = None) -> GateResult:
    """The full gate. Every check must pass; the first failure short-
    circuits (no point running the test suite against a branch with no
    commit on it). `run_tests` is `Callable[[], tuple[int, str]]`, injected
    so this function enforces WHAT must be true without deciding HOW the
    suite is run (checkout strategy, which command, which host)."""
    reasons: list[str] = []

    ok_commit, commit_msg = gate_commit_landed(repo_path, branch, base)
    reasons.append(commit_msg)
    if not ok_commit:
        return GateResult(False, reasons)

    if runner == "codex":
        ok_codex, codex_msg = gate_codex_turn_completed(codex_transcript)
        reasons.append(codex_msg)
        if not ok_codex:
            return GateResult(False, reasons)

    rc, output = run_tests()
    if rc != 0:
        reasons.append(f"test suite failed (exit {rc}): {output[-500:]}")
        return GateResult(False, reasons)
    reasons.append("test suite passed")
    return GateResult(True, reasons)


ROOT = Path(__file__).resolve().parent.parent

STORAGE_POLICY = ROOT / "config" / "storage-policy.yaml"
DEFAULT_DISK_ORANGE_GB = 5.0


def _disk_orange_floor_gb() -> float:
    """Tiny private loader for config/storage-policy.yaml `gauge.orange`
    (GB) — ADR 0030. A shared tools/storage_policy.py loader is being built
    separately (task brief) — do not create/import it here."""
    try:
        data = yaml.safe_load(STORAGE_POLICY.read_text(encoding="utf-8"))
        return float((data or {}).get("gauge", {}).get("orange", DEFAULT_DISK_ORANGE_GB))
    except (OSError, ValueError, TypeError):
        return DEFAULT_DISK_ORANGE_GB


def _scope_owners(feature: str) -> str | list[str] | None:
    """Raw `scope[<feature>]` value from config/storage-policy.yaml (ADR
    0030 §8; CEO widened all six features to "all" 2026-09-23). "all" —
    every task, including owner_cto=None; a list — only those owner_cto
    ids; missing `scope` key, missing `feature` key, or an unreadable
    policy file → None (fail closed: a feature nobody scoped applies to
    nobody, same as before the scope map existed)."""
    try:
        data = yaml.safe_load(STORAGE_POLICY.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None
    scope = data.get("scope")
    if not isinstance(scope, dict):
        return None
    value = scope.get(feature)
    if value == "all":
        return "all"
    if isinstance(value, list):
        return [str(o) for o in value]
    return None


def _scope_applies(feature: str, owner_cto: str | None) -> bool:
    """True if ADR 0030 feature `feature` (disk_floor, sparse_worktree,
    reclaim, work_dir, space_check, media_guard) applies to `owner_cto`
    per config/storage-policy.yaml `scope`. "all" → every task, including
    owner_cto=None. A list → membership only, owner_cto=None never
    matches. Missing scope/feature → False."""
    owners = _scope_owners(feature)
    if owners == "all":
        return True
    if isinstance(owners, list):
        return bool(owner_cto) and str(owner_cto) in owners
    return False


def _run_storage_reclaim() -> tuple[int, int]:
    """Run tools/storage_reclaim.py's plan()+apply() for every owner the
    `reclaim` scope covers (not just this task's own owner_cto — a scoped
    CTO can hold several in-flight task worktrees at once, and "all"
    covers every task in tasks.db). Returns (freed_bytes, item_count).

    Seam for tests: monkeypatch `delegate._run_storage_reclaim` directly
    (same pattern as `_free_gb`) rather than storage_reclaim's internals —
    a delegate-trigger test cares whether this ran, not how it deletes."""
    from tools import storage_reclaim
    policy = storage_policy.load(str(STORAGE_POLICY))
    owners = _scope_owners("reclaim") or []
    items = storage_reclaim.plan(str(db.DB_PATH), policy, owners)
    deleted = storage_reclaim.apply(items)
    return sum(i.get("bytes", 0) for i in deleted), len(deleted)


def _work_dir_for(task_id: str, owner_cto: str | None) -> str | None:
    """Create this task's Work/<task_id>/ folder (Work/RULES.md rule 1-2,
    tools/workdir.py) and return its path, so the spawned worker's env can
    carry WORK_DIR next to WORKER_CTO_ID — `work_dir` scope only (ADR 0030
    §8); an out-of-scope owner_cto gets None, unchanged from before this
    task. Creation failure never blocks a spawn already past the
    disk-floor gate above — it's logged and the worker starts without
    WORK_DIR."""
    if not _scope_applies("work_dir", owner_cto):
        return None
    try:
        return str(workdir.create(task_id))
    except Exception as e:
        warn(f"workdir.create failed task={task_id}: {e} (spawning without WORK_DIR)")
        return None


def _free_gb(path: str = "/") -> float:
    """Free space on `path` in GB. Module-level seam so tests can inject a
    fake value directly (monkeypatch this function) rather than an env var
    — an env var could disable the guard in prod (ADR 0030)."""
    return shutil.disk_usage(path).free / (1024 ** 3)


def _remote_free_gb(ssh_alias: str) -> float | None:
    """Free space (GB) on a spoke's `/` via `df`, or None if the probe
    itself fails — unreachable host, no `df`, unparseable output. Never
    raises. Mirrors `runners/branch_poller.remote_pid_alive`'s fail-OPEN
    contract on purpose (task-a5c0549d, disk-floor host-awareness fix):
    a broken probe must never become a false floor that silently queues
    every remote spawn to a host this check couldn't even reach. `-Pk`
    (POSIX output format, 1024-byte blocks) keeps the column layout stable
    across whatever `df` a spoke ships (GNU coreutils or BusyBox)."""
    try:
        r = subprocess.run(
            ["ssh", ssh_alias, "df", "-Pk", "/"],
            capture_output=True, text=True, timeout=REMOTE_SSH_TIMEOUT_S,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    lines = (r.stdout or "").strip().splitlines()
    if len(lines) < 2:
        return None
    fields = lines[1].split()
    if len(fields) < 4:
        return None
    try:
        avail_kb = float(fields[3])
    except ValueError:
        return None
    return avail_kb / (1024 ** 2)


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
    if not pid or resolved_host != self_host():
        return True
    try:
        return pid_alive(int(pid))
    except (TypeError, ValueError):
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
        raw = p.read_text(encoding="utf-8").strip()
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
                     owner_role: str | None = None,
                     work_dir: str | None = None) -> str:
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

    `work_dir`: this task's Work/<task_id>/ path (pilot scope only, ADR
    0030) — stamped into env WORK_DIR next to WORKER_CTO_ID. None for a
    non-pilot task, exactly as before this export existed.
    """
    display = display_for(role)
    tab_title = f"{display} ({task_id})"
    cto_env = f"export WORKER_CTO_ID='{owner_cto}' && " if owner_cto else ""
    work_env = f"export WORK_DIR='{work_dir}' && " if work_dir else ""
    if tmux_attach:
        # Trailing `; exit $?` (ADDENDUM 2, CTO 2026-09-07 — CEO rule:
        # ending a worker must close its window, never just the process).
        # Without it, when the tmux session dies the tab drops to a bare
        # shell prompt and stays open — iTerm's "Close Sessions On End" is
        # on, but the shell itself never ends, so it never fires. Mirrors
        # the non-tmux branch below, which has carried this since GH #27.
        cmd = (
            f"printf '\\\\033]1;{tab_title}\\\\007' && "
            f"{cto_env}{work_env}tmux attach -t {tmux_attach}; exit $?"
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
            f"{cto_env}{work_env}{WORKER_LAUNCHER} {role} {task_id}; exit $?"
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
    it. lib.proc probes existence without a signal (os.kill(pid, 0) is
    CTRL_C on Windows). A pid owned by another user is still alive."""
    return pid_alive(pid)


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


def _live_worker_alive(task: dict) -> bool:
    """True when the worker that last claimed `task` is still running here:
    the pid it stamped at claim is alive and, on the tmux backend, its
    session still exists. The session check is what keeps a recycled pid
    (an unrelated process that inherited the number) from passing."""
    if not _pid_alive(task.get("pid")):
        return False
    sess = task.get("tmux_session")
    if not sess:
        return True
    try:
        return tmux.has_session(sess)
    except Exception:
        return False


REOPEN_LIVE_MSG = (
    "The CTO reopened this task (iteration {iteration}). TASK.md was rewritten "
    "with the CTO feedback on top -- re-read it, act on the feedback, then "
    "submit_report again."
)


async def _resume_live_worker(task: dict, role_name: str) -> dict | None:
    """GH #158 part 3: hand a reopened task back to the worker still running it.

    reopen_task leaves the row pending + unassigned but keeps the pid the
    worker stamped at claim. Spawning from there claims nothing: tmux.create
    returns early for a session that already exists, and the iTerm path
    reuses the tab and skips the kickoff. _verify_claimed then marked the live
    worker `failed` 25 s later -- and `failed` is terminal, so the surface
    reaper closes the live process after REAP_GRACE_S. Measured 3x in 7 days:
    task-a63759d5 (2026-09-17), task-adbc6f43 and task-ad534f86 (2026-09-22).

    Returns None when no live worker owns the row (the caller spawns as
    before); otherwise restores the claim, queues the reopen pointer to the
    worker's mailbox, and returns the row -- no spawn, no claim watchdog.
    """
    task_id = task["id"]
    if not _live_worker_alive(task):
        return None
    # claim_task is atomic on status='pending' AND assigned_agent IS NULL, so
    # a racing delegate or a genuine claim wins cleanly and we just report it.
    if not db.claim_task(task_id, agent=role_name):
        return db.get_task(task_id)
    from tools.send_to_worker import send as send_to_worker_send
    msg = REOPEN_LIVE_MSG.format(iteration=task.get("iteration"))
    try:
        await asyncio.to_thread(send_to_worker_send, task_id, msg)
        note = "reopen pointer queued to its mailbox"
    except Exception as e:  # the claim stands; the CTO must message it
        note = f"mailbox send FAILED ({e}) -- message the worker yourself"
        warn(f"task={task_id}: {note}")
    info(f"task={task_id} reopened on a live worker pid={task.get('pid')}: "
         f"claim restored, no respawn; {note}")
    db.set_fields(
        task_id,
        delegate_log=(f"reopened on a live worker (pid {task.get('pid')}): "
                      f"claim restored instead of a respawn; {note}"),
        actor="cto",
    )
    return db.get_task(task_id)


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
                                owner_cto=owner_cto, owner_role=owner_role,
                                work_dir=_work_dir_for(task_id, owner_cto))
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


def _bytes_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _org_default_branch() -> str:
    """Branch the org repo's deploy files are read from (the `mooniex-agents`
    project's default branch)."""
    try:
        return get_project("mooniex-agents")["default_branch"]
    except Exception:
        return "main"


def _fetch_origin(base: str) -> None:
    """Refresh origin/<base> in the hub's own repo. A failed fetch only warns:
    the ref left by the last fetch is still merged code, unlike a working
    tree, and `_origin_blob` fails loudly when the ref is missing."""
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "fetch", "origin", base],
                           capture_output=True, text=True,
                           timeout=REMOTE_SSH_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError) as e:
        warn(f"deploy: git fetch origin {base} failed ({e}) — using the last fetched ref")
        return
    if r.returncode != 0:
        warn(f"deploy: git fetch origin {base} failed "
             f"({(r.stderr or '').strip()[:200]}) — using the last fetched ref")


def _origin_blob(base: str, rel: str) -> bytes | None:
    """Bytes of `rel` at origin/<base> (`git show`), or None when origin has
    no such file. Deploys never read the hub's working tree: a dirty or
    unmerged local copy must not reach a spoke (task-6f6e5179)."""
    r = subprocess.run(["git", "-C", str(ROOT), "show", f"origin/{base}:{rel}"],
                       capture_output=True, timeout=REMOTE_SSH_TIMEOUT_S)
    return r.stdout if r.returncode == 0 else None


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
                          dry_run: bool = False,
                          base: str | None = None) -> list[str]:
    """scp spawn-worker.ps1 + the role docs a remote DEV needs, but only
    the files missing or whose content changed (sha256 compare) — so a
    routine delegate call is a no-op scp-wise once the box is warm. Returns
    the actions taken (or, in dry-run, that would be taken).

    The bytes come from `git show origin/<base>:<path>` after a fetch, never
    from the hub's working tree (task-6f6e5179)."""
    ssh_alias = host_cfg["ssh"]
    agents_root = host_cfg["agents_root"]
    sep = "\\" if host_cfg.get("os") == "windows" else "/"
    files = list(_REMOTE_DEPLOY_FILES) + [(f"roles/{role_name}.md", f"roles/{role_name}.md")]
    base = base or _org_default_branch()

    actions: list[str] = []
    if not dry_run:
        _fetch_origin(base)
    dirs_needed: set[str] = set()
    to_copy: list[tuple[bytes, str, str]] = []
    for local_rel, remote_rel in files:
        remote_abs = f"{agents_root}{sep}{remote_rel.replace('/', sep)}"
        if dry_run:
            actions.append(f"[dry-run] would check/deploy origin/{base}:{local_rel} -> {ssh_alias}:{remote_abs}")
            continue
        blob = _origin_blob(base, local_rel)
        if blob is None:
            continue
        if _remote_sha256(ssh_alias, remote_abs) == _bytes_sha256(blob):
            continue
        to_copy.append((blob, local_rel, remote_abs))
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
    with tempfile.TemporaryDirectory() as td:
        for blob, local_rel, remote_abs in to_copy:
            staged = Path(td) / Path(local_rel).name
            staged.write_bytes(blob)
            r = subprocess.run(["scp", str(staged), f"{ssh_alias}:{remote_abs}"],
                               capture_output=True, text=True, timeout=REMOTE_SSH_TIMEOUT_S)
            if r.returncode != 0:
                raise RuntimeError(f"deploy scp failed for {staged.name}: {r.stderr}")
            actions.append(f"deployed {staged.name} -> {remote_abs}")
    return actions


# Linux/Contabo deploy (Phase 2, task-a5c0549d; extended task-378523bb).
# Separate from _ensure_remote_deploy/_remote_sha256 above (which stay
# windows-only and untouched) rather than branching those on os= -- keeps
# the winbox path byte-identical with zero risk. Role docs
# (roles/_worker_shared.md, roles/_worker_remote.md, roles/<role>.md) are
# NOT deployed here — unlike winbox's dedicated non-git deploy folder,
# Contabo's agents_root IS a live git checkout of this same repo (two CTO
# sessions run out of it today), so the launcher script reads those files
# directly from its own already-cloned location instead of a second copy
# that could drift or dirty that checkout's working tree.
#
# (source path in the org repo at origin/<base>, path relative to the spoke's
# agents_root). The launcher lands in the untracked `.launch/`, never in the
# spoke's tracked `scripts/`: every spawn used to overwrite the spoke's
# tracked scripts/spawn-worker-remote.sh (and hook-self-repo-guard.py) with
# the Mac's working-tree copies and dirty /opt/MoonieXHQ/Agents/Core
# (task-6f6e5179). A worktree carries origin's own guard, so the guard is no
# longer deployed at all.
_LINUX_LAUNCHER_REL = ".launch/spawn-worker-remote.sh"
_REMOTE_DEPLOY_FILES_LINUX = (
    ("scripts/spawn-worker-remote.sh", _LINUX_LAUNCHER_REL),
)


def _remote_sha256_posix(ssh_alias: str, remote_path: str) -> str | None:
    """SHA256 of a file already on a POSIX box (uppercase hex, matching
    `_local_sha256`'s case), or None if absent/unreachable — never raises,
    mirrors `_remote_sha256`'s contract for the windows side. Tries
    `sha256sum` (coreutils, the Debian/Ubuntu default) then falls back to
    `shasum -a 256` (macOS/BSD) in case a spoke's userland differs."""
    check = (
        f"if [ -f {shlex.quote(remote_path)} ]; then "
        f"sha256sum {shlex.quote(remote_path)} 2>/dev/null | cut -d' ' -f1 "
        f"|| shasum -a 256 {shlex.quote(remote_path)} 2>/dev/null | cut -d' ' -f1; fi"
    )
    try:
        r = subprocess.run(
            ["ssh", ssh_alias, check],
            capture_output=True, text=True, timeout=REMOTE_SSH_TIMEOUT_S,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    out = (r.stdout or "").strip().upper()
    return out or None


def _ensure_remote_deploy_linux(host_cfg: dict, *, dry_run: bool = False,
                                base: str | None = None) -> list[str]:
    """scp each of _REMOTE_DEPLOY_FILES_LINUX onto a Linux spoke, only when
    missing or changed (sha256 compare). The bytes are the `git show
    origin/<base>:<path>` blob after a fetch — never the hub's working tree,
    so a dirty or unmerged local edit cannot reach a spoke. Nothing is ever
    written under the spoke's tracked `scripts/` (task-6f6e5179)."""
    ssh_alias = host_cfg["ssh"]
    agents_root = host_cfg["agents_root"]
    base = base or _org_default_branch()
    actions: list[str] = []
    if not dry_run:
        _fetch_origin(base)
    for local_rel, remote_rel in _REMOTE_DEPLOY_FILES_LINUX:
        remote_abs = f"{agents_root}/{remote_rel}"

        if dry_run:
            actions.append(f"[dry-run] would check/deploy origin/{base}:{local_rel} -> {ssh_alias}:{remote_abs}")
            continue
        blob = _origin_blob(base, local_rel)
        if blob is None:
            continue
        if _remote_sha256_posix(ssh_alias, remote_abs) == _bytes_sha256(blob):
            continue

        remote_dir = remote_abs.rsplit("/", 1)[0]
        r = subprocess.run(["ssh", ssh_alias, f"mkdir -p {shlex.quote(remote_dir)}"],
                           capture_output=True, text=True, timeout=REMOTE_SSH_TIMEOUT_S)
        if r.returncode != 0:
            raise RuntimeError(f"remote mkdir failed: {(r.stderr or r.stdout or '').strip()}")
        with tempfile.TemporaryDirectory() as td:
            staged = Path(td) / Path(local_rel).name
            staged.write_bytes(blob)
            r = subprocess.run(["scp", str(staged), f"{ssh_alias}:{remote_abs}"],
                               capture_output=True, text=True, timeout=REMOTE_SSH_TIMEOUT_S)
        if r.returncode != 0:
            raise RuntimeError(f"deploy scp failed for {Path(local_rel).name}: {r.stderr}")
        r = subprocess.run(["ssh", ssh_alias, f"chmod +x {shlex.quote(remote_abs)}"],
                           capture_output=True, text=True, timeout=REMOTE_SSH_TIMEOUT_S)
        if r.returncode != 0:
            raise RuntimeError(f"chmod +x failed for {remote_abs}: {(r.stderr or r.stdout or '').strip()}")
        actions.append(f"deployed {Path(local_rel).name} -> {remote_abs}")
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
    model = role_cfg.get("model") or "claude-sonnet-5-5"
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


def _render_remote_runner_args(role_name: str, host_name: str, runner: str) -> str:
    """Flags rendered on the Mac and handed to spawn-worker.ps1 as
    `-ClaudeArgs` for `runner`.

    `claude` reuses `_render_remote_claude_args` UNCHANGED — same code path,
    same output, byte-identical regression guard (task-adbc6f43 scope: "claude
    argv unchanged from today"). codex and agy take no equivalent flags from
    here: neither CLI has claude's --model/--effort/--allowed-tools shape
    (docs/ops/agent-runners.md §1), and inventing flags neither measured
    invocation actually uses would be guessing, not threading through what's
    proven. spawn-worker.ps1 builds their full argv itself from -Task/-Role/
    the worktree path it already computes (positional prompt, -C/--add-dir,
    etc.) — see its Runner dispatch in the launch step."""
    if runner == "claude":
        return _render_remote_claude_args(role_name, host_name)
    return ""


# W0.3b: the variables a local launcher run keeps. Over ssh the launcher gets
# a fresh sshd environment; run locally it would inherit the hub's own
# (ORG_DB_URL, session ids, tokens), and when it starts the first tmux server
# the codex/agy worker would inherit that too. Keep only what bash, git and
# tmux need to find binaries, HOME and a locale.
_LOCAL_LAUNCHER_ENV_KEYS = ("PATH", "HOME", "USER", "LOGNAME", "LANG",
                            "LC_ALL", "SHELL", "TERM", "TMPDIR")


def _local_launcher_env() -> dict[str, str]:
    return {k: os.environ[k] for k in _LOCAL_LAUNCHER_ENV_KEYS if k in os.environ}


def _queued_remote_attempts(task_id: str) -> int:
    """How many times this task has been put in `queued_remote`: one
    `status_queued_remote` event per unreachable attempt (db.update_status).
    Counted in the ledger, not over a window of recent events: the retry cap
    (lib/mesh.max_attempts) reads this, and a row that logs many other events
    must not push its old attempts out of view and so never reach the cap."""
    with db.get_conn(readonly=True) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM events WHERE task_id=? AND kind=?",
            (task_id, "status_queued_remote"),
        ).fetchone()
    return int(row["n"])


def give_up_queued_remote(task_id: str, host_name: str, attempts: int) -> dict:
    """Fail a `queued_remote` row whose host never answered `attempts` times
    (the cap, lib/mesh.max_attempts). `failed` releases the row's path locks
    in db.update_status (RELEASING_STATUSES), the same way a failed launcher
    run does. The owner is told once, through the error path and the owner's
    mailbox; a row already moved off the wait (the far side took it, another
    watchdog failed it) is returned untouched and not announced, so a repeat
    call cannot notify twice. Returns the row."""
    row = db.get_task(task_id) or {}
    if row.get("status") not in ("queued_remote", "pending"):
        return row
    cap = mesh.max_attempts()
    msg = (f"mesh spawn_worker on {host_name} unreachable {attempts} times "
           f"(cap {cap}, {mesh.ENV_MAX_ATTEMPTS}); giving up, task failed and its path locks released")
    db.update_status(task_id, "failed", actor="cto", delegate_log=msg[:1000])
    error(f"mesh spawn gave up task={task_id} host={host_name} attempts={attempts}")
    try:
        send_to_cto.send(task_id, msg, role=row.get("role"), cto_id=row.get("owner_cto"),
                         owner_role=row.get("owner_role") or "cto")
    except Exception as e:  # the row is already failed: a mailbox error must not undo that
        warn(f"mesh spawn gave up task={task_id}: notify owner failed: {e}")
    return db.get_task(task_id)


def mesh_spawn_worker(task_id: str, host_name: str) -> dict:
    """Ask `host_name` to spawn `task_id` through lib/mesh (W2.3,
    ORG_MESH_DISPATCH). The whole remote spawn is one node_dispatch verb,
    `spawn_worker <task_id>`: the far side reads the row by id and runs its own
    delegate_task, so nothing rendered here (prompt, launcher args) crosses.
    Returns the fresh task row. Never raises for an unreachable host.

    The verb wants a `pending` row whose host is NULL or that box, so the row is
    put there first. No answer from the host (MeshUnreachable) leaves the row
    `queued_remote` with the host kept: the watchdog retries it, and path locks
    stay held. An answer that says no (a refusal or a failed spawn) fails the
    task, like a failed launcher run, unless the far side already moved the row."""
    row = db.get_task(task_id)
    if row["status"] != "pending":
        db.update_status(task_id, "pending", host=host_name, actor="cto")
    elif row.get("host") != host_name:
        db.set_fields(task_id, host=host_name, actor="cto")
    try:
        reply = mesh.dispatch(host_name, "spawn_worker", task_id)
    except mesh.MeshUnreachable as e:
        # No answer does not prove the verb did not run. On a shared ledger the far
        # side may already have moved the row (in_progress, blocked_host, ...):
        # only a row still `pending` is ours to queue, or the retry would spawn twice.
        seen = db.get_task(task_id) or {}
        if seen.get("status") != "pending":
            warn(f"mesh spawn task={task_id} host={host_name}: no answer ({e}), but the row "
                 f"is already {seen.get('status')}; not queued")
            return seen
        attempt = _queued_remote_attempts(task_id) + 1
        warn(f"mesh spawn queued task={task_id} host={host_name} attempt={attempt}: {e}")
        db.update_status(
            task_id, "queued_remote", host=host_name, actor="cto",
            delegate_log=f"mesh spawn_worker on {host_name} unreachable "
                         f"(attempt {attempt}): {e}"[:1000],
        )
        return db.get_task(task_id)
    if reply.get("ok"):
        success(f"mesh spawn task={task_id} host={host_name}: {reply.get('result')}")
        return db.get_task(task_id)
    detail = str(reply.get("error") or reply)[:1000]
    warn(f"mesh spawn refused task={task_id} host={host_name}: {detail}")
    if (db.get_task(task_id) or {}).get("status") == "pending":
        db.update_status(task_id, "failed", actor="cto",
                         delegate_log=f"mesh spawn_worker on {host_name} said no: {detail}")
    return db.get_task(task_id)


async def _spawn_remote(task: dict, host_name: str, *,
                        dry_run: bool = False, local: bool = False) -> dict:
    """Spawn a DEV on a remote spoke host (winbox today; a Contabo launcher
    is Phase 2, a non-goal of this task). No org MCP, no tmux, no iTerm —
    the worktree is cloned in from git by windows/spawn-worker.ps1, and the
    DEV reports back by pushing its branch + REPORT.md. This function's job
    ends at recording host/branch/worktree/pid on the task row;
    runners/branch_poller.py takes it from there.

    `local` (W0.3b, task-26988fe3): `host_name` is THIS machine (a Linux hub
    delegating a codex/agy task to itself). The linux launcher is then run
    with plain `bash <checkout>/scripts/spawn-worker-remote.sh <args>` — same
    args, same prompt on stdin, same output parsing as over ssh, but no ssh
    and no copy into `.launch/`: the checkout's own tracked script IS the
    launcher. Linux only."""
    from runners.worker_init import _build_prompt

    task_id = task["id"]
    role_name = task["role"]
    project_key = task["project"]

    host_cfg = get_host(host_name)  # raises ValueError if host_name is unknown

    # W2.3: with ORG_MESH_DISPATCH on, a remote spawn is one node_dispatch verb
    # over the org_dispatch key (lib/mesh.py), not the launcher ssh below. Off
    # (the default) this block is skipped and every line after it is unchanged.
    if mesh.enabled() and not local and host_name != self_host():
        if dry_run:
            try:
                printable = " ".join(shlex.quote(c) for c in
                                     mesh.build_argv(host_name, "spawn_worker", (task_id,)))
            except Exception as e:  # a dry run reports, it never fails the task
                printable = f"<not dispatchable: {e}>"
            info(f"[dry-run] task={task_id} host={host_name} mesh command: {printable}")
            db.set_fields(task_id, delegate_log=f"[dry-run] host={host_name} mesh_cmd={printable}",
                          actor="cto")
            return db.get_task(task_id)
        info(f"spawn remote task={task_id} host={host_name} role={role_name} transport=mesh")
        return await asyncio.to_thread(mesh_spawn_worker, task_id, host_name)

    os_name = host_cfg.get("os")
    if os_name not in ("windows", "linux"):
        raise NotImplementedError(
            f"host {host_name!r} (os={os_name}) has no remote launcher yet — "
            f"only winbox (Phase 1) and contabo (Phase 2, task-a5c0549d) are "
            f"wired; docs/design/multi-host-workers.md §4"
        )
    if local and os_name != "linux":
        raise NotImplementedError(
            f"local launcher transport is linux-only (host {host_name!r} os={os_name})"
        )
    ssh_alias = host_cfg.get("ssh")
    if not ssh_alias and not local:
        raise ValueError(f"host {host_name!r} has no ssh alias configured")

    # H3 (task-3cc9b119): _route_runner writes runner_model to the row with
    # set_fields and does not refresh the caller's dict, so read that one
    # field back fresh. Only that field: the rest of the dict is the caller's.
    try:
        fresh_task = db.get_task(task_id)
    except Exception:
        fresh_task = None
    if fresh_task and fresh_task.get("runner_model") and not task.get("runner_model"):
        task = {**task, "runner_model": fresh_task["runner_model"]}

    # Runner resolution + validation (task-adbc6f43). NULL on the task row
    # means "claude" (every pre-migration row, unchanged). Validated here —
    # loudly, before spawning — rather than discovered as a missing binary
    # on winbox after ssh has already fired.
    runner = (task.get("runner") or "claude").strip().lower()
    _validate_runner(runner, host_name)

    proj = get_project(project_key)
    repo_url = proj.get("remote")
    if not repo_url:
        raise ValueError(f"project {project_key!r} has no `remote:` — cannot clone it onto {host_name}")
    repo_url = _ssh_remote_url(repo_url)
    repo_path = project_path_for_host(project_key, host_name)  # raises if not routable
    worktree_root = host_cfg["worktrees"]
    branch = _runner_branch_name(runner, role_name, task_id)
    base = proj["default_branch"]
    # Windows paths join with '\\'; linux (contabo, task-a5c0549d) with '/'.
    sep = "\\" if os_name == "windows" else "/"
    remote_worktree = f"{worktree_root}{sep}{project_key}__{role_name}__{task_id}"

    claude_args = _render_remote_runner_args(role_name, host_name, runner)
    role_cfg = get_role(role_name)
    model = role_cfg.get("model") or "claude-sonnet-5-5"
    effort = role_cfg.get("effort") or "high"
    # ADDENDUM 1 (CTO 2026-09-07): machine-prefixed session name, rendered
    # once here (single source of truth) and handed to the launcher rather
    # than recomputed in PowerShell.
    session_name = get_worker_session_name(host_name, role_name, task_id,
                                           task.get("title") or "")

    if os_name == "windows":
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
            f"-SessionName {_ps_quote(session_name)} -Runner {_ps_quote(runner)}"
        )
        # H3: the model the router picked for codex/agy; spawn-worker.ps1
        # validates it again and falls back when it is absent.
        if runner != "claude" and task.get("runner_model"):
            remote_cmd += f" -RunnerModel {_ps_quote(str(task['runner_model']))}"
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

        for ln in lines:
            if ln.startswith("GITHUB_SSH_ROUTE="):
                info(f"task={task_id} host={host_name} {ln}")

        # GH #153: the probe's own verdict must GATE success, not just get
        # logged. spawn-worker.ps1's current version never exits early on
        # GITHUB_SSH_ROUTE=unreachable (the probe there is advisory-only) — it
        # can keep going and still print a valid pid on the last line, which
        # would otherwise read as a clean spawn. Checked before the returncode
        # branch below so it also wins when the dead route later makes git
        # itself fail (non-zero exit) — "unreachable" is the more specific,
        # more actionable diagnosis either way.
        route_line = next(
            (ln for ln in lines if ln.startswith("GITHUB_SSH_ROUTE=unreachable")), None,
        )
        if route_line is not None:
            kill_note = ""
            maybe_pid = lines[-1].strip() if lines else ""
            if maybe_pid.isdigit():
                # ps1 launched a worker despite the dead route (current
                # version) — coordination note in the task brief: since ps1 is
                # the paired task's file (not touched here), the hub kills
                # what it launched instead of relying on ps1 to refuse first.
                try:
                    kr = subprocess.run(
                        ["ssh", ssh_alias, "taskkill", "/PID", maybe_pid, "/T", "/F"],
                        capture_output=True, text=True, timeout=REMOTE_SSH_TIMEOUT_S,
                    )
                    kill_ok = kr.returncode == 0
                    kill_detail = "ok" if kill_ok else (kr.stderr or kr.stdout or "").strip()[:200]
                except (OSError, subprocess.SubprocessError) as e:
                    kill_ok, kill_detail = False, str(e)[:200]
                kill_note = f"; killed leaked pid {maybe_pid} on {host_name} ({kill_detail})"
                info(f"task={task_id} host={host_name} killed leaked pid={maybe_pid} "
                    f"(route unreachable) ok={kill_ok}")
            detail = (
                f"{route_line} — git route from {host_name} dead — fix "
                f"network/keys, then delegate again{kill_note}"
            )
            error(f"remote spawn blocked task={task_id} host={host_name}: {detail}")
            db.update_status(task_id, "blocked_host", delegate_log=detail, actor="cto")
            return db.get_task(task_id)

        refused_line = next((ln for ln in lines if ln.startswith("SPAWN_REFUSED=")), None)
        if refused_line is not None:
            reason = refused_line[len("SPAWN_REFUSED="):]
            warn(f"remote spawn refused task={task_id} host={host_name}: {reason}")
            db.update_status(
                task_id, "conflict",
                delegate_log=f"remote spawn refused ({host_name}): {reason}",
                actor="cto",
            )
            return db.get_task(task_id)

        if r.returncode != 0 or not lines:
            detail = (r.stderr or r.stdout or "").strip()[:1000]
            error(f"remote spawn failed task={task_id} host={host_name}: {detail}")
            db.update_status(task_id, "failed",
                             delegate_log=f"remote spawn ({host_name}) failed: {detail}",
                             actor="cto")
            return db.get_task(task_id)

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
            assigned_agent=role_name, runner=runner, actor="cto",
        )
        success(f"remote DEV spawned task={task_id} host={host_name} runner={runner} pid={pid}")
        return db.get_task(task_id)

    # os_name == "linux" (contabo, Phase 2, task-a5c0549d). Bash + tmux
    # instead of powershell + a scheduled task — no session-0/session-1 GUI
    # boundary to cross, so tmux new-session -d IS the detached worker;
    # see scripts/spawn-worker-remote.sh for the launcher itself.
    if local:
        remote_script = str(ROOT / "scripts" / "spawn-worker-remote.sh")
        deploy_actions = [f"local launcher {remote_script} (nothing to deploy)"]
    else:
        deploy_actions = _ensure_remote_deploy_linux(host_cfg, dry_run=dry_run)
        remote_script = f"{host_cfg['agents_root']}/{_LINUX_LAUNCHER_REL}"

    prompt = _build_prompt(task, proj, remote_worktree)

    # GH #180 (task-378523bb): the hub already knows this task's declared
    # touches — hand them to the spoke at spawn time instead of leaving the
    # spawned worktree to depend on its own (possibly unsynced) tasks.db
    # copy. Base64 so no quoting ever breaks crossing two shells (this
    # process's ssh argv, then spawn-worker-remote.sh's own re-quoting into
    # launch.sh). No secret in here — task_id/project/role/host/owner_cto
    # and repo-relative paths only.
    task_meta_b64 = base64.b64encode(
        json.dumps(_task_meta(task, host_name)).encode("utf-8")
    ).decode("ascii")

    script_args = [
        "--task", task_id, "--project", project_key, "--role", role_name,
        "--branch", branch, "--base", base, "--repo-url", repo_url,
        "--repo-path", repo_path, "--worktree-root", worktree_root,
        "--claude-args", claude_args, "--model", model, "--effort", effort,
        "--session-name", session_name, "--runner", runner,
        "--task-meta-b64", task_meta_b64,
    ]
    transport = "local" if local else "ssh"
    if local:
        cmd = ["bash", remote_script, *script_args]
    else:
        remote_cmd = "bash " + shlex.quote(remote_script) + " " + " ".join(
            shlex.quote(a) for a in script_args
        )
        cmd = ["ssh", ssh_alias, remote_cmd]

    if dry_run:
        printable = " ".join(shlex.quote(c) for c in cmd)
        info(f"[dry-run] task={task_id} host={host_name} deploy: {deploy_actions}")
        info(f"[dry-run] task={task_id} {transport} command: {printable}")
        db.set_fields(
            task_id,
            delegate_log=f"[dry-run] host={host_name} {transport}_cmd={printable}",
            actor="cto",
        )
        return db.get_task(task_id)

    # The prompt travels over the transport's own stdin (input=; ssh forwards
    # it, a local bash reads it directly) rather than a scp'd
    # file first — plain OpenSSH forwards local stdin to the remote command
    # by default, with none of the console-encoding hazards that made
    # winbox's PowerShell path scp a file instead (see spawn-worker.ps1's own
    # TaskFile comment). spawn-worker-remote.sh's TASK.md write is the last
    # thing on the box that reads stdin.
    info(f"spawn remote task={task_id} host={host_name} role={role_name} "
         f"transport={transport} deploy={deploy_actions}")
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                       timeout=REMOTE_LAUNCH_TIMEOUT_S,
                       env=_local_launcher_env() if local else None)
    lines = [ln for ln in (r.stdout or "").splitlines() if ln.strip()]

    refused_line = next((ln for ln in lines if ln.startswith("SPAWN_REFUSED=")), None)
    if refused_line is not None:
        reason = refused_line[len("SPAWN_REFUSED="):]
        warn(f"remote spawn refused task={task_id} host={host_name}: {reason}")
        db.update_status(
            task_id, "conflict",
            delegate_log=f"remote spawn refused ({host_name}): {reason}",
            actor="cto",
        )
        return db.get_task(task_id)

    spawned_line = next((ln for ln in lines if ln.startswith("SPAWNED ")), None)
    if r.returncode != 0 or spawned_line is None:
        detail = (r.stderr or r.stdout or "").strip()[:1000]
        error(f"remote spawn failed task={task_id} host={host_name}: {detail}")
        db.update_status(task_id, "failed",
                         delegate_log=f"remote spawn ({host_name}) failed: {detail}",
                         actor="cto")
        return db.get_task(task_id)

    m = re.match(r"^SPAWNED pid=(\d+) session=(\S+) worktree=(.+)$", spawned_line)
    if not m:
        error(f"remote spawn task={task_id}: could not parse SPAWNED line: {spawned_line!r}")
        db.update_status(task_id, "failed",
                         delegate_log=f"remote spawn ({host_name}): unparseable SPAWNED line {spawned_line!r}",
                         actor="cto")
        return db.get_task(task_id)

    pid = int(m.group(1))
    tmux_session_id = m.group(2)
    reported_worktree = m.group(3)

    db.update_status(
        task_id, "in_progress",
        pid=pid, host=host_name, worktree=reported_worktree, branch=branch,
        assigned_agent=role_name, runner=runner, tmux_session=tmux_session_id,
        actor="cto",
    )
    success(f"remote DEV spawned task={task_id} host={host_name} runner={runner} "
           f"pid={pid} tmux={tmux_session_id}")
    return db.get_task(task_id)


def _task_meta(task: dict, host_name: str) -> dict:
    """The `.org-task.json` sidecar payload (GH #180, task-378523bb): the
    hub already knows this task's declared touches, so the worktree gets them
    at spawn time instead of depending on its own (possibly unsynced)
    tasks.db copy. No secret in here — ids, role, host, owner and
    repo-relative paths only."""
    try:
        touches = json.loads(task.get("touches") or "[]")
    except (TypeError, ValueError):
        touches = []
    if not isinstance(touches, list):
        touches = []
    return {
        "task_id": task["id"],
        "project": task["project"],
        "role": task["role"],
        "host": host_name,
        "owner_cto": task.get("owner_cto"),
        "touches": touches,
        "runner_model": task.get("runner_model"),
    }


def _write_task_sidecar(worktree: str | Path | None, meta: dict) -> Path | None:
    """Write `<worktree>/.org-task.json` (mode 600) and keep it out of git,
    the way spawn-worker-remote.sh does for a remote spawn. Best-effort: a
    worktree that is not there yet or a write failure only warns — the guard
    falls back to the ledger, exactly as before this sidecar existed."""
    if not worktree or not Path(worktree).is_dir():
        return None
    path = Path(worktree) / ".org-task.json"
    try:
        _exclude_in_worktree(Path(worktree), (path.name,))
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(meta, f)
        os.chmod(path, 0o600)
    except OSError as e:
        warn(f"task sidecar not written for {meta.get('task_id')}: {e}")
        return None
    return path


async def _spawn_local(task: dict, proj: dict, *, kickoff: str | None = None,
                       touches: list | tuple = ()) -> dict:
    """Start a DEV on THIS host and return the task row.

    Mac (`sys.platform == "darwin"`): unchanged — the project's
    `spawn_backend` decides between a plain iTerm tab and tmux + an attached
    iTerm tab. Any other platform: tmux only, no iTerm/osascript/`open` at
    all. A spawn that fails leaves the row `failed` (the caller returns it
    as is); otherwise the claim watchdog is already scheduled."""
    task_id = task["id"]
    role_name = task["role"]
    project_key = task["project"]
    if sys.platform == "win32":
        # Neither backend below exists here: no tmux, and WORKER_LAUNCHER is
        # bash. Windows starts a worker as a one-shot scheduled task in session 1
        # (windows/spawn-worker.ps1, wired in W3.3). Until then fail the row with
        # the reason; tmux.create would die with a bare FileNotFoundError and
        # leave a pending row that looks like a spawn in flight.
        msg = ("local spawn is not available on Windows yet: no tmux and no bash "
               "launcher here. Delegate from the Mac or Contabo with host='winbox' "
               "(remote launcher), or wait for the scheduled-task spawn (W3.3).")
        error(f"{task_id}: {msg}")
        db.update_status(task_id, "failed", delegate_log=msg, actor="cto")
        return db.get_task(task_id)
    # GH #180: the same `.org-task.json` sidecar a remote spawn writes, so the
    # self-repo guard reads this task's touches from the worktree itself.
    _write_task_sidecar((db.get_task(task_id) or task).get("worktree"),
                        _task_meta(task, self_host()))
    # iTerm, osascript and `open` exist on the Mac only (IRON-RULES §29: the
    # Mac keeps its visible iTerm tab). Every other platform runs the worker
    # detached in the tmux backend and never touches them (task-6f6e5179).
    on_darwin = sys.platform == "darwin"
    backend = (proj.get("spawn_backend") or "iterm").lower() if on_darwin else "tmux"
    tmux_sess: str | None = None
    ttyd_port: int | None = None
    ttyd_pid: int | None = None

    owner_cto = task.get("owner_cto")
    # Pre-migration rows have owner_cto but NULL owner_role → default "cto"
    # (mirrors runners/worker_init.py's WORKER_CTO_ROLE fallback for the same rows).
    owner_role = task.get("owner_role") or "cto"
    # ADR 0030 / Work/RULES.md rule 1-2: pilot scope only.
    work_dir_path = _work_dir_for(task_id, owner_cto)

    if backend == "tmux":
        tmux_sess = tmux.session_name_for(task_id)
        # Record the tmux session BEFORE the DEV process exists. The DEV
        # claims (pending → in_progress) within seconds of tmux.create; a
        # status write after that point would silently regress the claim.
        db.set_fields(task_id, tmux_session=tmux_sess, actor="cto")
        cto_env = f"export WORKER_CTO_ID='{owner_cto}' && " if owner_cto else ""
        work_env = f"export WORK_DIR='{work_dir_path}' && " if work_dir_path else ""
        dev_cmd = f"{cto_env}{work_env}{WORKER_LAUNCHER} {role_name} {task_id}"
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
                # Best-effort open in default browser (Mac only).
                if on_darwin:
                    subprocess.run(["open", tmux.url_for(ttyd_port)], check=False)
            except Exception as e:
                warn(f"ttyd start failed (continuing without web UI): {e}")
                ttyd_port = None
                ttyd_pid = None

        if ttyd_port or ttyd_pid:
            db.set_fields(task_id, ttyd_port=ttyd_port, ttyd_pid=ttyd_pid,
                          actor="cto")

    spawn_result = "spawned"
    if on_darwin:
        try:
            spawn_result = _spawn_iterm_tab(role_name, task_id,
                                            tmux_attach=tmux_sess,
                                            owner_cto=owner_cto,
                                            owner_role=owner_role,
                                            work_dir=work_dir_path)
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

    return db.get_task(task_id)


def _route_runner(task: dict, role_name: str, host: str) -> str | None:
    from tools import route  # noqa: PLC0415 — outside try so PermissionError escapes
    refusal = route.check_override(task)
    if refusal:
        db.set_fields(task["id"], delegate_log=refusal, actor="cto")
        warn(refusal)
        raise PermissionError(refusal)
    try:
        if (task.get("runner")
                or (task.get("model_hint") or "").strip().lower() == "claude"
                or os.environ.get("ORG_ROUTER", "").strip().lower() == "off"):
            return None

        touches = task.get("touches")
        if isinstance(touches, str):
            try:
                touches = json.loads(touches)
            except Exception:
                touches = []
        elif touches is None:
            touches = []
        brief = task.get("description")

        choice = route.pick_runner(role_name, host, touches=touches, brief=brief)
        if choice is None:
            return None
        line = f"router: {choice.runner} {choice.model} [{choice.bucket}] — {choice.reason}"
        # set_fields, not update_status: the status must not be rewritten
        # from this (possibly stale) dict or logged as a transition.
        db.set_fields(task["id"], runner=choice.runner,
                      runner_model=choice.model, delegate_log=line,
                      actor="cto")
        info(line)
        return choice.runner
    except Exception as e:
        warn(f"router skipped task={task.get('id')}: {e}")
        return None


async def _route_host(task: dict, host: str | None) -> tuple[str | None, str]:
    """(host, delegate_log line) for a delegate with ORG_HOST_ROUTER on.

    Only reached with the flag on. An explicit `host` argument or a non-NULL
    `tasks.host` wins as before (line starts `manual:`); otherwise
    lib/router.pick_host chooses, off the event loop because it may do a cold
    quota read through tools.route. A None host means "no host fits"."""
    if host is not None:
        return host, host_router.manual_line(host, "host= argument")
    if task.get("host"):
        return task["host"], host_router.manual_line(task["host"], "tasks.host")
    pick = await asyncio.to_thread(host_router.pick_host, task)
    return pick.host, pick.line


def _keep_host_line(task_id: str, line: str) -> None:
    """_route_runner overwrites delegate_log with its own `router:` line; put
    the host decision back in front of it so the row shows both. (The
    overwritten value also survives in the events table.)"""
    current = (db.get_task(task_id) or {}).get("delegate_log") or ""
    if line not in current:
        db.set_fields(task_id, delegate_log=f"{line}\n{current}" if current else line,
                      actor="cto")


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
    `self_host()` (this machine, W0.3). A resolved host other than this
    machine skips every local step below (iTerm/tmux, local worktree) and
    hands off entirely to `_spawn_remote` — see
    docs/design/multi-host-workers.md Phase 1. With env ORG_HOST_ROUTER on
    (default off) a task with neither an arg nor a `tasks.host` gets its host
    from `lib/router.pick_host`; no fitting host leaves it pending.
    `dry_run`: never starts a worker. A remote host prints the exact ssh
    command; a codex/agy task on a Linux hub (W0.3b) prints the local `bash
    scripts/spawn-worker-remote.sh ...` command; a same-host `_spawn_local`
    task logs what it would have started and returns with its locks
    released."""
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

    # Host resolution (Phase 1): explicit arg > tasks.host > self_host(). Computed
    # here, ahead of storage reclaim/disk-floor below (task-a5c0549d,
    # CTO 2026-09-24: a spawn bound for contabo was refused/queued for the
    # MAC's disk, even though its worktree, git clone and worker process all
    # live on the spoke — task-43b6514d, "queued for disk — 3.9 GB free"
    # while Contabo itself had plenty). resolved_host is also what the
    # browser cap check right after needs.
    #
    # W2.6/H2 (PLAN-auto-dispatch §4): with ORG_HOST_ROUTER on (default OFF),
    # a task that names no host is given one by lib/router.pick_host, and no
    # fitting host means the task stays pending with `no_host: <why>` in
    # delegate_log and NO spawn. An explicit host= / tasks.host still wins and
    # is logged as `manual:`. With the flag off the else-branch below is the
    # resolution exactly as it was before.
    host_line = None
    if host_router.enabled():
        resolved_host, host_line = await _route_host(task, host)
        db.set_fields(task_id, delegate_log=host_line, actor="cto")
        if resolved_host is None:
            warn(f"{host_line} task={task_id}")
            return db.get_task(task_id)
    else:
        resolved_host = host if host is not None else (task.get("host") or self_host())
    this_host = self_host()

    # Storage reclaim (ADR 0030 §2, task-44963fee): below the orange band,
    # REBUILD-tier directories inside a scoped owner's OWN task worktrees
    # (node_modules, .venv, __pycache__, ...) are deleted automatically,
    # before the disk-floor check below even takes its own reading — so a
    # spawn that would otherwise be refused by the floor gets a chance to
    # clear it first. `reclaim` scope only (ADR 0030 §8): never another
    # session's worktree, never a project under ~/MoonieXHQ/Projects, unless
    # scope[reclaim] is "all". Out-of-scope tasks skip this block entirely.
    # A reclaim failure never blocks the spawn beyond what the floor check
    # below already decides. Mac-only (unaffected by the host-aware floor
    # below) — a remote task has no Mac-side worktree of its own to reclaim
    # from, and freeing Mac disk opportunistically is harmless either way.
    reclaim_applies = resolved_host == this_host and _scope_applies("reclaim", task.get("owner_cto"))
    if reclaim_applies:
        pre_free_gb = _free_gb()
        try:
            policy = storage_policy.load(str(STORAGE_POLICY))
            pre_band = storage_policy.band(pre_free_gb, policy)
        except storage_policy.PolicyError as e:
            pre_band = None
            warn(f"storage reclaim: policy load failed task={task_id}: {e}")
        if pre_band in ("orange", "red"):
            try:
                freed_bytes, freed_count = _run_storage_reclaim()
                if freed_count:
                    info(f"storage reclaim task={task_id}: freed {freed_bytes} "
                         f"bytes across {freed_count} item(s), band={pre_band}")
            except Exception as e:
                warn(f"storage reclaim failed task={task_id}: {e}")

    # Disk floor (ADR 0030): the Mac hit 0 bytes free on 2026-09-23 and every
    # tool died. Checked before anything else touches this task's row — no
    # locks, no worktree, no status write — so a refusal here leaves the row
    # exactly as it was and is trivially retried once space is back. Returns
    # the task row dict (not a bare string) like every other refusal path
    # here (depends_on, touches collision) — lib/org_tools_registry.py:196
    # does `_slim_task(await do_delegate(...))` and delegate_parallel_tasks
    # gathers results, both of which assume a dict (CTO reopen feedback,
    # task-bfa778ab iter1: a str return broke the MCP tool on a low-disk spawn).
    # `disk_floor` scope: only tasks whose owner_cto scope[disk_floor]
    # covers — other sessions' work is never refused by this gate until the
    # CEO widens it.
    #
    # Gates the disk that will actually HOLD this spawn's worktree
    # (task-a5c0549d, CTO 2026-09-24 review): resolved_host == 'mac' reads
    # the Mac's own free space (re-measured here, not reused from
    # pre_free_gb above, so it sees the post-reclaim reading when reclaim
    # ran); any other host probes THAT box over ssh instead — its worktree,
    # git clone and worker process live there, not on the Mac, so the Mac's
    # disk is not what will run out. `_remote_free_gb` fails OPEN (None) on
    # an unreachable host or missing `df` — same shape as
    # runners/branch_poller.remote_pid_alive's liveness probe — so a broken
    # probe can never become a false floor that blocks every remote spawn.
    disk_floor_applies = _scope_applies("disk_floor", task.get("owner_cto"))
    orange_gb = _disk_orange_floor_gb()
    free_gb: float | None
    if resolved_host == this_host:
        free_gb = _free_gb()
    elif dry_run:
        # `dry_run`'s own contract (this function's docstring): "print the
        # exact ssh command instead of running it" — a real ssh probe here
        # would be exactly the real network call dry_run promises not to
        # make, even though it's only a disk check. Skipped (never
        # refuses/queues a dry-run), not faked, so a dry-run's log/db writes
        # stay identical to before this host-awareness fix existed.
        free_gb = None
    else:
        try:
            host_cfg_for_disk = get_host(resolved_host)
        except ValueError:
            host_cfg_for_disk = None
        free_gb = (_remote_free_gb(host_cfg_for_disk["ssh"])
                  if host_cfg_for_disk and host_cfg_for_disk.get("ssh") else None)
    if disk_floor_applies and free_gb is not None and free_gb < orange_gb:
        # ADR 0030 §D / task-dbe47b9b (CEO 2026-09-23: "สั่งเป็นกฎอย่างเดียว
        # ไม่ได้ ต้องทำระบบเข้าคิวไว้ด้วย รันตามคิว"): a refused spawn no
        # longer just dies here — it joins tools/disk_queue.py's FIFO queue
        # (state/disk_queue.jsonl) and runners/watchdog.py's scan_once drains
        # it, oldest first, one per tick, once free space clears
        # gauge.orange + 1 GB. Status is left exactly as it was (pending),
        # matching the pre-queue behaviour this branch already had.
        #
        # KNOWN GAP (task-a5c0549d, not fixed here — runners/watchdog.py is
        # not a declared touches path for this task): _drain_disk_queue()'s
        # own resume check (runners/watchdog.py DISK_QUEUE_RESUME_MARGIN_GB)
        # still gates EVERY queued entry on the Mac's free space alone,
        # regardless of which host it was queued for. A task queued here for
        # a spoke whose own disk is fine will still wait on the Mac's disk
        # clearing before the watchdog even attempts to drain it — this
        # function's re-resolution of `resolved_host` fixes the INITIAL
        # refusal to gate on the right box, but the drain's resume gate
        # needs the same per-entry host awareness to fully close the loop.
        host_note = "" if resolved_host == this_host else f" on {resolved_host}"
        ahead = disk_queue.enqueue(task_id, task.get("owner_cto"))
        msg = (f"disk red{host_note}: {free_gb:.1f} GB free < {orange_gb:.1f} GB floor "
               f"— spawn refused (ADR 0030) — queued for disk ({ahead} ahead)")
        warn(f"disk floor blocked task={task_id}: {msg}")
        db.set_fields(task_id, delegate_log=msg, actor="cto")
        try:
            send_to_cto.send(
                task_id,
                f"queued for disk ({ahead} ahead) — {free_gb:.1f} GB free{host_note}, "
                f"needs {orange_gb:.1f} GB. Will spawn automatically once "
                f"space clears.",
                role=task.get("role"), cto_id=task.get("owner_cto"),
                owner_role=task.get("owner_role") or "cto",
            )
        except Exception as e:  # never let a mailbox failure break the refusal
            warn(f"disk queue: notify owner failed task={task_id}: {e}")
        return db.get_task(task_id)

    role_name = task["role"]
    project_key = task["project"]

    proj = get_project(project_key)
    if role_name not in proj["agents_allowed"]:
        raise PermissionError(f"role {role_name} not allowed on project {project_key}")

    # Off the event loop: a cold quota read is an ssh + a CLI call.
    routed = await asyncio.to_thread(_route_runner, task, role_name, resolved_host)
    if routed:
        task["runner"] = routed
    if host_line:
        _keep_host_line(task_id, host_line)

    # Runner pre-flight (task-adbc6f43): reject an unknown/unavailable runner
    # loudly, here, before any worktree/ssh/iTerm work starts — not discovered
    # later as a missing binary on the spoke. NULL on the row means "claude"
    # (every pre-migration task, unchanged). Applies to EVERY host, not just
    # remote spokes: a bad runner value must never reach runners/worker_init.py
    # either.
    resolved_runner = (task.get("runner") or "claude").strip().lower()
    try:
        _validate_runner(resolved_runner, resolved_host)
    except ValueError as e:
        warn(f"runner rejected task={task_id}: {e}")
        db.update_status(task_id, "failed", delegate_log=f"runner rejected: {e}", actor="cto")
        return db.get_task(task_id)

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
                if (t.get("host") or this_host) == resolved_host
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
    # (worktree creation, iTerm/tmux, kickoff, the claim watchdog) runs on
    # THIS host — any other host hands off entirely to _spawn_remote, which
    # has its own worktree/spawn/report path over git.
    #
    # W0.3b (task-26988fe3): a Linux hub delegating a codex/agy task to ITSELF
    # takes the same launcher path over a LOCAL transport (bash, no ssh).
    # `_spawn_local` starts Claude only; codex and agy need the launcher's own
    # runner blocks (tmux, launch.sh, commit + push of the branch). On the Mac
    # a local agy task still goes to `_spawn_local`; claude always does.
    local_launcher = (resolved_host == this_host
                      and resolved_runner != "claude"
                      and sys.platform.startswith("linux"))
    if dry_run and resolved_host == this_host and not local_launcher:
        # A dry run starts nothing on any path. This one (a same-host
        # `_spawn_local`) used to ignore the flag and spawn a real worker:
        # a lane A smoke on Contabo, 2026-09-30, got a worktree and a live
        # tmux session from `delegate_task(..., dry_run=True)`. Drop the
        # locks taken above, say what would have run, touch nothing else.
        if touches:
            db.release_task_locks(task_id, project_key)
        msg = (f"[dry-run] host={this_host} local {resolved_runner} spawn: "
               f"would create the worktree and tmux "
               f"{tmux.session_name_for(task_id)}; nothing started")
        info(msg)
        db.set_fields(task_id, delegate_log=msg, actor="cto")
        return db.get_task(task_id)
    if resolved_host != this_host or local_launcher:
        db.set_fields(task_id, spawned_at=db.now_iso(), actor="cto")
        try:
            return await _spawn_remote(task, resolved_host, dry_run=dry_run,
                                       local=local_launcher)
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
        sparse_applies = _scope_applies("sparse_worktree", task.get("owner_cto"))
        wt_info = create_worktree(project_key, role_name, task_id,
                                  sparse=sparse_applies)
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
        #
        # Before any of that: a reopened task whose worker is still running
        # goes back to that worker, not to a spawn that cannot claim
        # (GH #158 part 3 — see _resume_live_worker).
        resumed = await _resume_live_worker(task, role_name)
        if resumed is not None:
            return resumed
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
    #
    # `host` is also written here (W0.1, docs/design/org-mesh.md C1): this
    # branch is local-spawn only (the resolved_host != this_host branch above
    # already returned), so the DEV about to be spawned runs on THIS host.
    # A self_host() failure fails the spawn loudly rather than guessing.
    db.set_fields(task_id, spawned_at=db.now_iso(), host=this_host,
                  actor="cto")

    row = await _spawn_local(task, proj, kickoff=kickoff, touches=touches)
    if row.get("status") == "failed":
        return row

    if not wait:
        success(f"DEV spawned task={task_id} (fire-and-forget)")
        return row

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
