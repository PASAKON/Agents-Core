# task-f35f2935 — BL EP58: caption pill above the avatar's head on COMP beats, proved and re-rendered (v3, both arms)

Developer worker, Sonnet 5.5. Spent no money. Nothing pushed, nothing posted. v2 finals untouched.

## Outputs (mp4/jpg live in Work, none in git)

| | arm B (`prototypes/bl-ep58/beats.json`) | arm A (`prototypes/bl-ep58/armA/beats.json`) |
|---|---|---|
| final | `/opt/MoonieXHQ/Work/bl-ep58/cut/v3/final-ep58-v3.mp4` | `/opt/MoonieXHQ/Work/bl-ep58/armA/v3/final-ep58-armA-v3.mp4` |
| sheet | `cut/v3/sheet-ep58-v3.jpg` (25 frames) | `armA/v3/sheet-ep58-armA-v3.jpg` (24 frames) |
| review frames | `cut/v3/frames/` | `armA/v3/frames/` |
| windows rendered | seg01–seg07 | seg01, seg02, seg05, seg06, seg07, seg12 |
| windows reused from v2 | seg08–seg12 (no COMP / changed beat) | seg03, seg04, seg08–seg11 (no COMP / changed beat) |
| frames / loudness | 2871 / -15.4 LUFS | 2871 / -15.4 LUFS |

The reuse is a copy (`cp -a`), not a move. Arm A's v2 build dirs no longer exist, so the one-caption-style gate read the six v3 build dirs only.
Both arms went through `bl_merge --beats`, then single-pass `loudnorm=I=-14:TP=-1.5:LRA=11 -c:v copy`.

## Acceptance (one line each)

1. **text_over_face PASS, per-take face boxes, both arms.** `bl_checker --per-take-face-boxes` returns `text_over_face: []` and `comp_evidence_landing: []` on both finals. `ck.face_box_beats` (identical for lip_a and lip_b in both arms):
   - lip_a COMP box `[-25,903,573,559]`: HOOK-1, HOOK-2, HOOK-3, HOOK-4, PATTERN-1, PATTERN-2, PATTERN-3.
   - lip_b COMP box `[-7,968,576,494]`: MAIN-5 … MAIN-11.
   - lip_c: arm B = **FF** `[151,277,742,824]` (SUMMARY-7/8/9 stay full-frame, pill at 1300); arm A = **COMP** `[48,999,416,463]` (SUMMARY-7/8/9).
   - Why it holds: the 2-line pill's bottom is centre+82. lip_a 797+82 = 879 < head top 903.04; lip_b 862+82 = 944 < 968.56; lip_c 893+82 = 975 < 999.92. That is a 24 px margin at each take's highest frame, and the head-top comes from a 30 fps scan of every frame the cut can show.
2. **Brand mark ≥ 95% of steady on every frame, both arms.** Arm B min ratio 0.9841 (at 83.767 s), arm A 0.9882 (at 4.533 s), all 2871 frames, `failing_frames: 0`. t=0 and the 11 seam frames are inside that range.
3. **Merge gates PASS, both arms.** frame_count 2871 vs 2872 ±1, empty_frames `[]`, seam_failures `[]`, audio offset 0.0 s, extra_caption_styles `[]`. Excused KIN-entry frames: arm B 16.633–16.733, 29.667–29.733, 71.567–71.667; arm A 16.633–16.733.
4. **`bl_tools.py verify` PASSED with the 3 lip seats, both arms.** Sync 0 ms at 4.8/43.1/86.1 s; lip A/B/C seated at 0.00/38.77/80.84 s at 0 ms, r = 0.978/0.992/0.985. The originals were read from `Work/bl-ep58/drive/AI Drafts`.
5. **Identical avatar geometry in both arms.** `.avatar-comp` (56%, bottom 0, translateX −6%) is untouched. `scripts/bl_edl.py` `AVATAR_BOX` is unchanged (845) and a test pins it. The A/B variable is still first 3 s + headline only.

## Pill centres (the number the whole change rests on)

| take | head top (canvas y, min over 30 fps frames shown) | pill centre | beats |
|---|---|---|---|
| lip_a | 903.04 | **797** | HOOK-1…4, PATTERN-1…3 |
| lip_b | 968.56 | **862** | MAIN-5…11 |
| lip_c | 999.92 | **893** | arm A SUMMARY-7/8/9 |
| FF / EVID / KIN | – | 1300 (unchanged) | |

