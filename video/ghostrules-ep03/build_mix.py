#!/usr/bin/env python3
"""GhostRules EP3 M2b mix: voice takes + approved-pack cues + night bed + ONE jump scare.
usage: build_mix.py BED_FILE OUT_DIR      (BED_FILE = Flow ambience, or the rain fallback)
Run with /opt/MoonieXHQ/Agents/Core/.venv/bin/python -I (numpy only)."""
import sys, json, subprocess, math
import numpy as np
SR = 48000
IN = "/opt/MoonieXHQ/Work/task-af2d7f8f/in"; OLD = "/opt/MoonieXHQ/Work/task-af2d7f8f/out"
PACK = "/opt/MoonieXHQ/Work/ghost-pilot/sfx-horror-pack/"
BED, OUT = sys.argv[1], sys.argv[2]
BED_REL_DB = float(sys.argv[3]) if len(sys.argv) > 3 else -24.0   # bed RMS under voice RMS

def rd(path, sr=SR, ch=1):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", str(ch), "-ar", str(sr), "-"], capture_output=True, check=True)
    x = np.frombuffer(r.stdout, dtype=np.float32).copy()
    return x.reshape(-1, ch) if ch > 1 else x
def S(t): return int(round(t * SR))
def rms_db(x): return 20 * np.log10(np.sqrt((x.astype(np.float64) ** 2).mean()) + 1e-12)

tl = json.load(open(f"{OLD}/timeline.json")); led = json.load(open(f"{OLD}/cue_ledger.json"))
# ---- jump scare layout (take c06; cut in the real pause, speech ends ~12.78 s, resumes ~13.55 s)
c06 = next(t for t in tl["takes"] if t["take"] == "c06")
A_END, B_START = 12.85, 13.45               # cut points inside the silence of the take
BED_FADE = (12.0, 12.6)                     # bed fades out under the last words (take time)
CREAK_AFTER_A = 0.75                        # false cue ~1 s into the calm (bed gone at 12.6 -> creak at 13.6)
raw_sting = c06["start"] + A_END + 3.0
STING = round(raw_sting * 6) / 6            # on both the 24 and 30 fps grids
TAIL = 1.45
G = (STING + 1.5) - (c06["start"] + A_END)  # narration-free hole
SHIFT = G - (B_START - A_END)
CALM_START = c06["start"] + BED_FADE[1]
print("sting", STING, "G", G, "shift", SHIFT, "calm", STING - CALM_START)

# ---- new timeline
cut_at = c06["start"] + A_END
def mv(t): return t + SHIFT if t >= cut_at + 0.01 else t
new_takes = []
for t in tl["takes"]:
    n = dict(t)
    if t["take"] == "c06":
        n["voice_end"] = t["voice_end"] + SHIFT; n["next_boundary"] = t["next_boundary"] + SHIFT; n["duration"] = t["duration"] + SHIFT
    elif t["start"] > c06["start"]:
        for k in ("start", "voice_end", "next_boundary"): n[k] = t[k] + SHIFT
    new_takes.append(n)
new_cards = [dict(c, start=(c["start"] + SHIFT if c["start"] > cut_at else c["start"]), end=(c["end"] + SHIFT if c["start"] > cut_at else c["end"])) for c in tl["cards"]]
TOTAL = tl["duration"] + SHIFT
rain_iv = tl["rain_intervals"]
N = S(TOTAL)

# ---- voice
voice = np.zeros(N, np.float32)
for t in new_takes:
    x = rd(f"{IN}/takes/{t['take']}.wav")
    if t["take"] == "c06":
        a = x[:S(A_END)]; b = x[S(B_START):]
        o = S(t["start"]); voice[o:o + len(a)] += a
        o2 = o + len(a) + S(G); voice[o2:o2 + len(b)] += b
    else:
        o = S(t["start"]); voice[o:o + len(x)] += x
vrms_active = rms_db(voice[np.abs(voice) > 0.01])

