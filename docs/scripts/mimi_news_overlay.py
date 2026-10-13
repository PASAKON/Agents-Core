#!/usr/bin/env python3
"""Friday 0-credit clip (hook A «ข่าวด่วนในบ้าน», CEO 2026-10-13 test): transparent 720x1280 TV-news overlay cards,
rendered by headless Chromium (correct Thai shaping). Zero model: HTML -> PNG; every word is composed here.

  mimi_news_overlay.py <out_dir> <cards.json>
cards.json = {"cards": [{"name": "n1", "tag": "ข่าวด่วน", "head": "...", "sub": "..."}], "ticker": "..."}
  tag    red label top-left (default «ข่าวด่วน»); "head" (use <br> for a line break; lines never wrap by themselves, Thai has no spaces to break on)/"sub" go in the lower-third; the ticker bar is on every card.
"""
import json, pathlib, sys
from playwright.sync_api import sync_playwright

out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
spec = json.load(open(sys.argv[2], encoding="utf-8"))

CSS = """
html,body{margin:0;background:transparent;width:720px;height:1280px;overflow:hidden;font-family:'Noto Sans Thai','Prompt',sans-serif}
.tag{position:absolute;left:0;top:70px;background:#d6001c;color:#fff;font-weight:800;font-size:58px;padding:4px 44px 10px 34px;
 clip-path:polygon(0 0,100% 0,calc(100% - 26px) 100%,0 100%);box-shadow:0 6px 18px rgba(0,0,0,.45)}
.live{position:absolute;right:30px;top:80px;color:#fff;font-weight:700;font-size:34px;text-shadow:0 0 6px #000,0 0 2px #000}
.live i{display:inline-block;width:22px;height:22px;border-radius:50%;background:#e11;margin-right:10px;vertical-align:-2px}
.lt{position:absolute;left:0;right:0;bottom:258px;background:linear-gradient(90deg,#0b2a6b,#14408f);color:#fff;
 padding:18px 30px 22px;border-top:6px solid #ffd21f;box-shadow:0 -6px 22px rgba(0,0,0,.4)}
.head{font-weight:800;font-size:50px;line-height:1.22;white-space:nowrap}
.sub{font-weight:500;font-size:32px;color:#ffe48a;margin-top:6px;line-height:1.25;white-space:nowrap}
.tick{position:absolute;left:0;right:0;bottom:180px;height:78px;background:#0a0a0a;color:#ffd21f;font-weight:700;font-size:34px;
 line-height:78px;white-space:nowrap;overflow:hidden;padding-left:30px}
"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 720, "height": 1280})
    for c in spec["cards"]:
        sub = f"<div class=sub>{c['sub']}</div>" if c.get("sub") else ""
        lt = f"<div class=lt><div class=head>{c['head']}</div>{sub}</div>" if c.get("head") else ""
        body = (f"<div class=tag>{c.get('tag', 'ข่าวด่วน')}</div><div class=live><i></i>สด</div>{lt}"
                f"<div class=tick>{spec['ticker']}</div>")
        pg.set_content(f"<style>{CSS}</style>{body}")
        pg.wait_for_timeout(250)
        pg.screenshot(path=str(out / f"{c['name']}.png"), omit_background=True)
        print("wrote", out / f"{c['name']}.png")
    b.close()
