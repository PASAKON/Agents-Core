# task-c32c40e8 — brand-mark blink, mark gate, KIN-entry grace, caption balance

Branch `agent/developer-task-c32c40e8`, base `origin/main` (ecbab7cf). Developer, Sonnet 5.5 (model override to Claude
because the change touches the shipping gates `bl_checker` / `bl_merge` and the composed HTML of every BL cut).
No render, no Contabo, no paid call, `prototypes/bl-ep58/` untouched, no SKILL.md edited.

## What changed, per item

### Item 1 — brand mark on from frame 0 (blocking)

Cause: template `index.html` carried `tl.from("#bug", { x: -50, opacity: 0, duration: 0.7, ease: "power3.out" }, 0.25);`.
A range render replays the whole timeline at its own local t=0, so every window (t=0 and each of the 11 seams) began
with the mark absent for 8 frames and faded in. `.bug` has no `opacity: 0` in its CSS, so with no tween at all the mark
sits at its end state from frame 0.

- `tools/bl_compose.py` writes the composed HTML with `tl.set("#bug", { x: 0, opacity: 1 }, 0);` in place of the
  entrance, in both arms (arm A moves the mark to the top-left through its own CSS override; the end state is
  position-neutral because it sets `x: 0`).
- It anchors on exact template text, the way `apply_arm_a` does, and refuses when the anchor count is not expected
  (`check_template_anchors`: exactly one `</head>`, and exactly one of {old entrance line, new end-state line}).
  It does not rely on the staged generator's template copy being current: an old copy (entrance present) and a new copy
  (end-state line present) compose to the same functional HTML (diff below).
- **Conflict with the unmodified `assemble.py`, and how it was handled.** `assemble.py` (origin/agent/video_editor-task-501f1d89,
  not editable) splices the cut's `script_lines` and `caps_js` by replacing the exact `tl.from("#bug"…)` text. If that
  text is absent it replaces nothing, and every caption, kinetic block, evidence plate and clip call of the cut is
  silently dropped; the render still succeeds and the video is a bare template. So a template that simply loses the
  entrance line, which is what the brief asked for, breaks every cut. Handling:
  - compose swaps the end-state line back to the entrance line in memory before it runs `assemble.py`
    (`expose_assemble_anchor`), then replaces the entrance line with the end-state line afterwards (`pin_bug_end_state`);
  - `check_pieces_landed` compares the composed HTML against the cut's pieces after assemble and raises
    (`assemble.py spliced N of the cut's M pieces into nothing …`) if any did not land, so this class of silent drop is
    now loud whatever the cause;
  - the skill template's new end-state line carries a comment saying compose finds it to splice the cut in, so a later
    edit does not remove it unknowingly.
  No `dev_message` was sent for this: the brief's constraints (template edit asked for, assemble.py off-limits) are
  both met and the handling needs no CTO decision. Worth the CTO knowing if `assemble.py` is ever regenerated.
- Template: the entrance line is replaced by a comment plus the `tl.set` line.
- **Other always-on elements (the "check and report" part).** `.bl-legal` (the legal pill) and `#hl` (the arm-A headline
  plate) are static: no `tl.from`, no `tl.fromTo`, no entrance, so nothing replays at a seam. `#bug` was the only one.
  The date chip is inside `#bug`, so it is covered by the same fix. Item 3's grace relies on this: during a KIN entry
  the legal pill is on screen.

### Item 2 — acceptance gate on the mark (`tools/bl_checker.py`, section 8)

Part of `run_checker` / `--video`, arm-aware: right side for arm B, left for arm A (`headline["bug_side"]`).

