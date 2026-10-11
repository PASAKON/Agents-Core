#!/usr/bin/env python3
"""The Old Telling EP1 ACT 1, Thai version: picture of the English master (English picture text, no burned subtitles)
+ Thai narration and Thai character lines. Run from the repo root with the repo venv:

    .venv/bin/python -I <this file> [--e05 <king clip>] [--dry]

No paid call. Picture: e01 (0 to 15.08), e02 (0 to 12.5), e05 king (4.46), e03 (0 to 15.08), black card 2.2, e04 (0 to 12.5).
Thai sentences are laid on the picture; no time-stretch (CEO 2026-10-09: a longer line may run on, a shorter one gets air).
Without --e05 a STAND-IN (tail of e02) is used so the sound timing can be checked; the output is then marked standin.
v2 (2026-10-11): the picture stream of the v1 master is copied; only the sound is rebuilt with edit_lib (narration cut at measured silence, beds level-matched and crossfaded).
"""
import json, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import edit_lib as E  # noqa: E402  (v2, 2026-10-11: sound rebuilt on measured silence; the picture of v1 is kept as it is, ACT 1 had no frozen frames)

S = pathlib.Path("/private/tmp/claude-501/-Users-gob-MoonieXHQ-Agents-Core/4f1a10f5-0427-4c0c-bbaf-d71cf76492bf/scratchpad")
OUT = S / "edit8"; OUT.mkdir(exist_ok=True)
V1_PICTURE = S / "edit2" / "ACT1_th_final_1080p.mp4"   # the v1 master: its picture stream is copied (ACT 1 has no hold, nothing to re-cut)
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
    (OUT / "ACT1_placement.json").write_text(json.dumps(placement, indent=1), encoding="utf-8")
    if "--dry" in sys.argv:
        print(json.dumps(placement, indent=1)); return

    assert not STANDIN, "v2 sound is built for the real king clip: pass --e05 <clips/e05.mp4>"
    video = OUT / "ACT1_video.mp4"
    if not video.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(V1_PICTURE), "-an", "-c:v", "copy", "-movflags", "+faststart", str(video)], check=True)
    files = {"e01": CLIP["e01"], "e02": CLIP["e02"], "e05": E05, "e03": CLIP["e03"], "e04": CLIP["e04"]}
    segs = []
    for name, a, n in SEG:
        if name == "card":
            segs.append(dict(key=name, a=0, n=n, hold=0.0, mute=[], silence=True)); continue
        segs.append(dict(key=name, file=str(files[name]), a=a, n=n, hold=0.0, mute=[] if (STANDIN and name == "e05") else list(MUTE.get(name, []))))
    items = [(sid, r["start"], r["end"]) for sid, r in N.items()]
    lines = [dict(path=V / "act1_c1_king_brian.mp3", a0=a0, a1=a1, at=starts["e05"] + at0) for a0, a1, at0 in KING_PIECES]
    lines += [dict(path=S / "voice1/out/orpheus_liam.mp3", a0=None, at=ORPH_AT), dict(path=V / "act1_c3_eurydice.mp3", a0=None, at=EURY_AT),
              dict(path=V / "act1_t1_teller_daniel.mp3", a0=None, at=T1_AT)]
    A = E.build_audio(OUT, "ACT1", segs, TOTAL, V / "act1_teller_daniel.mp3", items, PLACE, lines, fade_in=0.8, fade_out=1.5)
    master = OUT / "ACT1_th_final_1080p.mp4"
    E.mux(video, A["audio"], master, TOTAL)
    E.preview540(master, OUT / "ACT1_th_final_540p.mp4")
    print(json.dumps(A["audit"], indent=1))
    print("done", master.name, "total", round(TOTAL, 3))

main()
