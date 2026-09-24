# Brief: ILAG trailer, round 5b (2 images, runner-ready)

The CEO on round 4, 2026-09-24: "7 ชอบมุมนี้มากๆ น้ำและแสงฟ้าผ่าสีม่วง สวยมาก แต่อสุรกายไม่ผ่าน · 8 ฉากนี้ดีมาก
แต่ดวงตาใหญ่กว่านี้ และ Design Monster ตามแบบที่ส่งให้ มันต้องหน้าแบบนั้น มันดูหลอนไปเลย".
The new monster is `creature_v2` from round 5a. Each ATTACH is ONE picture holding two parts side by side:
LEFT = the round-4 shot whose composition we keep, RIGHT = the creature_v2 design sheet (`refs/creature_v2.jpg`).

```
python tools/chatgpt_images.py --brief docs/ops/briefs/ilag-trailer-round5b.md --out <out dir>
```

---

## Image 1: crt_mountain_horizon_v2

ATTACH: docs/promo/topview-trailer/refs/ref5b_mountain_plus_creature.jpg

PROMPT START
The attached picture has two parts. LEFT: a film still whose camera angle, composition, dark water, storm clouds and violet lightning must be kept exactly. RIGHT: the design sheet of our sea monster (smooth dark slate-blue skin with almost no detail, a broad flat head, a wide mouth, two enormous glowing pale yellow-green eyes with thin vertical slit pupils). Make ONE single film still, not two panels: recreate the LEFT scene with the same composition, but instead of the distant mountain range on the horizon, the monster from the RIGHT is rising there: the top of its colossal smooth head breaks the surface on the far horizon, as wide as a mountain range, and its two huge eyes glow pale yellow-green through the rain and the dark. In the foreground, far away and seen from behind, a tiny glowing manta-like sea creature carrying three small riders, a speck on the dark water. Awe and dread, horror film mood. Cinematic photorealistic, landscape 3:2, no text, no watermark.
PROMPT END

## Image 2: crt_eye_v2

ATTACH: docs/promo/topview-trailer/refs/ref5b_eye_plus_creature.jpg

PROMPT START
The attached picture has two parts. LEFT: a film still whose darkness, night ocean, water pouring off the creature and faint bioluminescence must be kept. RIGHT: the design sheet of our sea monster (smooth dark slate-blue skin with almost no detail, a broad flat head, a wide mouth, two enormous glowing pale yellow-green eyes with thin vertical slit pupils). Make ONE single film still, not two panels: the monster from the RIGHT, not a crocodile. Its broad smooth face rises just out of the black ocean at night, water streaming off it, and BOTH eyes are open and staring straight into the camera, each eye far bigger than in the LEFT picture, bigger than a whole village, glowing pale yellow-green with thin vertical slit pupils. Haunting, terrifying, silent. Cinematic photorealistic, landscape 3:2, no text, no watermark.
PROMPT END
