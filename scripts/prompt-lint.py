#!/usr/bin/env python3
"""Flag operator/CTO/CEO guidance that has leaked into a pasteable prompt body.

These prompt files (docs/prompts/absence/*) get pasted whole into a web
composer -- whatever sits in the paste zone IS the prompt, notes included.
S1C burned two operator sessions and three renders because a block of CTO
guidance sat inside the pasted text and described the very things it was
banning (see docs/prompts/absence/AUTHORING-RULES.md). This is the check
that runs before a shot fires, and before a new/edited prompt block is
committed, so that failure mode stops depending on someone remembering to
re-read the whole block by eye.

Three zones a file can have, per AUTHORING-RULES.md Part 2 rule 2:
  NOTES zone   -- between "=== NOTES ... ===" and "=== END NOTES ==="
  PASTE zone   -- between a "paste from here" marker and a "paste stops
                  here" marker (or EOF, if there is no closing marker)
  no markers   -- 13 of the 16 files have none at all; the whole file is
                  then the paste zone, because nothing tells the operator
                  otherwise

Detectors only run against the PASTE zone (or the whole file, when there
is no zone split at all). The NOTES zone is supposed to hold this stuff.

Usage:
    scripts/prompt-lint.py FILE [FILE...] [--shot SHOT_ID]
    scripts/prompt-lint.py --validate   # check catch rate vs the 30 known
                                         # instances in AUTHORING-RULES.md Part 1 A

Exit code is non-zero iff any ERROR-severity finding was reported (i.e.
something in the "would corrupt generation" class) across all scanned
files. --validate always exits 0; it is a report, not a gate.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ABSENCE_DIR = Path(__file__).resolve().parent.parent / "docs" / "prompts" / "absence"

# --- zone markers ------------------------------------------------------

# anchored right after the opening === -- the PASTE markers' own template
# text ("everything above/below is notes, never paste it") also contains the
# bare word "notes", so a loose \bNOTES\b anywhere would misclassify them
NOTES_START_RE = re.compile(r"^===\s*NOTES\b", re.IGNORECASE)
NOTES_END_RE = re.compile(r"^===.*\bEND NOTES\b.*===\s*$", re.IGNORECASE)
PASTE_START_RE = re.compile(
    r"^===.*(PASTE FROM HERE|paste from here down).*===\s*$", re.IGNORECASE
)
PASTE_END_RE = re.compile(r"^===.*(PASTE STOPS HERE).*===\s*$", re.IGNORECASE)
# a pure separator line (block boundary) -- distinct from the marker lines
# above, which always carry words inside the ===...=== wrapper
BLOCK_SEP_RE = re.compile(r"^[=\-]{10,}\s*$")
# a sentence that nullifies a paste-start marker by telling the operator
# to paste from higher up the file (rule 3) -- operators read top to bottom
CANCEL_RE = re.compile(r"paste\s+(this\s+entire\s+text|the\s+entire\s+text)", re.IGNORECASE)

# --- content detectors (apply inside the PASTE zone only) --------------

# The CTO's own pre-fire grep from AUTHORING-RULES.md ("ก่อนกด Generate"),
# kept case-sensitive exactly as tested against the corpus -- this catches
# warning glyphs, dates, attributions, take-id mentions, file references,
# composer vocabulary and editorial notes in one pass.
GUIDANCE_GREP_RE = re.compile(
    r"⚠️|✅|\(CE[OT]|\(CTO|20[0-9]{2}-[0-9]{2}|take [0-9]|GH #|\.md|\.txt|\.MP4"
    r"|chip|plate|Elements panel|UUID|paste|operator|spoken words|Fire |Cuts against|as S[0-9]"
)
TAKE_ID_RE = re.compile(r"\b[0-9a-f]{8}\b")
# composer mechanics the CTO's own grep (above) doesn't cover but the task
# brief names explicitly
COMPOSER_TERM_RE = re.compile(r"\b(upload|button|tab|picker|composer|drop-down|dropdown)\b", re.IGNORECASE)
ATTRIBUTION_RE = re.compile(r"\(CE[OT]\b|\(CTO\b|CEO 20\d{2}-|CTO[ -](?!\w*ONLY)|per your")
DATE_RE = re.compile(
    r"\b20\d{2}-\d{2}-\d{2}\b"
    r"|\b\d{1,2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b"
)
AT_VIDEO_RE = re.compile(r"@Video\b")
QUOTED_REF_RE = re.compile(r'"[^"\n]{2,80}[—–][^"\n]{0,80}"')
QUOTED_SAID_RE = re.compile(r'\b(said|wrote|quoted?|reads?)\b[^".\n]{0,20}"[^"\n]+"', re.IGNORECASE)
DESCRIBES_FORBIDDEN_RE = re.compile(
    r"\btwo identical\b"
    r"|\brendered (?:him|it|them|her) TWICE\b"
    r"|\bcame back with TWO\b"
    r"|\b(?:Do not|Never|Don't) write [\"']"
    r"|\btwo \w+, ?two \w+\b",
    re.IGNORECASE,
)
# a bare cross-scene pointer sitting in prose (rule 9 -- "as S12a" is already
# in the CTO grep above; this catches the "in S14" / "from S12" shape too)
SCENE_CROSS_REF_RE = re.compile(r"\b(?:in|from|brings.{0,20}in) S\d+\b")
# rule 10 / PROMPT-STYLE.md:75-79 -- meta-commentary phrases measured to get
# spoken aloud even when visual review passes clean
UNSAFE_PHRASE_RE = re.compile(
    r"with no idea what he is doing"
    r"|telling the same truth he has told all along"
    r"|this is the line the film turns on"
    r"|chose not to give this line a face"
    r"|by this line he believes it himself"
    r"|this silence is the most important beat",
    re.IGNORECASE,
)
# a timeline restarting to [0s] more than once inside one block is a second
# shot smuggled into the same paste-able unit (rule 11: one block = one shot)
TIMELINE_RESTART_RE = re.compile(r"\[0s\]")

# seed contradiction pairs: (negative pattern, positive pattern it contradicts, label)
CONTRADICTION_PAIRS = [
    (
        re.compile(r"no un-?mirrored", re.IGNORECASE),
        re.compile(r"never mirrored|correct-way-round", re.IGNORECASE),
        "negative bans the un-mirrored (correct) reading while a reference in the same block demands correct-way-round text",
    ),
    (
        re.compile(r"no large \w+", re.IGNORECASE),
        re.compile(r"large and unmistakable|large, unmistakable", re.IGNORECASE),
        "negative bans 'large' while a reference in the same block demands large and unmistakable",
    ),
]


@dataclass
class Finding:
    file: str
    line: int
    cls: str
    severity: str  # "ERROR" or "WARN"
    text: str
    action: str


@dataclass
class ZoneMap:
    # per-line zone: "notes", "paste", "header", or "unzoned"
    zones: list[str]
    has_markers: bool
    malformed: list[tuple[int, str, str]] = field(default_factory=list)


def build_zone_map(lines: list[str]) -> ZoneMap:
    n = len(lines)
    has_markers = False
    malformed: list[tuple[int, str, str]] = []

    notes_start = notes_end = paste_start = paste_end = None
    for i, line in enumerate(lines):
        if NOTES_START_RE.match(line):
            notes_start, has_markers = i, True
        elif NOTES_END_RE.match(line):
            notes_end, has_markers = i, True
        elif PASTE_START_RE.match(line):
            paste_start, has_markers = i, True
        elif PASTE_END_RE.match(line):
            paste_end, has_markers = i, True

    if not has_markers:
        # no zone split at all -- the whole file is what an operator would
        # paste, because nothing tells them otherwise
        return ZoneMap(zones=["paste"] * n, has_markers=False)

    zones = ["header"] * n

    if notes_start is not None:
        if notes_end is None:
            # dangerous: an unclosed NOTES zone means everything after it,
            # including what should be paste text, gets silently swallowed
            # as "notes" -- or, if we didn't zone it, notes text bleeds
            # forward with unknown extent. Either way this needs a fix.
            malformed.append((notes_start + 1, "ERROR", "NOTES zone opened but never closed with '=== END NOTES ==='"))
            notes_end = n - 1
        for i in range(notes_start, min(notes_end + 1, n)):
            zones[i] = "notes"

    if paste_start is not None:
        end = paste_end if paste_end is not None else n - 1
        if paste_end is None:
            # not dangerous by itself -- paste-to-EOF is the pattern all
            # three existing videoref files already use on purpose. Still
            # worth flagging since Part 2 rule 2 wants a head AND a foot.
            malformed.append((paste_start + 1, "WARN", "PASTE zone has no closing 'PASTE STOPS HERE' marker -- treated as open to EOF (valid pattern, but rule 2 wants a foot marker too)"))
        for i in range(paste_start, min(end + 1, n)):
            zones[i] = "paste"

    return ZoneMap(zones=zones, has_markers=True, malformed=malformed)


def split_blocks(lines: list[str]) -> list[tuple[int, int, str]]:
    """Return (start, end, header) 0-indexed inclusive line ranges between pure
    separator lines. Shot titles in this corpus are sandwiched between two
    separator lines (`--- \\n S1A * THE FLOOR \\n ---`), which would otherwise
    split the title from its own body into two unrelated blocks -- a lone
    title segment is merged forward into the block that follows it, and its
    text is kept as that merged block's header for --shot matching."""
    bounds = [i for i, l in enumerate(lines) if BLOCK_SEP_RE.match(l)]
    raw = []
    prev = 0
    for b in bounds:
        if b > prev:
            raw.append((prev, b - 1))
        prev = b + 1
    if prev < len(lines):
        raw.append((prev, len(lines) - 1))

    def first_nonblank(s: int, e: int) -> str:
        return next((lines[i] for i in range(s, e + 1) if lines[i].strip()), "")

    def is_lone_title(s: int, e: int) -> bool:
        text = "\n".join(lines[s : e + 1]).strip()
        return bool(text) and "\n" not in text.strip("\n") and len(text) < 100

    merged: list[tuple[int, int, str]] = []
    i = 0
    while i < len(raw):
        s, e = raw[i]
        if is_lone_title(s, e) and i + 1 < len(raw):
            header = first_nonblank(s, e)
            ns, ne = raw[i + 1]
            merged.append((s, ne, header))
            i += 2
        else:
            merged.append((s, e, first_nonblank(s, e)))
            i += 1
    return merged


