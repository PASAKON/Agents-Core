"""Rehearsal narrator for the ILAG hook demo (task-ee1dbcf0): ONE edge-tts call reading narration.txt, written as
  <out>.mp3   the whole narration
  <out>.json  its WordBoundary events as an ElevenLabs alignment:
              {"characters": [...], "character_start_times_seconds": [...], "character_end_times_seconds": [...]}
so the morning ElevenLabs v4 take is a one-file swap in the build:  --audio take.mp3 --align take.json.
No speed-up: rate is +0% unless --rate says otherwise (the CEO's rule is normal rate).

usage: tts_rehearsal.py <narration.txt> <out-base> [--voice th-TH-NiwatNeural] [--rate +0%]
Needs edge_tts (the khaohom-survival venv has it).  Characters the service sends no word for (spaces, punctuation)
get a zero-length slot between the neighbouring words, so the arrays stay exactly as long as the text.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

import edge_tts

ap = argparse.ArgumentParser()
ap.add_argument("narration")
ap.add_argument("out")
ap.add_argument("--voice", default="th-TH-NiwatNeural")
ap.add_argument("--rate", default="+0%")
a = ap.parse_args()

text = Path(a.narration).read_text(encoding="utf-8").strip()
mp3, js = Path(a.out + ".mp3"), Path(a.out + ".json")
words = []  # (text, start s, end s)


async def main():
    comm = edge_tts.Communicate(text, a.voice, rate=a.rate, boundary="WordBoundary")
    with open(mp3, "wb") as f:
        async for ch in comm.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                s = ch["offset"] / 1e7
                words.append((ch["text"], s, s + ch["duration"] / 1e7))


asyncio.run(main())
if not words:
    sys.exit("edge-tts sent no WordBoundary events")

n = len(text)
st, en = [None] * n, [None] * n
cur = 0
for w, s, e in words:
    i = text.find(w, cur)
    if i < 0:
        sys.exit(f"WordBoundary word {w!r} not found in the narration after offset {cur}")
    step = (e - s) / len(w)
    for k in range(len(w)):  # the word's time is shared evenly by its characters
        st[i + k], en[i + k] = s + k * step, s + (k + 1) * step
    cur = i + len(w)
# gap characters (spaces, punctuation): zero length, at the end of the word before them (0.0 before the first word)
last = 0.0
for i in range(n):
    if st[i] is None:
        st[i] = en[i] = last
    else:
        last = en[i]
js.write_text(json.dumps({"characters": list(text), "character_start_times_seconds": [round(x, 4) for x in st],
                          "character_end_times_seconds": [round(x, 4) for x in en]}, ensure_ascii=False), encoding="utf-8")
print(f"{a.voice} rate {a.rate}: {n} characters, {len(words)} words, last word ends {max(en):.2f} s -> {mp3.name}, {js.name}")
