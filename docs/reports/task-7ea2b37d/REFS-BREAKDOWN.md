# REFS-BREAKDOWN: MYPASAKON v5 reference edits (task-7ea2b37d)

Analysis of the CEO reference clips for the MYPASAKON v5 recut. Scope: edit grammar only (timing, layout, motion, captions, transitions, sound), measured with ffprobe / ffmpeg scene scores / frame diffs / audio STFT, then checked by eye on contact sheets and full-resolution frames. Content, words and footage in section (c) are ours.

**ref4.mp4 is not present** in `/opt/MoonieXHQ/Work/mypasakon-voice/v5/refs/` (only ref1, ref2, ref3). Nothing here covers a fourth reference.

| clip | file id | duration | size / fps | audio | loudness (ebur128) |
|---|---|---|---|---|---|
| ref1 | ZSprNycKN | 118.99 s | 1080x1920, 30 fps | 2ch, L/R corr 0.968 | -19.4 LUFS, LRA 6.3, peak -0.9 dBFS |
| ref2 | ZSprNmJfE | 180.32 s | 1080x1920, 60 fps | 2ch, L/R corr 0.996 | -22.6 LUFS, LRA 5.1, peak -0.1 dBFS |
| ref3 | ZSprNuyka | 183.69 s | 1080x1920, 60 fps | 2ch but exact mono (corr 1.0000) | -20.2 LUFS, LRA 4.5, peak -0.4 dBFS |

---

## (a) Summary

### a1. Cut-length statistics (shots = clustered scene-change events, verified by eye)

Cut detection: `select=gt(scene,0.20)` frame scores clustered with a 0.35 s merge gap (an FX transition spans several frames and would otherwise count as many cuts). Width <= 0.075 s = hard cut, wider = FX transition. Five soft transitions the threshold misses (star-sticker pop, light leak, petal whip, laptop swipe, panel slide-in) were added from a lagged frame-diff and confirmed on strips.


| metric | ref1 | ref2 | ref3 | all three |
|---|---|---|---|---|
| duration (s) | 118.99 | 180.32 | 183.69 | 483.00 |
| shots | 23 | 39 | 54 | 116 |
| cuts (hard / FX) | 22 (19 / 3) | 38 (29 / 9) | 53 (46 / 7) | 113 (94 / 19) |
| mean shot (s) | 5.17 | 4.62 | 3.40 | 4.16 |
| median shot (s) | 3.70 | 3.40 | 3.38 | 3.40 |
| min / max (s) | 0.15 / 22.68 | 0.37 / 16.47 | 0.43 / 8.47 | 0.15 / 22.68 |
| p25 / p75 (s) | 1.55 / 6.48 | 2.38 / 6.42 | 2.05 / 4.54 | 2.01 / 5.16 |
| cuts per 10 s | 1.85 | 2.11 | 2.89 | 2.34 |
| shots under 1 s / under 2 s | 2 / 8 | 4 / 9 | 3 / 12 | 9 / 29 |
| shots over 8 s | 4 | 5 | 1 | 10 |
| first cut at (s) / cuts in first 3 s / in first 10 s | 0.95 / 2 / 4 | 2.65 / 1 / 3 | 4.79 / 0 / 2 | - |

Footnote: the strict `gt(scene,0.20)` frame counts are 25 / 85 / 89 frames for ref1 / ref2 / ref3. They are not cuts: FX transitions fire on many consecutive frames. Use the table above.

Read it as three tempos, not one: ref1 is a tutorial (screen holds of 6-22 s between labels), ref2 is meme news (many sub-2-s inserts plus 15-16 s caption holds), ref3 is the steadiest explainer (median 3.4 s, only one shot over 8 s, 12 shots under 2 s). All three mix very short shots (0.15-1.5 s) with holds of 6-22 s. None cuts on a fixed 2-3 s grid. That variance is the grammar.

### a2. What is on screen (share of running time)

| type | ref1 | ref2 | ref3 | note |
|---|---|---|---|---|
| face A-roll full frame | 15% (17.7 s) | 20% (35.9 s) | 31% (56.3 s) | |
| split / top panel with face | - | 1% (2.6 s) | 9% (17.4 s) | |
| screen / chart / UI | 84% (99.7 s) | 5% (8.6 s) | 22% (41.1 s) | |
| sticker or cutout on paper | - | 14% (25.2 s) | 12% (22.9 s) | |
| meme or photo insert | - | 31% (55.9 s) | 2% (3.4 s) | |
| graphic card (mint / green / brand) | - | 9% (16.9 s) | 20% (37.0 s) | |
| text card | - | 16% (29.2 s) | - | |
| end card (risk burst) | 1% (1.4 s) | 3% (5.0 s) | 3% (5.7 s) | |
| flash micro-shot | 0% (0.2 s) | 0% (0.9 s) | - | |
| face visible (A + split + round PIP) | 40% | 21% | 99% | PIP counted as face visible |
| face A-roll to non-face switches | 8 (1 per 15 s) | 13 (1 per 14 s) | 33 (1 per 5.6 s) | A + split = "face" |
| face run median / max (s) | 2.3 / 10.0 | 5.7 / 9.0 | 3.4 / 15.7 | consecutive A / split shots |
| non-face run median / max (s) | 14.6 / 67.5 | 12.1 / 78.1 | 5.2 / 25.6 | between face shots |
| shots with 3 or more stacked layers | 17 of 23 | 18 of 39 | 41 of 54 | layers counted by eye per shot (bg, media, sticker/PIP/label, caption) |

### a3. Repeated edit-grammar patterns

Numbers marked (m) are measured on 1080x1920 frames; (v) are visual estimates; (ORB) are whole-frame feature-match estimates and only trusted on face A-roll shots.

