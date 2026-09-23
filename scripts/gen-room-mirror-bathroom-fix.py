#!/usr/bin/env python3
"""One-off: fix the room's layout — the bathroom door must be on the wall
directly OPPOSITE the full-length mirror (facing each other across the
room), not adjacent to it on the same wall as it currently is. Image-to-
image using the existing plate as reference for material/lighting only.
fal.ai openai/gpt-image-2/edit, medium quality, $0.053/image.

  python scripts/gen-room-mirror-bathroom-fix.py
"""
import base64, json, re, urllib.request, urllib.error, os

OUT = "/Users/gob/MoonieXHQ/Agents/Core/output/pok-pok-klued"
ENV = "/Users/gob/MoonieXHQ/Agents/Core/.env"
DEST = os.path.join(OUT, "location-room-mirror-bathroom.png")
EDIT_EP = "https://fal.run/openai/gpt-image-2/edit"

PROMPT = (
    "Using the reference image as the exact starting point — this is a "
    "pixel-faithful edit, not a re-imagining. Keep every single element "
    "of the composition, camera framing, zoom level, wall positions, "
    "furniture, and lighting EXACTLY as shown, unchanged down to the "
    "pixel, except for the one specific correction listed below. Do "
    "NOT reframe, re-crop, zoom, or change the camera angle. Do NOT "
    "redesign the room, do NOT change how much of the bed is visible or "
    "its size in frame. This must look like the same photo with only "
    "the pillow position altered.\n\n"
    "Correction: the pillow on the bed (left side of frame) must sit "
    "clearly and unambiguously in the back-left corner of that bed — at "
    "the far end away from the camera, pushed into the corner where the "
    "bed meets the back wall. It should read as one single, distinct, "
    "clearly-shaped pillow sitting in that back-left corner — not "
    "centered, not floating mid-bed, not near the front/camera edge. "
    "The rumpled blanket fills the rest of the visible bed, trailing "
    "from that back-left corner toward the front and toward the right "
    "side of the bed.\n\n"
    "Nothing else changes: same mirror position, same bathroom doorway "
    "position, same balcony door, same desk, same cabinet, same floor "
    "tiles, same ceiling light, same cold desaturated night lighting, "
    "same camera distance and angle as the reference. Empty room, no "
    "people, no characters, completely still — a location reference "
    "shot only. Fine film grain, realistic horror-film cinematography. "
    "No people, no text, no on-screen graphics, no watermark."
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
    print("POST -> gpt-image-2/edit (medium), ~$0.053, fixing mirror/bathroom layout (self-ref) ...")
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
