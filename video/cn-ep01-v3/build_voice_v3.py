"""EP01 v3 voice + music builder: lays the narrator inserts into the existing voice chains.
TH = voice/arcN chain (concat -> silenceremove 0.35 -> atempo 1.15 + loudnorm -16, 44.1k).
EN = voice/enN chain B (per chunk AF -> concat -> loudnorm -16, 48k; rebuild_en_b.py).
Every insert goes into a pause: the chunk is cut inside its silence, the take is trimmed and loudness-matched to its chunk,
and the pieces are rejoined with short fixed pauses. Everything after the insert moves later by the insert's length.
Usage: build_voice_v3.py <th1|th3|en1|en3> <check|build> [--takes th_title=1,th_punch=1,...]
  check = rebuild WITHOUT inserts and compare with the shipped v2 voice (proves the method), build = with inserts.
Writes voice/v3/<key>/<key>_voice.wav, sections_v3.json, music wav; numbers go to <key>/timing.json."""
import json, os, re, subprocess, sys, shutil
W = "/opt/MoonieXHQ/Work/cn-series"; V = f"{W}/voice"; V3 = f"{V}/v3"; PY = "/opt/MoonieXHQ/Agents/Core/.venv/bin/python"
key, mode = sys.argv[1], sys.argv[2]
takes = dict(kv.split("=") for kv in sys.argv[4].split(",")) if len(sys.argv) > 4 and sys.argv[3] == "--takes" else {}
LANG, N = key[:2], key[2]
FF = ["ffmpeg", "-nostdin", "-v", "error", "-y"]
TRIM = "silenceremove=stop_periods=-1:stop_duration=0.35:stop_threshold=-40dB"
AF_EN = "silenceremove=stop_periods=-1:stop_duration=0.8:stop_threshold=-45dB:stop_silence=0.55,atempo=1.04,aresample=48000"
# (chunk, silence interval seen in the raw chunk mp3, insert id, pause kept each side of the take in s, extra pad L/R in s)
# silence intervals: silencedetect -35dB on the raw chunk; word times confirmed with faster-whisper small
SPEC = {
    "th1": [("c05", (24.52, 25.16), "punch", 0.30, 0.06, 0.06)],  # title left out: 4.27 s trimmed, 3.4 s even at atempo 1.1 (brief: <= 3 s)
    "th3": [("c06", (65.35, 66.02), "reveal", 0.30, 0.08, 0.10)],
    "en1": [("c13", (23.65, 24.28), "punch", 0.20, 0.06, 0.06)],  # title left out: 4.48 s trimmed, 4.1 s at atempo 1.1
    "en3": [("c08", (7.70, 8.41), "reveal", 0.30, 0.08, 0.10)],
}[key]
SRC = f"{V}/arc{N}" if LANG == "th" else f"{V}/en{N}"
OUT = f"{V3}/{key}"; TMP = f"{OUT}/tmp"; os.makedirs(TMP, exist_ok=True)
SR = 44100 if LANG == "th" else 48000
def run(c): subprocess.run(c, check=True)
def dur(f): return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]))
def lufs(f):
    o = subprocess.run(["ffmpeg", "-nostdin", "-i", f, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", o)[-1])
def wav(src, dst, af=None, t=None, ss=None):
    c = FF + (["-ss", f"{ss:.3f}"] if ss is not None else []) + ["-i", src] + (["-t", f"{t:.3f}"] if t is not None else [])
    run(c + (["-af", af] if af else []) + ["-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", dst])
def silence(sec, dst): run(FF + ["-f", "lavfi", "-i", f"anullsrc=r={SR}:cl=mono", "-t", f"{sec:.3f}", "-c:a", "pcm_s16le", dst])
chunks = [l.split("'")[1][:-4] for l in open(f"{SRC}/list.txt")] if LANG == "th" else \
         sorted(re.findall(r"c\d\d", " ".join(os.listdir(SRC))), key=lambda x: x)
chunks = sorted(set(chunks))
def chunk_wav(c):  # one decoded chunk, with the language's per-chunk filter applied for EN
    d = f"{TMP}/{c}.wav"
    if not os.path.exists(d): wav(f"{SRC}/{c}.mp3", d, AF_EN if LANG == "en" else None)
    return d
def prep_take(iid, ref_lufs):
    t = takes[f"{LANG}_{iid}"]; src = f"{V3}/takes/{LANG}_{iid}_t{t}.mp3"; d = f"{TMP}/ins_{iid}.wav"
    edge = "silenceremove=start_periods=1:start_silence=0.03:start_threshold=-42dB"
    wav(src, f"{TMP}/ins_raw_{iid}.wav", f"{edge},areverse,{edge},areverse" + (f",{AF_EN.split(',', 1)[1]}" if LANG == "en" else ""))
    g = max(-8.0, min(8.0, ref_lufs - lufs(f"{TMP}/ins_raw_{iid}.wav")))
    wav(f"{TMP}/ins_raw_{iid}.wav", d, f"volume={g:.2f}dB")
    return d, g
def build(inserts):
    """inserts: ids to include. Returns (parts list, per-insert info, index in parts where each insert's take starts)."""
    parts, info, pos = [], {}, {}
    for c in chunks:
        sp = [s for s in SPEC if s[0] == c]
        if not sp: parts.append(chunk_wav(c)); continue
        _, sil, iid, kl, pl, pr = sp[0]
        if iid not in inserts: parts.append(chunk_wav(c)); continue
        ref = lufs(f"{SRC}/{c}.mp3"); ins, g = prep_take(iid, ref)
        if sil == "after":
            parts.append(chunk_wav(c))
        else:
            a, b = f"{TMP}/{c}_A.wav", f"{TMP}/{c}_B.wav"
            wav(f"{SRC}/{c}.mp3", a, AF_EN if LANG == "en" else None, t=sil[0] + kl)
            wav(f"{SRC}/{c}.mp3", b, AF_EN if LANG == "en" else None, ss=sil[1] - kl)
            parts.append(a)
        sl, sr_ = f"{TMP}/padL_{iid}.wav", f"{TMP}/padR_{iid}.wav"; silence(pl, sl); silence(pr, sr_)
        pos[iid] = len(parts); parts += [sl, ins, sr_]
        info[iid] = {"gain_db": round(g, 2), "take_s": round(dur(ins), 3), "pad_l": pl, "pad_r": pr}
        if sil != "after": parts.append(b)
    return parts, info, pos
def render(parts, name):
    lst = f"{TMP}/{name}.list"; open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    cat = f"{TMP}/{name}_cat.wav"; run(FF + ["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", cat])
    out = f"{TMP}/{name}_voice.wav"
    if LANG == "th":
        run(FF + ["-i", cat, "-af", TRIM, "-ar", "44100", f"{TMP}/{name}_trim.wav"])
        run(FF + ["-i", f"{TMP}/{name}_trim.wav", "-af", "atempo=1.15,loudnorm=I=-16:TP=-1.5", "-ar", "44100", out]); os.remove(f"{TMP}/{name}_trim.wav")
    else:
        run(FF + ["-i", cat, "-af", "loudnorm=I=-16:TP=-1.5", "-ar", "48000", out])
    os.remove(cat); return out
ids = [s[2] for s in SPEC]
res = {"key": key, "takes": takes}
md = lambda f: subprocess.run(f"ffmpeg -nostdin -v error -i {f} -f s16le - | md5sum", shell=True, capture_output=True, text=True).stdout.split()[0]
old_wav = f"{SRC}/arc{N}_voice.wav" if LANG == "th" else f"{SRC}/en{N}_voice.wav"
D0f = render(build([])[0], "v2"); D0 = dur(D0f)
if mode == "check":
    print("rebuilt", dur(D0f), "shipped", dur(old_wav), "pcm md5 same:", md(D0f) == md(old_wav)); shutil.rmtree(TMP); sys.exit()
d_of, t_old, t_new_start, prev_ids, prevD = {}, {}, {}, [], D0
for iid in ids:
    parts, info, pos = build(prev_ids + [iid]); D = dur(render(parts, "x"))
    d_of[iid] = D - prevD; prevD = D
    t_new_start[iid] = dur(render(parts[: pos[iid] + 1], "pre"))  # end of the left pad = where the take starts
    prev_ids.append(iid)
for iid in ids:  # old-timeline position of each insert: the shipped-chain voice up to the cut point of its chunk
    sp = [x for x in SPEC if x[2] == iid][0]; pre = []
    for cc in chunks:
        if cc == sp[0] and sp[1] != "after":
            a = f"{TMP}/{cc}_A0.wav"; wav(f"{SRC}/{cc}.mp3", a, AF_EN if LANG == "en" else None, t=sp[1][0] + sp[3]); pre.append(a); break
        pre.append(chunk_wav(cc))
        if cc == sp[0]: break
    t_old[iid] = dur(render(pre, "pre0"))
parts, info_all, pos = build(ids); final = render(parts, "final"); shutil.copy(final, f"{OUT}/{key}_voice.wav"); Dn = dur(final)
if LANG == "th":
    j = json.load(open(f"{SRC}/sections.json")); sec_old, end_old = [x["start"] for x in j["sections"]], j["duration"]
else:
    j = json.load(open(f"{SRC}/sections.json")); sec_old, end_old = j["sec"], j["end"]
sec_new = [round(x + sum(d_of[i] for i in ids if x >= t_old[i] - 0.05), 2) for x in sec_old]
end_new = round(end_old + sum(d_of.values()), 2)
res.update({"D_old_rebuilt": round(D0, 3), "D_old_shipped": round(end_old, 3), "D_new": round(Dn, 3), "d": {k: round(v, 3) for k, v in d_of.items()},
            "t_old": {k: round(v, 2) for k, v in t_old.items()}, "t_new_start": {k: round(v, 2) for k, v in t_new_start.items()},
            "insert": info_all, "sec_old": sec_old, "sec_new": sec_new, "end_new": end_new})
json.dump(res, open(f"{OUT}/timing.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: res[k] for k in ("D_old_rebuilt", "D_old_shipped", "D_new", "d", "t_old", "t_new_start", "insert")}, ensure_ascii=False))
shutil.rmtree(TMP)
