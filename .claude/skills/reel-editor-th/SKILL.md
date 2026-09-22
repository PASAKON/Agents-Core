---
owner: CTO
created_by: human
origin: mooniex-org
name: reel-editor-th
description: >-
  Turn a talking-head clip (a single person to camera, usually shot on a
  phone) into a finished vertical 9:16 Thai-subtitled Instagram/TikTok Reel
  with a professional fast-cut rhythm: the talking head alternates with
  footage cutaways (still photos or real motion video b-roll) and animation
  beats (kinetic typography or full-frame info-graphic cards) roughly every
  1.5-3.5s, word-by-word Thai captions with green keyword highlights added as
  a separate final layer, a 3-second hook, CTA chips, sparse SFX, and a
  matching cover. Use this whenever you have an .mp4 of a single person
  talking and want subtitles, a reel, "ตัดคลิป", "ทำ reel", "ใส่ซับ",
  "subtitle", captions, or a viral IG/TikTok video. Also use it when
  re-rendering a reel already made with this pipeline (style, captions, CTA,
  cutaway rhythm, cover tweaks). Do NOT use it for building a video from
  scratch with no footage, for non-Thai narration, or for multi-person edits.
---

# IG Reel (Thai talking-head) — MoonieX org edition

A repeatable pipeline that turns one talking-head clip into a polished,
professionally-paced 9:16 Thai reel. The hard parts (HDR color, Thai word
segmentation, caption motion, cutaway compositing) are solved in bundled
scripts. Your job per clip is to author one file — `timeline.py` — from the
transcript, then run `build.sh`.

**MoonieX org context**: this skill is CTO-maintained (the code/pipeline).
The *process* of directing what to cut, brand voice, and asset sourcing is
owned by CMO via the `video_editor` role — see the companion
`mooniex-video-editor` skill for that org-specific layer. This skill alone is
also fully usable standalone (personal/non-org use).

## Default preferences (override per project)

- **Style = `clean`** (translucent pill + green underline on the active
  word). It reads premium/editorial. `bold` (loud TikTok) and `terminal`
  (coder) also exist — pick per brand fit, not by default.
- **No color filter on the talking-head footage — true colors.** The
  pipeline only fixes HDR→SDR so colors are correct (see below); it does NOT
  grade the avatar shot. Footage/photo cutaways DO get a dark/moody grade
  automatically (contrast+15%, saturation-15%, brightness-8% down) — that's
  intentional and separate.
- **No em dashes** anywhere in copy — an AI tell, not natural Thai.
- **Accent green `#0BDE85`** on near-black by default (override via
  `timeline.ACCENT`). Highlight only payload words (nouns, numbers, product
  names), not everything.
- **CTA points to the BIO**, not "comment a keyword". Keep a follow CTA.
- Hook is provocative and lands on-screen text within the first second
  (most viewers watch muted).
- Font is **Sukhumvit Set** (bundled on macOS). No Kanit/Prompt installed.
- **SFX must stay SPARSE.** A whoosh on literally every cut (10+ identical
  samples) reads as repetitive/annoying on review, not "professional". Use 2-4
  distinct sounds tied to genuinely discrete UI moments (a chip popping in, a
  tag appearing) — not one sound hammered on every hard cut. When in doubt,
  fewer SFX events, not more.

## The cut-rhythm rule (added 2026-08-03 — do this by default, not just when asked)

A talking-head reel that never cuts away reads as amateur. Alternate three
beat types roughly every **1.5-3.5s**, driven by phrase/sentence boundaries
(never cut mid-word):

- **Avatar** — the talking head, for thesis statements, personal anecdotes,
  naming things ("Revenge Trade"), and the hook/close. Never let one
  continuous avatar run exceed ~3.5s — always cut away before returning.
- **Footage** — a full-frame hard-cut cutaway (photo OR real motion video),
  matched to what's being said. Photo and video cutaways can sit back-to-back
  without needing an avatar beat between them (viewer still perceives change).
- **Animation** — a full-frame PIL-drawn beat: kinetic typography (1-2 big
  bold words, accent-colored) for a punchy short line, or an info-graphic
  card (checklist/numbers) for a "there are N things" setup line. Also counts
  as a hard cut; captions are suppressed during these (see below) since the
  animation itself IS the caption in styled form.

Plan the whole clip's beats against the transcript BEFORE authoring
`timeline.py` — see `references/cutaway-authoring.md` for the exact
`CUTAWAYS` schema (`photo` / `video` / `kinetic` / `card`) and a worked
example.

## Two-layer render: picture-lock first, captions LAST (added 2026-08-03)

`build.sh` renders the word-by-word caption as its own SEPARATE final overlay
layer, composited on top of everything else (`render_overlay_video.py ... scene`
then `... subs`, then two `overlay=0:0` stages in ffmpeg). Do not merge these
back into one pass — keeping the caption as the last layer means it never
bakes in or visually couples with whatever cutaway/background is behind it,
and lets you review the cut rhythm on its own before captions go on.

## Environment setup (one-time gotcha)

Homebrew's default `python3` is externally-managed (PEP 668) — `pip install`
into it fails. Use a dedicated venv on `python3.12` (mlx-whisper is
bleeding-edge sensitive; 3.12 tested working, `python3.14` untested):
```
/opt/homebrew/bin/python3.12 -m venv ~/.claude/skills/reel-editor-th/.venv
source ~/.claude/skills/reel-editor-th/.venv/bin/activate
pip install --quiet pillow mlx-whisper
```
Reuse this same venv across clips instead of recreating it each time.

## Workflow

Work in a fresh per-clip directory (e.g. `~/Desktop/ig/<clip-name>/`).

