# BL EP62, 10-second clip in the "clean dev-explainer" motion style

The CEO did not like the last six versions (dark B-roll, big stamps, lots of effects). He pointed at a Thai TikTok
channel whose motion he likes. This spec describes that channel's style, adapted to our story. Follow it exactly:
the look is the job. Calm, clean, precise. NO B-roll, NO presenter, NO glow, NO shake, NO grain, NO gradients.

## The style in one paragraph
A flat near-black screen (#0C1016). One idea at a time in the centre. A short Thai caption (3-6 words) under the
idea, synced to the voice, swapped every ~0.7-1 s like karaoke, white with ONE keyword in yellow #FED100. The idea
is shown with a small, simple UI mock-up: a dark card (#161B22, 2 px border #2A313C, radius 18 px) holding a mono
label, a number, a line of text. Things enter quickly and settle (8 frames, ease-out, scale 0.96 -> 1.0 + opacity
0 -> 1, or rise 24 px). When a new focus element arrives over an old one, the old one blurs (8 px) and dims to 35%.
Danger is shown by a card's border turning red #F0444B, never by flashing. Lots of empty space. Cuts are hard.

## Canvas, sound, fonts
- 1080 x 1920, 30 fps, exactly 10.0 s (300 frames). Background #0C1016 everywhere, every frame.
- Sound: `voice-10s.wav`, starts at 0, never re-timed.
- Fonts (only these, from `fonts/`): Kanit 800 (captions, headline), Kanit 600 (small Thai text), Archivo 800 (big
  digits), DejaVu Sans Mono (`DejaVuSansMono.ttf`, `DejaVuSansMono-Bold.ttf`) for mono labels.
  Kanit and Archivo are each split over several woff2 files (character subsets). Declare every file as its OWN
  family name (e.g. Kanit800_1..Kanit800_4) and use a font-family list of all of them, so every glyph is found.
- Thai text never wraps: `white-space: nowrap` on every text line; shrink the size if needed.
- Colours: text white #F2F4F7, grey #8B949E, yellow #FED100, red #F0444B, green #3FB950.

## Always on (every frame, no animation)
- Top-left small brand: `bl-logo.png` at 64 px high, x 120, y 150, and next to it the mono grey label
  `BLACK LIQUIDITY · EP62` (24 px).
- Legal line, mono grey #8B949E, 22 px, centred, y ~1440:
  `เนื้อหาเพื่อการศึกษา ไม่ใช่คำแนะนำหรือการชักชวนลงทุน · การลงทุนมีความเสี่ยง` (Kanit 600 is fine for this line).
- Safe area: everything important inside x 120..960, y 250..1480.

## Layout bands
- HEADLINE band y 300..520 (centred): 2 lines, Kanit 800, line 1 white 76 px, line 2 yellow 76 px.
- IDEA band y 600..1050: the UI card(s), centred, max width 840.
- CAPTION band y ~1180 (centred): Kanit 800 64 px, white, one keyword yellow. Under it (y ~1250) an optional small
  mono grey sub-label 26 px.

## Timeline (seconds). Caption chunks swap HARD at these times (a 3-frame 12 px rise is allowed)
| t0 | t1 | caption (keyword in yellow is marked *like this*) |
|---|---|---|
| 0.00 | 1.00 | `ตามที่เจ้าของโพสต์เล่า` (grey, Kanit 600 44 px) |
| 1.00 | 1.80 | `ถือออเดอร์` |
| 1.80 | 2.50 | `*สองชั่วโมง*` |
| 2.50 | 3.05 | `แต่โดนข้อหา` |
| 3.05 | 3.60 | `เทรด*เร็วเกินไป?*` |
| 3.60 | 4.30 | `เธอเล่าว่า` |
| 4.30 | 5.20 | `CXM *ไม่จ่ายกำไร*` |
| 5.20 | 6.40 | `*เกือบ 6 ล้านบาท*` |
| 6.40 | 7.30 | `CXM แจ้งใน*อีเมล*` |
| 7.30 | 8.10 | `ว่าเป็น` |
| 8.10 | 9.30 | `*ท็อกซิกเทรดดิ้ง*` |
| 9.30 | 10.00 | `*3 คำถาม*ที่ยังไร้คำตอบ` |

### Scene A, 0.00-3.60: "held 2 hours"
- Frame 0 already shows the headline and the card (no empty first frame). Headline 0.00-3.60:
  line 1 `ถือออเดอร์ 2 ชั่วโมง`, line 2 (yellow) `แต่โดนหาว่าเร็วเกิน?`.
- Card A (IDEA band, 760 x 300): mono grey label top-left `ระยะเวลาที่ถือออเดอร์`; a big timer (Archivo 800,
  150 px, white) that counts `0:00:00` -> `2:00:00` from 1.00 to 2.40 s (ease-out; integer seconds only, written as
  h:mm:ss), then holds; a thin progress bar (8 px, track #2A313C) under it that fills yellow in step with the timer.
  Under the bar, mono green 24 px with a green dot: `● ถือไว้ 2 ชม.` appears at 2.40.
- At 3.05: card A's border turns red (6 frames); a small red pill appears at the card's top-right corner:
  mono 26 px `"เร็วเกินไป?"` (red text, red 2 px border, transparent fill). Nothing shakes.

### Scene B, 3.60-6.40: her post, then the number
- Hard cut. Headline band now: line 1 white `เธอเล่าว่า CXM`, line 2 yellow `ไม่จ่ายกำไร`.
- 3.60: Card B = a "post" card (840 wide): a top bar 56 px (#1C222B) with three grey dots and mono grey label
  `โพสต์ของเธอ · ชื่อเบลอแล้ว`; inside, `stills/cxm-post-claim.png` cropped to its text band (still coordinates
  y 760..1160, full width), scaled to the card width. Never show the still outside that band (the blurred name lives
  above it). No zoom, no pan.
- 3.80-4.30: a yellow highlighter (yellow at 35%, multiply-like look, radius 6) sweeps left-to-right over the claim
  line, still coordinates x 120, y 850, w 720, h 60 (convert into the card's coordinates).
- 5.20: card B blurs (8 px) and dims to 35%. On top, centred, Card C (640 x 260, border yellow 2 px): mono grey label
  `กำไรที่เธอบอกว่าไม่ได้รับ`, then Archivo 800 120 px yellow number counting `฿0` -> `฿6,000,000` from 5.20 to
  5.90 (comma separated, integer steps), under it Kanit 600 34 px white `เกือบ 6 ล้านบาท (ตามที่เธอเล่า)`.

### Scene C, 6.40-9.30: the email
- Hard cut. Headline band: line 1 white `CXM แจ้งในอีเมลว่า`, line 2 yellow `"Toxic Trading"`.
- 6.40: Card D = an email mock (840 x 420): top bar like card B with the mono label `อีเมล · ตามที่เธอเล่า`; rows in
  mono 30 px: `From:  CXM` (grey key, white value), then an empty row
  `เหตุผล:` whose value TYPES ON (one character per 2 frames, block cursor) from 7.30: `Toxic Trading` in red.
  When typing ends, card D's border turns red (6 frames).
  (These rows are an illustration of what she says the email said; keep the label `ตามที่เธอเล่า` visible.)
- 8.10: under card D, a red mono line 26 px fades in: `TypeError: กำไร is undefined` . (A small dev-joke, like the
  channel does; keep it.)

### Scene D, 9.30-10.00: the teaser
- Hard cut. No headline. Three square chips (120 x 120, card style) in a row, centred at y ~820, with Archivo 800
  digits `1` `2` `3`; they pop in one after another at 9.30, 9.40, 9.50 (scale 0.9 -> 1, 6 frames); chip `3` gets a
  yellow border and yellow digit at 9.70. Above them three short grey bars (like a progress step indicator).

## Done means
- 10.0 s, 1080x1920, 30 fps, h264 + the narration.
- Frame 0: headline + card A visible. No black or half-built frame anywhere.
- No text outside the safe area; no Thai line wrapped; brand + legal line on every frame.
- Everything is a pure function of the frame (deterministic).
## Framework: Remotion
Remotion 4.0.532, React 18.3.1, TypeScript are installed in node_modules. Use only installed packages (remotion, @remotion/cli, react; check
node_modules/@remotion for what else is there, e.g. transitions, and use it only if it is installed).
Media is in `public/` (use staticFile()). Write `src/index.ts` (registerRoot), `src/Root.tsx` with ONE
`<Composition id="Clip" width={1080} height={1920} fps={30} durationInFrames={300}>`, and your components.
Render command I will run: `npx remotion render src/index.ts Clip out/raw.mp4 --codec h264 --concurrency 1`.
Audio: <Audio src={staticFile("voice-10s.wav")}/>. Fonts: @font-face, and make the render
wait for them (delayRender/continueRender).


## Speed rules
- Do NOT open, view or listen to any .mp4 or .wav file, and do not use subagents. You may look at stills/cxm-post-claim.png once.
- Do not run any command (no npm, npx, node, git, ffmpeg). I render it. Read and edit files in this folder only.
- No Math.random, Date, setTimeout, requestAnimationFrame, CSS animations or transitions.
- Exact media file names (do not guess others): bl-logo.png, voice-10s.wav, stills/cxm-post-claim.png,
  stills/cxm-post-account.png, stills/cxm-post-full.png, and
  - fonts/DejaVuSansMono-Bold.ttf
  - fonts/DejaVuSansMono.ttf
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
- Write the deliverable files within your first 10 minutes, then refine. NOTES.md last (5-10 lines, what you built per scene).
