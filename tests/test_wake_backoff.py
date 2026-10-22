from datetime import datetime, timezone
import unittest

from lib.wake_backoff import PROVIDERS, backoff_factor


class BackoffTests(unittest.TestCase):
    def budget(self, states, stamp=10000):
        return {"ts": stamp, "rows": {
            p: {"state": s} for p, s in zip(PROVIDERS, states)}}

    def test_pressure(self):
        for states, expected in [(["under"] * 3, 1), (["over", "unknown"], 2),
                                 (["over"] * 2, 2), (["over"] * 3, 4),
                                 (["unknown"] * 3, 1)]:
            with self.subTest(states=states):
                self.assertEqual(backoff_factor(self.budget(states), 10000), expected)

    def test_age_boundary(self):
        b = self.budget(["over"] * 3)
        self.assertEqual(backoff_factor(b, 11800), 4)
        self.assertEqual(backoff_factor(b, 11800.01), 1)
        self.assertEqual(backoff_factor(b, 9999), 1)

    def test_invalid(self):
        for b in [None, {}, [], {"ts": "bad"}, {"ts": float("nan")},
                  {"ts": True}, {"ts": 10000, "rows": []}, {"ts": 10000, "agy": {"state": "over"}}]:
            with self.subTest(b=b):
                self.assertEqual(backoff_factor(b, 10000), 1)

    def test_iso_p1_shape(self):
        b = {"ts": "2026-10-22T00:00:00+00:00", "day": "2026-10-22",
             "rows": {"agy": {"state": "over"}, "agy-claude": {"state": "over"}}}
        self.assertEqual(backoff_factor(b, datetime(2026, 10, 22, tzinfo=timezone.utc)), 2)