**1. Transcribe (Thai, word-level segments).** Use mlx-whisper (fast on Apple
Silicon). Turn OFF conditioning or the tail loops into garbage:
```
python3 -c "import mlx_whisper,json; r=mlx_whisper.transcribe('audio.wav', \
 path_or_hf_repo='mlx-community/whisper-large-v3-turbo', language='th', \
 word_timestamps=True, condition_on_previous_text=False, verbose=False); \
 [print(f\"[{s['start']:.1f}-{s['end']:.1f}] {s['text'].strip()}\") for s in r['segments']]"
```
Extract audio first: `ffmpeg -i source.mp4 -vn -ar 16000 -ac 1 audio.wav`.
**Word-level timestamps for Thai are near-useless** (mlx-whisper tokenizes at
the syllable/character level since Thai has no spaces) — use the SEGMENT
boundaries (reliable) and distribute caption chunks proportionally within
each segment by hand/eye, per the authoring guide. Fix obvious ASR errors by
ear before authoring captions.

**2. Plan the beats.** Read the full segment transcript, decide which spans
are Avatar / Footage / Animation per the cut-rhythm rule above. Pick specific
assets: check `assets/mooniex-broll/` first (already-sourced, no-baked-text
trader mood photos + 2 motion b-roll clips + their pre-extracted 9:16 PNG
frame sequences — see the filenames, they're descriptive) before sourcing
anything new. For anything not covered there, MoonieX's own Google Drive
"BLACK LIQUIDITY" project (owner pass.gob1@gmail.com) has a much larger
per-episode photo library — ask the CEO/CMO which Drive folder if a specific
topic needs a specific image; don't guess which of several similarly-named
episode folders is "the" one.

**3. Author `timeline.py`.** Copy `scripts/timeline_template.py` into the
workdir. Fill `CAPTIONS`/`HOOK_TEXT`/`CTA` per the original authoring guide,
PLUS `CUTAWAYS` (and optionally `COUNTERS`, `SFX_EVENTS`) per
`references/cutaway-authoring.md`.

**4. Build:**
```
bash ~/.claude/skills/reel-editor-th/scripts/build.sh <source.mp4> <workdir> clean
```
Output: `<workdir>/out/reel_clean.mp4` + `cover_*.jpg`.

**5. Verify before delivering.** Sample a frame from EVERY beat (not just a
couple) and actually LOOK: colors natural, Thai tone marks intact, no tofu
boxes, cutaway aspect not distorted (source that isn't already 9:16 needs
scale-to-cover + crop, not a bare non-uniform scale — `build.sh` already does
this), caption not duplicated under kinetic/card beats, hard cuts land
exactly on phrase boundaries (check the frame right before AND right after
every cut point). Fix in `timeline.py` and re-run.

**6. Deliver.** Copy the mp4 + a cover + a caption/hashtag doc into a
clearly-named folder (e.g. on the Desktop — macOS may block *overwriting*
existing Desktop files from the shell, use a new folder/filename if needed).

## What each script does

- `tonemap.swift` — HDR(HLG)→SDR bt709 via AVFoundation. Compiled on first build.
- `render_lib.py` — fonts, easing, text drawing helpers.
- `render_captions.py` — caption styles, hook, punch, CTA, counter tag, AND
  the cutaway system (`draw_cutaway`, `draw_kinetic`, `draw_traps_card`,
  photo/video loaders). Exposes `build_frame_scene` (everything but captions)
  and `build_frame_subs` (captions only) as the two render passes.
- `render_cards.py` — the original top-band demo cards (skillmd/arrow/
  claudechat/excel/browser). **Check your footage framing before using
  these** — if the talking head fills most of the vertical frame (beanie/hat
  touching the top edge, no headroom), these WILL cover the face. Prefer a
  `CUTAWAYS` `"card"` beat (full-frame, no face to avoid) instead for tight
  framing.
- `render_overlay_video.py` — renders either layer to a ProRes4444 alpha
  `.mov`; takes a `scene`/`subs`/`all` 3rd CLI arg.
- `render_cover.py` — 3 Reel covers. **The `cover_clean` text/checklist
  content is hardcoded per-topic** and does NOT read `timeline.py`. It ships
  as an obvious `[placeholder]`-text template — fill it in per clip, but
  **edit the copy `build.sh` places in YOUR OWN workdir, never this shared
  master file** (`~/.claude/skills/reel-editor-th/scripts/render_cover.py`).
  Two clips run back-to-back (or in parallel) both read/write this same path
  with no lock — a prior clip's hardcoded content silently became the next
  clip's stale default this way (confirmed 2026-08-03, see
  `references/cutaway-authoring.md` gotchas). The same rule applies to any
  other shared script you're tempted to tweak per-clip.
- `build_audio.py` — derives/mixes SFX from `timeline.py` (`SFX_EVENTS`
  overrides auto-derive, which only covers legacy `INSERTS`/`REVEAL_T`/
  number-captions/`PUNCH_TEXT` and produces nothing for `CUTAWAYS`-based
  timelines without an explicit override).
- `build.sh` — orchestrates: tonemap → scene overlay → subs overlay → SFX →
  composite (base + scene + subs, in that order) → mux → covers.

## SFX library

`~/.claude/skills/hyperframes-media/assets/sfx/` — `whoosh-short.mp3`,
`pop.mp3`, `chime.mp3` (free, Mixkit license, commercial use OK, no
attribution required). Use sparingly (see preferences above).

## Common tweaks

- Different caption look → change the `style` arg (`clean`/`bold`/`terminal`).
- Reposition/resize captions → `STYLES[...]["y"]` and `["size"]` in `render_captions.py`.
- Change the CTA offer/number → `draw_cta` in `render_captions.py`.
- Add a new cutaway asset type → extend `draw_cutaway` in `render_captions.py`.
