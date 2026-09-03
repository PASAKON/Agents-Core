# Absence handover — 2026-09-03/04, session 8

Two Fix-1 fires per `task-00bbc44d`: S2-Fix1 (the accident, video-ref) and
IV2b re-fire (whip-pan crew reveal, strengthened negatives). Merged local
`main` at task start to pick up commits `22fde5f`/`c74442a` (prompts +
previz), which had landed on local `main` but not yet on `origin/main`.

## 1. WHAT FIRED

| Block | Take | Result | Drive path | Duration/spec | Notes |
|---|---|---|---|---|---|
| S2-Fix1 (the accident, video-ref) | 1 | **REJECTED — no output** | none (nothing to file) | n/a | Higgsfield's own content filter rejected the generation outright: "Output may contain sensitive content. Try changing your inputs." No clip, no thumbnail, no player — total rejection, not a completed-but-flagged take. |
| IV2b-Fix1-take2 (crew reveal, re-fire) | 1 | **FLAGGED** | `All Scene/Fix-1/IV2b-Fix1-take2.MP4` | 20.04s/1280x720/24fps | Camera-points-back joke still lands clean; crew-reveal room still does not read as Dupe's house, same defect as take 1 despite the added negatives |

Both fired Seedance 2.5, Unlimited Mode, 720p, 20s, High, Sound On — zoom-
verified struck-through-to-0 on the Generate button immediately before every
click (`UNLIMITED · ~~140~~ · 0` both times).

### S2-Fix1 — REJECTED, full account

Staged exactly per the brief: uploaded `docs/S2Fix1-Render.MP4` through the
reference picker, confirmed `@Video 1` resolved in the mention dropdown (not
red), pasted the six-Element prompt from between the PASTE markers verbatim,
verified all seven `@project_absence_*`/`@loc_hall_big_e` mentions resolved
lime-green with count 1 each (no duplicates, no red text), drove the
duration slider from 5s to 20s via 15× `ArrowRight` on the focused
`role="slider"` (verified `aria-valuenow="20"`), and re-verified 720p/High/
Sound On/Unlimited-$0 immediately before firing.

**The Generate button came up disabled after everything was staged**, with
no visible error. This turned into the bulk of the session's time. Root
cause, confirmed by process of elimination:

1. First upload attempt: the reference panel showed a permanent verifying
   spinner that never cleared after 90+ seconds. Backend check
   (`fnf-api-gw.higgsfield.ai/fnf/assets/<id>/detail`) returned 404 "Asset
   not found" for that asset id even though the raw CDN file itself
   eventually resolved 200. Removed the stuck reference and re-uploaded
   through the Uploads-panel "Upload media" tile instead of the composer's
   inline `+`/file-input path — that one showed a normal "Uploading…" →
   "Checking.." → real-thumbnail sequence and worked cleanly.
2. Even after a clean, verified attach and all seven Elements resolved
   green, the Generate button stayed `disabled: true` (confirmed by reading
   the DOM property directly, not just the visual state — the button's
   `opacity-40` disabled styling reads as "still colorful" against the dark
   backdrop at a glance, so a screenshot alone would have missed it).
3. Toggling Unlimited off proved the composer itself was fine — priced mode
   showed a normal, clickable `GENERATE 80/45`. So the block was specific to
   Unlimited mode, not the form.
