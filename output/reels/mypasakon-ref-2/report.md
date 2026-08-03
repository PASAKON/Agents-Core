# mypasakon-ref-2 — edit report

Source: `mypasakon-183BJc8fUwoXHmwUjp3i0ffrRkbOzE12t-1779572870912-ref-2.mp4`
(20s, 1080x1920, 30fps). Content: Tesla stock drops 15% in a day after a
public Trump/Elon Musk spat.

## Delivered

- `~/Desktop/video-editor-mypasakon-ref-2/reel_clean.mp4`
- `~/Desktop/video-editor-mypasakon-ref-2/cover.jpg`
- `~/Desktop/video-editor-mypasakon-ref-2/caption.txt`
- `timeline.py` (this folder) — authored per-clip file
- `render_cover.py`'s `cover_clean` was edited in the **workdir copy only**
  (`~/Desktop/ig/mypasakon-ref-2/render_cover.py`, copied there by
  `build.sh`), not in the shared skill file — per its own comment it's
  hardcoded per-topic and meant to be edited each time.

## Beats

- 0.0-4.2 avatar (HOOK: "Tesla ร่วง 15% / ในคืนเดียว")
- 4.2-7.7 footage (video) — candlestorm b-roll, freshly extracted at the
  beat's exact 3.5s duration (not the pre-extracted 2.72s asset, to avoid a
  clamped freeze-frame)
- 7.7-11.2 avatar (date/time exposition)
- 11.2-14.0 footage (photo) — trader-laptop-cash-risk.jpg
- 14.0-16.2 footage (photo) — trader-silhouette-red-tradingfloor.jpg
- 16.2-17.8 animation (kinetic) — "4 ทุ่ม 45 / ตอบโต้ทันที"
- 17.8-20.0 avatar (cliffhanger close + PUNCH_TEXT + CTA cascade)

## Assets used

- `assets/mooniex-broll/broll-candlestorm-15s.mp4` — re-extracted my own
  3.5s/105-frame PNG sequence at offset 0 (not the pre-extracted
  `frames-candlestorm-2.72s` folder) so the beat runs full-length without
  clamping to a frozen last frame. Candle motion reads well for a stock-crash
  story even though it's mood b-roll, not a literal price chart.
- `assets/mooniex-broll/trader-laptop-cash-risk.jpg` — no baked text, checked.
- `assets/mooniex-broll/trader-silhouette-red-tradingfloor.jpg` — no baked
  text, checked.
- Skipped `trader-stressed-BAKED-TEXT-avoid.jpg` (explicitly flagged) and
  `trader-victory-confetti.jpg` (wrong tone — celebratory doesn't fit a
  stock-crash/conflict story).
- Did not need to go to Drive; mooniex-broll covered everything.

## Brand / judgment calls

- **Source-truncation, flagged**: the clip's last line ("Elon Musk บอกว่า...
  ถ้าไม่ใช่ผมเนี่ย...") cuts off mid-sentence exactly at the 20.0s file
  boundary — Musk's rebuttal is never completed. Per the brand rule against
  inventing structure the source doesn't support, I did NOT fabricate a
  resolution or punchline. Instead I used the actual last spoken words as
  `PUNCH_TEXT` (an honest cliffhanger, not an invented one) and framed the
  follow CTA as "what did Musk say next, follow for the update" rather than
  claiming a payoff that was never said.
- **ASR correction**: mlx-whisper's raw Thai output had several garbled
  segments (e.g. "ลวงสันที 15%" -> "ร่วงลงไป 15%", "ห้ามพิธุนา" -> "5 มิถุนา",
  "ออกประตอบโต้" -> "ออกมาโต้ตอบ"). Corrected by ear/context against the
  reliable segment boundaries before authoring captions; no COUNTERS tag
  used since there's no discrete named list in this content (news story, not
  a trap-checklist clip), so nothing to mis-count.
- **Caption position fix**: this speaker's framing is tight (beanie brim near
  the top edge, eyes sitting low in frame) -- the pipeline's default
  `clean`-style caption y=1215 landed the caption bar directly over the eyes
  in every avatar beat (confirmed visually in initial QC pass). Used the
  existing per-clip `CAPTION_Y` override already built into
  `render_captions.py` (`cy = getattr(T, "CAPTION_Y", st["y"])`, line 47) --
  set `CAPTION_Y = 1000` in timeline.py to move it up onto the
  forehead/brim band instead. Re-rendered subs overlay + recomposited +
  remuxed only (skipped tonemap/scene/audio since those didn't change).
  Re-checked every affected frame after the fix.
- SFX kept to 4 distinct moments (whoosh on the b-roll cut-in, chime on the
  Trump reveal, pop on the kinetic time-stat, pop on the follow chip) -- no
  repeated whoosh-per-cut.
- `cover_clean`'s hardcoded "3 traps psychology" content (headline + mini
  checklist card) was rewritten to match this clip's actual topic (Tesla/
  Trump/Musk headline + a 3-line conflict timeline card), per the skill's
  own instruction that this function is topic-hardcoded and must be edited
  each time.

## Issues / gaps found in the skill docs

None blocking. One thing worth a note for future clips: the hook-caption
suppression boundary (`t >= 4.6` hardcoded in `render_captions.py`) is
independent of whatever `HOOK_TEXT` end time you set in `timeline.py` -- if a
clip's first segment naturally ends before or after 4.6s, there's a small
silent gap (no hook text, no caption) worth planning around rather than
being surprised by. Not a bug, just an implicit coupling that isn't spelled
out in the authoring guide.
