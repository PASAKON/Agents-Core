#!/usr/bin/env python3
"""One-off SpaceX IPO news poster (2026-06-12) — MoonieX theme.

V1 = brand-only liquidity-vacuum concept (text-to-image).
V2 = personal-brand variant with CEO figure (edit + @image1 face ref).
Palette/composite rules follow memory `reference_mooniex_poster_recipe.md`;
MeiGen base structure: "CONTROLLED UNSEALING" (rank 253).

  python scripts/spcx_poster.py dry    # print prompts, no cost
  python scripts/spcx_poster.py gen    # gen V1+V2 (~$0.38, CEO-approved)
  python scripts/spcx_poster.py stamp  # re-composite logo only (free)
"""
import sys, os, json, base64, re, urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mooniex_logo import stamp_corner

BASE = "/Users/gob/MoonieXHQ/Agents/Core/output/personal-brand"
CROP = os.path.join(BASE, "_ref_crop.png")
OUT = "/Users/gob/MoonieXHQ/Agents/Core/output/mooniex-posters"
ENV = "/Users/gob/MoonieXHQ/Projects/MoonieX/ClaudeFlow/.env"
EDIT_EP = "https://fal.run/openai/gpt-image-2/edit"
T2I_EP = "https://fal.run/openai/gpt-image-2"
COST_PER_IMAGE = 0.19

HEADLINE_EN = "SPACEX IPO"
THAI_LINE = "แรงดึงดูด — เมื่อเงินทั้งโลก ไหลไปกองที่เดียว"
FACTS = "NASDAQ: SPCX • $135/SHARE • $1.77T • 12 JUNE 2026"

PALETTE = (
    "Palette STRICTLY deep navy (#0c1c2b) + warm champagne gold (#cdac65) only — NO cyan, "
    "purple, magenta, teal or blue neon. Premium institutional fintech, photorealistic, 8k. "
    "1:1 bold editorial poster. Keep the TOP-RIGHT corner clean and empty for a logo. "
    "Do NOT add any logo, badge or watermark; the ONLY text allowed is exactly what is "
    "specified below. Render all Thai text accurately and legibly. "
)

TYPO = (
    f"The single MOST DOMINANT element of the poster: a MASSIVE champagne-gold display "
    f"headline reading '{HEADLINE_EN}' stacked on two lines (SPACEX above, IPO below), "
    "filling the upper third edge-to-edge, rendered as sleek LIQUID-GOLD lettering with "
    "smooth molten highlights — bigger and brighter than everything else in frame. "
    f"Below it a much smaller white-and-gold Thai line '{THAI_LINE}'. At the very bottom, "
    f"one thin elegant gold uppercase fact strip in small tracking-wide type: '{FACTS}'. "
    "No other text anywhere. "
)

V1_PROMPT = (
    PALETTE
    + "Deep matte navy studio, almost pure dark background with a soft controlled champagne-gold "
    "glow diffused behind the subject, no visible light source, ultra clean dark floor with very "
    "soft 5-8% reflection. HERO: a sleek minimalist rocket lifting off at center frame, slightly "
    "low angle, composed not aggressive, razor-sharp edges, monolithic dark body with subtle gold "
    "trim, a controlled molten-gold engine plume below it. Around the rocket, a restrained "
    "gravitational vortex: small gold coins, thin gold candlestick-chart fragments and faint gold "
    "currency glyphs being pulled in a gentle spiral toward the rocket — sparse, elegant, premium, "
    "not cluttered. Negative space dominant and intentional. "
    + TYPO
)

V2_PROMPT = (
    "Identity (Critical): strictly reference @image1 — preserve the exact face, proportions, "
    "skin tone and hairstyle of the man; keep his black suit and black turtleneck; he must stay "
    "clearly recognizable. "
    + PALETTE
    + "The man stands by a dark penthouse window at night, three-quarter view, hands in his "
    "pockets, confident, watching a distant golden rocket launching into the deep navy sky above "
    "city lights, warm gold bokeh and gold reflections on the glass, warm gold rim light on him. "
    + TYPO
)

