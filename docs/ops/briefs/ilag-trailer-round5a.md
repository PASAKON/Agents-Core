# Brief: ILAG trailer, round 5a (6 images, runner-ready)

CEO review of round 4, 2026-09-24 (numbers = the round-4 contact sheet):
"1 2 3 ผ่าน · 5 สวย ... เล็กไปด้วยซ้ำ อยากให้ดูน่ากลัวและใหญ่กว่านี้ · 6 รายละเอียดของตัว Model มันเยอะไป
เอาแบบเรียบๆ และอยากได้แบบดูน่ากลัวกว่านี้มากๆ อย่าง 2 รูปหลังที่ส่งไป · 7 ชอบมุมนี้มากๆ ... แต่อสุรกายไม่ผ่าน ·
8 ฉากนี้ดีมาก แต่ดวงตาใหญ่กว่านี้ และ Design Monster ตามแบบที่ส่งให้ ... มันดูหลอนไปเลย · 9 ที่อยู่บนหลัง
ปลากระเบน ... เป็นไม้สักสวยงามเกินไป มันต้องดูประดิษฐ์ประดอยกว่านี้หน่อย · 11 12 เพิ่มหมู่บ้าน บันไดปีนขึ้น
ท่าจอดกระเบน (ไม่มีเรือ เขาใช้กระเบนเรืองแสงเป็นพาหนะกัน) · 13 ผ่าน". Plus a new shot: "ดาวดวงนี้ในมุมมอง
นอกอวกาศ ที่เป็นสีฟ้าทั้งดวง เอาไว้ใช้ตอนซูมออกมา และอย่าลืมดวงจันทร์ที่ใกล้ดาวดวงนี้ด้วย".

7 and 8 need the new monster design, so they are round 5b, run after this one with the new creature attached.

`refs-ceo/monster_moodboard.jpg` = the CEO's two reference pictures side by side (third-party images from the web,
kept only on the runner box, not in git). Every other ATTACH is our own image in `docs/promo/topview-trailer/refs/`.

```
python tools/chatgpt_images.py --brief docs/ops/briefs/ilag-trailer-round5a.md --out <out dir>
```

---

## Image 1: creature_v2

ATTACH: refs-ceo/monster_moodboard.jpg

PROMPT START
Use the two attached pictures ONLY as mood and design reference for how the monster's face should feel: a colossal face looming under dark water, enormous glowing eyes with slit pupils, a wide dark mouth, simple smooth shapes, pure dread. Do not copy them; design our own creature. Creature design sheet, landscape 3:2, dark charcoal background, even lighting. A primordial sea monster of unimaginable size: it is to a person what the Sun is to the Earth. SIMPLE, SMOOTH design with very little surface detail: dark slate-blue skin, almost featureless, no barnacles, no spikes, no plates, no patterns, no glowing lights on the body; a broad flat head, a wide lipless mouth, and two enormous eyes glowing pale yellow-green with thin vertical cat-like slit pupils. Silent, haunting, terrifying. It lives under the water; we mostly see its face and eyes beneath the surface. Four views, each titled top-left in bold sans-serif:
01 FROM ABOVE: its face beneath the surface of a dark blue ocean seen from straight above, a tiny glowing manta-like sea creature carrying three small riders swims over it, a speck, each eye far bigger than the manta
02 UNDERWATER FRONT: only the two glowing eyes and the faint outline of the face in black water, a few tiny fish in front of it for scale
03 SIDE SILHOUETTE: its head rising under the sea, a tiny village of trees on the surface above it for scale, the village barely a speck
04 THE EYE: one eye filling the panel, pale yellow-green glow, vertical slit pupil
Cinematic photorealistic, horror film mood, no text other than the labels, no watermark.
PROMPT END

## Image 2: loc_giant_waves_v2

ATTACH: docs/promo/topview-trailer/refs/loc_giant_waves.jpg

