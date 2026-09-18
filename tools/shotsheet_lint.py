#!/usr/bin/env python3
"""Refuse a shot sheet that has a shot with no spoken line.

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

    print(f"{path.name}: {len(total)} shots, {len(silent)} with no spoken line")
    if not silent:
        print("PASS — every shot carries dialogue.")
        return 0

    # Consecutive silent shots are the real defect: a listener loses the thread.
    runs, run = [], [silent[0]]
    for n in silent[1:]:
        if n == run[-1] + 1:
            run.append(n)
        else:
            runs.append(run)
            run = [n]
    runs.append(run)
    runs.sort(key=len, reverse=True)

    print("\nSilent shots:", ", ".join(str(n) for n in silent))
    print("\nUnbroken silent stretches, worst first:")
    for r in runs:
        print(f"  shots {r[0]}-{r[-1]}  {len(r)} shots  {len(r) * 8}s of no one speaking")

    print(
        "\nFAIL — the CEO's rule is that every shot carries a spoken line, however\n"
        "short. Silence is allowed inside a line's delivery, not instead of it.\n"
        "Fix the sheet before spending a single credit."
    )
    return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(max(audit(Path(a)) for a in sys.argv[1:]))
