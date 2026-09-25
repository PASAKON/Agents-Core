# REPORT task-fcd2b95d

## Summary
Cut seg04 of BL EP57's split-editor A/B, Arm 2 (`docs/ops/bl-split-ab-2026-09-25/BRIEF-seg.md`) — the
window [104.5333, 153.0333)s, tags CURIOSITY-3..5 + SUMMARY-1..9 (12 lines). Final render
(`/opt/MoonieXHQ/Work/bl-split-ep57/parts/seg04.mp4`, 1080x1920/30fps/48.500000s/1455 frames/h264,
video-only) passes `tools/bl_checker.py` clean on every gate. Ran the Jev loop per the CTO override
(no `plan`/`freeze`, copied `decisions.base.jsonl`, recorded my own `final` call on all 55 question
rows across my 12 lines). Two real render defects were found and fixed along the way (details below) —
neither was an editorial-content mistake, both were size/overflow bugs in the KIN line content.

## Beats
- CURIOSITY-3 (104.74-108.24) **KIN** — outside every avatar window (lip_c starts 137.16); 3 lines, highlight WikiFX
- CURIOSITY-4 (108.24-114.22) **KIN** — same; 3 lines, highlight WikiFX
- CURIOSITY-5 (114.22-117.74) **KIN** — same; 3 lines
- SUMMARY-1 (118.2-119.32) **KIN** — same; 1 short line
- SUMMARY-2 (119.76-125.02) **KIN** — same; 3 lines
- SUMMARY-3 (125.4-128.96) **KIN** — same; 3 lines
- SUMMARY-4 (129.38-132.88) **KIN** — checklist card 1/3 (no real footage, per SCRIPT.tsv's own note); numeral + 2 lines
- SUMMARY-5 (133.52-137.26) **KIN** — checklist card 2/3; numeral + 2 lines
- SUMMARY-6 (137.86-141.02) **KIN** — checklist card 3/3; numeral + 2 lines, highlight WikiFX
- SUMMARY-7 (141.48-145.64) **FF** — t0 141.48 falls inside lip_c's [137.16, 152.51) window
- SUMMARY-8 (146.08-150.5) **FF** — same window, CTA line (keyword "เช็กเว็บโบรก" unchanged)
- SUMMARY-9 (150.8-152.64) **FF** — same window, close line; holds to segment end 153.0333

All 12 lines have empty `shot_basename` in SCRIPT.tsv (no real-footage still assigned to any line in my
window), so the only mode choices in play were FF vs KIN, decided purely by the avatar-footage windows
constraint (see Brand/Judgment Calls). No COMP/EVID beats in this segment.

## Assets Used
- `media/broll/S29.mp4`..`S37.mp4` — one clip per KIN beat's own SCRIPT.tsv line number (`default_kin_broll()`'s
  built-in default, left unset in `extra` so the tool applies it). Reviewed all 9 as a contact-sheet thumbnail
  before using: generic brand b-roll (host in "RICH" beanie, neon server corridor, magnifying glass, files/keys,
  city skyline silhouette) — no baked-in text, nothing misleading for a KIN card with no real footage behind it.
- `media/lip_c.mp4` + `media/matte/lip_c-matte.webm` — avatar footage for the 3 FF beats (all inside lip_c's window).

## Brand / Judgment Calls
- **9 of 12 lines are KIN, not FF, because of a hard technical constraint, not an editorial choice**: the
  fixture's 3 recorded lipsync takes only cover `lip_a [0,14.9)`, `lip_b [68.3,82.95)`, `lip_c [137.16,152.51)`.
  My window (104.53-153.03s) only overlaps `lip_c`, and only from 137.16s onward — so CURIOSITY-3 through
  SUMMARY-6 (104.74s-141.02s) have no avatar footage at all and had to become KIN. I derived this independently
  from `build_cut.py`'s `pick_lip`/`lip_offset` before checking, then found the prior Arm1 pilot (commit
  0034f4d7) had reached the exact same mode split for these same tags — cross-checked, not copied.
