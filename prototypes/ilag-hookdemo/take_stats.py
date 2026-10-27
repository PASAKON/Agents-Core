"""Numbers for REPORT.md (task-ee1dbcf0): per rendered take, voice end, lengths, LUFS, true peak and every hold under 0.8 s.

usage: take_stats.py <hookdemo dir> [take-name ...]     (default: every folder in out/v4)
LUFS and true peak are measured with ffmpeg ebur128 on the 720p and the 1080 master as delivered, not read from a plan.
Holds checked: each subtitle line (what is on screen as text), each spoken phrase, each cut.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

LIMIT = 0.8


def probe(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                                capture_output=True, text=True, check=True).stdout)


def loud(path):
    err = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    tail = err[err.rfind("Summary:"):]
    return (float(re.search(r"I:\s+(-?[\d.]+) LUFS", tail).group(1)), float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail).group(1)))


def main():
    hd = Path(sys.argv[1])
    root = hd / "out/v4"
    names = sys.argv[2:] or sorted(p.name for p in root.iterdir() if p.is_dir())
    for n in names:
        d = root / n
        t = json.loads((d / "timing.json").read_text(encoding="utf-8"))
        p720, mst = d / f"hook-{n}-720p.mp4", d / f"hook-{n}-master-1080.mp4"
        i720, tp720 = loud(p720)
        im, tpm = loud(mst)
        print(f"### {n}")
        print(f"voice end {t['voice_end_s']:.2f} s | montage {t['montage_end_s']:.2f} s | total {t['total_s']:.2f} s "
              f"(720p file {probe(p720):.2f} s, master {probe(mst):.2f} s) | 720p {p720.stat().st_size / 2**20:.1f} MiB, master {mst.stat().st_size / 2**20:.1f} MiB")
        print(f"LUFS 720p {i720} / master {im} | true peak 720p {tp720} dBTP / master {tpm} dBTP")
        short = [f"line {s['line']} {s['to'] - s['from']:.2f} s" for s in t["subs"] if s["to"] - s["from"] < LIMIT]
        print(f"subtitle holds under {LIMIT} s: {short or 'none'} (shortest {min(s['to'] - s['from'] for s in t['subs']):.2f} s)")
        ph = [f"{k} {v['text']} {v['end'] - v['start']:.2f} s" for k, v in t["phrase"].items() if v["end"] - v["start"] < LIMIT]
        print(f"spoken phrases under {LIMIT} s: {ph or 'none'}")
        cu = [f"cut {c['cut']} ({c['shot']}) {c['len']:.2f} s" for c in t["cuts"] if c["len"] < LIMIT]
        print(f"cuts under {LIMIT} s: {cu or 'none'} (shortest {min(c['len'] for c in t['cuts']):.2f} s, longest {max(c['len'] for c in t['cuts']):.2f} s)")


main()
