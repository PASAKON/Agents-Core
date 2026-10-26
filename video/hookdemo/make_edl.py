"""Build edl.json + timing.json for the ILAG hook demo (task-ee1dbcf0) from ONE narration file and its alignment.

usage: make_edl.py <work dir> --audio take.mp3 --align take.json [--phrases phrases.json] [--lines lines.txt]

Chain: alignment -> phrase start/end (align.py, by character offset) -> cut times and subtitle times -> work/edl.json
(for ilag_cut.py) + work/timing.json.  Nothing is sped up: the voice plays at the speed it was made.
The montage lasts as long as the voice (last phrase end + TAIL); the kit title (2 s) and rewcard (1 s) come after it.
A cut is anchored to a phrase, not to a number of seconds, so a new take with other pauses moves every cut with it:
  None                       the first cut, at 0
  ("s", line, phrase, off)   the phrase's start + off
  ("e", line, phrase, off)   the phrase's end + off
  ("g", line, phrase, frac)  frac of the way through the silence after that phrase (0 = its end, 1 = next phrase starts)
Exit non-zero, naming the phrase, when the alignment does not have the shape or the phrase (align.py).
"""
import argparse
import json
import math
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import align  # noqa: E402

FPS = 24
TAIL = 0.34          # the montage runs this long past the last spoken word
SUB_LEAD, SUB_HOLD, SUB_MIN = 0.02, 0.30, 0.8   # a subtitle shows a little before its line, holds after it, >= 0.8 s
MIN_CUT = 0.4
TITLE_S, REW_S = 2.0, 1.0

# (anchor, src time in ep5-ep1.mp4, script shot id, what the cut shows)
CUTS = [
    (None,               4.2,   "S1",  "the mother pounding at the stall"),
    (("s", 1, 2, -0.02), 54.0,  "S7",  "the mother chopping garlic"),
    (("e", 1, 2, -0.25), 8.0,   "S1",  "the mother pounding, the collector beside her"),
    (("s", 2, 1, -0.02), 45.0,  "S6",  "pestle raised at her son"),
    (("s", 2, 3, -0.02), 48.0,  "S6",  "the son takes it in"),
    (("g", 2, 3, 0.5),   37.0,  "S5",  "phone held at arm's length, no glasses"),
    (("s", 3, 2, -0.02), 40.0,  "S5",  "the son looks on while she holds the phone"),
    (("g", 3, 2, 0.5),   20.5,  "S3",  "the son asks what is wrong"),
    (("s", 4, 2, -0.02), 24.0,  "S3",  "her bright smile over the papaya"),
    (("g", 4, 2, 0.9),   11.0,  "S2",  "the collector at the stall"),
    (("s", 5, 2, -0.02), 9.5,   "S1",  "the collector speaking: the rent"),
    (("s", 5, 3, -0.02), 14.5,  "S2",  "the mother, palms pressed together"),
    (("g", 5, 3, 0.5),   17.0,  "S2",  "the collector looking back: tomorrow noon"),
    (("s", 6, 2, -0.02), 52.0,  "S7",  "the son wiping his hands, jaw set"),
    (("s", 6, 3, -0.02), 133.0, "S17", "a hand of blank cards fanned out"),
]


def fq(x):
    return round(x * FPS) / FPS


def fail(msg):
    print(f"make_edl.py ERROR: {msg}", file=sys.stderr)
    sys.exit(2)


ap = argparse.ArgumentParser()
ap.add_argument("work")
ap.add_argument("--audio", required=True)
ap.add_argument("--align", required=True)
ap.add_argument("--phrases", default=str(Path(__file__).resolve().parent / "phrases.json"))
ap.add_argument("--lines", default=str(Path(__file__).resolve().parent / "lines.txt"))
a = ap.parse_args()
W = Path(a.work)

try:
    phrases = align.load(a.phrases)
    times = align.phrase_times(align.load(a.align), phrases)
except align.AlignError as e:
    fail(str(e))
lines = [x.strip() for x in Path(a.lines).read_text(encoding="utf-8").splitlines() if x.strip()]
if len(lines) != len(phrases):
    fail(f"{a.lines} has {len(lines)} lines but {a.phrases} has {len(phrases)}")
try:
    audio_len = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                      a.audio], capture_output=True, text=True, check=True).stdout)
except (subprocess.CalledProcessError, ValueError):
    fail(f"cannot read the duration of {a.audio}")


WJ = "\u2060"
LEADING = "เแโใไ"


def glue(text, phrases_of_line):
    """The kit sub wraps Thai by dictionary and split บางอย่าง mid-word.  Put a word joiner between the characters of each
    phrase found in the line, so a wrap can only fall between phrases.  Never in front of a combining mark or behind a
    leading vowel, where it could break the glyph."""
    out, cur = [], 0
    for ph in phrases_of_line:
        k = text.find(ph.strip(), cur)
        if k < 0:
            continue
        out.append(text[cur:k])
        chars = list(ph.strip())
        g = chars[0]
        for prev, c in zip(chars, chars[1:]):
            g += (c if (unicodedata.category(c) == "Mn" or prev in LEADING or c.isspace() or prev.isspace()) else WJ + c)
        out.append(g)
        cur = k + len(ph.strip())
    out.append(text[cur:])
    return "".join(out)


def T(i, j):
    return times[i - 1][j - 1]


