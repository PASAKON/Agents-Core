#!/usr/bin/env python3
"""The Old Telling EP1 ACT 2 (Thai): picture of the new H3 shots (clips2/sNN.mp4) + Thai narration + Orpheus' line. No paid call.

    .venv/bin/python -I docs/prompts/the-old-telling-ep1/build_act2_edit.py [--dry]

Picture is the master, hard cuts. Each shot carries the narration sentences it was planned for (build_act2.py `line`), the first sentence
LEAD seconds after the cut, the rest at their natural gaps. No time-stretch (CEO 2026-10-09): a sentence longer than its shot makes the shot hold
its last frame for at most HOLD_MAX seconds, a shorter one leaves air. 2.04 (three questions) is a cut of three pieces: field, cave, river.
s12 (Orpheus speaks): H3 voices the audio hint itself and the lips follow ITS voicing; its voicing is muted and each phrase of the real Thai line
is laid on the matching mouth burst, found by the envelope of the clip's own track (same method as the king shot in ACT 1).
Picture text that matters is spoken (BRAND.md): ACT 2 has no picture text.
"""
import json, math, pathlib, subprocess, sys
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import edit_lib as E  # noqa: E402  (v2, 2026-10-11: shots extend instead of freezing; narration cut at measured silence; beds level-matched and crossfaded)

S = pathlib.Path("/private/tmp/claude-501/-Users-gob-MoonieXHQ-Agents-Core/4f1a10f5-0427-4c0c-bbaf-d71cf76492bf/scratchpad")
OUT = S / "edit8"; OUT.mkdir(exist_ok=True)
NOEXT = {"s03"}  # the retake shows a small flame at the torch tip from 6.4 s: this shot is never lengthened past 6.3 s, its narration runs into the next shot instead
V, C2, C1 = S / "voice2" / "out", S / "clips2", S / "clips"
FPS, LEAD, TAIL, HOLD_MAX = 24, 0.35, 0.15, 1.0
TH = {r["id"]: r for r in json.loads((V / "timings.json").read_text(encoding="utf-8"))["act2"]}
LINE = V / "act2_215_orpheus_liam.mp3"

