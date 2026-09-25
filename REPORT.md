# REPORT task-94eb699b

## Summary
Cut BLACK LIQUIDITY EP57 segment `seg02` — [39.3, 65.8333)s, tags CONTEXT-3..MAIN-3
— per `docs/ops/bl-split-ab-2026-09-25/segments.json`'s Arm 2 ("ช่วยกัน") split-editor
A/B. Rendered, checked (`bl_checker.py` pass), and delivered to
`/opt/MoonieXHQ/Work/bl-split-ep57/parts/seg02.mp4` +
`/opt/MoonieXHQ/Work/bl-split-ep57/compositions/seg02.html` for the CTO's merge.

## Beats
- 39.30–43.16s (local 0.00–4.60) EVID `real/whois-no-match.png` — CONTEXT-3, "we don't
  have a current record". Box narrowed to [54,830,972,150] to fit the checker's
  safe-area margins after the first render flagged it out-of-bounds at full width.
- 43.90–47.72s (local 4.60–9.00) EVID `real/whois-domain-history.jpg` — CONTEXT-4,
  reassigned from the SCRIPT.tsv-suggested `whois-no-match.png` (see Judgment Calls).
- 48.50–54.22s (local 9.00–15.54) EVID `real/whois-domain-history.jpg` — CONTEXT-5,
  tight zoom on "4 snapshots spanning 2022–2026". No caption (see Judgment Calls).
- 54.84–58.30s (local 15.54–19.00) KIN, darkened broll (auto S14.mp4) — MAIN-1,
  "กูเลยลองไปดูที่ WikiFX" / "เว็บที่เช็กโบรกทั่วโลก". Was planned as FF "avatar full
  frame" per the brief's own script note; became KIN (see Judgment Calls).
- 58.30–61.84s (local 19.00–22.94) EVID `real/wikifx-profile-website-inaccessible.png`
  — MAIN-2, WikiFX's own "Note:" disclosure, spotlight tight on that paragraph.
- 62.32–65.8333s (local 23.02–26.5333, held to segment end) KIN, darkened broll
  (auto S16.mp4) — MAIN-3, "แปลว่าไม่ใช่กูคนเดียว" / "WikiFX" / "ก็เจอเหมือนกัน" (3
  lines after splitting the original 2-line version for kinetic-width — see below).

Mode tally: 4 EVID, 2 KIN, 0 FF, 0 COMP. All 4 EVID beats are `show` lines with a
spotlight box; the 2 KIN beats are the segment's `verdict` lines, converted from the
originally-planned FF because no avatar footage exists anywhere in this window.

## Assets Used
- `real/whois-no-match.png` — from fixture `media/real/` (existing, `SCRIPT.tsv`-assigned).
- `real/whois-domain-history.jpg` — from fixture `media/real/` (existing; reassigned
  from `whois-no-match.png` for CONTEXT-4, kept for CONTEXT-5 as SCRIPT.tsv already had it).
- `real/wikifx-profile-website-inaccessible.png` — from fixture `media/real/` (existing,
  SCRIPT.tsv-assigned).
- `broll/S14.mp4`, `broll/S16.mp4` — from fixture `media/broll/`, auto-selected by
  `bl_compose.py`'s own `default_kin_broll()` (line-number match, no `broll` key set
  in my beats). Screened both by pulling a frame before accepting: S14 is a stylised
  wallet-losing-coins shot, S16 is abstract glass/light prisms — both generic, on-theme
  (financial loss / cold hard fact), neither makes a claim the line doesn't support.

## Brand / Judgment Calls
1. **Avatar windows don't reach this segment at all.** The brief's own avatar-window
   table (lip_a [0,14.9), lip_b [68.3,82.95), lip_c [137.16,152.51)) has zero overlap
   with [39.3,65.8333). MAIN-1 and MAIN-3 both carry the SCRIPT.tsv note "avatar full
   frame" (and Jev's `bl.beat`="verdict" at 0.80/0.81 confidence), which would normally
   mean FF — but `bl_compose.py`'s `check_avatar_window()` refuses any FF/COMP beat
   whose `t0` isn't inside one of those three windows, exactly as the brief warned.
   I converted both to KIN (kinetic text over a darkened broll plate) rather than
   burn a render finding this out empirically. `bl.beat`="verdict" stays my own final
   answer too (that's the line's narrative FUNCTION, unaffected by which render mode
   is technically available) — only the mode changed, not the content tag.
