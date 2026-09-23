# BLACK LIQUIDITY EDL schema — layers, not one big HTML

CEO ruling 2026-09-23: one AI hand-writing the whole `index.html` loses
detail, and the longer the clip the more it drops. The cut is now **layers,
one JSON file per editing phase**. Different workers fill different layers at
the same time; a deterministic composer (`scripts/bl_compose.py`) turns the
layers into `index.html`. No AI writes HTML any more.

## The phases (CEO's own words)

| layer | file | phase |
|---|---|---|
| P1 | `p1_layout.json` | เลือก B-Roll + Footage + Avatar ก่อนว่าจะวางช่วงไหน วินาทีที่เท่าไหร่ เป็นการวางดิบแบบไม่มี Animation |
| P2 | `p2_focus.json` | เริ่มใส่ Animation การย่อลง การ Highlight การ zoom fade in fade out เพื่อให้คนดู Focus ที่จุดที่เราจะนำเสนอเท่านั้น |
| P3 | `p3_text.json` | เริ่มใส่ Text เพื่ออธิบาย ใส่ตรงไหน เหลือที่วางเท่าไหร่ ไม่บังจุด Focus และไม่ติดขอบ |
| P4 | `p4_audio.json` | เสียง Effect VFX + Soundtrack ให้ตรงกับทุก transaction ใน P1 - P3 |
| P5 | (constant, in `template/index.html`) | ลายน้ำ Blackliquidity — §6a brand bug, §6b legal label |

P5 needs no layer file: it never changes per episode except the bug's date,
which `bl_compose.py` reads off P1's `episode.bug_date`.

Only **P1 is fully implemented** by `scripts/bl_compose.py` today. P2-P4 are
schema-validated (unknown `type`, dangling `refs`, bad `t0/t1` all fail the
composer loudly) but render nothing — later tasks add one renderer per event
type.

## File layout

```
<episode-edl-dir>/
  p1_layout.json      required
  p2_focus.json        optional — validated if present
  p3_text.json         optional — validated if present
  p4_audio.json         optional — validated if present
```

`prototypes/bl55-cut/edl/` is the worked example (EP55's approved cut,
P1 only — P2-P4 don't exist for that episode yet).
`.claude/skills/blackliquidity-cut/edl/example/` is a tiny made-up 2-shot
episode ("epXX") showing all four files and how a later layer points back
at an earlier one **by id**.

## Shared rules, every layer

- **Every event carries a stable `id`, unique within its own file.** IDs are
  never reused across episodes and never renumbered once another layer
  references them — a later layer refers to an earlier event **by id, never
  by time**. Example: a P4 whoosh binds to the P2 shrink's `id`, so retiming
  P1 cannot orphan a sound; if P1 moves a plate, the P2/P3/P4 events that
  reference it by id are still correctly bound, only their own `t0/t1` (which
  a human or a later pass re-times) can go stale.
- **`t0`/`t1` are seconds on the voice-track clock** — the same clock
  `bl_tools.py offsets` and `verify` already use. Not frames, not a percent,
  not a per-layer-local clock.
- **Coordinates are px on the 1080x1920 canvas** — the same canvas the
  template's `#root` uses. `(0,0)` is top-left.
- **`type` + `params`.** `type` is a string naming what the event does.
  `params` is an object whose shape depends on `type`. P1 has exactly one
  `type` (`"plate"`, see below). P2-P4 draw `type` from the open registry in
  `event_types.json` (next section).
- Every layer file's top level also carries `episode` (string id, e.g.
  `"bl55"`) and `duration` (seconds — the voice track length). P2-P4 events
  must all fall inside `[0, duration]`.

## P2-P4: the open event-type registry

