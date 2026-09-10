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
single word-wrap newlines to a space (and preserving any real blank-line
paragraph breaks, if the sheet has them) makes the landed innerText match
the source length exactly, char for char.

    extract-paste-block.py <sheet.txt> <out.txt> [--keep-newlines]

--keep-newlines skips the flatten step, for a sheet whose PASTE block is
already meant to render as multiple paragraphs (blank-line separated).
"""
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

if not keep_newlines and "\n\n" not in block:
    # No real blank-line paragraph breaks in this block -- every \n is a
    # word-wrap artifact, so flatten all of them to a single space.
    block = block.replace("\n", " ")

with open(out_path, "w", encoding="utf-8", newline="\n") as f:
    f.write(block)

print(f"{len(block)} chars -> {out_path}")
