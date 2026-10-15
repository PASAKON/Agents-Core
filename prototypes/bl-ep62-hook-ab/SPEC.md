# BL EP62 hook (first 15.0 s): one design, two renderers

The same 15-second opening of a BLACK LIQUIDITY TikTok episode, rendered twice: V1 in HyperFrames (HTML+GSAP), V2 in Remotion (React).
Both follow THIS file exactly, so the only difference the viewer sees is the renderer and the motion craft.

Why: the posted version (V0) shows mostly text on a black plate. Viral BL clips always show a REAL topical image behind a
2-line headline from frame 0, plus moving footage. This spec adds those.

## Canvas and sound
- 1080 x 1920, 30 fps, exactly 15.0 s (450 frames).
- Sound: `audio-0-15.wav` (the narration, already timed), starts at 0. Never re-time it.
- Fonts: Kanit 600 / 800 (Thai text), Archivo 800 (Latin digits are fine in Kanit too). Font files are given.
- Thai text never wraps mid-word: every line is ONE line (`white-space: nowrap`), shrink the font size to fit, never let it wrap.

## Safe area (TikTok covers these parts of the frame)
- All text and important graphics inside x 120..840 and y 252..1500.
- Above y 900 a text block may run to x 960 (the right rail starts at y ~960).
- Nothing important below y 1500 (TikTok's caption block), and nothing outside x 97..983.

## Always on, every frame, never animated
1. **Legal label**, bottom, small (about 22 px), white on a dark translucent strip, centred inside the safe area at about y 1440..1490:
   `เนื้อหาเพื่อการศึกษา ไม่ใช่คำแนะนำหรือการชักชวนลงทุน · การลงทุนมีความเสี่ยง`
2. **Brand bug**, top right at about x 700..840, y 180..260: the logo image `bl-logo.png` (about 150 px wide),
   a short red rule under it, and the date `14 ต.ค. 69` in small white text.

## The poster's identity
The three stills (`cxm-post-*.png`, 1080x1920 each) are screenshots of a Facebook post whose name and photo are ALREADY blurred.
Use them as they are. Never un-blur, sharpen, or crop to the blurred name area. Zoom in on the TEXT lines only.
"CXM" / "CXM Direct" stays readable (that is intended).

## The headline (the viral look)
A 2-line headline in the top band, from frame 0:
- line 1 (white, Kanit 800, about 76 px): `CXM ไม่จ่ายกำไร`
- line 2 (yellow #FFD60A, Kanit 800, about 92 px): `เกือบ 6 ล้านบาท`
- under it, small (Kanit 600, about 30 px, white at 85%): `ตามที่เจ้าของโพสต์เล่า`
- Placed at y ~300..560, left-aligned at x 120, on a soft dark gradient so it reads over any image.
- On screen from 0.00 to 9.27 s, hidden during the avatar (9.27..11.67), back from 11.67 to 15.00 as a smaller
  one-line version (`CXM ไม่จ่ายกำไร เกือบ 6 ล้าน`, about 52 px).
- In the first 0.4 s it lands with a quick, strong motion (slide up + scale from 1.08 to 1.0). No slow fades from black.
  Frame 0 itself must already show the image AND the headline (no empty first frame).

## Timeline (seconds; the narration line being spoken is in brackets)

| beat | t0 | t1 | what is on screen |
|---|---|---|---|
| OPEN | 0.00 | 1.00 | `cxm-post-claim.png` full-bleed, darkened to ~55% brightness, slow push-in (scale 1.00 -> 1.06 over the beat). Headline on top. |
| HOOK-1 | 1.00 | 3.57 | [ถือออเดอร์สองชั่วโมง แต่โดนข้อหาเทรดเร็วเกินไป?] B-roll `broll-12.mp4` (red-sand hourglass) full-bleed, darkened ~50%. Centre (y ~850..1050): a big clock that COUNTS UP from `0:00` to `2:00` with the unit `ชม.` (Archivo/Kanit 800, about 150 px, white), finishing by 2.6 s and holding. Caption below it (y ~1150): `ถือ 2 ชม. → โดนข้อหา "เร็วเกิน"` (Kanit 800, about 58 px, the word `"เร็วเกิน"` in yellow) and the small credit `ตามที่เจ้าของโพสต์เล่า` under it. |
| HOOK-2 | 3.57 | 6.43 | [เธอเล่าว่าซีเอ็กซ์เอ็มไม่จ่ายกำไรเกือบหกล้านบาท] `cxm-post-claim.png` full-bleed (not darkened as much, ~80%), slow zoom toward the claim line (centre of zoom ~x 480, y 880). A yellow highlight box DRAWS itself around the claim line (rectangle x 120, y 850, w 720, h 60 on the still, in still coordinates: move it with the zoom) between 3.8 and 4.3 s. Caption (y ~1150): `เธอเล่าว่า CXM ไม่จ่ายกำไร` then a number that COUNTS UP `0 -> 6` followed by `ล้านบาท`, prefixed by `เกือบ`, i.e. it ends as `เกือบ 6 ล้านบาท` in yellow, about 96 px; count finishes by 5.2 s. |
| HOOK-3 | 6.43 | 9.27 | [ซีเอ็กซ์เอ็มแจ้งในอีเมลว่าเป็นท็อกซิกเทรดดิ้ง] `cxm-post-account.png` full-bleed (~80%), slight zoom toward the `CXM Direct` line; yellow highlight box draws around x 120, y 818, w 720, h 55 (still coordinates) by 6.9 s. A red stamp-style label SLAMS in at 7.0 s (scale 1.4 -> 1.0, slight rotation -4 deg, red #E5202E border and text, Archivo 800 about 64 px): `TOXIC TRADING?` centred at y ~1100. Under it (Kanit 600, ~36 px): `ตามที่เธอเล่า: CXM แจ้งในอีเมล` |
| HOOK-4 | 9.27 | 11.67 | [เธอเลยถามสามข้อที่ยังไร้คำตอบ] The avatar: `avatar.mp4` (640x1024, lip-synced to this audio, so play it with media time = timeline time, i.e. start inside the file at 9.27 s) scaled to COVER the full 1080x1920 frame, centred. No headline (do not cover the face). Caption low (y ~1250..1400): `เธอเลยถาม` + a big yellow `3` that pops (scale 0 -> 1.15 -> 1.0) + `ข้อที่ยังไร้คำตอบ`. |
| PATTERN-1 | 11.67 | 13.97 | [เธอเล่าว่าเปิดบัญชีเซนต์กับซีเอ็กซ์เอ็ม] B-roll `broll-29.mp4` (finger taps a red lock icon) full-bleed, darkened ~45%, and on top of it `cxm-post-account.png` as a CARD: scaled to ~62%, centred at y ~900, rounded corners 24 px, soft shadow, enters by sliding up 80 px + fade in 0.35 s. Caption (y ~1330): `เธอเล่าว่า เปิดบัญชีเซนต์ กับ CXM`. Small headline back at the top. |
| PATTERN-2 | 13.97 | 15.00 | [ยี่สิบสองกันยายน เธอว่าไม่ใช้บอทเลย] `cxm-post-full.png` full-bleed (~80%), slow zoom toward x 540, y 1100. Caption (y ~1300): `22 กันยายน · เธอว่า "ไม่ใช้บอทเลย"` and the credit `ตามที่เจ้าของโพสต์เล่า`. Hard cut at 15.00 (it continues in the full episode). |

Cuts between beats are hard cuts, or a 4-frame flash/whip at most. No crossfades longer than 6 frames.
Captions appear within 0.25 s of their beat start (wipe in left-to-right or pop) and stay until the beat ends.
All captions sit on a dark rounded pill (black at ~60%) so they read over any image.

## What "done" looks like
- 15.0 s, 1080x1920, 30 fps, h264 + the narration audio.
- Frame 0 shows image + headline. No empty, black or half-loaded frame anywhere.
- Every text line fully inside the safe area; no Thai line wrapped.
- Legal label and brand bug on every frame.
