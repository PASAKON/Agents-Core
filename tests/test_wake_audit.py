from pathlib import Path
import tempfile
import unittest

from tools import wake_audit
from tools.wake_audit import ROOT, classify_unit, scan_skills

WEEKLY = "[Timer]\nOnCalendar=Mon *-*-* 08:00:00 Asia/Bangkok\nPersistent=true"


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

    def test_escalation_timed_parts_are_backoff_gated(self):
        row = classify_unit("a.timer", "ExecStart=python tools/escalation_watch.py --nudge")
        self.assertFalse(row["flagged"])
        self.assertEqual(row["trigger"], "backoff")

    def test_escalation_without_wake_interval_in_its_source_is_flagged_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "tools").mkdir()
            (Path(tmp) / "tools" / "escalation_watch.py").write_text("REMIND_S = 3600\n")
            old, wake_audit.ROOT = wake_audit.ROOT, Path(tmp)
            try:
                row = classify_unit("a.timer", "ExecStart=python tools/escalation_watch.py --nudge")
            finally:
                wake_audit.ROOT = old
        self.assertTrue(row["flagged"])

    def test_scheduled_report(self):
        cmd = "ExecStart=python tools/tool_value.py report --week"
        row = classify_unit("a.timer", cmd, WEEKLY)
        self.assertEqual((row["flagged"], row["trigger"]), (False, "scheduled-report"))
        self.assertTrue(classify_unit("a.timer", cmd)["flagged"], "no timer text: not proven date-anchored")
        for label, timer in [("every minute", "[Timer]\nOnCalendar=*:0/1"),
                             ("daily", "[Timer]\nOnCalendar=*-*-* 08:00:00"),
                             ("interval", WEEKLY + "\nOnUnitActiveSec=60"),
                             ("no schedule", "[Timer]\nPersistent=true")]:
            with self.subTest(label):
                self.assertTrue(classify_unit("a.timer", cmd, timer)["flagged"])
        self.assertTrue(classify_unit("a.timer", cmd + "\nExecStartPost=tmux send-keys x", WEEKLY)["flagged"])

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

    def test_reviewed_skill_allows_only_its_counted_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "CMO_Workflow_MimiPage_Weekly"
            skill.mkdir()
            file = skill / "SKILL.md"
            file.write_text("one-shot CronCreate\nthe note on CronCreate\n")
            row = scan_skills(root)[0]
            self.assertEqual((row["flagged"], row["trigger"]), (False, "reviewed"))
            file.write_text("CronCreate\nCronCreate\nCronCreate again\n")
            self.assertTrue(scan_skills(root)[0]["flagged"], "one line over the count")
            file.write_text("CronCreate\nScheduleWakeup\n")
            self.assertTrue(scan_skills(root)[0]["flagged"], "another primitive")
            other = root / "Other_Skill"
            other.mkdir()
            (other / "SKILL.md").write_text("CronCreate\n")
            self.assertTrue([r for r in scan_skills(root) if r["source"].startswith("Other_")][0]["flagged"],
                            "an unlisted skill")

    def test_the_five_flagged_wake_sources_stay_fixed(self):
        rows = {r["source"]: r for r in scan_skills(ROOT / ".claude" / "skills")}
        self.assertNotIn("ALL_Protocol_RunInbox/SKILL.md", rows, "waits on the event path, no clock primitive")
        for name in ("CMO_Workflow_MimiPage_Weekly", "CXO_Protocol_OvernightSelfWake"):
            with self.subTest(name):
                self.assertFalse(rows[name + "/SKILL.md"]["flagged"])
        text = (ROOT / ".claude/skills/CXO_Protocol_OvernightSelfWake/SKILL.md").read_text()
        self.assertNotIn("ScheduleWakeup", text)
        self.assertNotIn("/loop", text)
