# Brief: ILAG trailer, round 7 (4 images, runner-ready)

CEO review of round 6, 2026-09-25: "1 ผ่านนะ แต่ 2 มันดูตลกเลย ม่วงเกินไป · 3 โอเค · 4 ชอบมาก แต่ถ้าทรงกระบอก
เล็กกว่านี้และยาวขึ้นไปสุดท้องฟ้าเลยจะดีมาก อยากให้มันดูสูงมากๆ เมื่อเทียบกับคน".
Two options for each fix, so he can choose. 1 and 3 CONTINUE the round-5 chat of crt_eye_v2 (no violet yet) and the
round-6 chat of crt_eye_v3 (too violet); 3 and 4 work from loc_storm_pillars_A.

```
python tools/chatgpt_images.py --brief docs/ops/briefs/ilag-trailer-round7.md --out <out dir with the round-5/6 ledger>
```

---

## Image 1: crt_eye_v4a

CONTINUE: crt_eye_v2

PROMPT START
Keep this exact image: the same monster face and eyes, framing, camera angle, the dark natural skin and the water pouring off it. Add only a TOUCH of violet, subtle and realistic: a few thin violet lightning bolts far away in the storm clouds behind it, a faint cold violet rim light along the top edges of its head from that lightning, and a few magenta-violet glints of bioluminescence in the spray. The skin stays dark slate-blue, the sea stays dark indigo-black, the eyes stay pale yellow-green. It must look like a real film still, grounded and terrifying, not stylised and not neon. Same aspect ratio, landscape 3:2.
PROMPT END

## Image 2: crt_eye_v4b

CONTINUE: crt_eye_v3

PROMPT START
This is far too purple and looks cartoonish. Keep the same monster, framing and camera, but reduce the violet by about 70 percent: the skin goes back to a dark natural slate-blue with no purple tint, the sea back to dark indigo-black, and violet remains only in the lightning in the sky and a few faint glints in the spray. Eyes stay pale yellow-green. Realistic, grounded, terrifying film still, not neon. Same aspect ratio, landscape 3:2.
PROMPT END

## Image 3: loc_storm_pillars_A_v2

CONTINUE: loc_storm_pillars_A

PROMPT START
I love this image. Keep the same palette, light, moon, clouds, sea and camera. Change the storm pillars: make every column much THINNER and much TALLER, a slender straight cylinder of swirling cloud and rain that rises from the sea all the way up to the very top of the sky and out of the frame, so they look impossibly tall. Keep the small gentle whirlpool where each touches the water. Add, in the middle distance on the water, a tiny glowing manta-like sea creature carrying three small riders, dwarfed by the nearest pillar, so the height reads against a person. Same aspect ratio, landscape 3:2.
PROMPT END

## Image 4: loc_storm_pillars_A_v3

ATTACH: docs/promo/topview-trailer/refs/loc_storm_pillars_A.jpg

PROMPT START
Use the attached image for its palette, light, moon, clouds and sea. Cinematic photorealistic film still, landscape 3:2. Low camera just above the water, tilted up. On an alien ocean planet with no land, dozens of calm storm pillars stand on the sea: each one a very THIN, perfectly straight cylinder of slowly swirling cloud and rain, the same width from bottom to top (not a funnel, not a cone, not a tornado), rising from the water up and up until it vanishes into the highest sky beyond the top of the frame, impossibly tall. The air is still; at the base of each pillar the water turns in a small, gentle whirlpool. In the foreground a tiny glowing manta-like sea creature carrying three small riders glides between two pillars, the riders looking up, dwarfed. Awe, silence, otherworldly scale. No text, no watermark.
PROMPT END
