#!/usr/bin/env python3
"""The Old Telling EP1 ACT 3 (Thai): picture of the 16 new H3 shots (clips3/sNN.mp4) + Thai narration + Orpheus' line. No paid call.

    .venv/bin/python -I docs/prompts/the-old-telling-ep1/build_act3_edit.py [--dry]

Same method as build_act2_edit.py. Picture is the master, hard cuts. Each shot carries the narration sentences it was planned for (build_act3.py `line`),
the first sentence LEAD seconds after the cut, the rest at their natural gaps. No time-stretch (CEO 2026-10-09): a sentence longer than its shot makes the shot
hold its last frame for at most HOLD_MAX seconds, a shorter one leaves air. Shots longer than their sentence are cut at DUR (the action is already finished).
3.11 is three sentences over three clips (s11a, s11b, s11c). s09 (Orpheus speaks): H3 voices the audio hint itself and the lips follow ITS voicing; its voicing
is muted and the real Thai line is laid on the lip bursts of the clip (sentence 1 on bursts 1-2, sentence 2 on burst 3), found by the envelope of the clip's own track.
Picture text that matters is spoken (BRAND.md): ACT 3 has no picture text.
"""
import json, math, pathlib, subprocess, sys
import numpy as np

S = pathlib.Path("/private/tmp/claude-501/-Users-gob-MoonieXHQ-Agents-Core/4f1a10f5-0427-4c0c-bbaf-d71cf76492bf/scratchpad")
HERE = pathlib.Path(__file__).parent
OUT = S / "edit5"; OUT.mkdir(exist_ok=True)
C3, V = S / "clips3", S / "voice3"
FPS, LEAD, TAIL, HOLD_MAX = 24, 0.35, 0.15, 1.0
TH = {r["id"]: r for r in json.loads((V / "timings.json").read_text(encoding="utf-8"))["act3"]}
LINE = HERE / "voice-th/out-act3/act3_309_orpheus_liam.mp3"
NARR = V / "act3_teller_daniel.mp3"

# (key, file, in_s, dur_s or None = rest of clip, sentence ids, lead)
GROUPS = [
    ("s01", C3 / "s01.mp4", 1.4, None, ["3.01"], LEAD),   # clip opens warm brown and cools over about 2 s: start at 1.4 s
    ("s02", C3 / "s02.mp4", 0.0, None, ["3.02"], LEAD),
    ("s03", C3 / "s03.mp4", 0.0, None, ["3.03"], LEAD),
    ("s04", C3 / "s04.mp4", 0.0, None, ["3.04"], LEAD),
    ("s05", C3 / "s05.mp4", 0.0, 2.4, ["3.05"], LEAD),
    ("s06", C3 / "s06.mp4", 0.0, 6.4, ["3.06"], LEAD),
    ("s07", C3 / "s07.mp4", 0.0, 11.2, ["3.07"], LEAD),
    ("s08", C3 / "s08.mp4", 0.0, 8.2, ["3.08"], LEAD),
    ("s09", C3 / "s09.mp4", 0.0, None, [], 0),
    ("s10", C3 / "s10.mp4", 0.0, 2.9, ["3.10"], LEAD),
    ("s11a", C3 / "s11a.mp4", 0.0, 3.4, ["3.11a"], LEAD),
    ("s11b", C3 / "s11b.mp4", 0.0, 2.8, ["3.11b"], LEAD),
    ("s11c", C3 / "s11c.mp4", 0.0, 3.5, ["3.11c"], LEAD),
    ("s12", C3 / "s12.mp4", 0.0, 4.0, ["3.12"], LEAD),
    ("s13", C3 / "s13.mp4", 0.0, 7.0, ["3.13"], LEAD),
    ("s14", C3 / "s14.mp4", 0.0, 6.2, ["3.14"], LEAD),
    ("s15", C3 / "s15.mp4", 0.0, None, ["3.15"], LEAD),
    ("s16", C3 / "s16.mp4", 0.0, None, ["3.16"], LEAD),
]