order = [(i, j) for i, row in enumerate(times, 1) for j in range(1, len(row) + 1)]
last_end = T(*order[-1])[1]
if last_end > audio_len + 0.3:
    fail(f"the alignment runs to {last_end:.2f} s but {a.audio} is only {audio_len:.2f} s long: wrong audio for this alignment")
mend = fq(last_end + TAIL)


def at(anchor):
    if anchor is None:
        return 0.0
    kind, i, j, x = anchor
    if kind == "s":
        return T(i, j)[0] + x
    if kind == "e":
        return T(i, j)[1] + x
    nxt = order[order.index((i, j)) + 1]
    return T(i, j)[1] + x * (T(*nxt)[0] - T(i, j)[1])


starts = [fq(max(at(c[0]), 0.0)) for c in CUTS]
for n in range(1, len(starts)):
    if starts[n] - starts[n - 1] < MIN_CUT:
        fail(f"cut {n + 1} starts {starts[n]:.2f} s, only {starts[n] - starts[n - 1]:.2f} s after cut {n}: the pauses of this take do not fit the cut list")
if mend - starts[-1] < MIN_CUT:
    fail(f"the last cut would last {mend - starts[-1]:.2f} s")
ends = starts[1:] + [mend]

# one subtitle per line of lines.txt, shown over every cut it overlaps
subs_line = []
for li, row in enumerate(times, 1):
    s = max(row[0][0] - SUB_LEAD, 0.0)
    nxt = max(times[li][0][0] - SUB_LEAD, 0.0) if li < len(times) else mend
    e = min(row[-1][1] + SUB_HOLD, nxt - 0.02 if li < len(times) else nxt)
    if e - s < SUB_MIN:
        e = min(s + SUB_MIN, nxt)
        if e - s < SUB_MIN - 1e-6:
            fail(f"line {li} has only {e - s:.2f} s on screen, under the {SUB_MIN} s minimum")
    subs_line.append((s, e, glue(lines[li - 1], phrases[li - 1])))

segs, cuts = [], []
for n, (c, s, e) in enumerate(zip(CUTS, starts, ends), 1):
    frames = round((e - s) * FPS)
    dur = round(frames / FPS - 1e-5, 6)  # ilag_cut ceils to frames with a 1e-6 tolerance: 25/24 written as 1.041667 became 26 frames
    span = frames / FPS
    subs = []
    for (sa, sb, text) in subs_line:
        lo, hi = max(sa, s), min(sb, s + span)
        if hi - lo > 0.05:
            subs.append({"at": math.floor((lo - s) * 1000) / 1000,
                         "dur": math.floor((hi - lo) * 1000 - 2) / 1000, "text": text})  # stays inside the segment
    segs.append({"id": f"h{n:02d}", "kind": "clip", "src": "src/ep5-ep1.mp4", "in": c[1], "dur": dur, "gain": 0.12,
                 "note": f"{c[2]}: {c[3]}", "subs": subs, "sfx": [{"name": "thud", "at": 0.0, "gain": 0.3}]})
    cuts.append({"cut": n, "from": round(s, 3), "to": round(e, 3), "len": round(e - s, 3), "src": c[1], "shot": c[2],
                 "what": c[3], "subs": [x["text"].replace(WJ, "") for x in subs]})
segs.append({"id": "title", "kind": "title", "src": "src/ep5-ep1.mp4", "in": 8.0, "dur": TITLE_S, "gain": 0.12,
             "texts": {"season": "ขายชื่อ", "ep": "EP.1", "title": "สามพันแลกชื่อ", "tagline": "คุ้มจริงเหรอ?"}})
segs.append({"id": "rew", "kind": "clip", "src": "src/ep5-ep1.mp4", "in": 4.2, "dur": REW_S, "gain": 0.3,
             "cards": [{"el": "rewcard", "at": 0.0, "dur": REW_S, "texts": {"tct": "ย้อนกลับไปเมื่อเช้านี้"}}],
             "sfx": [{"name": "whoosh", "at": 0.0, "gain": 0.5}]})
total = mend + TITLE_S + REW_S
edl = {"fps": FPS, "size": [1080, 1920], "sfx": "work/sfx", "output": "hook-rehearsal-master.mp4", "loudnorm": -16,
       "note": "ILAG 15 s Chinese-style hook demo, one-file narration, task-ee1dbcf0", "segments": segs}
(W / "edl.json").write_text(json.dumps(edl, ensure_ascii=False, indent=1), encoding="utf-8")
(W / "timing.json").write_text(json.dumps({
    "audio": Path(a.audio).name, "audio_s": round(audio_len, 3), "voice_end_s": round(last_end, 3),
    "montage_end_s": mend, "title_s": [mend, mend + TITLE_S], "rewcard_s": [mend + TITLE_S, total], "total_s": total,
    "phrase": {f"{i}.{j}": {"start": round(T(i, j)[0], 3), "end": round(T(i, j)[1], 3), "text": phrases[i - 1][j - 1]}
               for i, j in order},
    "subs": [{"line": k, "from": round(s, 3), "to": round(e, 3), "text": t.replace(WJ, "")} for k, (s, e, t) in enumerate(subs_line, 1)],
    "cuts": cuts}, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"voice ends {last_end:.2f} s (file {audio_len:.2f} s), montage {mend:.2f} s, total {total:.2f} s, {len(CUTS)} cuts, "
      f"lengths {[round(e - s, 2) for s, e in zip(starts, ends)]}")
