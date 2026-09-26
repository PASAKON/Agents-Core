# REPORT task-ea50d556

## Summary

Cut the whole BLACK LIQUIDITY EP57 episode (0–153.0333s, all 40 lines)
under the Arm 1 route (`docs/ops/bl-split-ab-2026-09-25/BRIEF-arm1.md`,
CTO overrides applied), delivered as `arm1b` (re-run of the pilot's
route, do not confuse with `arm1/`). `beats.json` was authored by hand,
one beat per line, deciding FF/COMP/EVID/KIN per line from the actual
stills and the recorded avatar windows — never guessed. The episode
rendered clean on the 5th render *strategy* (8th literal attempt, see
Issues/Blockers) and passes `bl_checker.py` on all 6 checks.

Final deliverable: `/opt/MoonieXHQ/Work/bl-split-ep57/arm1b/final-arm1b.mp4`
(1080x1920, 30fps, h264/aac, 153.0s, 50.16MB) — left outside the
worktree per the brief, not committed to git.

## Beats — mode breakdown and judgment calls

40 lines: **15 EVID, 15 KIN, 5 FF, 5 COMP.**

Avatar footage only exists in three narrow windows (`lip_a` t0∈[0,14.9),
`lip_b` t0∈[68.3,82.95), `lip_c` t0∈[137.16,152.51)) — 14 of the 40
lines fall inside a window, 26 don't. That constraint, not the writer's
own beat label, is what actually decided FF/COMP vs EVID/KIN:

- **FF (5):** HOOK-2, MAIN-6, SUMMARY-7/8/9 — all inside a window, all
  "hook/verdict/cta" lines with no still to show.
- **COMP (5):** PATTERN-1, MAIN-5/7/8/9 — inside a window, "show" lines
  where the avatar staying visible matters (evidence + presenter in
  frame together).
- **EVID (15):** HOOK-1/3/4, PATTERN-2/3/4, CONTEXT-3/4/5, MAIN-2/10/11/12,
  CURIOSITY-1/2 — all "show" lines with a real still, most of them
  outside every avatar window so the avatar is off-screen regardless.