# ---- bed loop (equal-power crossfade >= 2 s) + envelope
bed = rd(BED, ch=1)
XF = S(2.0)
def loop(x, n):
    out = np.zeros(n, np.float32); pos = 0; first = True
    fo = np.sin(np.linspace(0, np.pi / 2, XF)).astype(np.float32); fi = fo[::-1].copy()
    while pos < n:
        seg = x.copy()
        if first: out[pos:pos + len(seg)] += seg[:n - pos]; pos += len(seg) - XF; first = False; continue
        m = min(len(seg), n - pos)
        out[pos:pos + XF] = out[pos:pos + XF] * fi + seg[:XF] * fo   # overlap region
        out[pos + XF:pos + m] = seg[XF:m]; pos += len(seg) - XF
    return out
bedl = loop(bed, N)
env = np.ones(N, np.float32)
def ramp(a, b, up):    # cosine ramp over [a,b] s
    i0, i1 = S(a), S(b); r = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, i1 - i0)); return i0, i1, (r if up else 1 - r).astype(np.float32)
def setenv(a, b, up, lo=0.0):
    i0, i1, r = ramp(a, b, up); env[i0:i1] = np.minimum(env[i0:i1], r) if not up else env[i0:i1]
    return i0, i1
# start/end fades
i0, i1, r = ramp(0, 0.25, True); env[i0:i1] *= r
i0, i1, r = ramp(TOTAL - 2.5, TOTAL, False); env[i0:i1] *= (0.4 + 0.6 * r)   # floor 0.4: no digital hole at file end
# rain crossfade windows: bed out while rain in
rain_env = np.zeros(N, np.float32)
for a, b in rain_iv:
    i0, i1, r = ramp(a, a + 2.0, False); env[i0:i1] *= r; env[i1:S(b)] = 0
    ri0, ri1, rr = ramp(a, a + 2.0, True); rain_env[ri0:ri1] = rr; rain_env[ri1:S(b - 2.0)] = 1
    j0, j1, r2 = ramp(b - 2.0, b, False); rain_env[j0:j1] = r2
    k0, k1, r3 = ramp(b - 2.0, b, True); env[k0:k1] = r3
# jump-scare calm: bed out before, back in after the tail
cs = c06["start"]
i0, i1, r = ramp(cs + BED_FADE[0], cs + BED_FADE[1], False); env[i0:i1] *= r; env[i1:S(STING + 0.4)] = 0
i0, i1, r = ramp(STING + 0.4, STING + 2.4, True); env[i0:i1] *= r
bed_g = 10 ** ((vrms_active + BED_REL_DB - rms_db(bedl)) / 20)
bedst = (bedl * env * bed_g).astype(np.float32)   # bed stem (before the final gain)
mix = voice.copy()
# rain (outdoor only), from the approved pack
rain = rd(PACK + "rain_metal_roof_13.wav")
rain = loop(rain, N) if len(rain) < N else rain[:N]
rain_g = 10 ** ((vrms_active - 20 - rms_db(rain[rain_env > 0.5])) / 20)
mix += rain * rain_env * rain_g

# ---- cues carried over from M2 (shifted), omitted cues stay omitted
cues = []
def put(src, start, gain, dur=None, fade_out=None, off=0.0, peak=None):
    x = rd(PACK + src)[S(off):]
    if dur: x = x[:S(dur)]
    if peak: x = x * (peak / np.abs(x).max())
    else: x = x * gain
    if fade_out:
        f = S(fade_out); x[-f:] *= np.linspace(1, 0, f).astype(np.float32)
    o = S(start); mix[o:o + len(x)] += x[:N - o]
for c in led["cues"]:
    c2 = dict(c); c2["start"] = mv(c["start"]); c2["end"] = mv(c["end"]); c2["frame"] = int(round(c2["start"] * 24))
    put(c["source"], c2["start"], c["gain"]); cues.append(c2)
# false cue + sting
creak_t = c06["start"] + A_END + CREAK_AFTER_A
put("wood_floor_creak_06.wav", creak_t, 0, peak=0.30)
put("hard_horror_hit_drum_21.wav", STING, 0, dur=TAIL, fade_out=0.6, off=0.04, peak=0.50)

