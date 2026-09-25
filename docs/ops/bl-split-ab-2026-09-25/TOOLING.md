# BL split-by-dead-air A/B — tooling (task-1678d38e)

Builds steps 0 and 1 of `PLAN.md`: the fixed kit both arms start from, plus
`tools/bl_split.py`, `tools/bl_merge.py`, and `tools/bl_ab_run.py`'s
`fixture-full`/`spawn-seg`. **This task does not cut EP57 and does not spawn
any editor** — everything below through "Arm 2 — segment briefs" is either a
dry run (`spawn-seg` only ever prints a brief) or the real, already-run
`tools/bl_split.py` plan for EP57. Steps 2-4 in PLAN.md's own "Order of
work" (run Arm 1, run Arm 2, CTO merges, report to the CEO) are separate,
future work.

## Step 0 recap — what changed before either arm can run

- `.claude/skills/blackliquidity-cut/template/index.html`: one `caption(at,
  out, text)` generator, EP55's approved `.cap` band baked in as the only
  caption look, in every mode (§6f). §6d's old per-mode chip rule is marked
  `[SUPERSEDED 2026-09-25]`.
- SKILL.md §6g: a plate's end is the next plate's start (promoted from the
  2026-09-24 field note) — nothing may go empty during a TTS pause.
- `tools/bl_checker.py`: `detect_empty_frames` now samples at 30fps with a
  single-frame mean-dip check (the old 4fps grid missed EP57's 76.37s
  one-frame black flash); a new one-caption-style-per-composition gate.

Both arms' editors must use the template and skill AFTER these fixes — that
is the whole point of the A/B (PLAN.md: "both arms must start from it").

## Commands in order

### Arm 1 — ต่อเนื่อง (one editor, the whole episode)

Arm 1 needs no new tooling from this task — it is one `video_editor` task
cutting EP57 end to end with the normal `blackliquidity-cut` skill, using
the fixed template above and a fixture with the FULL episode media (built
once, shared, so nothing about the source material differs between the two
arms):

```bash
# 1. stage the full-episode fixture (once, shared by Arm 1 and every Arm 2 segment)
python3 tools/bl_ab_run.py fixture-full
#   -> /opt/MoonieXHQ/Work/bl-split-ep57/generator (default --dest)
#   WARNING printed if any lip_[abc]-matte.webm is missing -- true for lip_c
#   on this box today (media/matte/ only has lip_a and lip_b, see below).

# 2. CTO spawns ONE video_editor task, brief = "cut EP57 0-153.0s end to end,
#    following the blackliquidity-cut skill and the fixed template, from the
#    fixture-full staged above" -- this task does not spawn it (out of scope).

# 3. render + verify per the skill's own steps 7-9, deliver final-arm1.mp4.
```

### Arm 2 — ช่วยกัน (N editors, one segment each, CTO merges)

```bash
# 1. same fixture-full as Arm 1 (idempotent, safe to re-run)
python3 tools/bl_ab_run.py fixture-full

# 2. the dead-air split (already run for real -- see segments.json below)
python3 tools/bl_split.py /opt/MoonieXHQ/Work/bl-split-ep57/audio-hq.mp3 \
  --script /opt/MoonieXHQ/Work/bl-split-ep57/SCRIPT.tsv \
  --timings /opt/MoonieXHQ/Work/bl-split-ep57/timings.tsv \
  --blocks docs/ops/bl-split-ab-2026-09-25/ep57-blocks.json \
  -o docs/ops/bl-split-ab-2026-09-25/segments.json

# 3. one brief per segment (dry run only -- prints, never spawns; see
#    "Arm 2 — segment briefs" below for all 5, already generated)
python3 tools/bl_ab_run.py spawn-seg \
  --segments docs/ops/bl-split-ab-2026-09-25/segments.json --seg seg01

# 4. CTO spawns N video_editor tasks with those briefs (out of scope here).
#    Each editor takes the render lock before rendering:
#      flock /tmp/bl-render.lock npx hyperframes@0.8.40 render -o segNN.mp4
#    and copies its output to:
#      /opt/MoonieXHQ/Work/bl-split-ep57/parts/<id>.mp4
#      /opt/MoonieXHQ/Work/bl-split-ep57/compositions/<id>.html

# 5. CTO merges once every part has landed
python3 tools/bl_merge.py docs/ops/bl-split-ab-2026-09-25/segments.json \
  --parts /opt/MoonieXHQ/Work/bl-split-ep57/parts \
  --compositions /opt/MoonieXHQ/Work/bl-split-ep57/compositions \
  --audio /opt/MoonieXHQ/Work/bl-split-ep57/audio-hq.mp3 \
  -o /opt/MoonieXHQ/Work/bl-split-ep57/final-arm2.mp4
# exits non-zero and names every failed gate (frame_count / empty_frames /
# seam_failures / audio_offset / extra_caption_styles) -- refuses to ship
# on any failure, per PLAN.md's merge gates.
```

**Known gap on this box today**: `media/matte/` under
`/opt/MoonieXHQ/Work/bl-split-ep57/` has `lip_a-matte.webm` and
`lip_b-matte.webm` but no `lip_c-matte.webm` — `fixture-full` prints a
WARNING about this. Any segment whose window needs a COMPOSITE (avatar +
evidence) beat inside `lip_c`'s range (roughly t≥120s, i.e. inside seg04/
seg05) needs a fresh `bl_tools.py matte` run on `lip_c.mp4` before that
beat can render; a plain full-frame avatar beat in that range is unaffected.

## EP57 segment plan (already run for real)