- Measures, per frame, the redness `R − (G+B)/2` of the logo's neon rule (`#FF2D40`, ≈ 200.5) in a rectangle derived
  from the same geometry constants the bug mask uses: arm B rule (856, 380, 74, 5) from `.bug{right:150px;top:310px}`,
  column gap 10, logo 163.59 × 60; arm A rule (297.59, 198, 5, 44) from `BUG_LEFT_ORIGIN` (120, 190), gap 14. The sample
  rect is inset by 1 px so antialiased edges are never read (arm B: x857 y381 72×3, close to the CMO's x860-930 y380-385).
- Ratio = level / steady level; the steady level is the 90th percentile of the per-frame levels (a median would be
  dragged down by a long fade). A frame under 0.95 (`MARK_MIN_OPACITY`) fails. If the steady level is itself under 0.6 of
  the neon the verdict is `mark_missing`; no frames decoded is `no_frames`.
- Verdict keys: `ok, side, min_opacity, steady_level, frames, min_ratio, min_time, failing_frames, failing_times,
  failing_ranges` (+ `error`).
- The gate runs inside `run_checker`, not inside `bl_merge`; run `bl_checker --video` on the merged final.

Results on synthetic clips (1080×1920, 30 fps, 30 frames, dark plate, rule drawn in RGB, encoded libx264 yuv420p crf 18):

| clip | side | verdict | min ratio (at) | failing frames |
|---|---|---|---|---|
| steady mark | right | ok | 0.991 (0.133 s) | 0 |
| steady mark | left | ok | 0.996 (0.000 s) | 0 |
| absent 8 frames, ramp to .8 over 8, then full | right | FAIL | 0.000 (0.000 s) | 16 = [0.0 – 0.5 s] |
| same | left | FAIL | −0.006 (0.167 s) | 16 = [0.0 – 0.5 s] |

(−0.006 is encode noise around zero; the ratio is not clamped.)

Calibration on the real template's mark: the real `#bug` + `.bl-legal`, drawn by the render's own headless Chromium
(152) at a scripted per-frame alpha and encoded like the kit's renders. The blink shape is modelled on the CMO's
measurement (absent 8 frames, ramp over 9, at t=0 and at 1.5 s); the pixels are the template's own:

| clip | right / left verdict | min ratio | failing frames |
|---|---|---|---|
| steady | ok / ok | 0.998 / 1.000 (noisy 0.986 / 0.971) | 0 |
| 97 % dip for 10 frames | ok / ok | 0.987 / 0.990 (noisy 0.978 / 0.974) | 0 |
| 90 % dip for 10 frames | FAIL / FAIL | 0.933 / 0.942 (noisy 0.926 / 0.904) | 10 / 9 |
| blink | FAIL / FAIL | 0.073 / 0.117 (noisy 0.060 / 0.100) | 34 = [0.0–0.533 s] + [1.5–2.033 s] |

Limits, measured: a thin 4:2:0 rule reads about 3–4 points high near the top of a fade; the gate is lenient over a
red-ish backdrop (a mark over a red plate reads above its true level) and tracks opacity over a dark plate. A real
Chromium alpha of .9 reads .93–.94. A chroma-plane metric gave the same decisions as RGB redness on every real clip, so
RGB stays.

**No EP58 mp4 on the Mac** (`/opt/MoonieXHQ/Work/bl-ep58/cut/final-ep58.mp4` is on Contabo; `prototypes/bl-ep58/` holds
beats and decisions only), and the brief forbids fetching media over ssh. So the per-frame minimum and failing
timestamps of the real EP58 file are not reported here. Expected, from the CMO's measurement and the clips above:
failing ranges at 0.0 s and at each of the 11 seams, about 17 frames each. To get the real numbers, run on Contabo:
`bl_checker --video /opt/MoonieXHQ/Work/bl-ep58/cut/final-ep58.mp4 --beats prototypes/bl-ep58/beats.json`
(read `brand_mark.failing_ranges`).

### Item 3 — KIN-entry grace

- `bl_checker.excuse_kin_entry(video, empty_times, beats, bug_side, fps, levels=None)` returns `(still_empty, excused)`.
  An empty frame is excused only if it is one of the first `KIN_ENTRY_GRACE_FRAMES = 4` frames from a KIN beat's t0
  (frames `round(t0·fps) … +3`) **and** on that frame the mark ratio is ≥ 0.95 **and** the legal pill is present
  (`LEGAL_PILL_RECT` (120, 1430, 720, 81), sample rect inset by the pill padding (24, 8): (144, 1438, 672, 65); present
  when the sample's standard deviation ≥ `LEGAL_MIN_STD = 15`; real text measured about 40, flat plate 0–2).
- Frame 5 or later of a KIN entry, an empty frame at any other beat, or an entry frame with the mark or pill missing,
  still fails.
- `run_checker` applies it always (it has the beats); the result gains `empty_frames_excused`. `bl_merge` applies it in
  the seam gate only when `--beats` is given (and `gates["empty_frames_excused"]` appears only then); without `--beats`
  today's behaviour is unchanged. The generator is not touched.
- **Label correction.** The brief names SUMMARY-1 for the EP58 flag at 71.567–71.667. In `prototypes/bl-ep58/beats.json`
  71.567 s is the t0 of **CURIOSITY-5** (KIN, t0 71.57); SUMMARY-1 starts at 74.42. The other flag, 29.667–29.733 s, is
  MAIN-1 (KIN, t0 29.66). Both are KIN entries, so the grace rule covers both.
- The 7 flagged EP58 frames are 29.667, 29.700, 29.733 and 71.567, 71.600, 71.633, 71.667: 3 and 4 frames, both within
  the 4-frame grace.

### Item 4 — caption orphans

`text-wrap: balance` is added to the caption band through two routes: the skill template's `.cap` rule (the CMO-owned
style lives there) and `bl_compose`'s render-workdir override (`<style id="bl-caption-balance">.cap{text-wrap:balance}</style>`
before `</head>`), so a staged generator with the older template also gets it.

