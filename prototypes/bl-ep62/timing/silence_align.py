#!/usr/bin/env python3
"""EP62 line timings from the voice's own pauses ($0, no ASR): ffmpeg silencedetect gives the pauses, a DP picks the 25
boundaries between the 26 SCRIPT.tsv lines so that every line's duration is closest to chars/rate (rate fitted on the whole).
whisper medium costs ~80 min on this box (EP61 REPORT); the TTS pauses between lines are 0.2-0.8 s and are all in the file.

    silence_align.py SCRIPT.tsv audio16k.wav out.tsv
"""
import re
import subprocess
import sys

script, wav, out = sys.argv[1:4]
lines = [l.split("\t") for l in open(script, encoding="utf-8").read().splitlines() if l.strip()]
chars = [len("".join(l[1].split())) for l in lines]
err = subprocess.run(["ffmpeg", "-hide_banner", "-i", wav, "-af", "silencedetect=noise=-38dB:d=0.18", "-f", "null", "-"],
                     capture_output=True, text=True, stdin=subprocess.DEVNULL).stderr
starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
dur = float(re.search(r"time=(\d+):(\d+):([\d.]+)", err.split("silence")[-1] + err[-300:]).group(3)) if False else None
sil = list(zip(starts, ends))
# speech begins after the first silence if it starts at 0; ends at the last silence_start
speech_t0 = sil[0][1] if sil and sil[0][0] < 0.05 else 0.0
speech_t1 = sil[-1][0]
inner = [s for s in sil if s[0] > speech_t0 + 0.2 and s[1] < speech_t1 - 0.2]
N, K = len(lines), len(inner)
speech_total = speech_t1 - speech_t0 - 0.0
# rate = chars per second of speech excluding the 25 inter-line pauses (about 0.35 s each)
rate = sum(chars) / (speech_total - 0.35 * (N - 1))
print(f"chars {sum(chars)} speech {speech_t0:.2f}-{speech_t1:.2f} rate {rate:.2f} ch/s, {K} candidate pauses")
INF = 1e9
# state: best[i][k] = min cost with line i ending at the pause k (line i = between pause j and pause k)
bounds = [(speech_t0, speech_t0)] + inner + [(speech_t1, speech_t1)]   # (silence_start, silence_end)
M = len(bounds)
best = [[INF] * M for _ in range(N + 1)]
back = [[-1] * M for _ in range(N + 1)]
best[0][0] = 0.0
for i in range(1, N + 1):
    for k in range(1, M):
        if i == N and k != M - 1:
            continue
        for j in range(0, k):
            if best[i - 1][j] >= INF:
                continue
            d = bounds[k][0] - bounds[j][1]
            exp = chars[i - 1] / rate
            c = best[i - 1][j] + (d - exp) ** 2 / max(exp, 0.5)
            if c < best[i][k]:
                best[i][k], back[i][k] = c, j
k, path = M - 1, []
for i in range(N, 0, -1):
    j = back[i][k]
    path.append((bounds[j][1], bounds[k][0]))
    k = j
path.reverse()
with open(out, "w") as f:
    f.write("tag\tt0\tt1\n")
    for (a, b), l, c in zip(path, lines, chars):
        f.write(f"{l[0]}\t{a:.2f}\t{b:.2f}\n")
        print(f"{l[0]:12s} {a:6.2f} {b:6.2f} {b-a:5.2f}s {c:3d}ch {c/(b-a):5.1f} ch/s  {l[1][:36]}")
