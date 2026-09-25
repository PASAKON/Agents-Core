# REPORT task-1a5eb073

## Summary
Cut BLACK LIQUIDITY EP57 (all 40 lines, 0.0-153.0333s) as Arm 1 of the
split-editor A/B (`docs/ops/bl-split-ab-2026-09-25/BRIEF-arm1.md`) — one
editor, one pass, whole episode. Final render (1080x1920, 30fps, h264+aac,
153.0s, 25.5MB) is at `/opt/MoonieXHQ/Work/bl-split-ep57/arm1/final-arm1.mp4`
(outside the worktree, not in git, per the brief). Ran the Jev loop alongside
the cut: copied the CTO's pre-frozen `decisions.base.jsonl`, then recorded my
own editorial call against every one of its 199 rows (`jev_edit.py final`).

## Beats
40 lines, mode split: **EVID 15 · KIN 15 · COMP 5 · FF 5**. One line per beat
below (tag, mode, why).

- HOOK-1 (0.18-2.64) COMP wikifx-profile-score.png — name+logo card, avatar visible for the opening line
- HOOK-2 (3.08-5.54) FF — avatar, no capture named
- HOOK-3 (5.54-7.38) EVID xxlmarkets-direct-visit-error.png — full-page browser error, needs full width
- HOOK-4 (7.82-10.86) EVID third-party/wikifx-xxlmarkets-review.jpg (credit) — branded evidence card, logo+name crop
- PATTERN-1 (11.4-17.86) EVID wikifx-profile-website-inaccessible.png — company-profile paragraph, needs full width
- PATTERN-2 (18.48-22.42) EVID xxlmarkets-direct-visit-error.png — full-page error (repeat)
- PATTERN-3 (22.8-27.78) EVID xxlmarkets-www-visit-error.png — full-page error, www variant
- PATTERN-4 (28.26-30.78) EVID xxlmarkets-www-visit-error.png — same result, repeated
- CONTEXT-1 (31.3-35.44) **KIN** — no image named; also lands in an avatar dead zone (see Issues)
- CONTEXT-2 (36.12-38.86) **KIN** — same
- CONTEXT-3 (39.66-43.16) EVID whois-no-match.png — "no WHOIS record" result block
- CONTEXT-4 (43.9-47.72) EVID whois-no-match.png — "4 historical snapshots" banner
- CONTEXT-5 (48.5-54.22) EVID whois-domain-history.jpg — snapshot-count card (landscape still, letterboxed)
- MAIN-1 (54.84-58.3) **KIN** — dead zone, highlight "วิกิเอฟเอ็กซ์"
- MAIN-2 (58.3-61.84) EVID wikifx-profile-website-inaccessible.png — the Note line, highlight "วิกิเอฟเอ็กซ์"
- MAIN-3 (62.32-65.44) **KIN** — dead zone, highlight "วิกิเอฟเอ็กซ์"
- MAIN-4 (66.12-68.32) **KIN** — dead zone (2.18s short of lip_b's window)
- MAIN-5 (69.04-70.88) COMP wikifx-profile-no-license.png — license card, avatar visible
- MAIN-6 (71.44-73.08) FF — avatar
- MAIN-7 (73.32-76.06) COMP wikifx-profile-no-regulation.png — regulation stamp
- MAIN-8 (76.36-79.92) COMP wikifx-profile-score.png — score box (Jev auto-applied bl.beat @0.98)
- MAIN-9 (80.26-83.08) COMP wikifx-profile-score.png — header line (UK/2-5yr), tight crop (source image clips at its own right edge)
- MAIN-10 (83.4-86.58) EVID wikifx-profile-warning-banner.png — banner line 1 (past lip_b's real window, see Issues)
- MAIN-11 (86.84-88.86) EVID wikifx-profile-warning-banner.png — banner line 2
- MAIN-12 (89.32-93.24) EVID fca-register-search-spinner.jpg — FCA site state, landscape letterboxed
- MAIN-13 (93.64-97.2) **KIN** — dead zone
- CURIOSITY-1 (97.64-100.16) EVID third-party/wikifx-xxlmarkets-review.jpg (credit) — headline crop, past lip_c's window
- CURIOSITY-2 (100.6-104.28) EVID third-party/wikifx-xxlmarkets-review.jpg (credit) — subscore radar crop
- CURIOSITY-3 (104.74-108.24) **KIN** — dead zone, highlight "วิกิเอฟเอ็กซ์"
- CURIOSITY-4 (108.24-114.22) **KIN** — dead zone, highlight "วิกิเอฟเอ็กซ์"
- CURIOSITY-5 (114.22-117.74) **KIN** — dead zone
- SUMMARY-1 (118.2-119.32) **KIN** — dead zone
- SUMMARY-2 (119.76-125.02) **KIN** — dead zone
- SUMMARY-3 (125.4-128.96) **KIN** — dead zone
- SUMMARY-4/5/6 (129.38-141.02) KIN x3 — checklist card 1/3-3/3, no real footage per the brief; highlight "วิกิเอฟเอ็กซ์" on 3/3
- SUMMARY-7 (141.48-145.64) FF — avatar (lip_c window)
- SUMMARY-8 (146.08-150.5) FF — avatar, CTA
- SUMMARY-9 (150.8-152.64) FF — avatar, close

## Assets Used
- `real/*.png` (8), `real/*.jpg` (2) — first-party captures, no credit (per `real/` vs `third-party/` convention in the brief's mode notes)
- `third-party/wikifx-xxlmarkets-review.jpg` — WikiFX's own branded card, credited `ขอบคุณภาพจาก WikiFX` on every beat that uses it (HOOK-4, CURIOSITY-1, CURIOSITY-2)
- `media/broll/S14.mp4`, `S26.mp4`, `S31.mp4` — **not used**. No line in `SCRIPT.tsv` names a broll shot, and the SUMMARY-4/5/6 checklist cards are explicitly "no real footage" in the brief, so all 15 KIN beats render text-over-standing-background with no broll plate.
- `lip_a.mp4`/`lip_b.mp4`/`lip_c.mp4` + mattes — avatar footage, used only where the technical constraint below allows.

## Brand / Judgment Calls
- **Avatar footage only covers 3 narrow windows** — this drove most of the mode decisions. `build_cut.py`'s `pick_lip()`/`lip_offset()` map absolute episode time to one of three short takes (`lip_a` valid ~[0,14.9), `lip_b` valid ~[68.3,83.0), `lip_c` valid ~[137.2,152.5)); any FF/COMP beat outside those windows computes a negative or overflowing `media_start` and hyperframes refuses to render it (`VIDEO_SOURCE_UNRENDERABLE`, confirmed against the real box, not guessed). My first beats.json draft put FF on every no-image verdict/hook line by the brief's own convention rule and failed to render for exactly this reason. Fix: the 12 no-image lines that fall in the two dead zones (15.5-68.3s and 83.0-137.2s) became KIN (kinetic text, the same treatment the brief already specifies for SUMMARY-4/5/6) instead of FF; 4 near-miss COMP lines with real images (MAIN-10, MAIN-11, CURIOSITY-1, CURIOSITY-2) became EVID instead, since dropping the avatar composite there is free. Net effect: 15 of 40 beats are KIN rather than the ~3 the brief's checklist-card carve-out implies — a real technical constraint, not an editorial preference, and worth the CTO's attention if it should be fixed at the fixture level (record wider avatar takes) rather than absorbed by the editor every time.
- **HOOK-1 opens on COMP, not the FF a bare hook/verdict convention would suggest** — line 1 needs to establish WHICH broker (CEO's own note in SCRIPT.tsv) while still opening on the host's face, so I read it as a `show` line where the avatar staying visible matters (per the brief's own convention text) rather than a plain hook.
- **MAIN-9's box is unusually narrow (320x50px)** — the underlying screenshot (`wikifx-profile-score.png`) itself clips its own right edge at x=1080 (the "🇬🇧 สหราชอาณาจักร | 2-5 ปี" line runs off-frame in the source capture), and the safe-area gate caps any box at x+w<=1026, so the spotlight can only outline what's actually on screen and in-bounds — a defect in the source capture, not something I can crop around.
- **Highlight words** applied via `<span class="n">` inside `cap`/kinetic text wherever Jev's `bl.highlight_word` named "WikiFX" or "XXLMARKETS" at reasonable confidence and the word was genuinely in that line's text (HOOK-4, PATTERN-1, PATTERN-3 [www+https], MAIN-1, MAIN-2, MAIN-3, CURIOSITY-1, CURIOSITY-3, CURIOSITY-4, SUMMARY-6).
- **Real-vs-third-party credit rule**: only `third-party/wikifx-xxlmarkets-review.jpg` gets the `ขอบคุณภาพจาก WikiFX` credit chip. The 10 `real/*` stills are first-party captures of WikiFX's/who.is's/FCA's public pages, not WikiFX-supplied assets, so no credit per the brief's own COMP/EVID field description.

## Jev scoreboard (all 199 rows, `prototypes/bl-split-ep57/arm1/decisions.jsonl`)
- `bl.beat` (the only site with a measured gate, th @0.95): **39/40 agreed** with Jev's own answer; the one disagreement (CURIOSITY-3, Jev said `show` @0.46, I cut it `verdict` per `SCRIPT.tsv`'s own beat column) was below gate, editor decides per the skill's own rule.
- `applied_by`: **1 `jev`** (MAIN-8's `bl.beat`, the only row at/above the 0.95 gate) · **198 `editor`**.
- **`jev_wrong_at_gate` = 0** — the safety metric the skill's pass/fail hinges on stayed clean.
- `bl.focus_target` (16 rows, only asked where Jev had *some* candidate geometry despite the brief's expectation that this site would be fully skipped without a manifest): I matched Jev's own candidate label on 5/16 (CONTEXT-5, MAIN-2, MAIN-5, MAIN-11, CURIOSITY-2) where its box genuinely overlapped mine; the other 11 got `other` — several because the candidate cited the **wrong source image entirely** (PATTERN-1's and PATTERN-3's `bl.focus_target` candidates point at `xxlmarkets-direct-visit-error.png`/`xxlmarkets-www-visit-error.png`, not the still those lines actually use), a real defect worth flagging to whoever owns the Jev prompt for that site.
- `bl.text_slot` (40 rows): structurally can't be applied to FF/COMP/EVID beats — the template's `caption()` is one fixed band for every mode by the CEO's own 2026-09-25 ruling (task-1678d38e), so there is no per-line slot to pick; recorded `other` for those 25 rows and note it below. For the 15 KIN beats I mapped my own `top` choice to whichever candidate slot's `y` was closest.
- `bl.entry`/`bl.focus_device`: accepted Jev's own `bl.entry` suggestion as-is (this beats.json schema has no per-line transition-style field to express an independent choice); `bl.focus_device` final = `spotlight` wherever I actually drew a box, `none` otherwise.

## What made a call hard
- The source-truncation defect on `wikifx-profile-score.png`/`wikifx-profile-no-license.png`/etc. (screenshots clipped at their own right edge) repeatedly limited how tight a spotlight box could be without also cutting off the very text it's supposed to highlight.
- `wikifx-profile-website-inaccessible.png`'s SCRIPT.tsv note for MAIN-2 says "avatar+username censored" but no such element is visible anywhere in that capture — I cropped the visible "Note:" paragraph instead and flagged the mismatch rather than guessing at a region that isn't there.
- The avatar-footage dead zones (above) were the single biggest structural surprise — not decided in the source material at all, discovered only by attempting a real render.

## Checker verdict
`tools/bl_checker.py --video final-arm1.mp4 --beats beats.json --composition build/index.html`:
```
out_of_safe_area: []
text_over_face: []
credit_missing: []
extra_caption_styles: []
empty_frames: 15 frames in 5 clusters of 3 (~0.1s each) at 31.33-31.40 / 54.87-54.93 / 62.37-62.43 / 93.67-93.73 / 104.77-104.83
```
Root-caused by pulling the exact frame at 31.35s and looking at it: every cluster is a boxed EVID beat cutting straight into a boxless KIN beat. The shared template's `spotlight()` fades out over 0.18s starting 0.1s before the beat's own end, but the evidence `<img>` plate is a hard cut at that same instant (video plates don't fade) — so for ~0.1-0.17s the KIN beat's dark standing background shows with only the *previous* beat's spotlight box still fading out on nothing. This is a real, visible artifact (confirmed by eye, not just the checker's std-threshold), but it's a property of the fixed template's `spotlight()`/plate-cut timing (spotlight always inherits the beat's own `t0`/`t1`, `beats.json` has no independent fade-duration field) interacting with the avatar-dead-zone KIN fallback above — not something fixable from beats.json without either editing the shared kit (off-limits) or dropping the box from otherwise editorially-important EVID beats (CONTEXT-5's "4 snapshots" counter, MAIN-2/MAIN-12/CURIOSITY-2's specific evidence). Did not re-render to chase this, per the brief's own "fix what a real editor would obviously catch... don't loop chasing a clean checker past that" — 0.85s total across a 153s episode, all five instances the same root cause, all other checker categories clean.

## Files Changed
- `prototypes/bl-split-ep57/arm1/beats.json` — 40-beat composition (new)
- `prototypes/bl-split-ep57/arm1/decisions.jsonl` — Jev's 199 base rows + my 199 `final` calls (new)
- `prototypes/bl-split-ep57/arm1/final_calls.tsv` — the bulk `jev_edit.py final --tsv` input, kept for the record (new)
- `prototypes/bl-split-ep57/arm1/render-meta.json` — final-arm1.mp4's path/size/duration/fps (new)
- `RUNLOG.md` — append-as-you-go step log (new)

Not in git (per the brief): `/opt/MoonieXHQ/Work/bl-split-ep57/arm1/final-arm1.mp4` (25.5MB, left at that path for pickup) and `/opt/MoonieXHQ/Work/bl-split-ep57/arm1/build/` (scratch render workdir).

## Commits
- `0034f4d7` — video(bl-split-arm1): EP57 whole-episode beats.json + Jev decisions
- (final commit with RUNLOG/render-meta/REPORT — see `git log`)

## Tests
- ran: `tools/bl_checker.py --video final-arm1.mp4 --beats beats.json --composition build/index.html` — see Checker verdict above (fails on `empty_frames` only, explained and accepted; all other gates pass)
- No unit-test suite applies to a content/editorial deliverable; `bl_compose.py`'s/`bl_checker.py`'s own `tests/test_bl_*.py` weren't touched and weren't re-run (no code changes to those tools).

## Issues / Blockers
- **Tool bug found (not fixed in tool source)**: this appears to be the first real end-to-end render of `bl_compose.py` against the actual EP57 fixture (task-99f3d2e8's own RUNLOG confirms they never ran one). `assemble.py` hardcodes the composed `<audio>` element's `src` to `media/voice.mp3`, which does not exist in this generator-dir (only `audio-hq.mp3` does, at the generator root, not under `media/`). `hyperframes@0.8.40 render` treats that as a hard-blocking `audio_processing_failed` correctness warning even under its own default `--best-effort=true`, refusing to render at all rather than producing video-only output. Worked around it **without editing `build_cut.py`/`assemble.py`/`bl_compose.py`**: after `bl_compose.compose()` writes the composed `index.html` into the scratch out-dir, I copied the real `audio-hq.mp3` into that same disposable out-dir and patched only that generated file's `<audio src="...">` before calling `bl_compose.render()`; the actual audio track that ends up in `final-arm1.mp4` is still muxed from the master track by `bl_compose.mux_audio()` exactly as the tool always does, so this patch only unblocks the renderer's internal placeholder, it doesn't change what audio ships. The CTO should decide whether to fix this properly in `assemble.py` (point the placeholder at whatever file is actually there, or make hyperframes' best-effort mode actually tolerate a missing audio source) — see `RUNLOG.md` for the exact repro.
- **Avatar footage dead-zone constraint** (see Brand/Judgment Calls above) — 15 of 40 beats are KIN rather than FF/COMP because the recorded avatar takes only cover ~15s + ~15s + ~15s of the 153s episode. If the CEO/CTO would rather have more avatar presence through the middle of the episode, that needs wider avatar takes recorded for `lip_b`, not a beats.json change.
- **5 checker-flagged empty-frame clusters** (~0.1s each, template timing artifact) — see Checker verdict above. Accepted, not fixed, per the brief's own guidance not to chase a clean checker past what a real editor would obviously catch.
- Did not run `jev plan`/`freeze` per the CTO's explicit override (already done by the CTO 2026-09-23).

## Notes for Reviewer
- `final-arm1.mp4` and the composed `build/index.html` are at `/opt/MoonieXHQ/Work/bl-split-ep57/arm1/` for pickup, matching the brief's delivery path.
- The audio-placeholder tool bug (above) will hit **every** Arm-2 segment editor too, since they use the same `bl_compose.py`/`assemble.py`/generator-dir — worth fixing once at the tool level before those segments render, rather than each segment editor rediscovering and independently working around it.
- The `bl.focus_target` source-image mismatches (PATTERN-1, PATTERN-3) are worth a look by whoever owns the Jev prompt for that site — they're not just low-confidence, they're pointing at the wrong still entirely.

## Skill learning
- WRONG [VIDEO_EDITOR_jev-editor-helper §bl.focus_target] : Jev's PATTERN-1 and PATTERN-3 `bl.focus_target` candidates cite `xxlmarkets-direct-visit-error.png`/`xxlmarkets-www-visit-error.png` — the wrong still entirely (those lines use `wikifx-profile-website-inaccessible.png` and the www-error image respectively) · evidence: task-1a5eb073, `prototypes/bl-split-ep57/arm1/decisions.jsonl` line_id=PATTERN-1/PATTERN-3 · fix: audit whatever heuristic computes `bl.focus_target` candidates without a manifest — it appears to attach a generic "full-page error" box template to `show` lines regardless of which still that line actually names.
- MISSING [VIDEO_EDITOR_jev-editor-helper §bl.text_slot] : this site asks a per-line text-position question on every one of the 40 lines, but the template's `caption()` (task-1678d38e, CEO's one-caption-style ruling) is a single fixed band for every mode — there is no per-line slot to actually pick for FF/COMP/EVID beats, only for KIN's own `top` parameter · evidence: task-1a5eb073, 25/40 `bl.text_slot` rows recorded `other` for exactly this reason · fix: either scope `bl.text_slot` to KIN-only in the plan step, or document in the skill that its answer is advisory-only outside KIN beats.
- MISSING [reel-editor-th or blackliquidity-cut, whichever owns bl_compose.py/build_cut.py §avatar footage windows] : `build_cut.py`'s `pick_lip()`/`lip_offset()` only cover 3 narrow recorded avatar windows out of a 153s episode ([0,14.9), [68.3,83.0), [137.2,152.5)); any FF/COMP beat outside them fails render with `VIDEO_SOURCE_UNRENDERABLE`/`media_start_out_of_range` rather than a clear upfront error naming the valid windows · evidence: task-1a5eb073, first render attempt, 12 beats affected · fix: either document the valid windows in the brief/skill so editors plan avatar beats around them from the start (saves a wasted render cycle), or have `bl_compose.py` validate this before spending 60s+ on video extraction and fail fast with a clear message naming which beats and which windows.
- COSTLY [no owner] : the `assemble.py`-hardcoded `media/voice.mp3` placeholder vs. the real `audio-hq.mp3` cost one full failed render cycle (~70s) plus a second failed attempt before the working fix (copy the real file into the out-dir, patch the composed HTML's `src`) · evidence: task-1a5eb073, RUNLOG.md render-attempt entries · prevented by: `bl_compose.py`'s `build_render_workdir()` could symlink the generator's actual audio file to `media/voice.mp3` (or whatever the template's placeholder name is) alongside the existing `media/` symlink, so every future render of this fixture works without a per-editor patch.
