#!/usr/bin/env python3
"""Shared edit helpers for The Old Telling EP1 builders (ACT 1 to 6). Written 2026-10-11 after the CEO watched the first full Thai cut:

  1. "the sound jerks: you did not measure the sound, you cut by time"   -> narration windows are cut at the MEASURED quietest point between sentences,
     never overlap, carry a 12 ms fade each side; shot beds are level-matched and joined by a 0.12 s equal-power crossfade, never a hard concat.
  2. "the picture stalls on the last frame before the next shot"        -> a shot is lengthened with its own real frames (settle), a sentence that is still
     too long runs into the next shot (L-cut, the next sentence waits); a frozen last frame is allowed only on the last shot of an ACT, under the closing fade.

Everything here is numeric and offline (numpy + ffmpeg), no paid call. Every build writes the same audit numbers the CEO was shown, old method next to new.
"""
import json, math, pathlib, re, subprocess
import numpy as np

SR, FPS = 48000, 24
FADE_N = 0.012     # fade at each edge of a narration window (s)
FADE_L = 0.020     # fade at each edge of a character line (s)
XF = 0.12          # bed crossfade (s), equal power (qsin both sides), runs from the cut forward so every shot keeps its own timing
GAIN_MAX = 12.0    # beds are level-matched to the median shot: quiet ones lifted by at most this (dB)
GAIN_DOWN = 20.0   # loud ones lowered by at most this (dB); a loud H3 clip beside a quiet one is the jerk the CEO heard
SPEECH_DB = -30.0  # a cut that lands above this, relative to the speech level, is inside speech


def run(cmd):
    subprocess.run([str(c) for c in cmd], check=True)


def load_mono(path, sr=SR):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def db(v):
    return 20 * math.log10(max(float(v), 1e-9))


def probe_dur(path, stream="a:0"):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", stream, "-show_entries", "stream=duration", "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout.split()
    return float(out[0]) if out and out[0] not in ("N/A", "") else 0.0


# ---------------------------------------------------------------- picture: extend, then spill, then (last shot only) hold

def settle(seg, t, last_end, n_full, tail, noext=False, is_last=False, hold_max=1.0):
    """seg: dict(a, n, hold) in frames; t: shot start (s); last_end: when its narration ends (s, absolute).
    Lengthen the shot with real frames of its own clip while the narration needs it; only the last shot of an ACT may freeze its last frame (under the closing fade).
    Returns (shot end, spill): spill > 0 means the narration runs that many seconds into the next shot (an L-cut, the next sentence waits for it)."""
    seg_end = t + seg["n"] / FPS
    need = last_end + tail - seg_end
    if need > 0 and not noext:
        add = min(n_full - seg["a"] - seg["n"], math.ceil(need * FPS))
        if add > 0:
            seg["n"] += add; seg_end += add / FPS; need -= add / FPS
    if need > 0 and is_last:
        seg["hold"] = min(hold_max, math.ceil(need * FPS) / FPS); seg_end += seg["hold"]
    return seg_end, max(0.0, last_end - seg_end)


# ---------------------------------------------------------------- narration: cut where it is quiet

