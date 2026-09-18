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
MIN_SYLLABLES = 14        # per 8-second shot. Reference reel: ~1.8 syl/s overall. Act 1 averaged 7 and
                          # was unwatchable; Thai conversation runs ~4-5 syl/s, so an
                          # 8s shot carries ~32-40 at full talk. 20 = speech fills ~5s.
MAX_SYLLABLES = 30        # shot 48 carried ~40 and the model dropped the last two lines
MAX_SILENT_RUN = 1        # CEO 2026-09-18: one silent shot is allowed; the next MUST speak

# The thresholds belong to the CEO and bend to the story ("กฎนี้เปลี่ยนได้ทุกเมื่อ
# ขึ้นอยู่กับเนื้อเรื่อง ตามประสงค์ของฉัน", 2026-09-18). A sheet may carry its own
# values on one line near the top, and MUST say who ruled it and when, so nobody
# quietly loosens the rule for their own convenience:
#
#   <!-- lint: min_spoken=0.70 max_silent_run=2 (CEO 2026-10-02: ฉากไล่ล่าเงียบ) -->
#
# A line without "(CEO" in it is ignored and the defaults apply.
OVERRIDE = re.compile(r"<!--\s*lint:([^>]*?)\(CEO[^>]*-->")


def thresholds(text: str):
    m = OVERRIDE.search(text)
    if not m:
        return MIN_SPOKEN_RATIO, MAX_SILENT_RUN, None
    kv = dict(re.findall(r"(\w+)=([\d.]+)", m.group(1)))
    ratio = float(kv.get("min_spoken", MIN_SPOKEN_RATIO))
    run = int(kv.get("max_silent_run", MAX_SILENT_RUN))
    return ratio, run, m.group(0)


def audit(path: Path):
    text = path.read_text(encoding="utf-8")
    marks = [(m.group(1), m.start()) for m in SHOT.finditer(text)]
    if not marks:
        print(f"{path}: no '### SHOT n' headings found — is this a shot sheet?")
        return 2

    silent, total, thin, fat = [], [], [], []
    for i, (num, start) in enumerate(marks):
        end = marks[i + 1][1] if i + 1 < len(marks) else len(text)
        head = text[start:end].split("```", 1)[0]
        total.append(int(num))
        if SPOKEN not in head:
            silent.append(int(num))
            continue
        # every quoted Thai line in the header, summed; ~1 syllable per 1.6 Thai letters
        lines = re.findall(r'`"([^"]+)"`', head)
        syl = round(sum(len(re.findall(r"[ก-ฮ]", l)) for l in lines) / 1.6)
        dm = re.search(r"·\s*(4|6|8|10)\s*s\b", head.splitlines()[0])
        dur = int(dm.group(1)) if dm else 8
        lo, hi = round(MIN_SYLLABLES * dur / 8), round(MAX_SYLLABLES * dur / 8)
        if syl < lo:
            thin.append((int(num), syl))
        elif syl > hi:
            fat.append((int(num), syl))

    min_ratio, max_run, ruling = thresholds(text)
    if ruling:
        print(f"CEO override in sheet: {ruling}")
    ratio = 1 - len(silent) / len(total)
    print(f"{path.name}: {len(total)} shots, {len(silent)} silent, {ratio:.0%} spoken "
          f"(floor {min_ratio:.0%}, max silent run {max_run})")

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
    dead_air = [r for r in runs if len(r) > max_run]

    fail = False
    if ratio < min_ratio:
        print(f"FAIL — only {ratio:.0%} of shots speak; the floor is {min_ratio:.0%}.")
        fail = True
    if dead_air:
        print(f"FAIL — dead air: more than {max_run} silent shot(s) back to back.")
        for r in sorted(dead_air, key=len, reverse=True):
            print(f"         shots {r[0]}-{r[-1]}  {len(r)} shots  {len(r) * 8}s of no one speaking")
        fail = True

    if thin:
        print(f"FAIL — {len(thin)} shot(s) speak for under ~5 of their 8 seconds "
              f"(< {MIN_SYLLABLES} syllables per 8 s, scaled to the shot's length). One short line per shot is dead air with a word in it.")
        print("       " + ", ".join(f"{n}({k})" for n, k in thin))
        fail = True
    if fat:
        print(f"WARN — {len(fat)} shot(s) carry more than the model reliably delivers in 8s "
              f"(> {MAX_SYLLABLES} per 8 s, scaled; shot 48 dropped its last two lines at ~40):")
        print("       " + ", ".join(f"{n}({k})" for n, k in fat))
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
