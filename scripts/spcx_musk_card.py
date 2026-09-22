#!/usr/bin/env python3
"""MoonieX trillionaire-card news poster (SpaceX IPO / Elon Musk $1T).

Newsjack of the iUX/Peace-of-Mind-Trader "World's First Trillionaire"
billionaire-index card. Brand-strict MANUAL composition (HTML -> Playwright),
NOT image-gen: gpt-image-2 refuses real faces + hallucinates hex. Real Musk
photo is cropped from the reference screenshot and composited; co-brand footer
is the MoonieX moon lockup (replaces iUX/POMT). Organic post (CEO-approved
likeness risk, 2026-06-13).

Palette LOCKED per assets/brand-refs/mooniex/BRAND.md:
  navy #0c1c2b -> #0a1622, champagne gold #cdac65 (grad #e6d0a3->#cdac65->#766540),
  green=up. NO cyan/purple/teal/blue-neon. Thai font = Prompt.

  python scripts/spcx_musk_card.py        # build the PNG ($0, no API)
"""
import base64
import io
import os

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = "/Users/gob/MoonieXHQ/Agents/Core"
SRC = "/Users/gob/Desktop/720655493_1566045434883239_2334179446712343628_n.jpg"
LOCKUP = os.path.join(ROOT, "output/personal-brand/lockup-moon-text.png")
OUT = os.path.join(ROOT, "output/mooniex-posters/spcx_musk_card.png")

# ── News facts (the event being newsjacked — cited as news, not MoonieX data) ──
NETWORTH = "$1.1T"
DELTA = "+$61.2B (+5.78%) SINCE PRIOR TRADING DAY"
NAME = "Elon Musk"
SUBNAME = "Tesla, SpaceX"
AGE = "54"

# ── MoonieX angle (Job A: edge / position smart — NOT get-rich-like-Musk bait) ──
HOOK = "จังหวะเปลี่ยนชีวิต ไม่เคยรอคนที่ลังเล"
SUBHOOK = "เรียน position อย่างมีระบบ — เทรดด้วยเหตุผล ไม่ใช่ดวง"


def b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def musk_crop_b64() -> str:
    """Tight crop of the white-bg Musk headshot from the reference card."""
    im = Image.open(SRC)
    w, h = im.size
    box = (int(0.695 * w), int(0.122 * h), int(0.929 * w), int(0.268 * h))
    crop = im.crop(box).convert("RGB")
    buf = io.BytesIO()
    crop.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


