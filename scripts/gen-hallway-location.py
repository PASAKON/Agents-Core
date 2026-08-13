#!/usr/bin/env python3
"""One-off: re-grade the existing hallway location plate — same corridor
layout, doors, light fixtures — but push to a much darker night look and
strip out the peeling/stained texture, keeping it just old/worn.
Image-to-image using the hallway's own current PNG as reference.
fal.ai openai/gpt-image-2/edit, medium quality, $0.053/image.

  python scripts/gen-hallway-location.py
"""
import base64, json, re, urllib.request, urllib.error, os

OUT = "/Users/gob/Projects/Agents/output/pok-pok-klued"
ENV = "/Users/gob/Projects/Agents/.env"
DEST = os.path.join(OUT, "location-hallway.png")
EDIT_EP = "https://fal.run/openai/gpt-image-2/edit"

PROMPT = (
    "Using the reference image as the exact starting point — keep the "
    "identical corridor layout, camera framing, door positions, and "
    "ceiling light fixture positions exactly as shown — apply two "
    "changes only:\n\n"
    "1. Push the lighting to a much darker, deeper nighttime look: less "
    "overall fluorescent brightness, more of the corridor sitting in "
    "near-total shadow, the working fixtures dimmer and flickering, the "
    "dead fixture's shadow pool even deeper and larger, the far-end glow "
    "softer and dimmer too.\n\n"
    "2. Remove the dirty, peeling, and stained look from the walls and "
    "floor — keep the surfaces just old and worn (faded paint, aged "
    "texture, scuffed doors) but clean, no grime, no peeling flakes, no "
    "floor stains.\n\n"
    "Still an empty environment establishing plate, no people, no "
    "characters, completely still. Fine film grain, realistic "
    "horror-film cinematography, cold desaturated color grading, very "
    "low-key night lighting. No people, no text, no on-screen graphics, "
    "no watermark."
)


def load_key():
    m = re.search(r'^FAL_API_KEY=["\']?([^"\'\n]+)', open(ENV, encoding="utf-8").read(), re.M)
    if not m:
        raise SystemExit("FAL_API_KEY not found in " + ENV)
    return m.group(1).strip()


def image_data_uri(path):
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:image/png;base64,{b64}"


def main():
    key = load_key()
    os.makedirs(OUT, exist_ok=True)
    ref_uri = image_data_uri(DEST)
    payload = {"prompt": PROMPT, "image_urls": [ref_uri], "image_size": "square_hd",
               "quality": "medium", "num_images": 1, "output_format": "png"}
    body = json.dumps(payload).encode()
    req = urllib.request.Request(EDIT_EP, data=body, method="POST",
        headers={"Authorization": "Key " + key, "Content-Type": "application/json"})
    print("POST -> gpt-image-2/edit (medium), ~$0.053, re-grading hallway (self-ref) ...")
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code}: {e.read().decode()[:400]}")
    imgs = data.get("images") or []
    if not imgs:
        raise SystemExit(f"no images: {json.dumps(data)[:300]}")
    urllib.request.urlretrieve(imgs[0]["url"], DEST)
    print(f"OK -> {DEST}")


if __name__ == "__main__":
    main()