V3_PROMPT = (
    "General promo poster, NO people anywhere in frame. "
    "Palette: deep space black-navy (#0c1c2b) gradient sky with very faint subtle stars — the "
    "SpaceX aesthetic of black + polished chrome-silver — bridged with MoonieX warm champagne "
    "gold (#cdac65). Headline and rocket in sleek silver-white chrome; champagne gold reserved "
    "for the engine plume, fine accents, the Thai line and the fact strip. NO cyan, purple, "
    "magenta or teal. Premium institutional fintech, photorealistic, 8k, 1:1 bold editorial "
    "poster. Keep the TOP-RIGHT corner clean and empty for a logo. Do NOT add any logo, badge "
    "or watermark; the ONLY text allowed is exactly what is specified. Render all Thai text "
    "accurately and legibly. "
    "The single MOST DOMINANT element: a MASSIVE headline 'SPACEX IPO' stacked on two lines "
    "(SPACEX above, IPO below) in the upper third, set in the style of the SpaceX wordmark — "
    "ultra-extended minimalist futuristic sans-serif, PERFECTLY UPRIGHT letters with NO italic "
    "and NO slant, polished chrome-silver metallic, crisp razor edges, subtle gold reflection "
    "on the lower bevels — bigger and brighter than everything else. The headline is centered "
    "and spans only ~78% of the width, leaving generous clear dark margin on both sides; the "
    "ENTIRE top-right corner region (top 18% x right 22% of the frame) must stay completely "
    "empty dark sky — no letters may enter it. "
    "Scene below: a slender Falcon-style white-silver rocket lifting off at center frame on a "
    "controlled molten champagne-gold engine plume, slightly low angle, composed not aggressive; "
    "a huge faint crescent moon glowing dim gold behind it in the deep navy sky; a restrained "
    "sparse spiral of tiny gold coins being drawn toward the rocket; ultra clean dark ground "
    "with soft 5-8% reflection; negative space dominant and intentional. "
    "Below the headline a much smaller white-and-gold Thai line "
    f"'{THAI_LINE}'. At the very bottom, ONE single row of four small rounded pill-shaped "
    "badge buttons, evenly spaced on the same line: each pill has a thin elegant gold outline, "
    "dark navy fill, and one short gold uppercase label inside — 'NASDAQ: SPCX', '$135/SHARE', "
    "'$1.77T', '12 JUNE 2026'. All four pills MUST sit on one row. No other text anywhere. "
)

JOBS = [("v1", V1_PROMPT, False), ("v2", V2_PROMPT, True), ("v3", V3_PROMPT, False)]


def load_key():
    m = re.search(r"^FAL_API_KEY=(.+)$", open(ENV, encoding="utf-8").read(), re.M)
    if not m:
        sys.exit("FAL_API_KEY not found in " + ENV)
    return m.group(1).strip().strip('"').strip("'")


def gen_one(key, tag, prompt, with_ref):
    payload = {"prompt": prompt, "image_size": "square_hd", "quality": "high",
               "num_images": 1, "output_format": "png"}
    ep = T2I_EP
    if with_ref:
        uri = "data:image/png;base64," + base64.b64encode(open(CROP, "rb").read()).decode()
        payload["image_urls"] = [uri]
        ep = EDIT_EP
    body = json.dumps(payload).encode()
    req = urllib.request.Request(ep, data=body, method="POST",
        headers={"Authorization": "Key " + key, "Content-Type": "application/json"})
    print(f"[{tag}] POST ({len(body)}B) -> {ep.rsplit('/',1)[-1]} ...")
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        print(f"[{tag}] HTTP {e.code}: {e.read().decode()[:400]}"); return False
    imgs = data.get("images") or []
    if not imgs:
        print(f"[{tag}] no images: {json.dumps(data)[:300]}"); return False
    urllib.request.urlretrieve(imgs[0]["url"], os.path.join(OUT, f"spcx_{tag}.png"))
    print(f"[{tag}] OK -> spcx_{tag}.png")
    return True


def stamp_one(tag):
    from PIL import Image
    src = os.path.join(OUT, f"spcx_{tag}.png")
    if not os.path.exists(src):
        print(f"[{tag}] no clean image"); return
    out = stamp_corner(Image.open(src))
    out.convert("RGB").save(os.path.join(OUT, f"spcx_{tag}_final.png"))
    print(f"[{tag}] stamped -> spcx_{tag}_final.png")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry"
    only = sys.argv[2] if len(sys.argv) > 2 else None
    global JOBS
    if only:
        JOBS = [j for j in JOBS if j[0] == only]
    os.makedirs(OUT, exist_ok=True)
    if mode == "dry":
        for tag, prompt, _ in JOBS:
            print(f"\n===== spcx_{tag} =====\n{prompt}")
        print(f"\n{len(JOBS)} prompts. gen cost ≈ ${len(JOBS)*COST_PER_IMAGE:.2f}")
        return
    if mode == "stamp":
        for tag, _, _ in JOBS:
            stamp_one(tag)
        return
    print(f"About to gen {len(JOBS)} image(s) ≈ ${len(JOBS)*COST_PER_IMAGE:.2f} (CEO approved)")
    key = load_key()
    ok = 0
    for tag, prompt, with_ref in JOBS:
        if gen_one(key, tag, prompt, with_ref):
            stamp_one(tag); ok += 1
    print(f"done: {ok}/{len(JOBS)} -> {OUT}")


if __name__ == "__main__":
    main()
