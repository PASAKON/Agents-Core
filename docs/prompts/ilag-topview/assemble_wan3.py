"""Assemble the Wan3 clips into cut-5 order, one segment per shot, at 1080p for review.

    python assemble_wan3.py [--clips /tmp/ilag-wan3/clips] [--out /tmp/ilag-wan3/assembly] [--name ILAG-Wan3-assembly-1]

Writes <name>.mp4 (clean) and <name>-labeled.mp4 (shot id + source clip burned in the corner, for notes by shot).
Shot boundaries inside a group clip are the hard cuts ffmpeg's scene detection found (threshold 0.25, and 0.08 for
the g7 space pull-out); where a group has no cut (g3 dive, g4 pillars -> line) the planned time from the group's
prompt is used, and those shots sit next to each other in the cut anyway. N10 (the shadow) is cut into the long take
at 16 s, where the mountain begins to rise. Every time is a frame number at 30 fps, so no segment starts mid-frame.
"""
import argparse, subprocess, tempfile
from pathlib import Path

FPS = 30
# (shot, clip, first frame, end frame exclusive or None for the clip's end) — cut 5: O1 O2 O3 O4 M4 N1 N2 N3 M6 N4
# N12 N5 N6 N7 N13 N9 N10 N11 M13 (assemble_cut.py ORDER "5").
SEGMENTS = [
    ("O1", "g1", 0, 478), ("O2", "g1", 478, 900),
    ("O3", "g2", 0, 346), ("O4", "g2", 346, 615), ("M4", "g2", 615, 900),
    ("N1", "g7", 0, 179),
    ("N2", "g3", 0, 330), ("N3", "g3", 330, 900),
    ("M6", "g4", 0, 255), ("N4", "g4", 255, 460), ("N12", "g4", 460, 638), ("N5", "g4", 638, 900),
    ("N6", "g5a", 0, None), ("N7", "g5b", 0, None), ("N13", "g5c", 0, None),
    ("N9", "g6r2", 0, 480), ("N10", "g8", 0, None), ("N11", "g6r2", 480, 900),
    ("M13", "g7", 419, None),
]
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def frames(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_read_packets", "-of", "csv=p=0", str(p)], capture_output=True, text=True, check=True)
    return int(out.stdout.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", type=Path, default=Path("/tmp/ilag-wan3/clips"))
    ap.add_argument("--out", type=Path, default=Path("/tmp/ilag-wan3/assembly"))
    ap.add_argument("--name", default="ILAG-Wan3-assembly-1")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(dir=a.out))
    parts, labels, t = [], [], 0.0
    for i, (shot, clip, f0, f1) in enumerate(SEGMENTS):
        src = a.clips / f"{clip}.mp4"
        f1 = f1 if f1 is not None else frames(src)
        n = f1 - f0
        part = tmp / f"{i:02d}-{shot}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{f0 / FPS:.4f}", "-i", str(src), "-frames:v", str(n),
                        "-t", f"{n / FPS:.4f}", "-vf", "scale=1920:1080:flags=lanczos,fps=30,format=yuv420p",
                        "-af", "aresample=48000,apad", "-ac", "2", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                        "-c:a", "aac", "-b:a", "192k", "-shortest", str(part)], check=True)
        parts.append(part)
        labels.append((shot, clip, t, t + n / FPS))
        print(f"{shot:4s} {clip:5s} {t:7.2f}s  +{n / FPS:5.2f}s", flush=True)
        t += n / FPS
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    clean = a.out / f"{a.name}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                    "-movflags", "+faststart", str(clean)], check=True)
    draw = ",".join(
        f"drawtext=fontfile={FONT}:text='{shot}  {clip}':x=36:y=30:fontsize=38:fontcolor=white:box=1:"
        f"boxcolor=black@0.55:boxborderw=12:enable='between(t,{s:.3f},{e - 0.001:.3f})'"
        for shot, clip, s, e in labels)
    labeled = a.out / f"{a.name}-labeled.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(clean), "-vf", draw, "-c:v", "libx264", "-preset",
                    "medium", "-crf", "20", "-c:a", "copy", "-movflags", "+faststart", str(labeled)], check=True)
    print(f"total {t:.2f}s -> {clean} + {labeled}")


if __name__ == "__main__":
    main()
