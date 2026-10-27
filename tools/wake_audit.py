"""Read-only, zero-model wake inventory. Heuristic findings require review.

Exit 1: clock wake candidates; 2: incomplete inventory without findings; 0: clean.
Never executes a service or prints its command/environment (may contain secrets).

Rows that are not flagged say why: EVENT (a reviewed event gate), BACKOFF (its timed parts run
on lib/wake_backoff, checked in the source), SCHEDULED-REPORT (a weekly-or-slower calendar
report), REVIEWED (a skill allowed a counted number of clock-primitive lines), REVIEW (needs a
human look). Each reviewed list below is code: adding to one is a reviewed change.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
# Reviewed event gates, not a generic claim that any `if` is an event check.
GATED = {
    "mail_wake_sweep": "mailbox.wake_due: pending eligible letters",
    "run_watch_driver": "Follower events and active-run lifecycle; review restarts",
    "escalation_watch": "new stuck episode; timed parts paced by wake_interval",
    "secretary_waker": "pending reply letters (secretary, outside CXO/PH scope)",
}
# Timed parts that must run on lib/wake_backoff (UsageBudget P4b); the source is read, not trusted.
BACKOFF_GATED = {"escalation_watch": "tools/escalation_watch.py"}
# A report on a calendar date (weekly or slower) is a deadline, not a loop.
SCHEDULED_REPORT = ("tool_value report", "weekly report, Mon 08:00 TH: a calendar deadline, not a loop")
DATE_ANCHORED = re.compile(
    r"\s*(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\w*|weekly|monthly|quarterly|semiannually|yearly|annually)\b", re.I)
# Skills allowed some clock-primitive lines: {file: {primitive: (most lines, reason)}}. More lines
# than counted, or another primitive, is flagged again.
REVIEWED_SKILLS = {
    "CMO_Workflow_MimiPage_Weekly/SKILL.md": {
        "CronCreate": (2, "one-shot per post time (19:33 comment, 19:45 live check): a deadline, never a poll")},
    "CXO_Protocol_OvernightSelfWake/SKILL.md": {
        "CronCreate": (3, "one one-shot at a job's due time; no recurring wake, no heartbeat")},
}
PRIMITIVES = re.compile(r"\b(?:ScheduleWakeup|CronCreate|Monitor|sleep)\b|/loop\b")
CLOCK = {"ScheduleWakeup", "CronCreate", "/loop"}


def backoff_gated(key: str) -> bool:
    try:
        return "wake_interval(" in (ROOT / BACKOFF_GATED[key]).read_text()
    except (KeyError, OSError):
        return False


def date_anchored(timer_text: str | None) -> bool:
    """True when every OnCalendar spec is weekly or slower and no interval directive is set.
    No timer text (unreadable): not proven, so the report stays flagged."""
    if timer_text is None:
        return False
    specs = re.findall(r"^\s*OnCalendar=(.*)$", timer_text, re.M)
    interval = re.search(r"^\s*On(?:Boot|Startup|UnitActive|UnitInactive|Active)Sec=\s*\S", timer_text, re.M)
    return bool(specs) and not interval and all(DATE_ANCHORED.match(spec) for spec in specs)


def classify_unit(name: str, text: str, timer_text: str | None = None) -> dict | None:
    """Classify effective service command directives; comments are not evidence.

    Unknown wrappers are outside this static classifier's coverage. Mixed known
    gates and direct sends remain flagged, rather than inheriting a safe label.
    `timer_text`: the timer unit; a report counts as scheduled only if it is on a calendar date.
    """
    commands = []
    for line in text.replace("\\\n", " ").splitlines():
        match = re.match(r"\s*(ExecStart(?:Pre|Post)?|ExecCondition)=(.*)", line)
        if match:
            if not match[2].strip():
                commands = [c for c in commands if c[0] != match[1]]
            else:
                commands.append(match.groups())
    command = "\n".join(c[1] for c in commands)
    gates = [k for k in GATED if re.search(r"\b" + k + r"\b", command)]
    direct = re.search(r"send_to_cxo|SendMessage|send-keys|(?:^|[\s/])claude(?=\s|$)|idle-ping-watcher", command)
    report = bool(re.search(r"tool_value(?:\.py)?\s+report\b", command))
    if not gates and not direct and not report:
        return None
    reminder = "escalation_watch" in gates and not backoff_gated("escalation_watch")
    scheduled = report and not direct and not gates and date_anchored(timer_text)
    flagged = bool(direct or (report and not scheduled) or reminder)
    row = {"source": name, "kind": "timer", "flagged": flagged,
           "trigger": "clock / unverified gate" if flagged else "event",
           "evidence": "stuck event gate, but its timed reminder is not on wake_interval" if reminder else
           "no reviewed event gate for command" if flagged else "; ".join(GATED[k] for k in gates)}
    if not flagged and scheduled:
        row.update(trigger="scheduled-report", evidence=SCHEDULED_REPORT[1])
    elif not flagged and "escalation_watch" in gates:
        row.update(trigger="backoff", evidence=row["evidence"] + "; reminder, idle and digest on budget x tier")
    return row


def scan_skills(root: Path) -> list[dict]:
    rows = []
    for path in sorted(root.rglob("*.md")):
        hits = {}
        for number, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            for match in PRIMITIVES.finditer(line):
                hits.setdefault(match.group(), []).append(number)
        if hits:
            rel = str(path.relative_to(root))
            allowed = REVIEWED_SKILLS.get(rel, {})
            clock = CLOCK.intersection(hits)
            open_ = {c for c in clock if len(set(hits[c])) > allowed.get(c, (0, ""))[0]}
            row = {"source": rel, "kind": "skill", "flagged": bool(open_),
                   "trigger": "clock candidate" if open_ else "reviewed" if clock else "review",
                   "evidence": ", ".join(sorted(hits)), "lines": hits}
            if clock and not open_:
                row["evidence"] += "; reviewed: " + "; ".join(allowed[c][1] for c in sorted(clock))
            rows.append(row)
    return rows


def systemctl(*args):
    return subprocess.run(["systemctl", *args], capture_output=True, text=True,
                          timeout=20, check=True).stdout


def inventory() -> tuple[list[dict], list[str]]:
    rows, errors = [], []
    try:
        listing = systemctl("list-timers", "--all", "--no-pager", "--plain")
        timers = sorted(set(re.findall(r"\b[\w@.:-]+\.timer\b", listing)))
        for timer in timers:
            try:
                service = systemctl("show", timer, "--property=Unit", "--value").strip()
                row = classify_unit(timer, systemctl("cat", service), systemctl("cat", timer))
                if row:
                    rows.append(row)
            except (OSError, subprocess.SubprocessError):
                errors.append(f"cannot inspect {timer}")
    except (OSError, subprocess.SubprocessError):
        errors.append("systemd unavailable; installed unit-file fallback, activation unknown")
        for timer in sorted(Path("/etc/systemd/system").glob("*.timer")):
            try:
                match = re.search(r"^Unit=(.+)$", timer.read_text(), re.M)
                service = timer.parent / (match[1].strip() if match else timer.with_suffix(".service").name)
                texts = [service.read_text()]
                texts += [p.read_text() for p in sorted(service.with_name(service.name + ".d").glob("*.conf"))]
                row = classify_unit(timer.name, "\n".join(texts), timer.read_text())
                if row:
                    rows.append(row)
            except OSError:
                errors.append(f"cannot read service for {timer.name}")
    skills = ROOT / ".claude" / "skills"
    if skills.exists():
        rows.extend(scan_skills(skills))
    else:
        errors.append("skills directory missing")
    return rows, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    rows, errors = inventory()
    flags = sum(row["flagged"] for row in rows)
    if args.json:
        print(json.dumps({"sources": rows, "errors": errors, "flagged": flags}, indent=2))
    else:
        for error in errors:
            print(f"INCOMPLETE: {error}")
        for row in rows:
            print(f"{'FLAG' if row['flagged'] else row['trigger'].upper()} {row['source']}: {row['evidence']}")
        print(f"{len(rows)} sources; {flags} flagged; {len(errors)} inventory errors")
    return 1 if flags else 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
