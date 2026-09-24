# Brief: ILAG trailer, round 9 (5 images, runner-ready)

CEO review of round 8, 2026-09-25: "ชอบไอเดียที่เด็กเห็นปลาที่เรืองแสงในน้ำ · แมงกะพรุนอยากให้ออกแบบ design ใหม่
ไม่เอาเหมือนในโลกของเรา เอาเหนือจินตนาการไปเลย ใหญ่ดีแล้ว ผิวมองทะลุและใส ถูกแล้ว · 1 and 2 reject · 3 กับ 4
ตัดเหลือ ใสสุดกับดำสนิทไปเลย เรามีเวลาเล่าน้อย · ดำสนิทจะต้องมีพายุ และเมฆม่วง ฟ้าผ่าสีม่วง เส้นแบ่งชัดเจน ·
โลกขอเป็นโลกที่แบ่ง 2 ซีก เป็น 2 สีชัดเจน สีดำออกม่วงมีพายุ กับสีฟ้าขาวสดใส".
Images 2-4 CONTINUE their round-8/6 chats (same chat, text only); 1 and 5 are new chats.

```
python tools/chatgpt_images.py --brief docs/ops/briefs/ilag-trailer-round9.md --out <out dir with the earlier ledger>
```

---

## Image 1: crt_jellyfish_v2

PROMPT START
Creature design sheet, landscape 3:2, plain black background so the glow shows, even lighting, no scene. Four DIFFERENT species of giant drifting sea creatures from an alien ocean planet that fill the role of jellyfish, but look like NOTHING on Earth: no bell-and-tentacle shape, no Earth jellyfish, no squid, no octopus. Beyond imagination, otherworldly and beautiful. Each one is enormous, as big as a house or bigger, with a tiny manta-like sea creature beside it for scale, and has TRANSLUCENT, SEE-THROUGH skin like clear glass or soap film, so its glowing inner organs and light show through, shimmering in iridescent rainbow colours. Each panel titled top-left in bold sans-serif:
01 SPIRAL: a slowly turning corkscrew of glass-clear membrane, light running along it like a current
02 CATHEDRAL: a floating dome built of layered translucent veils like stacked petals, a rainbow core glowing inside
03 HALO: a set of floating rings of clear membrane, one inside another, trailing threads of light
04 BLOOM: a vast floating flower of transparent petals that slowly opens and closes, seeds of light drifting from it
Cinematic photorealistic creature design, no text other than the labels, no watermark.
PROMPT END

## Image 2: loc_water_zones_v2

CONTINUE: loc_water_zones

PROMPT START
We only have time for two states. Redo this as TWO panels only, same camera just above the surface looking down into the water. Panel 01 VERY CLEAR: keep it exactly as it is, glass-clear turquoise water over a pale sandy seabed with coral, bright blue-white daylight. Panel 02 PITCH BLACK: the deep water, black as ink, nothing visible below the surface, under a dark storm: purple-black clouds, violet lightning reflected on the black water, rain. Each panel titled top-left in bold sans-serif. Landscape 3:2, no other text, no watermark.
PROMPT END

## Image 3: loc_deep_line_v2

CONTINUE: loc_deep_line

PROMPT START
Keep this exact composition, camera and the sharp line across the sea, and the tiny manta with three riders stopped at the line. Change both sides to the extremes: the near side is the clearest possible water, glass-clear bright turquoise over a pale sandy seabed, under a brilliant blue-white sky with the huge close moon. The far side is PITCH BLACK water, black as ink, under a violent storm: purple-black clouds, violet lightning striking the black sea, rain sweeping. The line between the two must be razor sharp, sea and sky both. Same aspect ratio, landscape 3:2.
PROMPT END

## Image 4: planet_from_space_v3

CONTINUE: planet_from_space_v2

PROMPT START
Keep this exact image: the same framing, space, stars, the moon at half the planet's size and its position. Change the planet: it is split into TWO HEMISPHERES of clearly different colour, with a sharp, clean dividing line between them. One half is bright blue-white and clear: glowing turquoise ocean with white clouds. The other half is black tinged with purple, covered in a storm: dark violet cloud masses with violet lightning flickering inside them. No land anywhere. Same aspect ratio, landscape 3:2.
PROMPT END

## Image 5: crt_glowfish_child

ATTACH: docs/promo/topview-trailer/refs/char_young.jpg

PROMPT START
Use the attached image ONLY for the look of the young character (same species, face, colours and gill mane). Cinematic photorealistic underwater film still, landscape 3:2. In glass-clear turquoise shallow water over a pale sandy seabed, bright blue-white light falling from the surface, the young one floats still, eyes wide, its gill frills glowing softly gold. In front of it, a shoal of small fish glow faintly gold and silver in the water, a light so faint that only this child can see it. Wonder, stillness, a secret gift. No text, no watermark.
PROMPT END
