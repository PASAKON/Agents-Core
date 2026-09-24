# Brief: ILAG trailer, round 6 (5 images, runner-ready)

CEO review of round 5, 2026-09-25 (numbers = the round-5 contact sheet):
"1 ไม่ผ่าน เหมือนเลียนแบบเขามาเลย ไม่เอาตัดทิ้ง · 2 ผ่านในมุมมองนี้ แต่ควรไม่เห็นดวงตา ให้ 3 คนนั้นสงสัยว่ามันคือเกาะ
หรืออะไร · 3 ขาดความม่วง แต่มุมมองนี้น่ากลัวมาก ผ่านในเรื่องของรูปทรงและมุมมอง ไม่ผ่านในเรื่องของสี ขาดม่วง ·
4 5 6 7 ผ่าน · 8 ตัวจันทร์ต้องขนาดครึ่งนึงของโลก · 9 ผ่าน 10 ผ่าน". New: "ขอพายุเหนือจินตนาการหน่อย ไม่ได้มีลูกเดียว
แต่เป็นลูกเล็กๆ แต่ไม่ใช่ลมแรง เหมือนมันเกิดธรรมชาติของมันอยู่แล้ว หลายๆ ก้อน พายุผอมทรงกระบอก (ไม่ใช่ทรงกรวย)
สูงถึงเมฆเลย และใต้พายุติดน้ำ มีน้ำวนเล็กน้อย theme ใช้ Turning ในรูป 9".

`creature_v2` is REJECTED (too close to the CEO's web references): never attach it or its composites again.
Images 1-3 CONTINUE the round-5 chat of the named image (same chat, text only), so everything not named stays.

```
python tools/chatgpt_images.py --brief docs/ops/briefs/ilag-trailer-round6.md --out <out dir with the round-5 ledger>
```

---

## Image 1: crt_mountain_horizon_v3

CONTINUE: crt_mountain_horizon_v2

PROMPT START
Keep this exact image: the same composition, camera, dark water, storm clouds, violet lightning and the tiny manta with three riders. Change only one thing: remove the glowing eyes completely. The dark shape on the horizon must show no eyes and no face at all; it should read as a vast dark island or a mountain range standing where no land should exist, so the three riders, and the viewer, cannot tell what it is. Keep its smooth dark silhouette and size. Same aspect ratio, landscape 3:2.
PROMPT END

## Image 2: crt_eye_v3

CONTINUE: crt_eye_v2

PROMPT START
Keep this exact image: the same monster face and eyes, the same framing, camera angle and water pouring off it. Change only the colour: bring in strong VIOLET. Violet lightning cracking across the sky behind it, violet storm light on the clouds and on its wet skin, magenta and violet bioluminescence glowing in the water and the spray, deep indigo-violet shadows. The eyes stay pale yellow-green. Same aspect ratio, landscape 3:2.
PROMPT END

## Image 3: planet_from_space_v2

CONTINUE: planet_from_space

PROMPT START
Keep this exact image: the same blue ocean planet with no land, the same clouds, space, stars and lighting. Change only the moon: it must be exactly HALF the planet's diameter (its width is half the planet's width), still very close beside the planet, the same pale grey cratered look, fully inside the frame. Same aspect ratio, landscape 3:2.
PROMPT END

## Image 4: loc_storm_pillars_A

ATTACH: docs/promo/topview-trailer/refs/colour_script.jpg

PROMPT START
Use ONLY panel 02 TURNING of the attached image for colour and light: a violet-grey bruised sky, the huge moon dim behind thin cloud, deep indigo water, cool silver light. Do not copy its layout. Cinematic photorealistic environment, landscape 3:2, no characters, no creatures. On an alien ocean planet with no land, a natural phenomenon beyond imagination: dozens of small storms stand on the sea at the same time, spread across the ocean all the way to the horizon. Each storm is a SLENDER, STRAIGHT, CYLINDER-shaped column of slowly swirling cloud and rain, the same width from bottom to top (not a funnel, not a cone, not a tornado), rising all the way up into the cloud ceiling. They are calm and silent, not violent: the air around them is still and the sea is mostly smooth, as if these pillars were simply part of this planet's nature. Where each column meets the sea, the water turns in a small, gentle whirlpool. Seen from just above the water, the pillars receding into the distance. Eerie, beautiful, otherworldly. High-end sci-fi film still, no text, no watermark.
PROMPT END

## Image 5: loc_storm_pillars_B

ATTACH: docs/promo/topview-trailer/refs/colour_script.jpg

PROMPT START
Use ONLY panel 02 TURNING of the attached image for colour and light: a violet-grey bruised sky, the huge moon dim behind thin cloud, deep indigo water, cool silver light. Do not copy its layout. Cinematic photorealistic environment, landscape 3:2, no characters, no creatures. High aerial view over an alien ocean planet with no land: dozens of small storms stand on the sea at the same time, scattered across the ocean to the horizon like a forest of pillars. Each storm is a SLENDER, STRAIGHT, CYLINDER-shaped column of slowly swirling cloud and rain, the same width from bottom to top (not a funnel, not a cone, not a tornado), rising up into the cloud ceiling. Calm and silent, not violent, as if they were simply part of this planet's nature. At the base of each column a small, gentle whirlpool turns on the water. Eerie, beautiful, otherworldly. High-end sci-fi film still, no text, no watermark.
PROMPT END