`docs/ops/bl-split-ab-2026-09-25/segments.json`, built from the REAL episode
audio (`/opt/MoonieXHQ/Work/bl-split-ep57/audio-hq.mp3`, measured duration
153.0514s — PLAN.md's own worked numbers round this to 153.0s) and the real
`SCRIPT.tsv`/`timings.tsv`, with `ep57-blocks.json` (this dir) as the one
forbidden span (the SUMMARY-4..6 checklist card, 129.38-141.48s):

```
audio: /opt/MoonieXHQ/Work/bl-split-ep57/audio-hq.mp3  total_duration=153.0514s  pauses_detected=55  candidates(>=0.45s)=37
cuts (frame-floored, s): [39.3, 65.83333333333333, 104.53333333333333, 145.9]
N segments = 5
  seg01  t0=  0.000  t1= 39.300  dur=39.300s  frames=1179   tags: HOOK-1, HOOK-2, HOOK-3, HOOK-4, PATTERN-1, PATTERN-2, PATTERN-3, PATTERN-4, CONTEXT-1, CONTEXT-2
  seg02  t0= 39.300  t1= 65.833  dur=26.533s  frames=796    tags: CONTEXT-3, CONTEXT-4, CONTEXT-5, MAIN-1, MAIN-2, MAIN-3
  seg03  t0= 65.833  t1=104.533  dur=38.700s  frames=1161   tags: MAIN-4, MAIN-5, MAIN-6, MAIN-7, MAIN-8, MAIN-9, MAIN-10, MAIN-11, MAIN-12, MAIN-13, CURIOSITY-1, CURIOSITY-2
  seg04  t0=104.533  t1=145.900  dur=41.367s  frames=1241   tags: CURIOSITY-3, CURIOSITY-4, CURIOSITY-5, SUMMARY-1, SUMMARY-2, SUMMARY-3, SUMMARY-4, SUMMARY-5, SUMMARY-6, SUMMARY-7
  seg05  t0=145.900  t1=153.033  dur=7.133s  frames=214    tags: SUMMARY-8, SUMMARY-9
wrote docs/ops/bl-split-ab-2026-09-25/segments.json
```

5 segments — inside PLAN.md's own "EP57 estimate 3-5" for Arm 2's N. No cut
falls inside the forbidden checklist-card span (checked: none of
[39.3, 65.83, 104.53, 145.9] land in [129.38, 141.48]).

## Arm 2 — segment briefs

The exact brief text `tools/bl_ab_run.py spawn-seg` generates for each of
the 5 segments above, reusing the default `--fixture-dir
/opt/MoonieXHQ/Work/bl-split-ep57/generator` (i.e. what `fixture-full`
stages by default). This is the "same editor brief as Arm A [interpreted
here as Arm 1's own brief — see note below] with only the time range and the
segment contract from PLAN.md added" the task asked for.

**Interpretation note**: the task text says "brief = the same editor brief
as Arm A". The only existing "Arm A" brief on disk
(`docs/ops/bl-ab-2026-09-25/arms/A/README.md`) belongs to a DIFFERENT,
already-finished experiment (task-aae4f843, a 30.78s window, beats.json +
`bl_compose.py`) — its fixture, output format and render path don't apply
to this PLAN.md at all (Arm 1 here cuts the real HTML composition directly,
per the normal `blackliquidity-cut` skill, not beats.json). Read literally
as "whatever brief Arm 1 gets, Arm 2's segments get too, minus the full
timeline and plus a window", the brief below is that: the standard
`blackliquidity-cut` pipeline brief, scoped to one segment, with PLAN.md's
segment contract layered on top. If the CTO actually wants Arm 1/Arm 2 to
route through `bl_compose.py`'s beats.json shape instead (mirroring the old
A/B/C mechanically), say so and this brief template is a small edit away.

### seg01

