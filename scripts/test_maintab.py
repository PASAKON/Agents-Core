"""Tests for tools/maintab.py — the Main Tab (window titlebar) layer.

The two-layer tab only works while each layer stays in its own lane:

    OSC 1 -> tab strip       (tab-title.sh, colored, carries "<ROLE> #<sid>")
    OSC 2 -> window titlebar (maintab.py, goal + progress + clock)

OSC 0 writes BOTH, so any accidental use of it makes one layer eat the other.
test_push_uses_osc2_only covers that from this side; scripts/test_tab_title.py
asserts the OSC 1 half.

Run via:   python3 scripts/test_maintab.py
"""
from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import maintab  # noqa: E402


def _mark(ok: bool, msg: str) -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


class _FakeRoot:
    """Point maintab at a throwaway state dir holding one fake session."""

    def __init__(self, tmp: Path, role: str = "cto", sid: str = "testsid1"):
        self.role, self.sid = role, sid
        self.titles = tmp / "tab-titles"
        self.locks = tmp / "locks"
        self.titles.mkdir(parents=True, exist_ok=True)
        self.locks.mkdir(parents=True, exist_ok=True)
        self.faketty = tmp / "faketty"
        self.faketty.write_text("")
        (self.locks / f"{role}-{sid}.tty").write_text(str(self.faketty) + "\n")
        (self.titles / f"{role}-{sid}.base").write_text(f"CTO #{sid}\n")
        self._saved = (maintab._TITLE_DIR, maintab._LOCKS, maintab._PIDFILE)

    def __enter__(self):
        maintab._TITLE_DIR = self.titles
        maintab._LOCKS = self.locks
        maintab._PIDFILE = self.locks / "maintab-daemon.pid"
        return self

    def __exit__(self, *exc):
        maintab._TITLE_DIR, maintab._LOCKS, maintab._PIDFILE = self._saved
        return False

    def tty_text(self) -> str:
        return self.faketty.read_text()


def test_bar_endpoints() -> bool:
    return (
        maintab.render_bar(0) == "░" * 10
        and maintab.render_bar(100) == "▓" * 10
        and len(maintab.render_bar(37)) == 10
    )


def test_percent_from_done_total() -> bool:
    return (
        maintab.progress_percent({"done": 12, "total": 13}) == 92
        and maintab.progress_percent({"done": 0, "total": 13}) == 0
        and maintab.progress_percent({}) is None
        # total=0 must not raise ZeroDivisionError
        and maintab.progress_percent({"done": 1, "total": 0}) is None
    )


def test_explicit_percent_wins_and_clamps() -> bool:
    return (
        maintab.progress_percent({"percent": 62, "done": 1, "total": 13}) == 62
        and maintab.progress_percent({"percent": 150}) == 100
        and maintab.progress_percent({"percent": -5}) == 0
    )


def test_elapsed_format() -> bool:
    f = maintab.format_elapsed
    return (
        f(0) == "0m"
        and f(59) == "0m"
        and f(42 * 60) == "42m"
        and f(2 * 3600 + 14 * 60) == "2h14m"
        and f(3600) == "1h00m"
        and f(26 * 3600) == "1d2h"
        and f(-5) == "0m"  # clock skew must not produce a negative
    )


def test_render_has_goal_bar_and_clock(tmp: Path) -> bool:
    with _FakeRoot(tmp / "a") as fr:
        maintab.set_main(fr.role, fr.sid, goal="ทำแท็บ 2 ชั้น", done=12, total=13)
        started = datetime.now(timezone.utc) - timedelta(hours=2, minutes=14)
        maintab.write_state(fr.role, fr.sid,
                            {**maintab.read_state(fr.role, fr.sid),
                             "started": started.isoformat()})
        line = maintab.render(fr.role, fr.sid)
    return (
        line.startswith("🎯 ทำแท็บ 2 ชั้น")
        and "92%" in line
        and "▓" in line
        and "⏱ 2h14m" in line
    )


def test_render_without_progress_omits_bar(tmp: Path) -> bool:
    with _FakeRoot(tmp / "b") as fr:
        maintab.set_main(fr.role, fr.sid, goal="แค่เป้า")
        line = maintab.render(fr.role, fr.sid)
    return "🎯 แค่เป้า" in line and "▓" not in line and "%" not in line


