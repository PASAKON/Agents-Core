"""Tests for lib/quota_router.py (GH mooniex-agents#38) — no real SSH/HTTP
calls; fetchers are injected as fakes via pick_provider()'s keyword args.

Run via:   python3 scripts/test_quota_router.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.quota_router import pick_provider  # noqa: E402


def _fetch(five_hour: float, seven_day: float):
    return lambda *a, **k: {"five_hour": five_hour, "seven_day": seven_day}


def _fetch_none():
    return lambda *a, **k: None


class PickProviderTests(unittest.TestCase):
    def test_zai_wins_when_it_has_more_headroom(self):
        got = pick_provider(
            "tok",
            _claude_fetch=_fetch(five_hour=20, seven_day=10),
            _zai_fetch=_fetch(five_hour=90, seven_day=80),
        )
        self.assertEqual(got, "zai")

    def test_claude_wins_when_it_has_more_headroom(self):
        got = pick_provider(
            "tok",
            _claude_fetch=_fetch(five_hour=87, seven_day=93),
            _zai_fetch=_fetch(five_hour=100, seven_day=0),
        )
        self.assertEqual(got, "claude")

    def test_bottleneck_window_dominates_not_the_average(self):
        # Z.ai looks great on 5h (95) but is fully out on 7d (0) -> the 7d
        # bottleneck must sink it below Claude's 40/40, not get averaged away.
        got = pick_provider(
            "tok",
            _claude_fetch=_fetch(five_hour=40, seven_day=40),
            _zai_fetch=_fetch(five_hour=95, seven_day=0),
        )
        self.assertEqual(got, "claude")

    def test_tie_falls_back_to_claude(self):
        got = pick_provider(
            "tok",
            _claude_fetch=_fetch(five_hour=50, seven_day=50),
            _zai_fetch=_fetch(five_hour=50, seven_day=50),
        )
        self.assertEqual(got, "claude")

    def test_claude_fetch_failure_falls_back_to_claude(self):
        got = pick_provider(
            "tok",
            _claude_fetch=_fetch_none(),
            _zai_fetch=_fetch(five_hour=90, seven_day=90),
        )
        self.assertEqual(got, "claude")

    def test_zai_fetch_failure_falls_back_to_claude(self):
        got = pick_provider(
            "tok",
            _claude_fetch=_fetch(five_hour=10, seven_day=10),
            _zai_fetch=_fetch_none(),
        )
        self.assertEqual(got, "claude")

    def test_no_token_falls_back_to_claude(self):
        from lib.quota_router import fetch_zai_headroom
        self.assertIsNone(fetch_zai_headroom(None))
        self.assertIsNone(fetch_zai_headroom(""))


if __name__ == "__main__":
    unittest.main()