| element | ref1 (tutorial) | ref2 (meme news) | ref3 (explainer) | pattern to carry |
|---|---|---|---|---|
| 0-3 s hook | full-frame face, caption from frame 0; first cut 0.95 s (soft star-sticker pop plus background swap under the face), 2 cuts in 3 s | split frame, photo on top, face below, 2-line caption at y 45-57% (m), held 2.65 s, then paper flash | split frame, chart on top, face below, white + green caption at y 43-52% (m), held 4.79 s, then text-mask whip | caption is already on screen at frame 0; face is on screen at frame 0; media-over-face split or a bg-swap pop inside the first 3 s |
| A-roll vs B-roll cadence | face 15% of time, 6 runs (median 2.3 s, max 10 s); 67 s screen block in the middle is broken by a new label every 2-7.5 s and a face PIP on 7 of 15 screen shots | face 21%, runs median 5.7 s; between faces: stickers, memes, photos (non-face median 12 s) | face full frame 31%, plus split 40%, plus round PIP on nearly every other shot (99% face visible); face returns every 5.6 s | never leave the face off screen for more than about 6 s unless a PIP carries it; screen shots carry a label change at least every 7.5 s |
| 3+ stacked background layers | card layouts: dark bg + blurred zoomed duplicate of the screen + sharp card + PIP + label = 4 | paper texture + cutout + sticker (BUY pop, falling notes, rising money) + caption = 3-4 | paper or mint bg + chart / graphic + PIP + caption (+ BUY pill, stars, counters) = 4 | every non-face shot has at least 3 layers; one of them moves (blurred dup zoom, falling notes, animated chart line, counter) |
| screen card (ref1, m) | about 94% of width (about 1000 px), 573-612 px tall (30-32%) in "small card" layouts with the top edge at y 27-36%; 1009-1196 px tall (52-62%) in "tall card" layouts; no tilt; no drop shadow on the dark bg; corner radius about 8 px (v); slow push on the card, indicative +0.5 to +2%/s (v) | no screen cards (one laptop swipe plus one UI strip) | screens are full-bleed or small cutouts; chart cards on paper, not tilted | card layout = flat card, full width, centred at y 50%, label below, slow zoom |
| round face PIP (m) | circle about 428 px diameter (39.6% of width), centre about x 76%, y 14.6% (top-right), thin ring (from half-scale crops, about 10 px error) | none | circle about 256 px (23.7%), centre x 50% (top-centre), centre y 11-35% depending on the layout (above the caption block); one layout moves it mid-left | PIP ring 4-6 px; size and anchor set per layout family |
| stickers (ref2, m/v) | star sticker pop | white die-cut outline about 14-18 px, soft shadow, no tilt; BUY button pop with about 0.25 s overshoot; money stack rises, notes fall | BUY pill pop, counter cards (977035 > 920668 > 864301), stars | spring pop 0.25 s with overshoot, then settle |
| caption: face A-roll | white fill, black outline, y 24.3-29.8% (m), glyph box 87-111 px; hero keyword line above at y 15-22%: cyan-blue gradient ("FEATURE") or yellow-orange gradient ("TREND"), about 130 px glyphs; hard-pop pages, one frame at 30 fps (m) | L1 cream-yellow #FAFE77 + L2 red #ED1D37, black outline with dark-red glow; L1 y-top 13.8-15.4%, L2 y 19.7-26.6% (n=4, m); glyph box 63-118 px (m); paper cards y 30-40%; builds by syllable | L1 green #23FD0A, L2 white, black outline; L1 y-top median 13.2%, bottom 17.7% (n=20, m); L1 glyph box median 85 px (58-103) | 2 lines in the top third, line 1 accent colour, line 2 white, heavy black outline |
| caption: other layouts | label box under the card: near-white rectangle (luma > 222), black Thai text, 75-86 px tall, 263-296 px wide, top edge y 70.3-70.8% (n=3 clean samples), pages every 2-7.5 s | red text with black offset extrude shadow on paper, y 30-60%; text cards build line by line at about 4 s steps | B-roll and sticker captions sit at y 35-52%, same 2-colour pair | label box for screens, big centred text for paper cards |
| caption animation (m) | instant on/off: "วิธีการ" 31.37-31.57, 0.13 s gap, "ซึ่งง่ายมาก" 31.70-32.04; no scale or blur | progressive build (v), pages about every 3-6 s | L1 reveals left to right in 0.36 s (width 48 to 548 px at full res) with a height overshoot (glyph box 122 px settling to 84 px within 0.35 s), then a slow downward drift of about 6 px per 0.35 s | page-by-page captions; the pop is one of {instant, syllable build, 0.36 s wipe with overshoot} per layout, not mixed inside a shot |
| transitions | 19 of 22 hard cuts; 3 FX: star-sticker pop (0.95 s), warm light-leak flash (0.15 s shot at 100.25), a soft FX at 110.37 (not classified) | 29 of 38 hard cuts; 9 FX: ink-brush paper white-flash about 0.45-0.55 s at 3.3, 41.5, 60.9, 75.4, two sweeps 141.8-143.8, 175.1; red-petal whip 109.8; laptop swipe 110.7; blur-zoom whip about 142.0 | 46 of 53 hard cuts; 7 FX: giant-text-mask whip with glow flash 0.5-0.65 s at 4.5, 13.2, 60.6, 177.8; phone-UI glitch jump cuts 91.3 and 95.4; panel slide-in from top 99.15 (0.3 s ease-out) | 76-87% hard cuts; FX only at section boundaries, hook to body, and into the end card |
| long holds | 17.3 s and 22.1 s screen holds with a new label every 5.8-7.5 s | 15.9 s paper list builds line by line; 16.5 s stack with caption pages every 6 s | longest 8.5 s (face) | a hold is allowed only if the caption or a layer changes every 4-7 s |
| end card | yellow comic-burst CFD risk warning, 1.4 s, then 1.2 s face outro | black card "ถึงเวลาพิสูจน์ตัวเองแล้ว!" 3.2 s then red burst 5.0 s | green burst 5.7 s with PIP | all three close on the same burst card: star at top, cloud base, small paragraph |
| loudness | -19.4 LUFS | -22.6 LUFS | -20.2 LUFS | target -20 LUFS integrated, peak below -1 dBFS |

### a4. Sound: SFX on cuts (honest read)

The refs are mixes of speech, music and effects with no stems, and ref3 is exactly mono, ref2 nearly so (L/R correlation 1.0000 and 0.996), so a mid/side split cannot separate effects from the centred voice. What can be measured: whether the loudest 10 ms frame in the window -0.15 s to +0.25 s around a cut is above that track's own 95th / 98th percentile, compared with random windows.

| | ref1 | ref2 | ref3 |
|---|---|---|---|
| random windows above p95 / p98 | 41% / 20% | 42% / 23% | 33% / 15% |
| hard cuts above p95 / p98 | 74% / 47% (n=19) | 76% / 48% (n=29) | 70% / 48% (n=46) |
| FX transitions above p95 / p98 | 100% / 33% (n=3) | 67% / 44% (n=9) | 86% / 57% (n=7) |
| cut-aligned average, high band (4-10 kHz) peak | +7.6 dB at -0.11 s | +10.2 dB at +0.04 s | +11.2 dB at +0.15 s |

Reading: hard cuts land on a loud frame about twice as often as chance at p98 (47-48% vs 15-23%), so roughly a quarter to a third of cuts (excess 25-33 points) carry an audible hit above the bed. FX transitions carry one more often (ref3 57%, ref1 and ref2 about 33-44% at p98, ref1 n=3 too small to read). The high-band lift is consistent with whoosh or flash sounds on FX and with speech sibilants, so it is evidence of "SFX on most FX transitions and on some hard cuts", not proof of an effect on every cut. Per-cut flags are in the last column of each table in section (b): **P98** = peak above p98, p95 = above p95, dot = neither. Treat a flag as a candidate hit, not a confirmed one.

### a5. Why v4 feels flat next to these

v4 (`v4/qc/cut-summary.json`): 42 shots in 102.7 s, 41 cuts = 4.0 cuts per 10 s, every shot between 2.06 s and 3.00 s, 28 cuts snapped to silences and 13 to caption starts, no FX. The refs cut less often (1.9-2.9 per 10 s) but vary their shot length 0.15-22 s, with 12-25% of shots under 2 s and holds of 6-22 s. v4 has the right number of cuts and none of the variance, which reads as a metronome.

---

## (b) Per-clip shot tables

Columns: shot, in, out, length (s), type (A face full frame, AS split/panel with face, B screen/chart/UI, S sticker or cutout on paper, M meme/photo insert, G graphic card, T text card, E end card, X flash micro-shot), on-screen content (PIP = round face inset), camera/card motion, background layers, text (position, colour, animation), transition into the shot, audio flag at the cut. Motion: `static` = whole-frame feature match shows < 0.8%/s zoom on A-roll or < 0.5%/s on other layouts; push-in values are whole-frame ORB estimates (indicative); `n/m` = not measured (shot too short, or the estimate was unreliable because contents swap between first and last frame). Timecodes are m:ss.ss.


### ref1 ZSprNycKN (118.99 s, 30 fps, 23 shots)

