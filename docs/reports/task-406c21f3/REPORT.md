# task-406c21f3 — BlackLiquidity arm A (headline plate): one beats.json, either look

Branch `agent/developer-task-406c21f3`, three commits on top of 18da8cc1 (task-ee30ba95's per-episode avatar
windows, brought in by cherry-pick because `git merge main` conflicted in two skill files). Nothing pushed. No paid
call, no generation, no Contabo render: code, unit tests, and one local headless-Chromium layout check.

## What was built

`beats.json` is now either

- a bare list of beats — **arm B**, today's look, output byte-identical to before (proof below), or
- an object `{"headline": {...}, "beats": [...]}` — **arm A**.

### Schema as built (one example; the numbers in it were run through the code)

```json
{
  "headline": {
    "lines": ["โบรกเกอร์ไม่อยากให้คุณรู้", "Weltrade เปิดบัญชีง่ายจริงไหม"],
    "red": "ไม่อยากให้คุณรู้",
    "bug_side": "left",
    "backdrop": [
      {"t0": 0.0, "src": "real/a.png"},
      {"t0": 1.0, "src": "real/b.png"},
      {"t0": 2.0, "src": "real/c.png"}
    ]
  },
  "beats": [
    {"tag": "HOOK-1", "t0": 0.0, "t1": 3.4, "mode": "COMP", "extra": {"cap": "..."}},
    {"tag": "EV-1", "t0": 3.4, "t1": 6.0, "mode": "EVID",
     "extra": {"img": "real/x.png", "native_w": 1080, "native_h": 1500, "box": [40, 800, 900, 500],
               "credit": "WikiFX", "cap": "..."}}
  ]
}
```

(The two lines are illustrative; EP58's come from HEADLINE.md.) Those lines are 25 and 29 code points, **19 and 24
visual characters**.

| field | rule |
|---|---|
| `lines` | exactly 2 non-empty strings, no line break; each **≤ 30 characters counted by `bl_checker._visual_len`** — spacing characters only, Unicode category Mn (Thai vowel and tone marks) not counted. `"ก"*30 + "ิ"` (31 code points) passes; `"ก"*31` is refused. |
| `red` | exact substring that occurs **exactly once across both lines** (overlapping matches count). Missing, absent or ambiguous → refused, exit 2, message names the rule. Also refused when it would start or end on a Thai combining mark (a tone mark left outside the red span). |
| `bug_side` | `"left"` (arm A) or `"right"`; default `"right"`. `"right"` with a headline is refused at compose time with the hint to set `"left"` (the plate sits where the right bug does). |
| `backdrop` | exactly three `{"t0", "src"}` at t0 0.0, 1.0, 2.0. `src` must sit under `real/` (there is no credit chip, so only first-party captures), no `..`. Compose refuses a file that is not under `<generator>/media/`. |

**Deviation from the CMO text: `red` is an exact substring, not a "red_word index".** Thai has no spaces, so a word
index is undefined. Written here as ordered.

**Exit codes.** A malformed schema (`ArmAError`) exits **2** from both `bl_compose.py` and `bl_checker.py`. A
well-formed table that arm A cannot render (`ComposeError`: FF, missing backdrop file, opening rule, plate on an
EVID box…) keeps this tool's existing exit **1**. Both print the reason on stderr.

### Layout as built (canvas 1080 × 1920)

| element | where |
|---|---|
| bug (arm A) | `#bug` override: left 120, top 190, one row: logo, 5 px divider, date. Measured in Chromium: x 120–428, y 190–250. Checker zone (100,176,400,86). |
| plate | `#hl`, left 120, top 276 (14.4 %), width 840, two lines, centred, `z-index:38`, no `data-start` → on screen from frame 0 for the whole clip. Height 100–220 px → ends between 19.6 % and 25.8 % of the height (CMO: about 12–26 %). |
| font | Kanit 800, the largest size ≤ 88 px at which the widest line fits 840 px: short lines 88, the mixed Thai/Latin example 59, a Thai sample line of 30 characters with marks 55, 30 spacing consonants 48, 30 capitals 40. |
| red | `<span class="hl-red">` colour `var(--neon)`; text escaped. |

The bug move and the plate are applied to the **render workdir's index.html only**, after the unmodified
`assemble.py` ran. The staged generator and the skill template are never edited (tested: byte-for-byte before/after).
Arm B composes exactly as before, so EP57's staged generator rebuilds identically (`fixture-full` is untouched; its
tests pass).