`event_types.json` in this folder is the registry `bl_compose.py` validates
`type` against. It is **open** — task-82380776 (census of the reference) and
later workers add more entries as they measure more of the channel's motion
grammar — but at any moment it is a **closed, checked-in list**: a `type` not
in the file fails the composer loudly, on purpose (deliverable 2's "fail
loudly on an unknown type"). Add the type to the registry first, then use it.

Seed types (measured in `SKILL.md` §6d), one line each in the registry:

| type | layer | what it is |
|---|---|---|
| `hook_slide` | P2 | the opening avatar slide-down (§6d "hook opening") |
| `avatar_shrink` | P2 | animated shrink into composite mode (§6d table) |
| `hard_cut` | P2 | a cut with 0 in-between frames (exit, or a section-change entry) |
| `spotlight` | P2 | dim-to-grey + bright circle on one value |
| `highlight_sweep` | P2 | left→right yellow bar on a table row / spoken word |
| `zoom` | P2 | continuous pan/push on a plate |
| `fade` | P2 | opacity in/out, not a wipe |
| `caption_chip` | P3 | the small dark chip above the head in composite mode |
| `headline` | P3 | a `kinetic()`-style headline block |
| `data_label` | P3 | a label pinned to a specific evidence value |
| `sfx` | P4 | a one-shot sound effect |
| `music_bed` | P4 | a continuous soundtrack bed |

Each registry entry also carries the `params` keys that type expects and
which earlier-layer `id`s (via `refs`) it is allowed/expected to bind to —
see `event_types.json` itself, not a second copy of the same list here.

### Cross-layer references

An event in P2/P3/P4 that depends on an earlier layer's event carries
`"refs": ["<id>", ...]` — a list of ids, each of which **must exist** in an
earlier-or-same layer already loaded (P2 may ref P1; P3 may ref P1/P2; P4 may
ref P1/P2/P3). A `refs` entry that does not resolve is a **dangling id** and
fails the composer loudly (deliverable 2). An event with no cross-layer
dependency (e.g. a P3 headline with its own independent timing) may have
`"refs": []` or omit the key.

## P1 — the one layer that renders

### Top level

```json
{
  "episode": "bl55",
  "duration": 133.13,
  "audio": { "media": "media/audio-hq-v2.mp3" },
  "bug_date": "23 ก.ย. 69",
  "lipsync_offsets": { "A": 0.00, "B": 58.72, "C": 115.44 },
  "events": [ ... ]
}
```

- `audio.media` — path to the voice track, relative to the media root
  `bl_compose.py --media-root` points at (see below).
- `bug_date` — the brand bug's date (§6a: the day the episode was **made**,
  Thai short form with the Buddhist year), copied verbatim into `.bug .dt2`.
- `lipsync_offsets` — the **output of `bl_tools.py offsets`**, one entry per
  lipsync part letter, `true_s`. A P1 avatar event names a part via
  `params.lipsync_part` instead of writing `media_start` by hand; the
  composer computes `media_start = t0 - lipsync_offsets[part]` itself. This
  is literally "lipsync seating from `bl_tools.py offsets` output" — the
  seating is a formula, not something an author can silently get wrong per
  event once the one true offset per part is in this table.

### Events — one `type`: `"plate"`

P1 events **tile the voice track with no gaps and no overlaps**: sorted by
`t0`, each event's `t1` equals the next event's `t0`; the first event's `t0`
is `0`; the last event's `t1` equals `duration`. That tiling **is** the P1
gate (`bl_check.py p1`, deliverable 3).

```json
{
  "id": "p1-004",
  "t0": 9.46,
  "t1": 11.60,
  "type": "plate",
  "params": {
    "role": "avatar",
    "kind": "video",
    "media": "media/lip_a.mp4",
    "lipsync_part": "A",
    "avatar_mode": "full",
    "darken": false
  }
}
```

`params` fields:

