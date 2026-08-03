"""Tests for the DEV tab color sync in tools/itermtab.py (task-0942febc).

CEO ask: DEV tabs use the SAME color vocabulary as C-level tabs
(_STATUS_STYLE, IRON-RULES §32), read once per tick from state/tasks.db and
applied to the SUB tab (title + color) — never the window titlebar.

Covers, per the task's acceptance list:
  1. each task status maps to the expected color, or to no-color
  2. a C-level title is never matched
  3. a tick with zero in-flight tasks does no API work
  4. a DB failure returns cleanly instead of raising

No real iTerm2 or real DB is needed: `_iterm2` is swapped for a fake module
(same convention as scripts/test_itermtab_status_color.py) and lib.db.DB_PATH
is pointed at a scratch sqlite file.

Run via:   python3 scripts/test_dev_tab_color.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import db  # noqa: E402
from tools import itermtab  # noqa: E402


def _mark(ok: bool, msg: str) -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


# --------------------------------------------------------------------------
# Fake iterm2 module — records profile writes + injected title bytes instead
# of talking to a real iTerm.
# --------------------------------------------------------------------------
class FakeProfile:
    def __init__(self) -> None:
        self.calls: dict = {}

    def __getattr__(self, name):
        if not name.startswith("set_"):
            raise AttributeError(name)

        def setter(value):
            self.calls[name] = value
        return setter


class FakeColor:
    def __init__(self, *rgb):
        self.rgb = rgb

    def __eq__(self, other):
        return isinstance(other, FakeColor) and self.rgb == other.rgb

    def __repr__(self):
        return f"FakeColor{self.rgb}"


class FakeSession:
    def __init__(self, title: str):
        self.title = title
        self.applied: list = []
        self.injected: list = []

    async def async_get_variable(self, name):
        return self.title if name == "autoName" else None

    async def async_set_profile_properties(self, profile):
        self.applied.append(profile)

    async def async_inject(self, data: bytes):
        self.injected.append(data)


class FakeTab:
    def __init__(self, sessions):
        self.sessions = sessions
        self.current_session = sessions[0] if sessions else None


class FakeWindow:
    def __init__(self, tabs, window_id="w1"):
        self.tabs = tabs
        self.window_id = window_id


class FakeApp:
    def __init__(self, windows):
        self.windows = windows


class FakeConnection:
    @staticmethod
    async def async_create():
        return object()


class PoisonedModule:
    """A fake `iterm2` that fails loudly if touched at all.

    Used to prove sync_dev_tab_colors() never opens a connection when there
    is nothing in-flight to color.
    """
    class Connection:
        @staticmethod
        async def async_create():
            raise AssertionError("iTerm API was touched with zero in-flight tasks")

    @staticmethod
    async def async_get_app(conn):
        raise AssertionError("iTerm API was touched with zero in-flight tasks")


def _fake_module(app):
    class Mod:
        Color = FakeColor
        LocalWriteOnlyProfile = FakeProfile
        Connection = FakeConnection

        @staticmethod
        async def async_get_app(conn):
            return app
    return Mod


def _with_fake(mod, fn):
    """Run fn() with itermtab._iterm2 swapped for `mod`."""
    original = itermtab._iterm2
    itermtab._iterm2 = mod
    try:
        return fn()
    finally:
        itermtab._iterm2 = original


# --------------------------------------------------------------------------
# scratch DB helpers
# --------------------------------------------------------------------------
def _seed_tasks(statuses: dict[str, str], owner_role: str | None = None) -> None:
    """Create one task row per {task_id: status}, all owned by `owner_role`.

    owner_role=None leaves the column NULL — what pre-ownership rows look
    like, which is the "defaults to cto" path.
    """
    with db.get_conn() as conn:
        now = db.now_iso()
        for task_id, status in statuses.items():
            conn.execute(
                "INSERT INTO tasks (id, project, role, status, title, "
                "description, created_at, updated_at, owner_role) "
                "VALUES (?, 'p', 'developer', ?, 't', 'd', ?, ?, ?)",
                (task_id, status, now, now, owner_role),
            )


def _with_scratch_db(fn):
    original_path = db.DB_PATH
    with tempfile.TemporaryDirectory() as tmp:
        db.DB_PATH = Path(tmp) / "tasks.db"
        db.init()
        try:
            return fn()
        finally:
            db.DB_PATH = original_path


# --------------------------------------------------------------------------
# 1. status -> color / no-color mapping
# --------------------------------------------------------------------------
_EXPECT_COLORED = {
    "in_progress":   "⏳",
    "review":        "✅",
    "blocked_human": "🔴",
    "failed":        "🔴",
    "conflict":      "🔴",
    "stalled":       "🔴",
    "rate_limited":  "🔴",
}
_EXPECT_NO_COLOR = ("pending", "done", "merged", "cancelled", "reverted",
                    "some_future_status")


def test_each_status_maps_to_expected_color() -> bool:
    for status, glyph in _EXPECT_COLORED.items():
        style = itermtab._status_style(status)
        want = itermtab._STATUS_STYLE[glyph]
        if style is None or style["rgb"] != want["rgb"]:
            return False
    return True


def test_terminal_and_pending_statuses_have_no_color() -> bool:
    return all(itermtab._status_style(s) is None for s in _EXPECT_NO_COLOR)


# --------------------------------------------------------------------------
# 2. C-level title guard
# --------------------------------------------------------------------------
def test_clevel_title_never_matched() -> bool:
    titles = [
        "CTO #bafbda08 ⏳ working on task-0942febc",
        "CMO #11112222 ✅ done",
        "CGO #33334444 🔴 blocked",
        "CFO #55556666 ⏳ reviewing budget",
    ]
    return all(itermtab._dev_task_id(t) is None for t in titles)


def test_dev_title_extracts_task_id() -> bool:
    cases = [
        ("Developer (task-0942febc)", "task-0942febc"),
        ("DevOps Engineer (task-0fd57504) [RESUMED]", "task-0fd57504"),
        ("plain shell, no task id here", None),
    ]
    return all(itermtab._dev_task_id(title) == want for title, want in cases)


# --------------------------------------------------------------------------
# 3. zero in-flight tasks -> no API work
# --------------------------------------------------------------------------
def test_zero_in_flight_does_no_api_work() -> bool:
    def run():
        return _with_fake(PoisonedModule, itermtab.sync_dev_tab_colors)

    def with_db():
        _seed_tasks({"task-aaaaaaaa": "done", "task-bbbbbbbb": "pending"})
        return run()

    hits = _with_scratch_db(with_db)
    return hits == 0


# --------------------------------------------------------------------------
# 4. DB failure returns cleanly instead of raising
# --------------------------------------------------------------------------
def test_db_failure_returns_cleanly() -> bool:
    def boom():
        raise RuntimeError("database is locked")

    original = db.get_conn
    db.get_conn = boom
    try:
        result = itermtab._in_flight_dev_statuses()
    except Exception:
        return False
    finally:
        db.get_conn = original
    return result == {}


def test_sync_survives_db_failure() -> bool:
    def boom():
        raise RuntimeError("database is locked")

    original = db.get_conn
    db.get_conn = boom
    try:
        hits = _with_fake(PoisonedModule, itermtab.sync_dev_tab_colors)
    except Exception:
        return False
    finally:
        db.get_conn = original
    return hits == 0


# --------------------------------------------------------------------------
# 5. end-to-end: colors get applied, and only to matching DEV tabs
# --------------------------------------------------------------------------
def test_sync_colors_matching_dev_tabs_only() -> bool:
    dev_working = FakeSession("Developer (task-11111111)")
    dev_blocked = FakeSession("DevOps Engineer (task-22222222) [RESUMED]")
    dev_done = FakeSession("Developer (task-33333333)")  # not in-flight
    cto_tab = FakeSession("CTO #bafbda08 ⏳ task-11111111 landed")
    app = FakeApp([FakeWindow([
        FakeTab([dev_working]), FakeTab([dev_blocked]),
        FakeTab([dev_done]), FakeTab([cto_tab]),
    ])])

    def with_db():
        _seed_tasks({
            "task-11111111": "in_progress",
            "task-22222222": "blocked_human",
            "task-33333333": "done",
        })
        return _with_fake(_fake_module(app), itermtab.sync_dev_tab_colors)

    hits = _with_scratch_db(with_db)
    if hits != 2:
        return False
    if cto_tab.applied:
        return False  # C-level tab must never be touched
    if dev_done.applied:
        return False  # a task not in this tick's colored-status read is left alone

    want_amber = FakeColor(*itermtab._STATUS_STYLE["⏳"]["rgb"])
    want_red = FakeColor(*itermtab._STATUS_STYLE["🔴"]["rgb"])
    ok_working = (dev_working.applied
                  and dev_working.applied[0].calls.get("set_tab_color") == want_amber)
    ok_blocked = (dev_blocked.applied
                  and dev_blocked.applied[0].calls.get("set_tab_color") == want_red)
    # title reasserted via OSC 1 injection, never OSC 0
    ok_title = (dev_working.injected
                and dev_working.injected[0] == b"\x1b]1;Developer (task-11111111)\x07")
    return bool(ok_working and ok_blocked and ok_title)


def test_blocker_badge_names_whoever_ordered_the_work() -> bool:
    """A blocker must name the C-level who ORDERED the task, not the CEO.

    The badge was hardcoded "🔴 รอ CEO" — a C-level message — so a DEV task
    the CTO delegated told the CEO it was waiting on them (CEO caught it
    2026-08-03). The org already routes reports by owner_role; the badge now
    follows the same owner.
    """
    b = itermtab._blocker_badge
    return (
        b("failed", "cto") == "🔴 รอ CTO"
        and b("blocked_human", "cmo") == "🔴 รอ CMO"
        and b("stalled", "cgo") == "🔴 รอ CGO"
        and b("conflict", "cfo") == "🔴 รอ CFO"
        # legacy rows predate owner_role -> the same "cto" default the rest
        # of the org uses (tools/delegate.py, runners/dev_init.py)
        and b("rate_limited", None) == "🔴 รอ CTO"
        # never says CEO for a DEV task, whoever owns it
        and all("CEO" not in (b(s, o) or "")
                for s in ("failed", "stalled", "blocked_human")
                for o in ("cto", "cmo", "cgo", "cfo", None))
    )


def test_only_stuck_tasks_get_a_badge() -> bool:
    """Working/finished tabs carry colour alone — no watermark over output."""
    b = itermtab._blocker_badge
    return b("in_progress", "cto") is None and b("review", "cto") is None


def test_badge_reaches_the_tab_with_the_right_owner() -> bool:
    """End-to-end: a CMO-owned failed task paints 'รอ CMO' on its tab."""
    dev = FakeSession("Developer (task-44444444)")
    app = FakeApp([FakeWindow([FakeTab([dev])])])

    def with_db():
        _seed_tasks({"task-44444444": "failed"}, owner_role="cmo")
        return _with_fake(_fake_module(app), itermtab.sync_dev_tab_colors)

    itermtab._COLORED_DEV_TABS.clear()
    _with_scratch_db(with_db)
    if not dev.applied:
        return False
    return dev.applied[0].calls.get("set_badge_text") == "🔴 รอ CMO"


def test_stale_color_is_cleared_when_task_leaves_flight() -> bool:
    """A tab we coloured must lose it once its task is no longer in flight.

    Merging closes the DEV tab, but a task closed any other way leaves the
    tab open — and it kept its old colour forever, so a finished task still
    showed red (CEO caught it 2026-08-03).
    """
    dev = FakeSession("Developer (task-55555555)")
    app = FakeApp([FakeWindow([FakeTab([dev])])])

    def tick_failed():
        _seed_tasks({"task-55555555": "failed"}, owner_role="cto")
        return _with_fake(_fake_module(app), itermtab.sync_dev_tab_colors)

    def tick_done():
        _seed_tasks({"task-55555555": "done"}, owner_role="cto")
        return _with_fake(_fake_module(app), itermtab.sync_dev_tab_colors)

    itermtab._COLORED_DEV_TABS.clear()
    _with_scratch_db(tick_failed)
    if not dev.applied or dev.applied[0].calls.get("set_use_tab_color") is not True:
        return False          # first tick must actually colour it
    if "task-55555555" not in itermtab._COLORED_DEV_TABS:
        return False          # and remember that it did

    _with_scratch_db(tick_done)
    if len(dev.applied) != 2:
        return False          # second tick must write again, to clear
    cleared = dev.applied[1].calls
    return (
        cleared.get("set_use_tab_color") is False
        and cleared.get("set_use_tab_color_light") is False
        and cleared.get("set_use_tab_color_dark") is False
        and "task-55555555" not in itermtab._COLORED_DEV_TABS
    )


def test_untouched_tabs_are_never_cleared() -> bool:
    """Clearing is scoped to tabs WE coloured — never a stranger's tab."""
    dev = FakeSession("Developer (task-66666666)")
    app = FakeApp([FakeWindow([FakeTab([dev])])])

    def with_db():
        _seed_tasks({"task-66666666": "done"}, owner_role="cto")
        return _with_fake(_fake_module(app), itermtab.sync_dev_tab_colors)

    itermtab._COLORED_DEV_TABS.clear()
    _with_scratch_db(with_db)
    return dev.applied == []


