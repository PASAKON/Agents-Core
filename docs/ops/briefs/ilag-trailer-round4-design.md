# Brief: ILAG trailer, round 4 design plates (8 images, runner-ready)

CEO, 2026-09-24: "ทำตัวละครให้ครบก่อนเลย ชาวบ้าน Prop ต่างๆ location กลางทะเล สีพื้นหลังที่เปลี่ยนไป
คลื่นสูงมหึมา และปีศาจ อสุรกาย ตัวเท่าดวงอาทิตย์". Looks: `docs/promo/topview-trailer/BIBLE.md`.
Approved so far: `char_young`, `char_elder` (round 1). Small reference copies of earlier plates live in
`docs/promo/topview-trailer/refs/` so any machine can attach them.

Run from the repository root (ATTACH paths are relative to it):

```
python tools/chatgpt_images.py --brief docs/ops/briefs/ilag-trailer-round4-design.md --out <out dir>
```

Never overwrite an existing file. The runner stops on a paywall, usage limit or login prompt.

---

## Image 1: villagers

ATTACH: docs/promo/topview-trailer/refs/char_young.jpg

PROMPT START
Character lineup reference sheet, landscape 3:2. Plain white/light-grey studio background, even soft studio lighting, no props beyond what each carries, no scene. Six villagers of the SAME alien species as the attached character (same face shape, large round glossy eyes, frilly axolotl-like gill mane, slightly translucent skin with tiny glowing freckles, webbed three-fingered hands, webbed feet, short tail fin), standing side by side in one row, full body, each a different individual, each numbered below in bold sans-serif:
01 a small child, pale mint-green skin, pink gill frills
02 a young woman, lavender skin, peach gill frills, a necklace of woven kelp flowers
03 an old woman, pale blue skin, white gill frills, leaning on a curved driftwood stick
04 a middle-aged man, sand-yellow skin, teal gill frills, a woven basket of softly glowing golden seed pods on his hip
05 a teenager, soft orange skin, yellow gill frills, a small fishing net over one shoulder
06 a mother, rose skin, violet gill frills, holding a tiny baby of the same species
All cheerful and relaxed. Cinematic photorealistic creature design, high-end sci-fi VFX film quality, not cartoon, not anime. No text other than the numbers, no watermark.
PROMPT END

## Image 2: props

PROMPT START
Prop reference sheet, landscape 3:2. Plain white/light-grey studio background, even soft studio lighting, no characters, no scene. Five props, each titled top-left in bold sans-serif:
01 SEED LANTERN FULL: a lantern made from a clear glass-like seashell with a woven kelp handle, holding three softly glowing golden seed pods, warm light inside
02 SEED LANTERN EMPTY: the same lantern, empty and dark, a faint dusty residue inside
03 GLOW-SEED POD: a single seed pod the size of a plum, translucent skin, glowing soft gold from inside, a short curled stem
04 STEERING POLE: a long pale bone-like pole, carved with simple wave patterns, a woven grip near the top
05 SEED-HUSK NECKLACE: a necklace of dry brown seed husks strung on kelp twine
Cinematic photorealistic prop design, detailed materials, no text other than the labels, no watermark.
PROMPT END

## Image 3: loc_open_sea

ATTACH: docs/promo/topview-trailer/refs/loc_village_above_A.jpg

PROMPT START
Use the attached image ONLY for its sky, moon, light and water colour; do not include its trees, houses or roots. Cinematic photorealistic environment, landscape 3:2. No characters, no creatures, no trees, no land anywhere. Endless open ocean on an alien planet that has no land at all, gentle swells to every horizon, the same bright blue-white daytime sky with faint stars and the same huge moon hanging very close to the planet, enormous and sharply detailed. Seen from just above the water. Calm, vast, beautiful and a little lonely. High-end sci-fi film still, anamorphic lens feel, no text, no watermark.
PROMPT END

## Image 4: colour_script

ATTACH: docs/promo/topview-trailer/refs/loc_village_above_A.jpg

PROMPT START
Use the attached image ONLY for the look of the sky, moon and water in panel 01. Colour script, landscape 3:2, three vertical panels showing the SAME open-ocean view on an alien planet with no land, no characters, the huge close moon in the sky, each panel titled top-left in bold sans-serif:
01 DAY: bright blue-white sky like a brilliantly lit night, faint stars, turquoise water, calm
02 TURNING: at midday the sky bruises to violet-grey, the moon dims behind thin cloud, the water turns deep indigo, wind lifts spray, the first unnatural swell rises
03 DARK: the sea almost black under a dark sky, lit only by bioluminescence in the water, cyan, magenta and amber glows, violet lightning far away
Cinematic photorealistic, no text other than the labels, no watermark.
PROMPT END

## Image 5: loc_giant_waves

PROMPT START
Cinematic photorealistic environment, landscape 3:2. No characters, no creatures. The open ocean of an alien planet with no land, gone wrong: colossal waves many times taller than a forty-metre tree, rising steeply AGAINST the direction of the wind, walls of dark indigo water with streaks of cyan and magenta bioluminescence glowing inside them, spray torn sideways, a violet-grey sky, a huge moon half hidden behind storm cloud, violet lightning. The scale must feel impossible and wrong. Dark with colourful accents. High-end sci-fi film still, no text, no watermark.
PROMPT END

## Image 6: creature_sheet

PROMPT START
Creature design sheet, landscape 3:2, plain dark charcoal background so its glowing patterns show, even lighting, no scene. A primordial sea creature of unimaginable size: it is to a person what the Sun is to the Earth. Its body is so vast that its back reads as a mountain range: ancient dark stone-like hide crusted with fossil reef, forests of barnacles and its own drifting clouds; along its flanks rows of bioluminescent patterns in cyan, magenta and amber that glow like the lights of a city at night; one enormous eye, a slow amber disc. Ancient, calm, overwhelming. Not a dragon, not a whale, not a kaiju. Four views, each titled top-left in bold sans-serif:
01 FULL SIDE SILHOUETTE, with a tiny village of trees drawn beside it for scale, the village barely a speck
02 ITS BACK AS A MOUNTAIN RANGE rising from the sea
03 THE EYE, amber, filling the panel
04 SKIN DETAIL, barnacle forests and glowing lights
Cinematic photorealistic creature design, no text other than the labels, no watermark.
PROMPT END

## Image 7: crt_mountain_horizon

PROMPT START
Cinematic photorealistic film still, landscape 3:2. On an alien planet with no land, only ocean, a dark mountain range stands on the far horizon where no land should exist, under a dark violet sky; faint cyan and magenta lights glow along its slopes like a distant city; clouds cling to its peaks. In the foreground, far away and seen from behind, a tiny manta-like sea creature carrying three small riders is a speck on dark water. The mountain is a living creature's back, but the viewer must not be sure yet. Awe and dread. High-end sci-fi film still, no text, no watermark.
PROMPT END

## Image 8: crt_eye

PROMPT START
Cinematic photorealistic film still, landscape 3:2. In a dark ocean at night an eye opens on the side of a colossal ancient creature: a slow amber disc of light far bigger than a whole village, its iris textured like molten glass, its lids of barnacle-crusted stone-like hide, cyan and magenta bioluminescent patterns glowing around it, sea water streaming off. No characters. Overwhelming scale, quiet menace. High-end sci-fi film still, no text, no watermark.
PROMPT END
