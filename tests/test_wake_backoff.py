from datetime import datetime, timezone
import unittest

from lib.wake_backoff import PROVIDERS, backoff_factor


class BackoffTests(unittest.TestCase):
    def budget(self, states, stamp=10000):
        return {"updated_at": stamp, "providers": {
            p: {"state": s} for p, s in zip(PROVIDERS, states)}}

    def test_pressure(self):
        for states, expected in [(["under"] * 4, 1), (["over", "unknown"], 2),
                                 (["over"] * 3, 2), (["over"] * 4, 4),
                                 (["unknown"] * 4, 1)]:
            with self.subTest(states=states):
                self.assertEqual(backoff_factor(self.budget(states), 10000), expected)

    def test_age_boundary(self):
        b = self.budget(["over"] * 4)
        self.assertEqual(backoff_factor(b, 11800), 4)
        self.assertEqual(backoff_factor(b, 11800.01), 1)
        self.assertEqual(backoff_factor(b, 9999), 1)

    def test_invalid(self):
        for b in [None, {}, [], {"updated_at": "bad"}, {"updated_at": float("nan")},
                  {"updated_at": True}, {"updated_at": 10000, "providers": []}]:
            with self.subTest(b=b):
                self.assertEqual(backoff_factor(b, 10000), 1)

    def test_iso_and_flat_rows(self):
        b = {"updated_at": "2026-10-22T00:00:00Z", "agy": {"state": "over"}}
        self.assertEqual(backoff_factor(b, datetime(2026, 10, 22, tzinfo=timezone.utc)), 2)
