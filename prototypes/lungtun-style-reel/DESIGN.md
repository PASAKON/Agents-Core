# DESIGN.md — "ลงทุน Diary" style, reverse-engineered

Every value below was **measured** off the reference clip
(`sompong-video-acf8db9a4470b313.mp4`, TikTok re-encode, 1080×1920 HEVC 30fps),
not eyeballed. Where a number is a derivation rather than a direct read, it says so.

Reference frames used: t=4.5s, t=21.0s, t=35.0s.

## Style Prompt

A quiet, editorial product diary. Warm paper-cream ground, forest-green ink, one
oversized Latin product name per section and a small Thai voice underneath it.
Nothing shouts. The motion is a UI demonstrating itself — cards check themselves
off, rows fill in, a hub connects — while a single dark-green subtitle card at a
fixed height carries the narration. It reads as someone showing you their desk,
not as an ad.

## Colors (measured)

| Role | Hex | Where measured |
|---|---|---|
| Ground | `#F1F4E3` | left margin x=25, sampled y=5…1914 → F2F5E4…F3F6E5, flat |
| Ink (headline, icons) | `#3B4E32` | 'Loop' glyph body, t=4.5 |
| Subtitle card fill | `#253721` | card interior, t=21 and t=35 (identical) |
| Subtitle text | `#F0F8E5` | bright pixels inside the card |
| Muted (kicker, watermark) | `#939983` | 'CLAUDE CODE' kicker + 'ลงทุน Diary' mark |
| Card surface (light UI) | `#FBFCF2` | derived: ground + white lift |
| Accent (active state) | `#2F4A2B` | 'Focus' / 'Suggest Today' filled rows |
| Warning chip | `#E8DFC0` | 'ยังไม่เปิด' chip, t≈31s |

There is **no neon**. The whole clip lives between `#253721` and `#F1F4E3`.

## Typography

Two voices, not two sans-serifs-for-decoration:

- **`Gabarito`** 700/800 — the *product-name voice*. Only ever the big Latin word
  (`Loop`, `Agent`, `Merged`) and the tracked uppercase kicker. Foreign, technical,
  named object.
- **`IBM Plex Sans Thai Looped`** 400/600 — the *person's voice*. Every Thai word:
  headline, subtitle card, UI row labels, watermark. Looped terminals, because the
  reference's Thai is looped (หัวกลม), not cut.

The tension is the content's own: a Thai person narrating an English-named tool.
The two never share a line role.

Banned by the skill and not used: Inter, Roboto, Poppins, Noto Sans, Syne.

### Measured type scale

| Element | Measured | CSS |
|---|---|---|
| Kicker | ink band y185–210 (h 25px), tracked | 26px / 800 / `0.14em` / uppercase |
| Headline Thai | body band y285–319 (h 35px, marks above from y257) | 70px / 600 |
| Headline Latin | 'L' cap height **108px**, 'p' descender to y515 | **150px** / 800 / `-0.03em` |
| Subtitle | line pitch 65px, 2-line card h=174 | 52px / 600 / line-height 1.25 |
| Watermark | ink band y1755–1791 (h 36px) | 34px / 400 italic |

## Layout (measured)

- Canvas 1080×1920 @ 30fps.
- Left margin **86px** (kicker x=86, Thai headline x=88, Latin x=94, watermark x=84).
- Kicker baseline block at y≈185; Thai headline y≈257; Latin headline y≈375.
- Decorative loop glyph: 127×99 at x731–858, y340–439, stroke ≈7px.
- Stage (the UI mock) occupies roughly y580–1400, horizontally centred.
- **Subtitle card is vertically centred on y=1587 — fixed.** Verified on two frames
  whose card heights differ (174px and 106px); both centre on 1587 exactly.
- Subtitle card is **fit-content width**, horizontally centred (left gap == right gap
  on every frame: 306/306 and 158/158). Padding 24px 38px, radius 22px
  (corner walk: inset 18 at +0px → 0 at +20px).
- Watermark bottom-left at y≈1755.

## Motion

- **Section changes every ~13s in the reference** (hard cuts measured at 20.3s,
  27.3s, 32.7s — only 3 in 51.2s). This prototype runs 3 sections in 30s.
- **Subtitle changes every 1.77s median** (30 changes measured, min 0.90, max 3.10).
- Transition: `instant` preset, 0.15s. The reference uses true hard cuts; a 0.15s
  crossfade is the closest thing that does not read as a jump cut.
- Entrances: rows and chips stagger in at 90–140ms. Eases vary per scene
  (`power3.out`, `back.out(1.4)`, `sine.out`, `expo.out`).
- No exit animations except the final scene (house rule).
- The UI mock animates *itself* — checkmarks land in sequence, a row fills, an arrow
  drops. That self-demonstration is the whole visual idea; static cards would miss it.

## What NOT to Do

1. **No neon green, no near-black ground.** That is the `reel-editor-th` look and it
   is the opposite of this one.
2. **No word-by-word subtitle.** The reference's caption is a whole phrase that swaps
   wholesale — verified across 20 consecutive frames at 10fps. Karaoke highlighting
   would be a different video.
3. **No screen recordings.** Every UI surface is drawn in CSS so it stays crisp and
   on-palette.
4. **No fast cutting.** Under ~8s per section this stops reading as calm and starts
   reading as a generic explainer.
5. **No emoji, no drop shadows heavier than `0 18px 40px rgba(37,55,33,.10)`.**
6. **Never more than one oversized Latin word on screen.**

## Content of this prototype

The CEO briefed the **look**, not the script. Copy is about the org's own agent
workflow so every element type in the spec gets exercised (kicker + headline, a
device mock with a pulled-out callout row, a self-checking list, a hub diagram, a
light data card). Swap `CAPTIONS` and the three scene bodies in `index.html` to
retarget it; nothing else needs to move.