### Beat rules in arm A

- **FF is refused**, naming the beat, judged on the whole table (a range render that excludes it still refuses).
- COMP (avatar lower, matted), EVID and KIN are allowed.
- **A COMP beat with no `img` rides the backdrop**: one full-bleed `object-fit:cover` plate per backdrop slot that
  falls inside the beat (slot 0 → 1 s, slot 1 → 2 s, slot 2 → the beat's end), the matted avatar over it, `avatar_until`
  honoured, caption as usual. The slots tile the beat with no hole (tested at every 50 ms of [0, 3.4)).
- Everything here is **my reading of an ambiguity** in the CMO text (it does not say how backdrop and beats relate);
  see "Please confirm" below.

## Checker

- `_frame_stats` / `detect_empty_frames` take the arm: arm A masks the left bug zone instead of the top-right one **and
  the plate rectangle** (white text standing on every frame would otherwise lift the frame's std above the "empty"
  threshold and hide a genuinely empty frame — the silent-wrong-answer case). Arm B's call and mask are untouched
  (`arm_mask_kwargs(None) == {}`).
- New `check_headline`: text rect inside `safe_rect()` (`outside_safe_area`), clear of the bug zone
  (`overlaps_bug_<side>`), clear of every COMP/EVID `box` (`overlaps_evidence:<tag>`) and credit chip
  (`overlaps_credit:<tag>`). A beat with no `box` declares no content area, so there is nothing to overlap.
- New `check_headline_plate`: reads the plate's left/top/width/height/font-size and the bug override back out of the
  **composed HTML** and compares them with `headline_layout()` — the verdict is tied to what was composed.
- `check_text_over_face(headline=...)` treats the plate as text: every FF/COMP beat is flagged when the plate's text
  rect meets the face box, caption or not.
- `run_checker(headline=...)` adds a `"headline"` list to the verdict. Without a headline the verdict dict is
  exactly the old one (asserted by the existing test, untouched).

## Files changed

- `tools/bl_checker.py` — arm A schema (`ArmAError`, `parse_headline`, `split_beats_doc`), geometry (`headline_layout`,
  `bug_zone`, `arm_mask_kwargs`), per-arm mask, `check_headline`, `check_headline_plate`, `check_text_over_face`,
  `run_checker`, `main`.
- `tools/bl_compose.py` — imports the schema/geometry from the checker; `check_arm_a_beats`, `check_backdrop_files`,
  `headline_plate_html`, `apply_arm_a`, `_avatar_comp_html`; `emit_pieces(headline=)`, `compose(headline=)`, `main`.
- `tools/bl_ab_run.py` — `push-tool` and `run-c` now `scp` `bl_checker.py` with `bl_compose.py` (compose imports the
  checker; a box with the new compose and an old checker could not import it, arm B included).
- `tests/test_bl_checker.py`, `tests/test_bl_compose.py`, `tests/test_bl_ab_run.py` — appended only, no existing test
  edited.
- `tests/fixtures/bl_arm_b/` — goldens recorded from the PRE-change tool (see proof).
- `docs/reports/task-406c21f3/REPORT.md` — this file.

## Tests

`.venv/bin/python -m pytest tests/test_bl_*.py -o addopts= -p no:warnings -q` in the worktree:

- after: **396 passed, 1 skipped, 0 failed**. The skip is pre-existing (`pilot composition not staged on this box`:
  `/opt/MoonieXHQ/Work/bl-split-ep57/arm1/build/index.html`).
- per file: ab_run 23 · checker 113 + 1 skipped · compose 109 · merge 16 · realfootage 33 · scripter 33 · split 27 ·
  tiktok_cta 22 · tiktok_watch 20.
- every pre-existing test in the files is untouched; new tests are appended.

New tests cover: schema (list vs object, 2 lines, 30-char limit with combining marks, `red` missing / blank / absent /
twice in one line / once in each line / overlapping / cutting a syllable, bug_side, backdrop count / t0 / src
prefix / `..`, unknown keys), FF refused in arm A, missing backdrop file, the opening rule, bug_side right, plate on an
EVID box, a template without the anchors, workdir not cleared on refusal, generator dir untouched, per-arm mask (a
standing box in each zone), plate safe-area / bug / evidence / credit overlap, text over face, composed-HTML read-back,
exit codes, and the **HTML smoke** (compose an arm-A fixture to a workdir, assert the plate element, the one red span,
the left bug override and the three backdrop switches with their timings, no render).

Guards were proved with bad inputs (each refusal test feeds the bad table and asserts the named error), not by
disabling a guard. Per-arm mask proved on ffmpeg `drawbox` videos: right bug masked in arm B only, left bug in arm A
only, plate masked only when passed as `extra_zones`.

## Arm B byte-identity proof

Old = `git show 18da8cc1:tools/bl_compose.py` / `bl_checker.py` (saved before the first edit); new = this branch. Both run on the
**real staged generator** (branch `assemble.py` + `build_cut.py`, skill-template `index.html`, built by
`bl_ab_run.build_full_generator` from an EP58-shaped work dir), sha256 of the output files:

```
COMPOSE  full        cut_pieces.json 766be8eb27d70285 / 766be8eb27d70285  index.html 198b772316b8e636 / 198b772316b8e636  identical
COMPOSE  range@4.0   cut_pieces.json 05d68320e0114953 / 05d68320e0114953  index.html 7b16ceb20c12eee2 / 7b16ceb20c12eee2  identical
COMPOSE  main()      cut_pieces.json 766be8eb27d70285 / 766be8eb27d70285  index.html 198b772316b8e636 / 198b772316b8e636  identical
CHECKER  _frame_stats means/stds identical (45 frames) · run_checker verdict identical · check_out_of_safe_area / check_credit_missing / check_text_over_face identical
```

(old / new in each pair; beats: FF, COMP with box + credit + avatar_until, EVID, KIN with named and default broll;
checker clip: 1.5 s synthetic video with 15 black frames, EVID + COMP beats with boxes.) The same is pinned in the
repo by `tests/fixtures/bl_arm_b/` — goldens recorded from the old tool for a six-beat table, full and range render —
and `test_arm_b_compose_is_byte_identical_to_the_pre_arm_a_golden` (+ a `main()` variant). `main()` calls
`compose()` for arm B with exactly the old argument list (two existing tests stub that signature).

## Layout checked in a browser (local file, network blocked)

The composed arm-A HTML from the real template was loaded in headless Chromium and the plate lines measured. Real
rendered width of the widest line vs the checker's estimate (px): mixed 786 vs 828 · short 493 vs 510 · 30 Thai
802 vs 829 · 30 capitals 725 vs 826. The first run showed **30 all-caps characters rendering 870 px in an 840 px
box** at the Thai ratio 0.58 em — the estimate was optimistic for Latin capitals (measured: Thai 0.553, lowercase
0.539, digits 0.556, capitals 0.688, max 0.94). Capitals are now estimated at 0.70 (commit f3d3ab24); Thai layouts
did not change. Screenshot checked by eye: logo + date top-left, two centred lines, red substring, nothing
overlapping. The estimate is a conservative upper bound on text width, not an exact measure; a line of wide capitals
(W, M) at the full 30 characters has no safety margin beyond the 0.70 ratio — the render will show it.

## Please confirm (CMO) — interpretation, not re-litigation

1. **Backdrop vs beats.** I made the first 3 s strict: at 0, 1 and 2 s the beat on screen must be a COMP with no `img`
   (its plate is the backdrop); an img-less COMP may only start before 3.0 s; it carries no `box` / `credit`. If you meant
   the backdrop to sit under EVID or KIN beats in the opening too, that is a small change, but then the plate layering
   needs a decision.
2. `red` as a substring, and the refusal when it would cut a Thai syllable.
3. Exit 2 for a bad schema, exit 1 for a table that cannot be rendered.

## Left for the first real render on EP58

- HEADLINE.md (task-eb88fd7b) → the headline object; three `real/` captures staged so that `fixture-full` copies
  them into `media/real` (compose refuses a missing one by name).
- A real hyperframes render of arm A — **not run here** (no render allowed). Unverified in the render engine: the
  plate's paint over matted avatar video, and the existing `#bug` entrance (`x:-50`, from 0.25 s) now starting off the
  safe edge on the left; arm B has the same 0.25 s entrance on the right.
- Matte avatars for every COMP lip part (`fixture-full` warns when missing).
- Run `bl_checker --beats <the object> --composition <composed index.html>` on the render; it now also verdicts the plate.
- Nothing detects a backdrop image that is itself blank (the empty-frame gate masks the plate, not the backdrop).
- `overlaps_credit` cannot fire with today's geometry (the chip is at y 40–85, the plate starts at 276); it is tested by
  moving the plate, and exists so a later geometry change cannot overlap silently.

## Issues / blockers

- **`tools/bl_merge.py` is outside this task's declared `touches`** (the self-repo guard refused my edit; I did not work
  around it). Its empty-frame gate calls `bl_checker.detect_empty_frames(out_path)` with the **arm-B mask**. A
  segment-merged arm-A cut would be judged with the right-hand bug mask and the plate unmasked — standing text on every
  frame can hide an empty frame, and the left bug is unmasked. The fix is ready on the checker side
  (`arm_mask_kwargs`); in bl_merge it is one line plus an optional `--beats` argument:
  `bl_checker.detect_empty_frames(out_path, **bl_checker.arm_mask_kwargs(headline))`. Needs `tools/bl_merge.py` and
  `tests/test_bl_merge.py` added to the task's touches. Not needed if EP58 arm A is rendered whole (the shipping gate,
  `bl_checker --video`, is arm-aware).