# ---- stems: ONE linear gain g puts voice+cues+rain+bed at -14 LUFS (stereo); stems are mono float32 with g applied.
# final = alimiter(nobed + bed). Swap the bed later: ffmpeg -i ep03_nobed.wav -i NEWBED.wav ... (see remux_audio.sh)
mix = mix.astype(np.float32)
pre = f"{OUT}/_pre.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-c:a", "pcm_f32le", pre], input=(mix + bedst).tobytes(), check=True)
r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", pre, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True)
import re
I_mono = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)[-1]); I_st = I_mono + 3.0103   # dual-mono stereo
g = 10 ** ((-14.0 - I_st) / 20); print("pre I (stereo)", I_st, "gain dB", 20 * np.log10(g))
for nm, arr in (("ep03_nobed.wav", mix * g), ("ep03_bed.wav", bedst * g)):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-c:a", "pcm_f32le", f"{OUT}/{nm}"], input=arr.astype(np.float32).tobytes(), check=True)
final = f"{OUT}/ep03_m2b_mix.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{OUT}/ep03_nobed.wav", "-i", f"{OUT}/ep03_bed.wav", "-filter_complex",
                "[0][1]amix=inputs=2:normalize=0:duration=longest,pan=stereo|c0=c0|c1=c0,alimiter=limit=0.72:attack=5:release=60:level=0", "-ar", str(SR), "-c:a", "pcm_s16le", final], check=True)
j = dict(I_pre_stereo=I_st, gain_db=float(20 * np.log10(g)), method="linear gain + alimiter 0.72 (-2.9 dBFS)")
json.dump(dict(pass1=j, bed=BED, bed_rel_db=BED_REL_DB, bed_gain=float(bed_g), voice_active_rms_db=float(vrms_active)), open(f"{OUT}/mix_metrics.json", "w"), indent=1)

# ---- ledgers
tl2 = dict(tl, duration=TOTAL, takes=new_takes, cards=new_cards, fps=24, render_fps=30, jump_scare=dict(sting_time=STING, shift=SHIFT))
tl2["cards"][-1]["end"] = TOTAL
json.dump(tl2, open(f"{OUT}/timeline.json", "w"), indent=1, ensure_ascii=False)
led2 = dict(led, cues=cues, jump_scares=1, thunder_count=0, narration_overlaps=[], narration_ducking=False)
led2["jump_scare"] = dict(
    sting_time_s=STING, sting_frame_24=int(round(STING * 24)), sting_frame_30=int(round(STING * 30)),
    sting_source="hard_horror_hit_drum_21.wav", sting_trim_from_s=0.04, sting_tail_s=TAIL, sting_peak_pre_norm=0.50,
    bed_drop_start_s=cs + BED_FADE[0], bed_drop_end_s=cs + BED_FADE[1], calm_seconds_bed_gone_to_sting=STING - CALM_START,
    false_cue=dict(source="wood_floor_creak_06.wav", start_s=creak_t, seconds_into_calm=creak_t - CALM_START),
    narration_hole=dict(from_s=cut_at, to_s=STING + 1.5), narration_resumes_s=STING + 1.5,
    picture="HARD CUT to the close eye plate (S06-03 / P025) on exactly sting_time_s; S06-02 holds through the calm; no dissolve",
    timeline_shift_after_hole_s=SHIFT)
led2["bed"] = dict(file=BED, loop_crossfade_s=2.0, rain_only_in=rain_iv, rain_source="rain_metal_roof_13.wav")
led2["bed"]["flow_music"] = dict(status="FAILED_NO_SPEND", credits_spent=0, reason="flow_music.py on winbox: connect_over_cdp to 127.0.0.1:9226 timed out (30 s) on 2 dry runs; no Generate click; CMO: 9226 is the YouTube Studio Chrome, CMO will make the Flow bed")
led2["bed"]["fallback"] = "creepy_tomb_ambience_19.wav (approved pack, 41.2 s) looped with 2 s equal-power crossfades, -24 dB under voice; NOT rain (CEO rule 2)"
led2["stems"] = dict(nobed="ep03_nobed.wav", bed="ep03_bed.wav", final="ep03_m2b_mix.wav", recipe="final = alimiter(amix(nobed,bed), 0.8414); one linear gain g applied to both stems")
json.dump(led2, open(f"{OUT}/cue_ledger.json", "w"), indent=1, ensure_ascii=False)
print("done", final)