class Narr:
    def __init__(self, path):
        self.x = load_mono(path)
        self.c = np.concatenate([[0.0], np.cumsum(self.x.astype(np.float64) ** 2)])
        h = int(0.02 * SR); n = len(self.x) // h
        fr = np.sqrt((self.x[:n * h].reshape(n, h) ** 2).mean(1))
        self.speech = float(np.median(fr[fr > 0.1 * fr.max()]))
        self.dur = len(self.x) / SR

    def _rms(self, i, w):
        i = max(0, min(i, len(self.x) - w))
        return math.sqrt(max(self.c[i + w] - self.c[i], 0.0) / w)

    def level(self, t, width=0.008):
        """level of the 8 ms around t, dB relative to the speech level of this take"""
        w = int(width * SR)
        return db(self._rms(int(t * SR) - w // 2, w) / self.speech)

    def _snap(self, c, reach=0.0025):
        r = int(reach * SR); lo = max(1, c - r); hi = min(len(self.x) - 1, c + r)
        sg = np.sign(self.x[lo - 1:hi + 1]); cross = np.nonzero(sg[1:] * sg[:-1] < 0)[0]
        return int(lo + cross[np.argmin(np.abs(lo + cross - c))]) if len(cross) else c

    def quietest(self, t0, t1, width=0.008):
        """middle of the quietest stretch in [t0, t1], snapped to a zero crossing (seconds)"""
        w = int(width * SR); n = len(self.x)
        i0 = int(max(0.0, t0) * SR); i1 = int(min(t1 * SR, n - w - 1))
        if i1 <= i0:
            return min(max(0.0, t0), self.dur - 0.01)
        idx = np.arange(i0, i1, 48)
        r = np.sqrt(np.maximum(self.c[idx + w] - self.c[idx], 0.0) / w)
        k = int(np.argmin(r)); lim = max(r[k] * 1.41, 1e-5); a = b = k
        while a > 0 and r[a - 1] <= lim:
            a -= 1
        while b < len(r) - 1 and r[b + 1] <= lim:
            b += 1
        return self._snap(int(idx[(a + b) // 2] + w // 2)) / SR

    def windows(self, items):
        """items: [(sid, start, end)] from the provider timestamps. -> {sid: [a0, a1]} cut at measured minima; neighbours share one cut, never overlap"""
        its = sorted(items, key=lambda r: r[1]); res = {}
        for k, (sid, s, e) in enumerate(its):
            prev_e = its[k - 1][2] if k else 0.0
            next_s = its[k + 1][1] if k + 1 < len(its) else self.dur
            a0 = self.quietest(max(prev_e - 0.06, s - 0.30, 0.0), s + 0.03)
            a1 = self.quietest(e - 0.03, min(next_s + 0.06, e + 0.35, self.dur))
            res[sid] = [min(a0, s), max(a1, e)]
        for k in range(len(its) - 1):
            a, b = its[k][0], its[k + 1][0]
            if res[a][1] > res[b][0]:
                cut = self.quietest(res[b][0] - 0.02, res[a][1] + 0.02)
                res[a][1] = res[b][0] = cut
        return res


def narr_filters(idx, narr, items, places, fade=FADE_N):
    """items: [(sid, start, end)] of the placed sentences, places: {sid: output time of the first spoken sound}. -> (filters, labels, windows, out_spans)"""
    wins = narr.windows(items); src = {sid: (s, e) for sid, s, e in items}
    order = sorted(places, key=lambda x: places[x]); spans, prev = {}, None
    for sid in order:
        s, e = src[sid]; a0, a1 = wins[sid]
        delay = places[sid] - (s - a0)
        if delay < 0:                       # the window would start before the ACT does: drop its leading quiet part
            a0 -= delay; delay = 0.0
        if prev is not None and delay < spans[prev][1]:   # the pause between the two was compressed: trim the quiet tail of the earlier window, never its speech
            pa0, pa1 = wins[prev]; pa1 = max(pa1 - (spans[prev][1] - delay), src[prev][1])
            wins[prev] = [pa0, pa1]; spans[prev] = (spans[prev][0], spans[prev][0] + pa1 - pa0)
        wins[sid] = [a0, a1]; spans[sid] = (delay, delay + a1 - a0); prev = sid
    fc, labels = [], []
    for sid in order:
        a0, a1 = wins[sid]; dur = a1 - a0; ms = int(round(spans[sid][0] * 1000)); lab = "n" + re.sub(r"\W", "_", sid)
        fc.append(f"[{idx}:a]atrim=start={a0:.5f}:end={a1:.5f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
                  f"afade=t=in:st=0:d={fade},afade=t=out:st={dur - fade:.5f}:d={fade},adelay={ms}|{ms}[{lab}]")
        labels.append(f"[{lab}]")
    return fc, labels, wins, spans


def line_filters(lines, idx_of, base="ln"):
    """character lines: dict(path, a0, a1, at) cut by envelope (voice_span), or a0=None: whole take, leading silence removed (ACT 1)"""
    fc, labels = [], []
    for k, ln in enumerate(lines):
        i = idx_of[str(ln["path"])]; ms = int(round(ln["at"] * 1000))
        if ln.get("a0") is None:
            fc.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,silenceremove=start_periods=1:start_threshold=-45dB,adelay={ms}|{ms}[{base}{k}]")
        else:
            dur = ln["a1"] - ln["a0"]
            fc.append(f"[{i}:a]atrim=start={ln['a0']:.4f}:end={ln['a1']:.4f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
                      f"afade=t=in:st=0:d={FADE_L},afade=t=out:st={dur - FADE_L:.4f}:d={FADE_L},adelay={ms}|{ms}[{base}{k}]")
        labels.append(f"[{base}{k}]")
    return fc, labels


# ---------------------------------------------------------------- beds: level-match, crossfade

def _rms_of(v):
    v = v[~np.isnan(v)]
    return db(math.sqrt(float((v.astype(np.float64) ** 2).mean()))) if len(v) else None


def bed_plan(segs):
    """segs: dict(file, a, n frames, mute [(s,s)] shot-relative, silence).
    -> (mean level dB per shot (None = silent), gain dB for the shot mean gm, gain at its start gs, gain at its end ge, target dB).
    gm matches every shot to the median shot; gs/ge then pull the first and last second of each shot so the two sides of every cut meet at one level."""
    cache, levels, heads, tails = {}, [], [], []
    for s in segs:
        if s.get("silence"):
            levels.append(None); heads.append(None); tails.append(None); continue
        key = str(s["file"])
        if key not in cache:
            cache[key] = load_mono(s["file"], 16000)
        i0 = int(s["a"] / FPS * 16000); seg = cache[key][i0:i0 + int(s["n"] / FPS * 16000)].copy()
        for m0, m1 in s.get("mute", []):
            seg[int(m0 * 16000):int(m1 * 16000)] = np.nan
        levels.append(_rms_of(seg)); heads.append(_rms_of(seg[:int(0.4 * 16000)])); tails.append(_rms_of(seg[-int(0.4 * 16000):]))
    ok = lambda l: l is not None and l > -60
    real = [l for l in levels if ok(l)]
    target = float(np.median(real)) if real else -30.0
    gm = [0.0 if not ok(l) else float(np.clip(target - l, -GAIN_DOWN, GAIN_MAX)) for l in levels]
    gs, ge = list(gm), list(gm)
    for k in range(len(segs) - 1):
        if not (ok(tails[k]) and ok(heads[k + 1])):
            continue
        j = (tails[k] + gm[k] + heads[k + 1] + gm[k + 1]) / 2          # the level both sides of the cut should meet at
        ge[k] = float(np.clip(j - tails[k], -GAIN_DOWN, GAIN_MAX)); gs[k + 1] = float(np.clip(j - heads[k + 1], -GAIN_DOWN, GAIN_MAX))
    return levels, gm, gs, ge, target


def mute_filter(ranges, r=0.02):
    """smooth mute (20 ms ramps) of H3's own voicing; 64-sample frames so the ramp is not one hard step"""
    if not ranges:
        return ""
    terms = "*".join(f"(1-clip(min((t-{m0 - r:.3f})/{r},({m1 + r:.3f}-t)/{r}),0,1))" for m0, m1 in ranges)
    return f",volume='{terms}':eval=frame"


def _gain_filter(gm, gs, ge, D):
    """shot gain in dB: gm over the shot, gs->gm over its first second, gm->ge over its last second (linear in dB), evaluated every 128 samples"""
    if abs(gs - gm) < 0.05 and abs(ge - gm) < 0.05:
        return f",volume={gm:.3f}dB"
    R = max(0.05, min(1.0, D / 3))
    expr = f"pow(10,({gm:.3f}+({gs - gm:.3f})*max(0,1-t/{R:.3f})+({ge - gm:.3f})*min(1,max(0,(t-{D - R:.3f})/{R:.3f})))/20)"
    return f",volume='{expr}':eval=frame"


def bed_filters(segs, idx_of, gm, gs, ge, total):
    out, n = [], len(segs)
    for k, s in enumerate(segs):
        last = k == n - 1; D = s["n"] / FPS + s.get("hold", 0.0); tgt = D + (0.0 if last else XF)
        if s.get("silence"):
            out.append(f"aevalsrc=0:d={tgt:.4f}:s=48000:c=stereo,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[b{k}]"); continue
        i = idx_of[str(s["file"])]; a0 = s["a"] / FPS; end0 = a0 + s["n"] / FPS
        want = s.get("hold", 0.0) if last else XF
        post = max(0.0, min(want, s["audio_dur"] - end0 - 0.005))
        f = f"[{i}:a]atrim=start={a0:.4f}:end={end0 + post:.4f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,asetnsamples=n=128:p=0{mute_filter(s.get('mute', []))}{_gain_filter(gm[k], gs[k], ge[k], s['n'] / FPS + s.get('hold', 0.0))}"
        if post < want - 0.001:             # the clip's own sound ends here: close it with a 20 ms fade so the pad after it is not a click
            f += f",afade=t=out:st={s['n'] / FPS + post - 0.02:.4f}:d=0.02"
        out.append(f + f",apad=whole_dur={tgt:.4f},atrim=end={tgt:.4f},aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[b{k}]")
    cur = "[b0]"
    for k in range(1, n):
        out.append(f"{cur}[b{k}]acrossfade=d={XF}:c1=qsin:c2=qsin[x{k}]"); cur = f"[x{k}]"
    out.append(f"{cur}atrim=end={total:.4f},asetpts=PTS-STARTPTS,volume=4dB[ambient]")
    return out


# ---------------------------------------------------------------- the audio build: mix -> two-pass loudnorm -> aac

def build_audio(work, tag, segs, total, narr_path, items, places, lines, fade_in, fade_out):
    """segs: shots in order (dict file, a, n, hold, mute, silence); items [(sid, start, end)] of the narration take; places {sid: output time}; lines (see line_filters).
    Writes work/<tag>_bed.wav, <tag>_mix.wav, <tag>_audio.m4a. Returns dict(audio, bed, audit)."""
    work = pathlib.Path(work); work.mkdir(exist_ok=True, parents=True)
    inputs = []
    for s in segs:
        if not s.get("silence") and str(s["file"]) not in inputs:
            inputs.append(str(s["file"]))
    for p in [narr_path] + [ln["path"] for ln in lines]:
        if str(p) not in inputs:
            inputs.append(str(p))
    idx_of = {f: i for i, f in enumerate(inputs)}
    for s in segs:
        if not s.get("silence"):
            s["audio_dur"] = probe_dur(s["file"])
    narr = Narr(narr_path)
    levels, gains, gs, ge, target = bed_plan(segs)
    fc = bed_filters(segs, idx_of, gains, gs, ge, total)
    nf, nl, wins, spans = narr_filters(idx_of[str(narr_path)], narr, items, places)
    lf, ll = line_filters(lines, idx_of)
    fc += nf + lf
    parts = nl + ll
    fc.append("".join(parts) + f"amix=inputs={len(parts)}:normalize=0:duration=longest,apad=whole_dur={total:.3f}[bus]")
    fc.append("[bus]asplit=2[bus_sc][bus_mix]")
    fc.append("[ambient]asplit=2[amb_a][amb_b]")
    fc.append("[amb_a][bus_sc]sidechaincompress=threshold=0.02:ratio=6:attack=15:release=450:makeup=1[duck]")
    fc.append("[duck][bus_mix]amix=inputs=2:normalize=0:duration=first[mixout]")
    bed, mix, aac = work / f"{tag}_bed.wav", work / f"{tag}_mix.wav", work / f"{tag}_audio.m4a"
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for f in inputs:
        cmd += ["-i", f]
    cmd += ["-filter_complex", ";".join(fc), "-map", "[mixout]", "-t", f"{total:.3f}", "-c:a", "pcm_s24le", str(mix),
            "-map", "[amb_b]", "-t", f"{total:.3f}", "-c:a", "pcm_s24le", str(bed)]
    (work / f"{tag}_audio_cmd.txt").write_text(" ".join(str(c) for c in cmd), encoding="utf-8")
    run(cmd)
    # two-pass loudnorm in linear mode: one gain for the whole ACT, so no pumping at the cuts (the one-pass dynamic mode rides the gain)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(mix), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    j = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    ln_f = (f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:"
            f"offset={j['target_offset']}:linear=true,aresample=48000,afade=t=in:st=0:d={fade_in},afade=t=out:st={total - fade_out:.3f}:d={fade_out}")
    run(["ffmpeg", "-v", "error", "-y", "-i", mix, "-af", ln_f, "-c:a", "aac", "-b:a", "192k", "-ar", "48000", aac])
    e = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(aac), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    lufs = float(re.findall(r"I:\s+(-?[0-9.]+) LUFS", e)[-1]); peak = float(re.findall(r"Peak:\s+(-?[0-9.]+) dBFS", e)[-1])
    audit = audit_all(narr, items, wins, spans, segs, levels, gains, bed)
    audit.update(lufs=round(lufs, 1), true_peak_db=round(peak, 1), bed_target_db=round(target, 1), bed_gains_db=[round(g, 1) for g in gains], bed_gain_start_db=[round(g, 1) for g in gs], bed_gain_end_db=[round(g, 1) for g in ge])
    (work / f"{tag}_audit.json").write_text(json.dumps(audit, indent=1), encoding="utf-8")
    return dict(audio=aac, bed=bed, audit=audit)


# ---------------------------------------------------------------- the same numbers the CEO was shown, old method next to new

def _seg_raw(s, cache):
    """raw bed of one shot as the old method laid it: the clip's own sound, cut by frame, padded with digital silence over a hold"""
    D = int(round((s["n"] / FPS + s.get("hold", 0.0)) * 16000))
    if s.get("silence"):
        return np.zeros(D, dtype=np.float32)
    key = str(s["file"])
    if key not in cache:
        cache[key] = load_mono(s["file"], 16000)
    i0 = int(s["a"] / FPS * 16000); seg = cache[key][i0:i0 + int(s["n"] / FPS * 16000)]
    out = np.zeros(D, dtype=np.float32); out[:len(seg)] = seg[:D]
    return out


def _rms_db(x):
    return db(math.sqrt(float((x.astype(np.float64) ** 2).mean()))) if len(x) else -120.0


def _steps(bed16, cuts, lead, win=0.26):
    res = []
    for T in cuts:
        a = bed16[max(0, int((T - 0.30) * 16000)):int((T - 0.04) * 16000)]
        b = bed16[int((T + lead + 0.04) * 16000):int((T + lead + 0.04 + win) * 16000)]
        if len(a) > 1600 and len(b) > 1600:
            res.append(abs(_rms_db(a) - _rms_db(b)))
    return res


def audit_all(narr, items, wins, spans, segs, levels, gains, bed_wav):
    src = {sid: (s, e) for sid, s, e in items}; order = sorted(src, key=lambda x: src[x][0])
    new_edges = [narr.level(t) for sid in order for t in wins[sid]]
    old_win = {sid: (max(0.0, src[sid][0] - 0.03), src[sid][1] + 0.10) for sid in order}
    old_edges = [narr.level(t) for sid in order for t in old_win[sid]]
    old_over = sum(1 for a, b in zip(order, order[1:]) if old_win[a][1] > old_win[b][0] + 1e-6)
    new_over = sum(1 for a, b in zip(order, order[1:]) if spans[a][1] > spans[b][0] + 1e-6)
    cuts, t = [], 0.0
    for s in segs[:-1]:
        t += s["n"] / FPS + s.get("hold", 0.0); cuts.append(t)
    cache = {}
    raw = np.concatenate([_seg_raw(s, cache) for s in segs])
    old_steps = _steps(raw, cuts, 0.0)
    new16 = load_mono(bed_wav, 16000)
    new_steps = _steps(new16, cuts, XF)
    b48 = load_mono(bed_wav, SR); clicks = []
    for T in cuts:
        i = int(T * SR); w = b48[max(1, i - 150):i + 150]; ctx = b48[max(1, i - SR // 2):i + SR // 2]
        clicks.append(float(np.abs(np.diff(w)).max() / (np.abs(np.diff(ctx)).std() + 1e-9)))
    dig = sum(s.get("hold", 0.0) for s in segs)
    ok = [(l, g) for l, g in zip(levels, gains) if l is not None and l > -60]   # whole-shot mean levels, the first measure the CEO was shown
    lv_old = [abs(a[0] - b[0]) for a, b in zip(ok, ok[1:])]; lv_new = [abs((a[0] + a[1]) - (b[0] + b[1])) for a, b in zip(ok, ok[1:])]
    return dict(
        sentences=len(order),
        narr_edges_in_speech=dict(old=int(sum(1 for v in old_edges if v > SPEECH_DB)), new=int(sum(1 for v in new_edges if v > SPEECH_DB)), of=len(new_edges)),
        narr_edge_median_db=dict(old=round(float(np.median(old_edges)), 1), new=round(float(np.median(new_edges)), 1)),
        narr_window_overlaps=dict(old=old_over, new=new_over, of=max(0, len(order) - 1)),
        bed_steps_over_12db=dict(old=int(sum(1 for v in old_steps if v > 12)), new=int(sum(1 for v in new_steps if v > 12)), of=len(old_steps)),
        bed_steps_over_6db=dict(old=int(sum(1 for v in old_steps if v > 6)), new=int(sum(1 for v in new_steps if v > 6)), of=len(old_steps)),
        bed_step_median_db=dict(old=round(float(np.median(old_steps)), 1) if old_steps else 0, new=round(float(np.median(new_steps)), 1) if new_steps else 0),
        bed_step_max_db=dict(old=round(max(old_steps), 1) if old_steps else 0, new=round(max(new_steps), 1) if new_steps else 0),
        cut_click_ratio_max=round(max(clicks), 1) if clicks else 0,
        shot_level_steps_over_12db=dict(old=sum(1 for d in lv_old if d > 12), new=sum(1 for d in lv_new if d > 12), of=len(lv_old)),
        shot_level_step_median_db=dict(old=round(float(np.median(lv_old)), 1) if lv_old else 0, new=round(float(np.median(lv_new)), 1) if lv_new else 0),
        hold_seconds=round(dig, 2), shots=len(segs), shot_levels_db=[None if l is None else round(l, 1) for l in levels],
    )


def mux(video, audio, master, total):
    run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", audio, "-map", "0:v:0", "-map", "1:a:0", "-c", "copy", "-t", f"{total:.3f}", "-movflags", "+faststart", master])


def preview540(master, out):
    run(["ffmpeg", "-v", "error", "-y", "-i", master, "-vf", "scale=960:540:flags=lanczos", "-c:v", "libx264", "-preset", "medium", "-crf", "24",
         "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out])
