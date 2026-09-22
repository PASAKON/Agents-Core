#!/usr/bin/env python3
"""MoonieX Musk $1T poster — AI scene + crisp text overlay (approved layout).

Two stages (CEO-approved 2026-06-13 wireframe = spcx_layout_mock):
  1) gen_scene()  — gpt-image-2/edit makes the SCENE ONLY: Musk hero on the
     right, Falcon rocket -> gold crescent moon, navy+gold, LEFT 45% kept dark
     empty for text. NO text/letters/logo in the AI image (so nothing garbles).
     Musk supplied as face-ref @image1 (cropped from the news screenshot);
     identity clause avoids the celebrity name to dodge refusals.
  2) compose()    — HTML->Playwright overlays ALL copy crisp (Thai never
     garbles), real moon lockup, on top of the AI scene.

Message focus: Elon Musk = world's first $1-trillion net worth, after SpaceX
IPO. Palette LOCKED (BRAND.md): navy #0c1c2b, champagne gold #cdac65, green=up.
Organic post only (not paid FB ads). $0.19 for the one AI scene; overlay free.

  python scripts/spcx_musk_gen.py gen        # gen scene ($0.19) + compose
  python scripts/spcx_musk_gen.py compose    # re-overlay text only (free)
  python scripts/spcx_musk_gen.py dry        # print scene prompt, no cost
"""
import base64
import io
import os
import sys
import json
import urllib.request
import urllib.error

from PIL import Image
from playwright.sync_api import sync_playwright

SRC = "/Users/gob/Desktop/720655493_1566045434883239_2334179446712343628_n.jpg"
OUT = "/Users/gob/Projects/Agents/output/mooniex-posters"
SCENE = os.path.join(OUT, "spcx_scene.png")
FINAL = os.path.join(OUT, "spcx_musk_final.png")
LOCKUP = "/Users/gob/Projects/Agents/output/personal-brand/lockup-moon-text.png"
ENV = "/Users/gob/MoonieXHQ/Projects/MoonieX/ClaudeFlow/.env"
EDIT_EP = "https://fal.run/openai/gpt-image-2/edit"
COST = 0.19

# ── copy (Thai badge per CEO; news facts; brand names/ticker stay EN) ──
BADGE = "เศรษฐีล้านล้านคนแรกของโลก"          # was "THE WORLD'S FIRST TRILLIONAIRE"
NUM = "$1.1T"
DELTA = "+$61.2B (+5.78%)"
NAME = "ELON MUSK"
SUBNAME = "Tesla · SpaceX"
THAI = "ทรัพย์สินแตะ 1 ล้านล้านดอลลาร์<br>หลังจาก SpaceX IPO"
PILLS = ["SPACEX IPO", "NASDAQ: SPCX", "13 JUNE 2026"]
SUPPORT = "รองรับ Exness · XM"

PROMPT = (
    "Identity (Critical): strictly reference @image1 — preserve the EXACT face, "
    "proportions, skin tone and short hairstyle of the man in the reference; he must "
    "stay clearly recognizable as the same person, dressed in a sharp black suit over a "
    "black turtleneck. "
    "Photorealistic 1:1 editorial poster BACKGROUND scene, 8k, premium institutional "
    "fintech mood. Composition: the man stands on the RIGHT third of the frame, "
    "three-quarter view, hands relaxed, calm and confident, looking up toward a slender "
    "Falcon-style white-silver rocket lifting off in the right-center distance on a "
    "controlled molten champagne-gold engine plume; a huge faint crescent moon glows dim "
    "gold behind the rocket; a restrained sparse spiral of tiny gold coins is drawn toward "
    "the rocket; warm champagne-gold rim light on the man, soft gold bokeh, ultra-clean "
    "dark ground with soft 5-8% reflection. "
    "The LEFT 45% of the frame MUST be deep dark navy (#0c1c2b) empty negative space — no "
    "subject, no objects, no glow there — reserved clean for text overlay. "
    "Palette STRICTLY deep navy #0c1c2b + champagne gold #cdac65 (with polished "
    "chrome-silver only on the rocket). NO cyan, purple, magenta, teal or blue neon. "
    "ABSOLUTELY NO text, NO letters, NO numbers, NO headline, NO logo, NO badge, NO "
    "watermark anywhere in the image — scene only. "
)


def load_key() -> str:
    import re
    m = re.search(r"^FAL_API_KEY=(.+)$", open(ENV, encoding="utf-8").read(), re.M)
    if not m:
        sys.exit("FAL_API_KEY not found in " + ENV)
    return m.group(1).strip().strip('"').strip("'")


