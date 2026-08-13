#!/usr/bin/env python3
"""Gen SCENE-ONLY poster backgrounds for BrandPrompt TH sample library.

Model: fal openai/gpt-image-2 (T2I), quality=medium (CEO-approved budget
~$15.90 for 300 @ 1024x1024 medium). SCENE ONLY: no text baked in — text is
overlaid crisp afterward (same brand-safe technique as mooniex posters and
the BrandPrompt TH BRAND.md sample image).

  python scripts/gen-brandprompt-scenes.py dry    # print prompts + cost, no spend
  python scripts/gen-brandprompt-scenes.py test   # gen first 3 only (~$0.10)
  python scripts/gen-brandprompt-scenes.py gen    # gen all defined JOBS
"""
import sys, os, json, re, urllib.request, urllib.error

OUT = "/Users/gob/Projects/Agents/output/brandprompt-th/scenes"
ENV = "/Users/gob/Projects/Agents/.env"
T2I_EP = "https://fal.run/openai/gpt-image-2"
COST_PER_IMAGE = 0.053  # medium, 1024x1024 (fal.ai pricing table, checked 2026-07-20)

LOCKED = (
    "Editorial small-business campaign poster background, SCENE ONLY. "
    "Warm 'ink & paper' mood: near-black warm ink (#241E1A) and warm ivory "
    "paper (#F7F0E2) as the base tones, one warm terracotta/clay accent "
    "(#C1502C family). Photorealistic or soft-editorial illustration, "
    "generous negative space in the upper-center for later text overlay. "
    "CRITICAL: absolutely NO text, NO letters, NO numbers, NO logos, NO "
    "watermarks anywhere in the image — this is a background plate only. "
    "1:1 square, premium, uncluttered, warm and approachable (not "
    "cold/neon/cyberpunk sci-fi)."
)

CATEGORIES = {
    "cafe": "a cozy independent coffee shop counter, warm latte cup, soft morning window light, wood and ceramic textures",
    "skincare": "a minimal skincare product display, soft diffused studio light, glass bottle silhouette, delicate botanical accents",
    "fitness": "a warm-toned gym/studio space, soft directional light across the floor, dynamic but calm energy, no people in focus",
    "realestate": "a clean modern home exterior at golden hour, warm light on the facade, minimal landscaping",
    "flower": "a romantic flower shop corner, soft natural window light, loose floral textures, pastel warm tones",
}

JOBS = [(f"{cat}-scene-{i}", f"{LOCKED} Subject: {desc}, variation {i} of 3.")
        for cat, desc in CATEGORIES.items() for i in range(1, 4)]


def load_key():
    m = re.search(r'^FAL_API_KEY=["\']?([^"\'\n]+)', open(ENV, encoding="utf-8").read(), re.M)
    if not m:
        sys.exit("FAL_API_KEY not found in " + ENV)
    return m.group(1).strip()


def gen_one(key, tag, prompt):
    payload = {"prompt": prompt, "image_size": "square_hd", "quality": "medium",
               "num_images": 1, "output_format": "png"}
    body = json.dumps(payload).encode()
    req = urllib.request.Request(T2I_EP, data=body, method="POST",
        headers={"Authorization": "Key " + key, "Content-Type": "application/json"})
    print(f"[{tag}] POST ({len(body)}B) -> gpt-image-2 (medium) ...")
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
    jobs = JOBS[:3] if mode == "test" else JOBS
    if mode == "dry":
        for tag, prompt in jobs:
            print(f"\n===== {tag} =====\n{prompt}")
        print(f"\n{len(jobs)} scene prompts. gen cost ~ ${len(jobs)*COST_PER_IMAGE:.2f}")
        return
    print(f"About to gen {len(jobs)} SCENE(s) ~ ${len(jobs)*COST_PER_IMAGE:.2f} via fal gpt-image-2 (medium)")
    key = load_key()
    ok = 0
    for tag, prompt in jobs:
        if gen_one(key, tag, prompt):
            ok += 1
    print(f"done: {ok}/{len(jobs)} -> {OUT}")


if __name__ == "__main__":
    main()
