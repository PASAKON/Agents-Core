# Job: make the best-looking 10-second TikTok finance-news clip you can

You are the editor AND the motion designer. There is no template, no layout rule, no checker. You choose the pacing,
the cuts, the motion, the type, the transitions, the colour treatment. Make it look like the top finance-news / drama
accounts on TikTok Thailand: a strong first frame that stops the scroll, fast and confident cuts on the voice,
punchy kinetic Thai type, numbers that hit, and real movement in every second. Surprise me.

Story (BLACK LIQUIDITY channel, episode 62): a woman trader says the broker CXM refused to pay her almost 6 million
baht of profit, accusing her of "toxic trading" for trading too fast, although she says she held the order for 2 hours.
Everything is "according to her post" (ตามที่เจ้าของโพสต์เล่า): a claim, not a proven fact.

## Canvas and sound
- 1080 x 1920, 30 fps, exactly 10.0 s (300 frames).
- Sound: `voice-10s.wav` (10.0 s, Thai narration, starts at 0). Do not re-time it. What is said, roughly:
  - 0.0–1.0 s: lead-in
  - 1.0–3.6 s: "ถือออเดอร์สองชั่วโมง แต่โดนข้อหาเทรดเร็วเกินไป?"
  - 3.6–6.4 s: "เธอเล่าว่าซีเอ็กซ์เอ็มไม่จ่ายกำไรเกือบหกล้านบาท"
  - 6.4–9.3 s: "ซีเอ็กซ์เอ็มแจ้งในอีเมลว่าเป็นท็อกซิกเทรดดิ้ง"
  - 9.3–10.0 s: silence
  Put on-screen words on the beats where they are spoken. Write the broker as "CXM" on screen.

## Footage you have (all owned by us, use any of it, as much or as little as you like)
- `avatar-lipsync-0-10s.mp4`: 640x1024, the presenter (sunglasses, beanie) lip-synced to `voice-10s.wav` for the WHOLE
  10 s. Its time must equal the timeline time wherever you show it (if a shot of it starts at t seconds, start inside the
  file at t seconds), otherwise the lips do not match. Scale it up as you like (it is low-res, so it looks best as a
  full-frame shot with grading, or as a cut-out style frame, not tiny).
- `stills/cxm-post-claim.png`, `stills/cxm-post-account.png`, `stills/cxm-post-full.png`: 1080x1920 screenshots of
  her Facebook post (white text band on black). Useful text lines in them are around y 760..1160.
- `broll/` (1080x1920, 8 s, 24 fps, no sound): `hourglass-red-sand`, `red-digital-countdown`, `finger-taps-red-lock`,
  `red-forbidden-icon-glow`, `gold-bar-in-glass-cube`, `typewriter-red-neon-ticker-tape`, `contract-signature-wax-seal`.
  All dark, red/black/gold. Speed-ramp, crop, zoom, split-screen, mask: all allowed.
- `bl-logo.png` (channel logo) and `fonts/` (Kanit 600/800, Archivo 800 woff2; the file name says family + weight).
  You may also use other text effects; any font must come from these files (no web fonts, no network).
- The numbers: 2 ชั่วโมง, เกือบ 6 ล้านบาท, "toxic trading".

## Two hard lines (the only rules)
1. The poster's name and photo are blurred in the stills. Use the stills as they are: never un-blur, sharpen, or zoom
   onto the blurred name/photo area. "CXM" / "CXM Direct" readable is fine.
2. A legal label is on screen for the whole 10 s, any style, readable:
   `เนื้อหาเพื่อการศึกษา ไม่ใช่คำแนะนำหรือการชักชวนลงทุน · การลงทุนมีความเสี่ยง`
Practical: TikTok covers the right edge (x > 960 below y 960) and the bottom (y > 1500) with its UI; keep key text clear of those.
Thai text: keep each line on one line (`white-space: nowrap`), shrink rather than wrap mid-word.

## How you work
Read and edit files in this folder only. Do not run any command (no npm, npx, node, git, ffmpeg); I render it.
Deterministic only: everything is a pure function of time (the renderer seeks frame by frame). No Math.random,
Date, setTimeout, requestAnimationFrame, CSS animations or transitions. Pseudo-random = a fixed seeded function.
When done, write `NOTES.md`: 5-10 lines on your creative choices, shot by shot with times.
