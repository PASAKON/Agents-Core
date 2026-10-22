"""Read-only, zero-model wake inventory. Heuristic findings require review.

Exit 1: clock wake candidates; 2: incomplete inventory without findings; 0: clean.
Never executes a service or prints its command/environment (may contain secrets).
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
    "escalation_watch": "new stuck episode; includes one timed reminder",
    "secretary_waker": "pending reply letters (secretary, outside CXO/PH scope)",
}
PRIMITIVES = re.compile(r"\b(?:ScheduleWakeup|CronCreate|Monitor|sleep)\b|/loop\b")
CLOCK = {"ScheduleWakeup", "CronCreate", "/loop"}


def classify_unit(name: str, text: str) -> dict | None:
    """Classify effective service command directives; comments are not evidence.

    Unknown wrappers are outside this static classifier's coverage. Mixed known
    gates and direct sends remain flagged, rather than inheriting a safe label.
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
    reminder = "escalation_watch" in gates
    flagged = bool(direct or report or reminder)
    return {"source": name, "kind": "timer", "flagged": flagged,
            "trigger": "clock / unverified gate" if flagged else "event",
            "evidence": "stuck event gate plus timed unchanged-episode reminder" if reminder else
            "no reviewed event gate for command" if flagged else "; ".join(GATED[k] for k in gates)}


def scan_skills(root: Path) -> list[dict]:
    rows = []
    for path in sorted(root.rglob("*.md")):
        hits = {}
        for number, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            for match in PRIMITIVES.finditer(line):
                hits.setdefault(match.group(), []).append(number)
        if hits:
            rows.append({"source": str(path.relative_to(root)), "kind": "skill",
                         "flagged": bool(CLOCK.intersection(hits)),
                         "trigger": "clock candidate" if CLOCK.intersection(hits) else "review",
                         "evidence": ", ".join(sorted(hits)), "lines": hits})
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
                row = classify_unit(timer, systemctl("cat", service))
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
                row = classify_unit(timer.name, "\n".join(texts))
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
            print(f"{'FLAG' if row['flagged'] else 'REVIEW' if row['trigger'] == 'review' else 'EVENT'} {row['source']}: {row['evidence']}")
        print(f"{len(rows)} sources; {flags} flagged; {len(errors)} inventory errors")
    return 1 if flags else 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