Thai line breaking does not make `balance` a no-op in the render's Chromium (152.0.7977.30, `CSS.supports` true, Thai
dictionary breaks at word boundaries; no word segmenter was written). Measured on all 31 EP58 captions with the old
template (`.cap` width 720): 26 are one line and unchanged; all 5 multi-line captions ended in a short orphan, and
balance changes all 5:

| before | after balance |
|---|---|
| `อีกคนรอสามสัปดาห์ ว่ากำลัง` / `ตรวจ` | `อีกคนรอสาม` / `สัปดาห์ ว่ากำลังตรวจ` |
| `มีผู้อ้างถอนสองหมื่นกว่าดอลลาร์` / `ไม่ได้` | `มีผู้อ้างถอนสองหมื่น` / `กว่าดอลลาร์ไม่ได้` |
| `ปีสองพันยี่สิบสาม ไม่เจอ` / `สำนักงาน` | `ปีสองพันยี่สิบสาม` / `ไม่เจอสำนักงาน` |
| `หัวข้อบทความ ใบเบลีซถูกเพิก` / `ถอน` | `หัวข้อบทความ ใบ` / `เบลีซถูกเพิกถอน` |
| `คอมเมนต์ เช็กลิสต์ ถ้าอยากได้` / `ตาราง` | `คอมเมนต์ เช็กลิสต์` / `ถ้าอยากได้ตาราง` |

For the CMO's eye: in the fourth row balance leaves `ใบ` at the end of line one, separated from its noun. The break is
on a Thai word boundary, so it reads correctly, but it is the one line a human might still prefer to break differently.

### Item 5 — `text_over_face` passes while the pill covers the chin (investigated, not changed)

- The checker's face box is **not a constant and not wrong for lip_a: there is none.** `run_checker` takes
  `face_box=None` by default, and `check_text_over_face` returns `[]` immediately when it is `None`
  (`tools/bl_checker.py:292-293`). EP58's checker run passed no `--face-box`, so the check did not run and reported an
  empty list, which reads like a pass. Nothing in the skill tells the operator to pass one (SKILL.md and the EP58
  report have no `--face-box`), and nothing derives one: `bl_tools.py safearea` prints a chin y for a clip, never a box,
  and nothing feeds it to the checker.
- What the check would test if it ran: `caption_band("FF"|"COMP")` = 0.62 × 1920 … 0.72 × 1920 = y 1190.4 … 1382.4,
  an approximation set in task-1678d38e (2026-09-25) from EP55's `.caplayer { top: 1300px }` and a one/two-line `.cap`
  (48 px, line-height 1.28, padding 20 px: one line is 1250–1350 in the render, two lines about 1218–1382). It is a
  band-versus-box overlap, so with a real box it would flag.
