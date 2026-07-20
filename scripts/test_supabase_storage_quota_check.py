"""Tests for scripts/supabase_storage_quota_check.py — HTTP fully mocked,
no real network calls, no real Supabase credentials used.

Run via:   python3 scripts/test_supabase_storage_quota_check.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import scripts.supabase_storage_quota_check as sq  # noqa: E402


def _page(sizes: list[int]):
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = [{"name": f"f{i}", "metadata": {"size": s}} for i, s in enumerate(sizes)]
    m.raise_for_status.return_value = None
    return m


def _restricted():
    m = MagicMock()
    m.status_code = 402
    m.json.return_value = {"message": "Service for this project is restricted due to the following violations: exceed_storage_size_quota."}
    return m


class StorageQuotaCheckTests(unittest.TestCase):
    def test_under_threshold_ok(self):
        # 100MB used, default 80% of 1GB (~819MB) threshold -> OK
        with patch.object(sq.requests, "post", return_value=_page([50 * 1024 * 1024, 50 * 1024 * 1024])):
            used = sq.bucket_usage_bytes("https://x.supabase.co", "key", "bucket")
        self.assertEqual(used, 100 * 1024 * 1024)
        pct = used / sq.DEFAULT_QUOTA_BYTES * 100
        self.assertLess(pct, sq.DEFAULT_THRESHOLD_PCT)

    def test_over_threshold_warns(self):
        # 900MB used > 80% of 1GB -> should trigger WARNING path
        big = 900 * 1024 * 1024
        with patch.object(sq.requests, "post", return_value=_page([big])):
            used = sq.bucket_usage_bytes("https://x.supabase.co", "key", "bucket")
        threshold_bytes = sq.DEFAULT_QUOTA_BYTES * sq.DEFAULT_THRESHOLD_PCT // 100
        self.assertGreaterEqual(used, threshold_bytes)

    def test_pagination_sums_across_pages(self):
        page1 = _page([1024] * 1000)  # full page (limit=1000) -> triggers a second request
        page2 = _page([2048] * 5)     # short page -> stop
        with patch.object(sq.requests, "post", side_effect=[page1, page2]) as m:
            used = sq.bucket_usage_bytes("https://x.supabase.co", "key", "bucket")
        self.assertEqual(used, 1000 * 1024 + 5 * 2048)
        self.assertEqual(m.call_count, 2)

    def test_402_raises_restricted_error(self):
        with patch.object(sq.requests, "post", return_value=_restricted()):
            with self.assertRaises(sq.RestrictedError):
                sq.bucket_usage_bytes("https://x.supabase.co", "key", "bucket")

    def test_check_returns_2_when_restricted(self):
        with patch.object(sq, "_load_env", return_value={
            "SUPABASE_URL": "https://x.supabase.co", "SUPABASE_SERVICE_KEY": "key"}), \
             patch.object(sq.requests, "post", return_value=_restricted()):
            rc = sq.check("claudeflow-media", 80)
        self.assertEqual(rc, 2)

    def test_check_returns_1_when_over_threshold(self):
        big = 900 * 1024 * 1024
        with patch.object(sq, "_load_env", return_value={
            "SUPABASE_URL": "https://x.supabase.co", "SUPABASE_SERVICE_KEY": "key"}), \
             patch.object(sq.requests, "post", return_value=_page([big])):
            rc = sq.check("claudeflow-media", 80)
        self.assertEqual(rc, 1)

    def test_check_returns_0_when_ok(self):
        small = 10 * 1024 * 1024
        with patch.object(sq, "_load_env", return_value={
            "SUPABASE_URL": "https://x.supabase.co", "SUPABASE_SERVICE_KEY": "key"}), \
             patch.object(sq.requests, "post", return_value=_page([small])):
            rc = sq.check("claudeflow-media", 80)
        self.assertEqual(rc, 0)

    def test_check_returns_3_when_no_creds(self):
        import os
        with patch.object(sq, "_load_env", return_value={}), \
             patch.dict(os.environ, {}, clear=True):
            rc = sq.check("claudeflow-media", 80)
        self.assertEqual(rc, 3)

    def test_never_calls_delete(self):
        # Static guarantee: the module has no DELETE verb anywhere.
        src = (ROOT / "scripts" / "supabase_storage_quota_check.py").read_text()
        self.assertNotIn("requests.delete", src)
        self.assertNotIn('"DELETE"', src)
        self.assertNotIn("'DELETE'", src)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(StorageQuotaCheckTests)
    runner = unittest.TextTestRunner(verbosity=2)
    result_obj = runner.run(suite)
    sys.exit(0 if result_obj.wasSuccessful() else 1)
