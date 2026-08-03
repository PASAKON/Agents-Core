"""Tests for the tab status COLOR path in tools/itermtab.py (IRON-RULES §32).

Regression guards for the 2026-08-03 debugging session, where "tab color
never renders" took three wrong fixes to diagnose. The traps, all covered
below:

  1. tab_status_update() used to `return True` unconditionally, so every
     check reported success even when the title match found zero sessions.
  2. Only 🔴 got a color; every other glyph fell through to _clear_profile(),
     so a color set by any other means was wiped on the next status update.
  3. Profiles with "Use separate colors for light and dark mode" enabled
     ignore the plain Tab Color / Use Tab Color keys — the API call still
     succeeds silently and nothing repaints. Both variants must be written.

No real iTerm2 is needed: `_iterm2` is swapped for a fake module, which is
also what makes these deterministic in CI.

Run via:   python3 scripts/test_itermtab_status_color.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import itermtab  # noqa: E402


def _mark(ok: bool, msg: str) -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


# --------------------------------------------------------------------------
# Fake iterm2 module — records profile writes instead of talking to iTerm.
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

    async def async_get_variable(self, name):
        return self.title if name == "autoName" else None

    async def async_set_profile_properties(self, profile):
        self.applied.append(profile)


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


def _fake_module(app):
    """A stand-in for the `iterm2` package wired to a given fake app."""
    class Mod:
        Color = FakeColor
        LocalWriteOnlyProfile = FakeProfile
        Connection = FakeConnection

        @staticmethod
        async def async_get_app(conn):
            return app
    return Mod


def _with_fake(app, fn):
    """Run fn() with itermtab._iterm2 swapped for a fake bound to `app`."""
    original = itermtab._iterm2
    itermtab._iterm2 = _fake_module(app)
    try:
        return fn()
    finally:
        itermtab._iterm2 = original


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------
def test_style_table_matches_glyph_rank() -> bool:
    """_STATUS_STYLE and _GLYPH_RANK must cover the same glyph set.

    They are two halves of one feature (color + sort order). A glyph added
    to one but not the other silently loses its color or its sort position.
    """
    return set(itermtab._STATUS_STYLE) == set(itermtab._GLYPH_RANK)


def test_every_active_glyph_has_distinct_color() -> bool:
    """🔴/⏳/✅/🏁 each get their own color; 💤 is explicitly colorless."""
    styles = itermtab._STATUS_STYLE
    colored = [s["rgb"] for g, s in styles.items() if s["rgb"] is not None]
    return (
        styles["💤"]["rgb"] is None
        and len(colored) == 4
        and len(set(colored)) == 4  # all distinct
    )


def test_attention_profile_sets_light_and_dark() -> bool:
    """Trap 3: unified + light + dark tab-color keys must ALL be written.

    A profile with separate light/dark colors enabled ignores the unified
    key, so writing only that repaints nothing while still 'succeeding'.
    """
    def run():
        p = itermtab._attention_profile((1, 2, 3), "badge!")
        return p.calls

    calls = _with_fake(FakeApp([]), run)
    want_color = FakeColor(1, 2, 3)
    return (
        calls.get("set_use_tab_color") is True
        and calls.get("set_use_tab_color_light") is True
        and calls.get("set_use_tab_color_dark") is True
        and calls.get("set_tab_color") == want_color
        and calls.get("set_tab_color_light") == want_color
        and calls.get("set_tab_color_dark") == want_color
        and calls.get("set_badge_text") == "badge!"
    )


def test_clear_profile_disables_light_and_dark() -> bool:
    """Clearing must disable all three flags, else stale color lingers."""
    def run():
        return itermtab._clear_profile().calls

    calls = _with_fake(FakeApp([]), run)
    return (
        calls.get("set_use_tab_color") is False
        and calls.get("set_use_tab_color_light") is False
        and calls.get("set_use_tab_color_dark") is False
        and calls.get("set_badge_text") == ""
    )


def test_status_update_false_when_no_match() -> bool:
    """Trap 1: a match that hits nothing must report False, not True."""
    session = FakeSession("CTO #aaaaaaaa ⏳ working")
    app = FakeApp([FakeWindow([FakeTab([session])])])
    result = _with_fake(
        app, lambda: itermtab.tab_status_update("CTO #zzzzzzzz", "0", "⏳"))
    return result is False and session.applied == []


def test_status_update_true_and_applies_on_match() -> bool:
    """A real match reports True and actually writes the profile."""
    session = FakeSession("CTO #aaaaaaaa ⏳ working")
    app = FakeApp([FakeWindow([FakeTab([session])])])
    result = _with_fake(
        app, lambda: itermtab.tab_status_update("CTO #aaaaaaaa", "0", "⏳"))
    if not (result is True and len(session.applied) == 1):
        return False
    calls = session.applied[0].calls
    want = FakeColor(*itermtab._STATUS_STYLE["⏳"]["rgb"])
    return calls.get("set_tab_color") == want and calls.get("set_use_tab_color") is True


def test_each_glyph_applies_its_own_color() -> bool:
    """Trap 2: ⏳/✅/🏁 must get their own color, not fall through to clear."""
    for glyph in ("🔴", "⏳", "✅", "🏁"):
        session = FakeSession(f"CTO #aaaaaaaa {glyph} x")
        app = FakeApp([FakeWindow([FakeTab([session])])])
        _with_fake(app,
                   lambda: itermtab.tab_status_update("CTO #aaaaaaaa", "0", glyph))
        if not session.applied:
            return False
        calls = session.applied[0].calls
        want = FakeColor(*itermtab._STATUS_STYLE[glyph]["rgb"])
        if calls.get("set_tab_color") != want or calls.get("set_use_tab_color") is not True:
            return False
    return True


def test_idle_and_unknown_glyph_clear_color() -> bool:
    """💤 and any unrecognized action must clear, never pick a color."""
    for action in ("💤", "", "🦄"):
        session = FakeSession("CTO #aaaaaaaa x")
        app = FakeApp([FakeWindow([FakeTab([session])])])
        _with_fake(app,
                   lambda: itermtab.tab_status_update("CTO #aaaaaaaa", "0", action))
        if not session.applied:
            return False
        calls = session.applied[0].calls
        if calls.get("set_use_tab_color") is not False:
            return False
        if "set_tab_color" in calls:
            return False
    return True


def test_empty_match_is_refused() -> bool:
    """An empty match would color every tab in every window — refuse it."""
    session = FakeSession("CTO #aaaaaaaa ⏳ x")
    app = FakeApp([FakeWindow([FakeTab([session])])])
    result = _with_fake(app, lambda: itermtab.tab_status_update("", "0", "⏳"))
    return result is False and session.applied == []


def main() -> int:
    tests = [
        (test_style_table_matches_glyph_rank,
         "_STATUS_STYLE and _GLYPH_RANK cover the same glyph set"),
        (test_every_active_glyph_has_distinct_color,
         "🔴/⏳/✅/🏁 have distinct colors, 💤 is colorless"),
        (test_attention_profile_sets_light_and_dark,
         "attention profile writes unified + light + dark tab color"),
        (test_clear_profile_disables_light_and_dark,
         "clear profile disables unified + light + dark tab color"),
        (test_status_update_false_when_no_match,
         "tab_status_update returns False when match hits nothing"),
        (test_status_update_true_and_applies_on_match,
         "tab_status_update returns True and applies profile on match"),
        (test_each_glyph_applies_its_own_color,
         "each active glyph applies its own color (not clear)"),
        (test_idle_and_unknown_glyph_clear_color,
         "💤 / unknown glyph clears color instead of picking one"),
        (test_empty_match_is_refused,
         "empty match is refused (would color every tab)"),
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