| # | in | out | len | type | on-screen content | motion | background layers | text | transition into shot | audio |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0:00.00 | 0:00.95 | 0.95 | A | Face A-roll, green vine wall behind | n/m (short) | 2: wall + face | white Thai, black outline, y 24.6-29.5%, hard-pop page "ใครที่ยังใช้" | start | - |
| 2 | 0:00.95 | 0:02.63 | 1.68 | A | Face over white Gemini-style screen bg; blue-violet star sticker pops in | n/m (unreliable) | 3: screen bg + face + star sticker | white Thai lines, 2 pages | soft: star-sticker pop + bg swap under face | **P98** |
| 3 | 0:02.63 | 0:07.20 | 4.57 | B | PIP: Small dark UI card, face PIP top-right, white label box under card | static | 4: dark bg + card + PIP + label | label pages x3 (white box, black Thai) | hard cut | **P98** |
| 4 | 0:07.20 | 0:09.53 | 2.33 | A | Face on green wall | pull-out -4.2%/s (ORB) | 2 | pages "ตอนนี้นะครับ", "ผมไปเจอตัว"; then hero "FEATURE" cyan-blue gradient + white outline, line 2 Thai white (y 24.6-29.5%) | hard cut | **P98** |
| 5 | 0:09.53 | 0:14.07 | 4.53 | B | PIP: TradingView-style chart card over blurred zoomed duplicate of itself, PIP | n/m | 4: blurred dup + sharp card + PIP + label | label pages x3 | hard cut | . |
| 6 | 0:14.07 | 0:17.37 | 3.30 | B | Dark extension-panel card (larger), no PIP | n/m | 3: dark bg + card + label | label pages x3 | hard cut | **P98** |
| 7 | 0:17.37 | 0:24.37 | 7.00 | B | Chart card + side panel, label under card | n/m | 3 | label pages x3 | hard cut | . |
| 8 | 0:24.37 | 0:28.23 | 3.87 | B | Small browser-store page card, light | n/m | 3 | label pages x3 | hard cut | **P98** |
| 9 | 0:28.23 | 0:31.27 | 3.03 | B | Stack: chart strip top, table strip bottom, blue box icon between | n/m | 3-4 | label pages x3 | hard cut | **P98** |
| 10 | 0:31.27 | 0:32.90 | 1.63 | A | Face on green wall | pull-out -6.5%/s (ORB) | 2 | pages "วิธีการ" then "ซึ่งง่ายมาก" (instant) | hard cut | p95 |
| 11 | 0:32.90 | 0:34.27 | 1.37 | B | PIP: Browser-store card with trophy graphic, PIP | n/m | 4 | label pages x3 | hard cut | **P98** |
| 12 | 0:34.27 | 0:42.40 | 8.13 | B | PIP: Extension page cards, PIP; 8.1 s hold | n/m | 4 | label pages x3 (~2.7 s each) | hard cut | p95 |
| 13 | 0:42.40 | 0:43.87 | 1.47 | B | PIP: Wide white chart screen, PIP overlaps card corner | static | 3 | label pages x2 | hard cut | **P98** |
| 14 | 0:43.87 | 0:47.57 | 3.70 | B | PIP: Dark list UI full width, PIP | static | 3 | label pages x3 | hard cut | . |
| 15 | 0:47.57 | 0:53.13 | 5.57 | B | Login then dark dialog screens, no PIP | n/m (unreliable) | 3 | label pages x3 | hard cut | **P98** |
| 16 | 0:53.13 | 1:10.67 | 17.53 | B | 17.3 s hold: white UI screens in card, no PIP | n/m | 3 | label pages x3 (~5.8 s each) | hard cut | p95 |
| 17 | 1:10.67 | 1:17.57 | 6.90 | B | Dark dialog then text-document card | n/m (unreliable) | 3 | label pages x3 | hard cut | **P98** |
| 18 | 1:17.57 | 1:40.25 | 22.68 | B | 22 s hold: TradingView chart card, no PIP | n/m | 3 | label pages x3 (~7.5 s each) | hard cut | . |
| 19 | 1:40.25 | 1:40.40 | 0.15 | X | Warm peach/orange light-leak wash, cross-dissolve face <-> chart card | n/m (short) | 2 | none | warm light-leak flash (0.15 s shot) | p95 |
| 20 | 1:40.40 | 1:50.37 | 9.97 | A | Face on green wall; 10 s hold | static | 2 | hero "TREND" yellow-orange gradient + "ขึ้น"; then white Thai pages | hard cut | p95 |
| 21 | 1:50.37 | 1:56.43 | 6.07 | B | PIP: MT5 chart card, PIP top-right | n/m | 4 | label pages x3 (~2 s each) | soft FX (type not classified) | p95 |
| 22 | 1:56.43 | 1:57.83 | 1.40 | E | Yellow comic-burst CFD risk card, white star top, cloud base | n/m | 3: burst bg + star + text | small black Thai paragraph, centred | hard cut | p95 |
| 23 | 1:57.83 | 1:58.99 | 1.16 | A | Face outro on green wall | pull-out -14.1%/s (ORB) | 2 | pages "คอยบอก", "แล้วกันนะครับ" | hard cut | . |

### ref2 ZSprNmJfE (180.32 s, 60 fps, 39 shots)