Centre = head top − 24 − 82. A 1-line pill is ~101 px tall, a 2-line one 164 px. Measured by `tools/bl_face_box.py`, committed in `docs/reports/task-f35f2935/head-top.json`, pinned by `tests/test_bl_face_box.py`. The 0.5 s sampling of d4c1f234 read 111 where frame 0 is 104, which is why the scan is per frame.

Because the head-top comes from the take-wide minimum, the pill sits ~100 px above the *steady* head after the first second. A per-beat envelope would give more evidence room (see Alternatives).

## Golden diff (`tests/fixtures/bl_arm_b`)

FF `caption(0.0, 2.0, "Hook line");` and the EVID lines are byte-identical before and after.

```
beats.json       C1 extra: "avatar_until": 3.5,  +"cap_cy": 797
cut_pieces.json  -caption(2.0, 4.0, "Comp caption");   +caption(2.0, 4.0, "Comp caption", 797);
full/index.html  +.caplayer rule in <head><style>, +CAPN / caption(at,out,text,cy) override, call line with 797
range/index.html same (12 lines)
```

Template `caption(at,out,text,cy)` sets `d.style.top=(cy-1300)+"px"`; 3-argument calls behave as before.

## Per-beat changes since v2 (where the crop / box / shift changed)

Every captioned COMP beat now carries `extra.cap_cy`. Boxes are canvas coordinates (all real stills are 1080×1920). A COMP beat's `shift` lifts still and spotlight together; placed y = box y − shift.

Arm B:

