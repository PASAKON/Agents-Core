#!/usr/bin/env python3
"""Gen MODELER reference sheets for the Minecraft Frost Knight product.

Purpose: hand these to a 3D modeler so they clearly understand the SIZE and the
identity (เอกลักษณ์) of each weapon + the boss. So every sheet ALSO shows a
standard Minecraft player character (Steve-style) standing beside the subject as
a SCALE reference. The boss sheet shows the full BOSS MODEL + its ice sword.

Default batch = the 4 hero references (tier-3 / legendary look):
  archer-bow-t3, knight-sword-t3, wizard-staff-t3, boss-icesword-t3
The lower tiers (t1/t2) exist for later upgrade-art if wanted.

Model: fal openai/gpt-image-2 (T2I). Plain studio background, Minecraft blocky.

  python scripts/frost_knight_weapons.py dry           # prompts + cost, no spend
  python scripts/frost_knight_weapons.py gen t3        # the 4 hero sheets (~$0.88)
  python scripts/frost_knight_weapons.py gen archer    # all archer tiers
  python scripts/frost_knight_weapons.py gen           # everything (10, ~$2.20)
"""
import sys, os, json, re, urllib.request, urllib.error

OUT = "/Users/gob/MoonieXHQ/Agents/Core/output/minecraft-frost-knight/weapons"
ENV = "/Users/gob/MoonieXHQ/Projects/MoonieX/ClaudeFlow/.env"
T2I_EP = "https://fal.run/openai/gpt-image-2"
SIZE = "square_hd"
COST_PER_IMAGE = 0.22           # square high; verify on fal.ai dashboard

BASE = (
    "Minecraft Bedrock Edition style REFERENCE SHEET for a 3D modeler. Plain neutral "
    "light-grey studio background, even studio lighting, BLOCKY low-poly voxel Minecraft "
    "shapes with clear readable texture detail. "
    "SCALE REFERENCE (important): also include a standard DEFAULT Minecraft player "
    "character (Steve-style, neutral skin, normal player height) standing beside the "
    "subject at correct relative scale, so the modeler can judge the real SIZE. "
    "3/4 side view, full subjects visible head to toe. "
    "NO text, NO letters, NO numbers, NO logo, NO watermark. "
)

TIERS = {
    "t1": ("TIER 1 (COMMON): basic plain materials, simple shape, minimal detail, NO "
           "glow, muted dull colors."),
    "t2": ("TIER 2 (RARE): polished higher-quality materials, metal/silver trim and "
           "engraved accents, a subtle magical glow, richer color — clearly upgraded."),
    "t3": ("TIER 3 (LEGENDARY, premium): ornate signature engravings, inlaid gemstones, "
           "gold accents, a strong magical glow and energy aura, pristine epic finish — "
           "the most beautiful and detailed version, with a clear unique identity."),
}

CLASS_WEAPONS = {
    "archer-bow": ("a GREEN ARCHER LONGBOW: wooden limbs, green signature theme, a "
                   "bowstring, an elegant ranger weapon"),
    "knight-sword": ("a KNIGHT GREATSWORD: a broad metal blade, crossguard and wrapped "
                     "grip, a heroic STEEL weapon (steel, clearly NOT ice)"),
    "wizard-staff": ("a WIZARD STAFF: a shaft topped by a glowing crystal orb in metal "
                     "prongs, carved with arcane runes"),
}

# Boss sheet = the full BOSS MODEL + its weapon + scale character.
BOSS_SHEET = (
    "Show the FULL BOSS MODEL together with his weapon AND the standard player character "
    "for scale. The boss is an ORIGINAL ice villain 'Frost Knight' (NOT the Lich King): a "
    "TOWERING knight of cracked blue ice and dark frostbitten plate armor, ALWAYS wearing "
    "a shining GOLD CROWN, holding a MASSIVE ICE GREATSWORD as tall as a player, with "
    "glowing pale-blue runes and frost vapor. The boss must clearly TOWER over the normal "
    "player character beside him (roughly 2-3x player height) so his huge size is obvious. "
    "Show the boss's silhouette, armor identity and proportions clearly. "
) + TIERS["t3"]

JOBS = {}
for wk, wdesc in CLASS_WEAPONS.items():
    for tk, tdesc in TIERS.items():
        JOBS[f"{wk}-{tk}"] = BASE + (
            f"The hero subject is {wdesc}, shown upright at full size next to the standing "
            f"player character for a clear height comparison. {tdesc}")
JOBS["boss-icesword-t3"] = BASE + BOSS_SHEET


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
    jobs = {k: v for k, v in JOBS.items() if not only or only in k}
    os.makedirs(OUT, exist_ok=True)
    if mode == "dry":
        for tag, prompt in jobs.items():
            print(f"\n===== {tag} =====\n{prompt}\n")
        print(f"{len(jobs)} prompt(s). gen cost ~ ${len(jobs)*COST_PER_IMAGE:.2f} "
              f"(verify on fal.ai dashboard)")
        return
    print(f"About to gen {len(jobs)} sheet(s) ~ ${len(jobs)*COST_PER_IMAGE:.2f} "
          f"via fal gpt-image-2 ({SIZE})")
    key = load_key()
    ok = 0
    for tag, prompt in jobs.items():
        if gen_one(key, tag, prompt):
            ok += 1
    print(f"done: {ok}/{len(jobs)} -> {OUT}")


if __name__ == "__main__":
    main()