```
You are cutting BLACK LIQUIDITY EP57, segment seg01 (1 of 5
segments) -- seconds 0.0 to 39.3 (1179 frames at 30fps). This is Arm 2
("ช่วยกัน") of the split-editor A/B (docs/ops/bl-split-ab-2026-09-25/PLAN.md, CEO 2026-09-25): N editors
each cut one segment in parallel from the SAME fixed skill + template, and the CTO
concats/merges the parts afterward with `tools/bl_merge.py` -- you never see or touch any
other segment. Follow the `blackliquidity-cut` skill's normal pipeline (SKILL.md) end to
end, scoped to your segment only -- steps 1-9 apply exactly as written (transcribe/measure/
normalise/write the cut/gate/look/render/verify), except step 10 (delivery) is replaced by
the push instructions below, and there is no step 5 lipsync-offset search: this fixture's
`SCRIPT.tsv`/`timings.tsv` already carry every line's true wording and exact timing.

**Source material** (all under `/opt/MoonieXHQ/Work/bl-split-ep57/generator`, already staged on this box):
- `SCRIPT.tsv` / `timings.tsv` -- every script line's tag, Thai text, shot name, Jev verb
  and exact [t0,t1], for the WHOLE episode (read only the rows inside your window, listed
  below for convenience).
- `media/real/*`, `media/third-party/*`, `media/broll/*.mp4` -- every real-footage still,
  third-party credit image and B-roll clip the full episode uses.
- `media/lip_a.mp4`, `lip_b.mp4`, `lip_c.mp4` + `media/matte/*-matte.webm` -- the avatar's
  real lipsync footage and its pre-matted overlay (SKILL.md §6d). If your window needs a
  matte that is missing from this fixture, say so in REPORT.md rather than skipping the
  composite -- do not fall back to full-frame avatar just because the matte isn't there.
- `index.html` -- the FIXED template (task-1678d38e): one `.cap` style everywhere (§6f),
  `caption(at, out, text)` generator, plates-hold-until-next-plate is now the rule (§6g).
  Copy it into your own workdir per SKILL.md step 6 -- do not hand-roll captions.
- `build_cut.py`/`assemble.py` (read-only, ground-truth redacted) -- for the pure coordinate
  math ONLY (`img_placement`/`box_to_canvas`/`pick_lip`/`lip_offset`) if you want it; their
  own `BEATS`/`CHECK_ITEMS` lists are blanked out on purpose -- make your own editorial
  calls, the same as any BL editor would.

**Your window's script lines:**
  - `HOOK-1` [0.18, 2.64]: ใครใช้โบรกนี้อยู่ รีบเข้าเว็บไปเช็กด่วนเลย
  - `HOOK-2` [3.08, 5.54]: ตอนนี้แม่งปิดเว็บ เข้าไม่ได้แล้ว
  - `HOOK-3` [5.54, 7.38]: นี่คือหลักฐานตอนที่กูพยายามเข้าเว็บ
  - `HOOK-4` [7.82, 10.86]: โบรกตัวนี้ชื่อ เอ็กซ์เอ็กซ์แอลมาร์เก็ตส์ มึงดูภาพเอาเอง
  - `PATTERN-1` [11.4, 17.86]: เป็นโบรกฟอเร็กซ์ ที่วิกิเอฟเอ็กซ์บอกว่าเปิดที่อังกฤษตั้งแต่ปีสองพันยี่สิบเอ็ด ให้เทรดทั้งค่าเงิน หุ้น และสินค้า
  - `PATTERN-2` [18.48, 22.42]: กูลองพิมพ์ชื่อเว็บนี้ใส่เบราว์เซอร์ตรงๆ หน้าเว็บขึ้นว่าเข้าไม่ได้
  - `PATTERN-3` [22.8, 27.78]: ลองอีกทาง ใส่ www นำหน้าบ้าง ใส่ https ตรงๆบ้าง
  - `PATTERN-4` [28.26, 30.78]: ผลเหมือนเดิมทุกครั้ง เข้าไม่ได้
  - `CONTEXT-1` [31.3, 35.44]: กูไม่เชื่อว่าแค่เว็บล่มเฉยๆ เลยลองเช็กว่าใครเป็นเจ้าของชื่อเว็บนี้
  - `CONTEXT-2` [36.12, 38.86]: เข้าเว็บเช็กชื่อเว็บฟรีๆ พิมพ์ชื่อเว็บนี้ลงไป

**Segment contract** (PLAN.md §"Segment contract (what makes the joins invisible)") --
this is what makes your part concat cleanly with every other segment:
- Your segment covers EXACTLY [0.0, 39.3) seconds of EP57 -- a plate must be
  on screen every frame in that range. The FIRST plate starts at 0.0. The
  LAST plate holds all the way to 39.3 -- do not let it end early just
  because its own spoken line ends before 39.3; SKILL.md §6g ("a plate's
  end is the next plate's start") applies at your segment's own edges too.
  No fade in or out at either edge -- it has to cut hard into whatever comes
  before/after your segment.
- Same template, same caption style (SKILL.md §6f -- use the template's
  own `caption()` generator, never a hand-rolled style or a mode-based
  chip/rail/strip -- that is the exact bug this fix exists to prevent), same
  encoder settings (1080x1920, 30fps) as every other segment, so every
  segment concats with `ffmpeg -c copy`, no re-encode.
- **Render VIDEO ONLY -- no audio track.** The master narration audio is
  muxed once, across the WHOLE episode, by the CTO's `tools/bl_merge.py` at
  merge time. An audio track baked into your segment would only be discarded
  -- do not spend time syncing/exporting one.
- Before you render (`npm run render` / `npx hyperframes render`), take the
  render lock so your render never overlaps another segment editor's on this
  4-core/7GB box: `flock /tmp/bl-render.lock npm run render`. Hold the SAME lock
  for `npm run check`/`hyperframes snapshot` too if you run them concurrently
  with another segment's render -- the lock, not a schedule, is what keeps
  renders serialized.

**Write** your composition to `prototypes/bl-split-ep57/seg01/index.html` (in your own
worktree) and render `prototypes/bl-split-ep57/seg01/seg01.mp4`.

**Render** (inside your composition's own workdir):
```
flock /tmp/bl-render.lock npx hyperframes@0.8.40 render -o seg01.mp4
```

**Verify by eye**: pull frames at a few representative timestamps inside [0.0,
39.3) and actually look at them -- caption readable and in the one approved style,
no empty/black frames, nothing on screen ends before the NEXT plate in your window starts.
Then run `python3 tools/bl_checker.py --video seg01.mp4 --beats <your beats/description>
--composition index.html` and report its verdict.

**Push** (git add/commit/push on your task branch): your composition's `index.html`, a small
`render-meta.json` (path/size/duration/fps via `ffprobe`) -- **not the mp4 itself, media never
goes in git.** Copy `seg01.mp4` to `/opt/MoonieXHQ/Work/bl-split-ep57/parts/seg01.mp4`
and your composed `index.html` to `/opt/MoonieXHQ/Work/bl-split-ep57/compositions/seg01.html`
(outside your worktree -- `merge_task` deletes it, and `tools/bl_merge.py --parts .../parts
--compositions .../compositions` reads directly from there).

Report in REPORT.md: which lines you called COMP/EVID/FF/KIN and why, whether your window's
first/last plate lands exactly on 0.0/39.3 with no fade, and the checker verdict.

```

### seg02

```
You are cutting BLACK LIQUIDITY EP57, segment seg02 (2 of 5
segments) -- seconds 39.3 to 65.8333 (796 frames at 30fps). This is Arm 2
("ช่วยกัน") of the split-editor A/B (docs/ops/bl-split-ab-2026-09-25/PLAN.md, CEO 2026-09-25): N editors
each cut one segment in parallel from the SAME fixed skill + template, and the CTO
concats/merges the parts afterward with `tools/bl_merge.py` -- you never see or touch any
other segment. Follow the `blackliquidity-cut` skill's normal pipeline (SKILL.md) end to
end, scoped to your segment only -- steps 1-9 apply exactly as written (transcribe/measure/
normalise/write the cut/gate/look/render/verify), except step 10 (delivery) is replaced by
the push instructions below, and there is no step 5 lipsync-offset search: this fixture's
`SCRIPT.tsv`/`timings.tsv` already carry every line's true wording and exact timing.

**Source material** (all under `/opt/MoonieXHQ/Work/bl-split-ep57/generator`, already staged on this box):
- `SCRIPT.tsv` / `timings.tsv` -- every script line's tag, Thai text, shot name, Jev verb
  and exact [t0,t1], for the WHOLE episode (read only the rows inside your window, listed
  below for convenience).
- `media/real/*`, `media/third-party/*`, `media/broll/*.mp4` -- every real-footage still,
  third-party credit image and B-roll clip the full episode uses.
- `media/lip_a.mp4`, `lip_b.mp4`, `lip_c.mp4` + `media/matte/*-matte.webm` -- the avatar's
  real lipsync footage and its pre-matted overlay (SKILL.md §6d). If your window needs a
  matte that is missing from this fixture, say so in REPORT.md rather than skipping the
  composite -- do not fall back to full-frame avatar just because the matte isn't there.
- `index.html` -- the FIXED template (task-1678d38e): one `.cap` style everywhere (§6f),
  `caption(at, out, text)` generator, plates-hold-until-next-plate is now the rule (§6g).
  Copy it into your own workdir per SKILL.md step 6 -- do not hand-roll captions.
- `build_cut.py`/`assemble.py` (read-only, ground-truth redacted) -- for the pure coordinate
  math ONLY (`img_placement`/`box_to_canvas`/`pick_lip`/`lip_offset`) if you want it; their
  own `BEATS`/`CHECK_ITEMS` lists are blanked out on purpose -- make your own editorial
  calls, the same as any BL editor would.

**Your window's script lines:**
  - `CONTEXT-3` [39.66, 43.16]: เจอเลย ไม่มีใครเป็นเจ้าของชื่อเว็บนี้แล้วตอนนี้
  - `CONTEXT-4` [43.9, 47.72]: แต่เจอประวัติว่าเคยมีเจ้าของ ย้อนไปถึงปีสองพันยี่สิบสอง
  - `CONTEXT-5` [48.5, 54.22]: หน้าเดียวกันนี้มีตัวนับให้ดูชัดๆอีกด้วย สี่ครั้งตั้งแต่สองพันยี่สิบสองถึงสองพันยี่สิบหก
  - `MAIN-1` [54.84, 58.3]: กูเลยลองไปดูที่วิกิเอฟเอ็กซ์ เว็บที่เช็กโบรกทั่วโลก
  - `MAIN-2` [58.3, 61.84]: วิกิเอฟเอ็กซ์เขียนไว้เองเหมือนกันว่าเว็บนี้เข้าไม่ได้ตามปกติ
  - `MAIN-3` [62.32, 65.44]: แปลว่าไม่ใช่กูคนเดียวที่เข้าไม่ได้ วิกิเอฟเอ็กซ์ก็เจอเหมือนกัน

**Segment contract** (PLAN.md §"Segment contract (what makes the joins invisible)") --
this is what makes your part concat cleanly with every other segment:
- Your segment covers EXACTLY [39.3, 65.8333) seconds of EP57 -- a plate must be
  on screen every frame in that range. The FIRST plate starts at 39.3. The
  LAST plate holds all the way to 65.8333 -- do not let it end early just
  because its own spoken line ends before 65.8333; SKILL.md §6g ("a plate's
  end is the next plate's start") applies at your segment's own edges too.
  No fade in or out at either edge -- it has to cut hard into whatever comes
  before/after your segment.
- Same template, same caption style (SKILL.md §6f -- use the template's
  own `caption()` generator, never a hand-rolled style or a mode-based
  chip/rail/strip -- that is the exact bug this fix exists to prevent), same
  encoder settings (1080x1920, 30fps) as every other segment, so every
  segment concats with `ffmpeg -c copy`, no re-encode.
- **Render VIDEO ONLY -- no audio track.** The master narration audio is
  muxed once, across the WHOLE episode, by the CTO's `tools/bl_merge.py` at
  merge time. An audio track baked into your segment would only be discarded
  -- do not spend time syncing/exporting one.
- Before you render (`npm run render` / `npx hyperframes render`), take the
  render lock so your render never overlaps another segment editor's on this
  4-core/7GB box: `flock /tmp/bl-render.lock npm run render`. Hold the SAME lock
  for `npm run check`/`hyperframes snapshot` too if you run them concurrently
  with another segment's render -- the lock, not a schedule, is what keeps
  renders serialized.

**Write** your composition to `prototypes/bl-split-ep57/seg02/index.html` (in your own
worktree) and render `prototypes/bl-split-ep57/seg02/seg02.mp4`.

**Render** (inside your composition's own workdir):
```
flock /tmp/bl-render.lock npx hyperframes@0.8.40 render -o seg02.mp4
```

**Verify by eye**: pull frames at a few representative timestamps inside [39.3,
65.8333) and actually look at them -- caption readable and in the one approved style,
no empty/black frames, nothing on screen ends before the NEXT plate in your window starts.
Then run `python3 tools/bl_checker.py --video seg02.mp4 --beats <your beats/description>
--composition index.html` and report its verdict.

**Push** (git add/commit/push on your task branch): your composition's `index.html`, a small
`render-meta.json` (path/size/duration/fps via `ffprobe`) -- **not the mp4 itself, media never
goes in git.** Copy `seg02.mp4` to `/opt/MoonieXHQ/Work/bl-split-ep57/parts/seg02.mp4`
and your composed `index.html` to `/opt/MoonieXHQ/Work/bl-split-ep57/compositions/seg02.html`
(outside your worktree -- `merge_task` deletes it, and `tools/bl_merge.py --parts .../parts
--compositions .../compositions` reads directly from there).

Report in REPORT.md: which lines you called COMP/EVID/FF/KIN and why, whether your window's
first/last plate lands exactly on 39.3/65.8333 with no fade, and the checker verdict.

```

### seg03

```
You are cutting BLACK LIQUIDITY EP57, segment seg03 (3 of 5
segments) -- seconds 65.8333 to 104.5333 (1161 frames at 30fps). This is Arm 2
("ช่วยกัน") of the split-editor A/B (docs/ops/bl-split-ab-2026-09-25/PLAN.md, CEO 2026-09-25): N editors
each cut one segment in parallel from the SAME fixed skill + template, and the CTO
concats/merges the parts afterward with `tools/bl_merge.py` -- you never see or touch any
other segment. Follow the `blackliquidity-cut` skill's normal pipeline (SKILL.md) end to
end, scoped to your segment only -- steps 1-9 apply exactly as written (transcribe/measure/
normalise/write the cut/gate/look/render/verify), except step 10 (delivery) is replaced by
the push instructions below, and there is no step 5 lipsync-offset search: this fixture's
`SCRIPT.tsv`/`timings.tsv` already carry every line's true wording and exact timing.

**Source material** (all under `/opt/MoonieXHQ/Work/bl-split-ep57/generator`, already staged on this box):
- `SCRIPT.tsv` / `timings.tsv` -- every script line's tag, Thai text, shot name, Jev verb
  and exact [t0,t1], for the WHOLE episode (read only the rows inside your window, listed
  below for convenience).
- `media/real/*`, `media/third-party/*`, `media/broll/*.mp4` -- every real-footage still,
  third-party credit image and B-roll clip the full episode uses.
- `media/lip_a.mp4`, `lip_b.mp4`, `lip_c.mp4` + `media/matte/*-matte.webm` -- the avatar's
  real lipsync footage and its pre-matted overlay (SKILL.md §6d). If your window needs a
  matte that is missing from this fixture, say so in REPORT.md rather than skipping the
  composite -- do not fall back to full-frame avatar just because the matte isn't there.
- `index.html` -- the FIXED template (task-1678d38e): one `.cap` style everywhere (§6f),
  `caption(at, out, text)` generator, plates-hold-until-next-plate is now the rule (§6g).
  Copy it into your own workdir per SKILL.md step 6 -- do not hand-roll captions.
- `build_cut.py`/`assemble.py` (read-only, ground-truth redacted) -- for the pure coordinate
  math ONLY (`img_placement`/`box_to_canvas`/`pick_lip`/`lip_offset`) if you want it; their
  own `BEATS`/`CHECK_ITEMS` lists are blanked out on purpose -- make your own editorial
  calls, the same as any BL editor would.

**Your window's script lines:**
  - `MAIN-4` [66.12, 68.32]: เช็กต่อว่ามีใบอนุญาตซื้อขายฟอเร็กซ์ไหม
  - `MAIN-5` [69.04, 70.88]: ไม่พบใบอนุญาตซื้อขายฟอเร็กซ์เลย
  - `MAIN-6` [71.44, 73.08]: เช็กเรื่องหน่วยงานกำกับดูแลต่อ
  - `MAIN-7` [73.32, 76.06]: เจอคำเตือนว่ายังไม่มีการกำกับดูแลที่ถูกต้องจริงๆ
  - `MAIN-8` [76.36, 79.92]: คะแนนความน่าเชื่อถือที่วิกิเอฟเอ็กซ์ให้ อยู่ที่หนึ่งจุดเก้าเก้าจากสิบ
  - `MAIN-9` [80.26, 83.08]: จดทะเบียนที่สหราชอาณาจักร เปิดมาแค่สองถึงห้าปี
  - `MAIN-10` [83.4, 86.58]: แล้วเจอคำเตือนอีกอัน ใบอนุญาตกำลังถูกตั้งข้อสงสัย
  - `MAIN-11` [86.84, 88.86]: กลุ่มธุรกิจก็ถูกจัดว่าน่าสงสัยเหมือนกัน
  - `MAIN-12` [89.32, 93.24]: กูลองเช็กหน่วยงานการเงินของอังกฤษเองด้วย แต่หน้าเว็บโหลดผลไม่ขึ้นเลย
  - `MAIN-13` [93.64, 97.2]: กูไม่ได้บอกว่าเจ้านี้โกงแน่นอน กูแค่พาไปดูของจริงที่เช็กเจอ
  - `CURIOSITY-1` [97.64, 100.16]: นี่คือการ์ดที่วิกิเอฟเอ็กซ์เขาสรุปเรื่องนี้ไว้เองเลย
  - `CURIOSITY-2` [100.6, 104.28]: คะแนนย่อยแทบทุกด้านก็แย่เหมือนกัน ทั้งกำกับดูแลและความเสี่ยง

**Segment contract** (PLAN.md §"Segment contract (what makes the joins invisible)") --
this is what makes your part concat cleanly with every other segment:
- Your segment covers EXACTLY [65.8333, 104.5333) seconds of EP57 -- a plate must be
  on screen every frame in that range. The FIRST plate starts at 65.8333. The
  LAST plate holds all the way to 104.5333 -- do not let it end early just
  because its own spoken line ends before 104.5333; SKILL.md §6g ("a plate's
  end is the next plate's start") applies at your segment's own edges too.
  No fade in or out at either edge -- it has to cut hard into whatever comes
  before/after your segment.
- Same template, same caption style (SKILL.md §6f -- use the template's
  own `caption()` generator, never a hand-rolled style or a mode-based
  chip/rail/strip -- that is the exact bug this fix exists to prevent), same
  encoder settings (1080x1920, 30fps) as every other segment, so every
  segment concats with `ffmpeg -c copy`, no re-encode.
- **Render VIDEO ONLY -- no audio track.** The master narration audio is
  muxed once, across the WHOLE episode, by the CTO's `tools/bl_merge.py` at
  merge time. An audio track baked into your segment would only be discarded
  -- do not spend time syncing/exporting one.
- Before you render (`npm run render` / `npx hyperframes render`), take the
  render lock so your render never overlaps another segment editor's on this
  4-core/7GB box: `flock /tmp/bl-render.lock npm run render`. Hold the SAME lock
  for `npm run check`/`hyperframes snapshot` too if you run them concurrently
  with another segment's render -- the lock, not a schedule, is what keeps
  renders serialized.

**Write** your composition to `prototypes/bl-split-ep57/seg03/index.html` (in your own
worktree) and render `prototypes/bl-split-ep57/seg03/seg03.mp4`.

**Render** (inside your composition's own workdir):
```
flock /tmp/bl-render.lock npx hyperframes@0.8.40 render -o seg03.mp4
```

**Verify by eye**: pull frames at a few representative timestamps inside [65.8333,
104.5333) and actually look at them -- caption readable and in the one approved style,
no empty/black frames, nothing on screen ends before the NEXT plate in your window starts.
Then run `python3 tools/bl_checker.py --video seg03.mp4 --beats <your beats/description>
--composition index.html` and report its verdict.

**Push** (git add/commit/push on your task branch): your composition's `index.html`, a small
`render-meta.json` (path/size/duration/fps via `ffprobe`) -- **not the mp4 itself, media never
goes in git.** Copy `seg03.mp4` to `/opt/MoonieXHQ/Work/bl-split-ep57/parts/seg03.mp4`
and your composed `index.html` to `/opt/MoonieXHQ/Work/bl-split-ep57/compositions/seg03.html`
(outside your worktree -- `merge_task` deletes it, and `tools/bl_merge.py --parts .../parts
--compositions .../compositions` reads directly from there).

Report in REPORT.md: which lines you called COMP/EVID/FF/KIN and why, whether your window's
first/last plate lands exactly on 65.8333/104.5333 with no fade, and the checker verdict.

```

### seg04

```
You are cutting BLACK LIQUIDITY EP57, segment seg04 (4 of 5
segments) -- seconds 104.5333 to 145.9 (1241 frames at 30fps). This is Arm 2
("ช่วยกัน") of the split-editor A/B (docs/ops/bl-split-ab-2026-09-25/PLAN.md, CEO 2026-09-25): N editors
each cut one segment in parallel from the SAME fixed skill + template, and the CTO
concats/merges the parts afterward with `tools/bl_merge.py` -- you never see or touch any
other segment. Follow the `blackliquidity-cut` skill's normal pipeline (SKILL.md) end to
end, scoped to your segment only -- steps 1-9 apply exactly as written (transcribe/measure/
normalise/write the cut/gate/look/render/verify), except step 10 (delivery) is replaced by
the push instructions below, and there is no step 5 lipsync-offset search: this fixture's
`SCRIPT.tsv`/`timings.tsv` already carry every line's true wording and exact timing.

**Source material** (all under `/opt/MoonieXHQ/Work/bl-split-ep57/generator`, already staged on this box):
- `SCRIPT.tsv` / `timings.tsv` -- every script line's tag, Thai text, shot name, Jev verb
  and exact [t0,t1], for the WHOLE episode (read only the rows inside your window, listed
  below for convenience).
- `media/real/*`, `media/third-party/*`, `media/broll/*.mp4` -- every real-footage still,
  third-party credit image and B-roll clip the full episode uses.
- `media/lip_a.mp4`, `lip_b.mp4`, `lip_c.mp4` + `media/matte/*-matte.webm` -- the avatar's
  real lipsync footage and its pre-matted overlay (SKILL.md §6d). If your window needs a
  matte that is missing from this fixture, say so in REPORT.md rather than skipping the
  composite -- do not fall back to full-frame avatar just because the matte isn't there.
- `index.html` -- the FIXED template (task-1678d38e): one `.cap` style everywhere (§6f),
  `caption(at, out, text)` generator, plates-hold-until-next-plate is now the rule (§6g).
  Copy it into your own workdir per SKILL.md step 6 -- do not hand-roll captions.
- `build_cut.py`/`assemble.py` (read-only, ground-truth redacted) -- for the pure coordinate
  math ONLY (`img_placement`/`box_to_canvas`/`pick_lip`/`lip_offset`) if you want it; their
  own `BEATS`/`CHECK_ITEMS` lists are blanked out on purpose -- make your own editorial
  calls, the same as any BL editor would.

**Your window's script lines:**
  - `CURIOSITY-3` [104.74, 108.24]: วิกิเอฟเอ็กซ์เขียนไว้ด้วยว่าหน่วยงานการเงินของอังกฤษไม่พบข้อมูลเจ้านี้เหมือนกัน
  - `CURIOSITY-4` [108.24, 114.22]: อันนี้ไม่ใช่กูพูดเอง วิกิเอฟเอ็กซ์เขียนไว้ มึงไปอ่านเองได้
  - `CURIOSITY-5` [114.22, 117.74]: โบรกที่ยังไหวอยู่จริง จะไม่ปล่อยให้เว็บหายไปเงียบๆแบบนี้
  - `SUMMARY-1` [118.2, 119.32]: สรุปแบบไม่โลกสวย
  - `SUMMARY-2` [119.76, 125.02]: เว็บหาย ไม่มีใบอนุญาต ไม่มีหน่วยงานคุ้มครอง สามอย่างนี้ไม่ใช่เรื่องบังเอิญ
  - `SUMMARY-3` [125.4, 128.96]: ก่อนฝากเงินโบรกไหนก็ตาม เช็กสามอย่างแบบที่กูทำให้ดูวันนี้
  - `SUMMARY-4` [129.38, 132.88]: หนึ่ง เข้าเว็บโบรกตรงๆตอนนี้เลย ยังเปิดอยู่จริงไหม
  - `SUMMARY-5` [133.52, 137.26]: สอง เช็กชื่อเว็บที่เว็บตรวจสอบฟรีๆ ยังมีเจ้าของอยู่ไหม
  - `SUMMARY-6` [137.86, 141.02]: สาม เข้าวิกิเอฟเอ็กซ์ เช็กว่ามีใบอนุญาตจริงไหม
  - `SUMMARY-7` [141.48, 145.64]: กูไม่ได้แนะนำให้ใช้หรือเลิกใช้เจ้าไหน กูแค่ชี้วิธีเช็กให้เป็น

**Segment contract** (PLAN.md §"Segment contract (what makes the joins invisible)") --
this is what makes your part concat cleanly with every other segment:
- Your segment covers EXACTLY [104.5333, 145.9) seconds of EP57 -- a plate must be
  on screen every frame in that range. The FIRST plate starts at 104.5333. The
  LAST plate holds all the way to 145.9 -- do not let it end early just
  because its own spoken line ends before 145.9; SKILL.md §6g ("a plate's
  end is the next plate's start") applies at your segment's own edges too.
  No fade in or out at either edge -- it has to cut hard into whatever comes
  before/after your segment.
- Same template, same caption style (SKILL.md §6f -- use the template's
  own `caption()` generator, never a hand-rolled style or a mode-based
  chip/rail/strip -- that is the exact bug this fix exists to prevent), same
  encoder settings (1080x1920, 30fps) as every other segment, so every
  segment concats with `ffmpeg -c copy`, no re-encode.
- **Render VIDEO ONLY -- no audio track.** The master narration audio is
  muxed once, across the WHOLE episode, by the CTO's `tools/bl_merge.py` at
  merge time. An audio track baked into your segment would only be discarded
  -- do not spend time syncing/exporting one.
- Before you render (`npm run render` / `npx hyperframes render`), take the
  render lock so your render never overlaps another segment editor's on this
  4-core/7GB box: `flock /tmp/bl-render.lock npm run render`. Hold the SAME lock
  for `npm run check`/`hyperframes snapshot` too if you run them concurrently
  with another segment's render -- the lock, not a schedule, is what keeps
  renders serialized.

**Write** your composition to `prototypes/bl-split-ep57/seg04/index.html` (in your own
worktree) and render `prototypes/bl-split-ep57/seg04/seg04.mp4`.

**Render** (inside your composition's own workdir):
```
flock /tmp/bl-render.lock npx hyperframes@0.8.40 render -o seg04.mp4
```

**Verify by eye**: pull frames at a few representative timestamps inside [104.5333,
145.9) and actually look at them -- caption readable and in the one approved style,
no empty/black frames, nothing on screen ends before the NEXT plate in your window starts.
Then run `python3 tools/bl_checker.py --video seg04.mp4 --beats <your beats/description>
--composition index.html` and report its verdict.

**Push** (git add/commit/push on your task branch): your composition's `index.html`, a small
`render-meta.json` (path/size/duration/fps via `ffprobe`) -- **not the mp4 itself, media never
goes in git.** Copy `seg04.mp4` to `/opt/MoonieXHQ/Work/bl-split-ep57/parts/seg04.mp4`
and your composed `index.html` to `/opt/MoonieXHQ/Work/bl-split-ep57/compositions/seg04.html`
(outside your worktree -- `merge_task` deletes it, and `tools/bl_merge.py --parts .../parts
--compositions .../compositions` reads directly from there).

Report in REPORT.md: which lines you called COMP/EVID/FF/KIN and why, whether your window's
first/last plate lands exactly on 104.5333/145.9 with no fade, and the checker verdict.

```

### seg05

```
You are cutting BLACK LIQUIDITY EP57, segment seg05 (5 of 5
segments) -- seconds 145.9 to 153.0333 (214 frames at 30fps). This is Arm 2
("ช่วยกัน") of the split-editor A/B (docs/ops/bl-split-ab-2026-09-25/PLAN.md, CEO 2026-09-25): N editors
each cut one segment in parallel from the SAME fixed skill + template, and the CTO
concats/merges the parts afterward with `tools/bl_merge.py` -- you never see or touch any
other segment. Follow the `blackliquidity-cut` skill's normal pipeline (SKILL.md) end to
end, scoped to your segment only -- steps 1-9 apply exactly as written (transcribe/measure/
normalise/write the cut/gate/look/render/verify), except step 10 (delivery) is replaced by
the push instructions below, and there is no step 5 lipsync-offset search: this fixture's
`SCRIPT.tsv`/`timings.tsv` already carry every line's true wording and exact timing.

**Source material** (all under `/opt/MoonieXHQ/Work/bl-split-ep57/generator`, already staged on this box):
- `SCRIPT.tsv` / `timings.tsv` -- every script line's tag, Thai text, shot name, Jev verb
  and exact [t0,t1], for the WHOLE episode (read only the rows inside your window, listed
  below for convenience).
- `media/real/*`, `media/third-party/*`, `media/broll/*.mp4` -- every real-footage still,
  third-party credit image and B-roll clip the full episode uses.
- `media/lip_a.mp4`, `lip_b.mp4`, `lip_c.mp4` + `media/matte/*-matte.webm` -- the avatar's
  real lipsync footage and its pre-matted overlay (SKILL.md §6d). If your window needs a
  matte that is missing from this fixture, say so in REPORT.md rather than skipping the
  composite -- do not fall back to full-frame avatar just because the matte isn't there.
- `index.html` -- the FIXED template (task-1678d38e): one `.cap` style everywhere (§6f),
  `caption(at, out, text)` generator, plates-hold-until-next-plate is now the rule (§6g).
  Copy it into your own workdir per SKILL.md step 6 -- do not hand-roll captions.
- `build_cut.py`/`assemble.py` (read-only, ground-truth redacted) -- for the pure coordinate
  math ONLY (`img_placement`/`box_to_canvas`/`pick_lip`/`lip_offset`) if you want it; their
  own `BEATS`/`CHECK_ITEMS` lists are blanked out on purpose -- make your own editorial
  calls, the same as any BL editor would.

**Your window's script lines:**
  - `SUMMARY-8` [146.08, 150.5]: คอมเมนต์คำว่า เช็กเว็บโบรก ถ้ามึงอยากได้ขั้นตอนเช็กเว็บและใบอนุญาตเอง
  - `SUMMARY-9` [150.8, 152.64]: อย่าปล่อยให้เว็บหายไปพร้อมเงินมึง

**Segment contract** (PLAN.md §"Segment contract (what makes the joins invisible)") --
this is what makes your part concat cleanly with every other segment:
- Your segment covers EXACTLY [145.9, 153.0333) seconds of EP57 -- a plate must be
  on screen every frame in that range. The FIRST plate starts at 145.9. The
  LAST plate holds all the way to 153.0333 -- do not let it end early just
  because its own spoken line ends before 153.0333; SKILL.md §6g ("a plate's
  end is the next plate's start") applies at your segment's own edges too.
  No fade in or out at either edge -- it has to cut hard into whatever comes
  before/after your segment.
- Same template, same caption style (SKILL.md §6f -- use the template's
  own `caption()` generator, never a hand-rolled style or a mode-based
  chip/rail/strip -- that is the exact bug this fix exists to prevent), same
  encoder settings (1080x1920, 30fps) as every other segment, so every
  segment concats with `ffmpeg -c copy`, no re-encode.
- **Render VIDEO ONLY -- no audio track.** The master narration audio is
  muxed once, across the WHOLE episode, by the CTO's `tools/bl_merge.py` at
  merge time. An audio track baked into your segment would only be discarded
  -- do not spend time syncing/exporting one.
- Before you render (`npm run render` / `npx hyperframes render`), take the
  render lock so your render never overlaps another segment editor's on this
  4-core/7GB box: `flock /tmp/bl-render.lock npm run render`. Hold the SAME lock
  for `npm run check`/`hyperframes snapshot` too if you run them concurrently
  with another segment's render -- the lock, not a schedule, is what keeps
  renders serialized.

**Write** your composition to `prototypes/bl-split-ep57/seg05/index.html` (in your own
worktree) and render `prototypes/bl-split-ep57/seg05/seg05.mp4`.

**Render** (inside your composition's own workdir):
```
flock /tmp/bl-render.lock npx hyperframes@0.8.40 render -o seg05.mp4
```

**Verify by eye**: pull frames at a few representative timestamps inside [145.9,
153.0333) and actually look at them -- caption readable and in the one approved style,
no empty/black frames, nothing on screen ends before the NEXT plate in your window starts.
Then run `python3 tools/bl_checker.py --video seg05.mp4 --beats <your beats/description>
--composition index.html` and report its verdict.

**Push** (git add/commit/push on your task branch): your composition's `index.html`, a small
`render-meta.json` (path/size/duration/fps via `ffprobe`) -- **not the mp4 itself, media never
goes in git.** Copy `seg05.mp4` to `/opt/MoonieXHQ/Work/bl-split-ep57/parts/seg05.mp4`
and your composed `index.html` to `/opt/MoonieXHQ/Work/bl-split-ep57/compositions/seg05.html`
(outside your worktree -- `merge_task` deletes it, and `tools/bl_merge.py --parts .../parts
--compositions .../compositions` reads directly from there).

Report in REPORT.md: which lines you called COMP/EVID/FF/KIN and why, whether your window's
first/last plate lands exactly on 145.9/153.0333 with no fade, and the checker verdict.

```