def lint_file(path: Path, shot: str | None = None) -> list[Finding]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    lines = raw.split("\n")
    fname = path.name
    findings: list[Finding] = []

    zmap = build_zone_map(lines)

    if not zmap.has_markers:
        findings.append(
            Finding(
                fname, 1, "NO_MARKER", "WARN",
                "(file has no NOTES/PASTE markers at all)",
                "add the two-marker pair from AUTHORING-RULES.md Part 2 rule 2 so an "
                "operator (or this tool) can tell notes from paste text",
            )
        )

    for ln, sev, why in zmap.malformed:
        findings.append(Finding(fname, ln, "MALFORMED_MARKER", sev, lines[ln - 1].strip(), why))

    # marker-cancelling sentence: anywhere in the file, a "paste this entire
    # text" instruction sitting above a real paste-start marker
    for i, line in enumerate(lines):
        if CANCEL_RE.search(line) and zmap.zones[i] != "paste":
            findings.append(
                Finding(
                    fname, i + 1, "MARKER_CANCELLED", "ERROR", line.strip(),
                    "operators read top-to-bottom and will follow this instead of the "
                    "marker below it -- reword to 'paste everything below the marker.'",
                )
            )

    blocks = split_blocks(lines)
    if shot:
        shot_re = re.compile(r"\b" + re.escape(shot) + r"\b", re.IGNORECASE)
        shot_blocks = [(s, e, h) for s, e, h in blocks if shot_re.search(h)]
        if shot_blocks:
            blocks = shot_blocks
        else:
            print(f"# {fname}: shot '{shot}' not found in any block header -- scanning whole file", file=sys.stderr)

    scan_lines = set()
    for s, e, _h in blocks:
        for i in range(s, e + 1):
            if zmap.zones[i] == "paste":
                scan_lines.add(i)

    # per-line detectors, restricted to the paste zone (and to the
    # requested shot's blocks, if --shot was given)
    for i in sorted(scan_lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or BLOCK_SEP_RE.match(line):
            continue
        if PASTE_START_RE.match(line) or PASTE_END_RE.match(line) or NOTES_START_RE.match(line) or NOTES_END_RE.match(line):
            continue

        if GUIDANCE_GREP_RE.search(line):
            findings.append(
                Finding(
                    fname, i + 1, "GUIDANCE_LEAK", "ERROR", stripped,
                    "operator/CTO/CEO guidance or composer mechanics sitting in the "
                    "paste zone -- move to the NOTES zone or delete",
                )
            )
        if TAKE_ID_RE.search(line):
            for m in TAKE_ID_RE.finditer(line):
                findings.append(
                    Finding(fname, i + 1, "TAKE_ID", "ERROR", m.group(0),
                            "take id in pasteable text -- move the sentence to NOTES")
                )
        if ATTRIBUTION_RE.search(line):
            findings.append(
                Finding(fname, i + 1, "ATTRIBUTION", "ERROR", stripped,
                        "who-said-it stamp in pasteable text -- keep the rule, drop the attribution")
            )
        if DATE_RE.search(line):
            findings.append(
                Finding(fname, i + 1, "DATE_STAMP", "ERROR", stripped,
                        "date stamp in pasteable text -- move to NOTES or drop")
            )
        if QUOTED_REF_RE.search(line) or QUOTED_SAID_RE.search(line):
            findings.append(
                Finding(fname, i + 1, "QUOTED_REFERENCE", "ERROR", stripped,
                        "quoted string reads like a reference/chip declaration -- the model "
                        "may render it as on-screen or spoken text; remove the quote")
            )
        if COMPOSER_TERM_RE.search(line) and not GUIDANCE_GREP_RE.search(line):
            findings.append(
                Finding(fname, i + 1, "COMPOSER_MECHANICS", "ERROR", stripped,
                        "composer UI vocabulary in pasteable text -- describe the image, not the tool")
            )
        if DESCRIBES_FORBIDDEN_RE.search(line):
            findings.append(
                Finding(fname, i + 1, "PROHIBITION_BY_DESCRIPTION", "ERROR", stripped,
                        "a ban written as a picture -- the model reads the description, not "
                        "the intent; replace with the positive statement of what IS wanted")
            )
        if SCENE_CROSS_REF_RE.search(line):
            findings.append(
                Finding(fname, i + 1, "SCENE_CROSS_REFERENCE", "ERROR", stripped,
                        "points at another scene's off-frame events -- this block will be "
                        "pasted alone; the other scene doesn't exist to the model")
            )
        if UNSAFE_PHRASE_RE.search(line):
            findings.append(
                Finding(fname, i + 1, "SPOKEN_ALOUD_RISK", "ERROR", stripped,
                        "meta-commentary phrase from PROMPT-STYLE.md's measured UNSAFE list -- "
                        "S15a take 1 spoke a phrase like this aloud; visual review alone won't "
                        "catch it, move the reasoning out of the beat")
            )

    # per-block detectors
    for s, e, _h in blocks:
        block_paste_lines = [i for i in range(s, e + 1) if zmap.zones[i] == "paste"]
        if not block_paste_lines:
            continue
        block_text = "\n".join(lines[i] for i in block_paste_lines)

        seen_any = False
        for i in block_paste_lines:
            occurrences = list(AT_VIDEO_RE.finditer(lines[i]))
            for k, _m in enumerate(occurrences):
                if seen_any:
                    findings.append(
                        Finding(fname, i + 1, "SECOND_AT_VIDEO", "ERROR", lines[i].strip(),
                                "@Video mentioned more than once in this shot's paste text -- "
                                "the platform accepts one video reference per generation; "
                                "mention it once and refer to it with plain words after that")
                    )
                seen_any = True

        restart_lines = [i for i in block_paste_lines if TIMELINE_RESTART_RE.search(lines[i])]
        if len(restart_lines) > 1:
            for i in restart_lines[1:]:
                findings.append(
                    Finding(fname, i + 1, "MULTIPLE_SHOTS_IN_BLOCK", "ERROR", lines[i].strip(),
                            "timeline restarts to [0s] again inside the same block -- this "
                            "reads as a second shot; split into its own block (rule 11)")
                )

        for neg_re, pos_re, label in CONTRADICTION_PAIRS:
            neg_match = neg_re.search(block_text)
            if neg_match and pos_re.search(block_text):
                line_no = block_text[: neg_match.start()].count("\n") + block_paste_lines[0] + 1
                findings.append(
                    Finding(fname, line_no, "NEGATIVE_CONTRADICTS_REFERENCE", "ERROR",
                            neg_match.group(0), label)
                )

    return findings


def print_findings(findings: list[Finding]) -> None:
    for f in findings:
        print(f'{f.file}:{f.line}: [{f.severity}] {f.cls} — "{f.text}" → {f.action}')


# --- validation against AUTHORING-RULES.md Part 1 §A (the "would corrupt
# generation" instances) -------------------------------------------------
# (index, file, line_lo, line_hi, one-line description) -- transcribed by
# hand from docs/prompts/absence/AUTHORING-RULES.md Part 1 A1-A6, items 1-30.
KNOWN_INSTANCES = [
    (1, "s1-angles.txt", 67, 96, "S1C-ONLY OVERRIDES block sitting in body"),
    (2, "s1-angles.txt", 12, 12, "shared header carries LOCKED into S1C"),
    (3, "s1-angles.txt", 21, 76, "cart Element binding vs wheels-visible contradiction (blocker)"),
    (4, "s1-angles.txt", 103, 106, "S1D take id + TWO Dupes description"),
    (5, "s4-s5.txt", 170, 198, "camera-change announced but beat/negative still old camera"),
    (6, "s2-accident.txt", 40, 125, "plaque falls vs plaque doesn't fall contradiction"),
    (7, "s6-s18.txt", 132, 333, "negative bans un-mirrored while reference demands correct-way-round"),
    (8, "s4-s5.txt", 123, 123, "negative bans large crack while reference demands large"),
    (9, "s2-accident.txt", 17, 121, "cart design has ladder, negative bans ladder"),
    (10, "s4-s5.txt", 83, 110, "people count mismatch (two of three / eight / ten)"),
    (11, "s7-s9.txt", 158, 301, "ONE VALDER block x4 describes two identical men"),
    (12, "s-arrivals.txt", 217, 219, "post-mortem quoting banned phrase + take id"),
    (13, "s-arrivals.txt", 256, 262, "'never write the row of five' contradicts own body"),
    (14, "s4-s5.txt", 100, 102, "take-1 post-mortem sentence in beat"),
    (15, "s2-accident.txt", 34, 35, "SIZE CONTINUITY describes the wrong (bigger) painting"),
    (16, "s2-accident.txt", 85, 99, "essay-to-reader + QC PASS/FAIL rubric in body"),
    (17, "s6-s18.txt", 95, 306, "VIEWPOINT REBALANCE history block x2"),
    (18, "s7-s9.txt", 309, 309, "'this is the line the film turns on' spoken-aloud risk"),
    (19, "s6-s18.txt", 617, 619, "approval note parenthetical stuck to dialogue line"),
    (20, "s4-s5.txt", 161, 165, "CTO casting call note + other scene's dialogue quoted in"),
    (21, "s13-the-back-door.txt", 18, 24, "STALE mention note between REFERENCES and declaration"),
    (22, "s13-the-back-door.txt", 65, 65, "'same three as S13a' pointer instead of real references"),
    (23, "s-dupe-inserts.txt", 28, 38, "5 shots in one block, dialogue dragged into NO DIALOGUE shot"),
    (24, "s7-reshoot-videoref.txt", 32, 37, "note wedged mid-sentence, Elements-panel jargon"),
    (25, "s-extras.txt", 150, 152, "CTO reading-of-brief note between spec and beat"),
    (26, "s-price-inserts.txt", 22, 25, "'the film cuts to' / 'the room goes mad' vs no-cuts/no-people negatives"),
    (27, "s13-the-back-door.txt", 93, 94, "HANDOFF note referencing off-frame events"),
    (28, "s-price-inserts.txt", 34, 35, "REWRITTEN note + 'the arrivals see' inserts a person into no-people shot"),
    (29, "s-extras.txt", 181, 191, "two shots (X8a/X8b) sharing one timeline block"),
    (30, "s1-v3-videoref.txt", 8, 8, "'paste THIS ENTIRE TEXT' cancels marker below (also s2b-v3-split-videoref.txt:13, s7-reshoot-videoref.txt:8)"),
]


def run_validate() -> int:
    files_needed = sorted({row[1] for row in KNOWN_INSTANCES} | {"s2b-v3-split-videoref.txt", "s7-reshoot-videoref.txt"})
    all_findings: dict[str, list[Finding]] = {}
    for fname in files_needed:
        p = ABSENCE_DIR / fname
        if p.exists():
            all_findings[fname] = lint_file(p)

    caught, missed = [], []
    for idx, fname, lo, hi, desc in KNOWN_INSTANCES:
        fs = all_findings.get(fname, [])
        hit = any(fname == f.file and lo - 2 <= f.line <= hi + 2 for f in fs)
        (caught if hit else missed).append((idx, fname, lo, hi, desc))

    known_ranges: dict[str, list[tuple[int, int]]] = {}
    for idx, fname, lo, hi, desc in KNOWN_INSTANCES:
        known_ranges.setdefault(fname, []).append((lo, hi))

    extra = []
    for fname, fs in all_findings.items():
        for f in fs:
            ranges = known_ranges.get(fname, [])
            if not any(lo - 2 <= f.line <= hi + 2 for lo, hi in ranges):
                extra.append(f)

    print(f"=== VALIDATE: {len(caught)}/{len(KNOWN_INSTANCES)} known instances caught ===\n")
    print("-- caught --")
    for idx, fname, lo, hi, desc in caught:
        print(f"  #{idx:>2} {fname}:{lo}-{hi} — {desc}")
    print("\n-- missed --")
    for idx, fname, lo, hi, desc in missed:
        print(f"  #{idx:>2} {fname}:{lo}-{hi} — {desc}")
    print(f"\n-- findings outside the 30 known ranges ({len(extra)}) --")
    for f in extra:
        print(f'  {f.file}:{f.line}: [{f.severity}] {f.cls} — "{f.text}"')

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", type=Path, help="prompt file(s) to lint")
    ap.add_argument("--shot", help="only scan the block(s) whose header line matches this shot id")
    ap.add_argument("--validate", action="store_true", help="check catch rate against the 30 known instances")
    args = ap.parse_args()

    if args.validate:
        return run_validate()

    if not args.files:
        ap.error("give at least one file, or --validate")

    any_error = False
    for path in args.files:
        if not path.exists():
            print(f"{path}: not found", file=sys.stderr)
            any_error = True
            continue
        findings = lint_file(path, shot=args.shot)
        print_findings(findings)
        if any(f.severity == "ERROR" for f in findings):
            any_error = True

    return 1 if any_error else 0


if __name__ == "__main__":
    sys.exit(main())
