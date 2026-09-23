#!/usr/bin/env python3
"""Wireframe / layout mockup for the Musk $1T poster — APPROVAL BEFORE gen.

CEO asked to see the layout drawn before spending another AI gen. This renders
a $0 HTML->Playwright wireframe: DASHED boxes = regions the AI will generate
(Musk hero, rocket->moon), SOLID styled text = the copy that gets overlaid
crisp (so no Thai garble). Message focus (CEO 2026-06-13): Elon Musk = world's
first $1-trillion net worth, after the SpaceX IPO.

Palette per BRAND.md: navy #0c1c2b, champagne gold #cdac65, green=up. Thai=Prompt.

  python scripts/spcx_layout_mock.py
"""
import os
from playwright.sync_api import sync_playwright

OUT = "/Users/gob/MoonieXHQ/Agents/Core/output/mooniex-posters/spcx_layout_mock.png"

HTML = """<!doctype html><html lang="th"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Prompt:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
  *{margin:0;padding:0;box-sizing:border-box;}
  html,body{width:1080px;height:1080px;}
  body{font-family:'Prompt',sans-serif;
    background:radial-gradient(125% 95% at 50% 0%,#15324d 0%,#0c1c2b 48%,#0a1622 100%);
    color:#fff;}
  .card{width:1080px;height:1080px;padding:54px 58px;position:relative;}
  .gen{position:absolute;border:3px dashed rgba(205,172,101,.6);border-radius:18px;
    display:flex;align-items:center;justify-content:center;text-align:center;
    color:#cdac65;font-size:26px;font-weight:600;letter-spacing:.02em;background:rgba(205,172,101,.05);}
  .muskbox{right:58px;top:148px;width:372px;height:452px;}
  .rocketbox{right:108px;bottom:188px;width:262px;height:300px;}
  .lockup{position:absolute;top:46px;left:58px;color:#cdac65;font-weight:700;font-size:30px;
    border:2px dotted rgba(205,172,101,.5);padding:8px 16px;border-radius:10px;}
  .badge{position:absolute;top:168px;left:58px;padding:13px 24px;border-radius:12px;
    background:linear-gradient(95deg,#e6d0a3,#cdac65 55%,#b9974e);color:#0a1622;
    font-weight:700;font-size:27px;letter-spacing:.04em;}
  .num{position:absolute;top:262px;left:54px;font-family:'Anton',sans-serif;
    font-size:228px;line-height:.86;color:#fff;letter-spacing:-.01em;}
  .delta{position:absolute;top:506px;left:62px;color:#3ecf8e;font-size:42px;font-weight:700;}
  .name{position:absolute;top:592px;left:60px;font-size:54px;font-weight:700;}
  .sub{position:absolute;top:660px;left:62px;color:#9fb0c0;font-size:34px;}
  .thai{position:absolute;top:742px;left:60px;width:600px;color:#e6d0a3;font-size:40px;
    font-weight:600;line-height:1.34;}
  .strip{position:absolute;left:58px;bottom:62px;display:flex;gap:16px;}
  .pill{border:2px solid rgba(205,172,101,.7);border-radius:30px;padding:13px 24px;
    color:#cdac65;font-size:25px;font-weight:600;}
  .foot{position:absolute;right:58px;bottom:70px;color:#7f93a6;font-size:24px;}
</style></head>
<body><div class="card">
  <div class="lockup">&#127769; MOONIEX  <span style="font-size:16px;font-weight:400">[logo lockup]</span></div>

  <div class="gen muskbox">MUSK HERO PHOTO<br>(AI-gen, suit/turtleneck,<br>navy+gold rim light)</div>
  <div class="gen rocketbox">ROCKET &rarr; MOON<br>(AI-gen accent,<br>gold plume)</div>

  <div class="badge">THE WORLD&rsquo;S FIRST TRILLIONAIRE</div>
  <div class="num">$1.1T</div>
  <div class="delta">&#9650; +$61.2B (+5.78%)</div>
  <div class="name">ELON MUSK</div>
  <div class="sub">Tesla &middot; SpaceX</div>
  <div class="thai">คนแรกของโลกที่ทรัพย์สินแตะ<br>1 ล้านล้านดอลลาร์ &mdash; หลังจาก SpaceX IPO</div>

  <div class="strip">
    <div class="pill">SPACEX IPO</div>
    <div class="pill">NASDAQ: SPCX</div>
    <div class="pill">13 JUNE 2026</div>
  </div>
  <div class="foot">รองรับ Exness &middot; XM</div>
</div></body></html>"""


def build() -> None:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1080}, device_scale_factor=2)
        pg.set_content(HTML, wait_until="networkidle")
        pg.wait_for_timeout(600)
        pg.screenshot(path=OUT, clip={"x": 0, "y": 0, "width": 1080, "height": 1080})
        b.close()
    print(f"OK -> {OUT}")


if __name__ == "__main__":
    build()