| # | in | out | len | type | on-screen content | motion | background layers | text | transition into shot | audio |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0:00.00 | 0:02.65 | 2.65 | AS | Split: photo top (politician-family, flag bg), A-roll face below; hook | static | 3: photo + face + caption | L1 cream #FAFE77, L2 red #ED1D37, black outline, y 45-57%; builds by syllable | start | - |
| 2 | 0:02.65 | 0:03.51 | 0.86 | M | Locker-room clip on black bar (meme insert), then paper flash | n/m (short) | 2: video + black bars | none | hard cut | . |
| 3 | 0:03.51 | 0:08.38 | 4.87 | S | White-outlined cutout photo (two people) filling frame on paper | static | 3: paper + cutout + caption | L1 red-gradient "เทรดแม่นยำ" / L2 "ถึง 100% !!" top, y 14-30% | ink-brush paper white-flash | **P98** |
| 4 | 0:08.38 | 0:13.48 | 5.10 | S | Cutout figure on paper; green BUY button sticker pops (overshoot ~0.25 s) with hand cursor; candles rise right | static | 4: paper + cutout + BUY + candles | none | hard cut | **P98** |
| 5 | 0:13.48 | 0:16.20 | 2.72 | S | Cutout with pixel sunglasses + gold chain on dark bg | static | 3 | L1 cream + L2 red, bottom third | hard cut | p95 |
| 6 | 0:16.20 | 0:20.12 | 3.92 | S | Cutout of pointing figure on paper, white outline | static | 3 | L1 cream + L2 red, bottom | hard cut | p95 |
| 7 | 0:20.12 | 0:22.70 | 2.58 | A | Face A-roll (dark red studio) with green money-arrow sticker top | pull-out -3.6%/s (ORB) | 3: studio bg + face + sticker | none | hard cut | p95 |
| 8 | 0:22.70 | 0:24.17 | 1.47 | M | CGI footballer meme on black bars | n/m | 2 | none | hard cut | . |
| 9 | 0:24.17 | 0:24.53 | 0.37 | M | SMPTE colour bars on black (0.37 s) | n/m (short) | 1-2 | none | hard cut | p95 |
| 10 | 0:24.53 | 0:27.63 | 3.10 | M | Photo, person in sweater, blurred bg | n/m | 2 | 2 lines bottom, cream/red | hard cut | **P98** |
| 11 | 0:27.63 | 0:28.13 | 0.50 | M | Face-grimace meme clip on black bars (0.5 s) | n/m (short) | 2 | none | hard cut | **P98** |
| 12 | 0:28.13 | 0:31.53 | 3.40 | M | Same photo as shot 10 | static | 2 | 2 lines bottom | hard cut | p95 |
| 13 | 0:31.53 | 0:33.17 | 1.63 | S | Cutout with sunglasses on paper, banknotes falling (bg layer) | static | 4: paper + falling notes + cutout + caption | none | hard cut | **P98** |
| 14 | 0:33.17 | 0:34.70 | 1.53 | M | CCTV trading-room clip on black bars | static | 2 | none | hard cut | p95 |
| 15 | 0:34.70 | 0:41.70 | 7.00 | S | Cutout + sunglasses on paper | static | 3 | 2 lines top, y 14-26%, cream L1 / red L2 | hard cut | **P98** |
| 16 | 0:41.70 | 0:58.17 | 16.47 | M | Stack: UI table strip top, blurred zoom of portrait below; 16.5 s hold | static | 3: strip + blurred zoom + caption | cream L1 / red L2 top, pages change ~every 6 s | ink-brush paper white-flash | **P98** |
| 17 | 0:58.17 | 1:01.15 | 2.98 | M | DJ meme clip on black bars | n/m | 2 | none (burned-in subs from source) | hard cut | . |
| 18 | 1:01.15 | 1:05.17 | 4.02 | M | Portrait photo, caption top | static | 2 | 2 lines top | ink-brush paper white-flash | **P98** |
| 19 | 1:05.17 | 1:12.33 | 7.17 | M | Group photo, dark bg | static | 2 | 2 lines top | hard cut | **P98** |
| 20 | 1:12.33 | 1:15.58 | 3.25 | T | Paper bg, rising banknote stacks, caption red | n/m (unreliable) | 3: paper + stacks + caption | red text with black offset shadow, y 30-45% | hard cut | **P98** |
| 21 | 1:15.58 | 1:21.53 | 5.95 | G | Crypto-coin graphic with capitol, big push-in to coin | big push-in x2.1 (ORB) | 3: blue bg + capitol + coin | 2 lines bottom, cream/red | ink-brush paper white-flash | **P98** |
| 22 | 1:21.53 | 1:32.50 | 10.97 | G | Gold building sign, then group photo rises from bottom | n/m | 3 | 2 lines top, cream/red | hard cut | . |
| 23 | 1:32.50 | 1:36.02 | 3.52 | M | Group photo | n/m | 2 | 2 lines top | hard cut | p95 |
| 24 | 1:36.02 | 1:38.55 | 2.53 | M | Stack: broker table strip top, portrait below blurred | static | 3 | 2 lines top | hard cut | **P98** |
| 25 | 1:38.55 | 1:40.77 | 2.22 | M | Two stacked photos | static | 2 | 2 lines | hard cut | . |
| 26 | 1:40.77 | 1:49.80 | 9.03 | A | Face A-roll, dark studio; 9 s hold | n/m (unreliable) | 2 | 2 lines top, y 14-26%, caption pages ~every 3 s | hard cut | **P98** |
| 27 | 1:49.80 | 1:50.67 | 0.87 | X | Red-petal whip + laptop slides in at an angle | n/m (short) | 3: black + petals + laptop | none | red-petal whip | p95 |
| 28 | 1:50.67 | 1:59.30 | 8.63 | B | Laptop UI screen card, white/dark; flow diagram, $1,000,000 USD | static | 3 | red/pink heading in the UI itself | swipe: laptop to text card | p95 |
| 29 | 1:59.30 | 2:01.88 | 2.58 | M | Split: woman photo top, candle chart bottom | static | 3 | 2 lines red/cream | hard cut | **P98** |
| 30 | 2:01.88 | 2:09.13 | 7.25 | A | Face A-roll, thumb gesture; 7.3 s | push-in +1.9%/s (ORB) | 2 | 2 lines top, cream/red | hard cut | . |
| 31 | 2:09.13 | 2:16.02 | 6.88 | T | Paper bg, icon hand+cash, caption centred | static | 3 | red + cream, y 30-40% | hard cut | **P98** |
| 32 | 2:16.02 | 2:20.10 | 4.08 | A | Face A-roll | push-in +1.6%/s (ORB) | 2 | 2 lines top | hard cut | p95 |
| 33 | 2:20.10 | 2:22.03 | 1.93 | M | Kid video clip, bright | n/m | 2 | none | hard cut | **P98** |
| 34 | 2:22.03 | 2:23.30 | 1.28 | M | Man-praying photo, then second pose photo | n/m (short) | 2 | none | blur-zoom whip + ink-brush | . |
| 35 | 2:23.30 | 2:29.00 | 5.70 | A | Face A-roll; 5.7 s | static | 2 | 2 lines top | ink-brush paper white-flash (2nd sweep) | . |
| 36 | 2:29.00 | 2:44.83 | 15.83 | T | Paper text card, 15.8 s hold: list builds line by line, green @handle appears last | static | 2: paper + text | red text, black offset shadow, y 30-60%; lines appear at ~4 s steps | hard cut | **P98** |
| 37 | 2:44.83 | 2:52.07 | 7.23 | A | Face A-roll; 7.2 s | static | 2 | 2 lines top | hard cut | . |
| 38 | 2:52.07 | 2:55.32 | 3.25 | T | Black card, 3.2 s | n/m | 1 | cream L1 + red L2 centred, y 48% | hard cut | **P98** |
| 39 | 2:55.32 | 3:00.32 | 5.01 | E | Red comic-burst CFD risk card, white star top, cloud base; 5.0 s | n/m | 3 | small cream Thai paragraph | ink-brush paper white-flash | . |

### ref3 ZSprNuyka (183.69 s, 60 fps, 54 shots)