- Geometry of the COMP avatar from the template: `.avatar-comp { height: 56%; bottom: 0; left: 0;
  transform: translateX(-6%) }` = 1075 px tall, top at y 845, chest-up, cut off by the frame bottom. The caption pill
  (1250–1350) therefore sits on the avatar's lower face whatever lip_a's exact chin is.
- Not fixed, by the brief's rule: the checker's geometry is not the cause, a missing input is. Options for the CMO / CTO
  (no change made): (a) derive the box per COMP beat from `bl_tools.py safearea` and pass it automatically; (b) make
  `run_checker` return `text_over_face_checked: false` when there is no face box, so absence stops looking like a pass;
  (c) move the band, which is the CMO's call. The numbers for (c): band y 1190–1382, pill 1250–1350, `.caplayer` top
  1300, avatar top 845. I did not move the band.

## Old vs new composed HTML on the real staged generator

Method: `bl_ab_run.build_full_generator` on an EP58-shaped work dir (offsets.json with EP58's 0 / 38.77 / 80.84, date
2026-10-01, stand-in audio and lip media; `build_cut.py` and `assemble.py` fetched from
`origin/agent/video_editor-task-501f1d89` exactly as the kit does), once with the skill template as of base ecbab7cf
("old generator") and once with the template of this branch ("new generator"). `bl_compose` run with
`prototypes/bl-ep58/beats.json`, the full cut (`--t-max 95.7`) and the window 9.067 – 16.6 s, old tool (ecbab7cf) versus
new tool.

Old tool vs new tool, same (old-template) staged generator. The full cut and the window give the same two hunks:

```
322c322,323
<   </head>
---
>   <style id="bl-caption-balance">.cap{text-wrap:balance}</style>
> </head>
628c629
<       tl.from("#bug", { x: -50, opacity: 0, duration: 0.7, ease: "power3.out" }, 0.25);
---
>       tl.set("#bug", { x: 0, opacity: 1 }, 0);
```

(Window: lines 322 and 589→590, same text.) That is the entrance removal and the caption-balance style (item 4) and
nothing else. `cut_pieces.json` is byte-identical between old and new tool, and the pieces-landed guard passes.

New tool, old-template generator vs new-template generator (full cut; the window is identical): the composed HTML
differs only by the template's own two-line comment + `text-wrap: balance` rule inside `.cap` and the four-line comment
above the end-state line. Same functional page, which is the point of the anchor swap.

The two arm-B golden fixtures (`tests/fixtures/bl_arm_b/full|range/index.html`) were regenerated; their diff against
the old golden is the same two hunks.

## Tests (worktree, `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_bl_*.py`)

- Total: 442 passed, 1 skipped (pre-existing skip), 0 failed.
- Per file: checker 136 passed / 1 skipped, compose 123, merge 25, ab_run 23, split 27, scripter 33, realfootage 33
  (the remaining `test_bl_*` files make up the total).
- New or changed coverage:
  - geometry of the mark rectangles against the template CSS (both sides);
  - steady mark passes, fade-in at the opening and at a seam fails, per side, with `failing_ranges` and `min_time`;
    threshold boundary (alpha .97 passes, .85 fails); no mark at all; no frames;
  - arm-aware side selection in `run_checker`;
  - KIN grace: frames 1–4 excused, frame 5 not, non-KIN not, frames away from t0 not, mark or pill absent not, arm-A
    side; in merge: without beats unchanged, with beats excused, fifth frame refused, non-KIN refused, `--beats` switches
    it on;
  - compose: end state pinned in every window, old and current template copies compose the same, the template is never
    edited, `text-wrap` style present, anchor refusals, pieces-landed guard, arm A keeps both overrides.
- Synthetic fixtures: `tests/bl_mark_clips.py` (ffmpeg; drawn in RGB because `drawbox` alpha is non-linear in
  yuv420p).
- Not run: any hyperframes render (forbidden); a real GSAP seek (no network for the CDN script). `.bug` has no CSS
  `opacity: 0`, so with no tween it is on at frame 0 either way; the `tl.set` line is the SKILL.md rule for what is
  already on screen.

## Files changed

