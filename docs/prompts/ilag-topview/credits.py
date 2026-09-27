"""End credits for the ILAG TopView trailer, rolled up on black the way «Sorry, Sir» was (CEO 2026-09-27).

    python3 credits.py --title "TITLE" [--editor PASAKON] [--track "Glass Bloom" ...] [--out DIR] [--png-only]

Writes <out>/credits.png (the whole roll as one tall strip) and <out>/ILAG-Credits-4K.mp4.

«Sorry, Sir» (Drive: Sorry, Sir/Final Draft/Sorry sir THE VALDER - End Credits v2.mp4), measured 2026-09-27 because
its credits.py and render_smooth.sh died with a session scratchpad on 16 Sep:
  - pure black, a continuous roll-up, no fades, no music under it (the film is silent from the first line to the last);
  - 72 px/s at 1280x720 = 10% of the frame height per second, rendered at 2x and 144 fps, 1 px per frame, tmix over
    6 frames (a 1/24 s shutter) then 24 fps: v1 moved 2 and 4 px on alternate frames and the CEO called it not smooth;
  - DejaVu Sans Bold / Book, no letter-spacing; white #FAF9F6, grey #B4B3B1; roles right-aligned 26 px left of the
    centre, names and list items left-aligned 26 px right of it, headings centred (sizes below in 720p pixels).
Here the canvas is the delivery size itself (3840x2160, so the text is sharp at 4K), 1 px per frame at 210 fps
(9.7% of the height per second), tmix over 7 frames (a 1/30 s shutter), 30 fps out: an even 7 px every frame.
A 38-s roll took 22 min on Contabo's 4 cores (2026-09-27).
"""
import argparse, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# 210 fps, not 216: 216/30 = 7.2 px per output frame came out as 7.3/6.7/8.0 steps (measured on the test roll,
# 2026-09-27); 210/30 = 7 px every frame exactly, like «Sorry, Sir»'s 144/24 = 6. 9.7% of the height per second.
W, H, FPS_IN, FPS_OUT, BLUR = 3840, 2160, 210, 30, 7
K = H / 720  # sizes and gaps are «Sorry, Sir»'s 720p measurements
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
BOOK = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
WHITE, GREY = (0xFA, 0xF9, 0xF6), (0xB4, 0xB3, 0xB1)
STYLE = {  # name: (font file, 720p size, colour)
    "title": (BOLD, 33, WHITE), "name": (BOLD, 21, WHITE), "head": (BOLD, 19, GREY),
    "role": (BOOK, 19, GREY), "small": (BOOK, 16, GREY), "year": (BOOK, 15, GREY),
}
ITEM, ROW, GROUP, AFTER_HEAD, GUTTER = 34, 78, 132, 54, 26  # 720p gaps between baselines-to-tops, as measured


# The twelve Flow Music tracks (docs/promo/topview-trailer/MUSIC-LEDGER.json); CEO 2026-09-27: "คิดว่าใช้หมดเลย".
TRACKS = ["Glass Bloom", "First Contact", "Deep Bloom", "Rising Light", "The Awakening", "Something Vast",
          "Something Breathes", "The Deep Opens", "Wake and Ride", "Into the Current", "Momentum", "Through the Storm"]


def blocks(a):
    tracks = TRACKS if a.all_tracks else (a.track or [])
    music = ([("head", "ORIGINAL MUSIC"), ("list", tracks), ("role", "Generated with", ["Google Flow Music"])]
             if tracks else [("role", "Music generated with", ["Google Flow Music"])])
    return [
        ("center", "ILAG STUDIO", "head"), ("space", 22), ("center", a.title, "title"),
        *([("space", 14), ("center", a.subtitle, "small")] if a.subtitle else []),
        ("group",),
        ("role", "Written and Directed by", ["PASAKON"]),
        ("role", "Edited by", [a.editor]),
        ("role", "AI Agent", ["Claude Code"]),
        ("group",), *music,
        ("group",), ("head", "GENERATED ON"), ("list", ["TOPVIEW"]),
        # TopView Terms: the video must be made with Wan3 on TopView and "Content generated with other models does not
        # count" — so MODELS names what each tool made, and MiniMax H3 appears only as the previz it was.
        ("group",), ("head", "MODELS"),
        ("role", "Every shot", ["Wan 3.0"]), ("role", "Reference plates", ["GPT Image (ChatGPT)"]),
        ("role", "Music", ["Google Flow Music"]),
        ("group",),
        ("role", "Previsualisation", ["MiniMax H3"]),
        ("role", "Editing", ["CapCut"]),
        *([("role", "Colour", a.colour)] if a.colour else []),  # CEO 2026-09-27: "รอ Grading สี"
        ("group",), ("head", "MADE FOR"), ("list", ["TOPVIEW WAN3 CHALLENGE"]), ("space", 6), ("center", "2026", "year"),
        ("group",), ("center", "Every frame was generated. Nothing was filmed.", "small"),
        ("group",), ("center", "ILAG STUDIO", "head"),
    ]


