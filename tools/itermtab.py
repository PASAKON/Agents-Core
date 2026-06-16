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


def close_tab(task_id: str) -> bool:
    """Close the iTerm tab whose title contains the given task id.

    Returns True if any tab was closed. Safe to call when no matching
    tab exists (returns False).
    """
    if not task_id or not task_id.startswith("task-"):
        # Refuse to operate on inputs that don't look like a real task id.
        # Protects against accidental empty/garbage matches reaching
        # iTerm and closing the wrong tab.
        return False
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
    """A write-only profile that turns a tab loud: tab color + badge text."""
    profile = _iterm2.LocalWriteOnlyProfile()
    profile.set_use_tab_color(True)
    profile.set_tab_color(_iterm2.Color(*color_rgb))
    if badge is not None:
        profile.set_badge_text(badge)
    return profile


def _clear_profile():
    """A write-only profile that restores a tab to normal (no color/badge)."""
    profile = _iterm2.LocalWriteOnlyProfile()
    profile.set_use_tab_color(False)
    profile.set_badge_text("")
    return profile


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
                   notify_msg: str | None = None) -> bool:
    """Make every tab whose title contains `match` shout for attention.

    Sets a red tab color + a badge on each matching tab, and — only when
    `notify_msg` is given — fires one macOS notification. `match` is a title
    substring: a task-id, a role+session base prefix, or even a glyph.
    Returns True if at least one tab was marked.
    """
    if not match:
        return False

    async def factory(conn):
        app = await _iterm2.async_get_app(conn)
        return await _apply_to_matching(app, match, _attention_profile(color, badge))

    hits = _run_api(factory) or 0
    if hits and notify_msg:
        _post_notification(notify_title or "mooniex org", notify_msg)
    return bool(hits)


def clear_attention(match: str) -> bool:
    """Undo mark_attention for tabs whose title contains `match`."""
    if not match:
        return False

    async def factory(conn):
        app = await _iterm2.async_get_app(conn)
        return await _apply_to_matching(app, match, _clear_profile())

    return bool(_run_api(factory))


def tab_status_update(match: str, window_id: str | None, action: str) -> bool:
    """Combined attention + arrange in ONE iTerm API connection.

    The tab-title.sh hook fires on every status change across every C-level
    session, so it must be cheap: this does the mark/clear AND the
    arrange-by-glyph in a single connection instead of two, halving the
    connection churn that was causing API timeouts under burst.

    action: "mark" -> red tab + badge on tabs matching `match`;
            anything else -> clear them. Then reorder window `window_id`
            (skipped if falsy/"0"). All best-effort, no-op if API is down.
    """
    if not match:
        return False

    async def factory(conn):
        app = await _iterm2.async_get_app(conn)
        profile = (_attention_profile(_ATTENTION_RGB, "🔴 รอ CEO")
                   if action == "mark" else _clear_profile())
        await _apply_to_matching(app, match, profile)
        if window_id and str(window_id) != "0":
            for w in app.windows:
                if str(w.window_id) == str(window_id):
                    await _arrange_window(w)
                    break
        return True

    return bool(_run_api(factory))


if __name__ == "__main__":
    import sys

    argv = sys.argv[1:]
    usage = ("usage: python -m tools.itermtab "
             "<task_id> | arrange [window_id] | mark <match> [badge] | "
             "clear <match> | status <match> <window_id> <mark|clear>")
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
        print(f"marked: {mark_attention(argv[1], badge=badge)}")
    elif cmd == "clear":
        if len(argv) < 2:
            print(usage)
            sys.exit(1)
        print(f"cleared: {clear_attention(argv[1])}")
    elif cmd == "status":
        if len(argv) < 4:
            print(usage)
            sys.exit(1)
        print(f"status: {tab_status_update(argv[1], argv[2], argv[3])}")
    else:
        print(f"closed: {close_tab(cmd)}")
