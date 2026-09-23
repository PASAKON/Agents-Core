#!/usr/bin/env python3
"""One-off: generate @Character4 The Alien reference portrait for ประตูวาป
(Warp Door). Same fal.ai openai/gpt-image-2 pattern as
scripts/gen-brandprompt-scenes.py (medium quality, $0.053/image).

  python scripts/gen-alien-character.py
"""
import json, re, urllib.request, urllib.error, os

OUT = "/Users/gob/MoonieXHQ/Agents/Core/output/warp-door"
ENV = "/Users/gob/MoonieXHQ/Agents/Core/.env"
T2I_EP = "https://fal.run/openai/gpt-image-2"

PROMPT = (
    "Character reference sheet, plain white/light-grey studio background, "
    "even soft studio lighting, no shadows, no props, no scene — identical "
    "character in every panel, only expression and pose change.\n\n"
    "LEFT SIDE — 5 emotion close-ups in a labeled grid, each panel numbered "
    "and titled top-left in bold sans-serif:\n"
    "01 NEUTRAL/NORMAL — calm, unreadable, resting alien expression\n"
    "02 CURIOUS — head tilted slightly, watching\n"
    "03 PAIN — eyes tightened, jaw clenched from captivity\n"
    "04 PLEADING — eyes wide, searching, silently asking for help\n"
    "05 FEAR — recoiling, eyes wide with alarm\n\n"
    "RIGHT SIDE — 1 full-body panel, larger than the emotion grid, "
    "character standing straight in a neutral pose, arms at sides, full "
    "wardrobe and body visible head to toe, same plain white background.\n\n"
    "CHARACTER (identical across all 6 panels): a sexless, ageless humanoid "
    "alien being. Gaunt, elongated face, no hair, smooth hairless scalp. "
    "Pale, near-translucent, sickly grey-white skin, faint teal "
    "bioluminescent veins visible near cable connection points on the neck "
    "and forearms. Thin, frail, slightly stooped build. Torn lab-issue "
    "containment wrap, medical tubing and cables connecting its body to "
    "external ports, restraint marks on the wrists. High resolution, "
    "detailed textures, no text other than the panel labels, no watermark."
)


def load_key():
    m = re.search(r'^FAL_API_KEY=["\']?([^"\'\n]+)', open(ENV, encoding="utf-8").read(), re.M)
    if not m:
        raise SystemExit("FAL_API_KEY not found in " + ENV)
    return m.group(1).strip()


def main():
    key = load_key()
    os.makedirs(OUT, exist_ok=True)
    payload = {"prompt": PROMPT, "image_size": "square_hd", "quality": "medium",
               "num_images": 1, "output_format": "png"}
    body = json.dumps(payload).encode()
    req = urllib.request.Request(T2I_EP, data=body, method="POST",
        headers={"Authorization": "Key " + key, "Content-Type": "application/json"})
    print("POST -> gpt-image-2 (medium), ~$0.053 ...")
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code}: {e.read().decode()[:400]}")
    imgs = data.get("images") or []
    if not imgs:
        raise SystemExit(f"no images: {json.dumps(data)[:300]}")
    dest = os.path.join(OUT, "character4-alien.png")
    urllib.request.urlretrieve(imgs[0]["url"], dest)
    print(f"OK -> {dest}")


if __name__ == "__main__":
    main()