4. Tested the "one Unlimited generation at a time" hypothesis by opening a
   **completely fresh tab** with no prior interaction: Unlimited Generate
   was enabled there immediately, before I had fired anything. That isolated
   the cause to **stale client-side state in the long-lived original tab**
   (the skill's documented "a long-lived tab lies about the concurrency
   slot" failure mode), not an account-wide busy slot and not the earlier
   404 (which turned out to be a red herring — a second clean upload in the
   fresh tab produced a *different* new asset id that also 404'd on that
   same detail endpoint, yet the button was enabled and the fire worked
   fine, so that endpoint is evidently the wrong one to check for upload-type
   assets).
5. Rebuilt the whole composer from scratch in the fresh tab — model,
   720p, 20s (slider), High, Sound On, Unlimited, all 7 Elements re-pasted
   and re-verified, video re-uploaded and re-attached, zoom-verified
   `UNLIMITED · ~~140~~ · 0` — and fired. **"Generation started" confirmed.**

After a ~35-minute render (Thai night-into-early-morning, should have been
the fast window, but see the render-slot note below — this and IV2b both ran
slower than the skill's stated 20-25 min baseline) the card came back with an
**NSFW flag and "Credits refunded" status** and, on opening its info panel,
the literal message **"Output may contain sensitive content. Try changing
your inputs."** — no video was ever produced, not even a flagged one to
review. This is a harder failure than the Rights-verification banner the
skill's hard rule 3 covers (which applies to a *completed* clip); there was
nothing here to confirm rights on or file. I did not retry the identical
prompt a second time given the ~35-minute cost per attempt and no indication
of what specifically triggered the filter — flagging it to the CTO instead.

**Nothing to file for S2-Fix1** — there is no MP4. The prompt text itself
is exactly the CEO-cleared, unmodified block from `s2-fix1-accident.txt`;
nothing about it reads as sensitive to a human eye (an accident with a
falling painting, a cleaner, a cracked wall). Best guess, unconfirmed: the
automated filter may be pattern-matching on "accident"/"falls"/"crack" +
museum-staff-uniform framing, or on the video-reference path specifically
(this is the only one of the two Fix-1 prompts using a video ref this
session) — worth the CTO's read since I have no way to query the filter's
actual reasoning from here.

### IV2b-Fix1-take2 — FLAGGED, full reasoning

Per the task brief: added five negatives to the end of the CRITICAL
NEGATIVES line in `docs/prompts/absence/s-interview-iv2b-fix1.txt` — `no
studio, no soundstage, no black or grey backdrop, no bare production walls,
no cyclorama` — then ran `scripts/prompt-lint.py` (exit 0) before pasting.
That edit is committed (`6d56e60`).

Staged during S2-Fix1's render so the slot was never idle: cleared the
composer, pasted the updated prompt (no video ref — this prompt takes none),
verified the single `@project_absence_char_dupe_interview_house` mention
resolved lime-green, re-verified 720p/20s/High/On/Unlimited-$0 was intact,
and fired the instant S2-Fix1's card resolved (rejected, in this case — the
slot freed up regardless of the outcome).

Downloaded the finished clip directly from its CDN URL and inspected with
`ffprobe`/`ffmpeg` frame extraction (the in-browser player's duration stayed
stuck at 0:00/0:00, the same known stuck-player-state issue documented in
session 7's report — not a real processing problem, the CDN served the full
12.4 MB file cleanly). **1280x720, 20.04s, 24fps** — spec-correct.

Checked against the prompt file's own review criteria:

- **Dupe's locked frame at 0-7s and 11-20s: clean.** Frames pulled at 0s,
  11s, 14s, 18s all show the identical correct composition — tall windows,
  warm daylight, purple sunken seating, warm wood, no gear, no crew, no
  cable anywhere in his own frame.
- **Camera visibly pointed back at Dupe inside the pan: yes.** Frames at
  8.5s and 9.5s show a heavy-tripod cinema camera dead centre, pointed
  straight down the lens — joke reads correctly, same as take 1.
- **"The house still readable behind them" — still NOT satisfied. This is
  the same defect as take 1, unresolved by the added negatives.** The
  crew-reveal frames (8.5s/9.5s) show plain wood-panelled walls, sconce
  lighting, a hard tile/stone floor, and two visible LED panel lights — no
  windows, no daylight, no purple sunken seating, nothing that visually
  connects to the house frame that opens and closes the shot. It still
  reads as a bare production space. The five additional negatives (studio/
  soundstage/backdrop/production-walls/cyclorama) did not change the
  model's output here — worth noting for whoever revises this prompt next,
  since the fix that actually worked for other scenes in this project was
  naming the *positive* replacement materials explicitly in the beat text,
  not stacking more negatives.
- Secondary, non-disqualifying-per-the-stated-tolerance note: **4 crew
  members visible again, not the scripted 3** (one at the camera with a
  hand on the operator's shoulder, one operating the camera, one holding a
  tablet/monitor centre-frame, one on the right sighting through a second
  camera). The review criteria says the exact count (2 or 3) isn't worth a
  re-fire on its own; flagging for completeness since the prompt's own
  negatives literally say "no fourth crew member," but the room mismatch is
  the disqualifying reason for FLAGGED here, not the count.

Filed as `IV2b-Fix1-take2.MP4` per the brief's naming — take 1
(`IV2b-Fix1.MP4`) is untouched, unreplaced; the editor picks between them.

## 2. FILING

- `IV2b-Fix1-take2.MP4` uploaded via `scripts/gdrive-bridge/ilag_mirror.py`
  to the existing `All Scene/Fix-1/` folder
  (`1WBk3uts8UaJQwBZuLwWjTFf6mcCMoidc`), size-verified against a fresh Drive
  listing (12.4 MB local == 12.4 MB on Drive) before the staging copy was
  deleted. `logs.txt` ADD line written with verdict + reasoning in the note
  field.
- Nothing to file for S2-Fix1 — no output was produced.

## 3. MONEY

Two Unlimited video fire attempts (S2-Fix1 fired twice — see the disabled-
button investigation above; the first click on the stale tab never actually
submitted anything, confirmed via Usage History showing zero Seedance 2.5
entries in the relevant window before the real fire). Generate button
zoom-verified struck-price-to-0 immediately before every real click. No live/
unstruck price ever appeared, no priced click was ever made. S2-Fix1's
rejection shows as "Credits refunded" in its own card status — consistent
with $0 either way since it ran Unlimited. No real money was ever at risk or
spent this session.

## 4. RENDER SLOT DISCIPLINE

S2-Fix1 fired first (~23:05), IV2b-Fix1-take2 was staged in full during its
~35-min render and fired within seconds of S2-Fix1's card resolving
(rejected) — the slot was never left idle. IV2b-Fix1-take2 then took ~34 min
to render. Both renders ran slower than the skill's documented 20-25 min
night-window baseline; time of fire was ~23:00-00:25 ICT, which per the
skill's UTC-window table (01:00-07:00 UTC = 08:00-14:00 ICT is the fast
window) was outside the fast window on both counts — consistent with the
observed pace, not a bug.