def main() -> int:
    tests = [
        (test_each_status_maps_to_expected_color,
         "in_progress/review/blocked_human/failed/conflict/stalled/rate_limited "
         "map to their _STATUS_STYLE color"),
        (test_terminal_and_pending_statuses_have_no_color,
         "pending/done/merged/cancelled/reverted/unknown -> no color"),
        (test_clevel_title_never_matched,
         "a C-level title (CTO/CMO/CGO/CFO prefix) is never matched"),
        (test_dev_title_extracts_task_id,
         "a DEV title extracts its task id, incl. [RESUMED] suffix"),
        (test_zero_in_flight_does_no_api_work,
         "zero in-flight tasks -> DB read only, iTerm API never touched"),
        (test_db_failure_returns_cleanly,
         "_in_flight_dev_statuses() returns {} instead of raising on a DB failure"),
        (test_sync_survives_db_failure,
         "sync_dev_tab_colors() returns 0 instead of raising on a DB failure"),
        (test_sync_colors_matching_dev_tabs_only,
         "sync colors only in-flight DEV tabs, skips C-level + done tasks, "
         "reasserts the DEV tab's title"),
        (test_blocker_badge_names_whoever_ordered_the_work,
         "blocker badge names the C-level who ordered the task, never the CEO"),
        (test_only_stuck_tasks_get_a_badge,
         "only stuck tasks get a badge; working/finished carry colour alone"),
        (test_badge_reaches_the_tab_with_the_right_owner,
         "a CMO-owned failed task paints 'รอ CMO' on its tab end-to-end"),
        (test_stale_color_is_cleared_when_task_leaves_flight,
         "a coloured tab is cleared once its task leaves the in-flight set"),
        (test_untouched_tabs_are_never_cleared,
         "clearing is scoped to tabs we coloured — a stranger's tab is untouched"),
    ]
    fails = 0
    for fn, desc in tests:
        try:
            ok = fn()
        except Exception as e:  # a raising test is a failing test
            ok = False
            desc = f"{desc} — raised {e!r}"
        fails += not ok
        _mark(ok, desc)
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
