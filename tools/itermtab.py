"""iTerm tab lifecycle helpers.

Spawn is owned by tools/delegate.py:_spawn_iterm_tab. This module owns the
close side: when a task reaches `done` (post-merge) git_ops.merge_task
calls close_tab(task_id) so the DEV tab disappears and the desktop stays
clean. Tabs for tasks that are still pending / in_progress / review /
blocked stay open.

Tab title set by delegate is `<RoleDisplay> (<full task_id>)`. We match
the full task_id substring, with a 6-char fallback for tabs spawned
before the full-id title change.

## Safety: which tabs we will close

close_tab only closes a tab whose title contains the requested `task_id`
substring AND that task_id starts with `task-`. Tabs we deliberately
never close:
  - CTO Chat / CTO Log / Dev Logs (spawn-cto.sh side tabs — no task_id).
  - User-opened terminals (shells without a task_id in title).
  - Tabs from a hypothetical interactive `spawn Web Designer` REPL whose
    title does not carry a task_id.

A tab is therefore only closeable when it was spawned by the delegate
path (`tools/delegate.py:_spawn_iterm_tab`) or by `tools/resume_dev.py:
_spawn_resume_tab`. Both set the title `<Role> (task-<id>)`.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# iTerm2 Python API — used only by the arrange / attention helpers at the
# bottom of this module (AppleScript cannot reorder tabs or set tab
# color/badge, so those features need the API). Optional: if the package is
# absent or the API is disabled, every API helper degrades to a no-op so the
# close_tab / close_session osascript path keeps working everywhere.
try:
    import iterm2 as _iterm2
except ImportError:  # pragma: no cover - depends on host setup
    _iterm2 = None

_ROOT = Path(__file__).resolve().parent.parent
_LOCKS = _ROOT / "state" / "locks"


def _task_pid(task_id: str) -> int | None:
    """Look up the pid recorded for a task in state/tasks.db.

    Returns None on any failure (task not found, no pid recorded, DB
    unreadable, `lib` not importable from this cwd) so callers fall back
    to the title-match path below — never raises into close_tab.
    """
    try:
        from lib import db
    except ImportError:
        return None
    try:
        task = db.get_task(task_id)
    except Exception:
        return None
    if not task:
        return None
    pid = task.get("pid")
    try:
        return int(pid) if pid else None
    except (TypeError, ValueError):
        return None


def _close_tab_by_pid(pid: int) -> bool:
    """Close the tab whose current session's job pid matches `pid`.

    TRUST BOUNDARY: this function believes the pid it is given. It matches
    on `jobPid` alone and its only guard excludes C-level tabs by title —
    nothing here checks that the process actually belongs to the task the
    caller has in mind. Verifying that is the caller's job (see
    `tools/dev_reap._pid_matches_task`); callers who cannot verify must
    pass `allow_pid=False` to `close_tab` instead of reaching this path.

    GH mooniex-agents#27: title-substring matching (the fallback below)
    is fragile — once a spawned process exits (crash, manual `kill`, or
    `dev_init.py` failing before claiming), the tab's title reverts to a
    plain shell name and can no longer be found by substring, leaving a
    zombie tab open forever. `jobPid` is a real iTerm2 session variable
    (confirmed live against this machine's running tabs) and stays valid
    regardless of title state, so this is tried first. Same C-level
    exclusion as the title-match path below.
    """
    async def factory(conn):
        app = await _iterm2.async_get_app(conn)
        for window in app.windows:
            for tab in window.tabs:
                session = tab.current_session
                if session is None:
                    continue
                try:
                    job_pid = await session.async_get_variable("jobPid")
                except Exception:
                    continue
                try:
                    if job_pid is None or int(job_pid) != pid:
                        continue
                except (TypeError, ValueError):
                    continue
                title = await _session_title(session)
                if any(f"{p} " in title for p in ("CTO", "CMO", "CGO", "CFO")):
                    continue
                await tab.async_close()
                return True
        return False

    return bool(_run_api(factory))


def close_tab(task_id: str, *, allow_pid: bool = True) -> bool:
    """Close the iTerm tab running the given task, by pid first, falling
    back to a title-substring match.

    Returns True if any tab was closed. Safe to call when no matching
    tab exists (returns False).

    `allow_pid=False` skips the pid path and closes by title only. Pass it
    whenever the caller has reason to doubt that the recorded pid is still
    this task's process: `_close_tab_by_pid` trusts the pid it is handed,
    so an unverified one closes whichever tab happens to hold it now —
    which, after any delay long enough for the OS to recycle pids, may
    belong to something entirely unrelated.
    """
    if not task_id or not task_id.startswith("task-"):
        # Refuse to operate on inputs that don't look like a real task id.
        # Protects against accidental empty/garbage matches reaching
        # iTerm and closing the wrong tab.
        return False

    pid = _task_pid(task_id) if allow_pid else None
    if pid is not None and _close_tab_by_pid(pid):
        return True

    fallback = task_id[:6]
    # Both title surfaces are checked (sticky tab name + session badge,
    # same as delegate's spawn matcher) — the session badge flickers to
    # the running process name, which made session-name-only closes miss.
    #
    # C-level tabs carry a live work summary in the title (IRON-RULES §32,
    # scripts/tab-title.sh). If a summary ever mentions a task, a naive
    # task-id match would close the C-level chat itself — so any tab whose
    # title carries a C-level prefix is excluded from closing.
    guard = ('and not (nm contains "CTO ") and not (nm contains "CMO ") '
             'and not (nm contains "CGO ") and not (nm contains "CFO ") '
             'and not (tn contains "CTO ") and not (tn contains "CMO ") '
             'and not (tn contains "CGO ") and not (tn contains "CFO ")')
    script = f'''
tell application "iTerm"
  set closedAny to false
  repeat with w in windows
    set tabsList to tabs of w
    repeat with t in tabsList
      set nm to ""
      try
        set nm to name of current session of t
      end try
      set tn to ""
      try
        set tn to name of t
      end try
      if ((nm contains "{task_id}") or (tn contains "{task_id}")) {guard} then
        close t
        set closedAny to true
      end if
    end repeat
  end repeat
  if not closedAny then
    repeat with w in windows
      set tabsList to tabs of w
      repeat with t in tabsList
        set nm to ""
        try
          set nm to name of current session of t
        end try
        set tn to ""
        try
          set tn to name of t
        end try
        if ((nm contains "{fallback}") or (tn contains "{fallback}")) {guard} then
          close t
          set closedAny to true
        end if
      end repeat
    end repeat
  end if
  if closedAny then
    return "1"
  else
    return "0"
  end if
end tell
'''
    r = subprocess.run(["osascript", "-e", script],
                       capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == "1"


def close_session(role: str, session_id: str) -> bool:
    """Close the iTerm tab owned by role+session_id.

    Enforces four gates: lock file exists, winid is live in iTerm, caller
    env ($CXO_ROLE/$CXO_SESSION_ID) matches, no in-progress task for session.
    Refusals are appended to state/locks/close-refusals.log as JSON lines.
    """
    lock_path = _LOCKS / f"{role}-{session_id}.winid"
    refusals_log = _LOCKS / "close-refusals.log"

    def _refuse(reason: str) -> bool:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "role": role,
            "session_id": session_id,
            "reason": reason,
        }
        try:
            _LOCKS.mkdir(parents=True, exist_ok=True)
            with refusals_log.open("a") as fh:
                fh.write(json.dumps(entry) + "\n")
        except OSError:
            pass
        return False

    # Gate 1: lock file must exist
    if not lock_path.exists():
        return _refuse("lock file missing")

    winid = lock_path.read_text().strip()
    if not winid.isdigit():
        return _refuse(f"lock file malformed: {winid!r}")

    # Gate 2: winid must be in iTerm's live window list
    r = subprocess.run(
        ["osascript", "-e", 'tell application "iTerm2" to return id of windows'],
        capture_output=True, text=True,
    )
    live = "," + r.stdout.strip().replace(" ", "") + ","
    if f",{winid}," not in live:
        return _refuse(f"winid {winid} not in live windows")

    # Gate 3: caller env must match owner
    if os.environ.get("CXO_ROLE") != role or os.environ.get("CXO_SESSION_ID") != session_id:
        return _refuse("caller env mismatch")

    # Gate 4: no in-progress task bound to this session via c_level_sessions
    try:
        import sys as _sys
        _sys.path.insert(0, str(_ROOT))
        from lib.db import db_conn
        with db_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM c_level_sessions "
                "WHERE role = ? AND session_id = ? AND active_task_id IS NOT NULL "
                "AND active_task_id IN (SELECT id FROM tasks WHERE status = 'in_progress')",
                (role, session_id),
            ).fetchone()
        if row is not None:
            return _refuse("session has in-progress task")
    except Exception:
        pass

    # All gates passed — close the window
    script = f"""
tell application "iTerm2"
  repeat with w in windows
    if id of w is {winid} then
      close w
      return "1"
    end if
  end repeat
  return "0"
end tell
"""
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip() == "1":
        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            pass
        return True
    return _refuse("iTerm close failed or window not found")


# ---------------------------------------------------------------------------
# iTerm2 Python API helpers (idea 1: arrange-by-status, idea 2: attention)
#
# Two features pulled from the open-source iTerm2 ecosystem
# (iterm2.com Sort-Tabs example + JasperSui/claude-code-iterm2-tab-status):
#
#   1. arrange_tabs()    — reorder a window's tabs by the IRON-RULES §32
#                          status glyph so the CEO's eye lands on blockers
#                          first (🔴) and finished sessions last (🏁).
#   2. mark_attention()  — make a blocked tab shout: red tab color + badge
#                          (+ optional macOS notification), cleared on unblock.
#
# AppleScript can do neither (no tab `index`, no tab color/badge), so both
# go through the iTerm2 Python API. All of it degrades to a no-op returning
# False/0 when `iterm2` is missing or the API is disabled — see _run_api.
# ---------------------------------------------------------------------------

# Status glyph -> sort rank (IRON-RULES §32). Lower sorts nearer the front of
# the tab bar: blocker first (needs CEO), then active work, done-with-queue,
# idle, fully-finished last. Tabs with no status glyph (user shells, the
# "CTO Log" / "Dev Logs" side tabs) get _NO_GLYPH_RANK and keep their
# relative order at the end.
_GLYPH_RANK = {"🔴": 0, "⏳": 1, "✅": 2, "💤": 3, "🏁": 4}
_NO_GLYPH_RANK = 99

# Default attention color — a strong red (solarized-ish #D6402F).
_ATTENTION_RGB = (214, 64, 47)

# Status glyph -> tab color + badge (IRON-RULES §32). Same glyph set as
# _GLYPH_RANK. rgb=None means "no color" (idle / unrecognized) — the profile
# turns tab color off rather than picking a color for it.
_STATUS_STYLE = {
    "🔴": {"rgb": _ATTENTION_RGB,   "badge": "🔴 รอ CEO"},  # blocked
    "⏳": {"rgb": (219, 173, 33),   "badge": None},          # working
    "✅": {"rgb": (46, 160, 90),    "badge": None},          # batch done, queued
    "🏁": {"rgb": (32, 160, 190),   "badge": None},          # all done, closeable
    "💤": {"rgb": None,             "badge": None},          # idle
}


def _title_rank(title: str) -> int:
    """Sort rank for a tab title, by the first status glyph it contains."""
    for glyph, rank in _GLYPH_RANK.items():
        if glyph in title:
            return rank
    return _NO_GLYPH_RANK


def _run_api(coro_factory, timeout: float = 8.0):
    """Run an iTerm2 API coroutine and return its result, or None.

    coro_factory: callable(connection) -> awaitable. Returns None when the
    `iterm2` package is absent, the API is disabled, no event loop can be
    started, or anything times out. Callers treat None as "API unavailable"
    and degrade to a no-op — this module must never raise into the org's
    merge / spawn paths.
    """
    if _iterm2 is None:
        return None

    async def _guarded():
        conn = await asyncio.wait_for(
            _iterm2.Connection.async_create(), timeout=timeout)
        return await asyncio.wait_for(coro_factory(conn), timeout=timeout)

    try:
        return asyncio.run(_guarded())
    except Exception:
        # RuntimeError (already-running loop), connection refused (API off),
        # asyncio.TimeoutError, etc. — all mean "can't, no-op".
        return None


async def _session_title(session) -> str:
    """Best-effort tab title for a session (the name we set via OSC-0)."""
    try:
        return (await session.async_get_variable("autoName")) or ""
    except Exception:
        return ""


async def _arrange_window(window) -> bool:
    """Reorder one window's tabs by status-glyph rank. True if order changed."""
    tabs = list(window.tabs)
    if len(tabs) < 2:
        return False
    ranked = []
    for orig_index, tab in enumerate(tabs):
        title = await _session_title(tab.current_session)
        # (rank, orig_index) keeps the sort stable: same-rank tabs stay in
        # their current left-to-right order instead of shuffling.
        ranked.append(((_title_rank(title), orig_index), tab))
    ranked.sort(key=lambda pair: pair[0])
    new_order = [tab for _, tab in ranked]
    if new_order == tabs:
        return False  # already sorted — skip the churn / focus flicker
    await window.async_set_tabs(new_order)
    return True


def arrange_tabs(window_id: str | None = None) -> bool:
    """Reorder tabs by status-glyph priority (🔴 ⏳ ✅ 💤 🏁, others last).

    window_id=None reorders the current terminal window; otherwise the
    window whose id matches. Returns True if any tab order changed, False
    on no-op (already sorted, single tab, or API unavailable).
    """
    async def factory(conn):
        app = await _iterm2.async_get_app(conn)
        if window_id is None:
            w = app.current_terminal_window
            return await _arrange_window(w) if w is not None else False
        for w in app.windows:
            if str(w.window_id) == str(window_id):
                return await _arrange_window(w)
        return False

    return bool(_run_api(factory))


def _attention_profile(color_rgb, badge):
    """A write-only profile that turns a tab loud: tab color + badge text.

    Sets the unified AND the light/dark-mode tab-color keys. Profiles with
    "Use separate colors for light and dark mode" enabled (Preferences >
    Profiles > Colors) ignore the plain `Tab Color`/`Use Tab Color` keys
    for rendering — the API call still succeeds silently, the tab just
    never repaints. Setting all three pairs makes this work regardless of
    that per-profile toggle (confirmed against gnachman/iTerm2
    api/library/python/iterm2/iterm2/profile.py, 2026-08-03).
    """
    color = _iterm2.Color(*color_rgb)
    profile = _iterm2.LocalWriteOnlyProfile()
    profile.set_use_tab_color(True)
    profile.set_tab_color(color)
    profile.set_use_tab_color_light(True)
    profile.set_tab_color_light(color)
    profile.set_use_tab_color_dark(True)
    profile.set_tab_color_dark(color)
    if badge is not None:
        profile.set_badge_text(badge)
    return profile


def _clear_profile():
    """A write-only profile that restores a tab to normal (no color/badge)."""
    profile = _iterm2.LocalWriteOnlyProfile()
    profile.set_use_tab_color(False)
    profile.set_use_tab_color_light(False)
    profile.set_use_tab_color_dark(False)
    profile.set_badge_text("")
    return profile


def _reassert_title(tty_path: str | None, title: str | None) -> None:
    """Re-send the OSC-0 Header title after a profile write.

    async_set_profile_properties() (badge/tab-color) resets whatever title
    was showing while that profile is active — confirmed live 2026-07-20:
    a title set right before mark()/clear() reverts to the bare job name
    ("<base> (node)") even seconds later, with no in-between write. The
    profile and the Header title are two independent iTerm mechanisms that
    don't compose; re-sending the title AFTER the profile write is the fix,
    not a race — order alone (title-then-profile) was tested and still lost.
    Best-effort: swallow errors, never let this break the mark/clear call.

    Uses OSC 1 (icon/tab name), not OSC 0: OSC 0 also rewrites the window
    title, which would wipe the Main Tab that tools/maintab.py owns via
    OSC 2 (changed 2026-08-03 with the two-layer tab).
    """
    if not tty_path or not title:
        return
    try:
        with open(tty_path, "w") as f:
            f.write(f"\033]1;{title}\007")
    except OSError:
        pass


async def _apply_to_matching(app, match, profile) -> int:
    """Apply a profile to every session whose title contains `match`."""
    hits = 0
    for window in app.windows:
        for tab in window.tabs:
            for session in tab.sessions:
                title = await _session_title(session)
                if match in title:
                    try:
                        await session.async_set_profile_properties(profile)
                        hits += 1
                    except Exception:
                        pass
    return hits


def _post_notification(title: str, message: str) -> None:
    """Fire a macOS notification (best-effort, never raises)."""
    try:
        subprocess.run(
            ["osascript", "-e",
             f"display notification {json.dumps(message)} "
             f"with title {json.dumps(title)} sound name \"Glass\""],
            capture_output=True, text=True, timeout=5)
    except Exception:
        pass


def mark_attention(match: str, *, color=_ATTENTION_RGB, badge: str = "🔴 รอ CEO",
                   notify_title: str | None = None,
                   notify_msg: str | None = None,
                   tty_path: str | None = None,
                   title: str | None = None) -> bool:
    """Make every tab whose title contains `match` shout for attention.

    Sets a red tab color + a badge on each matching tab, and — only when
    `notify_msg` is given — fires one macOS notification. `match` is a title
    substring: a task-id, a role+session base prefix, or even a glyph.
    `tty_path`/`title`, when both given, re-send the Header title right
    after the profile write (see _reassert_title — the profile write alone
    resets it). Returns True if at least one tab was marked.
    """
    if not match:
        return False

    async def factory(conn):
        app = await _iterm2.async_get_app(conn)
        hits = await _apply_to_matching(app, match, _attention_profile(color, badge))
        _reassert_title(tty_path, title)
        return hits

    hits = _run_api(factory) or 0
    if hits and notify_msg:
        _post_notification(notify_title or "mooniex org", notify_msg)
    return bool(hits)


def clear_attention(match: str, *, tty_path: str | None = None,
                     title: str | None = None) -> bool:
    """Undo mark_attention for tabs whose title contains `match`.

    `tty_path`/`title`: see mark_attention — same title-reassert need.
    """
    if not match:
        return False

    async def factory(conn):
        app = await _iterm2.async_get_app(conn)
        hits = await _apply_to_matching(app, match, _clear_profile())
        _reassert_title(tty_path, title)
        return hits

    return bool(_run_api(factory))


def tab_status_update(match: str, window_id: str | None, action: str,
                       tty_path: str | None = None,
                       title: str | None = None) -> bool:
    """Combined tab-color/badge + arrange in ONE iTerm API connection.

    The tab-title.sh hook fires on every status change across every C-level
    session, so it must be cheap: this does the color/badge update AND the
    arrange-by-glyph in a single connection instead of two, halving the
    connection churn that was causing API timeouts under burst.

    action: a status glyph (🔴/⏳/✅/🏁/💤) — looked up in _STATUS_STYLE for
            its tab color + badge. Unrecognized glyph or a style with
            rgb=None (💤) clears the tab color. Then reorders window
            `window_id` (skipped if falsy/"0"). `tty_path`/`title` re-assert
            the Header after the profile write (a profile write otherwise
            resets it — see _reassert_title). All best-effort, no-op if API
            is down.

    Returns True only when at least one session actually matched `match`.
    This used to `return True` unconditionally, which made both callers and
    manual `python -m tools.itermtab status ...` checks report success even
    when the title match found nothing — it masked a real bug for an entire
    debugging session (2026-08-03). Keep it reporting real hits.
    """
    if not match:
        return False

    async def factory(conn):
        app = await _iterm2.async_get_app(conn)
        style = _STATUS_STYLE.get(action)
        profile = (_attention_profile(style["rgb"], style["badge"])
                   if style and style["rgb"] is not None else _clear_profile())
        hits = await _apply_to_matching(app, match, profile)
        _reassert_title(tty_path, title)
        if window_id and str(window_id) != "0":
            for w in app.windows:
                if str(w.window_id) == str(window_id):
                    await _arrange_window(w)
                    break
        return hits

    return bool(_run_api(factory))


# ---------------------------------------------------------------------------
# DEV tab color sync (task-0942febc)
#
# CEO ask: the tab bar should use ONE color vocabulary for C-level AND DEV
# tabs. Both halves already exist — a DEV tab title already carries its task
# id (tools/delegate.py:_spawn_iterm_tab / tools/resume_dev.py) and
# authoritative status already lives in state/tasks.db — so this is a read
# of existing state applied to existing tabs, driven once per tick from the
# maintab daemon loop (tools/maintab.py:run_daemon). No DEV-side plumbing.
#
# task status -> _STATUS_STYLE glyph. Anything not listed here (pending,
# done, merged, cancelled, reverted, or a status not yet invented) falls
# through to "no color" in _status_style below — the same outcome an
# idle/unrecognized glyph gets elsewhere in this module. Colors themselves
# stay derived from _STATUS_STYLE so a future palette change stays in one
# place, not two.
# ---------------------------------------------------------------------------
_TASK_STATUS_GLYPH = {
    "in_progress":   "⏳",
    "review":        "✅",
    "blocked_human": "🔴",
    "failed":        "🔴",
    "conflict":      "🔴",
    "stalled":       "🔴",
    "rate_limited":  "🔴",
}

_CLEVEL_PREFIXES = ("CTO ", "CMO ", "CGO ", "CFO ")
_TASK_ID_RE = re.compile(r"task-[0-9a-fA-F]+")

# DEV tabs coloured on the last tick, so the next one can clear a tab whose
# task has since left the coloured statuses. Without this, a task going
# failed -> done keeps its red forever whenever the tab outlives the task
# (CEO spotted exactly that, 2026-08-03): merging closes the DEV tab, but a
# task closed any other way leaves the tab open and stale-red. Only tabs we
# actually coloured get cleared, so this never fights tab-title.sh and never
# writes to a tab nobody asked us to touch.
_COLORED_DEV_TABS: set[str] = set()


def _status_style(status: str | None) -> dict | None:
    """A task status -> its _STATUS_STYLE entry, or None for "no color"."""
    glyph = _TASK_STATUS_GLYPH.get(status or "")
    return _STATUS_STYLE.get(glyph) if glyph else None


def _blocker_badge(status: str, owner_role: str) -> str | None:
    """The badge for a stuck DEV task — naming who has to act.

    A blocker is a request for a decision, so it has to name the person the
    decision belongs to: whoever ORDERED the work. The org already routes
    this way — `owner_role` + `owner_cto` pick the window that DEV reports,
    `send_to_cto`, and delegate's spawn all target — but the tab badge was
    the one signal still hardcoded to "รอ CEO", which told the CEO a DEV
    task delegated by the CTO was waiting on them (CEO caught it,
    2026-08-03). Now a CTO-ordered task reads "รอ CTO", a CMO-ordered one
    "รอ CMO", and so on. C-level tabs keep "รอ CEO" — for those the CEO
    genuinely is the one who ordered the work.

    Only red/stuck statuses get a badge at all. Working and finished tabs
    carry their colour and nothing else; a watermark across a DEV's output
    should mean "someone must act", not "this tab exists".
    """
    if _TASK_STATUS_GLYPH.get(status) != "🔴":
        return None
    role = owner_role or "cto"
    try:
        from lib.config import display_for
        return f"🔴 รอ {display_for(role)}"
    except Exception:
        # Imported lazily and defensively: this module is imported by
        # git_ops/delegate/watchdog, and a config problem must not take the
        # merge path down with it. The uppercased role is a fine fallback.
        return f"🔴 รอ {role.upper()}"


def _dev_task_id(title: str) -> str | None:
    """The task id in a DEV tab title, or None.

    Never matches a C-level title — same exclusion close_tab uses above: a
    C-level tab's color is owned by scripts/tab-title.sh, and its live work
    summary (IRON-RULES §32) can legitimately mention a task id without
    that tab being that task's DEV tab.
    """
    if any(p in title for p in _CLEVEL_PREFIXES):
        return None
    m = _TASK_ID_RE.search(title)
    return m.group(0) if m else None


def _in_flight_dev_statuses() -> dict[str, tuple[str, str]]:
    """task_id -> (status, owner_role), for tasks whose status maps to a color.

    `owner_role` comes along because a blocker has to name whoever ORDERED
    the work — see _blocker_badge. Legacy rows predate the column and carry
    NULL; they default to "cto", the same fallback tools/delegate.py and
    runners/dev_init.py already use.

    The ONE DB read per tick (HARD REQUIREMENT 1), scoped to the handful of
    colored statuses rather than the full table (HARD REQUIREMENT 3 — never
    scan the 250+ done/merged backlog every minute). Any failure — locked
    DB, missing file, `lib` unimportable from this cwd — degrades to an
    empty dict rather than raising (HARD REQUIREMENT 4); an empty dict also
    lets sync_dev_tab_colors() below skip opening an iTerm connection at
    all when there is nothing in-flight.
    """
    try:
        from lib import db
    except ImportError:
        return {}
    statuses = tuple(_TASK_STATUS_GLYPH)
    placeholders = ",".join("?" * len(statuses))
    try:
        with db.get_conn() as conn:
            rows = conn.execute(
                f"SELECT id, status, owner_role FROM tasks "
                f"WHERE status IN ({placeholders})",
                statuses,
            ).fetchall()
        return {row["id"]: (row["status"], row["owner_role"] or "cto")
                for row in rows}
    except Exception:
        return {}


async def _reassert_session_title(session, title: str) -> None:
    """Re-send a DEV tab's OSC-1 title after the color profile write.

    async_set_profile_properties() resets whatever title the tab was
    showing (see _reassert_title's note above) — a DEV tab's title carries
    its task id and must survive every color tick. Uses the session's own
    async_inject rather than a stored tty path: unlike CXO sessions, a DEV
    tab has no state/locks/<role>-<sid>.tty file to read. OSC 1 only, never
    OSC 0 (scripts/test_osc_surface_boundary.py enforces this repo-wide) —
    OSC 0 would also stomp the owning CTO's OSC-2 window title when this
    DEV tab lives inside that CTO's window (HARD REQUIREMENT 6).
    """
    if not title:
        return
    try:
        await session.async_inject(f"\033]1;{title}\007".encode())
    except Exception:
        pass


def sync_dev_tab_colors() -> int:
    """Color every DEV tab by its task's live status (IRON-RULES §32 vocabulary).

    Called once per tick from tools/maintab.py:run_daemon, alongside the
    existing Main Tab push — no second daemon, no second process. Writes
    the SUB tab only (tab color + the OSC-1 title reassert above): never
    OSC 2, so a DEV tab living inside its owning CTO's window never
    touches that CTO's goal/progress line.

    Badges name whoever ordered the work — see _blocker_badge. Only stuck
    (red) tasks get one; working and finished tabs carry colour alone.

    HARD REQUIREMENT 1: at most one iTerm API connection here, and it is
    skipped entirely when there is nothing to colour AND nothing left over
    to clear — the DB read always runs first specifically to make that skip
    possible without touching iTerm.

    Returns the number of tabs (re-)colored or cleared. Degrades to 0 on any
    failure (DB, iTerm API down, a session that vanished mid-tick) — never
    raises into the daemon loop (HARD REQUIREMENT 4).
    """
    statuses = _in_flight_dev_statuses()
    if not statuses and not _COLORED_DEV_TABS:
        return 0

    async def factory(conn):
        app = await _iterm2.async_get_app(conn)
        hits = 0
        seen: set[str] = set()
        for window in app.windows:
            for tab in window.tabs:
                for session in tab.sessions:
                    title = await _session_title(session)
                    task_id = _dev_task_id(title)
                    if task_id is None:
                        continue
                    if task_id in statuses:
                        status, owner_role = statuses[task_id]
                        style = _status_style(status)
                        profile = (
                            _attention_profile(
                                style["rgb"], _blocker_badge(status, owner_role))
                            if style and style["rgb"] is not None
                            else _clear_profile())
                    elif task_id in _COLORED_DEV_TABS:
                        # We coloured this tab on an earlier tick and its task
                        # has since left the coloured statuses (merged, done,
                        # cancelled). Clear it, or the old colour outlives the
                        # work it described.
                        profile = _clear_profile()
                    else:
                        # A tab we never coloured, for a task that isn't in a
                        # coloured status. Not ours to touch.
                        continue
                    try:
                        await session.async_set_profile_properties(profile)
                    except Exception:
                        continue
                    await _reassert_session_title(session, title)
                    if task_id in statuses:
                        seen.add(task_id)
                    hits += 1
        # Rebuild from what we actually painted this tick, so a tab that has
        # closed drops out instead of leaking into the set forever.
        _COLORED_DEV_TABS.clear()
        _COLORED_DEV_TABS.update(seen)
        return hits

    return _run_api(factory) or 0


if __name__ == "__main__":
    import sys

    argv = sys.argv[1:]
    usage = ("usage: python -m tools.itermtab "
             "<task_id> | arrange [window_id] | mark <match> [badge] [tty_path] [title] | "
             "clear <match> [tty_path] [title] | "
             "status <match> <window_id> <mark|clear> [tty_path] [title]")
    if not argv:
        print(usage)
        sys.exit(1)

    cmd = argv[0]
    if cmd == "arrange":
        print(f"arranged: {arrange_tabs(argv[1] if len(argv) > 1 else None)}")
    elif cmd == "mark":
        if len(argv) < 2:
            print(usage)
            sys.exit(1)
        badge = argv[2] if len(argv) > 2 else "🔴 รอ CEO"
        tty_path = argv[3] if len(argv) > 3 else None
        title = argv[4] if len(argv) > 4 else None
        print(f"marked: {mark_attention(argv[1], badge=badge, tty_path=tty_path, title=title)}")
    elif cmd == "clear":
        if len(argv) < 2:
            print(usage)
            sys.exit(1)
        tty_path = argv[2] if len(argv) > 2 else None
        title = argv[3] if len(argv) > 3 else None
        print(f"cleared: {clear_attention(argv[1], tty_path=tty_path, title=title)}")
    elif cmd == "status":
        if len(argv) < 4:
            print(usage)
            sys.exit(1)
        tty_path = argv[4] if len(argv) > 4 else None
        title = argv[5] if len(argv) > 5 else None
        print(f"status: {tab_status_update(argv[1], argv[2], argv[3], tty_path=tty_path, title=title)}")
    else:
        print(f"closed: {close_tab(cmd)}")
