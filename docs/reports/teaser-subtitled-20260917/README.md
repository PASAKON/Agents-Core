# Thai subtitle proof — "เงินที่พ่อตั้งใจหา" teaser

Proves the org's first Thai-subtitle chain end to end on this project:
transcribe the 56s teaser's actual audio, produce a timed `.srt`, burn it
in, ship a watchable file. No new footage generated — everything here is
the 7 already-paid-for clips assembled today.

## What's in this folder

- `teaser-th.srt` — 3 subtitle cues, timed to the transcribed audio.
- `render_subs_overlay.py` — renders any `.srt` to a transparent ProRes4444
  alpha overlay sized to a source video (see "Why not the normal
  `subtitles=` filter" below).
- `render.sh` — the reusable build: concats the 7 source clips → runs the
  overlay renderer → composites → `teaser-ngoen-tee-por-th.mp4`. Run from the
  repo root: `bash docs/reports/teaser-subtitled-20260917/render.sh`.
- `teaser-ngoen-tee-por-th.mp4` — the delivered, subtitled file (56.04s,
  720x1280, matches the source teaser exactly).

## Transcription method

Extracted audio (`ffmpeg -vn -ar 16000 -ac 1`), ran mlx-whisper
(`whisper-large-v3-turbo`, `language='th'`, `word_timestamps=True`,
`condition_on_previous_text=False`) per `reel-editor-th`'s workflow. It
found exactly 3 spoken segments (18.26-20.72s, 25.46-27.72s, 50.84-52.18s).
I did not trust that as "the ASR missed 4 shots" — I cross-checked with
`silencedetect` + `volumedetect` per 8s shot window, and separately with
the committed shot table (`git show HEAD:docs/scripts/ngoen-tee-por-EP1.md`,
read for context/spelling-check only, per the task's own allowance — no
dialogue was copied from it). Both confirm shots 1, 2, 56, 57 are scripted
**SILENT** (wordless hook + reaction beats); the 3 ASR segments line up
exactly with the 3 shots (54, 55, 58) the shot table marks as having
dialogue. So the transcript is complete, not clipped — the committed script
was only used to fix two obvious ASR spelling slips against what's actually
audible ("มาจะไหน" → "มาจากไหน", "สมัก" → "สมัคร") — no word was added or
changed in meaning, timing untouched.

## Shot 55 — confirmed incomplete, not silently patched

Task brief said shot 55's clip audio was truncated by a Windows encoding
bug. The transcript confirms it: audio ends at "...ไม่ต้องรู้ว่ามันมาจากไหน"
and the payoff clause "แค่ใช้มันให้คุ้ม" (present in the script) is not
audible in this clip — there's 4.3s of silence after it before shot 56
starts (confirmed by `silencedetect`). The subtitle for shot 55 reflects
only what's actually spoken. This is a source-clip defect, not something
subtitling can fix — flagging here per instructions rather than inventing
the missing line.

## Thai rendering — does it actually work?

**Yes**, checked frame-by-frame at each caption and at every shot-boundary
cut. Font is **Sukhumvit Set Bold** (bundled macOS system font, matches
`reel-editor-th` default). Specifically checked stacking on:
- **ก่อน** — appears in caption 3 ("กินก่อนไปสมัครงานนะ"): ไม้เอก sits
  correctly above ก, สระออ + น read cleanly. Correct.
- **ตั้ง / ให้ / ต้อง / รู้** — all present in captions 1-2: tone marks
  (ไม้โท) and upper/lower vowels (สระอิ, สระอุ) stack on the right base
  consonant, no floating/offset glyphs, no tofu boxes.
- **ที่ / ผู้ / เมื่อ** — none of these three specific words occur in this
  clip's actual dialogue (can't fabricate text just to test them), so I
  can't confirm them in-context here. Confidence is high (same font + same
  PIL baseline-metrics draw path handles all of the above correctly), but
  if a future clip needs those exact words verified, check them then rather
  than assuming from this result.

No color grade, no watermark, no music, no SFX added — subtitles only, per
the hard stop.

## Why not the normal ffmpeg `subtitles=` filter

`SKILL-OVERRIDE: reel-editor-th :: build.sh's usual subtitles/karaoke-caption
path :: wrote a standalone PIL-based overlay renderer instead :: this
machine's ffmpeg 8.1 (homebrew) has no libass or drawtext compiled in
(confirmed via ffmpeg -filters — no "subtitles" filter listed, and
"ffmpeg -h filter=subtitles" returns "Unknown filter"), so the standard
"-vf subtitles=file.srt" burn-in isn't available on this box. Reused
reel-editor-th's own workaround pattern (PIL -> transparent ProRes4444 alpha
.mov -> ffmpeg overlay) instead of the full render_captions.py/timeline.py
machinery, because that machinery is built for word-by-word karaoke
captions on a raw talking-head clip needing hook/CTA/cutaway authoring —
this input is already an assembled 7-shot cut and the task's hard stop is
"subtitles only, one variable at a time, no branding." A plain
white-text-on-black-box burn (not the green-accent "clean" karaoke look) is
what actually matches that scope.`

## Style choices

- White text, black outline + semi-transparent rounded box behind each line
  — maximizes contrast against dark night footage; the footage itself is
  genuinely dark/low-key, so box + outline was the only way to guarantee
  phone-size legibility without a color grade.
- Positioned with a safe margin (20% of frame height) above the bottom edge,
  clear of Instagram's UI chrome.
- Font auto-shrinks to fit width before wrapping to a second line — none of
  the 3 captions needed a second line at this clip's line lengths.

## What I could not do / did not do

- Did not add a hook, CTA, cutaways, cover image, or any caption
  word-highlighting — out of scope per the hard stops ("subtitles only").
- Did not touch `docs/scripts/ngoen-tee-por-EP1.md` (locked by another
  task) — read via `git show HEAD:...` for context only.
- Did not fix or re-encode shot 55's underlying audio truncation — that's a
  source-footage bug, not a subtitling problem.
- Pillarboxing visible on shot 2 (grey bars top/bottom in the frame) is
  baked into that source clip itself (confirmed identical in the original
  un-subtitled teaser and in
  `docs/reports/teaser-shoot-winbox-20260907/shot02.mp4` directly) —
  pre-existing, not introduced by this task, and out of scope to fix (no
  source-clip edits allowed).