def nframes(p):
    return int(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=nb_frames", "-of", "csv=p=0", str(p)]).split()[0])


def envelope(path, hop=0.02):
    x = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True, check=True).stdout, dtype=np.int16).astype(np.float32) / 32768
    n = int(16000 * hop); k = len(x) // n
    return np.sqrt((x[:k * n].reshape(k, n) ** 2).mean(1)), hop


def bursts(path, rel=0.12, gap=0.3, minlen=0.15):
    e, hop = envelope(path); act = e > rel * e.max(); res, i = [], 0
    while i < len(act):
        if act[i]:
            j = i
            while j < len(act) and (act[j] or act[j:j + int(gap / hop)].any()):
                j += 1
            while j > i and not act[j - 1]:
                j -= 1
            if (j - i) * hop >= minlen:
                res.append((round(i * hop, 2), round(j * hop, 2)))
            i = j + 1
        else:
            i += 1
    return res


def main():
    dry = "--dry" in sys.argv
    segs, place, notes, t = [], {}, [], 0.0
    orph = {}
    for key, f, in_s, dur, sids, lead in GROUPS:
        n_full = nframes(f); a = int(round(in_s * FPS)); n = int(round(dur * FPS)) if dur else n_full - a
        assert a + n <= n_full, (key, "asks past the end of the clip", a + n, n_full)
        seg = dict(key=key, file=f, a=a, n=n, hold=0.0, mute=[], start=round(t, 3))
        seg_end = t + n / FPS
        if sids:
            at = t + lead; prev = None; last_end = 0.0
            for sid in sids:
                if prev is not None:
                    at = place[prev] + (TH[sid]["start"] - TH[prev]["start"])
                place[sid] = round(at, 3); last_end = at + TH[sid]["end"] - TH[sid]["start"]; prev = sid
            need = last_end + TAIL - seg_end
            if need > 0:
                seg["hold"] = min(HOLD_MAX, math.ceil(need * FPS) / FPS)
                if need > HOLD_MAX:
                    notes.append(f"{key}: narration runs {need - HOLD_MAX:.2f} s past the shot even after a {HOLD_MAX} s hold")
        if key == "s09":
            hb, lb = bursts(f), bursts(LINE)
            orph = dict(clip_bursts=hb, line_bursts=lb)
            seg["mute"] = [(max(0.0, b0 - 0.08), b1 + 0.08) for b0, b1 in hb]
        segs.append(seg); t = seg_end + seg["hold"]
    total = t
    order = sorted(place, key=lambda x: place[x])
    for a_, b_ in zip(order, order[1:]):
        end = place[a_] + TH[a_]["end"] - TH[a_]["start"]
        if end > place[b_] + 0.001:
            notes.append(f"narration overlap {a_} ends {end:.2f}, {b_} starts {place[b_]:.2f}")
    s09 = next(s for s in segs if s["key"] == "s09")
    cb, lb = orph["clip_bursts"], orph["line_bursts"]
    orph_pieces = []
    if len(lb) == 4 and len(cb) >= 3:
        # line = two sentences: 1 = phrases 1+2 (about 2.1 s), 2 = phrases 3+4 (about 2.5 s). Sentence 1 starts with the first lip burst, sentence 2 with the third.
        p1 = (max(0.0, lb[0][0] - 0.03), lb[1][1] + 0.05); p2 = (max(0.0, lb[2][0] - 0.03), lb[3][1] + 0.05)
        t1 = cb[0][0]; t2 = max(cb[2][0], t1 + (p1[1] - p1[0]) + 0.35)
        orph_pieces = [(p1[0], p1[1], round(s09["start"] + t1, 3)), (p2[0], p2[1], round(s09["start"] + t2, 3))]
        orph["lay_in_clip_s"] = [round(t1, 2), round(t2, 2)]
        orph["voice_ends_before_lips_s"] = round(cb[-1][1] - (t2 + p2[1] - p2[0]), 2)
    else:
        notes.append("s09: clip bursts / line bursts are not the >=3 / 4 this lay was written for; line laid whole from the first lip movement. CHECK BY EAR.")
        t1 = cb[0][0] if cb else 0.6
        orph_pieces.append((0.0, 6.0, round(s09["start"] + t1, 3)))
    placement = dict(total=round(total, 3), segments=[{k: (str(v) if isinstance(v, pathlib.Path) else v) for k, v in s.items()} for s in segs],
                     narration_at=place, orpheus=orph, orpheus_pieces=orph_pieces, notes=notes)
    (OUT / "placement.json").write_text(json.dumps(placement, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: placement[k] for k in ("total", "narration_at", "orpheus", "orpheus_pieces", "notes")}, indent=1, default=str))
    if dry:
        return

    files = []
    for s in segs:
        if s["file"] not in files:
            files.append(s["file"])
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for f in files:
        cmd += ["-i", str(f)]
    i_narr, i_line = len(files), len(files) + 1
    cmd += ["-i", str(NARR), "-i", str(LINE)]
    fc, vl, al = [], [], []
    for k, s in enumerate(segs):
        i = files.index(s["file"]); a0, dur = s["a"] / FPS, s["n"] / FPS + s["hold"]
        # new H3 clips carry black rounded corners: crop 4.3 % in and scale back
        fit = "crop=1840:1035:40:26,scale=1920:1080:flags=lanczos"
        v = f"[{i}:v]trim=start_frame={s['a']}:end_frame={s['a'] + s['n']},setpts=PTS-STARTPTS,{fit},setsar=1,fps=24,format=yuv420p"
        if s["hold"]:
            v += f",tpad=stop_mode=clone:stop_duration={s['hold']:.4f}"
        fc.append(v + f"[v{k}]"); vl.append(f"[v{k}]")
        au = f"[{i}:a]atrim=start={a0:.4f}:end={a0 + s['n'] / FPS:.4f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo"
        for m0_, m1_ in s["mute"]:
            au += f",volume=0:enable='between(t,{m0_:.3f},{m1_:.3f})'"
        fc.append(au + f",apad=whole_dur={dur:.4f},atrim=end={dur:.4f}[a{k}]"); al.append(f"[a{k}]")
    fc.append("".join(vl) + f"concat=n={len(vl)}:v=1:a=0[base]")
    fc.append(f"[base]fade=t=in:st=0:d=0.4,fade=t=out:st={total - 1.0:.3f}:d=1.0,format=yuv420p[vout]")
    fc.append("".join(al) + f"concat=n={len(al)}:v=0:a=1,volume=4dB[ambient]")
    parts = []
    for sid in order:
        r = TH[sid]; a0, a1 = max(0.0, r["start"] - 0.03), r["end"] + 0.10; ms = int(round((place[sid] - 0.03) * 1000))
        lab = "n" + sid.replace(".", "_")
        fc.append(f"[{i_narr}:a]atrim=start={a0:.3f}:end={a1:.3f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[{lab}]")
        parts.append(f"[{lab}]")
    for k, (a0, a1, at) in enumerate(orph_pieces):
        ms = int(round(at * 1000))
        fc.append(f"[{i_line}:a]atrim=start={a0:.3f}:end={a1:.3f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,afade=t=in:d=0.02,adelay={ms}|{ms}[orph{k}]")
        parts.append(f"[orph{k}]")
    fc.append("".join(parts) + f"amix=inputs={len(parts)}:normalize=0:duration=longest,apad=whole_dur={total:.3f}[bus]")
    fc.append("[bus]asplit=2[bus_sc][bus_mix]")
    fc.append("[ambient][bus_sc]sidechaincompress=threshold=0.02:ratio=6:attack=15:release=450:makeup=1[duck]")
    fc.append(f"[duck][bus_mix]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:st=0:d=0.5,afade=t=out:st={total - 1.0:.3f}:d=1.0[aout]")
    master = OUT / "ACT3_th_1080p.mp4"
    cmd += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}",
            "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", str(master)]
    (OUT / "ffmpeg_cmd_act3.txt").write_text(" ".join(cmd), encoding="utf-8")
    subprocess.run(cmd, check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(master), "-vf", "scale=960:540:flags=lanczos", "-c:v", "libx264", "-preset", "medium", "-crf", "24",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(OUT / "ACT3_th_540p.mp4")], check=True)
    print("done", master.name, "total", round(total, 3))


main()
