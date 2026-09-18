#!/usr/bin/env python3
"""Refuse a shot sheet that breaks the CEO's dialogue rule.

The rule (CEO 2026-09-18, refined the same day):
  - at least 80-90% of shots carry a spoken line
  - never two silent shots in a row - one is allowed, the next must speak
  - a character doing something says what they are doing while they do it


Why this exists as a script rather than a paragraph in a skill:

The rule "ตัวละครขับเนื้อเรื่อง — บทพูดขับเนื้อเรื่อง" was written into
`thai-moral-drama` as a TEST ("strip the images, read the dialogue cold") rather
than as a CONSTRAINT ("every shot carries a line"). A test run after the fact
does not stop anyone writing 24 silent shots, and on 2026-09-18 it did not: Act 1
of «บัญชี» went to camera 50% silent, with two unbroken 48-second stretches
carrying plot the audience could only get by looking.

Worse, the artefact used to run that test — a transcript file containing only the
spoken lines — cannot show a gap. It passes by construction. The check could
never fail, so it never did.

This reads the SHOT SHEET, where the gaps are visible, and exits non-zero.

    python3 tools/shotsheet_lint.py docs/scripts/banchi-ACT1.md
"""
import re
import sys
from pathlib import Path

SHOT = re.compile(r"^### SHOT (\d+)\b", re.M)
SPOKEN = "บทพูด"


MIN_SPOKEN_RATIO = 0.80   # CEO 2026-09-18: at least 80-90% of shots carry a line
MAX_SILENT_RUN = 1        # CEO 2026-09-18: one silent shot is allowed; the next MUST speak


def audit(path: Path):
    text = path.read_text(encoding="utf-8")
    marks = [(m.group(1), m.start()) for m in SHOT.finditer(text)]
    if not marks:
        print(f"{path}: no '### SHOT n' headings found — is this a shot sheet?")
        return 2

    silent, total = [], []
    for i, (num, start) in enumerate(marks):
        end = marks[i + 1][1] if i + 1 < len(marks) else len(text)
        head = text[start:end].split("```", 1)[0]
        total.append(int(num))
        if SPOKEN not in head:
            silent.append(int(num))

    ratio = 1 - len(silent) / len(total)
    print(f"{path.name}: {len(total)} shots, {len(silent)} silent, {ratio:.0%} spoken")

    # Consecutive silent shots are the defect the CEO named "dead air":
    # one silent shot is allowed, the shot after it must speak.
    runs, run = [], []
    for n in silent:
        if run and n == run[-1] + 1:
            run.append(n)
        else:
            if run:
                runs.append(run)
            run = [n]
    if run:
        runs.append(run)
    dead_air = [r for r in runs if len(r) > MAX_SILENT_RUN]

    fail = False
    if ratio < MIN_SPOKEN_RATIO:
        print(f"FAIL — only {ratio:.0%} of shots speak; the floor is {MIN_SPOKEN_RATIO:.0%}.")
        fail = True
    if dead_air:
        print("FAIL — dead air: silent shots back to back. One silent shot is allowed,")
        print("       the next one MUST carry a line.")
        for r in sorted(dead_air, key=len, reverse=True):
            print(f"         shots {r[0]}-{r[-1]}  {len(r)} shots  {len(r) * 8}s of no one speaking")
        fail = True

    if silent:
        print("Silent shots (each must be followed by a speaking one):",
              ", ".join(str(n) for n in silent))
    if fail:
        print("\nFix the sheet before spending a single credit.")
        return 1
    print("PASS — spoken ratio and dead-air rule both satisfied.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(max(audit(Path(a)) for a in sys.argv[1:]))
