# BL EP57 (XXLMARKETS) — cut RUNLOG (task-501f1d89)

2026-09-24T00:02 — Read skills (jev-ops helper, blackliquidity-cut, mooniex-video-editor).
Ran `jev_edit.py plan` on SCRIPT.tsv + REAL_MANIFEST.json, `--state-lang=th`: 40 lines,
199 rows, $0.006006 spent (cap $0.02). Froze immediately per rule before reading the storyboard.

2026-09-24T00:15 — Reviewed decisions.jsonl against script/manifest. Only 1 row cleared the
measured 0.95 gate (bl.beat, MAIN-8, correct). Editor-decided the other 198: accepted 161 Jev
hints as-is, overrode 4 (CURIOSITY-3 beat+entry, CURIOSITY-4 entry, SUMMARY-4 entry — all trace
to Jev's own ungated bl.beat guess for the preceding line, see UPSKILL.md). jev_wrong_at_gate = 0.
Bulk-applied via `final --tsv`, froze.

2026-09-24T00:15 — Downloaded Drive project (id 1Z7zdePteonqSIzpJtH01jilgKhwyp7lv): _MANIFEST.json,
audio-hq.mp3 (153.0s), lipsync_part_a/b/c.mp4, 40 S## scene clips list. Real footage (10 stills +
third-party WikiFX card) already staged in prototypes/bl57-realfootage from the script pass.

2026-09-24T00:16 — `bl_tools.py offsets`: A=0.00s r=1.000, B=68.30s r=1.000, C=137.16s r=0.999 —
filenames were correct this episode (unlike BL51).

2026-09-24T00:17 — Transcribed voice track (mlx-whisper large-v3-turbo, th). First pass silently
dropped ~17s of real speech (89-108s) into one corrupted segment — a known whisper artifact, not
a real gap (confirmed via silencedetect: only normal <0.6s pauses in that window). Re-transcribed
that window in isolation and spliced the recovered text back in. Verified every line's timing
against the transcript text directly (not a blind algorithm) — see timings.tsv.

2026-09-24T00:20 — Sampled 3 of the 40 S## scene clips (S14, S26, S31) before trusting them:
S14 = money-wallet B-roll (not avatar, despite has_character:true in the manifest), S26 = avatar
gesture, mouth CLOSED (safe cutaway per the catalogue-AV precedent), S31 = abstract particle
B-roll. Confirms the manifest's has_character flag is unreliable — judged each clip by eye instead
of trusting it. Used all 3 as verified-safe B-roll behind kinetic text (MAIN-1, MAIN-13,
CURIOSITY-5); every other no-footage/no-lipsync line got a plain kinetic block, matching BL51's
own precedent (61% text-only is normal, not a shortfall).

2026-09-24T00:22 — Built the beat table (40 lines → composite/full-frame/evidence/kinetic/graphic-
checklist), matted lipsync_part_a/b (RVM, ~3 min each in parallel, clean edges). Wrote
tmp/build_cut.py + tmp/assemble.py to generate the HyperFrames composition from the table
mechanically (still hand-authored content/timing/judgment; the generator only assembles the
markup) rather than hand-typing 40 blocks.

2026-09-24T00:24-00:38 — `npm run check` + `bl_tools.py safezone`: clean after two real bugs found
and fixed — (1) `.clip`'s `inset:0` over-constrained my inline `top` override for shifted real-
footage plates (CSS bottom+height both set = wrong position); fixed with `bottom:auto;right:auto`.
(2) the yellow evidence spotlight boxes never faded out, so every one of them stayed on screen and
stacked for the rest of the episode — fixed by adding the missing hide() call.

2026-09-24T00:38-01:05 — Rendered. First attempt failed outright: avatar-comp `data-media-start`
used absolute episode time instead of the lipsync part's own relative offset (worked for part A
only, since its offset is 0) — 8 sources `media_start_out_of_range`. Fixed by computing
`media_start = abs_t0 - lip_offset(part)` everywhere, plus clamping avatar duration to each part's
real measured length so no beat reads past its source's last frame.

2026-09-24T01:03-01:23 — Full-episode render (153s, 4590 frames) stalled 3 times at frame ~2470-
2484/4590 ("no frame progress for 60000ms"), system RAM down to 84-193MB free from other sessions
on this shared Mac (confirmed via `top`, not a composition bug — check/safezone/verify all pass on
the source). Told the CTO (dev_message) rather than blind-retrying a 4th time.

2026-09-24T01:23-01:45 — Split-render workaround: parameterized build_cut.py/assemble.py to emit
a windowed sub-composition (absolute times kept for lip-offset/media-start math, shifted only for
the composition-local clock). Split at 76.36s (a clean beat boundary). Both halves rendered clean
on the first try (fresh Chrome each, well under the stall's frame-2470 ceiling). Concatenated
video-only (stream copy) and muxed against the single master audio track directly — avoids the
AAC-frame-boundary drift a naive two-segment audio concat introduced (first attempt: lipsync B
r=0.807 FAIL; fixed to r=0.987 ok).

Two visual defects caught only by reading full-resolution frames (not by any gate) and fixed
before delivery:
- MAIN-8: the fixed-y caption chip sat directly over the WikiFX "1.99/10" score — the exact HARD-
  rule shape the skill's own field notes warned about ("the fix can recreate the bug one level
  up"). Fixed: caption Y is now computed per composite beat from the evidence box's own position
  (above it, or below it if that gap is bigger; dropped entirely if neither clears both the box
  and the avatar — matches the skill's stated precedent, not needed in practice here).
- The split render replayed the brand-bug's slide-in entrance at the start of window B — the logo
  visibly blinked out and back in at 76.36s. Fixed: a continuation window sets `#bug` fully visible
  at local t=0 instead of animating it in a second time.

2026-09-24T01:45 — `bl_tools.py verify` PASSED: 1080x1920@30, 4590 frames, 153.00s, -15.4 LUFS
(target -14 ±2), all three lipsync seatings lag 0ms / r 0.98-0.99. Read a 4×5 full-resolution
contact sheet across the whole episode plus targeted crops (MAIN-8 evidence, HOOK-3 caption
clearance, the 76.36s seam) — clean.

Delivered: $WORK_DIR/out/BL-EP57-final.mp4, BL-EP57-preview-540p.mp4.
Also wrote prototypes/bl-jev-scoreboard/ep57/timings.tsv and UPSKILL.md.
