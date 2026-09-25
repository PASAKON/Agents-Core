# REPORT task-b73f972f

## Summary
Cut segment seg03 of BLACK LIQUIDITY EP57 (12 lines, MAIN-4..MAIN-13 + CURIOSITY-1/2, absolute
window [65.8333, 104.5333)) per the Arm 2 split-editor A/B brief. Full-range rendering stalled
reproducibly (7 failed attempts, always frame ~388-390/1161) — the same defect CTO-FEEDBACK.md
identified as EP57's Mac incident. Switched to windowed rendering (6 sub-9s windows, concatenated
with `ffmpeg -c copy`) per the CTO's fix. Two further rounds of QC found and fixed real defects
(window-boundary gaps, four `bl_checker.py` gate failures) before delivery. Final `seg03.mp4`:
1161/1161 frames, 38.700000s, 1080x1920 30fps h264, `bl_checker.py` PASS on all 6 gates.

## Beats (12 lines, one per row — reviewable without opening the video)
- 66.12-68.32s (local 0.00-2.21s) KIN — MAIN-4, no shot + outside every avatar window; darkened
  broll/S17.mp4 (hand signing a document), 3-line kinetic "เช็กต่อว่า / มี ใบอนุญาต / ซื้อขายฟอเร็กซ์ไหม"
