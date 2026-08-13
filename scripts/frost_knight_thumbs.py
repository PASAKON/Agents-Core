#!/usr/bin/env python3
"""Gen 3 YouTube-cover thumbnails for the Minecraft "Frost Knight" boss product.

Model: fal openai/gpt-image-2 (T2I) — same path as gen-rebate-scenes.py.
Style: Minecraft Bedrock blocky characters rendered with epic cinematic light.
3 composition DIRECTIONS so CEO can pick:
  d1 throne-standoff | d2 mid-battle | d3 roster-showcase (weapons clearest)

SCENE/characters ONLY: no baked text, no logo (title overlaid crisp later).
Original characters — NOT GrandChase, NOT Lich King (IP-safe).

  python scripts/frost_knight_thumbs.py dry   # print prompts + cost, no spend
  python scripts/frost_knight_thumbs.py gen    # gen all 3 (~$0.6-0.75)
  python scripts/frost_knight_thumbs.py gen d3 # gen only one tag
"""
import sys, os, json, re, urllib.request, urllib.error

OUT = "/Users/gob/Projects/Agents/output/minecraft-frost-knight"
ENV = "/Users/gob/Projects/mooniex-claudeflow/.env"
T2I_EP = "https://fal.run/openai/gpt-image-2"
SIZE = "landscape_16_9"          # YouTube cover ratio
COST_PER_IMAGE = 0.25           # landscape high; verify on fal.ai dashboard

# Shared style anchor — keep it BLOCKY Minecraft, not realistic/anime.
BASE = (
    "Minecraft Bedrock Edition art style: BLOCKY cube-based characters, mobs and "
    "props (low-poly voxel look), but rendered as premium Marketplace key art with "
    "epic cinematic lighting, volumetric ice fog, dramatic rim light, snow particles. "
    "16:9 YouTube thumbnail, ultra high detail, vivid. Cold blue-and-gold palette "
    "inside a frozen ice cavern. "
    "BOSS: an ORIGINAL ice villain 'Frost Knight' (do NOT copy the Lich King) — a "
    "towering knight of cracked blue ice and dark frostbitten plate armor, ALWAYS "
    "wearing a shining GOLD CROWN, wielding a MASSIVE ICE GREATSWORD as tall as his "
    "whole body with glowing pale-blue runes, seated on / guarding a glacier ice throne. "
    "THREE FEMALE heroes fight him, each weapon a BOLD, well-lit, distinct-silhouette "
    "hero element, readable even at small size, weapons NOT overlapping: "
    "ARCHER in GREEN ranger outfit with a large GREEN LONGBOW drawn and a glowing green "
    "energy arrow; KNIGHT in steel armor with a gleaming STEEL GREATSWORD and a round "
    "shield (steel sword clearly different from the boss ice sword); WIZARD in a mage "
    "robe with a tall STAFF topped by a glowing crystal orb casting a frost spell. "
    "Original characters, do NOT copy GrandChase (inspiration only). "
    "ABSOLUTELY NO text, NO letters, NO numbers, NO logo, NO watermark anywhere. "
)

JOBS = {
    "d1-throne-standoff": BASE + (
        "COMPOSITION: symmetric epic cover. The Frost Knight sits ELEVATED and CENTERED "
        "on his throne behind the heroes. The three heroines stand in a foreground arc "
        "facing him, weapons drawn and fanned outward so all three read clearly. Leave "
        "clean negative space across the TOP for a title."
    ),
    "d2-mid-battle": BASE + (
        "COMPOSITION: dynamic DIAGONAL action, mid-combat. The Frost Knight in the UPPER "
        "area swinging his ice greatsword downward with a frost shockwave; the heroines "
        "leap in from the lower-left in motion — the archer's bright GREEN energy arrow "
        "streaks across the frame, the knight mid-leap with sword overhead, the wizard "
        "blasting a frost spell. Motion energy on bodies but each WEAPON stays sharp and "
        "isolated. Leave title space TOP-LEFT."
    ),
    "d3-roster-showcase": BASE + (
        "COMPOSITION: character-select / roster shot. The THREE heroines stand large, "
        "front-and-centre, each PRESENTING her weapon toward the camera so the weapon is "
        "the clearest element (bow drawn toward viewer, steel sword raised forward, staff "
        "orb glowing forward). The Frost Knight LOOMS LARGE in the background on his throne, "
        "gold crown and giant ice sword silhouette, menacing but secondary. Leave a clean "
        "band at TOP or BOTTOM for a title."
    ),
}


def load_key():
    m = re.search(r"^FAL_API_KEY=(.+)$", open(ENV, encoding="utf-8").read(), re.M)
    if not m:
        sys.exit("FAL_API_KEY not found in " + ENV)
    return m.group(1).strip().strip('"').strip("'")


def gen_one(key, tag, prompt):
    payload = {"prompt": prompt, "image_size": SIZE, "quality": "high",
               "num_images": 1, "output_format": "png"}
    body = json.dumps(payload).encode()
    req = urllib.request.Request(T2I_EP, data=body, method="POST",
        headers={"Authorization": "Key " + key, "Content-Type": "application/json"})
    print(f"[{tag}] POST ({len(body)}B) -> gpt-image-2 {SIZE} ...")
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        print(f"[{tag}] HTTP {e.code}: {e.read().decode()[:500]}"); return False
    imgs = data.get("images") or []
    if not imgs:
        print(f"[{tag}] no images: {json.dumps(data)[:300]}"); return False
    dest = os.path.join(OUT, f"{tag}.png")
    urllib.request.urlretrieve(imgs[0]["url"], dest)
    print(f"[{tag}] OK -> {dest}")
    return True


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry"
    only = sys.argv[2] if len(sys.argv) > 2 else None
    jobs = {k: v for k, v in JOBS.items() if not only or k.startswith(only)}
    os.makedirs(OUT, exist_ok=True)
    if mode == "dry":
        for tag, prompt in jobs.items():
            print(f"\n===== {tag} =====\n{prompt}\n")
        print(f"{len(jobs)} prompt(s). gen cost ~ ${len(jobs)*COST_PER_IMAGE:.2f} "
              f"(verify on fal.ai dashboard)")
        return
    print(f"About to gen {len(jobs)} thumbnail(s) ~ ${len(jobs)*COST_PER_IMAGE:.2f} "
          f"via fal gpt-image-2 ({SIZE})")
    key = load_key()
    ok = 0
    for tag, prompt in jobs.items():
        if gen_one(key, tag, prompt):
            ok += 1
    print(f"done: {ok}/{len(jobs)} -> {OUT}")


if __name__ == "__main__":
    main()
