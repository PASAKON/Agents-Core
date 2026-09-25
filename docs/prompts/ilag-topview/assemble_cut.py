"""Join the newest H3 take of every shot, in cut order, into one previz cut and file it on Drive.

    python3 assemble_cut.py --cut 4 [--no-drive]

Takes the newest <TAG>-H3-take<N>.mp4 of each shot from the collector's folder (h3_fire.py --out), re-encodes
the join so clips of slightly different streams concatenate cleanly, and uploads it to the film's Final Draft
folder with a logs.txt line. Prints the timecode of every shot so the review can cite them.
"""
import argparse, os, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).parent
CLIPS = Path("/tmp/ilag-h3-previz")
FINAL_DRAFT = "1NkLTYnK4kRCZbeaZePLTO4hp0LihZDNP"
LOGS = "1asL3Woa5f1Lz3qhdHHTRrB-krpSRXDBY"
ORDER = {
    "3": "O1 O2 O3 O4 M4 N1 N2 N3 M6 N4 N5 N6 N7 N8 N9 N10 N11 M13",
    # CEO 2026-09-25: N4 stops at the line, then the talk (N12), then the crossing.
    "4": "O1 O2 O3 O4 M4 N1 N2 N3 M6 N4 N12 N5 N6 N7 N8 N9 N10 N11 M13",
    # CEO 2026-09-25: the wave throws them off and goes black, they wake on THE MOUNT (N13), then the catch; N8 cut.
    "5": "O1 O2 O3 O4 M4 N1 N2 N3 M6 N4 N12 N5 N6 N7 N13 N9 N10 N11 M13",
}
# Mirrored in the edit (CEO OK 2026-09-25): M4 take 2 has the rider actions but travels right to left.
FLIP = {"5": {"M4"}}


def newest(tag):
    takes = sorted(CLIPS.glob(f"{tag}-H3-take*.mp4"), key=lambda p: int(re.search(r"take(\d+)", p.name).group(1)))
    if not takes:
        raise SystemExit(f"no take of {tag} in {CLIPS}")
    return takes[-1]


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                capture_output=True, text=True, check=True).stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cut", required=True, choices=sorted(ORDER))
    ap.add_argument("--no-drive", action="store_true")
    a = ap.parse_args()
    shots = [(t, newest(t)) for t in ORDER[a.cut].split()]
    for i, (tag, p) in enumerate(shots):
        if tag in FLIP.get(a.cut, ()):
            flipped = CLIPS / f"{p.stem}-mirrored.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(p), "-vf", "hflip", "-c:v", "libx264", "-crf", "18",
                            "-c:a", "copy", str(flipped)], check=True)
            shots[i] = (tag, flipped)
    t = 0.0
    for tag, p in shots:
        print(f"{tag:4} {int(t // 60)}:{t % 60:05.2f}  {p.name}")
        t += dur(p)
    out = CLIPS / f"ILAG-H3-previz-cut{a.cut}.mp4"
    lst = CLIPS / f"cut{a.cut}.txt"
    lst.write_text("".join(f"file '{p}'\n" for _, p in shots))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c:v", "libx264",
                    "-preset", "fast", "-crf", "18", "-c:a", "aac", "-b:a", "160k", str(out)], check=True)
    print(f"total {dur(out):.1f}s -> {out}")
    if a.no_drive:
        return
    sys.path.insert(0, str(HERE.parents[2] / "scripts/gdrive-bridge"))
    import ilag_rest as d
    info, made = d.upload(out, out.name, FINAL_DRAFT)
    if made:
        d.append_log(LOGS, [d.line("ADD", "FILE", out.name, d.link(info["id"]), "Final Draft", len(d.ls(FINAL_DRAFT)),
                                   f"H3 360p previz, cut {a.cut}, {len(shots)} shots, md5 {info['md5Checksum']}")])
    print("ASSEMBLY", d.link(info["id"]))


if __name__ == "__main__":
    main()
