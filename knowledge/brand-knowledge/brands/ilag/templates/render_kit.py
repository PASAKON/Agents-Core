"""Build kit.html from kit.tpl.html and screenshot every kit element as a 1080x1920 transparent PNG."""
import re
import shutil
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

K = Path(sys.argv[1])
FONTS = K / "fonts"
for src, dst in (("Cinzel[wght].ttf", "Cinzel-VF.ttf"), ("Anuphan[wght].ttf", "Anuphan-VF.ttf")):
    if (FONTS / src).exists() and not (FONTS / dst).exists():
        shutil.copy(FONTS / src, FONTS / dst)

EMBLEM = (K / "emblem.svg").read_text()


def emblem(sfx):
    s = EMBLEM
    for i in ("gm", "bg", "cream", "dark", "L", "R"):
        s = s.replace(f'id="{i}"', f'id="{i}_{sfx}"').replace(f"url(#{i})", f"url(#{i}_{sfx})")
    return s.replace('width="400" height="400"', 'width="100%" height="100%"')


def orn(sfx, cls):
    return (f'<svg class="orn {cls}" viewBox="0 0 600 28"><defs><linearGradient id="og_{sfx}" x1="0" x2="1">'
            '<stop offset="0" stop-color="#E49C1D" stop-opacity="0"/><stop offset=".3" stop-color="#F7C440"/>'
            '<stop offset="1" stop-color="#FDE165"/></linearGradient>'
            f'<linearGradient id="oh_{sfx}" x1="1" x2="0"><stop offset="0" stop-color="#E49C1D" stop-opacity="0"/>'
            '<stop offset=".3" stop-color="#F7C440"/><stop offset="1" stop-color="#FDE165"/></linearGradient></defs>'
            f'<rect x="20" y="12.5" width="246" height="3" fill="url(#og_{sfx})"/>'
            f'<rect x="334" y="12.5" width="246" height="3" fill="url(#oh_{sfx})"/>'
            '<path d="M300 1 L313 14 L300 27 L287 14 Z" fill="#F7C440"/>'
            '<circle cx="276" cy="14" r="4" fill="#FDE165"/><circle cx="324" cy="14" r="4" fill="#FDE165"/></svg>')


def ng(sfx):
    return (f'<svg class="ng-svg" viewBox="0 0 600 600" width="100%" height="100%"><defs>'
            f'<filter id="rough_{sfx}" x="-5%" y="-5%" width="110%" height="110%">'
            '<feTurbulence type="fractalNoise" baseFrequency="0.03" numOctaves="2" seed="7" result="n"/>'
            '<feDisplacementMap in="SourceGraphic" in2="n" scale="10" xChannelSelector="R" yChannelSelector="G" result="d"/>'
            '<feTurbulence type="fractalNoise" baseFrequency="0.75" numOctaves="1" seed="3" result="g"/>'
            '<feColorMatrix in="g" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -2.2 2.25" result="speck"/>'
            '<feComposite in="d" in2="speck" operator="in"/></filter>'
            f'<path id="arcT_{sfx}" d="M 118 300 A 182 182 0 0 1 482 300"/>'
            f'<path id="arcB_{sfx}" d="M 102 300 A 198 198 0 0 0 498 300"/></defs>'
            f'<g transform="rotate(-12 300 300)" filter="url(#rough_{sfx})" fill="#B8322A" stroke="#B8322A">'
            '<circle cx="300" cy="300" r="272" fill="none" stroke-width="18"/>'
            '<circle cx="300" cy="300" r="244" fill="none" stroke-width="6"/>'
            '<text font-family="Chakra" font-weight="700" font-size="66" letter-spacing="8" stroke="none">'
            f'<textPath href="#arcT_{sfx}" startOffset="50%" text-anchor="middle">AI หลุด</textPath></text>'
            '<text x="300" y="382" text-anchor="middle" font-family="Chakra" font-weight="700" font-size="236" stroke="none">NG</text>'
            '<text font-family="Cinzel" font-weight="700" font-size="44" letter-spacing="10" stroke="none">'
            f'<textPath href="#arcB_{sfx}" startOffset="50%" text-anchor="middle">ILAG STUDIO</textPath></text>'
            '</g></svg>')


html = (K / "kit.tpl.html").read_text()
html = re.sub(r"\{\{EM:(\w+)\}\}", lambda m: emblem(m.group(1)), html)
html = re.sub(r"\{\{ORN:(\w+):(\w+)\}\}", lambda m: orn(m.group(1), m.group(2)), html)
html = re.sub(r"\{\{NG:(\w+)\}\}", lambda m: ng(m.group(1)), html)
(K / "kit.html").write_text(html)

head = html.split("<body>")[0]
(K / "emblem.html").write_text(head.replace("width:1080px;height:1920px", "width:1024px;height:1024px")
                               + f'<body><div style="position:absolute;inset:0">{emblem("solo")}</div>'
                               '<script>document.fonts.ready.then(()=>{document.body.dataset.ready="1"})</script></body></html>')

NAMES = sys.argv[2].split(",") if len(sys.argv) > 2 else [
    "wm", "skip", "rewcard", "flash", "ftag", "now", "place", "name", "title", "ng", "ngs", "ngt", "rew", "take2",
    "bltag", "blooper", "end", "sub", "safe", "fonts", "emblem"]
out = K / "overlays"
out.mkdir(exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1080, "height": 1920})
    for name in NAMES:
        pg.goto(f"file://{K}/kit.html?el={name}")
        pg.wait_for_function('document.body.dataset.ready === "1"')
        pg.wait_for_timeout(120)
        pg.screenshot(path=str(out / f"{name}.png"), omit_background=True)
    pg2 = b.new_page(viewport={"width": 1024, "height": 1024})
    pg2.goto(f"file://{K}/emblem.html")
    pg2.wait_for_function('document.body.dataset.ready === "1"')
    pg2.wait_for_timeout(120)
    pg2.screenshot(path=str(K / "out" / "ilag-emblem-1024.png"), omit_background=True)
    b.close()
print("rendered", len(NAMES), "overlays")
