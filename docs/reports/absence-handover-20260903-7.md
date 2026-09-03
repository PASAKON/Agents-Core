# Absence handover — 2026-09-03, session 7

Two Fix-1 fires, S2b split-screen (video-ref) then IV2b whip-pan restage, per
`task-63f182d9`. Both fired Unlimited, both filed to Drive regardless of
verdict, no verdict in either filename.

## 1. WHAT FIRED

| Block | Take | Result | Drive path | Duration/spec | Notes |
|---|---|---|---|---|---|
| S2b split-screen (phone call) | 1 | **PASS** | `All Scene/Fix-1/S2b-Fix1-Split.MP4` | 20.05s/1280x720/24fps | Clean split at 7s, exactly two halves throughout, no grid/quad-split defect |
| IV2b whip-pan restage (crew reveal) | 1 | **FLAGGED** | `All Scene/Fix-1/IV2b-Fix1.MP4` | 20.04s/1280x720/24fps | Camera-points-back joke lands clean; crew-reveal room does not match Dupe's house |

Both generated via Seedance 2.5, Unlimited Mode, 720p, 20s, High, Sound On —
struck-through-to-0 zoom-verified on the Generate button immediately before
every click. No real credits spent; no browser-tool error or timeout at any
point, so the hard-rule Usage-History check after an error was never
triggered.

### S2b-Fix1-Split — PASS, full reasoning

Staged per the brief: attached `docs/S2b-Split-Render.MP4` through the video
picker (verified `@Video 1` chip resolved, no red text — attach succeeded on
the first attempt, so the "STOP AND REPORT if it won't attach" branch never
triggered). Bound the three named Elements
(`@project_absence_char_cleaner_c`, `@project_absence_char_workman`,
`@project_absence_loc_hall_big_d`) — 4 chips total confirmed by direct DOM
read (all green/resolved, zero red text anywhere in the pasted prompt).
Duration slider driven from its default 5s to 20s via 15x `ArrowRight` on the
focused `role="slider"` element (per the higgsfield skill's documented
method — the visible "5s"/"20s" text is a read-only span, not a text
field), then re-verified via `aria-valuenow` before firing. All six fields
read back before the click: Seedance 2.5, 720p, 20s, 16:9 (default,
unchanged), High, Sound On, Unlimited toggled on.

