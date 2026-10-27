#!/usr/bin/env python3
"""The ILAG lakorn channel theme: gold, white and black, ruled by the CEO on 2026-10-26 for the Page
"ละครสั้นคุณธรรม by ILAG Studio" (gold for type, borders and cut points; black and white for the grounds, the
good side on white and the evil side on black, like the two halves of the lotus in the Page logo). It replaced
the navy + gold of 2026-09-28. Everything that decides the look lives in this file, so a worker cannot drift
from it. Skill: .claude/skills/CTO_ILAG_LakornTheme/SKILL.md, palette: knowledge/brand-knowledge/brands/ilag/BRAND.md

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

# Palette v2, CEO 2026-10-26 (BRAND.md, Palette v2).
# v1 (2026-09-28, navy + gold) drew NAVY #0A1A38, CARD_CREAM #FFF4D6, CARD_BG #0C0D1E at 88 %, CARD_GOLD #F6C453 and
# STAMP_RED #B8322A. None of them is drawn any more; they are named here only so an old render can be traced.
BLACK = "#0A0A0A"                                 # LOCKED. the evil side: card grounds, plates, the poster panel
WHITE = "#FFFFFF"                                 # LOCKED. the good side: the good character's card, the lesson plate
GOLD = "#F7C64E"                                  # LOCKED. flat gold: borders, rules, tags, pills, small text, number badges
GOLD_METAL = ("#FDE165", "#F7C440", "#E49C1D")    # LOCKED. gold display type, top to bottom (v1 listed it bottom to top)
STAMP_GOLD = "#E8B230"                            # PROPOSED. stamp ink on black; no render path of this tool draws a stamp
INK = "#111111"                                   # PROPOSED. text on white and on gold
MIST = "#C9C9C9"                                  # PROPOSED. second lines on black
SUK = "/System/Library/Fonts/SukhumvitSet.ttc"    # face 5 Bold, face 4 Semi Bold. The Kanit woff2 in the repo is a
                                                  # Thai subset with no "?", digits or Latin: it prints boxes.
KIT_FONTS = Path(__file__).resolve().parent.parent / "knowledge/brand-knowledge/brands/ilag/templates/fonts"

# The approved prompt (round1.json know-ep4-full, 2026-09-28) with the parts of the approved output that the
# prompt left to chance written in: rice-ear ornaments, gold rule, gold number discs, full-width tip box,
# rice-field footer, vertical divider. The colours are the v2 tokens above. The rest is word for word.
# The v2 version has not been fired yet (n=0).
POSTER_PROMPT = """Design a complete Thai public-education poster for Facebook, vertical 4:5, in a warm premium style (like a Thai TV-drama key-art card crossed with a clean infographic).

Image: use ONLY {column} of the attached reference sheet, {character}. Keep the face exactly as in the sheet. {scene} Place the character in the top 40% of the poster.

Below, a clean pure black panel ({black}) with thin golden ({gold}) rice-ear ornaments at its left and right edges, and this Thai text, EXACTLY as written, character for character, every vowel and tone mark included. Use a bold modern Thai sans-serif typeface.

Headline, very large, metallic gold gradient running top to bottom from {metal_top} through {metal_mid} to {metal_low}, centred:
รู้หรือไม่?

Sub-headline, white ({white}), centred, with a thin flat gold ({gold}) line under it:
{sub}

Three numbered points, white, medium size, left-aligned, each number a near-black ({ink}) digit in a flat gold ({gold}) circle:
1. {p1}
2. {p2}
3. {p3}

One highlighted tip line, near-black ({ink}) text in a rounded flat gold ({gold}) box across the full width:
{tip}

Footer strip at the very bottom, under a thin gold line, over a dim rice-field silhouette in black and charcoal (dark trees, a last thin line of gold light), small white text on the left, two lines:
ดูละครสั้น "{title}" ได้ที่เพจ
{page}
then a thin vertical gold divider, and on the right an EMPTY plain white circle (no drawing inside) about 12% of the poster width, reserved for a logo.

Colours: only black, white and gold.

No other words at all: no English except the page name, no signature, no watermark. No banknotes, no coins, no documents, no government emblems, no Garuda, no children."""


def poster_job(spec_path, job_path):
    s = json.loads(Path(spec_path).read_text())
    if len(s["points"]) != 3:
        sys.exit("the theme has exactly 3 points")
    prompt = POSTER_PROMPT.format(column=s.get("column", "column 1"), character=s["character"], scene=s["scene"],
                                  sub=s["sub"], p1=s["points"][0], p2=s["points"][1], p3=s["points"][2],
                                  tip=s["tip"], title=s["title"], page=PAGE_NAME,
                                  black=BLACK, white=WHITE, gold=GOLD, ink=INK,
                                  metal_top=GOLD_METAL[0], metal_mid=GOLD_METAL[1], metal_low=GOLD_METAL[2])
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
    except Exception as e:  # noqa: BLE001 (fall back to the last good copy, and say so)
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


def _font(size, face=5):
    """Sukhumvit Set where it exists (the Mac). Contabo and winbox have none, so the kit's OFL Taviraj stands in,
    Bold for face 5 and Semi Bold for face 4."""
    from PIL import ImageFont
    if Path(SUK).exists():
        return ImageFont.truetype(SUK, size, index=face, layout_engine=ImageFont.Layout.RAQM)
    taviraj = KIT_FONTS / ("Taviraj-Bold.ttf" if face == 5 else "Taviraj-SemiBold.ttf")
    return ImageFont.truetype(str(taviraj), size, layout_engine=ImageFont.Layout.RAQM)


def card_image(title, question):
    """The Story end card, 1080x1920 RGBA, transparent outside the plate: BLACK ground, GOLD line 1, WHITE line 2,
    MIST line 3."""
    from PIL import Image, ImageDraw
    W, H, y = 1080, 1920, 1440
    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((60, y, W - 60, y + 300), radius=28, fill=BLACK)
    line1 = f'ดูเต็มเรื่อง "{title}"'
    d.text((W // 2, y + 80), line1, font=_font(60), fill=GOLD, anchor="mm")
    d.text((W // 2, y + 170), f"ที่เพจ {PAGE_NAME}", font=_font(44, 4), fill=WHITE, anchor="mm")
    d.text((W // 2, y + 240), question, font=_font(40, 4), fill=MIST, anchor="mm")
    for text, font in ((line1, _font(60)), (question, _font(40, 4))):
        if d.textlength(text, font=font) > W - 160:
            sys.exit(f"card line too long for the box, shorten it: {text}")
    return card


def story(a):
    if not 15 <= a.dur <= 30:
        sys.exit("a Story is 15-30 s")
    W, H = 1080, 1920
    png = Path(a.out).with_suffix(".card.png")
    card_image(a.title, a.question).save(png)
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