| field | values | meaning |
|---|---|---|
| `role` | `avatar` \| `scene` \| `broll` \| `real_still` \| `real_clip` | what kind of plate this is. `avatar` = a lipsync part playing full-frame. `scene` = a generated `S##` plate. `broll` = a channel-catalogue clip. `real_still` / `real_clip` = rule-5a real footage (image or video). |
| `kind` | `video` \| `image` | how the plate is rendered: `<video class="clip">` or a full-bleed `<div class="clip">` with a `background-image` (stills need no ffmpeg Ken-Burns pass to be placed by P1 — that stays a P2 job if it ever becomes one). |
| `media` | path | relative to the media root, e.g. `media/s15.mp4`. |
| `media_start` | seconds | seek offset into `media`. Required unless `lipsync_part` is set (then it is derived — see above). Ignored for `kind: "image"`. |
| `lipsync_part` | `A`/`B`/`C`/… | only for `role: "avatar"` or an `avatar_mode: "composite"` sub-object. Looked up in the top-level `lipsync_offsets`. |
| `darken` | bool | maps to `.plate-darkened` (§6d: brightness 0.4 + blur). **Legal only on `role: "scene"` or `"broll"`.** Never on `real_still`/`real_clip` — §6d measured those at 227-237 luminance, already legible; darkening a real-footage plate fights rule 5a. |
| `avatar_mode` | `full` \| `composite` \| `none` | see below. |
| `avatar` | object, only when `avatar_mode: "composite"` | `{ "media": "media/matte/lip_a-matte.webm", "lipsync_part": "A" }` (or `"media_start"` directly instead of `lipsync_part`). Rendered as `<video class="avatar-comp">` at the CSS-fixed §6d box — P1 places it, it does not animate it ("static states, no animation yet"). The matte file itself is `bl_tools.py matte`'s job, upstream of P1. |
| `real_source` | string, only on `real_still`/`real_clip` | the exact `"file"` value from `real/REAL_MANIFEST.json` this plate was cut from, e.g. `"real/wikifx-profile-score.png"`. Lets `bl_check.py` cross-reference the manifest without guessing from the filename. |

`avatar_mode` legality (`bl_check.py p1`, "avatar mode is legal for the plate
kind"):

- `"full"` — **only** legal when `role: "avatar"`. The plate *is* the avatar,
  full frame. No `avatar` sub-object.
- `"composite"` — **only** legal when `role` is `scene`, `broll`,
  `real_still` or `real_clip` (§6d: "composite only over a plate" — you
  cannot composite the avatar onto itself). Requires the `avatar` sub-object.
- `"none"` — only legal when `role` is not `avatar` (an avatar event is
  always shown one way or the other). No `avatar` sub-object.
- `role: "avatar"` **requires** `avatar_mode: "full"` — an avatar plate with
  `"none"` or `"composite"` makes no sense and fails the check.

### The evidence-box HARD rule

§6d, HARD: **the avatar must never cover the evidence element on a
real-footage plate.** `bl_check.py p1` enforces this whenever
`avatar_mode: "composite"` and the underlying plate's `role` is
`real_still`/`real_clip`:

1. Resolve the plate's evidence box: look up `params.real_source` in
   `real/REAL_MANIFEST.json` (relative to the media root) and read its
   `evidence_box` field — `[{ "x", "y", "w", "h" }, ...]`, px on the same
   1080x1920 canvas.
2. Compare it against the avatar composite's fixed CSS box (measured §6d:
   bottom-anchored, height 56% of 1920 → top at **y=845**, left edge at
   **x=0**, right edge conservatively at **x=480** (44% — wider than the
   measured x-center of ≈37% on purpose, since a HARD safety check should
   err toward catching a real overlap over missing one). `AVATAR_BOX` in
   `bl_check.py` is that one constant, documented inline.
3. **Fail** if the two boxes intersect, or if `real_source` cannot be
   resolved to a manifest entry, or if the entry has no `evidence_box` at
   all — a plate the check cannot prove safe is treated as unsafe, not
   skipped. (`real/REAL_MANIFEST.json` as `tools/bl_realfootage.py` writes it
   today has no `evidence_box` field yet; until a census task adds it,
   composite-over-real events simply cannot pass this check, and the correct
   fix is either author `evidence_box` by hand off the still, or don't
   composite over that plate.)

## Media root

`bl_compose.py` and `bl_check.py p1` both take `--media-root <dir>`. Every
`media` path in P1 (including `audio.media` and `avatar.media`) is relative
to it, and so is `real/REAL_MANIFEST.json` (`<media-root>/real/REAL_MANIFEST.json`).
This is the episode's working directory in the SKILL.md sense (the place
`media/lip_a.mp4`, `media/s15.mp4`, `real/` etc. actually live) — the EDL
JSON itself never hard-codes an absolute path.

## Worked examples

- `.claude/skills/blackliquidity-cut/edl/example/` — tiny 2-shot made-up
  episode, all four layers, shows an id being referenced across P1→P2→P4.
- `prototypes/bl55-cut/edl/p1_layout.json` — EP55's real, approved cut's P1
  layer, reverse-derived from `prototypes/bl55-cut/index.html` (task-42e3b6af).
