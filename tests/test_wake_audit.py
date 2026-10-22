from pathlib import Path
import tempfile
import unittest

from tools.wake_audit import classify_unit, scan_skills


class AuditTests(unittest.TestCase):
    def test_gates(self):
        for name in ("mail_wake_sweep", "run_watch_driver"):
            with self.subTest(name=name):
                row = classify_unit("a.timer", f"[Service]\nExecStart=python -m tools.{name}")
                self.assertFalse(row["flagged"])

    def test_direct_clock(self):
        for cmd in ("tmux send-keys -t x ping Enter", "python -m tools.send_to_cxo cto ping",
                    "SendMessage ping", "claude -p patrol", "python tools/tool_value.py report"):
            with self.subTest(cmd=cmd):
                self.assertTrue(classify_unit("a.timer", "ExecStart=" + cmd)["flagged"])

    def test_comments_and_nonwaker(self):
        self.assertIsNone(classify_unit("a.timer", "# send_to_cxo\nExecStart=python backup.py"))
        self.assertIsNone(classify_unit("a.timer", "ExecStart=python tools/tool_value.py collect"))
        self.assertIsNone(classify_unit("a.timer", "ExecStart=python /srv/claude-usage/monitor.py"))

    def test_escalation_reminder(self):
        self.assertTrue(classify_unit("a.timer", "ExecStart=python tools/escalation_watch.py --nudge")["flagged"])

    def test_mixed_commands_not_whitelisted(self):
        text = "ExecStart=python -m tools.mail_wake_sweep\nExecStartPost=tmux send-keys x"
        self.assertTrue(classify_unit("a.timer", text)["flagged"])

    def test_dropin_reset_and_continuation(self):
        text = "ExecStart=claude -p ping\nExecStart=\nExecStart=python \\\n -m tools.mail_wake_sweep"
        self.assertFalse(classify_unit("a.timer", text)["flagged"])

    def test_skill_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "clock.md").write_text("CronCreate\nScheduleWakeup /loop")
            (root / "event.md").write_text("Monitor until changed; sleep 60")
            rows = scan_skills(root)
            self.assertTrue(rows[0]["flagged"])
            self.assertFalse(rows[1]["flagged"])
            self.assertEqual(rows[0]["lines"]["CronCreate"], [1])