- **KIN (15):** CONTEXT-1/2, MAIN-1/3/4/13, CURIOSITY-3/4/5, SUMMARY-1–6
  — "verdict"/transition lines with no still AND outside every avatar
  window (so FF isn't available either), plus the three SUMMARY-4/5/6
  checklist cards. One deliberate call: **SUMMARY-6 falls inside the
  `lip_c` window** (t0=137.86) but I kept it KIN anyway, to match
  SUMMARY-4/5's "1/3, 2/3, 3/3" graphic-checklist look — breaking that
  visual consistency for one avatar frame would read as a mistake, not
  a feature.

Hardest calls in the source material:
- Two "real capture" stills (`wikifx-profile-score.png` and
  `wikifx-profile-no-regulation.png`) turned out to be visually
  near-identical layouts (same badge/score/license card), while a third
  (`wikifx-profile-warning-banner.png`) that *looks* like the same page
  is actually a **different-scale capture** of it — same 1080x1920
  dims, more content per pixel. I built MAIN-10/11's spotlight boxes
  against the wrong one first (see Issues/Blockers) before catching it
  in frame QC.
- Several "real capture" stills are themselves truncated at the image's
  own right edge (e.g. `wikifx-profile-score.png`'s "🇬🇧 สหราชอาณาจักร |
  2-5ปี" line cuts off mid-word) — MAIN-9's spotlight box is narrower
  than I'd like as a result; that's the source, not something I can fix
  without a new capture.

## Assets used

Real-footage stills (`media/real/`, no credit needed): wikifx-profile-score.png (×3:
HOOK-1, MAIN-8, MAIN-9), xxlmarkets-direct-visit-error.png (×2), xxlmarkets-www-visit-error.png
(×2), wikifx-profile-website-inaccessible.png (×2: PATTERN-1, MAIN-2),
whois-no-match.png (×2), whois-domain-history.jpg, wikifx-profile-no-license.png,
wikifx-profile-no-regulation.png, wikifx-profile-warning-banner.png (×2),
fca-register-search-spinner.jpg.

Third-party asset (`media/third-party/`, credited "ขอบคุณภาพจาก WikiFX" on
every use): wikifx-xxlmarkets-review.jpg (×3: HOOK-4, CURIOSITY-1/2, a
different crop each time — headline, then the score radar chart).

KIN beats used `bl_compose.py`'s own default (line N → `broll/S{N:02d}.mp4`,
darkened) rather than naming a plate explicitly — none of the 40 broll
clips have content descriptions in this fixture, so I let the tool's
1:1 line mapping pick rather than guess a better one.

No real footage was invented or fabricated; every EVID/COMP `img` and
`box` points at an actual pixel region of a real still, verified with
`ffmpeg drawbox` against the source file before every render (see
Issues/Blockers — this caught two real placement bugs the checker's
own `out_of_safe_area`/`kinetic_overflow` checks could not see, since
neither checks *content correctness*, only geometry/sizing).

## Jev scoreboard — my `final` vs Jev's `choice`

165/199 rows got a `final` (34 legitimately `skipped` — no
`REAL_MANIFEST` for `bl.focus_target`, no number/word/brand candidate
for `bl.highlight_word` — left alone per the skill's rule 6, never
guessed):

| question | agree | disagree | note |
|---|---|---|---|
| `bl.beat` | 39/40 | 1 | I independently adopted the writer's own beat column for every line (I read all 40 and agreed with the writer's classification in every case) |
| `bl.highlight_word` | 11/11 | 0 | checked each of the 11 answered rows against the actual line text — Jev's brand/word candidate is always the one the line names |
| `bl.entry` | 34/39 | 5 | computed independently from a full/composite transition model (bl.entry.yaml's own definition), not copied from Jev |
| `bl.focus_device` | 13/24 | 11 | mine: spotlight wherever I used a `box`, else `none` — Jev's answers skew toward `highlight_sweep`/`zoom_only` more often |
| `bl.focus_target` | 5/11 | 6 | Jev's own computed candidate boxes were wrong for 3 lines I checked by eye (PATTERN-1 pointed at a different image entirely; MAIN-7/MAIN-11 pointed at empty regions) — see Skill learning |
| `bl.text_slot` | 15/40 | 25 | the current render template has ONE fixed caption band (`caption()`), no positional A–F slot system at all — I answered `other` for every row, this site doesn't apply to this pipeline any more |

## Files Changed
- `prototypes/bl-split-ep57/arm1b/beats.json` — 40-beat authored plan
- `prototypes/bl-split-ep57/arm1b/decisions.jsonl` — Jev's frozen base + my `final` on 165 rows
- `prototypes/bl-split-ep57/arm1b/render-meta.json` — final render's path/size/duration/fps/codecs + checker result
- `RUNLOG.md` (new) — timestamped build log, every step including the render-failure investigation

## Commits
- `36a950c2` — final render succeeded, checker clean; render-meta.json
- `1e77c3e3` — fix MAIN-10/11 boxes (wrong coordinate space)
- `96aa48bf` — fix MAIN-9/10/11 spotlight targets
- `4585e20c` — fix checker findings (safe-area boxes, kinetic sizing)
- `39d088a6` — beats.json + jev decisions.jsonl finals

## Tests
- ran: `python3 tools/bl_checker.py --video final-arm1b.mp4 --beats beats.json --composition build/index.html`
- result: **pass=true** — `empty_frames: []`, `out_of_safe_area: []`, `text_over_face: []`,
  `credit_missing: []`, `extra_caption_styles: []`, `kinetic_overflow: []`
- manual QC: ~30 frames pulled across the whole episode and looked at
  directly (not just "it built") at every stage — caught the checker's
  2 real findings' root causes plus 2 content-accuracy bugs the checker
  cannot see (spotlight on the wrong text) before calling it done.

## Issues / Blockers

**Render reliability (resolved, but worth a CTO look):** the render
failed 4 times in a row at the *identical* frame (2364–2366/4591,
~78.8s into the episode, well inside a beat I never touched), even
after box load dropped from 5.16 to 1.37 between attempts — ruling out
simple shared-box contention as the sole cause. `hyperframes`' own
diagnostic on the eventual success run: *"Screenshot capture (slower):
BeginFrame did not run... Heavy compositions can stall on software
GL"* — this box has no GPU. Fixed by invoking `npx hyperframes@0.8.40
render` **directly** (not through `bl_compose.py`'s wrapper, which
hardcodes the command with no way to pass extra flags) with
`--workers 1 --low-memory-mode --protocol-timeout 600000`, against the
already-composed build dir. That succeeded clean through all 4591
frames in 31m19s. **I did not edit `bl_compose.py`** — this was an
invocation-level workaround, documented in `RUNLOG.md`. Worth a CTO
follow-up: `bl_compose.py`'s `render()` (tools/bl_compose.py:451)
hardcodes the `npx hyperframes` command with no flags at all, so every
other editor on this GPU-less shared box will likely hit the same
stall on a long/heavy composition. Exposing `--workers`/`--low-memory-mode`
as `bl_compose.py` CLI passthrough flags (or just defaulting to them)
would save the next editor 4 failed render cycles (~2 hours in this
session).

- none blocking delivery — the final mp4 exists, passes the checker,
  and the RUNLOG documents every retry.

## Notes for Reviewer

- The script (`SCRIPT.tsv`, shared by every Arm in this A/B, not
  something I wrote or could change) contains มึง/กู throughout and one
  mild swear ("แม่ง", HOOK-2) — copied verbatim into captions per the
  brief's own instruction ("SCRIPT.tsv's spelling, never the TTS
  spelling"). Flagging for awareness against the general no-crude-
  language rule, since this is the channel's established persona
  voice across the whole test, not something a single editor should
  unilaterally censor.
- `audio-hq.mp3` and `generator/media/voice.mp3` are byte-identical
  (same size, same 153.05s duration) — I took the CTO override's word
  that this is already the "โบร๊ก" re-voice rather than re-verifying by
  ear, since the override explicitly told me to and there was no
  independent way to confirm from the file alone.
- `prototypes/bl-split-ep57/arm1/` (the pilot) was never read or
  touched, per the brief.

## Skill learning
- MISSING [VIDEO_EDITOR_jev-editor-helper §Output format] : `bl.focus_target`'s computed `candidate_map` can point at a wrong or empty region — 3 of 11 answered rows (PATTERN-1, MAIN-7, MAIN-11) had a candidate box that, checked directly against the source image with `ffmpeg drawbox`, either targeted a different image entirely (PATTERN-1: candidate said `xxlmarkets-direct-visit-error.png`, the line is actually about `wikifx-profile-website-inaccessible.png`) or an empty/wrong region (MAIN-7/11) · evidence: task-ea50d556 RUNLOG.md, `decisions.jsonl` MAIN-7/MAIN-11/PATTERN-1 rows vs. the boxes I actually shipped · fix: don't trust `bl.focus_target`'s candidate box without a direct crop-and-verify against the named source image; the skill doc should say so explicitly since the CEO's "who decides" table already sends every focus_target answer to the editor (no measured gate), but doesn't warn that the *candidates offered* can themselves be wrong.
- WRONG [reel-editor-th or blackliquidity-cut, whichever owns real-footage sourcing §asset notes] : two same-dimension (1080x1920) "real capture" stills of nominally the same WikiFX page can be different-scale captures with non-transferable pixel coordinates — I built MAIN-10/11's spotlight box against `wikifx-profile-score.png`'s measured coordinates and it landed on empty page chrome in `wikifx-profile-warning-banner.png` (same dims, "zoomed out" capture, more content per pixel) · evidence: task-ea50d556 RUNLOG.md, commit `1e77c3e3` · fix: never reuse a measured crop box across two different image files, even when they look like the same page and share dimensions — always `ffmpeg drawbox`-verify against the actual file the beat names.
- COSTLY [bl_compose.py | no owner] : `render()` hardcodes `npx hyperframes@0.8.40 render -o <path>` with zero passthrough flags, so a GPU-less box's "BeginFrame did not run... stall on software GL" failure mode has no way to be worked around except by hand-invoking the underlying `npx hyperframes` command outside the tool · evidence: task-ea50d556 RUNLOG.md, 4 consecutive identical-frame stalls, fixed only by bypassing bl_compose.py's `render()` with `--workers 1 --low-memory-mode --protocol-timeout 600000` · prevented by: exposing those three flags (or a single `--low-resource` shortcut) on `bl_compose.py`'s own CLI.
