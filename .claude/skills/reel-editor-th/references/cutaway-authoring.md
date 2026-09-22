# Authoring CUTAWAYS / COUNTERS / SFX_EVENTS (added 2026-08-03)

These three `timeline.py` variables layer on top of the original
`CAPTIONS`/`HOOK_TEXT`/`CTA` schema (see `authoring-guide.md`) to implement
the cut-rhythm rule from SKILL.md. All are optional — omit any of them and
that feature is simply unused (backward compatible with older timelines).

## CUTAWAYS — full-frame hard cuts

```python
CUTAWAYS = [
    (start_sec, end_sec, "photo", "/abs/path/to.jpg"),
    (start_sec, end_sec, "video", ("/abs/path/to/frame_folder", fps)),
    (start_sec, end_sec, "kinetic", (["line one", "line two"], {accent_line_idx, ...})),
    (start_sec, end_sec, "card", None),
]
```

- **`photo`**: cover-crops the image to the canvas + applies a dark/moody
  grade automatically. No baked-in text in the source image (check before
  using — a picture with someone else's caption already burned in will read
  as wrong/confusing under your own narration).
- **`video`**: plays back a PRE-EXTRACTED PNG frame sequence (no video-decode
  library is installed in the venv — mlx-whisper's numpy/torch stack doesn't
  include cv2/imageio). Extract once per beat:
  ```
  ffmpeg -ss <offset> -i source.mp4 -t <beat_duration> \
    -vf "scale=-2:1920:flags=bicubic,crop=1080:1920,fps=30" \
    -start_number 0 out_folder/frame_%04d.png
  ```
  Frame index at render time = `int(local_t * fps)`, clamped to the last
  frame if the beat runs slightly longer than extracted.
- **`kinetic`**: full-frame dark background + big bold pop-in text (1-2
  lines). `accent_idx` is a `set` of line indices to color red/accent instead
  of white — use it to punch the one word/line that matters (a number, a
  consequence, a named mistake).
- **`card`**: the full-frame 3-item checklist card (currently hardcoded to
  the "3 traps" content in `draw_traps_card` — generalize this function if a
  future clip needs a different checklist; don't just reuse the trap labels
  for unrelated content).

**Suppression rule (already wired in `render_captions.py`)**: `kinetic` and
`card` beats suppress the normal word-by-word caption (they ARE the caption,
just styled bigger) — the code checks `_current_cutaway_kind(t)` before
calling `draw_caption`. `photo` and `video` beats do NOT suppress it — the
spoken-word caption keeps running as pure B-roll under it, which is correct
(the viewer is still reading along with the voice, they've just cut away
visually).

## COUNTERS — small top-right tag

```python
COUNTERS = [
    (start_sec, end_sec, "label text"),
]
```
Reuses the `save_sticker` slot (top-right, `y=250`) — only safe if its
window doesn't overlap `CTA["save_sticker"]`'s window. Use for naming a
concept while the avatar or a cutaway is on screen (e.g. tagging which named
trap/step is currently being discussed). Don't invent counts you can't back
("1/3" when the clip only actually covers 2 of 3) — only label what's
actually said.

## SFX_EVENTS — manual override

```python
SFX_EVENTS = [
    (time_sec, "sound_name", gain_0_to_1),
]
```
`build_audio.py`'s auto-derive only looks at legacy `INSERTS`/`REVEAL_T`/
number-only-captions/`PUNCH_TEXT` — a `CUTAWAYS`-based timeline needs this
override or it produces silence (no SFX, not an error). **Keep this list
short.** A whoosh on every single cut point (10+ uses of the same sample)
reads as repetitive on review — reserve SFX for 2-4 genuinely distinct UI
moments (a tag popping in, a follow chip appearing), not as a transition
sound for every cut. Available samples:
`~/.claude/skills/hyperframes-media/assets/sfx/{whoosh-short,pop,chime}.mp3`.

## Worked example (from the first MoonieX test clip, 2026-08-03)

A 40s trading-psychology talking-head clip, cut into 15 beats alternating
avatar/footage/animation every ~2-3s:

```python
_INS = os.path.expanduser("~/.claude/skills/reel-editor-th/assets/mooniex-broll")
CUTAWAYS = [
    (4.60, 7.32, "video", (f"{_INS}/frames-candlestorm-2.72s", 30)),
    (10.30, 13.18, "video", (f"{_INS}/frames-candleglow-2.88s", 30)),
    (16.80, 18.90, "kinetic", (["ตัด SL", "ไม่ได้"], {0})),
    (18.90, 21.30, "photo", f"{_INS}/trader-laptop-cash-risk.jpg"),
    (24.48, 26.78, "card", None),
    (30.36, 32.78, "photo", f"{_INS}/trader-silhouette-red-tradingfloor.jpg"),
    (32.98, 34.60, "kinetic", (["กลับยิ่ง", "ขาดทุนหนักขึ้น"], {1})),
    (36.50, 38.14, "photo", f"{_INS}/trader-victory-confetti.jpg"),
]
COUNTERS = [
    (27.22, 34.60, "กับดัก: Revenge Trade"),
    (35.62, 40.0, "กับดัก: Overconfidence"),
]
SFX_EVENTS = [
    (2.05, "pop", 0.30),
    (27.27, "pop", 0.30),
    (35.67, "pop", 0.30),
    (36.05, "chime", 0.32),
]
```

Notice the beats NOT listed above (0-4.6, 7.74-10.3, 13.42-16.8, 21.3-24.06,
27.22-30.14, 35.62-36.5, 38.14-40.0) are plain avatar — `CUTAWAYS` only needs
entries for the non-avatar beats; everything else defaults to showing the
talking head.

## Gotchas found by the first cold-start video_editor test (2026-08-03)

- **`INSERTS` is a separate, legacy variable `CUTAWAYS` does NOT replace.**
  `render_cards.py`'s `draw()` reads `timeline.INSERTS` directly — even a
  `CUTAWAYS`-only timeline needs `INSERTS = []` defined or it crashes with
  `AttributeError`. (Now hardened with a `getattr` fallback in the shared
  code, but keep defining it explicitly — cheap and clear.)
- **`HOOK_TAG` has a default you almost certainly don't want**:
  `render_captions.py`'s `draw_hook` falls back to `"ทริค AI ที่ออฟฟิศไม่บอก"`
  (leftover copy from an unrelated demo clip) if `timeline.HOOK_TAG` is
  unset. Always set it explicitly per clip.
- **`PUNCH_TEXT` now auto-fits** (matching `HOOK_TEXT`'s behavior) — a long
  punch line shrinks to fit the canvas instead of overflowing both edges.
  Still keep it short; auto-fit is a safety net, not a design goal.
- **Never edit a shared skill script in place for one clip's content.**
  `render_cover.py`'s `cover_clean()` is NOT git-tracked and NOT per-task —
  two `video_editor` tasks running back-to-back or in parallel both read/
  write the exact same file with no lock. `build.sh` already copies every
  `render_*.py` into your own workdir before running
  (`cp -f "$SCRIPTS"/render_*.py ... "$WORK/"`) — make your per-clip edits
  to `$WORK/render_cover.py`, never to the path under
  `~/.claude/skills/reel-editor-th/scripts/`. This bit a real test: one
  clip's 2-item checklist silently became the next run's default content.