| # | in | out | len | type | on-screen content | motion | background layers | text | transition into shot | audio |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0:00.00 | 0:04.79 | 4.79 | AS | Split: chart top, face bottom; hook | static | 3: chart + face + caption | white L1 ("ได้เปรียบกว่า") + green L2, y 43-52% | start | - |
| 2 | 0:04.79 | 0:09.97 | 5.18 | B | PIP: MT5 terminal dark, PIP top-centre | n/m | 4: terminal + PIP + caption | white/red lines at bottom | text-mask whip (giant white glyph mask) + glow flash | **P98** |
| 3 | 0:09.97 | 0:13.29 | 3.32 | A | Face A-roll, caption on forehead area; "?" sticker | n/m (unreliable) | 3 | L1 red then green, L2 white, y 12-20% | hard cut | . |
| 4 | 0:13.29 | 0:15.65 | 2.36 | G | PIP: Blurred broker-logo wall (white), PIP, big caption | n/m | 4: logo wall + PIP + caption | L1 green "เลือก", L2 white, y 46-60% | text-mask whip + glow flash | **P98** |
| 5 | 0:15.65 | 0:19.75 | 4.10 | S | PIP: Paper bg, green "1.???? 2.???? 3.????" list, then photo card appears | static | 4 | green accent, black outline, centred; PIP top-centre | hard cut | **P98** |
| 6 | 0:19.75 | 0:23.00 | 3.25 | A | Face A-roll | pull-out -3.1%/s (ORB) | 2 | L1 green (e.g. "ตั้งแต่ปี"), L2 white "2026", top, y 12-20% | hard cut | . |
| 7 | 0:23.00 | 0:24.92 | 1.92 | S | PIP: Paper + rising candle chart, spread tag, PIP mid-left | n/m | 4: paper + chart + tag + PIP | L1 green "1.เรื่อง" L2 white "ค่า Spread", y 12-20% | hard cut | **P98** |
| 8 | 0:24.92 | 0:27.52 | 2.60 | G | PIP: Mint-green card: "ค่า Spread คืออะไร?" with black chart panel punch-zoom, stars | big push-in x1.8 (ORB) | 4: mint + panel + stars + PIP | white bold, y 20-30% | hard cut | **P98** |
| 9 | 0:27.52 | 0:31.77 | 4.25 | A | Face A-roll | pull-out -2.2%/s (ORB) | 2 | L1 green, L2 white, top | hard cut | **P98** |
| 10 | 0:31.77 | 0:36.63 | 4.87 | S | PIP: Paper + mini candle chart, BUY pill pops | n/m | 4 | green L1, white L2 | hard cut | p95 |
| 11 | 0:36.63 | 0:40.20 | 3.57 | B | PIP: Split: white chart top, reaction guy bottom, PIP | static | 4 | L1 green, L2 white | hard cut | **P98** |
| 12 | 0:40.20 | 0:43.93 | 3.73 | B | PIP: White chart with pink band, PIP | static | 3 | L1 red "ค่า Spread สูงมาก", L2 white | hard cut | p95 |
| 13 | 0:43.93 | 0:47.83 | 3.90 | S | PIP: Paper + animated green line chart | static | 4 | green L1, white L2 (y 35-50%) | hard cut | **P98** |
| 14 | 0:47.83 | 0:52.98 | 5.15 | B | PIP: Phone chart dark, PIP | static | 3 | green L1, white L2 (middle) | hard cut | **P98** |
| 15 | 0:52.98 | 0:54.75 | 1.77 | B | PIP: Laptop-and-hands photo, PIP | n/m | 3 | L1 green, L2 white | hard cut | **P98** |
| 16 | 0:54.75 | 0:57.32 | 2.57 | G | PIP: Green card, counter 977035 -> 920668 -> 864301, "LOSS" figure | n/m | 4: green + figure + counter + PIP | white numerals y 15-20% | hard cut | **P98** |
| 17 | 0:57.32 | 1:00.88 | 3.57 | AS | Split: chart top, face bottom | push-in +2.7%/s (ORB) | 3 | white L1 + green L2 | hard cut | **P98** |
| 18 | 1:00.88 | 1:04.38 | 3.50 | S | PIP: Paper + chart + caption "ข้อที่ 2 นะครับ" | n/m | 4 | green L1, white L2 | text-mask whip + glow flash | **P98** |
| 19 | 1:04.38 | 1:06.43 | 2.05 | B | PIP: Dark chart, PIP | n/m | 3 | green "Broker", white L2 | hard cut | **P98** |
| 20 | 1:06.43 | 1:09.02 | 2.58 | B | PIP: Dark chart with cyan bars, PIP | n/m | 3 | L1 red "กราฟต้อง ไม่ Delay" | hard cut | . |
| 21 | 1:09.02 | 1:11.90 | 2.88 | A | Face A-roll | pull-out -2.5%/s (ORB) | 2 | green L1, white L2 | hard cut | **P98** |
| 22 | 1:11.90 | 1:14.42 | 2.52 | B | PIP: White chart, PIP | n/m | 3 | L1 green, L2 white | hard cut | **P98** |
| 23 | 1:14.42 | 1:16.67 | 2.25 | A | Face A-roll | pull-out -5.9%/s (ORB) | 2 | green L1, white L2 | hard cut | . |
| 24 | 1:16.67 | 1:18.23 | 1.57 | B | PIP: Phone chart scrolling, PIP, quote line | static | 3 | white quote | hard cut | **P98** |
| 25 | 1:18.23 | 1:23.73 | 5.50 | A | Face A-roll; 5.3 s | static | 2 | L1 green, L2 white | hard cut | . |
| 26 | 1:23.73 | 1:27.10 | 3.37 | M | PIP: Handshake photo, PIP, caption lower | n/m | 3 | green L1, white L2 | hard cut | **P98** |
| 27 | 1:27.10 | 1:31.28 | 4.18 | A | Face A-roll | pull-out -3.2%/s (ORB) | 2 | green L1, white L2 | hard cut | p95 |
| 28 | 1:31.28 | 1:32.23 | 0.96 | B | PIP: Phone order-ticket UI jump-cut #1, PIP | n/m (short) | 3 | green L1, white L2 | FX/glitch jump-cut | **P98** |
| 29 | 1:32.23 | 1:32.67 | 0.43 | B | PIP: Order-ticket UI jump-cut #2 (0.44 s) | n/m (short) | 3 | green L1, white L2 | hard cut | . |
| 30 | 1:32.67 | 1:33.88 | 1.22 | B | PIP: Phone chart UI jump-cut #3 | static | 3 | green L1, white L2 | hard cut | . |
| 31 | 1:33.88 | 1:35.40 | 1.52 | B | PIP: Order UI jump-cut #4 to chart | n/m | 3 | green L1, white L2 | FX/glitch jump-cut | p95 |
| 32 | 1:35.40 | 1:39.15 | 3.75 | A | Face A-roll, slow push-in | pull-out -1.9%/s (ORB) | 2 | L1 green, L2 white | FX (unclassified) | p95 |
| 33 | 1:39.15 | 1:44.77 | 5.62 | AS | Top panel (green ad card) slides in over face | static | 3: face + green panel + caption | green L1, white L2 on panel | soft: panel slides in from top (~0.3 s ease-out) | . |
| 34 | 1:44.77 | 1:51.13 | 6.37 | A | Face A-roll, push-in | push-in +2.2%/s (ORB) | 2 | green L1, white L2, top | hard cut | **P98** |
| 35 | 1:51.13 | 1:53.02 | 1.88 | B | PIP: Laptop photo, PIP | n/m | 3 | green L1, white L2 | hard cut | **P98** |
| 36 | 1:53.02 | 1:56.42 | 3.40 | AS | Green card top ("พร้อมตรวจสอบปัญหา"), face bottom | static | 3 | white on card | hard cut | . |
| 37 | 1:56.42 | 2:00.12 | 3.70 | G | PIP: Green card "13 ภาษา", people icons, PIP | n/m | 4 | white on green | hard cut | **P98** |
| 38 | 2:00.12 | 2:02.15 | 2.03 | A | Face A-roll | push-in +4.9%/s (ORB) | 2 | green L1, white L2 | hard cut | **P98** |
| 39 | 2:02.15 | 2:07.48 | 5.33 | G | PIP: Green phone card "ช่องทางติดต่อ…24 ชั่วโมง", PIP | n/m | 4 | white on green | hard cut | . |
| 40 | 2:07.48 | 2:12.30 | 4.82 | A | Face A-roll | push-in +1.4%/s (ORB) | 2 | green L1, white L2 | hard cut | p95 |
| 41 | 2:12.30 | 2:16.90 | 4.60 | S | PIP: Paper bg, pixelated green logo, PIP | n/m | 4 | green L1, white L2 | hard cut | **P98** |
| 42 | 2:16.90 | 2:17.87 | 0.97 | G | Giant 3D green glyph over face, then green card (0.97 s) | static | 3 | none | hard cut | . |
| 43 | 2:17.87 | 2:20.88 | 3.02 | G | PIP: Green gold-bar card "12 จุด", PIP | n/m | 4 | white on green | hard cut | p95 |
| 44 | 2:20.88 | 2:22.93 | 2.05 | A | Face A-roll | push-in +4.1%/s (ORB) | 2 | green L1, white L2 | hard cut | . |
| 45 | 2:22.93 | 2:28.32 | 5.38 | G | PIP: Green card, laptop mock, counter "0.004 วินาที", PIP | n/m | 4 | white on green | hard cut | . |
| 46 | 2:28.32 | 2:29.78 | 1.47 | A | Face A-roll | push-in +5.2%/s (ORB) | 2 | green L1, white L2 | hard cut | p95 |
| 47 | 2:29.78 | 2:33.63 | 3.85 | G | PIP: Green card "ไม่ปรับลด LEVERAGE", phone + XAU coin, PIP | n/m | 4 | white on green | hard cut | p95 |
| 48 | 2:33.63 | 2:34.97 | 1.33 | B | PIP: White chart, PIP | static | 3 | none | hard cut | . |
| 49 | 2:34.97 | 2:36.67 | 1.70 | A | Face A-roll, small logo sticker top | static | 3 | green L1, white L2 | hard cut | . |
| 50 | 2:36.67 | 2:41.03 | 4.37 | G | PIP: Green card "13 ภาษา" repeat | n/m | 4 | white on green | hard cut | p95 |
| 51 | 2:41.03 | 2:43.92 | 2.88 | G | PIP: Green phone card repeat | n/m | 4 | white on green | hard cut | p95 |
| 52 | 2:43.92 | 2:49.55 | 5.63 | B | PIP: White chart with pink band, PIP | static | 3 | L1 green, L2 white | hard cut | **P98** |
| 53 | 2:49.55 | 2:58.02 | 8.47 | A | Face A-roll; 8.5 s hold | pull-out -2.4%/s (ORB) | 2 | green "Comment" + white; y 12-20% | hard cut | **P98** |
| 54 | 2:58.02 | 3:03.69 | 5.68 | E | PIP: Green comic-burst CFD risk card, PIP; 5.7 s | n/m | 3 | small white Thai paragraph | text-mask whip + glow flash | p95 |