Downloaded the finished clip directly from its CDN URL (the in-browser
preview player's `readyState` stayed 0/never loaded a frame — a UI glitch on
that panel, unrelated to the actual file, which HTTP-200'd cleanly at 24.2MB)
and inspected it with `ffprobe`/`ffmpeg` frame extraction instead of trusting
the stuck player:

- **1280x720, 20.05s, 24fps** — matches the previz spec and the locked
  20s/720p/Seedance 2.5/High/Sound On spec exactly.
- **0-6s**: single full frame, Dupe alone at the wall telephone, matching the
  prompt's pre-split beat.
- **7.5-18s**: clean split into exactly TWO halves, held through to the end.
  Left half: Dupe on the phone against the warm-cream museum wall, correct
  plate (`hall_big_d`'s top-left panel material only — cream walls, orange
  cove light, terrazzo floor). Right half: the contractor on a suspended
  plank, hi-vis harness, dark navy coveralls (not the older slate-blue),
  plastering — matches the CEO's 2026-09-03 revisions exactly.
- **No four-panel/grid/quad-split defect anywhere** — this was the one thing
  the brief specifically flagged as worth watching (first time binding
  `hall_big_d`'s four-panel sheet as a location reference), and it did not
  happen. The model correctly took only the material (walls/light/floor)
  from the grid sheet, never its own framing.

One minor, non-disqualifying note: Dupe stands close to but not fully
touching the telephone housing (prompt asked for "body almost touching the
wall") — a soft miss on the tightness the CEO wanted, not a hard-negative
violation, so I did not flag it. Filed as-is; the editor's call.

### IV2b-Fix1 — FLAGGED, full reasoning

Composer cleared and re-staged during S2b's render (per the "warm up the
next job during the wait" pattern): removed the S2b video-ref chip (this
prompt takes no video reference), cleared the prompt text, pasted the IV2b
prompt, re-verified the single Element chip
(`@project_absence_char_dupe_interview_house`) resolved green, re-verified
duration/quality/sound/Unlimited were all still intact after the composer
edit (720p/20s/High/On/Unlimited-$0, confirmed by DOM read, no re-drift).
Fired the moment S2b's card showed "New" with no processing state — the
render slot was never left idle.

Downloaded and frame-sampled the same way. **1280x720, 20.04s, 24fps** —
spec-correct.

Checked against the review criteria written into the prompt file's own
notes, not my own guess at what matters:

- **Dupe's locked frame at 0-7s and 10-20s: clean.** Confirmed by direct
  frame comparison (0s/6s/12s/18s pulled and eyeballed side by side) — no
  crew, no gear, no cable, no light stand in any of them, identical framing
  and composition throughout.
- **Camera visibly pointed back at Dupe inside the pan: yes, clearly.** The
  8.5s and 9.5s frames show a heavy-tripod cinema camera dead centre,
  pointed straight down the lens at the viewer — the exact composition the
  prompt asked for, and the joke reads instantly.
- **"The house still readable behind them" — NOT satisfied. This is the
  defect.** The crew-reveal frames (7.7s-10s) show a dark wood-panelled
  room with no windows, no daylight, no purple sunken seating, no visible
  connection at all to Dupe's retrofuturist house that frames every other
  shot. It reads as a bare soundstage/backstage space, which the prompt's
  own CRITICAL NEGATIVES list bans outright: *"no exterior, no studio, no
  soundstage, no bare walls, no location that is not his house."* This is
  not a borderline call — the negative is explicit and the frame matches it
  exactly.
- Secondary, non-disqualifying note: **4 crew members visible, not the
  scripted 3.** The review criteria explicitly says "the exact count of crew
  (2 or 3) is not worth a re-fire" — 4 sits just outside that stated
  tolerance, but since the criteria's own bright line is the camera pointing
  back (which passed), I read this as a note rather than the reason to flag.
  The room mismatch is why this is FLAGGED, not the count.

Filed as `IV2b-Fix1.MP4` per the naming rule — no verdict in the filename,
the verdict lives here and in `logs.txt`'s note field. `IV2-Fix1.MP4` (the
housekeeper version) is untouched, unreplaced, undeleted; the editor picks.

## 2. FILING

Both filed via `scripts/gdrive-bridge/ilag_mirror.py` against the existing
`All Scene/Fix-1/` folder (`1WBk3uts8UaJQwBZuLwWjTFf6mcCMoidc`), each upload
size-verified against a fresh Drive listing before the local staging copy
was deleted (S2b: 24.2 MB; IV2b: 12.4 MB). `logs.txt` ADD lines written for
both, verdict + reasoning in the note field. Local scratch copies
(`/tmp/s2b_check/`, `/tmp/iv2b_check/`) are outside the worktree and outside
Drive-staging, left as-is (frame JPEGs used for review, not deliverables).

## 3. MONEY

Two Unlimited video fires. Generate button zoom-verified struck-price-to-0
immediately before each click (S2b: `UNLIMITED · ~~440~~ · 0`; IV2b: same).
No live/unstruck price ever appeared. No browser-tool error or timeout at any
point in the session, so no Usage-History audit was triggered by the hard
rule — nothing to reconcile.

## 4. RENDER SLOT DISCIPLINE

S2b fired first, ~29.5 min render (Thai afternoon = Europe daytime per the
skill's timing table — slower window, consistent with the observed time).
IV2b was staged in full during that wait and fired the instant S2b's card
showed complete, so the account's one-generation-at-a-time slot was never
left idle. IV2b then took ~35 min to render (same slow-window explanation).

## 5. QUEUE POINTER

Both scripted fires for this task are complete. Nothing else was queued or
scripted for this session. If a re-fire of IV2b is wanted to fix the
crew-reveal room, the composer state (Seedance 2.5 / 720p / 20s / High /
Sound On / Unlimited) is known-good and documented above; the fix belongs in
the prompt's crew-reveal room description (name the house's own materials —
tall windows, warm wood, plum seating — explicitly in that beat rather than
leaving it to inherit from the plate alone, since Seedance clearly treated
the two rooms as independent scenes once the camera cut away from Dupe).

## Files Changed

- `docs/reports/absence-handover-20260903-7.md` — this report (new)

No prompt files, scripts, or other project files were edited. `git merge
main` at task start pulled in `beb1865` (the two new prompt files) — local
`main` already had it, only `origin/main`'s tracking ref was stale; merged
from local `main` instead of `origin/main`.

## Commits

(see below — this report + merge commit)

## Issues / Blockers

- **IV2b FLAGGED**: crew-reveal room doesn't match Dupe's house — see
  reasoning above. Not a re-fire I made unilaterally (per the review-loop
  doctrine, that's the CTO's/CEO's call), footage filed either way per the
  standing rule.
- **Minor note, not a blocker**: IV2b crew reveal shows 4 people, prompt
  scripted 3 — explicitly tolerated by the review criteria, noted for
  completeness only.
- **Minor note, not a blocker**: S2b's Dupe stands close to but not fully
  touching the telephone housing — softer than the prompt's "almost
  touching" direction, not a hard-negative violation.
- No hard stops hit. Unlimited toggle worked on the first clean click both
  times (no stuck-control escalation needed). No login walls, no instructions
  found embedded in page content, no unexpected NSFW/rights-verification
  banners on either clip.

## Notes for Reviewer

- Recommend opening both frames the CTO normally opens (t1 sheet / full-res
  on doubt) for IV2b's 8-10s window specifically — the room mismatch is
  visually obvious even at thumbnail size, but worth a second look before
  deciding whether to re-fire or accept the take as-is (editor's call,
  per the standing footage rule, applies either way).
- The in-browser preview player did not load either clip's video element
  (`readyState` stayed 0) even after the card showed "New"/complete. This
  looked like a stuck client-side player state (same class of issue the
  higgsfield-unlimited-gen skill documents for stale tabs), not a real
  processing problem — the CDN URLs served both files cleanly at full size
  immediately. Did not chase it further since downloading and inspecting the
  actual file bytes was faster and more reliable than fighting the player.

## SKILL-OVERRIDE

None. All HARD rules in `higgsfield-unlimited-gen` and `browser-operator`
followed as written this session — Rerun never used (Recreate/direct
attach/paste only), synthetic-paste-only text entry with the End→space→
Backspace bind-fix after every paste, duration driven via ArrowRight on the
slider (never typed), struck-to-zero zoom check before every Generate click,
one Unlimited video generation in flight at a time, next prompt staged
during the render wait rather than left idle.
