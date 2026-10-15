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

## Framework: HyperFrames 0.8.40 (HTML + GSAP)
Deliverable: `index.html` in this folder. Render command I will run: `npx hyperframes@0.8.40 render -o out/raw.mp4`.
Media is in `assets/` (stills/, broll/, fonts/, bl-logo.png, avatar-lipsync-0-10s.mp4, voice-10s.wav).
`reference-kit.html` is our old channel template. Use it ONLY to learn the HyperFrames mechanics (root element and its
data-duration, how clips are declared, the gsap script tag, @font-face, the one paused timeline registered as
`window.__timelines["main"] = tl; tl.seek(0);`). Do NOT copy its look; design your own. Mechanics:
- Video: `<video class="clip" src="assets/x.mp4" muted playsinline data-start="S" data-duration="D" data-media-start="M" data-track-index="N"></video>`;
  still: `<img class="clip" ... data-start data-duration data-track-index>`; higher track index draws on top.
  For the avatar, data-media-start = data-start (lip sync).
- Narration: one `<audio>` element pointing at assets/voice-10s.wav, data-start 0, data-duration 10.
- Every animation is a tween on the ONE paused gsap timeline `tl` at absolute times. Count-ups: tween a plain object
  with an onUpdate that writes text computed from the value only. The composition is exactly 10 s.


## Your skill: our channel's own editing rules
`skills/CMO_Procedure_BlackLiquidity_Cut/SKILL.md` (how BLACK LIQUIDITY episodes are cut: brand bug, legal label,
safe area, Thai type, beat modes, captions) and `skills/CMO_Workflow_BlackLiquidity/SKILL.md` (the channel workflow).
Read both first and apply what they say about LOOK and EDITING to this 10 s clip (it is the hook of an episode).
Parts about tools you cannot run (scripts, checkers, uploads, TikTok posting) do not apply. Where the skill and the
"free edit" wording above disagree, follow the skill; the two hard lines always hold.
For this clip `reference-kit.html` IS the channel template the skill talks about: start from it (its look included)
and replace its example content with this clip.

## Speed rules (a first attempt timed out after 25 min without writing anything)
- Do NOT open, view or listen to any .mp4 or .wav file, and do not use subagents. Everything you need to know about
  them is written above. You may look at the 3 PNG stills once if you want.
- The exact media file names (do not guess other names):
  - fonts/archivo-800-10d9bd15.woff2
  - fonts/archivo-800-23599068.woff2
  - fonts/archivo-800-87937726.woff2
  - fonts/kanit-600-0c71a5b8.woff2
  - fonts/kanit-600-9895ee29.woff2
  - fonts/kanit-600-b4b6e60e.woff2
  - fonts/kanit-600-fc0bae07.woff2
  - fonts/kanit-800-1bf17218.woff2
  - fonts/kanit-800-aa86a0cb.woff2
  - fonts/kanit-800-f57eab15.woff2
  - fonts/kanit-800-f99e92e2.woff2
  - avatar-lipsync-0-10s.mp4, voice-10s.wav, bl-logo.png
  - stills/cxm-post-claim.png, stills/cxm-post-account.png, stills/cxm-post-full.png
  - broll/hourglass-red-sand.mp4, broll/red-digital-countdown.mp4, broll/finger-taps-red-lock.mp4,
    broll/red-forbidden-icon-glow.mp4, broll/gold-bar-in-glass-cube.mp4, broll/typewriter-red-neon-ticker-tape.mp4,
    broll/contract-signature-wax-seal.mp4
- Write the deliverable files within your first 10 minutes, then refine. NOTES.md last.