- **Highlight word**: `<span class="n">วิกิเอฟเอ็กซ์</span>` (WikiFX) on CURIOSITY-3, CURIOSITY-4, SUMMARY-6 —
  matches Jev's own `bl.highlight_word` candidate (confidence 0.84-0.86) on all three, and the word is genuinely
  the subject of each line.
- **Checklist numerals**: SUMMARY-4/5/6 open with a standalone "1"/"2"/"3" line (`bl-xl`) before the question
  text, rather than repeating "หนึ่ง/สอง/สาม" verbatim — a numeral reads faster than the spoken word on a card
  labelled "checklist 1/3" in its own SCRIPT.tsv note, and KIN text is display copy, not a caption transcript.

## Two render defects found and fixed (not editorial mistakes — both are size/overflow bugs)
1. **A too-long single-line KIN string crashes the WHOLE render's text layer, silently.** My first beats.json
   put CURIOSITY-3's full 68-character sentence on one `bl-lg` line. `index.html`'s `fitKineticLine()` shrinks
   font size to fit, but at the 32px floor that line still measured 1896px against a 720px safe box and threw —
   which aborted the page's entire inline `<script>`, so **every** later `kinetic()`/`caption()` call (all 9 KIN
   beats + all 3 FF captions + the brand-bug entrance) never registered on the GSAP timeline. The render still
   exited 0, still produced the right frame count/duration, and the checker's own `empty_frames` gate didn't
   catch it (the underlying broll/avatar plates have real texture, so `std<12` never triggers) — this was a
   **silent, checker-invisible defect**, only caught by pulling frames and looking. Rendered twice (identical
   `sub_timeline_readiness_timeout` WARN both times, an unrelated red herring — this template has no actual
   sub-compositions) to confirm it was deterministic, not a load flake, then root-caused with a
   puppeteer/chrome-headless-shell debug script (loading the composed HTML directly and listening for
   `pageerror`) that pinpointed the exact throwing line in under 2 seconds — much faster than the ~12-13 min
   full render/QC loop. Fixed by splitting every long line to 2-3 shorter ones.
