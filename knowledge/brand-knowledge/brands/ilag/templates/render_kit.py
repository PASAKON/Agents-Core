"""Build kit.html from kit.tpl.html and screenshot every kit element as a 1080x1920 transparent PNG."""
import re
import shutil
import sys
from pathlib import Path


# The Page's own logo, lifted off its black square; never redrawn (CEO 2026-10-26: "ILAG เรามี Logo อยู่แลวนะ ไม่ต้องทำใหม่").
LOGO = '<img class="logo" src="logo.png" alt="">'
STAMP = "#E8B230"  # NG stamp ink, v2 theme: gold, white and black only


def split(sfx, y, op):
    """White over black with an S-shaped gold seam at height y: the two halves of the lotus in the logo."""
    y = int(y)
    curve = f"C270 {y - 200} 810 {y + 200} 1080 {y}"
    back = f"C810 {y + 200} 270 {y - 200} 0 {y}"
    return (f'<svg class="split" viewBox="0 0 1080 1920"><defs><linearGradient id="sg_{sfx}" x1="0" x2="1">'
            '<stop offset="0" stop-color="#E49C1D"/><stop offset=".5" stop-color="#FDE165"/>'
            '<stop offset="1" stop-color="#E49C1D"/></linearGradient></defs>'
            f'<path d="M0 0H1080V{y}{back}Z" fill="#FFFFFF" fill-opacity="{op}"/>'
            f'<path d="M0 {y}{curve}V1920H0Z" fill="#0A0A0A" fill-opacity="{op}"/>'
            f'<path d="M0 {y}{curve}" fill="none" stroke="url(#sg_{sfx})" stroke-width="7"/></svg>')


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
            f'<g transform="rotate(-12 300 300)" filter="url(#rough_{sfx})" fill="{STAMP}" stroke="{STAMP}">'
            '<circle cx="300" cy="300" r="272" fill="none" stroke-width="18"/>'
            '<circle cx="300" cy="300" r="244" fill="none" stroke-width="6"/>'
            '<text font-family="Chakra" font-weight="700" font-size="66" letter-spacing="8" stroke="none">'
            f'<textPath href="#arcT_{sfx}" startOffset="50%" text-anchor="middle">AI หลุด</textPath></text>'
            '<text x="300" y="382" text-anchor="middle" font-family="Chakra" font-weight="700" font-size="236" stroke="none">NG</text>'
            '<text font-family="Cinzel" font-weight="700" font-size="44" letter-spacing="10" stroke="none">'
            f'<textPath href="#arcB_{sfx}" startOffset="50%" text-anchor="middle">ILAG STUDIO</textPath></text>'
            '</g></svg>')


def build_kit(K):
    """Write K/kit.html from kit.tpl.html (logo, split, ornament and NG-stamp placeholders filled) and return its text."""
    K = Path(K)
    FONTS = K / "fonts"
    for src, dst in (("Cinzel[wght].ttf", "Cinzel-VF.ttf"), ("Anuphan[wght].ttf", "Anuphan-VF.ttf")):
        if (FONTS / src).exists() and not (FONTS / dst).exists():
            shutil.copy(FONTS / src, FONTS / dst)
    html = (K / "kit.tpl.html").read_text()
    html = html.replace("{{LOGO}}", LOGO)
    html = re.sub(r"\{\{SPLIT:(\w+):(\d+):([\d.]+)\}\}", lambda m: split(*m.groups()), html)
    html = re.sub(r"\{\{ORN:(\w+):(\w+)\}\}", lambda m: orn(m.group(1), m.group(2)), html)
    html = re.sub(r"\{\{NG:(\w+)\}\}", lambda m: ng(m.group(1)), html)
    assert "{{" not in html, "unfilled placeholder in kit.tpl.html"
    (K / "kit.html").write_text(html)
    return html


ALL = [
    "wm", "skip", "rewcard", "flash", "ftag", "now", "place", "name", "namegood", "title", "fact", "ng", "ngs", "ngt",
    "rew", "take2", "lesson", "bltag", "blooper", "end", "sub", "safe", "fonts", "emblem"]


def main():
    from playwright.sync_api import sync_playwright

    K = Path(sys.argv[1]).resolve()
    build_kit(K)
    NAMES = sys.argv[2].split(",") if len(sys.argv) > 2 else ALL
    if unknown := [n for n in NAMES if n not in ALL]:
        sys.exit(f"unknown element: {','.join(unknown)} (known: {','.join(ALL)})")
    out = K / "overlays"
    out.mkdir(exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        for name in NAMES:
            pg.goto((K / "kit.html").as_uri() + f"?el={name}")
            pg.wait_for_function('document.body.dataset.ready === "1"')
            pg.wait_for_timeout(120)
            pg.screenshot(path=str(out / f"{name}.png"), omit_background=True)
        b.close()
    print("rendered", len(NAMES), "overlays")


if __name__ == "__main__":
    main()
