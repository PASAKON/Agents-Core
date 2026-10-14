#!/usr/bin/env python3
"""EP58 timings.tsv builder (task-ee30ba95): SCRIPT.tsv + ASR words + audio energy -> tag,t0,t1.

Contabo has no mlx-whisper (what EP57's timings used, large-v3-turbo on the Mac), so the ASR here is
faster-whisper `medium` run by transcribe.py (word_timestamps). Whisper misspells Thai, so the ASR
text is only used to find WHICH words belong to which script line (Needleman-Wunsch on a
tone-mark-stripped character string); the line edges are then snapped to the audio's own silences.

    align_timings.py SCRIPT.tsv asr.json audio.mp3 timings.tsv [--report report.txt]
"""
import argparse, json, re, subprocess, sys
import numpy as np

STRIP = re.compile(r"[\s่-์็ๆํ.,!?\"'()\-:;…]+")   # spaces, tone marks, ็ ์ ๆ, punctuation


def norm(s):
    return STRIP.sub("", s).lower()


def nw(a, b, match=3, mism=-1, gap=-2):
    """Global alignment of strings a, b -> list of (i or None, j or None)."""
    n, m = len(a), len(b)
    S = np.zeros((n + 1, m + 1), dtype=np.int32)
    S[:, 0] = np.arange(n + 1) * gap
    S[0, :] = np.arange(m + 1) * gap
    for i in range(1, n + 1):
        ai = a[i - 1]
        row, prev = S[i], S[i - 1]
        for j in range(1, m + 1):
            row[j] = max(prev[j - 1] + (match if ai == b[j - 1] else mism), prev[j] + gap, row[j - 1] + gap)
    i, j, out = n, m, []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and S[i, j] == S[i - 1, j - 1] + (match if a[i - 1] == b[j - 1] else mism):
            out.append((i - 1, j - 1)); i -= 1; j -= 1
        elif i > 0 and S[i, j] == S[i - 1, j] + gap:
            out.append((i - 1, None)); i -= 1
        else:
            out.append((None, j - 1)); j -= 1
    return out[::-1]


def energy_db(audio, hop=0.01):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", audio, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    h = int(16000 * hop)
    n = len(x) // h
    rms = np.sqrt((x[: n * h].reshape(n, h) ** 2).mean(axis=1) + 1e-12)
    return 20 * np.log10(rms), len(x) / 16000.0


def otsu_db(db):
    """Threshold between the noise-floor hump and the speech hump of the 10 ms dB histogram."""
    h, edges = np.histogram(db, bins=np.arange(-100, 0, 1.0))
    h = h.astype(float); p = h / h.sum(); w = np.cumsum(p); mu = np.cumsum(p * edges[:-1]); mt = mu[-1]
    var = (mt * w - mu) ** 2 / (w * (1 - w) + 1e-12)
    return float(edges[int(np.argmax(var))])


def runs(mask, val):
    out, i = [], 0
    while i < len(mask):
        if mask[i] == val:
            j = i
            while j < len(mask) and mask[j] == val:
                j += 1
            out.append((i, j)); i = j
        else:
            i += 1
    return out


