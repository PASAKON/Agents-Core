#!/usr/bin/env python3
"""The ILAG lakorn channel theme: navy + gold, approved by the CEO on 2026-09-28 for the Page
«ละครสั้นคุณธรรม by ILAG Studio» ("KEEP Theme ไว้ … ทั้งโปสเตอร์และ Card ที่แสดงบน Video … รวมถึง Font
และการจัดวางด้วย"). Everything that decides the look lives in this file, so a worker cannot drift from it.
Skill: .claude/skills/CTO_ILAG_LakornTheme/SKILL.md

  ilag_theme.py poster-job <spec.json> <job.json>   write the ChatGPT job for one "รู้หรือไม่?" poster
  ilag_theme.py logo <chatgpt.png> <out.png>         paste the Page logo into the poster's empty circle, 1080x1350
  ilag_theme.py story --film F --start S --dur D --title T --question Q <out.mp4>
                                                     cut a Story clip and burn the end card on its last 5 s

poster spec: {"name": "know-ep4-k1", "attach": "<cast sheet>", "character": "...", "scene": "...",
              "sub": "...", "points": ["...", "...", "..."], "tip": "...", "title": "ขายฝากนาแม่"}
then: tools/chatgpt_images.py --cdp-url http://127.0.0.1:9223 --json <job.json> --out <dir> --timeout-s 600"""
import argparse, json, re, subprocess, sys, urllib.request
from pathlib import Path

PAGE_NAME = "ละครสั้นคุณธรรม by ILAG Studio"
PAGE_URL = "https://www.facebook.com/61594116376333"

# Colours measured off the approved poster (know-ep4-full.png) and the approved Story card, 2026-09-28.
NAVY = "#0A1A38"                                  # poster panel (#061835 top, #0E1B3C at the edges)
GOLD = "#F7C64E"                                  # tip box and number discs (#F6C048..#F9CD57)
GOLD_METAL = ("#E49C1D", "#F7C440", "#FDE165")    # headline gradient: shadow, body, highlight
CARD_BG = (12, 13, 30, 225)                       # Story card box, #0C0D1E at 88 %
CARD_GOLD = (246, 196, 83)                        # #F6C453, card line 1
CARD_WHITE = (255, 255, 255)                      # card line 2, the Page name
CARD_CREAM = (255, 244, 214)                      # #FFF4D6, card line 3, the question
SUK = "/System/Library/Fonts/SukhumvitSet.ttc"    # face 5 Bold, face 4 Semi Bold. The Kanit woff2 in the repo is a
                                                  # Thai subset with no "?", digits or Latin: it prints boxes.

# The approved prompt (round1.json know-ep4-full, 2026-09-28) with the parts of the approved output that the
# prompt left to chance written in: navy panel, rice-ear ornaments, gold rule, gold number discs, full-width
# tip box, dusk rice-field footer, vertical divider. The rest is word for word.
POSTER_PROMPT = """Design a complete Thai public-education poster for Facebook, vertical 4:5, in a warm premium style (like a Thai TV-drama key-art card crossed with a clean infographic).

Image: use ONLY {column} of the attached reference sheet, {character}. Keep the face exactly as in the sheet. {scene} Place the character in the top 40% of the poster.

Below, a clean dark-indigo navy panel (#0A1A38) with thin golden rice-ear ornaments at its left and right edges, and this Thai text, EXACTLY as written, character for character, every vowel and tone mark included. Use a bold modern Thai sans-serif typeface.

Headline, very large, metallic gold, centred:
รู้หรือไม่?

Sub-headline, white, centred, with a thin gold line under it:
{sub}

Three numbered points, white, medium size, left-aligned, each number in a gold circle:
1. {p1}
2. {p2}
3. {p3}

One highlighted tip line, navy text in a rounded gold box across the full width:
{tip}

Footer strip at the very bottom, under a thin gold line, over a dim dusk rice-field silhouette (dark trees, last orange light), small white text on the left, two lines:
ดูละครสั้น «{title}» ได้ที่เพจ
{page}
then a thin vertical gold divider, and on the right an EMPTY plain white circle (no drawing inside) about 12% of the poster width, reserved for a logo.

No other words at all: no English except the page name, no signature, no watermark. No banknotes, no coins, no documents, no government emblems, no Garuda, no children."""


def poster_job(spec_path, job_path):
    s = json.loads(Path(spec_path).read_text())
    if len(s["points"]) != 3:
        sys.exit("the theme has exactly 3 points")
    prompt = POSTER_PROMPT.format(column=s.get("column", "column 1"), character=s["character"], scene=s["scene"],
                                  sub=s["sub"], p1=s["points"][0], p2=s["points"][1], p3=s["points"][2],
                                  tip=s["tip"], title=s["title"], page=PAGE_NAME)
    job = {"name": s["name"], "prompt": prompt}
    if s.get("attach"):
        job["attach"] = s["attach"]
    Path(job_path).write_text(json.dumps([job], ensure_ascii=False, indent=1))
    print(f"wrote {job_path}. After ChatGPT: check every Thai word against the spec, then run `logo`.")