2. **`tools/bl_checker.py` has its own, stricter `kinetic_overflow` gate** — a static per-character-width
   estimate at each line's *authored* (unshrunk) font size, deliberately not crediting the render-time shrink
   ("a beats.json author should split a too-long line rather than lean on the render-time shrink" — the
   checker's own docstring). My first fix (splitting lines but keeping `bl-lg`) rendered and looked fine by eye,
   but still failed this gate on 13 lines. Recomputed the real per-class character budget from the checker's own
   `KINETIC_CHAR_WIDTH_RATIO` (bl-xl~12, bl-lg~15, bl-md~20, bl-sm~28 visual chars/line) and switched every long
   KIN body line to `bl-sm`, keeping `bl-xl` only for the 1-character checklist numerals and `bl-lg` for the one
   already-short SUMMARY-1 line. Verified against the checker's own `check_kinetic_overflow()` function directly
   on the dry-run compose (0 flags) before spending a third 12-minute render.

Net: 4 renders total (~50 min of render time on this shared box), 3 of them avoidable in hindsight only with a
faster local validator — which I built (a small puppeteer harness + calling the checker's own Python functions
directly against a `--no-render` dry-run compose) and used for the last two fixes, so the 4th render was the
first one I was actually confident would pass before starting it.

## Jev scoreboard (my window's 55 rows, `prototypes/bl-split-ep57/seg04/decisions.jsonl`)
- `bl.beat` (the only site with a measured gate, th @0.95): my confidence values topped out at 0.8 (SUMMARY-2),
  so the gate never fired — every row's `applied_by` is `editor`, `jev_wrong_at_gate` is `false` throughout.
- **32 of 43 answered rows agreed with Jev's own choice; 11 disagreed** (0 at the safety gate). The one
  substantive disagreement worth flagging: CURIOSITY-3's `bl.beat` — Jev said `show` @0.46 (low confidence);
  I cut it `verdict` per SCRIPT.tsv's own beat column (matches the prior Arm1 pilot's same call on this same
  line, found only after I'd already made mine). The rest of the disagreements are `bl.focus_device`/`bl.entry`
  overrides on KIN beats (Jev proposed `spotlight`/`shrink`, which don't structurally apply to a KIN card with
  no image and no avatar — I recorded `none` instead) and `bl.text_slot` (KIN's `top` is hardcoded to 760 by
  `bl_compose.py`, ignoring any per-line slot choice, so I recorded `other` throughout rather than pretending a
  slot choice does anything).

## Segment contract check
- First plate: CURIOSITY-3 starts at composition-local t=0.207s (its own SCRIPT.tsv t0, 104.74s, is 0.207s
  after my segment's t0 of 104.5333s — there's no spoken line exactly at the boundary). This sits inside
  `bl_checker.py`'s own 0.25s `EMPTY_FRAME_IGNORE_BEFORE` tolerance and matches the same pattern seg01/seg03
  already carry at their own edges (their first lines don't start exactly at t=0 either).
- Last plate: SUMMARY-9's avatar FF holds frozen on its last decoded frame all the way to 153.0333s (verified
  on the literal last encoded frame) — no fade in/out at either edge.
- Video-only, 1080x1920, 30fps, frame-exact (1455 frames = `round((153.0333-104.5333)*30)`).

## Files Changed
- `prototypes/bl-split-ep57/seg04/beats.json` — 12-beat composition (9 KIN + 3 FF)
- `prototypes/bl-split-ep57/seg04/decisions.jsonl` — Jev's rows for my 12 lines + my `final` calls (55 rows)
- `prototypes/bl-split-ep57/seg04/final_calls.tsv` — the bulk `jev_edit.py final --tsv` input
- `prototypes/bl-split-ep57/seg04/render-meta.json` — seg04.mp4's path/size/duration/fps/checker verdict
- `RUNLOG.md` — append-as-you-go step log, including both defects and their fixes

Not in git (per the brief — media never goes in the repo):
- `/opt/MoonieXHQ/Work/bl-split-ep57/parts/seg04.mp4` (18.7MB) and `/opt/MoonieXHQ/Work/bl-split-ep57/compositions/seg04.html` — delivered per the brief's own paths
- `/opt/MoonieXHQ/Work/bl-split-ep57/seg04/build/` — scratch render workdir

## Commits
- `7db3dc34` — beats.json (9 KIN + 3 FF) + Jev final calls
- `e1550636` — fix kinetic-text overflow crash (split long KIN lines)
- `14f75374` — switch long KIN lines to bl-sm to satisfy bl_checker's kinetic_overflow gate
- `b217906c` — final render passes bl_checker clean, deliver parts/compositions + render-meta

## Tests
- ran: `python3 tools/bl_checker.py --video .../seg04.mp4 --beats prototypes/bl-split-ep57/seg04/beats.json --composition .../build/index.html`
- result: `"pass": true` — `empty_frames`/`out_of_safe_area`/`text_over_face`/`credit_missing`/`extra_caption_styles`/`kinetic_overflow` all `[]`
- No unit-test suite applies to a content/editorial deliverable; `bl_compose.py`/`bl_checker.py`'s own `tests/test_bl_*.py` weren't touched and weren't re-run (no tool code changes).

## Issues / Blockers
- None blocking. See "Two render defects found and fixed" above — both fixed within this task, not left for the CTO.
- Did not run `jev plan`/`freeze` per the CTO's explicit override (already done 2026-09-23).
- Box is genuinely slow for this pipeline: each `bl_compose.py` render of my 48.5s window took ~12-13 minutes
  (software-GL chrome-headless-shell, no hardware acceleration on this Contabo VPS) — worth the CTO's attention
  if more Arm-2-style parallel segment renders are planned, since 4 editors' renders all serialize behind the
  same `/tmp/bl-render.lock`.

## Notes for Reviewer (CMO/CTO)
- The two defects above are worth folding into `bl_compose.py`'s/the skill's own documentation so the next
  segment editor doesn't rediscover them the slow way (see Skill learning below) — a beats.json author currently
  has no fast way to know a KIN line is too long until either a JS throw silently kills the whole render, or a
  full render+checker cycle flags it ~12 minutes later.
- `prototypes/bl-split-ep57/seg04/decisions.jsonl` has only my window's 55 rows (filtered from the 199-row base
  file) per the brief's "your window's lines only" instruction.