Notes on (b): the type, content, layer and text columns were read by eye from per-shot contact sheets (3 frames per shot at 15 / 50 / 85%) and from full-resolution crops; positions and colours quoted in section (a) are the measured ones. Text positions in (b) are given only where visible. Transition names for FX come from strips at 60 fps around each event.

---

## (c) Edit blueprint: 102.72 s on the approved voice

Inputs: voice `/opt/MoonieXHQ/Work/mypasakon-voice/v3/mypasakon-v3-voice-tight.mp3` (102.72 s, 9 parts), font `Kanit-SemiBold.ttf` (`/opt/MoonieXHQ/Work/khaohom-survival/long/render16/fonts/`), our footage: `v3/avatar_ref.mp4` (15 s face, 1080x1920, 30 fps) and `footage/clip1_terminal.mp4`, `clip2_log.mp4`, `clip3_chart.mp4`, `clip4_table.mp4` (5 s each, 1080x1920, 30 fps). Words are from `v3/text/p01..p09.txt`; captions are our own cuts of those words. No ref footage, image or text is reused.

Voice part windows (from silence map, pauses of 0.12 s or more; part gaps in brackets): p01 0.48-7.35, p02 7.77-23.75, p03 24.16-43.43, p04 43.83-51.16, p05 51.59-62.78, p06 63.62-70.48, p07 70.91-80.91, p08 81.32-94.17, p09 94.61-102.72 (inner pause 100.17-100.31). Cuts below land on these pauses; where no pause exists the cut is placed on a caption page change and marked "confirm". Word-level times were not measured: confirm each cut against a forced alignment of the voice before building.

### c1. Targets, taken from the refs

| parameter | blueprint | refs |
|---|---|---|
| shots / cuts | 30 / 29 | 23-54 / 22-53 |
| cuts per 10 s | 2.82 | 1.85-2.89 |
| mean / median / min / max shot | 3.42 / 3.12 / 0.73 / 7.50 s | mean 3.4-5.2, median 3.4-3.7, min 0.15-0.43, max 8.5-22.7 |
| shots under 2 s / 2-4 s / 4-8 s / over 8 s | 6 / 14 / 10 / 0 | pooled: 25% under 2 s |
| face A-roll / split-or-panel with face | 39% / 8% | 15-31% / 0-9% |
| face visible incl. PIP | 84% | 40% / 21% / 99% |
| FX transitions | 9 (shots 2, 5, 10, 16, 21, 22, 25, 26, 30: star pop 1, ink-brush paper flash 5, panel slide-in 2, text-mask whip into the end card 1) | 3 / 9 / 7 |
| captions | Kanit-SemiBold, L1 accent green, L2 white, black outline 8 px, hero keyword gradient; glyph box 85 px for L1 (calibrate on the first render) | see a3 |
| end card | comic-burst card with star and CTA, last 2.5 s of the voice; an optional 3 s held tail after the voice would give 5.5 s like the refs (CMO call) | 1.4 / 5.0 / 5.7 s |

Deliberate differences from the refs: A-roll share is higher (we have 15 s of avatar and 20 s of unique screen footage, so face crops at 112-135% carry the variety); the longest hold is 7.5 s (ref3 style) rather than ref1's 22 s; there is no meme or stock-photo footage, so sub-second inserts are our own HTML icons and screen crops.

### c2. Shot-for-shot blueprint

Layouts: **card** = clip card 94% wide x 31% high, top edge at y 30-35%, near-white label box under it, top edge at y 70.5%, PIP 428 px top-right (ref1 geometry); **stack** = sharp card centre with blurred zoomed copy above and below (ref1 / ref2 geometry); **paper** = procedural paper bg with die-cut white-outline stickers (ref2 / ref3 geometry, PIP 256 px top-centre); **panel** = top panel (55% height) slides in over the face (ref3 99.15 s). Face crops are from `avatar_ref.mp4`, trimmed and re-cropped per shot so no two neighbouring shots share a crop.