2. **CONTEXT-4 reassigned image.** SCRIPT.tsv's own shot column points CONTEXT-4 at
   `whois-no-match.png`, with its note quoting "4 historical WHOIS/RDAP snapshots ...
   from 2022 to 2026". That exact text is NOT legible in `whois-no-match.png` — the
   source screenshot's own capture width cuts it off mid-sentence at the frame's right
   edge (confirmed by cropping the region and reading it: line 1 reads "...but we hold
   4 historical WH[cut]", line 2 picks up mid-word at "2026. See its domain history.").
   `whois-domain-history.jpg` states the same fact cleanly and in full ("4 snapshots
   spanning 2022–2026"), and CONTEXT-5's own line — "หน้าเดียวกันนี้..." ("this SAME
   page...") — only makes sense if CONTEXT-4 is already on that page. I moved CONTEXT-4
   to `whois-domain-history.jpg` (a different box/crop than CONTEXT-5's tighter zoom,
   so the two lines still read as two distinct beats on the same page).
3. **CONTEXT-5 has no caption, by design.** Its evidence ("4 snapshots spanning
   2022–2026") sits, after the image's automatic letterbox placement (1374x868 source
   scaled into the 1080-wide canvas), at canvas y≈1252–1288 — inside the caption
   band's own span (`.caplayer{top:1300px}`, ±≈80–100px for one line of `.cap` text).
   Putting a caption there would print the dark caption chip directly over the exact
   number the spotlight is supposed to be selling. SKILL.md already documents this
   exact class of bug for COMP mode ("HARD — the avatar must never cover the evidence
   element", and its own follow-up note that the FIX can recreate the bug one level up
   when a relocated caption lands on the relocated evidence) — same failure, different
   pair of elements (EVID spotlight vs. caption band instead of avatar vs. evidence),
   same fix: drop the caption rather than force it in. The spoken line still reaches
   the viewer through the narration audio once the CTO muxes it at merge time.
4. **`bl.entry`: disagreed with Jev on 4 of 6 lines.** Jev proposed "shrink"/"other"
   entry styles for CONTEXT-3/4/5 and MAIN-2 at fairly high confidence (0.53–0.99).
   Reading `bl_compose.py`'s `emit_pieces()`, EVID/COMP/FF plates are plain
   `<video>`/`<img>` elements with only `data-start`/`data-duration` — no entry
   animation is ever called for the plate itself (only captions/spotlight/kinetic get
   `show()`/`hide()`/`wipe()`). Every plate in this fixed template hard-cuts in,
   mechanically, regardless of content. I recorded `final`="hard_cut" for all of
   CONTEXT-3/4/5/MAIN-2's `bl.entry`, matching MAIN-1/MAIN-3's own already-correct
   "hard_cut" (confidence 1.0). This is a measurable, checkable fact about the tool,
   not a subjective call — worth feeding back into Jev's training on this question.
5. **`bl.text_slot`: recorded "not applicable" for all 6 lines.** Jev's candidate
   boxes (A–F, y=252..1152) model an FF avatar layout's kinetic-text slot choices.
   None of my beats are FF; EVID's caption position is fixed at `top:1300px` by the
   template (no per-beat slot), and KIN's `kinetic()` call is hardcoded to `top:760`
   by `bl_compose.py` itself (not exposed in the `extra` schema). I recorded this
   explicitly rather than picking an arbitrary letter.
6. **`bl.focus_device`/`bl.focus_target`/`bl.highlight_word`:** mostly agreed with
   Jev where it proposed "spotlight"/candidate "A" (CONTEXT-5, MAIN-2's focus_target
   and focus_device both matched my own independently-drawn boxes almost exactly —
   Jev's CONTEXT-5 candidate A was [160,755,690,100], mine ended up [130,806,610,42],
   a tighter subset of the same region). Disagreed on CONTEXT-3/4 focus_device (Jev
   said "none", I used spotlight on both) and on MAIN-2's highlight_word (Jev proposed
   highlighting "WikiFX" inline inside the caption text; I left captions plain,
   matching the one established precedent in this repo — `docs/ops/bl-ab-2026-09-25/
   beats.json`'s captions are all plain SCRIPT.tsv text with no inline spans — since
   introducing per-line caption styling is the exact bug §6f exists to prevent).

## Issues / Blockers
- **Tool-level finding, not mine to fix:** `kinetic()`'s own exit has no lead time
  analogous to `SPOTLIGHT_EXIT_LEAD`. `emit_pieces()`'s KIN branch calls
  `kinetic(760, t0+0.05, t1, ...)` with `out=t1` (the exact hard-cut boundary), and
  `block()`'s `hide()` animates opacity 1→0 over a fixed 0.18s STARTING at `out` —
  so the outgoing kinetic text is still ~visible for up to 0.18s (≈5-6 frames)
  *after* the next beat's plate has already hard-cut in underneath it. I saw this by
  eye at the MAIN-1→MAIN-2 cut (local t=19.0–19.18, abs 58.3–58.48): MAIN-1's
  "กูเลยลองไปดูที่ WikiFX" kinetic text visibly ghosts over MAIN-2's fresh WikiFX
  screenshot + its own caption for a handful of frames. This is the exact bug class
  the `SPOTLIGHT_EXIT_LEAD=0.08` constant was already added to fix for `spotlight()`
  exits — never applied to `kinetic()`'s own exit. `bl_checker.py` has no check that
  would catch it (confirmed: `empty_frames`/`out_of_safe_area`/`text_over_face`/
  `credit_missing`/`extra_caption_styles`/`kinetic_overflow` — none of these look at
  cross-beat temporal overlap), so it ships silently clean on the checker. I did not
  patch `bl_compose.py` (out of scope per the task brief — tool bugs are the CTO's
  call). The fix, if wanted, is mechanically the same pattern as `SPOTLIGHT_EXIT_LEAD`:
  pass `t1 - KINETIC_EXIT_LEAD` (something in the ~0.18-0.26s range, high enough that
  `hide()`'s own 0.18s finishes at/before the true cut) as `kinetic()`'s own `out`.
  This only affects KIN→(anything) transitions; my segment has exactly one
  (MAIN-1→MAIN-2) inside its own boundaries — MAIN-3's own KIN exit lands at my
  segment's OUTER edge (65.8333s) where it should just hold, so it isn't visible
  within my own delivered clip, only at the seg02→seg03 join, which is the CTO's
  merge-time concern.
- The generator's `audio-hq.mp3` in this fixture is still the pre-splice voice per the
  brief's own caveat ("if the media there is still the pre-splice voice... say so").
  My segment renders video-only regardless (no `--audio` since `--t0`>0), so this had
  no effect on my output, but flagging per the brief's instruction.

## Notes for Reviewer (CMO/CTO)
- First plate's `t0` is set to the segment boundary 39.3s, not CONTEXT-3's own line
  t0 (39.66s) — the ~0.36s gap between them is the dead-air pocket the split algorithm
  cut through (seg01's own CONTEXT-2 plate already holds to 39.3s via its own
  hold-to-t_max rule). Setting CONTEXT-3's displayed t0 to 39.3s is what makes the
  segment's very first frame covered and the seg01↔seg02 join a true hard cut in the
  silence, per PLAN.md's segment contract ("the first starts at t0... no fade in/out
  at a segment edge"). `t1` in beats.json stays the verbatim timings.tsv value (43.16)
  since `bl_compose.py` never reads a beat's own `t1` (only `t0`, via hold-to-next).
- Please double check my CONTEXT-4 image reassignment (Judgment Call #2 above) against
  the other segments' editors' own CONTEXT lines if any of them also touch this image,
  since it's an editorial call, not a mechanical one.

## Tests
- ran: `python3 tools/bl_compose.py ... --no-render` (dry-run compose validation)
- ran: `flock /tmp/bl-render.lock python3 tools/bl_compose.py ...` (real render, twice
  — first render caught 2 defects, see below; second render clean)
- ran: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python tools/bl_checker.py --video ... --beats ... --composition ...`
  (host python had no numpy; used the repo's own `.venv` which does)
  - 1st render: `pass: false` — `out_of_safe_area: ["CONTEXT-3"]` (spotlight box used
    the full 0–1080 width, outside the checker's 5%-margin safe rect), `kinetic_overflow:
    ["MAIN-3: ~856px > 720px safe width"]` (the original 2-line MAIN-3 kinetic text
    was too wide at its authored font size, estimated statically — would have relied
    on the render-time auto-shrink, which the checker explicitly says not to lean on)
  - fixed both in beats.json (CONTEXT-3 box narrowed to fit the safe rect; MAIN-3 split
    into 3 shorter lines) and re-rendered
  - 2nd render: `pass: true`, all 6 sub-checks empty
- passed: 1 (bl_checker.py, 2nd render)
- failed: 0 (after fix; 1st render had 2 findings, both fixed before delivery)
- skipped: 0
- By-eye QC: pulled and read frames at local t=0.05, 2.3, 4.7, 7.0, 9.5, 12.0, 15.7,
  17.5, 19.1, 21.0, 24.0, 25.0, 26.4s on the final render. No black/empty frames;
  caption band and spotlight both readable in every EVID beat; kinetic text legible
  and correctly emphasized in both KIN beats; first plate covers t=0 of the segment;
  last plate (MAIN-3) still fully on screen at t=26.4 (segment ends at 26.5333),
  confirming the hold-to-segment-end rule; brand bug and legal label present and
  unobstructed throughout (both are baked into the fixture's own `index.html`, not
  something I control).
- `ffprobe`: 1080x1920, 30fps, h264, 795 frames (expected 796 from
  26.5333×30 exactly — within PLAN.md's merge-gate ±1 frame tolerance), video-only
  (no audio stream, correct for a `--t0`>0 range render).

## Skill learning
- WRONG [reel-editor-th | blackliquidity-cut — none, this is `bl_compose.py`'s own
  emission code, not a skill doc] : n/a — see MISSING below instead, this isn't a
  skill-doc correction, it's a tool-code gap.
- MISSING [blackliquidity-cut §HARD evidence-overlap rule] : the documented rule only
  names avatar-vs-evidence overlap (COMP mode). The SAME failure mode generalizes to
  caption-band-vs-spotlighted-evidence in EVID/COMP mode (fixed caption top:1300px can
  land on a still's own evidence box after image_placement's letterboxing, independent
  of any avatar). Worth a one-line addition noting the caption band itself is also a
  thing to check evidence boxes against, not just the avatar's fixed bottom-56% zone.
  · evidence: task-94eb699b, CONTEXT-5's box (canvas y≈1252-1288) vs `.caplayer{top:
  1300px}`'s own span; fixed by dropping CONTEXT-5's caption, confirmed clean by eye
  and by `bl_checker.py`.
- MISSING [blackliquidity-cut/reel-editor-th | no clear owner — this is `bl_compose.py`
  code, not a skill doc, but no skill currently tells an editor to expect it] : nothing
  in either skill's text told me `check_avatar_window()` would refuse FF/COMP outside
  the 3 lipsync windows — I only learned the exact windows from THIS task's own brief
  (which already explicitly warned about this, so this isn't a "the brief should have
  told me" gap — it did). Worth folding the general PRINCIPLE (a segment can land
  entirely outside every recorded avatar window, and every beat in it then MUST be
  EVID/KIN) into blackliquidity-cut's own SKILL.md so a future segment-split editor
  who doesn't get as explicit a brief still knows to check this before planning FF/COMP
  beats · evidence: task-94eb699b, seg02 = 100% EVID/KIN, zero FF/COMP possible.
- COSTLY [blackliquidity-cut — no owner] : the biggest single time cost was manually
  reading pixel coordinates off screenshots (cropping test regions, eyeballing box
  boundaries) since neither skill documents a faster way to find a UI element's
  bounding box in a static screenshot. A small script (crop-and-show at candidate
  coordinates, or an OCR-with-bounding-boxes pass) would speed this up materially for
  every future EVID/COMP box-picking task · prevented by: a `bl_tools.py` subcommand
  that takes an image + rough guess and prints/renders candidate boxes.
