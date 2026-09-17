"""Tests for tools/revert_task.py.

Run via:   python3 scripts/test_revert_task.py

All git and subprocess calls are mocked — no real git/ssh executed.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_module
from tools.revert_task import revert_task

MERGE_SHA = "abcd1234ef567890"
REVERT_SHA = "cafe5678ba901234"
FAKE_PROJECT = {
    "key": "fake-proj",
    "path": "/fake/repo",
    "default_branch": "main",
    "auto_push": False,
}


def _make_subprocess_mock(depth: int = 5, log_sha: str = "",
                           revert_sha: str = REVERT_SHA,
                           deploy_rc: int = 0):
    """Return a side_effect function for subprocess.run."""
    def side_effect(cmd, *args, **kwargs):
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        m.stderr = ""
        if isinstance(cmd, list):
            joined = " ".join(str(c) for c in cmd)
            if "rev-list" in joined and "--count" in joined:
                m.stdout = f"{depth}\n"
            elif "log" in joined and "--grep" in joined:
                m.stdout = log_sha
            elif "rev-parse" in joined:
                m.stdout = f"{revert_sha}\n"
            # fetch / checkout / pull / revert / push: rc=0, stdout=""
        elif isinstance(cmd, str):
            # shell=True deploy command
            m.returncode = deploy_rc
            m.stdout = "deploy output\n"
            m.stderr = ""
        return m
    return side_effect


class RevertTaskTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = Path(self.tmpdir) / "test.db"
        self._db_patcher = patch.object(db_module, "DB_PATH", self.db_path)
        self._db_patcher.start()
        # _insert_task() lets create_task() resolve its owner from the caller's
        # env. Run from a C-level shell (CTO_SESSION_ID set, no charter row in
        # this temp DB) that hits the charter gate before the revert logic under
        # test ever runs. This suite tests revert_task(), not the gate.
        self._gate_patcher = patch.dict(os.environ, {"ORG_CHARTER_GATE": "off"})
        self._gate_patcher.start()
        db_module.init()

    def tearDown(self):
        self._gate_patcher.stop()
        self._db_patcher.stop()
        shutil.rmtree(self.tmpdir)

    def _insert_task(self, status: str = "done",
                     review: str | None = None) -> str:
        tid = db_module.create_task(
            project="fake-proj",
            role="developer",
            title="test task",
            description="test",
        )
        fields: dict = {}
        if review is not None:
            fields["review"] = review
        db_module.update_status(tid, status, actor="system", **fields)
        return tid

    # ------------------------------------------------------------------
    # Test 1: happy path
    # ------------------------------------------------------------------
    def test_happy_path(self):
        review = json.dumps({"merge_sha": MERGE_SHA, "branch": "feat", "base": "main"})
        tid = self._insert_task(status="done", review=review)
        recorded_cmds = []

        def _side_effect(cmd, *a, **kw):
            recorded_cmds.append(cmd)
            return _make_subprocess_mock(depth=5, revert_sha=REVERT_SHA)(cmd, *a, **kw)

        with patch("subprocess.run", side_effect=_side_effect), \
             patch("tools.revert_task.get_project", return_value=FAKE_PROJECT):
            result = revert_task(tid)

        self.assertTrue(result["reverted"], result)
        self.assertEqual(result["merge_sha"], MERGE_SHA)
        self.assertEqual(result["revert_sha"], REVERT_SHA)
        self.assertTrue(result["pushed"])

        # status flipped to reverted
        updated = db_module.get_task(tid)
        self.assertEqual(updated["status"], "reverted")

        # event logged
        events = db_module.recent_events(task_id=tid)
        kinds = [e["kind"] for e in events]
        self.assertIn("task_reverted", kinds)
        payload = json.loads(next(
            e["payload"] for e in events if e["kind"] == "task_reverted"
        ))
        self.assertEqual(payload["merge_sha"], MERGE_SHA)
        self.assertEqual(payload["revert_sha"], REVERT_SHA)

        # git commands in correct order (rev-list from _commits_ahead, then git ops)
        git_verbs = [c[1] for c in recorded_cmds if isinstance(c, list) and c[0] == "git"]
        self.assertEqual(git_verbs,
                         ["rev-list", "fetch", "checkout", "pull", "revert", "push", "rev-parse"])

    # ------------------------------------------------------------------
    # Test 2: refuse not-merged
    # ------------------------------------------------------------------
    def test_refuse_not_merged(self):
        tid = self._insert_task(status="in_progress")
        with patch("tools.revert_task.get_project", return_value=FAKE_PROJECT), \
             patch("subprocess.run"):
            result = revert_task(tid)

        self.assertFalse(result["reverted"])
        self.assertEqual(result["reason"], "task not in mergeable state")
        self.assertEqual(db_module.get_task(tid)["status"], "in_progress")

    # ------------------------------------------------------------------
    # Test 3: refuse merge_sha not found
    # ------------------------------------------------------------------
    def test_refuse_merge_sha_not_found(self):
        tid = self._insert_task(status="done", review="{}")

        def _empty_stdout(cmd, *a, **kw):
            m = MagicMock()
            m.returncode = 0
            m.stdout = ""
            m.stderr = ""
            return m

        with patch("subprocess.run", side_effect=_empty_stdout), \
             patch("tools.revert_task.get_project", return_value=FAKE_PROJECT):
            result = revert_task(tid)

        self.assertFalse(result["reverted"])
        self.assertEqual(result["reason"], "merge_sha not found")

    # ------------------------------------------------------------------
    # Test 4: depth limit — refuse without force; proceed with force
    # ------------------------------------------------------------------
    def test_depth_limit_refuses_without_force(self):
        review = json.dumps({"merge_sha": MERGE_SHA})
        tid = self._insert_task(status="done", review=review)

        with patch("subprocess.run",
                   side_effect=_make_subprocess_mock(depth=25)), \
             patch("tools.revert_task.get_project", return_value=FAKE_PROJECT):
            result = revert_task(tid, force=False)

        self.assertFalse(result["reverted"])
        self.assertIn("25 commits behind HEAD", result["reason"])
        self.assertIn("force=True", result["reason"])

    def test_depth_limit_force_proceeds(self):
        review = json.dumps({"merge_sha": MERGE_SHA})
        tid = self._insert_task(status="done", review=review)

        with patch("subprocess.run",
                   side_effect=_make_subprocess_mock(depth=25, revert_sha=REVERT_SHA)), \
             patch("tools.revert_task.get_project", return_value=FAKE_PROJECT):
            result = revert_task(tid, force=True)

        self.assertTrue(result["reverted"], result)
        self.assertEqual(result["merge_sha"], MERGE_SHA)

    # ------------------------------------------------------------------
    # Test 5: auto_deploy fires
    # ------------------------------------------------------------------
    def test_auto_deploy_fires(self):
        review = json.dumps({"merge_sha": MERGE_SHA})
        tid = self._insert_task(status="done", review=review)

        proj_with_deploy = {
            **FAKE_PROJECT,
            "auto_deploy": {
                "enabled": True,
                "requires_ceo_ack": False,
                "command": "bash deploy.sh",
            },
        }
        deploy_calls: list[str] = []

        def _side_effect(cmd, *a, **kw):
            if isinstance(cmd, str):
                deploy_calls.append(cmd)
            return _make_subprocess_mock(depth=5, revert_sha=REVERT_SHA)(cmd, *a, **kw)

        with patch("subprocess.run", side_effect=_side_effect), \
             patch("tools.revert_task.get_project", return_value=proj_with_deploy):
            result = revert_task(tid)

        self.assertTrue(result["reverted"], result)
        self.assertEqual(deploy_calls, ["bash deploy.sh"],
                         "deploy command should be fired once via _run_shell")
        self.assertEqual(result["deploy"]["command"], "bash deploy.sh")
        self.assertEqual(result["deploy"]["exit_code"], 0)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(RevertTaskTests)
    runner = unittest.TextTestRunner(verbosity=2)
    result_obj = runner.run(suite)
    sys.exit(0 if result_obj.wasSuccessful() else 1)