def font(style):
    f, size, colour = STYLE[style]
    return ImageFont.truetype(f, round(size * K)), colour


def layout(bl):
    """Each drawable as (y, anchor, x, text, style); y grows down from 0. Returns items and the content height."""
    items, y, cx, g = [], 0.0, W / 2, GUTTER * K
    last = None
    for b in bl:
        kind = b[0]
        if kind == "space":
            y += b[1] * K
        elif kind == "group":
            y += GROUP * K - ITEM * K
        elif kind == "center":
            items.append((y, "mt", cx, b[1], b[2])); y += ITEM * K
        elif kind == "head":
            items.append((y, "mt", cx, b[1], "head")); y += AFTER_HEAD * K
        elif kind == "list":  # «Sorry, Sir»: the heading is centred, its items sit in the names column
            for t in b[1]:
                items.append((y, "lt", cx + g, t, "name")); y += ITEM * K
        elif kind == "role":
            if last == "role":
                y += (ROW - ITEM) * K
            items.append((y, "rt", cx - g, b[1], "role"))
            for t in b[2]:
                items.append((y, "lt", cx + g, t, "name")); y += ITEM * K
        last = kind
    return items, round(y)


def render_png(bl, path):
    items, content_h = layout(bl)
    top, bottom = round(0.23 * H), round(0.23 * H)  # «Sorry, Sir»: 2.3 s of black before the first line and after the last
    img = Image.new("RGB", (W, top + content_h + bottom), (0, 0, 0))
    d = ImageDraw.Draw(img)
    for y, anchor, x, text, style in items:
        f, colour = font(style)
        d.text((x, top + y), text, font=f, fill=colour, anchor=anchor)
    img.save(path)
    return img.height


def render_mp4(png, strip_h, path):
    frames = H + strip_h  # from the strip's top at the bottom edge to its bottom past the top edge, 1 px a frame
    seconds = frames / FPS_IN
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={FPS_IN}",
        "-loop", "1", "-framerate", str(FPS_IN), "-i", str(png),
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-filter_complex", f"[0:v][1:v]overlay=x=(W-w)/2:y='H-n':shortest=0,tmix=frames={BLUR},fps={FPS_OUT},"
                           "format=yuv420p[v]",
        "-map", "[v]", "-map", "2:a", "-t", f"{seconds:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "16",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(path)], check=True)
    return seconds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--editor", default="PASAKON")
    ap.add_argument("--track", action="append", help="a music title as it should read; repeat for each")
    ap.add_argument("--all-tracks", action="store_true", help="list all twelve TRACKS")
    ap.add_argument("--out", type=Path, default=Path("/tmp/ilag-credits"))
    ap.add_argument("--colour", action="append", help="what the grade was done with, one per line; repeat")
    ap.add_argument("--png-only", action="store_true")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    png = a.out / "credits.png"
    strip_h = render_png(blocks(a), png)
    print(f"{png} {W}x{strip_h}, roll {(H + strip_h) / FPS_IN:.1f} s at {FPS_IN} px/s")
    if not a.png_only:
        s = render_mp4(png, strip_h, a.out / "ILAG-Credits-4K.mp4")
        print(f"{a.out / 'ILAG-Credits-4K.mp4'} {s:.1f} s")


if __name__ == "__main__":
    main()