HTML = """<!doctype html><html lang="th"><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&family=Prompt:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  html,body { width:1080px; height:1620px; }
  body {
    font-family:'Prompt',sans-serif;
    background:radial-gradient(120% 90% at 50% 0%, #14304a 0%, #0c1c2b 46%, #0a1622 100%);
    color:#fff; -webkit-font-smoothing:antialiased;
  }
  .card { width:1080px; height:1620px; padding:72px 76px 60px; display:flex; flex-direction:column; }
  .badge {
    align-self:flex-start; padding:15px 28px; border-radius:14px;
    background:linear-gradient(95deg,#e6d0a3,#cdac65 55%,#b9974e);
    color:#0a1622; font-weight:700; font-size:29px; letter-spacing:.06em;
    box-shadow:0 8px 34px rgba(205,172,101,.32);
  }
  .head { display:flex; justify-content:space-between; align-items:flex-start; margin-top:44px; }
  .rank { font-family:'Playfair Display',serif; font-weight:700; font-size:90px; color:#cdac65; line-height:.9; }
  .name { font-family:'Playfair Display',serif; font-weight:800; font-size:96px; line-height:.94; margin-top:4px; letter-spacing:-.01em; white-space:nowrap; }
  .sub  { font-size:36px; color:#9fb0c0; font-weight:400; margin-top:16px; }
  .photo { width:244px; height:244px; border-radius:20px; object-fit:cover;
    border:3px solid rgba(205,172,101,.85); box-shadow:0 10px 40px rgba(0,0,0,.5); flex:none; margin-top:6px; }
  .rule { height:2px; background:linear-gradient(90deg,transparent,rgba(205,172,101,.5),transparent); margin:40px 0; }
  .tabs { display:flex; background:#13283c; border-radius:46px; padding:8px; gap:8px; }
  .tab { flex:1; text-align:center; padding:22px 0; border-radius:40px; font-size:36px; font-weight:500; color:#8fa1b3; }
  .tab.on { background:linear-gradient(95deg,#cdac65,#b9974e); color:#0a1622; font-weight:700; }
  .lbl { color:#8fa1b3; font-size:29px; letter-spacing:.16em; font-weight:600; margin-top:40px; }
  .nw  { font-size:150px; font-weight:700; line-height:1; margin-top:8px; letter-spacing:-.02em; }
  .delta { color:#3ecf8e; font-size:36px; font-weight:600; margin-top:18px; display:flex; align-items:center; gap:14px; }
  .delta .tri { font-size:30px; }
  .val { font-size:44px; font-weight:500; margin-top:12px; }
  .grid { display:flex; gap:120px; margin-top:34px; }
  .grid .lbl { margin-top:0; }
  .grid .val { font-size:44px; margin-top:10px; }
  .hookwrap { margin-top:auto; }
  .hook { font-size:48px; font-weight:700; line-height:1.18;
    background:linear-gradient(95deg,#e6d0a3,#cdac65 55%,#9e8246);
    -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }
  .subhook { font-size:32px; color:#c9d4de; font-weight:300; margin-top:16px; }
  .foot { display:flex; justify-content:space-between; align-items:center; margin-top:42px;
    padding-top:32px; border-top:2px solid rgba(205,172,101,.28); }
  .foot img { height:74px; }
  .support { color:#9fb0c0; font-size:32px; font-weight:500; text-align:right; }
  .support b { color:#cdac65; font-weight:700; }
</style></head>
<body><div class="card">
  <div class="badge">WORLD&rsquo;S FIRST TRILLIONAIRE</div>
  <div class="head">
    <div>
      <div style="display:flex;align-items:flex-start;gap:26px">
        <span class="rank">1.</span><span class="name">__NAME__</span>
      </div>
      <div class="sub">__SUBNAME__</div>
    </div>
    <img class="photo" src="data:image/png;base64,__MUSK__">
  </div>
  <div class="rule"></div>
  <div class="tabs"><div class="tab on">Stats</div><div class="tab">Biography</div></div>
  <div class="lbl">CURRENT NET WORTH</div>
  <div class="nw">__NW__</div>
  <div class="delta"><span class="tri">&#9650;</span><span>__DELTA__</span></div>
  <div class="lbl">SOURCE OF WEALTH</div>
  <div class="val">__SUBNAME__</div>
  <div class="grid">
    <div><div class="lbl">CITIZENSHIP</div><div class="val">United States</div></div>
    <div><div class="lbl">AGE</div><div class="val">__AGE__</div></div>
  </div>
  <div class="hookwrap">
    <div class="hook">__HOOK__</div>
    <div class="subhook">__SUBHOOK__</div>
    <div class="foot">
      <img src="data:image/png;base64,__LOCKUP__">
      <div class="support">รองรับ <b>Exness</b> &middot; <b>XM</b></div>
    </div>
  </div>
</div></body></html>"""


def build() -> None:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    html = (
        HTML.replace("__NAME__", NAME)
        .replace("__SUBNAME__", SUBNAME)
        .replace("__NW__", NETWORTH)
        .replace("__DELTA__", DELTA)
        .replace("__AGE__", AGE)
        .replace("__HOOK__", HOOK)
        .replace("__SUBHOOK__", SUBHOOK)
        .replace("__MUSK__", musk_crop_b64())
        .replace("__LOCKUP__", b64(LOCKUP))
    )
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1620},
                                device_scale_factor=2)
        page.set_content(html, wait_until="networkidle")
        page.wait_for_timeout(700)  # let webfonts settle
        page.screenshot(path=OUT, clip={"x": 0, "y": 0, "width": 1080, "height": 1620})
        browser.close()
    print(f"OK -> {OUT}")


if __name__ == "__main__":
    build()
