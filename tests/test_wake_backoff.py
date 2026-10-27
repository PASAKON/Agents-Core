from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from lib.wake_backoff import (PROVIDERS, backoff_factor, load_budget, tier_factor,
                              wake_interval)


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


class TierIntervalTests(unittest.TestCase):
    BASE = 600.0
    NOW = 10000

    def budget(self, states, stamp=10000):
        return {"ts": stamp, "rows": {p: {"state": s} for p, s in zip(PROVIDERS, states)}}

    def test_tier_factor(self):
        for tier, over, expected in [("critical", False, 1), ("critical", True, 1),
                                     ("normal", False, 1), ("normal", True, 2),
                                     ("low", False, None), ("low", True, None),
                                     (None, False, 1), (None, True, 2),
                                     ("bogus", True, 2)]:
            with self.subTest(tier=tier, over=over):
                self.assertEqual(tier_factor(tier, over), expected)

    def test_interval_table(self):
        """tier x {under, one over, all over, stale, missing} -> seconds (None = no timed wake)."""
        cases = {
            "under": self.budget(["under"] * 3),
            "one_over": self.budget(["over", "under", "under"]),
            "all_over": self.budget(["over"] * 3),
            "stale": self.budget(["over"] * 3, stamp=self.NOW - 1801),
            "missing": None,
        }
        expected = {
            "critical": {"under": 600, "one_over": 1200, "all_over": 2400, "stale": 600, "missing": 600},
            "normal": {"under": 600, "one_over": 2400, "all_over": 4800, "stale": 600, "missing": 600},
            "low": {k: None for k in cases},
            None: {"under": 600, "one_over": 2400, "all_over": 4800, "stale": 600, "missing": 600},
        }
        for tier, row in expected.items():
            for name, want in row.items():
                with self.subTest(tier=tier, budget=name):
                    got = wake_interval(self.BASE, tier=tier, budget_json=cases[name], now=self.NOW)
                    self.assertEqual(got, want)

    def test_interval_never_below_base(self):
        for tier in ("critical", "normal", None, "x"):
            for states in (["under"] * 3, ["over"] * 3, ["unknown"] * 3):
                with self.subTest(tier=tier, states=states):
                    self.assertGreaterEqual(
                        wake_interval(self.BASE, tier=tier, budget_json=self.budget(states), now=self.NOW),
                        self.BASE)


class LoadBudgetTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def path(self, name="b.json"):
        return os.path.join(self.dir.name, name)

    def write(self, text, name="b.json"):
        with open(self.path(name), "w") as f:
            f.write(text)
        return self.path(name)

    def test_reads_the_p1_shape(self):
        b = {"ts": 10000, "day": "2026-10-27", "rows": {"agy": {"state": "over"}}}
        self.assertEqual(load_budget(self.write(json.dumps(b))), b)

    def test_never_raises(self):
        os.mkfifo(self.path("fifo"))
        os.symlink(self.write("{}"), self.path("link"))
        for label, path in [("missing", self.path("nope")),
                            ("bad json", self.write("{not json")),
                            ("not an object", self.write("[1, 2]")),
                            ("too large", self.write("{" + " " * 70000 + "}")),
                            ("deep", self.write("[" * 100000)),
                            ("directory", self.dir.name),
                            ("fifo", self.path("fifo")),
                            ("symlink", self.path("link"))]:
            with self.subTest(label):
                self.assertIsNone(load_budget(path))

    def test_default_path_is_the_one_p1_writes(self):
        # A fresh interpreter: conftest.py pins BUDGET_PATH away from the live file in every test.
        code = ("from lib import wake_backoff; from tools import usage_budget; "
                "print(wake_backoff.BUDGET_PATH == usage_budget.SNAPSHOT)")
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                             cwd=Path(__file__).resolve().parent.parent, check=True).stdout
        self.assertEqual(out.strip(), "True")

    def test_no_file_means_no_slowdown(self):
        self.assertEqual(wake_interval(600, tier="normal", budget_json=load_budget(self.path("nope")),
                                       now=10000), 600)