| beat | change |
|---|---|
| HOOK-1/2 | box `[150,440,876,320]` → `[205,782,450,178]` (the score tile), shift none → 300 |
| HOOK-3 | box `[54,875,972,172]` → `[54,895,972,122]`, shift 120 → 332 |
| HOOK-4 | box `[54,962,972,65]` → `[54,968,972,55]`, shift 120 → 332 |
| PATTERN-1 | shift −50 → 130 |
| PATTERN-2 | shift −160 → −230 |
| PATTERN-3 | box `[85,285,910,190]` → `[85,288,910,62]`, shift −160 → −230 |
| PATTERN-4 | EVID complaint-1 still → KIN (like arm A): the blank-white still at 16.7 s is gone |
| CONTEXT-4 | box `[54,405,972,195]` → `[124,555,180,45]` (arm A's box) |
| MAIN-5, MAIN-7 | no crop or shift change |
| MAIN-6 | shift −50 → 130 |
| MAIN-8/9 | shift none → −265 |
| MAIN-10/11 | shift 780 → 990 |

Arm A (same boxes as arm B where both have one; shifts differ because of the headline plate and scrim, which end at 560):

| beat | change |
|---|---|
| HOOK-1/2 | cap_cy only (no still / box of its own: the opening is arm A's own plate backdrop) |
| HOOK-3/4 | same box and shift as arm B (332) |
| PATTERN-1 | shift −140 → 130 |
| PATTERN-2 | shift −470 → −310 |
| PATTERN-3 | box as arm B, shift −470 → −305 |
| MAIN-6 | shift −100 → 130 |
| MAIN-7 | shift −300 → −100 |
| MAIN-8/9 | shift −520 → −365 |
| MAIN-10/11 | shift 780 → 990 |
| SUMMARY-7/8 | cap_cy 893 only (shift 300 kept) |
| SUMMARY-9 | shift 300 → 570, box `[54,1170,700,70]` kept |
| MAIN-13 | still unchanged (already the same in both arms) |

The evidence region is the strip between the bug / headline plate and the pill: top 460.8 (arm B, below the bug) or 560 (arm A), bottom = pill top − 12 − 10. That is 232 / 297 px tall in arm B and 133–229 px in arm A, which is why boxes were cropped (HOOK-1/2, HOOK-3, PATTERN-3) and shifted. `check_comp_evidence_landing` (new, in `tools/bl_checker.py`) fails any COMP spotlight that lands outside it.

## Frame verdicts

Criteria per frame: caption clear of eyes/nose/mouth · evidence + spotlight readable inside the safe area (x ≥ 54, right rail, bottom 300) · nothing in the TikTok UI zone · brand mark on · no blank band. "OK" means all five hold. "Dark band" below means the template's own dark brand background shows where the still was lifted; it is not white and not a blank frame.

### Arm B (`final-ep58-v3.mp4`)

| t | beat | verdict |
|---|---|---|
| 0.0 | HOOK-1 | **OK, frame 0 fixed.** Pill not up yet (beat t0 0.28). Tile + name + "3.73/10" sit above the hat (tile y 715–879, head top 903). Card cut off at the right edge = source capture (e). Mark + legal pill on. |
| 0.5 | HOOK-1 | OK. Pill centred 797 ("Weltrade โดนว่าถอนเงินไม่ออก") above the head; yellow box round 3.73 fully inside the tile, x ≥ 205. |
| 3.0 | HOOK-2 | OK. Pill "จริงไหม กูไปเช็กมาให้" clear of the hat; spotlight on 3.73 still on. |
| 9.1 | PATTERN-1 | OK. Pill fading in at 797, clear of the head; abstract readable; spotlight not yet faded in. Bug sits over the still's headline, not over the spotlighted abstract. |
| 9.3 | PATTERN-1 | OK. Spotlight on the abstract's first lines (x ≈ 54), "43" readable; pill clear. |
| 16.7 | PATTERN-4 | **OK, fixed.** KIN entry frame 2: dark brand background, mark + legal pill on, text lands at 16.9 s; the gate excuses entry frames 1–4. The v2 blank-white EVID still is gone. |
| 34.1 | MAIN-3 | OK. Licence still, 3.73 + FSCA row readable; no avatar; mark on; legal pill over a heading (static band, as v2). |
| 48.97 | MAIN-8/9 | OK. Pill fading at 862, clear of the head; title "ไม่พบสำนักงาน" readable at placed y ≈ 465–525; bug only over the nav bar. Dark band at the top (cosmetic a). |
| 59.9 | EVID | OK. Spotlight on contents item 02 readable; EVID pill at 1300 (unchanged) over still text, as v2. |
| 74.4 | KIN | OK. Text on the red-orb plate, mark + legal pill on. |
| 86.7 | SUMMARY-6 | OK. KIN entry on the counter b-roll; mark + legal pill on; text starts at 86.8 ("สาม"). Unchanged from v2. |
| 89.5 | SUMMARY-7 (FF) | OK. Pill at 1300 over the jacket, under the chin; mark on. |
| 92.0 | SUMMARY-8 (FF) | OK. Same. |
| 94.5 | SUMMARY-9 (FF) | OK. Same. |
| seam 272 / 9.07 | PATTERN-1 in | OK. Article + avatar, pill not up yet, head clear. |
| seam 499 / 16.63 | PATTERN-4 in | OK (excused KIN entry, mark + legal pill on). |
| seam 751 / 25.03 | EVID | OK. Article headline + abstract readable; mark on. |
| seam 1023 / 34.10 | MAIN-3 | OK. Same as 34.1. |
| seam 1270 / 42.33 | MAIN-5/6 | OK. Avatar clear, article readable, pill not up yet. |
| seam 1469 / 48.97 | MAIN-8/9 | OK. Same as 48.97. |
| seam 1697 / 56.57 | EVID | OK. Warning card + rating readable. |
| seam 1944 / 64.80 | EVID | OK. St Vincent card readable. |
| seam 2147 / 71.57 | CURIOSITY-5 in | OK (excused KIN entry). |
| seam 2376 / 79.20 | FF | OK. Avatar full frame, mark + legal pill on, no caption yet. |
| seam 2598 / 86.60 | SUMMARY-6 in | OK (excused KIN entry). |

### Arm A (`final-ep58-armA-v3.mp4`)

| t | beat | verdict |
|---|---|---|
| 0.0 | HOOK-1 | **Minor flaw, not fixed.** Pill not up yet. The hat covers the left edge of the "3" in 3.73 for about the first 0.2 s (clear from 0.3 s on). Arm A's opening has no spotlight and no still of its own (plate backdrop = the A/B variable), so I left it. Mark + stamp on. |
| 0.5 | HOOK-1 | OK. Pill at 797 above the head; "3.73/10" readable; no overlap with the plate. |
| 1.0 | HOOK-1 | OK. Same. |
| 2.0 | HOOK-2 | OK. Same; pill clear of the head. |
| 3.0 | HOOK-2 | OK. Pill "จริงไหม กูไปเช็กมาให้" clear. |
| 9.1 | PATTERN-1 | OK. Pill fading in at 797; abstract readable below the scrim (ends 560). |
| 34.1 | MAIN-3 | OK. Licence still readable under the plate; mark on. |
| 48.97 | MAIN-8/9 | OK. Pill fading at 862; title readable inside the region; no dark top band (shift −365, the plate covers the top). |
| 59.9 | EVID | OK. Spotlight on item 02 readable; pill at 1300 unchanged. |
| 74.4 | KIN | OK. |
| 89.5 | SUMMARY-7 | OK. Pill at 893 above the head (gap to the hat ≈ 60 px); FSCA row readable above it; "หมายเลข…" line is under the pill (no spotlight on this beat). |
| 92.0 | SUMMARY-8 | OK. Same; 2-line pill ends above the hat. |
| 94.5 | SUMMARY-9 | OK. Yellow box on "50691" at placed y 600–670, below the scrim; pill clear of the head. Dark band right of the avatar from ≈ 1350 down (cosmetic b). |
| seam 272 / 9.07 | PATTERN-1 in | OK. |
| seam 499 / 16.63 | PATTERN-4 in | OK (excused KIN entry; plate + mark on). |
| seam 751 / 25.03 | EVID | OK. |
| seam 1023 / 34.10 | MAIN-3 | OK. |
| seam 1270 / 42.33 | MAIN-5/6 | OK. |
| seam 1469 / 48.97 | MAIN-8/9 | OK. |
| seam 1697 / 56.57 | EVID | OK. |
| seam 1944 / 64.80 | EVID | OK. |
| seam 2147 / 71.57 | CURIOSITY-5 in | OK (excused KIN entry). |
| seam 2376 / 79.20 | FF | OK. Plate over the hat, as v2 (arm A's design). |
| seam 2598 / 86.60 | SUMMARY-6 in | OK (excused KIN entry). |

## Known cosmetic issues (not fixed, outside the brief)

- (a) Arm B MAIN-8/9 and PATTERN-2/3 show a 230–265 px dark brand band at the top, a consequence of landing the spotlight below the bug. Candidate fix: let boxes with x+w ≤ 594 sit above y 461, since the bug zone is only on the right.
- (b) MAIN-10/11 (both arms) and arm A SUMMARY-9 lift the still by 990 / 570. That exposes the dark brand background to the right of the avatar, from about y 930 / 1350 down. v2 used 780 for MAIN-10/11. These frames are not on either review list.
- (c) The MAIN-6 spotlight cuts mid-word. Pre-existing; box left as it was.
- (d) Text inside the complaint stills is about 16 px at canvas scale, unreadable on a phone. Same as v2; needs a recapture or a zoom.
- (e) The weltrade-header still is a zoomed capture cut off at the right, so the "cut off" look of arm B frame 0 cannot be fixed without a recapture.
- (f) Arm A frame 0.0: hat over the edge of the "3" for ~0.2 s (see above).
- (g) PATTERN-4 has no clip because `media/broll` has no `S08.mp4`; `default_kin_broll` returns a path only when the line has one. Both arms show the bare brand background behind the text, as arm A did in v2.

## Editorial choices to confirm

- Arm B PATTERN-4 is now KIN, the same as arm A (the brief's "fix the 16.7 s EVID still"). The alternative was a replacement still.
- Arm B CONTEXT-4 takes arm A's box `[124,555,180,45]`. MAIN-13's still was already identical in both arms.

## Alternatives not taken

- A per-beat head-top envelope instead of the per-take minimum would put the pill closer to the head after the first second and give evidence 60–100 px more room.
- An EVID `view` crop (bl_compose ignores EVID `shift`) would let EVID pills move off still text. They are untouched here because the brief keeps them at 1300.

## Correction to the brief

The empty-frame mask does **not** use `caption_band`. It uses the static legal band (.66–.74 H) and the bug zone. Moving the pill therefore cannot change the empty-frame result, and did not.

## What changed in the repo

- `.claude/skills/CMO_Procedure_BlackLiquidity_Cut/template/index.html`: `caption(at,out,text,cy)`, `.caplayer`.
- `tools/bl_compose.py`: `cap_cy` plumbing (`add_caption_cy`, `check_cap_cy`, `caption_call`).
- `tools/bl_checker.py`: `COMP_TAKES`, `comp_caption_cy`, `caption_band(mode, cy)`, `evidence_region`, `check_comp_evidence_landing`, `check_text_over_face(..., take_boxes)`, `face_box_beats`, `--per-take-face-boxes`.
- `tools/bl_face_box.py`: the head-top envelope (merged from d4c1f234, extended).
- `tests/test_bl_checker.py`, `tests/test_bl_compose.py`, `tests/test_bl_face_box.py`, goldens in `tests/fixtures/bl_arm_b`.
- `prototypes/bl-ep58/beats.json`, `prototypes/bl-ep58/armA/beats.json`, `prototypes/bl-ep58/segments.json` (12 windows), `prototypes/bl-ep58/render_v3.sh` (flock + RAM-gated driver, one window at a time), both `render-meta.json`.
- `docs/reports/task-f35f2935/head-top.json`, this file.
- The old `prototypes/bl-ep58/armA/render_seq.sh` / `render_lock.sh` / `render_window.py` still point at old worktrees; `render_v3.sh` replaces them and calls `render_window.py` for arm A.
