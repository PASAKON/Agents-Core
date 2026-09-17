# -*- coding: utf-8 -*-
"""Render an .srt file to a transparent ProRes4444 alpha .mov overlay,
sized/timed to match a given source video. Used because this machine's
ffmpeg build has no libass/drawtext (checked 2026-09-17) so the usual
`subtitles=` filter is unavailable — PIL draws the glyphs instead, exactly
like reel-editor-th's render_captions.py does for its karaoke captions.

Usage: python3 render_subs_overlay.py <video.mp4> <subs.srt> <overlay.mov>

Reusable for the next episode: point it at any video + .srt pair.
"""
import sys, os, re, subprocess, json
from PIL import Image, ImageDraw, ImageFont

SUKHUMVIT = "/System/Library/Fonts/Supplemental/SukhumvitSet.ttc"
BOLD_IDX = 5  # SukhumvitSet.ttc face index for Bold

_font_cache = {}
def font(size):
    if size not in _font_cache:
        _font_cache[size] = ImageFont.truetype(SUKHUMVIT, size, index=BOLD_IDX)
    return _font_cache[size]

def probe(video):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate",
        "-show_entries", "format=duration",
        "-of", "json", video
    ])
    d = json.loads(out)
    w = int(d["streams"][0]["width"])
    h = int(d["streams"][0]["height"])
    num, den = d["streams"][0]["r_frame_rate"].split("/")
    fps = float(num) / float(den)
    dur = float(d["format"]["duration"])
    return w, h, fps, dur

def parse_srt(path):
    text = open(path, encoding="utf-8").read().strip()
    blocks = re.split(r"\n\s*\n", text)
    tc_re = re.compile(
        r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*"
        r"(\d{2}):(\d{2}):(\d{2}),(\d{3})"
    )
    def to_sec(h, m, s, ms):
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0
    cues = []
    for b in blocks:
        lines = [l for l in b.splitlines() if l.strip() != ""]
        if len(lines) < 2:
            continue
        idx = 0 if tc_re.search(lines[0]) else 1
        m = tc_re.search(lines[idx])
        if not m:
            continue
        start = to_sec(*m.group(1, 2, 3, 4))
        end = to_sec(*m.group(5, 6, 7, 8))
        body = "\n".join(lines[idx + 1:]).strip()
        cues.append((start, end, body))
    return cues

def wrap_to_width(s, size, max_w):
    """Shrink font size until s fits max_w on one line; if still too wide
    at the floor size, split into 2 lines at the nearest midpoint."""
    f = font(size)
    while size > 28 and f.getlength(s) > max_w:
        size -= 2
        f = font(size)
    if f.getlength(s) <= max_w:
        return [s], size
    mid = len(s) // 2
    return [s[:mid], s[mid:]], size

def draw_cue_frame(w, h, lines, size):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font(size)
    line_h = int(size * 1.35)
    pad_x, pad_y = 28, 14
    widths = [f.getlength(l) for l in lines]
    block_w = max(widths) if widths else 0
    block_h = line_h * len(lines)
    safe_bottom = int(h * 0.20)  # keep clear of IG bottom UI zone
    y0 = h - safe_bottom - block_h
    box = [
        w / 2 - block_w / 2 - pad_x,
        y0 - pad_y,
        w / 2 + block_w / 2 + pad_x,
        y0 + block_h + pad_y,
    ]
    d.rounded_rectangle(box, radius=14, fill=(0, 0, 0, 140))
    y = y0
    for line, lw in zip(lines, widths):
        x = w / 2 - lw / 2
        ow = 4
        for dx in range(-ow, ow + 1, 2):
            for dy in range(-ow, ow + 1, 2):
                if dx * dx + dy * dy <= ow * ow:
                    d.text((x + dx, y + dy), line, font=f, fill=(0, 0, 0, 255))
        d.text((x, y), line, font=f, fill=(255, 255, 255, 255))
        y += line_h
    return img

def main(video, srt, out_path):
    w, h, fps, dur = probe(video)
    cues = parse_srt(srt)
    max_w = int(w * 0.86)
    base_size = int(h * 0.052)

    rendered = {}
    for start, end, body in cues:
        lines, size = wrap_to_width(body, base_size, max_w)
        rendered[(start, end)] = draw_cue_frame(w, h, lines, size)

    n = int(round(dur * fps))
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
        "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
        out_path
    ], stdin=subprocess.PIPE)

    blank = Image.new("RGBA", (w, h), (0, 0, 0, 0)).tobytes()
    for i in range(n):
        t = i / fps
        frame_bytes = blank
        for (start, end), img in rendered.items():
            if start <= t < end:
                frame_bytes = img.tobytes()
                break
        ff.stdin.write(frame_bytes)
        if i % 200 == 0:
            print(f"  overlay: {i}/{n} frames")
    ff.stdin.close()
    rc = ff.wait()
    print(f"done overlay -> {out_path} rc={rc}")
    return rc

if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3]))