| # | in | out | len | type | voice anchor | layout and footage | motion | layers | caption | transition into shot | SFX |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0:00.00 | 0:01.85 | 1.85 | A | p01 "นี่คือ AI" (speech starts 0.48) | avatar_ref face, punch-in crop 112% | static, 112% | 2: face + caption | hero "AI" cyan-blue gradient L1 (y 15-22%), L2 white "ที่ผมใช้จริง" y 25-30%; on frame 0 | start (caption already up at frame 0) | none; low riser under 0.0-1.8 |
| 2 | 0:01.85 | 0:03.70 | 1.85 | A | p01 pause 1.63-2.07 then "ที่ผมใช้เทรดจริง" | avatar_ref face over clip3_chart blurred as bg; star-sticker pop | face static; star pops 0.25 s with overshoot | 3: chart bg + face + star | L1 white, hard-pop page "เทรดจริง" | soft: star-sticker pop + bg swap (ref1 0.95 s grammar) | pop at 1.85 |
| 3 | 0:03.70 | 0:05.58 | 1.88 | B | p01 "มาตลอดแปดเดือน" | PIP: card layout: clip3_chart card (94% wide x 31% high, top edge y 30-35%), PIP 428 px top-right, label box | card slow zoom 100->106% | 4: dark bg + card + PIP + label | white label box, black Kanit, y 71-75%: "8 เดือน" | hard cut | tick |
| 4 | 0:05.58 | 0:07.56 | 1.98 | A | p01 "Claude Code นี่แหละนะครับ" | avatar_ref face, punch-in 125% (different crop than shot 1) | push-in 1.5%/s | 2 | hero "Claude Code" cyan gradient, L2 white "นี่แหละ" | hard cut (cut on pause 5.36-5.80) | hit on 5.58 |
| 5 | 0:07.56 | 0:11.93 | 4.37 | S | p02 "ลองมาหมดแล้ว ทั้ง ChatGPT ทั้ง Gemini ทั้ง Grok" | PIP: paper bg, HTML text-stickers ChatGPT / Gemini / Grok / บอทเทรด pop one by one (white die-cut 16 px, soft shadow) | each sticker spring-pops 0.25 s, then drifts 1%/s | 4: paper + 4 stickers + PIP 256 px top-centre + caption | L1 accent green "ลองมาหมดแล้ว" y 13-18%, L2 white | ink-brush paper white-flash (0.5 s) from p01 into p02 | whoosh on flash, pop x4 on stickers |
| 6 | 0:11.93 | 0:14.70 | 2.77 | A | p02 "แล้วก็บอทเทรด AI Agent อะไรที่เขาว่าดีๆ" | avatar_ref face punch-in 118% | static | 2 | L1 green "ที่เขาว่าดี", L2 white | hard cut (pause 11.71-12.14) | none |
| 7 | 0:14.70 | 0:16.20 | 1.50 | B | p02 "เนี่ย ลองมาหมดแล้วจริงๆ" (insert, 1.5 s) | clip2_log fast crop of the scrolling lines, full-bleed | whip-pan crop 8%/s | 2 | none (caption-free insert, like ref2 meme inserts) | hard cut (pause 14.56-14.85) | tick |
| 8 | 0:16.20 | 0:21.36 | 5.16 | A | p02 "แต่บอกตรงๆ ว่าไม่มีตัวไหนถูกใจเลยสักตัวเท่าตัวนี้" | avatar_ref face, slow push-in (5.2 s hold) | push-in 1.2%/s | 2 | page 1 L1 green "ไม่มีตัวไหน" / L2 white; page 2 at ~19 s "ถูกใจเท่าตัวนี้" | hard cut (pause 16.05-16.34) | none |
| 9 | 0:21.36 | 0:23.95 | 2.59 | G | p02 "แล้วก็ใช้มันอยู่ทุกวันจนถึงวันนี้นะครับ" | PIP: mint graphic card (HTML): big "ทุกวัน" + 8 tick marks filling; PIP | punch-zoom 100->112% in 0.4 s then hold | 4: mint bg + card + ticks + PIP | white on mint, y 20-30% | hard cut (pause 21.21-21.51) | pop |
| 10 | 0:23.95 | 0:29.17 | 5.22 | B | p03 "แล้วเอามันมาทำอะไรนะครับ ผมเอามันมาเป็นผู้ช่วยวิเคราะห์การเทรด" | PIP: card layout: clip3_chart card + blurred zoom duplicate as bg bands, PIP, label | card zoom 100->108% | 4: blurred dup + card + PIP + label | label pages: "ผู้ช่วยวิเคราะห์" (at 24.2) then "เทรดให้ด้วย" (~27) | ink-brush paper white-flash at p02->p03 gap 23.75-24.16 | whoosh |
| 11 | 0:29.17 | 0:32.14 | 2.97 | A | p03 "มันเทรดให้ผมได้ด้วย ทำสถิติให้ก็ได้" | avatar_ref face crop 125% | push-in 1.5%/s | 2 | L1 green "เทรดให้ผมได้", L2 white "ทำสถิติให้ก็ได้" | hard cut (pause 28.95-29.39) | none |
| 12 | 0:32.14 | 0:35.68 | 3.54 | B | p03 "คำนวณความเสี่ยงให้ก็ได้ แล้วก็ย้อนไปทดสอบ" | stack layout: clip4_table sharp card centre, blurred zoomed copy above and below | sharp card zoom 100->104% | 3: blurred dup + card + label | label pages "คำนวณความเสี่ยง" then "ย้อนทดสอบ" (pause 33.61-33.90) | hard cut (pause 31.84-32.44) | tick x2 |
| 13 | 0:35.68 | 0:39.93 | 4.25 | B | p03 "ย้อนไปทดสอบกับข้อมูลเก่าให้ได้หมดเลย" | PIP: card layout: clip2_log card, PIP, label | card zoom 100->106% | 4 | label "ข้อมูลเก่า ทุกตัว" | hard cut (pause 35.41-35.95) | none |
| 14 | 0:39.93 | 0:43.10 | 3.17 | A | p03 "สิ่งที่ชอบที่สุดเลยก็คือมันไม่หลับไม่นอนนะครับ" | avatar_ref face punch-in 135% (tightest crop = emphasis) | push-in 2%/s | 2 | hero "ไม่หลับไม่นอน" yellow-orange gradient L1, L2 white | hard cut (pause 39.62-40.23) | hit |
| 15 | 0:43.10 | 0:43.83 | 0.73 | X | p03->p04 gap 43.43-43.83 (0.73 s sub-second insert) | black card with HTML crescent-moon icon, no face | icon scales 90->100% | 1 | none | hard cut, exits through paper white-flash | whoosh into p04 |
| 16 | 0:43.83 | 0:46.90 | 3.07 | B | p04 "เมื่อคืนนี้ ก่อนเข้านอน สั่งมันไปแค่ประโยคเดียวเอง" | clip1_terminal full-bleed crop with HTML prompt card typing one line in Thai (our own words) | typing 14 chars/s; terminal zoom 100->105% | 3: terminal + prompt card + caption | L1 green "ประโยคเดียว" y 13-18%, L2 white "ก่อนนอน" | ink-brush paper white-flash | whoosh |
| 17 | 0:46.90 | 0:51.38 | 4.48 | A | p04 "ไปวิจัยกลยุทธ์การเทรดทุกตัวย้อนหลังห้าปี แล้วก็ไปนอนนะครับ" | avatar_ref face crop 128% with sticker "5 ปี" popping top-right | push-in 1%/s; sticker pop 0.25 s | 3: face + sticker + caption | L1 green "ย้อนหลัง 5 ปี", L2 white "แล้วก็ไปนอน" | hard cut (on caption page change; confirm vs forced alignment) | pop on sticker |
| 18 | 0:51.38 | 0:57.80 | 6.42 | A | p05 "พอตื่นเช้ามา เพื่อนๆ รู้ไหมครับว่าเจออะไร มันก็นั่งไล่ดูกราฟ" | avatar_ref face crop 105% (wide), slow push-in (6.4 s hold) | push-in 1%/s | 2 | pages: "ตื่นเช้ามา เจออะไร?" then at ~55 s "ไล่ดูกราฟทั้งคืน" (green L1, white L2) | hard cut (gap p04->p05 51.16-51.59) | none |
| 19 | 0:57.80 | 1:00.03 | 2.23 | G | p05 "ไล่ทดสอบให้เป็นหมื่นๆ รอบ" | PIP: mint graphic card: counter 0 -> 10,000+ rounds, PIP | counter eases out over 1.8 s; punch-zoom at start | 4: mint + counter + chart clip3 faint + PIP | white numerals y 20-30%, label "รอบ" | hard cut (pause 57.60-58.00) | tick-run under counter, hit at end |
| 20 | 1:00.03 | 1:03.20 | 3.17 | B | p05 "แล้วสรุปออกมาเป็นตาราง กลยุทธ์ไหนอยู่รอด ไหนพัง" | stack layout: clip4_table card + blurred dup; green/red cell highlight | card zoom 100->105% | 3 | label pages "อยู่รอด" (green box) / "พัง" (red box) | hard cut (pause 59.97-60.09) | tick x2 |
| 21 | 1:03.20 | 1:10.70 | 7.50 | T | p06 "มันบอกด้วยว่าทำไมถึงดี ชนะเพราะอะไร แล้วจะพังตอนไหน" | PIP: paper text card (7.5 s hold): two lines build at ~3 s steps: "ชนะเพราะอะไร" / "พังตอนไหน"; PIP | lines build word by word; paper static | 3: paper + text + PIP | red-accent Kanit with black offset shadow 5 px, y 30-55% (ref2 text-card grammar) | ink-brush paper white-flash (gap 62.78-63.62) | whoosh, pop per line |
| 22 | 1:10.70 | 1:15.58 | 4.88 | AS | p07 "งานแบบนี้ ถ้าผมนั่งทำเองคนเดียว ผมว่าเป็นเดือนก็ยังไม่เสร็จ" | top panel slides in (HTML calendar card "1 เดือน", 55% height) over avatar_ref face bottom | panel slides 0.3 s ease-out; face static | 3: face + panel + caption | L1 green on panel "เป็นเดือน", L2 white | soft: panel slides in from top | whoosh (short) |
| 23 | 1:15.58 | 1:17.67 | 2.09 | G | p07 "ก็ยังไม่เสร็จ" (contrast beat, 2.1 s) | split counter card: "1 เดือน" greyed vs "1 คืน" lit, no face | lit side punch-zooms 100->110% | 3 | white + accent | hard cut (pause 75.27-75.88) | hit |
| 24 | 1:17.67 | 1:21.12 | 3.45 | A | p07 "แต่มันทำให้เสร็จได้ในคืนเดียว ตอนที่ผมกำลังนอนหลับอยู่นะครับ" | avatar_ref face crop 130%, slow push-in | push-in 1.5%/s | 2 | L1 green "คืนเดียว", L2 white "ตอนผมนอนหลับ" | hard cut (pause 77.60-77.74) | none |
| 25 | 1:21.12 | 1:25.52 | 4.40 | B | p08 "ตัดสินใจแล้ว ว่าต่อจากนี้ช่องนี้จะไม่ได้มีแค่เรื่องเทรด" | PIP: card layout: clip1_terminal card, PIP, label | card zoom 100->106% | 4 | label pages "ไม่ได้มีแค่เทรด" then "สอนใช้ AI" | ink-brush paper white-flash (gap 80.91-81.32) | whoosh |
| 26 | 1:25.52 | 1:29.25 | 3.73 | AS | p08 "จะสอนใช้ AI มาเป็นผู้ช่วยตัวเองด้วย" | top panel (HTML "ผู้ช่วยของคุณ" card) over avatar_ref face | panel slide-in 0.3 s | 3 | L1 green, L2 white | soft: panel slides in | whoosh (short) |
| 27 | 1:29.25 | 1:31.38 | 2.13 | S | p08 "ตั้งแต่วิธีติดตั้ง ตั้งแต่สั่งงานครั้งแรก" | PIP: paper bg, sticker "1 ติดตั้ง" pops, then "2 สั่งงาน" pops, PIP | 2 spring pops 0.25 s | 4: paper + 2 stickers + PIP + caption | L1 green "ติดตั้ง", L2 white "สั่งงานครั้งแรก" | hard cut (pause 89.18-89.32) | pop x2 |
| 28 | 1:31.38 | 1:34.39 | 3.01 | B | p08 "ไปจนถึงเอาไปใช้จริงกับพอร์ตตัวเองนะครับ" | PIP: card layout: clip3_chart card + sticker "3 ใช้จริง" pops, PIP | card zoom 100->106% | 4 | label "ใช้จริงกับพอร์ต" | hard cut (pause 91.27-91.50) | pop, hit at 94.17 |
| 29 | 1:34.39 | 1:40.24 | 5.85 | A | p09 "ใครที่อยากลองของแบบนี้บ้าง คอมเมนต์คำว่า Claude ไว้ใต้คลิปได้นะครับ" | avatar_ref face, push-in (5.9 s) | push-in 1.2%/s | 2 | L1 green "คอมเมนต์", hero "Claude" cyan gradient L2; pages change at ~97 s | hard cut (gap 94.17-94.61) | none |
| 30 | 1:40.24 | 1:42.72 | 2.48 | E | p09 "เดี๋ยวผมทำคลิปสอนวิธีติดตั้งให้คุณดูกันแบบเต็มๆ ทีละขั้นตอนเลยนะครับ" | end card: comic-burst card with star, "คอมเมนต์ Claude" CTA + one risk line (wording = CEO/legal call) | burst scales 90->100% in 0.3 s | 3: burst + star + text | Kanit centred, black on light burst (ref end-card grammar) | text-mask whip + glow flash (ref3 grammar, 0.5-0.65 s) | whoosh + hit |

