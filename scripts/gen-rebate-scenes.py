#!/usr/bin/env python3
"""Gen 2 SCENE-ONLY backgrounds for the MoonieX Rebate C1 A/B posters.

Model: fal openai/gpt-image-2 (T2I) — same path as spcx_poster.py.
SCENE ONLY: no text, no numbers, no logos (those are overlaid crisp by the
HTML text layer — brand-strict rule: never let gen bake $15/$8 or Thai/logos).

  python scripts/gen-rebate-scenes.py dry   # print prompts + cost, no spend
  python scripts/gen-rebate-scenes.py gen    # gen scene-a + scene-b (~$0.38)
"""
import sys, os, json, re, urllib.request, urllib.error

OUT = "/Users/gob/Projects/Agents/output/mooniex-rebate-c1"
ENV = "/Users/gob/Projects/mooniex-claudeflow/.env"
T2I_EP = "https://fal.run/openai/gpt-image-2"
COST_PER_IMAGE = 0.19

PALETTE = (
    "Premium institutional fintech background. Palette STRICTLY deep navy (#0c1c2b) base "
    "with warm champagne-gold (#cdac65) accents ONLY — NO cyan, purple, magenta, teal or "
    "blue neon. Photorealistic, 8k, 1:1 square. "
    "CRITICAL: absolutely NO text, NO numbers, NO letters, NO words, NO logos, NO badges, "
    "NO watermark anywhere in the image. The UPPER HALF and CENTER must stay clean dark "
    "navy negative space for later text overlay; keep gold elements restrained and confined "
    "to the LOWER portion and the edges. Calm, premium, uncluttered. "
)

SCENE_FINAL = (  # old rebate-poster style: navy radial + glossy gold bars in lower corners
    PALETTE
    + "Scene in the style of a premium gold rebate promo poster: a deep navy radial background "
    "glowing slightly brighter at the upper-center and darkening toward the edges, with very "
    "faint soft diagonal gold light streaks. In the LOWER-LEFT and LOWER-RIGHT corners, one "
    "elegant shiny 3D gold bullion bar resting at a slight angle together with a few small gold "
    "coins — glossy reflective polished gold with soft specular highlights. Subtle fine gold "
    "sparkle dust low in the frame. The ENTIRE upper half and the center stay clean dark navy "
    "negative space. Restrained, premium, balanced, uncluttered. "
)

JOBS = [("scene-final", SCENE_FINAL)]


def load_key():
    m = re.search(r"^FAL_API_KEY=(.+)$", open(ENV, encoding="utf-8").read(), re.M)
    if not m:
        sys.exit("FAL_API_KEY not found in " + ENV)
    return m.group(1).strip().strip('"').strip("'")


def gen_one(key, tag, prompt):
    payload = {"prompt": prompt, "image_size": "square_hd", "quality": "high",
               "num_images": 1, "output_format": "png"}
    body = json.dumps(payload).encode()
    req = urllib.request.Request(T2I_EP, data=body, method="POST",
        headers={"Authorization": "Key " + key, "Content-Type": "application/json"})
    print(f"[{tag}] POST ({len(body)}B) -> gpt-image-2 ...")
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        print(f"[{tag}] HTTP {e.code}: {e.read().decode()[:400]}"); return False
    imgs = data.get("images") or []
    if not imgs:
        print(f"[{tag}] no images: {json.dumps(data)[:300]}"); return False
    dest = os.path.join(OUT, f"{tag}.png")
    urllib.request.urlretrieve(imgs[0]["url"], dest)
    print(f"[{tag}] OK -> {dest}")
    return True


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry"
    os.makedirs(OUT, exist_ok=True)
    if mode == "dry":
        for tag, prompt in JOBS:
            print(f"\n===== {tag} =====\n{prompt}")
        print(f"\n{len(JOBS)} scene prompts. gen cost ~ ${len(JOBS)*COST_PER_IMAGE:.2f} (verify on fal.ai dashboard)")
        return
    print(f"About to gen {len(JOBS)} SCENE(s) ~ ${len(JOBS)*COST_PER_IMAGE:.2f} via fal gpt-image-2")
    key = load_key()
    ok = 0
    for tag, prompt in JOBS:
        if gen_one(key, tag, prompt):
            ok += 1
    print(f"done: {ok}/{len(JOBS)} -> {OUT}")


if __name__ == "__main__":
    main()