- 69.04-70.88s COMP — MAIN-5, wikifx-profile-no-license.png, avatar cleared via shift=380
- 71.44-73.08s FF — MAIN-6, no shot, full-frame avatar
- 73.32-76.06s COMP — MAIN-7, wikifx-profile-no-regulation.png (own box, not Jev's — see below)
- 76.36-79.92s COMP — MAIN-8, wikifx-profile-score.png (1.99/10 box) — the exact beat every
  full-range render stalled inside; renders cleanly windowed
- 80.26-83.08s COMP — MAIN-9, same still, header-line crop (UK | 2-5yr)
- 83.4-86.58s EVID — MAIN-10, wikifx-profile-warning-banner.png, top line
- 86.84-88.86s EVID — MAIN-11, same still, second line
- 89.32-93.24s EVID — MAIN-12, fca-register-search-spinner.jpg (non-1080x1920, native_w/h set)
- 93.64-97.2s KIN — MAIN-13, no shot + outside avatar window; darkened broll/S26.mp4, 3-line
  kinetic (compliance line, kept neutral — no red highlight on "โกง", see Brand/Judgment below)
- 97.64-100.16s EVID — CURIOSITY-1, third-party/wikifx-xxlmarkets-review.jpg, headline crop + credit
- 100.6-104.28s EVID — CURIOSITY-2, same card, subscore-radar crop + credit; holds to segment end (104.5333)

Mode split: KIN x2, COMP x4, FF x1, EVID x5. Every COMP/EVID box was verified by eye against the
actual source image (ffmpeg drawbox overlay + Read), not eyeballed from memory.

## Assets Used
- `real/wikifx-profile-no-license.png`, `-no-regulation.png`, `-score.png`, `-warning-banner.png`,
  `fca-register-search-spinner.jpg` — first-party captures, no credit
- `third-party/wikifx-xxlmarkets-review.jpg` — WikiFX-published card, credited both uses
  ("ขอบคุณภาพจาก WikiFX")
- `broll/S17.mp4` (hand signing a document — MAIN-4) and `broll/S26.mp4` (RICH-beanie "stop"
  gesture — MAIN-13) — the tool's own default-KIN-broll mapping (line-number → S##.mp4), reviewed
  by eye before accepting; no new B-roll sourced

## Jev / decisions.jsonl
Copied `decisions.base.jsonl` → `prototypes/bl-split-ep57/seg03/decisions.jsonl`, recorded 54
`final` calls (`jev_edit.py final --tsv`) — one per answered question on my 12 lines. Only
`MAIN-8`'s `bl.beat` crossed the measured 0.95 gate (0.98, state_lang=th) — Jev-decided, matched
my own call anyway. Every other line was editor-decided (Jev's answer shown only as a hint).
5 explicit disagreements, each with a concrete reason:
- **MAIN-7 `bl.focus_target`**: Jev's candidate box (130,20,900,400) lands on the WikiFX
  logo/nav header, not the "ยังไม่มีการกำกับดูแล" stamp the line is about — verified wrong by
  drawing the box on the actual image. Recorded `other`.
- **MAIN-10 / MAIN-12 `bl.focus_device`**: Jev said `none` (low confidence, 0.5/0.36); a spotlight
  on the warning line / FCA title is clearly the right call. Recorded `spotlight`.
- **MAIN-13 / CURIOSITY-1 `bl.entry`**: Jev said `hard_cut`/`shrink` (implying avatar presence),
  but both lines' t0 falls outside every recorded lipsync window — there is no avatar to enter.
  Recorded `other`.

## Brand / Judgment Calls
- **MAIN-4/MAIN-13 forced into KIN, not FF/COMP**: both lines' t0 falls outside all three
  recorded avatar windows (`lip_a [0,14.9) / lip_b [68.3,82.95) / lip_c [137.16,152.51)`), so
  `bl_compose.py`'s `check_avatar_window()` would refuse them as FF/COMP. Used the tool's default
  darkened-broll KIN fallback instead of forcing an avatar that doesn't exist there.
- **MAIN-13 kept neutral, not alarming**: the line is a compliance disclaimer ("I'm not saying
  this one is definitely scamming — I'm just showing what I checked"). I did not put the `.n`
  (red/neon) highlight class on "โกงแน่นอน" as the sibling-episode convention might suggest,
  since visually emphasizing "definitely scamming" inside a sentence that explicitly denies
  saying that would undercut the very disclaimer the line exists to make. Highlighted the
  compliant half ("ไปดูของจริง") in yellow instead.
- **COMP beats all use `shift: 380`**: per `blackliquidity-cut/SKILL.md` §6d's measured fix
  (the HARD rule: avatar must never cover the evidence box) — verified by eye on all 4 COMP
  frames that the evidence box clears the avatar's y≈845 top with margin.
- **Evidence boxes trimmed for `bl_checker.py`'s safe-area gate**: MAIN-9 (372→315px),
  MAIN-10 (750→690px), MAIN-12 ([0,0,1374,520]→[70,0,1230,520] — was spanning the full
  edge-to-edge plate), CURIOSITY-1 (y 150→200, which also fixed its credit-chip clearance).
  Every trim re-verified by eye against the source image; none lose the actual evidence text.

## Files Changed
- `prototypes/bl-split-ep57/seg03/beats.json` — the 12-beat composition (new)
- `prototypes/bl-split-ep57/seg03/decisions.jsonl` — Jev decisions + 54 editor finals (new)
- `prototypes/bl-split-ep57/seg03/render-meta.json` — final render metadata (new)
- `RUNLOG.md` — full timestamped build log, including every failed attempt and bug found (new)
- `CTO-FEEDBACK.md` — the windowing-fix instruction received mid-task (kept for the audit trail)
- Outside the worktree (not git-tracked, per the brief):
  - `/opt/MoonieXHQ/Work/bl-split-ep57/parts/seg03.mp4` — final video (7.09 MB, 1161 frames)
  - `/opt/MoonieXHQ/Work/bl-split-ep57/compositions/seg03.html` — composed HTML

## Commits
- 7c3811c6 — video(bl-ep57-seg03): author beats.json + jev finals for seg03 [65.83,104.53)
- c5be11c7 — video(bl-ep57-seg03): fix window-boundary gaps + checker-gate failures, ship windowed render

## Tests
- ran: `python3 tools/bl_checker.py --video .../seg03.mp4 --beats beats.json --composition .../build/index.html`
- passed: 6/6 gates (empty_frames, out_of_safe_area, text_over_face, credit_missing, extra_caption_styles, kinetic_overflow)
- failed: 0 (after 2 fix rounds — see Issues below for what the first two runs caught)
- skipped: 0
- Frame-count check: `ffprobe -count_frames` = 1161/1161, matching `104.5333-65.8333 = 38.7s * 30fps` exactly

## Issues / Blockers
- **Full-range render is unusable on this box for this composition** (7 failed attempts, always
  stalling at frame ~388-390/1161, inside MAIN-8's avatar-matte composite — the 3rd `lip_b`
  matte seek in the composition). CTO confirmed this is the same defect EP57 hit on the Mac.
  Worked around with the 6-window split; the underlying tool/box issue is unresolved and will
  hit the next full-episode or long-segment render too.
- **`bl_checker.py`'s safe-area/credit checks don't account for COMP's `shift` field** — its
  `img_placement()` (a read-only copy of `build_cut.py`'s geometry) has no `shift` parameter, so
  it evaluates a COMP beat's box position as if unshifted. My 4 COMP beats' boxes happened to
  still land inside the safe rect either way (checked by hand), so this didn't cause a false
  pass/fail here, but it's a real gap for a future beat where the shifted and unshifted
  positions disagree on safe-area membership.
- Window-splitting math is unforgiving of naive decimal rounding: truncating a repeating
  decimal (e.g. `2408/30`) to 6 places in either direction can flip a frame-count `floor()` by
  exactly one frame, or leave a sub-frame gap at a window seam. Used full float precision
  (`n/30` via Python, not hand-typed decimals) for the final boundary set — worth carrying into
  the shared tooling rather than leaving to each editor to rediscover.

## Notes for Reviewer
- The RUNLOG.md has a full, timestamped account of every failed render attempt, the exact
  frame/beat each one stalled on, and every QC bug found — useful if the frame-390 stall pattern
  needs to be diagnosed further at the tool level.
- Please double check MAIN-12's FCA screenshot placement (a 1374x868 non-1080x1920 image) renders
  as expected outside this sandbox — I verified it visually here and the geometry math checks out,
  but it's the one beat using the `img_placement()` non-square-aspect scaling branch in this segment.

## Skill learning
- MISSING [reel-editor-th/blackliquidity-cut §render] : the render lock (`flock /tmp/bl-render.lock`) serializes renders but does not prevent a single render from stalling irrecoverably around frame 388-390 on a composition with 3+ avatar-matte composites under memory pressure — the skill should document the ≤9s windowed-render pattern (bl_compose.py --t0/--t-max per window + ffmpeg -f concat -c copy) as the default for any segment with 2+ COMP beats, not a fallback discovered per-incident · evidence: task-b73f972f RUNLOG.md, 7 failed full-range attempts, CTO-FEEDBACK.md confirming the same failure on EP57/Mac · fix: add the windowed-render recipe + the "snap each window's first beat t0 to its window boundary" rule to blackliquidity-cut/SKILL.md's render section
- MISSING [reel-editor-th/blackliquidity-cut §checker] : bl_checker.py's img_placement() has no `shift` parameter, so its safe-area and credit-clearance checks evaluate a COMP beat's evidence box at its UNSHIFTED position, silently diverging from what shift=380 actually renders · evidence: tools/bl_checker.py lines 138-148 vs tools/bl_compose.py's real shift application at line 315 · fix: thread `extra.get("shift",0)` through bl_checker.py's img_placement/top calc the same way bl_compose.py does
- COSTLY [reel-editor-th/blackliquidity-cut §windows] : hand-rounding repeating-decimal window boundaries (e.g. writing 80.266667 for 2408/30) cost 2 extra render cycles (one beat silently excluded, one seam left a sub-frame gap) before I switched to full Python float precision for every boundary · evidence: RUNLOG.md 2026-09-25 entries re: MAIN-9 exclusion and the 4-seam empty-frame bug · prevented by: compute every window boundary as `frame_number/30` in code (or a small helper), never type a manually-rounded decimal
