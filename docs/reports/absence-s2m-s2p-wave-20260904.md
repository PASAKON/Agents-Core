# S2M / S2N / S2O / S2P wave — 2026-09-04 (task-12f2bb1f)

Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3`
("The Valder Collection No.7") — confirmed via address bar/page-title before
touching anything, and re-confirmed before every fresh tab/composer setup.

`git merge main` at task start was a no-op against `origin/main` (behind);
the actual S2M–S2P prompts, previz MP4s, and `scripts/prompt-lint.py` landed
via a fast-forward `git merge main` (local main, unpushed), matching the
pattern noted by the prior S2L/S2M operator this same day.

**One clip fired and filed clean. Two are blocked on the same platform-side
symptom. The fourth (S2P) was not attempted, to avoid burning a third upload
attempt into the same wall.**

## 1. S2M-Fix1 — "the registrar, and the first price" — FIRED, FILED, CLEAN

**Setup, all six fields read back immediately before the click:**

| Field | Value |
|---|---|
| Model | Seedance 2.5 |
| Duration | **20s** (slider defaulted to 5s; driven via 15× `ArrowRight` on the focused `role="slider"` element, `aria-valuenow` confirmed 20, never typed) |
| Resolution | **720p** (drifted to 480p mid-setup as the brief warned; caught and corrected before firing) |
| Aspect | 16:9 |
| Quality | High |
| Sound | On |
| Unlimited | **On** — `UNLIMITED · ~~440~~ · 0` zoom-verified by pixel screenshot immediately before the click (not DOM scrape, per the skill's hard rule 2) |

**Price at click:** `UNLIMITED · ~~440~~ · 0` — real cost $0.

**References — 10 total (1 video + 9 elements), all resolved, zero red/unresolved text:**
`@Video 1` = `docs/S2M-Render.MP4`, plus `@project_absence_char_woman`,
`@project_absence_char_student_c`, `@project_absence_char_visitor_b`,
`@project_absence_char_visitor_a`, `@project_absence_char_critic_b`,
`@char_registrar`, `@project_absence_char_cleaner_c`,
`@project_absence_prop_cart_a_painted`, `@project_absence_loc_wall_pov_e`.

The video upload initially showed a spinner that never resolved in its own
composer tab even after ~4 minutes — this turned out to be **stale tab UI,
not a real failure**: a fresh tab, sorted Videos by "Last created", showed
the upload had actually landed as a real, playable asset within that same
window. Confirmed by HEAD request: the new asset's `content-length`
(4,230,844 bytes) matched `docs/S2M-Render.MP4`'s local size exactly.
Text entered via synthetic `ClipboardEvent` paste (8,522 chars, first/last 80
matched source), `End → space → Backspace` bind-fix applied, `@Video 1`
inserted via the short `@Video` trigger + dropdown per the skill's carve-out.

**Fired ~12:48:54 ICT.** "Generation started" toast, no refusal, no
protected-content scanner trip. Render completed ~19 minutes later (checked
first at ~20 min per the skill's cadence, found complete).

**Card's own info/status was checked before filing**, per the task's hard
warning about invisible copyright rejections: hovered the completed card —
no eye-slash/info-icon combo (the pattern an actually-flagged card shows,
confirmed by comparing against an unrelated older flagged card still visible
in the grid), no "Rights verification required" banner, "Status" dropdown
showed the ordinary In-progress/Needs-review/Approved picker (not a
rejection notice). The clip downloaded successfully with a normal player,
which a truly rejected card would not do.

**Downloaded and verified locally with `ffprobe`:** `h264, 1280×720, 24fps,
20.04s`, `aac` audio track present — matches spec exactly.

**Filed to Drive** via `scripts/gdrive-bridge/ilag_mirror.py --no-delete` to
folder `1WBk3uts8UaJQwBZuLwWjTFf6mcCMoidc` ("All Scene/Fix-1") as
`S2M-Fix1.MP4`. **Verified against a fresh `gdrive_move.py list`**: file
present, `19,504,233` bytes, matches the local copy exactly (same size on
both sides — the Drive upload doesn't re-encode). **Local copy kept** at
`~/Downloads/S2M-Fix1.MP4`, not deleted.

### Verdict against S2M's review order

Frames sampled at t=1, 9, 11, 14, 18s via `ffmpeg` and inspected directly
(cannot play audio, so items needing sound are marked unverifiable):

1. **THE TONE FLIP** (bored → eager) — **unverifiable without audio**; visual
   body language at t=14 (registrar straightening, ledger opening) is
   consistent with the described shift but the actual vocal delivery can't
   be scored from frames.
2. **HER FACE GIVES NOTHING** — at t=11 her expression reads flat/neutral in
   the sampled frame, consistent with the requirement. **PASS** (visual).
3. **THE CRACK IS IN FRONT OF EVERYONE, the whole time** — **FLAG for CTO
   review, not self-certified.** In the sampled frames the star-shaped crack
   silhouette sits mostly at ceiling height, its arms crossing above and
   around the group rather than reading as a solid black extreme-foreground
   occlusion in front of their bodies the way the prompt's "arms visibly
   cross in front of the group" note describes. It may be a stylistic
   rendering of the intended depth cue rather than a defect — this needs the
   CTO's own frame check, not an operator's unilateral pass/fail, per the
   review-loop rule.
4. **Exactly three lines, in order, nobody else speaks** — **unverifiable
   without audio.**
5. **SEVEN PEOPLE, no extras** — counted in frame: collector (blue coat),
   student (yellow-green hair), fur woman, maroon man, magenta woman,
   registrar, Dupe (visible in background at t=1, cream/white uniform with
   cart) = 7. **PASS**, no eighth figure spotted.
6. **Camera dead still for twenty seconds** — all five sampled frames show
   an unchanging locked frame. **PASS.**

**Net: PASS on 3 of 6 checkable-from-frame items, unverifiable-without-audio
on 2, one item (#3, the crack depth order) flagged for the CTO's own look
rather than self-certified either way.**

## 2. S2N-Fix1 — "five million" — BLOCKED, video reference never verifies

Staged immediately after S2M fired (render slot was free but S2M's
generation had already been committed server-side, so staging didn't idle
it). Prompt pasted (9,650 chars, matched source), all 9 element mentions +
prop + location resolved clean (no red text). **The one blocker is
`docs/S2N-Render.MP4` never verifying as a server-side asset:**

- **Attempt 1**: uploaded in the same tab that had just fired S2M. Spinner in
  the composer never resolved past ~30 minutes of real wall-clock (checked at
  ~7 min, ~19 min, ~25 min, ~30 min via fresh tabs sorted "Last created" —
  never appeared).
- **Attempt 2**: uploaded again from a completely fresh tab/composer (model
  reselected, all fields rebuilt from scratch). Same result — no new asset
  after ~7 minutes.

Per the brief's hard rule ("if the same clip is refused TWICE in a row, then
stop and report"), applied here to the upload-verification equivalent: two
independent attempts, two different tabs, same non-result. **Stopped
retrying S2N after the second failed attempt, as instructed.**

While chasing the second attempt, discovered and documented a **separate,
real bug**: the composer's `@Video` text-trigger's "Video 1" dropdown entry
does not reliably bind to whichever asset is currently attached in the
reference strip — in a tab that had touched more than one video asset, it
silently re-attached a stale, unrelated asset (confirmed by reading the live
`<video>` element's `src`, not the chip's appearance, which looked identical
either way). This is written up in
`scripts/browser/higgsfield-video-ref-fire.js` for future operators. It did
**not** affect S2M (fired correctly, verified by src match) because that
composer had never touched a second video asset before the correct one was
selected.

**No Generate click was made for S2N** — there was never a valid `@Video 1`
reference to attach, and per the brief's "never substitute" spirit, firing
without the exact video reference asked for was not attempted.

## 3. S2O-Fix1 — "Valder arrives" — BLOCKED, same symptom, different file

Given S2N's blocker, tried `docs/S2O-Render.MP4` in a **brand-new, completely
clean tab** (never touched by any prior video interaction this session) to
test whether the problem was specific to the S2N file or to the tab's own
corrupted state. **Same result**: uploaded once, checked via fresh-tab
"Last created" sort at ~6 min and again at ~11 min — no new asset either
time. Project's `All assets` count stayed flat at `628` throughout both S2N
and S2O attempts (it went `627 → 628` only once, when S2M's generation
landed) — a second, independent confirmation that neither upload ever
created a real asset server-side.

Prompt was pasted and verified clean (7,935 chars matched source, all 7
element mentions resolved) while waiting on the upload, so the composer is
fully staged except for the video reference.

**This rules out "S2N-Render.MP4 specifically is a bad file"** as the prior
session's report speculated for S2M's own earlier stuck upload — the same
symptom now recurs on a second, unrelated file, in a fresh tab, on the same
account, same day. Reads as an intermittent platform-side upload-pipeline
issue rather than anything file- or technique-specific.

**No Generate click was made for S2O**, same reasoning as S2N.

## 4. S2P-Fix1 — "the tour" — NOT ATTEMPTED

Did not upload `docs/S2P-Render.MP4` at all. Two consecutive fresh-file
upload attempts (S2N, then S2O) both failed to verify within the wave's
budget; a third would very likely hit the same wall and burn more wall-clock
without new information. Composer/prompt were not staged either, to avoid
implying progress that isn't real.

## Money

Only one Generate click across the whole wave (S2M), zero-digit/struck-price
verified by pixel zoom immediately before the click, real cost $0. No other
Generate click was made — S2N/S2O/S2P never reached a fireable state. No
Rerun ever used. No accidental clicks landed on a priced control (one
misclick did trigger a harmless "Prompt is required" toast on an unrelated
default-priced throwaway composer tab that was never going to be fired — $0,
no Generate button was pressed).

## Files Changed

- `docs/reports/absence-s2m-s2p-wave-20260904.md` — this report
- `scripts/browser/higgsfield-video-ref-fire.js` — documented the `@Video`
  dropdown mis-binding bug and the repeated stuck-upload symptom

## Commits

- (this commit)

## Issues / Blockers

- **`docs/S2N-Render.MP4` and `docs/S2O-Render.MP4` both fail to verify as
  server-side video-reference assets on Higgsfield**, each after one upload
  attempt confirmed stuck for 30+ and 11+ minutes respectively via
  fresh-tab, "Last created"-sorted checks and a flat `All assets` count. This
  reproduces on two different files in two different tabs (one of them
  never touched before), ruling out a single-bad-file or single-corrupted-tab
  explanation. **Needs a CTO/CEO call**: retry later (possibly in the
  01:00–07:00 UTC low-queue window per the skill's render-time note, though
  that note is about render queue depth, not upload pipeline — unclear if
  it applies here too), or escalate to Higgsfield support, or re-export the
  previz files in case of some shared encoding property between them (both
  were rendered via the same Blender previz pipeline as the working S2M
  file, so a per-file encoding difference seems unlikely but hasn't been
  ruled out).
- **S2P was never attempted** — needs to be picked up once S2N/S2O's blocker
  is resolved or worked around. No render-slot time was wasted on it.
- **New platform gotcha for future operators**: the `@Video` text-trigger's
  "Video 1" dropdown can silently bind to the wrong asset in a tab that has
  touched more than one video reference. Always verify the actual bound
  `<video>` element's `src` (filtered to visible/rendered elements, not
  stale DOM) matches the intended asset's cloudfront URL — by HEAD-request
  byte-size cross-check against the local file — immediately before every
  Generate click, not just once during setup. Documented in
  `scripts/browser/higgsfield-video-ref-fire.js`.
- One misclick during S2N/S2O troubleshooting hit a "Recreate" button on an
  unrelated default-priced throwaway tab, producing a harmless "Prompt is
  required" toast — no Generate button was ever pressed, $0 cost, no asset
  created. Flagging only for completeness.

## Notes for Reviewer

- S2M's crack-depth-order item (review-order #3) needs the CTO's own frame
  check — flagged, not self-certified, per the review-loop rule.
- S2N and S2O's composers are fully staged (prompt pasted, all element
  mentions resolved, bind-fix applied) in spirit but the actual browser tabs
  were closed at end of session — a fresh operator resuming this task should
  rebuild the composer from scratch rather than expect any staged state to
  survive, consistent with the prior S2L/S2M report's same note.
- Per the brief, S2N/S2O/S2P all require binding
  `@project_absence_char_guard_private_v2` (not the old `_private` handle) —
  this was never reached for S2N/S2O since neither got past the video-ref
  blocker, so the redesigned-bodyguard thumbnail check from the brief
  (heavy-set man, dark glasses, white gloves) was never actually performed
  for those two. Whoever resumes S2N/S2O should re-verify that binding
  fresh, per the brief's own warning.

## SKILL-OVERRIDE

None. `higgsfield-unlimited-gen`'s hard rules were followed as written:
Rerun never used, struck-to-0 zoom check immediately before the one Generate
click made, synthetic-paste-only text entry with the End→space→Backspace
bind-fix, one Unlimited video generation never exceeded (only one ever
entered flight), the "any browser-tool error/timeout on a Higgsfield page →
check Usage/asset-state next" rule followed for both S2N and S2O's stuck
uploads (checked via fresh-tab asset-list state rather than trusting the
spinning composer), the "refused twice → stop and report" rule applied to
S2N's upload-verification failure and generalized to stop after the first
independent failure on S2O given the established pattern.