- The skill `CMO_Procedure_BlackLiquidity_Cut` does not describe arm A yet (outside touches).

## Skill learning

- MISSING [CMO_Procedure_BlackLiquidity_Cut §beats.json] : beats.json may now be `{"headline", "beats"}` (arm A); the skill documents only the bare list. Fields, rules and the FF refusal are in this report · evidence: task-406c21f3 · docs/reports/task-406c21f3/REPORT.md
- MISSING [CMO_Procedure_BlackLiquidity_Cut §6c safe area / text sizing] : Kanit 800 width per character, measured in the render's Chromium: Thai 0.553 em, Latin lowercase 0.539, digits 0.556, Latin CAPITALS 0.688 (max 0.94). The kinetic gate's flat 0.58 under-estimates all-caps Latin by about 20 % · evidence: task-406c21f3, 30 capitals = 870 px at 48 px vs an 840 px box
- MISSING [CMO_Procedure_BlackLiquidity_Cut §template `.bug`] : the skill treats the bug as fixed at the top right; arm A moves it top-left by an override applied in the render workdir only · evidence: tools/bl_compose.py `apply_arm_a` · fix: say "arm B" in that sentence
- COSTLY [CXO_Protocol_DevSpawn | no owner] : a brief whose `touches` omits a file the change forces (here `tools/bl_merge.py`: its empty-frame gate needs the arm mask) is only discovered when the self-repo guard blocks the edit mid-task · prevented by: the delegating CTO grepping the callers of every function in `touches` (`grep -rn detect_empty_frames`) before listing paths
- COSTLY [no owner] : pre-existing tests stub `bl_compose.compose` with a fixed signature, so adding a keyword argument to the call in `main()` broke two untouched tests; fix was to pass the new keyword only for the new case (arm A) · evidence: tests/test_bl_compose.py `_stub_main_io`