### c3. Build rules distilled from the refs

1. Caption is on screen at frame 0 and the face is on screen at frame 0 (shot 1).
2. Inside 3 s there is one pop or background-swap (shot 2), as in ref1.
3. No two neighbouring shots share a face crop. A face is on screen (full frame, split or PIP) at all times except two short runs, the longest 3.8 s (shots 15-16, 0:43.10-0:46.90). Counting PIP as no face, the longest stretch without a full-frame or split face is 12.9 s (0:57.80-1:10.70, shots 19-21), about the 14 s of ref1 and ref2.
4. Shot lengths come from three classes, not a grid: inserts 0.7-2.1 s (shots 1, 2, 3, 4, 7, 15, 23 and 27), working shots 2.5-5 s, holds 5.2-7.5 s (shots 8, 10, 18, 21 and 29).
5. Every non-face shot has 3 or more layers and one moving layer (blurred duplicate zoom, counter, typing, stickers popping).
6. FX only at part boundaries (shot 5 p01 to p02, shot 10 p02 to p03, shot 16 p03 to p04, shot 21 p05 to p06, shot 22 p06 to p07, shot 25 p07 to p08), the hook pop (shot 2), one panel in-shot (shot 26) and the end card (shot 30). All other cuts are hard.
7. Caption pop per layout: instant pages on card labels, 0.36 s wipe with overshoot on top-third captions, spring pop (0.25 s overshoot) on stickers.
8. Loudness -20 LUFS integrated, peak below -1 dBFS. SFX: a short hit or tick on about one cut in three plus every FX; voice stays on top.
9. Fonts: Kanit-SemiBold only (Thai and Latin); L1 hero keyword may use a cyan-blue or yellow-orange gradient fill.

### c4. Open points for the CMO

- The end-card risk wording and whether the 3 s tail is added.
- Whether the shot 15 sub-second moon insert is too abstract; the alternative is to fold it into shot 14.
- SFX files are not chosen; resolve them through the media-use SFX resolver and keep the hits at 1 in 3 cuts.

---

## Method and limits

- Cut detection: ffmpeg scene scores per frame at 270x480, clustered at 0.20 / 0.35 s; soft transitions from a lag-10 frame diff; every boundary confirmed on strips or per-shot sheets.
- Caption geometry: colour masks on full-resolution frames (n=20 for ref3 green line 1, n=6 usable for ref2 line 1/2, n=10 for ref1 white text and n=14 for ref1 labels); medians reported, the 1st-99th percentile used for box edges. Gradient hero text and stroke widths are visual estimates.
- Motion: ORB features on 540x960 frames at shot start+0.15 s and end-0.10 s, RANSAC partial affine; the estimate is wrong when contents change between the two frames, so it is shown only where trusted.
- Audio: mono 22.05 kHz STFT (1024 / 10 ms), spectral flux, cut-aligned averages against 500-1000 random times; no stems exist, so effects and speech are confounded.
- Not measured: per-layer speeds of background layers, exact shadow parameters, the type of the 110.37 s transition in ref1, word-level times of our voice.