def test_render_falls_back_to_base_name(tmp: Path) -> bool:
    """No goal set yet -> use '<ROLE> #<sid>' rather than an empty target."""
    with _FakeRoot(tmp / "c") as fr:
        line = maintab.render(fr.role, fr.sid)
    return "CTO #testsid1" in line


def test_long_goal_truncated(tmp: Path) -> bool:
    with _FakeRoot(tmp / "d") as fr:
        maintab.set_main(fr.role, fr.sid, goal="x" * 200)
        line = maintab.render(fr.role, fr.sid)
    return "…" in line and len(line) < 120


def test_set_preserves_unpassed_fields(tmp: Path) -> bool:
    """Updating progress alone must not clear the goal, and vice versa."""
    with _FakeRoot(tmp / "e") as fr:
        maintab.set_main(fr.role, fr.sid, goal="เป้าเดิม", done=1, total=10)
        maintab.set_main(fr.role, fr.sid, done=7, total=10)   # progress only
        s1 = maintab.read_state(fr.role, fr.sid)
        maintab.set_main(fr.role, fr.sid, goal="เป้าใหม่")     # goal only
        s2 = maintab.read_state(fr.role, fr.sid)
    return (
        s1.get("goal") == "เป้าเดิม" and s1.get("done") == 7
        and s2.get("goal") == "เป้าใหม่" and s2.get("done") == 7
    )


def test_push_uses_osc2_only(tmp: Path) -> bool:
    """The whole two-layer design rests on this: OSC 2, never OSC 0 or 1."""
    with _FakeRoot(tmp / "f") as fr:
        maintab.set_main(fr.role, fr.sid, goal="เป้า", done=1, total=2)
        ok = maintab.push(fr.role, fr.sid)
        written = fr.tty_text()
    return (
        ok
        and written.startswith("\x1b]2;")
        and written.endswith("\x07")
        and "\x1b]0;" not in written
        and "\x1b]1;" not in written
    )


def test_push_false_when_tty_gone(tmp: Path) -> bool:
    """A closed session must be skipped quietly, not raise in the daemon."""
    with _FakeRoot(tmp / "g") as fr:
        maintab.set_main(fr.role, fr.sid, goal="เป้า")
        (fr.locks / f"{fr.role}-{fr.sid}.tty").unlink()
        return maintab.push(fr.role, fr.sid) is False


def test_live_sessions_lists_only_sessions_with_tty(tmp: Path) -> bool:
    with _FakeRoot(tmp / "h") as fr:
        maintab.set_main(fr.role, fr.sid, goal="เป้า")
        alive = maintab.live_sessions()
        # a second session with state but no tty lock (already closed)
        maintab.write_state("cmo", "deadsid1", {"goal": "ตายแล้ว"})
        after = maintab.live_sessions()
    return alive == [("cto", "testsid1")] and after == [("cto", "testsid1")]


def main() -> int:
    fails = 0
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        cases = [
            (test_bar_endpoints, (),
             "progress bar renders 0%/100%/partial at fixed width"),
            (test_percent_from_done_total, (),
             "percent from done/total, total=0 is safe"),
            (test_explicit_percent_wins_and_clamps, (),
             "explicit percent wins and clamps 0-100"),
            (test_elapsed_format, (),
             "elapsed formats m / h / d and never goes negative"),
            (test_render_has_goal_bar_and_clock, (tmp,),
             "render shows goal + bar + percent + clock"),
            (test_render_without_progress_omits_bar, (tmp,),
             "no progress set -> no bar, no percent"),
            (test_render_falls_back_to_base_name, (tmp,),
             "no goal set -> falls back to '<ROLE> #<sid>'"),
            (test_long_goal_truncated, (tmp,),
             "over-long goal truncated with ellipsis"),
            (test_set_preserves_unpassed_fields, (tmp,),
             "set() preserves fields it wasn't given"),
            (test_push_uses_osc2_only, (tmp,),
             "push writes OSC 2 only (never OSC 0/1)"),
            (test_push_false_when_tty_gone, (tmp,),
             "push returns False when the tty is gone"),
            (test_live_sessions_lists_only_sessions_with_tty, (tmp,),
             "live_sessions skips sessions with no tty"),
        ]
        for fn, args, desc in cases:
            try:
                ok = fn(*args)
            except Exception as e:
                ok, desc = False, f"{desc} — raised {e!r}"
            fails += not ok
            _mark(ok, desc)
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