def page_logo(cache=Path.home() / ".cache/ilag/page-logo.jpg"):
    """The Page's current profile picture, taken from og:image of the public Page. The Graph /picture endpoint
    returns the grey default silhouette for this Page (measured 2026-09-28), so it is not used."""
    try:
        req = urllib.request.Request(PAGE_URL, headers={"User-Agent": "facebookexternalhit/1.1"})
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
        url = re.search(r'<meta property="og:image" content="([^"]+)"', html)[1].replace("&amp;", "&")
        data = urllib.request.urlopen(url, timeout=20).read()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(data)
    except Exception as e:  # noqa: BLE001 — fall back to the last good copy, and say so
        if not cache.exists():
            sys.exit(f"cannot fetch the Page logo ({e}) and no cached copy at {cache}")
        print(f"WARNING: Page logo fetch failed ({e}); using the cached {cache}")
    return cache


def _run(v, i):
    """The contiguous non-zero run of v around index i."""
    lo = hi = i
    while lo > 0 and v[lo - 1]:
        lo -= 1
    while hi < len(v) - 1 and v[hi + 1]:
        hi += 1
    return lo, hi


def logo(src, out):
    import numpy as np
    from PIL import Image, ImageDraw
    im = Image.open(src).convert("RGB")
    w, h = im.size
    if abs(w / h - 0.8) > 0.02:
        sys.exit(f"poster is {w}x{h}, not 4:5: ask ChatGPT again for 4:5")
    a = np.asarray(im)
    y0, x0 = int(h * 0.86), int(w * 0.5)
    m = (a[y0:, x0:] > 228).all(axis=2)                # near-white in the footer, right half
    col = m.sum(axis=0)
    if col.max() < 0.04 * w:
        sys.exit("no empty white circle in the footer: ask ChatGPT again for the circle")
    cx0, cx1 = _run(col, int(col.argmax()))            # the circle is the tallest white column block
    row = m[:, cx0:cx1 + 1].sum(axis=1)
    cy0, cy1 = _run(row, int(row.argmax()))
    bw, bh = cx1 - cx0 + 1, cy1 - cy0 + 1
    if abs(bw - bh) > 6 or not 0.06 * w < bw < 0.2 * w:
        sys.exit(f"white shape in the footer is {bw}x{bh}, not the logo circle: check the poster by eye")
    d = min(bw, bh) + 2
    lg = Image.open(page_logo()).convert("RGB").resize((d, d), Image.LANCZOS)
    mask = Image.new("L", (d, d))
    ImageDraw.Draw(mask).ellipse((0, 0, d - 1, d - 1), fill=255)
    cx, cy = x0 + (cx0 + cx1) // 2, y0 + (cy0 + cy1) // 2
    im.paste(lg, (cx - d // 2, cy - d // 2), mask)
    im.resize((1080, 1350), Image.LANCZOS).save(out)
    print(f"saved {out} 1080x1350, logo circle {bw}x{bh} centred at ({cx},{cy}) of {w}x{h}")


def story(a):
    from PIL import Image, ImageDraw, ImageFont
    if not 15 <= a.dur <= 30:
        sys.exit("a Story is 15-30 s")
    f = lambda size, face=5: ImageFont.truetype(SUK, size, index=face, layout_engine=ImageFont.Layout.RAQM)
    W, H, y = 1080, 1920, 1440
    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((60, y, W - 60, y + 300), radius=28, fill=CARD_BG)
    d.text((W // 2, y + 80), f"ดูเต็มเรื่อง «{a.title}»", font=f(60), fill=CARD_GOLD, anchor="mm")
    d.text((W // 2, y + 170), f"ที่เพจ {PAGE_NAME}", font=f(44, 4), fill=CARD_WHITE, anchor="mm")
    d.text((W // 2, y + 240), a.question, font=f(40, 4), fill=CARD_CREAM, anchor="mm")
    for text, font in ((f"ดูเต็มเรื่อง «{a.title}»", f(60)), (a.question, f(40, 4))):
        if d.textlength(text, font=font) > W - 160:
            sys.exit(f"card line too long for the box, shorten it: {text}")
    png = Path(a.out).with_suffix(".card.png")
    card.save(png)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(a.start), "-t", str(a.dur), "-i", a.film, "-i", str(png),
                    "-filter_complex", f"[0:v]scale={W}:{H},setsar=1[b];[b][1:v]overlay=0:0:enable='gte(t,{a.dur - 5})'[v]",
                    "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-crf", "20", "-preset", "medium",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", a.out], check=True)
    print(f"saved {a.out} ({a.dur:g} s, end card from {a.dur - 5:g} s)")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    j = sub.add_parser("poster-job")
    j.add_argument("spec"); j.add_argument("job")
    lo = sub.add_parser("logo")
    lo.add_argument("src"); lo.add_argument("out")
    s = sub.add_parser("story")
    s.add_argument("--film", required=True); s.add_argument("--start", type=float, required=True)
    s.add_argument("--dur", type=float, required=True); s.add_argument("--title", required=True)
    s.add_argument("--question", required=True); s.add_argument("out")
    a = p.parse_args()
    {"poster-job": lambda: poster_job(a.spec, a.job), "logo": lambda: logo(a.src, a.out), "story": lambda: story(a)}[a.cmd]()


if __name__ == "__main__":
    main()