# (key, file, in_s, dur_s or None = whole clip, sentence ids, lead)   m* = the 2.04 montage pieces, taken from clips already made
GROUPS = [
    ("s01", C2 / "s01.mp4", 0.0, None, ["2.01", "2.02", "2.03"], 0.05),
    ("m1", C2 / "s09.mp4", 0.3, 1.9, [], 0), ("m2", C2 / "s14.mp4", 2.4, 2.6, [], 0), ("m3", C1 / "e04.mp4", 9.0, 2.2, [], 0),
    ("s03", C2 / "s03.mp4", 0.0, 6.3, ["2.05", "2.06"], LEAD),  # retake: a small flame shows at the torch tip from 6.4 s, so the shot is cut at 6.3 s and holds its last frame under the narration
    ("s04", C2 / "s04.mp4", 0.0, None, ["2.07"], LEAD), ("s05", C2 / "s05.mp4", 0.0, None, ["2.08"], LEAD),
    ("s06", C2 / "s06.mp4", 0.0, None, ["2.09"], LEAD), ("s07", C2 / "s07.mp4", 0.0, None, ["2.10"], LEAD),
    ("s08", C2 / "s08.mp4", 0.0, None, ["2.11"], LEAD), ("s09", C2 / "s09.mp4", 0.0, None, ["2.12"], LEAD),
    ("s10", C2 / "s10.mp4", 0.0, None, ["2.13"], LEAD), ("s11", C2 / "s11.mp4", 0.0, None, ["2.14"], LEAD),
    ("s12", C2 / "s12.mp4", 0.0, None, [], 0),
    ("s13", C2 / "s13.mp4", 0.0, None, ["2.16"], LEAD), ("s14", C2 / "s14.mp4", 0.0, None, ["2.17"], LEAD),
    ("s15", C2 / "s15.mp4", 0.0, None, ["2.18"], LEAD),
]
M_NARR_AT = 0.30  # 2.04 starts this long after the montage starts; pieces are cut just before each question (1.9 s, 4.5 s)


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
    segs, place, notes, t = [], {}, [], 0.0   # segs: dict(key, file, a, n, hold, mute, start)
    orph = {}
    carry = 0.0   # when the narration so far ends (s): the next sentence waits for it, an L-cut over the next shot instead of a frozen last frame
    carry_in_s12 = 0.0
    for gi, (key, f, in_s, dur, sids, lead) in enumerate(GROUPS):
        n_full = nframes(f); a = int(round(in_s * FPS)); n = int(round(dur * FPS)) if dur else n_full - a
        assert a + n <= n_full, (key, "asks past the end of the clip", a + n, n_full)
        seg = dict(key=key, file=f, a=a, n=n, hold=0.0, mute=[], start=round(t, 3))
        seg_end = t + n / FPS
        if key == "s12":
            carry_in_s12 = carry
        if key == "m1":   # 2.04 starts a little after the montage starts, never before the sentence before it is over
            at04 = max(t + M_NARR_AT, carry + 0.30 if carry else 0.0)
            place["2.04"] = round(at04, 3); carry = at04 + TH["2.04"]["end"] - TH["2.04"]["start"]
            if at04 > t + M_NARR_AT + 0.001:
                notes.append(f"2.04 waits {at04 - t - M_NARR_AT:.2f} s for the sentence before it: the montage cuts no longer sit just before each question")
        if sids:
            at = max(t + lead, carry + 0.30 if carry else 0.0); prev = None; last_end = 0.0
            for sid in sids:
                if prev is not None:
                    at = place[prev] + (TH[sid]["start"] - TH[prev]["start"])
                place[sid] = round(at, 3); last_end = at + TH[sid]["end"] - TH[sid]["start"]; prev = sid
            carry = last_end
            seg_end, spill = E.settle(seg, t, last_end, n_full, TAIL, noext=key in NOEXT, is_last=gi == len(GROUPS) - 1, hold_max=HOLD_MAX)
            if seg["n"] != n:
                notes.append(f"{key}: lengthened {(seg['n'] - n) / FPS:.2f} s with the clip's own frames (no freeze)")
            if spill > 0.02:
                notes.append(f"{key}: narration runs {spill:.2f} s into the next shot (L-cut)")
            if seg["hold"]:
                notes.append(f"{key}: last shot of the ACT holds {seg['hold']:.2f} s under the closing fade")
        if key == "s12":
            hb, lb = bursts(f), bursts(LINE)
            orph = dict(clip_bursts=hb, line_bursts=lb, matched=len(hb) == len(lb) and len(hb) > 0)
            seg["mute"] = [(max(0.0, b0 - 0.08), b1 + 0.08) for b0, b1 in hb]
        segs.append(seg); t = seg_end
    total = t
    order = sorted(place, key=lambda x: place[x])
    for a_, b_ in zip(order, order[1:]):
        end = place[a_] + TH[a_]["end"] - TH[a_]["start"]
        if end > place[b_] + 0.001:
            notes.append(f"narration overlap {a_} ends {end:.2f}, {b_} starts {place[b_]:.2f}")
    s12 = next(s for s in segs if s["key"] == "s12")
    orph_pieces = []
    cb, lb = orph["clip_bursts"], orph["line_bursts"]
    if len(cb) == 2 and len(lb) == 3:
        # H3 voiced the line as 2 bursts (A about 1.3 s, B about 2.0 s); the real line is 3 bursts, sentence 1 = bursts 1+2, sentence 2 = burst 3 (about 2.0 s, same length as B).
        # No time-stretch: sentence 1 starts when the lips start (A), its inner pause is cut to 0.15 s, sentence 2 follows 0.35 s later but never before B starts.
        (p1a, p1b), (p2a, p2b), (p3a, p3b) = [(max(0.0, a - 0.03), b + 0.05) for a, b in lb]
        t1 = cb[0][0]; t2 = t1 + (p1b - p1a) + 0.15; t3 = max(t2 + (p2b - p2a) + 0.35, cb[1][0])
        orph_pieces = [(p1a, p1b, round(s12["start"] + t1, 3)), (p2a, p2b, round(s12["start"] + t2, 3)), (p3a, p3b, round(s12["start"] + t3, 3))]
        orph["lay_in_clip_s"] = [round(t1, 2), round(t2, 2), round(t3, 2)]
        orph["voice_after_lips_s"] = round(t3 + (p3b - p3a) - cb[1][1], 2)
    else:
        notes.append("s12: clip bursts / line bursts are not the 2 / 3 this lay was written for; line laid whole from the first lip movement. CHECK BY EAR.")
        t1 = cb[0][0] if cb else 0.6
        orph_pieces.append((0.0, 6.0, round(s12["start"] + t1, 3)))
    if carry_in_s12 > orph_pieces[0][2] - 0.15:
        notes.append(f"s12: the narration before it ends {carry_in_s12:.2f}, Orpheus' line starts {orph_pieces[0][2]:.2f}: they touch. CHECK BY EAR.")
    placement = dict(total=round(total, 3), segments=[{k: (str(v) if isinstance(v, pathlib.Path) else v) for k, v in s.items()} for s in segs],
                     narration_at=place, orpheus=orph, orpheus_pieces=orph_pieces, notes=notes)
    (OUT / "ACT2_placement.json").write_text(json.dumps(placement, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: placement[k] for k in ("total", "narration_at", "orpheus", "notes")}, indent=1, default=str))
    if dry:
        return

    files = []
    for s in segs:
        if s["file"] not in files:
            files.append(s["file"])
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for f in files:
        cmd += ["-i", str(f)]
    fc, vl = [], []
    for k, s in enumerate(segs):
        i = files.index(s["file"])
        # new H3 clips carry black rounded corners (corner 0, inner bright; radius about 90 px): crop 4.3 % in and scale back. Owned older clips: plain 1088 -> 1080 crop.
        fit = "crop=1840:1035:40:26,scale=1920:1080:flags=lanczos" if s["file"].parent == C2 else "crop=1920:1080:0:4"
        v = f"[{i}:v]trim=start_frame={s['a']}:end_frame={s['a'] + s['n']},setpts=PTS-STARTPTS,{fit},setsar=1,fps=24,format=yuv420p"
        if s["hold"]:
            v += f",tpad=stop_mode=clone:stop_duration={s['hold']:.4f}"
        fc.append(v + f"[v{k}]"); vl.append(f"[v{k}]")
    fc.append("".join(vl) + f"concat=n={len(vl)}:v=1:a=0[base]")
    fc.append(f"[base]fade=t=in:st=0:d=0.4,fade=t=out:st={total - 1.0:.3f}:d=1.0,format=yuv420p[vout]")
    video = OUT / "ACT2_video.mp4"
    cmd += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-an", "-t", f"{total:.3f}",
            "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-r", "24", "-movflags", "+faststart", str(video)]
    (OUT / "ffmpeg_cmd_act2_video.txt").write_text(" ".join(cmd), encoding="utf-8")
    if not ("--reuse-video" in sys.argv and video.exists()):   # --reuse-video: the picture is already encoded, redo only the sound (minutes saved)
        subprocess.run(cmd, check=True)
    items = [(sid, TH[sid]["start"], TH[sid]["end"]) for sid in order]
    lines = [dict(path=LINE, a0=a0, a1=a1, at=at) for a0, a1, at in orph_pieces]
    A = E.build_audio(OUT, "ACT2", segs, total, V / "act2_teller_daniel.mp3", items, place, lines, fade_in=0.5, fade_out=1.0)
    master = OUT / "ACT2_th_1080p.mp4"
    E.mux(video, A["audio"], master, total)
    E.preview540(master, OUT / "ACT2_th_540p.mp4")
    print(json.dumps(A["audit"], indent=1))
    print("done", master.name, "total", round(total, 3))


main()
