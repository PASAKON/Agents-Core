"""Reconstruct spoken "lines" (matching the reference's own per-utterance
bottom captions) from the char-split word-level whisper output. Whisper's own
segment boundaries under-split (vad_filter=False merged multiple captions into
one segment, e.g. seg 7 spans 15.18-29.98s) — this instead splits on any gap
between consecutive tokens > GAP_S, which lines up with real pauses between
spoken sentences, and reconstructs each line's text by concatenating token
text as-is (leading spaces already mark real word starts; Thai char-split
tokens have none and fuse correctly), per seed/README.md's note.

Usage: python build_lines.py words_raw.tsv > measurements/lines.tsv
Output columns: line_id, t0, t1, text
"""
import sys, csv

GAP_S = 0.12

rows = list(csv.DictReader(open(sys.argv[1]), delimiter="\t"))
lines = []
cur_words = []
cur_t0 = None
prev_t1 = None
for r in rows:
    t0, t1 = float(r["t0"]), float(r["t1"])
    if prev_t1 is not None and t0 - prev_t1 > GAP_S:
        lines.append((cur_t0, prev_t1, "".join(cur_words)))
        cur_words = []
        cur_t0 = None
    if cur_t0 is None:
        cur_t0 = t0
    cur_words.append(r["word"])
    prev_t1 = t1
if cur_words:
    lines.append((cur_t0, prev_t1, "".join(cur_words)))

print("line_id\tt0\tt1\ttext")
for i, (t0, t1, text) in enumerate(lines):
    print(f"{i}\t{t0:.3f}\t{t1:.3f}\t{text.strip()}")
