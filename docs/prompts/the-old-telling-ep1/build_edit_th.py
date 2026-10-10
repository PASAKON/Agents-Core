#!/usr/bin/env python3
"""The Old Telling EP1 ACT 1, Thai version: picture of the English master (English picture text, no burned subtitles)
+ Thai narration and Thai character lines. Run from the repo root with the repo venv:

    .venv/bin/python -I <this file> [--e05 <king clip>] [--dry]

No paid call. Picture: e01 (0 to 15.08), e02 (0 to 12.5), e05 king (4.46), e03 (0 to 15.08), black card 2.2, e04 (0 to 12.5).
Thai sentences are laid on the picture; no time-stretch (CEO 2026-10-09: a longer line may run on, a shorter one gets air).
Without --e05 a STAND-IN (tail of e02) is used so the sound timing can be checked; the output is then marked standin.
"""
import json, pathlib, subprocess, sys

S = pathlib.Path("/private/tmp/claude-501/-Users-gob-MoonieXHQ-Agents-Core/4f1a10f5-0427-4c0c-bbaf-d71cf76492bf/scratchpad")
OUT = S / "edit2"; OUT.mkdir(exist_ok=True)
V = S / "voice2" / "out"
FPS = 24
CLIP = {k: S / "clips" / f"{k}.mp4" for k in ("e01", "e02", "e03", "e04")}
STANDIN = "--e05" not in sys.argv
E05 = CLIP["e02"] if STANDIN else pathlib.Path(sys.argv[sys.argv.index("--e05") + 1])
E05_IN = 10.6 if STANDIN else 0.0  # stand-in = the last 4.46 s of e02
TITLE, T1 = S / "titlecard" / "title_en.png", S / "titlecard" / "t1_black.png"
TH = json.loads((V / "timings.json").read_text(encoding="utf-8"))["act1"]
N = {r["id"]: r for r in TH}

# segments in frames: (name, clip, in_frame, frames)
SEG = [("e01", 0, 362), ("e02", 0, 295), ("e05", int(E05_IN * FPS), 107), ("e03", 0, 362), ("card", 0, 53), ("e04", 0, 300)]
starts, t = {}, 0
for name, _, n in SEG:
    starts[name] = t / FPS; t += n
TOTAL = t / FPS  # 61.625

# voice placement on the final timeline (seconds): narration sentence start, line speech start
PLACE = {"N1": 3.05, "N2": 7.25, "N3": 10.85, "N4": 15.40, "N5": 20.40,
         "N6": 31.72, "N7": 36.27, "N8": 44.55, "N9": 49.45, "N10": 52.60}
KING_AT = starts["e05"] + 0.6          # H3 mouth window of the king shot opens 0.6 s in (the audio hint was padded to that)
ORPH_AT = starts["e03"] + 8.62         # clip 3: he turns at ~7.5-8.0 s, the lips open at 8.45 s; the call lands 0.17 s after, N7 ends just before
EURY_AT = starts["e03"] + 11.30        # the silhouette comes apart at ~11 s
T1_AT = 47.55                          # spoken 'seven months later' (CEO 2026-10-10): after N8 ends (47.35), card fully lit from 47.22, before N9 (49.45)
MUTE = {"e03": [(8.2, 9.4)], "e05": [(0.65, 2.05), (2.9, 4.3)]}  # H3's own voicing (clip seconds), muted; the real line is laid instead
# measured on the rendered e05 (RMS of its own track): H3 voiced 0.8-1.9 s and 3.0-4.0 s and the lips follow that; the real Thai king line has
# phrase 1 at 0.05-0.92 s, a 0.43 s pause, phrase 2 at 1.35-2.55 s, so it is cut at 1.15 s and each phrase is laid on its own mouth burst.
KING_PIECES = [(0.0, 1.15, 0.80), (1.15, 2.77, 2.80)]  # (take in, take out, clip second where the piece starts)