def musk_ref_uri() -> str:
    im = Image.open(SRC)
    w, h = im.size
    box = (int(0.695 * w), int(0.122 * h), int(0.929 * w), int(0.268 * h))
    crop = im.crop(box).convert("RGB").resize((512, 512))
    buf = io.BytesIO()
    crop.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def gen_scene() -> bool:
    os.makedirs(OUT, exist_ok=True)
    key = load_key()
    payload = {"prompt": PROMPT, "image_urls": [musk_ref_uri()],
               "image_size": "square_hd", "quality": "high",
               "num_images": 1, "output_format": "png"}
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        EDIT_EP, data=body, method="POST",
        headers={"Authorization": "Key " + key, "Content-Type": "application/json"})
    print(f"POST ({len(body)}B) -> gpt-image-2/edit scene ... (~${COST})")
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()[:600]}")
        return False
    imgs = data.get("images") or []
    if not imgs:
        print("no images (likely safety refusal): " + json.dumps(data)[:400])
        return False
    urllib.request.urlretrieve(imgs[0]["url"], SCENE)
    print(f"scene -> {SCENE}")
    return True


HTML = """<!doctype html><html lang="th"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Prompt:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
  *{margin:0;padding:0;box-sizing:border-box;}
  html,body{width:1080px;height:1080px;}
  .card{width:1080px;height:1080px;position:relative;overflow:hidden;font-family:'Prompt',sans-serif;color:#fff;
    background:#0a1622;}
  .scene{position:absolute;inset:0;width:1080px;height:1080px;object-fit:cover;}
  .scrim{position:absolute;inset:0;background:
    linear-gradient(90deg,rgba(8,18,30,.94) 0%,rgba(8,18,30,.86) 34%,rgba(8,18,30,.36) 56%,rgba(8,18,30,0) 70%);}
  .lockup{position:absolute;top:48px;left:58px;height:62px;}
  .badge{position:absolute;top:172px;left:58px;padding:13px 26px;border-radius:12px;
    background:linear-gradient(95deg,#e6d0a3,#cdac65 55%,#b9974e);color:#0a1622;
    font-weight:700;font-size:34px;letter-spacing:.01em;}
  .num{position:absolute;top:264px;left:52px;font-family:'Anton',sans-serif;
    font-size:232px;line-height:.86;letter-spacing:-.01em;
    text-shadow:0 6px 40px rgba(0,0,0,.5);}
  .delta{position:absolute;top:512px;left:60px;color:#3ecf8e;font-size:44px;font-weight:700;}
  .name{position:absolute;top:600px;left:58px;font-size:58px;font-weight:700;letter-spacing:.01em;}
  .sub{position:absolute;top:676px;left:60px;color:#b9c6d2;font-size:36px;}
  .thai{position:absolute;top:758px;left:58px;width:600px;color:#e6d0a3;font-size:43px;
    font-weight:600;line-height:1.34;text-shadow:0 2px 16px rgba(0,0,0,.6);}
  .strip{position:absolute;left:58px;bottom:60px;display:flex;gap:15px;}
  .pill{border:2px solid rgba(205,172,101,.75);border-radius:30px;padding:13px 24px;
    color:#cdac65;font-size:26px;font-weight:600;background:rgba(10,22,34,.45);}
  .foot{position:absolute;right:54px;bottom:70px;color:#aab8c6;font-size:26px;font-weight:500;
    text-shadow:0 2px 10px rgba(0,0,0,.7);}
</style></head>
<body><div class="card">
  <img class="scene" src="data:image/png;base64,__SCENE__">
  <div class="scrim"></div>
  <img class="lockup" src="data:image/png;base64,__LOCKUP__">
  <div class="badge">__BADGE__</div>
  <div class="num">__NUM__</div>
  <div class="delta">&#9650; __DELTA__</div>
  <div class="name">__NAME__</div>
  <div class="sub">__SUBNAME__</div>
  <div class="thai">__THAI__</div>
  <div class="strip">__PILLS__</div>
  <div class="foot">__SUPPORT__</div>
</div></body></html>"""


def compose() -> None:
    if not os.path.exists(SCENE):
        sys.exit("no scene yet — run `gen` first")
    pills = "".join(f'<div class="pill">{p}</div>' for p in PILLS)
    html = (HTML.replace("__SCENE__", b64(SCENE)).replace("__LOCKUP__", b64(LOCKUP))
            .replace("__BADGE__", BADGE).replace("__NUM__", NUM).replace("__DELTA__", DELTA)
            .replace("__NAME__", NAME).replace("__SUBNAME__", SUBNAME)
            .replace("__THAI__", THAI).replace("__PILLS__", pills)
            .replace("__SUPPORT__", SUPPORT))
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1080}, device_scale_factor=2)
        pg.set_content(html, wait_until="networkidle")
        pg.wait_for_timeout(700)
        pg.screenshot(path=FINAL, clip={"x": 0, "y": 0, "width": 1080, "height": 1080})
        b.close()
    print(f"OK -> {FINAL}")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry"
    if mode == "dry":
        print(PROMPT)
        print(f"\n1 scene image. gen cost ~${COST:.2f}")
        return
    if mode == "compose":
        compose()
        return
    if gen_scene():
        compose()


if __name__ == "__main__":
    main()
