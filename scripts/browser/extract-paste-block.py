#!/usr/bin/env python3
"""Extract the PASTE block from an absence prompt sheet, byte-exact, and
flatten word-wrap line breaks to spaces so Lexical doesn't render every
hard-wrapped source line as its own paragraph.

Never hand-transcribe prompt bytes — this reads the sheet and slices out
the text strictly between the paste markers, nothing more, nothing less.

Background: pasting a sheet's PASTE block verbatim (newlines intact) lands
correctly in Lexical's raw text, but the composer's own innerText adds one
extra character per line break (each hard-wrapped line becomes its own
paragraph), so a landed-length check against the raw file will show a
mismatch of exactly (line count - 1) characters even though nothing was
corrupted -- discovered and fixed the same way earlier on the TV-wall
plate sheets (docs/reports/absence-plate-tv-wall-winbox.md). Flattening
single word-wrap newlines to a space, WITHIN each real paragraph, makes
the landed innerText match the source length exactly, char for char.

A sheet can mix both: some blocks (S22, S2R-Q) are one giant word-wrapped
paragraph with zero blank lines; others (S2PT) are genuinely multi-
paragraph (blank-line separated, one paragraph per beat) AND each of
those paragraphs is itself hard-wrapped across several source lines. A
naive "keep everything if any blank line exists" rule under-flattens the
second case -- caught 2026-09-10 on the S2PT take-4 sheet, 192 raw lines
where only ~15 are real paragraph breaks. So: split on blank lines first,
flatten each paragraph's internal single newlines to a space, then
rejoin paragraphs with a blank line.

    extract-paste-block.py <sheet.txt> <out.txt> [--keep-newlines]

--keep-newlines skips the flatten step entirely, for a sheet whose PASTE
block must land byte-identical to the source (rare; verify against a
landed-length check either way).
"""
import re
import sys

sheet_path, out_path = sys.argv[1], sys.argv[2]
keep_newlines = "--keep-newlines" in sys.argv[3:]

with open(sheet_path, "r", encoding="utf-8") as f:
    text = f.read()

start_marker = "PASTE FROM HERE"
end_marker = "PASTE STOPS HERE"

start_line_end = text.index("\n", text.index(start_marker)) + 1
end_idx = text.rindex("===", 0, text.index(end_marker))
block = text[start_line_end:end_idx]

lines = block.split("\n")
while lines and lines[-1].strip().startswith("==="):
    lines.pop()
block = "\n".join(lines).rstrip("\n")

if not keep_newlines:
    # Split on one-or-more blank lines (real paragraph breaks), flatten
    # word-wrap newlines within each paragraph, rejoin with a single
    # blank line between paragraphs.
    paragraphs = re.split(r"\n\s*\n", block)
    paragraphs = [p.replace("\n", " ") for p in paragraphs]
    block = "\n\n".join(paragraphs)

with open(out_path, "w", encoding="utf-8", newline="\n") as f:
    f.write(block)

print(f"{len(block)} chars -> {out_path}")