## 5. QUEUE POINTER

Both scripted fires for this task are done (one rejected, one flagged).
Nothing else was queued or scripted for this session.

- **S2-Fix1 needs a CTO call before any re-fire**: the prompt was the
  CEO-cleared, unmodified text: is a re-fire of the identical prompt worth
  the ~35-min cost on the chance the content filter's flag was a one-off, or
  should the prompt be reworded first (and if so, which element — the
  video-ref specifically, or the "falls"/"crack"/accident language) to avoid
  tripping it again? I don't have visibility into what specifically the
  filter matched on.
- **IV2b-Fix1-take2's crew-reveal room is the open item** if a third attempt
  is wanted: the negative-stacking fix didn't move it. The composer state
  (Seedance 2.5/720p/20s/High/On/Unlimited) is known-good; the fix likely
  needs the room's positive materials named explicitly in the 8s beat itself
  (tall windows, warm daylight, purple sunken seating, warm wood — the same
  words that describe Dupe's own frame) rather than more negatives, per the
  pattern the reference report from session 7 already flagged for this
  exact defect.

## Files Changed

- `docs/prompts/absence/s-interview-iv2b-fix1.txt` — appended five negatives
  to the end of the CRITICAL NEGATIVES line (commit `6d56e60`, made before
  this report)
- `docs/reports/absence-handover-20260903-8.md` — this report (new)

Merge from local `main` at task start (`22fde5f`, `c74442a` and everything
between) already landed as an ordinary merge commit; `origin/main` was
stale, local `main` had the real tip — same situation session 7's report
already documented, confirmed again this session.

## Commits

- `6d56e60` — IV2b-Fix1: strengthen crew-reveal negatives against studio/
  soundstage bleed (made before this report)
- (this report, committed with this handover)

## Tests

- `python3 scripts/prompt-lint.py docs/prompts/absence/s2-fix1-accident.txt
  docs/prompts/absence/s-interview-iv2b-fix1.txt` — exit 0, before any
  editing (baseline).
- `python3 scripts/prompt-lint.py
  docs/prompts/absence/s-interview-iv2b-fix1.txt` — exit 0, after the
  negatives edit, before pasting (required by the brief).

## Issues / Blockers

- **S2-Fix1: hard content-policy rejection, zero output, needs a CTO
  decision before any re-fire** (see Queue Pointer above). This is the
  primary blocker from this session.
- **IV2b-Fix1-take2: FLAGGED**, same room-mismatch defect as take 1,
  unresolved by the negatives-only fix — see reasoning above and the
  suggested next step (positive materials in the beat, not more negatives).
- **Minor note, not a blocker**: 4 crew members visible in IV2b-Fix1-take2
  vs the scripted 3 — explicitly tolerated by the review criteria on its
  own, noted for completeness only.
- No hard stops hit otherwise. The Unlimited toggle itself worked on the
  first clean click both times it was actually touched (the disabled-button
  investigation above was a stale-tab issue, not a stuck-toggle issue, so
  hard rule 5's one-clean-attempt-then-escalate ladder was not the
  applicable path here). No login walls, no instructions found embedded in
  page content, no rights-verification banner on either result.

## Notes for Reviewer

- The disabled-Generate-button investigation (S2-Fix1, section 1 above) is
  worth reading even though it resolved cleanly — it's a new failure mode
  not yet documented in the `higgsfield-unlimited-gen` skill (existing
  entries cover a stuck *toggle* and a stuck *concurrency-slot* toast; this
  was a silently `disabled=true` Generate button with zero visible error,
  caused by tab staleness, that a screenshot alone would not have caught
  because the disabled styling is subtle against the composer's dark
  background). Recommend folding "check `.disabled` via JS, not just the
  screenshot" and "when Generate stays unexplainably unclickable, try a
  fully fresh tab before assuming a slot conflict" into the skill.
- Recommend the CTO open S2-Fix1's rejected prompt text
  (`docs/prompts/absence/s2-fix1-accident.txt`, unmodified) and judge
  whether a specific phrase is worth softening before any re-fire is
  authorised, since I can't query Higgsfield's filter for its actual
  reasoning.
- Recommend opening IV2b-Fix1-take2's 8-10s window at full res before
  deciding whether to accept the take as-is (editor's call stands either
  way, per the standing footage rule) or request a third attempt with the
  room rewritten positively.

## SKILL-OVERRIDE

None. All HARD rules in `higgsfield-unlimited-gen` and `browser-operator`
followed as written — Rerun never used, synthetic-paste-only text entry with
the End→space→Backspace bind-fix after every paste, duration driven via
ArrowRight on the slider (never typed), struck-to-zero zoom check on the
real button (not the DOM text scrape) before every Generate click, one
Unlimited video generation in flight at a time, next prompt staged during
the render wait rather than left idle, Usage History checked as the
concurrency-slot hypothesis was being tested rather than assumed.