## Skill learning
- WRONG [blackliquidity-cut / reel-editor-th, whichever owns bl_compose.py's kinetic() KIN authoring guidance §KIN plate table] : a KIN line at `bl-lg` (or any class) that "fits after the render-time shrink" is NOT good enough — `bl_checker.py`'s own `kinetic_overflow` gate measures the UNSHRUNK, as-authored width and fails a line that only fits after shrinking. The two checks disagree on purpose (checker docstring: "a beats.json author should split a too-long line rather than lean on the render-time shrink"), but nothing in the skill docs states the real per-class character budget an author should target. Real numbers from `bl_checker.py`'s own `KINETIC_CHAR_WIDTH_RATIO=0.58`: bl-xl ~12 visual chars/line, bl-lg ~15, bl-md ~20, bl-sm ~28 (a Thai tone/vowel mark like ั ิ ี ึ ื ุ ู ่ ้ ๊ ๋ ์ doesn't count toward this). · evidence: task-fcd2b95d, commits e1550636/14f75374, `bl_checker.py` lines 320-384 · fix: add this budget table to the skill's KIN authoring section so an editor sizes lines correctly on the FIRST beats.json draft instead of discovering it via a failed checker run after a 12-minute render.
- MISSING [blackliquidity-cut §KIN authoring / bl_compose.py's own module docstring] : a single kinetic() call whose line overflows even at the 32px floor throws inside the composed page's main inline `<script>`, which silently aborts EVERY later `kinetic()`/`caption()`/credit/spotlight/brand-bug call in the whole composition (not just the offending beat) — the render still exits 0 with the correct frame count/duration, and `bl_checker.py`'s own `empty_frames` gate does NOT catch it when the underlying video/image plate has real texture (a dark-but-detailed broll clip easily clears the `std<12` threshold with zero text on top). This means a broken render can look "done" (right size, right duration, checker technically doesn't run because nobody re-ran it against THIS exact failure mode until now) unless someone pulls frames and looks, or the NEW `kinetic_overflow` gate (which does catch the root cause, just not this specific silent-failure SYMPTOM) is run. · evidence: task-fcd2b95d, first two renders (identical `sub_timeline_readiness_timeout` WARN both times — an unrelated red herring, not the actual cause), root-caused via a puppeteer/chrome-headless-shell script loading the composed HTML directly and listening for `pageerror` · fix: document this failure mode explicitly (a thrown kinetic()/caption() call kills the WHOLE render's text layer, not just its own beat) so an editor doesn't waste a render cycle chasing the `sub_timeline_readiness_timeout` warning as if it were the cause — and consider whether `bl_compose.py` should wrap each per-beat script emission in its own try/catch so one bad line degrades gracefully instead of taking down every other beat's text.
- COSTLY [no owner] : each `bl_compose.py` render of a ~48s window took 12-13 minutes on this Contabo box's software-GL chrome-headless-shell — 3 of my 4 renders were spent re-discovering the same class of bug (line-width overflow) one render cycle at a time before I built a fast local validator. · evidence: task-fcd2b95d, render timestamps in RUNLOG.md (18:10-20:11 UTC for 4 renders + fix cycles) · prevented by: the `--no-render` dry-run compose + a 2-line Python check against `bl_checker.check_kinetic_overflow()` (or the puppeteer pageerror harness for the JS-throw case) catches both defect classes in under 5 seconds; worth adding as a documented pre-render step in the skill, or as a `bl_compose.py --check-only` flag, so no future editor burns a 12-minute render to discover either.