def silences(db, thr, hop=0.01, min_len=0.10, blip=0.06):
    """Silent stretches >= min_len. Speech runs shorter than `blip` seconds (clicks, breaths) count as silence."""
    speech = db >= thr
    for i, j in runs(speech, True):
        if (j - i) * hop < blip:
            speech[i:j] = False
    return [(i * hop, j * hop) for i, j in runs(speech, False) if (j - i) * hop >= min_len]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script"); ap.add_argument("asr"); ap.add_argument("audio"); ap.add_argument("out")
    ap.add_argument("--report")
    a = ap.parse_args()

    lines = [l.rstrip("\n").split("\t") for l in open(a.script, encoding="utf-8") if l.strip()]
    tags = [l[0] for l in lines]
    s_chars, s_line = [], []
    for k, l in enumerate(lines):
        for ch in norm(l[1]):
            s_chars.append(ch); s_line.append(k)
    words = [w for seg in json.load(open(a.asr, encoding="utf-8"))["segments"] for w in seg["words"]]
    a_chars, a_time, a_word = [], [], []          # per ASR char: (start, end) of its word share
    for wi, w in enumerate(words):
        cs = norm(w["w"])
        for ci, ch in enumerate(cs):
            d = (w["end"] - w["start"]) / max(len(cs), 1)
            a_chars.append(ch); a_time.append((w["start"] + ci * d, w["start"] + (ci + 1) * d)); a_word.append(wi)

    path = nw("".join(s_chars), "".join(a_chars))
    a_line = [None] * len(a_chars)
    for si, aj in path:
        if si is not None and aj is not None:
            a_line[aj] = s_line[si]
    last = None
    for j in range(len(a_line)):                  # insertions: inherit the previous aligned char's line
        if a_line[j] is None:
            a_line[j] = last
        else:
            last = a_line[j]
    nxt = None
    for j in range(len(a_line) - 1, -1, -1):      # leading insertions: inherit the next one
        if a_line[j] is None:
            a_line[j] = nxt
        else:
            nxt = a_line[j]

    # a word belongs to the line most of its characters aligned to; a 1-2 letter Latin word with no exact match
    # (the stray "x" of "Forex"; digits are NOT noise: "1." is หนึ่ง) is noise and joins the word before it, or it would drag the next line's onset early
    w_line = []
    for wi in range(len(words)):
        cnt = {}
        for j in range(len(a_chars)):
            if a_word[j] == wi and a_line[j] is not None:
                cnt[a_line[j]] = cnt.get(a_line[j], 0) + 1
        w_line.append(max(sorted(cnt), key=lambda k: cnt[k]) if cnt else None)
    matched = {}
    for si, aj in path:
        if si is not None and aj is not None and s_chars[si] == a_chars[aj]:
            matched[a_word[aj]] = matched.get(a_word[aj], 0) + 1
    word_len = {}
    for wi in a_word:
        word_len[wi] = word_len.get(wi, 0) + 1
    for wi in range(len(words)):
        if word_len.get(wi, 0) < 3 and not matched.get(wi) and wi > 0 and re.fullmatch(r"[a-z]+", norm(words[wi]["w"])):
            w_line[wi] = w_line[wi - 1]
    rough = []
    for k in range(len(lines)):
        ws = [words[wi] for wi in range(len(words)) if w_line[wi] == k]
        if not ws:
            sys.exit(f"line {tags[k]} got no ASR words -- the alignment lost it; do not guess")
        rough.append([min(w["start"] for w in ws), max(w["end"] for w in ws)])

    db, total = energy_db(a.audio)
    thr = otsu_db(db)
    sil = silences(db, thr)

    t0 = [r[0] for r in rough]; t1 = [r[1] for r in rough]
    kind = []
    prev_end = 0.0
    for k in range(len(lines) - 1):
        # whisper word STARTS are good, word ENDS stretch into the pause: so the next line's onset (w) is the anchor
        # and the pause that ends nearest to it is the gap between the two lines
        w = rough[k + 1][0]
        cand = [(abs(e - w) - 0.5 * (e - s_), s_, e) for s_, e in sil if w - 0.6 <= e <= w + 0.35 and s_ >= prev_end - 1e-6]
        if cand:
            _, s_, e = min(cand)
            t1[k], t0[k + 1] = s_, e; prev_end = e; kind.append("pause")
        else:                                      # contiguous lines: split at the quietest 10 ms near the ASR onset
            lo, hi = int((w - 0.25) / 0.01), int((w + 0.25) / 0.01)
            m = lo + int(np.argmin(db[lo:hi])); t1[k] = t0[k + 1] = m * 0.01; prev_end = m * 0.01; kind.append("contiguous")
    for edge, idx in ((0, 0), (1, len(lines) - 1)):  # first onset / last offset: nearest speech edge to the ASR guess
        g = rough[idx][edge]
        lo, hi = max(0, int((g - 0.5) / 0.01)), min(len(db), int((g + 0.5) / 0.01))
        loud = [i for i in range(lo, hi) if db[i] >= thr]
        if loud:
            (t0 if edge == 0 else t1)[idx] = (loud[0] if edge == 0 else loud[-1] + 1) * 0.01
    t1[-1] = min(t1[-1], total)

    rep = []
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("tag\tt0\tt1\n")
        for k in range(len(lines)):
            f.write(f"{tags[k]}\t{t0[k]:.2f}\t{t1[k]:.2f}\n")
            heard = "".join(words[wi]["w"] for wi in range(len(words)) if w_line[wi] == k)
            i0, i1 = int(t0[k] / 0.01), int(t1[k] / 0.01)
            speech = float((db[i0:i1] >= thr).mean()) if i1 > i0 else 0.0
            flag = " CHECK" if abs(t0[k] - rough[k][0]) > 0.35 else ""
            rep.append(f"{tags[k]:12s} {t0[k]:6.2f}-{t1[k]:6.2f} ({t1[k]-t0[k]:4.2f}s) asr_t0={rough[k][0]:6.2f}{flag} speech={speech:4.2f} "
                       f"{kind[k-1] if k else 'start':10s} script={lines[k][1]} | heard={heard.strip()}")
    rep.append(f"speech threshold {thr:.1f} dB (Otsu on the 10 ms dB histogram); audio decoded length {total:.4f}s")
    text = "\n".join(rep)
    print(text)
    if a.report:
        open(a.report, "w", encoding="utf-8").write(text + "\n")


if __name__ == "__main__":
    main()