def main():
    order = sorted(PLACE, key=lambda x: PLACE[x])
    for a, b in zip(order, order[1:]):
        end = PLACE[a] + (N[a]["end"] - N[a]["start"])
        assert end <= PLACE[b] + 0.001, ("narration overlap", a, b, round(end, 2), PLACE[b])
    placement = {"standin_e05": STANDIN, "total": TOTAL, "starts": starts, "place": PLACE, "king_at": KING_AT, "orpheus_at": ORPH_AT,
                 "eurydice_at": EURY_AT, "t1_at": T1_AT, "mute": MUTE,
                 "narration_ends": {k: round(PLACE[k] + N[k]["end"] - N[k]["start"], 2) for k in PLACE}}
    (OUT / "placement.json").write_text(json.dumps(placement, indent=1), encoding="utf-8")
    if "--dry" in sys.argv:
        print(json.dumps(placement, indent=1)); return

    inputs = [CLIP["e01"], CLIP["e02"], E05, CLIP["e03"], CLIP["e04"]]
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for p in inputs:
        cmd += ["-i", str(p)]
    cmd += ["-loop", "1", "-framerate", "24", "-t", "3.4", "-i", str(TITLE)]          # 5
    cmd += ["-loop", "1", "-framerate", "24", "-t", "2.2", "-i", str(T1)]             # 6
    cmd += ["-i", str(V / "act1_teller_daniel.mp3"), "-i", str(V / "act1_c1_king_brian.mp3"),   # 7 8
            "-i", str(S / "voice1/out/orpheus_liam.mp3"), "-i", str(V / "act1_c3_eurydice.mp3"),  # 9 10
            "-i", str(V / "act1_t1_teller_daniel.mp3")]  # 11
    fc = []
    idx = {"e01": 0, "e02": 1, "e05": 2, "e03": 3, "e04": 4}
    vl = []
    for name, a, n in SEG:
        if name == "card":
            fc.append("[6:v]scale=1920:1080,setsar=1,fps=24,format=yuv420p,fade=t=in:st=0:d=0.3,fade=t=out:st=1.9:d=0.3[vc]"); vl.append("[vc]"); continue
        i = idx[name]
        fc.append(f"[{i}:v]trim=start_frame={a}:end_frame={a + n},setpts=PTS-STARTPTS,crop=1920:1080:0:4,setsar=1,fps=24,format=yuv420p[v{name}]"); vl.append(f"[v{name}]")
    fc.append("".join(vl) + f"concat=n={len(vl)}:v=1:a=0[base]")
    fc.append("[5:v]scale=1920:1080,format=rgba,fade=t=in:st=0:d=0.5,fade=t=out:st=2.4:d=0.8:alpha=1[ti]")
    fc.append("[base][ti]overlay=0:0:eof_action=pass[vt]")
    fc.append(f"[vt]fade=t=out:st={TOTAL - 1.2:.3f}:d=1.2,format=yuv420p[vout]")
    # ambient from the clips (H3's own voicing muted), silence under the card
    al = []
    for name, a, n in SEG:
        if name == "card":
            fc.append(f"aevalsrc=0:d={n / FPS:.4f}:s=48000:c=stereo[ac]"); al.append("[ac]"); continue
        i, s0 = idx[name], a / FPS
        f = f"[{i}:a]atrim=start={s0:.4f}:end={s0 + n / FPS:.4f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo"
        if name in MUTE:
            if not (STANDIN and name == "e05"):
                for m0, m1 in MUTE[name]:
                    f += f",volume=0:enable='between(t,{m0},{m1})'"
        fc.append(f + f"[a{name}]"); al.append(f"[a{name}]")
    fc.append("".join(al) + "concat=n=6:v=0:a=1,volume=4dB[ambient]")
    # voices
    parts = []
    for sid, r in N.items():
        a0, a1 = max(0.0, r["start"] - 0.03), r["end"] + 0.10
        ms = int(round((PLACE[sid] - 0.03) * 1000))
        fc.append(f"[7:a]atrim=start={a0:.3f}:end={a1:.3f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[n{sid}]"); parts.append(f"[n{sid}]")
    for k, (a0, a1, at0) in enumerate(KING_PIECES):
        ms = int(round((starts["e05"] + at0) * 1000))
        fc.append(f"[8:a]atrim=start={a0}:end={a1},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,afade=t=in:d=0.02,adelay={ms}|{ms}[king{k}]"); parts.append(f"[king{k}]")
    for lab, i, at in (("orph", 9, ORPH_AT), ("eury", 10, EURY_AT), ("t1", 11, T1_AT)):
        ms = int(round(at * 1000))
        fc.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,silenceremove=start_periods=1:start_threshold=-45dB,adelay={ms}|{ms}[{lab}]"); parts.append(f"[{lab}]")
    fc.append("".join(parts) + f"amix=inputs={len(parts)}:normalize=0:duration=longest,apad=whole_dur={TOTAL:.3f}[bus]")  # pad: sidechaincompress ends with its shorter input, which cut the last 4.3 s of ambient
    fc.append("[bus]asplit=2[bus_sc][bus_mix]")
    fc.append("[ambient][bus_sc]sidechaincompress=threshold=0.02:ratio=6:attack=15:release=450:makeup=1[duck]")
    fc.append(f"[duck][bus_mix]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:st=0:d=0.8,afade=t=out:st={TOTAL - 1.5:.3f}:d=1.5[aout]")
    tag = "standin" if STANDIN else "final"
    master = OUT / f"ACT1_th_{tag}_1080p.mp4"
    cmd += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]", "-t", f"{TOTAL:.3f}",
            "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", str(master)]
    (OUT / f"ffmpeg_cmd_{tag}.txt").write_text(" ".join(cmd), encoding="utf-8")
    subprocess.run(cmd, check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(master), "-vf", "scale=960:540:flags=lanczos", "-c:v", "libx264", "-preset", "medium", "-crf", "24",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(OUT / f"ACT1_th_{tag}_540p.mp4")], check=True)
    print("done", master.name, "total", round(TOTAL, 3), "standin" if STANDIN else "")


main()