- `tools/bl_checker.py` — mark gate (section 8), KIN-entry grace (section 9), `run_checker` wiring, docstring.
- `tools/bl_compose.py` — end-state pin, assemble-anchor swap, caption-balance style, pieces-landed guard, anchor checks.
- `tools/bl_merge.py` — KIN grace in the seam gate when `--beats` is given; reads the arm-A headline for the side.
- `.claude/skills/CMO_Procedure_BlackLiquidity_Cut/template/index.html` — entrance line replaced by end state; `.cap`
  `text-wrap: balance`.
- `tests/bl_mark_clips.py` (new), `tests/test_bl_checker.py`, `tests/test_bl_compose.py`, `tests/test_bl_merge.py`,
  `tests/fixtures/bl_arm_b/full/index.html`, `tests/fixtures/bl_arm_b/range/index.html` — tests and regenerated goldens.

## Open points for the reviewer

1. Arm B composed HTML is no longer byte-identical to before; intended per the CMO ruling.
2. Run `bl_checker --video` on the EP58 final on Contabo before anyone calls the gate calibrated on the real file.
   Expected: the mark fails at 0.0 s and at the 11 seams, and the empty-frame list clears.
3. `text_over_face` stays silent without `--face-box`; decision for the CMO / CTO (item 5).
4. The pre-commit skill-lint printed "10 finding(s), 1 refused entry. This is a lint, not a gate"; not investigated,
   not from these files.
5. No `SKILL-OVERRIDE` lines were seen in tools, tests or the skill.

## Skill learning

- WRONG   [CMO_Procedure_BlackLiquidity_Cut §checker gates, 2026-10-01 note "empty_frames flags the 3-4 dark frames before a KIN text wipe-in"] : the note says the gate cannot tell the entrance from a real black frame; it now can (frames 1–4 of a KIN beat with the mark and legal pill present are excused, beats required) · evidence: task-c32c40e8 `tools/bl_checker.py` section 9, `tools/bl_merge.py`, tests · fix: replace the note with the grace rule and say `bl_merge` needs `--beats` for it.
- MISSING [CMO_Procedure_BlackLiquidity_Cut §template / assemble.py] : `assemble.py` splices a cut's script lines and captions only by replacing the exact `tl.from("#bug"…)` text; if the template loses that line the cut is silently dropped and the render still succeeds. Any template edit near that line must keep it, or `bl_compose` must swap it (it now does) · evidence: task-c32c40e8, `tools/bl_compose.py` `expose_assemble_anchor` / `check_pieces_landed`.
- MISSING [CMO_Procedure_BlackLiquidity_Cut §gates] : the brand mark must be on from frame 0 of every window; the check is `bl_checker --video` → `brand_mark` (95 % of steady per frame, arm-aware); `bl_merge` does not run it · evidence: task-c32c40e8.
- MISSING [CMO_Procedure_BlackLiquidity_Cut §checker gates, text_over_face] : the check returns `[]` when `--face-box` is not passed, so a run without it looks like a pass; SKILL.md never tells the operator to pass one or how to get one · evidence: task-c32c40e8 item 5, `tools/bl_checker.py:292-293`, EP58 checker run.
- MISSING [CMO_Procedure_BlackLiquidity_Cut §checker gates, empty frames] : the checker's "legal band" mask is .66–.74 H (y 1267–1421) but the real `.bl-legal` pill sits at y 1430–1511; the legal-pill probe added here uses the real position · evidence: task-c32c40e8 `LEGAL_PILL_RECT`.
- COSTLY  [no owner] : synthetic fade fixtures — ffmpeg `drawbox` alpha in yuv420p is non-linear (alpha .9 left the chroma at 98.7 %), so a "fade" clip was not a fade until it was drawn in `gbrp` and converted at the end; several calibration rounds · evidence: task-c32c40e8 `tests/bl_mark_clips.py` · prevented by: a one-line note in the video tooling notes: draw alpha fixtures in RGB, encode last.
- COSTLY  [no owner] : zsh `$a:t` expands as a modifier inside ffmpeg argument strings in a probe script; use `${a}` · evidence: task-c32c40e8 · prevented by: a line in the shell-traps memory index.