PROMPT START
Keep the look of the attached image: the same dark indigo water, the cyan and magenta bioluminescence glowing inside the waves like drifting jellyfish, the violet-grey sky, the moon behind storm cloud and the violet lightning. Change the scale: the waves must be COLOSSAL and terrifying, walls of water hundreds of metres tall towering over the whole frame and curling overhead, rising steeply against the wind. At the bottom of the frame, dwarfed, a tiny glowing manta-like sea creature carrying three small riders, a speck in front of the wall of water, so the scale reads at once. Low camera looking up. Horror, awe, impossible scale, dark with colourful accents. Cinematic photorealistic film still, landscape 3:2, no text, no watermark.
PROMPT END

## Image 3: char_mount_v3

ATTACH: docs/promo/topview-trailer/refs/char_mount_v2.jpg

PROMPT START
Keep this exact creature: the same body, colours, glow, camera views and panel layout. Change only the seat on its back, which now looks too polished, like fine teak furniture. Replace it with a howdah HAND-BUILT by a sea people who have no land and no trees to saw, from what the ocean gives them: weathered grey driftwood branches lashed together with woven green kelp rope, pale bone ribs as the backrest, a rim of seashells, small glowing golden seed pods tied on as lamps, tufts of neon-green glowing grass at the corners, carved wave glyphs, knots and bindings everywhere. Intricate, handmade, a little rough and uneven, clearly crafted with care; not factory-made, not polished. Room for three small riders, a small driver's perch at the front near the head, held on by kelp straps wrapped under the body. No riders. Plain white background, the same labeled views as before, landscape 3:2.
PROMPT END

## Image 4: loc_village_above_A_v2

ATTACH: docs/promo/topview-trailer/refs/loc_village_above_A.jpg

PROMPT START
Keep this exact village: the same giant mangrove-like trees, wooden houses, glowing neon-green grass, sky, moon, water and camera angle. ADD the signs of everyday life of an amphibious people who have no boats: ladders and steps climbing from the water up the stilt roots and trunks to the houses (rope ladders, wooden pegs driven into the trunks, carved steps), rope bridges between the trees, and a MANTA DOCK at water level: a floating landing platform of lashed driftwood where several glowing manta-like sea creatures (wide wings, soft lime-green glow underneath, hand-built driftwood seats on their backs) are moored with kelp ropes, like horses at a hitching rail. No boats anywhere. No villagers. Cinematic photorealistic, landscape 3:2, no text, no watermark.
PROMPT END

## Image 5: loc_village_above_B_v2

ATTACH: docs/promo/topview-trailer/refs/loc_village_above_B.jpg

PROMPT START
Keep this exact village and the same high aerial view: the same giant mangrove-like trees, wooden houses, rope bridges, glowing neon-green grass, sky, moon and water. ADD the signs of everyday life of an amphibious people who have no boats: ladders and steps climbing from the water up the stilt roots and trunks to the houses (rope ladders, wooden pegs driven into the trunks, carved steps), and a MANTA DOCK at water level: a floating landing platform of lashed driftwood where several glowing manta-like sea creatures (wide wings, soft lime-green glow underneath, hand-built driftwood seats on their backs) are moored with kelp ropes, like horses at a hitching rail. No boats anywhere. No villagers. Cinematic photorealistic, landscape 3:2, no text, no watermark.
PROMPT END

## Image 6: planet_from_space

ATTACH: docs/promo/topview-trailer/refs/loc_open_sea.jpg

PROMPT START
Use the attached image ONLY for the look of the moon: pale grey-white, heavily cratered, sharply detailed. Cinematic photorealistic space shot, landscape 3:2. An alien ocean planet seen from space, entirely covered by water: the whole globe is blue, deep sapphire and turquoise, with swirling white cloud bands; no land, no continents, no islands anywhere; a thin glowing blue atmosphere along its rim. Very close to it hangs its huge moon, so near that it looks almost as big as the planet, both in the same frame. Black space, faint stars, sunlight from one side. Majestic and lonely. High-end sci-fi film still, no text, no watermark.
PROMPT END
