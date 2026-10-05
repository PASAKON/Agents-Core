#!/usr/bin/env python3
"""Writes render-meta.json (arm B) and armA/render-meta.json from the finished finals and their gate logs (task-3ae66e7a)."""
import json
import os
import re
import subprocess
from pathlib import Path

W = Path("/opt/MoonieXHQ/Work/bl-ep60")
P = Path(__file__).resolve().parent


def probe(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_frames,codec_name,width,height,r_frame_rate", "-show_entries", "format=duration",
                        "-of", "json", str(f)], capture_output=True, text=True).stdout
    return json.loads(r)


def lufs(f):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(f), "-af", "loudnorm=I=-15.0:TP=-1.0:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL).stderr
    return float(re.search(r'"input_i"\s*:\s*"(-?[\d.]+)"', r).group(1))


def modes(beats):
    m = {}
    for b in beats:
        m[b["mode"]] = m.get(b["mode"], 0) + 1
    return m


def main():
    bb = json.loads((P / "beats.json").read_text())
    ba = json.loads((P / "armA/beats.json").read_text())["beats"]
    for arm, C, name, beats, sheet in (("B", W / "cut/v1", "final-ep60-v1.mp4", bb, "sheet-ep60-v1.jpg"),
                                       ("A", W / "armA/v1", "final-ep60-armA-v1.mp4", ba, "sheet-ep60-armA-v1.jpg")):
        f = C / name
        pr = probe(f)
        ck = json.loads((C / f"checker-{arm}.json").read_text())
        txt = (C / f"merge-{arm}.log").read_text()
        mg = json.JSONDecoder().raw_decode(txt)[0]
        vt = (C / f"verify-{arm}.log").read_text()
        s = pr["streams"][0]
        meta = {"task": "task-3ae66e7a", "episode": "BL EP60 GB (Goldenburg) ยังมีใบอนุญาตอยู่ไหม", "arm": arm, "final": str(f),
                "sheet": str(C / sheet), "bytes": os.path.getsize(f), "duration_s": round(float(pr["format"]["duration"]), 2),
                "fps": s["r_frame_rate"], "size": f'{s["width"]}x{s["height"]}', "frames": int(s["nb_read_frames"]),
                "video_codec": s["codec_name"], "loudness_lufs": lufs(f), "modes": modes(beats), "beats": len(beats), "windows": 12,
                "window_render": "tools/bl_compose.py --t0/--t-max" + (" via prototypes/bl-ep60/armA/render_window.py" if arm == "A" else "")
                                 + ", frame-aligned, merged with tools/bl_merge.py --beats against audio-hq-decoded.wav",
                "verify": "VERIFY PASSED" if "VERIFY PASSED" in vt else "FAILED", "checker_pass": ck["pass"],
                "brand_mark": ck["brand_mark"], "checker": {k: v for k, v in ck.items() if k not in ("brand_mark", "face_box_beats")},
                "merge_gates": mg["gates"], "part_frame_counts": mg["part_frame_counts"]}
        out = P / ("armA/render-meta.json" if arm == "A" else "render-meta.json")
        out.write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n")
        print(arm, meta["frames"], meta["loudness_lufs"], meta["modes"], meta["verify"], meta["checker_pass"],
              meta["brand_mark"]["min_ratio"], meta["brand_mark"]["min_time"])


if __name__ == "__main__":
    main()
