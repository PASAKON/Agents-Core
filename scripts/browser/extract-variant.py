#!/usr/bin/env python3
"""Extract one PASTE-block variant from a prompt sheet, byte-exact.

Never hand-transcribe prompt bytes — this reads the sheet and slices out
the text strictly between that variant's markers, nothing more, nothing less.

    extract-variant.py <sheet.txt> <VARIANT_LETTER> <out.txt>
"""
import sys

sheet_path, letter, out_path = sys.argv[1], sys.argv[2], sys.argv[3]

with open(sheet_path, "r", encoding="utf-8") as f:
    text = f.read()

start_marker = f"· VARIANT {letter} ===\n"
end_marker = "=== ↑↑↑ PASTE STOPS HERE"

start_idx = text.index(start_marker) + len(start_marker)
end_idx = text.index(end_marker, start_idx)
block = text[start_idx:end_idx].rstrip("\n")

with open(out_path, "w", encoding="utf-8", newline="\n") as f:
    f.write(block)

print(f"variant {letter}: {len(block)} chars -> {out_path}")
