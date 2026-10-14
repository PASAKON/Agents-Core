"""EP1 ACT 1 picture text, English master (CEO 2026-10-09: all picture text is English). Hand-made, no image-gen API.
Tokens copied from the passed Thai card.html (code wins): ink #0F0C0A, parchment #E8DDC4, ember #C9772B, ash #8C8277.
Run: .venv/bin/python -I render_cards.py   -> title_en.png (title card, transparent-free full frame) and t1_black.png (time card).
"""
import pathlib
from playwright.sync_api import sync_playwright

D = pathlib.Path(__file__).parent
HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=EB+Garamond:wght@500;600&family=IBM+Plex+Mono:wght@400&display=swap">
<style>
:root{--ink:#0F0C0A;--parch:#E8DDC4;--ember:#C9772B;--ash:#8C8277}
*{margin:0;box-sizing:border-box}
html,body{width:1920px;height:1080px;background:var(--ink);overflow:hidden}
"""
TITLE = HEAD + """
.wrap{position:absolute;left:160px;right:160px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center}
.tag{font-family:"IBM Plex Mono",monospace;font-size:26px;letter-spacing:.28em;text-transform:uppercase;color:var(--ash)}
.rule{width:120px;height:4px;background:var(--ember);margin:44px 0 52px}
h1{font-family:"EB Garamond",serif;font-weight:600;font-size:176px;line-height:1.1;color:var(--parch)}
p{font-family:"EB Garamond",serif;font-weight:500;font-size:62px;line-height:1.35;color:var(--parch);margin-top:36px}
p b{font-weight:600;color:var(--ember)}
</style></head><body><div class="wrap">
<div class="tag">The Old Telling · by ILAG Studio</div>
<div class="rule"></div>
<h1>The Legend of Orpheus</h1>
<p>The man who went down to bring his wife back from the <b>underworld</b></p>
</div></body></html>"""
T1 = HEAD + """
.c{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
.rule{width:96px;height:4px;background:var(--ember);margin-bottom:56px}
h2{font-family:"EB Garamond",serif;font-weight:500;font-size:104px;letter-spacing:.02em;color:var(--parch)}
h2 b{font-weight:600;color:var(--ember)}
</style></head><body><div class="c"><div class="rule"></div><h2>Seven months <b>later</b></h2></div></body></html>"""
(D / "card_en.html").write_text(TITLE, encoding="utf-8")
(D / "card_t1.html").write_text(T1, encoding="utf-8")
with sync_playwright() as p:
    b = p.chromium.launch()
    try:
        for html, png in (("card_en.html", "title_en.png"), ("card_t1.html", "t1_black.png")):
            pg = b.new_page(viewport={"width": 1920, "height": 1080})
            try:
                pg.goto((D / html).as_uri(), wait_until="networkidle")
                pg.wait_for_timeout(600)
                pg.screenshot(path=str(D / png))
            finally:
                pg.close()
    finally:
        b.close()
print("ok")
