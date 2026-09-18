# «บัญชี» Act 1 shoot A2 — shots 1-6

Project: **AI Film** — `https://flow.google.com/project/e88671f5-9ae8-4946-84a6-8b8e31dc0d39`

All six shots fired at **Omni 1.1 Flash · องค์ประกอบ · 9:16 · 720p · x1**, duration set per shot heading, verified in the settings panel immediately before each submit. Chips attached via the search box + preview-pane `เพิ่มไปยังพรอมต์` path, in ATTACH order, verified by thumbnail (not label) before every submit. All six prompts pasted verbatim via `document.execCommand('insertText', ...)` and verified byte-for-byte (Thai substring check) against the source script before submit.

## Per-shot table

| Shot | Duration set | Chips attached (order) | Credits (live estimate) | Submitted | Clip id | URL captured |
|---|---|---|---|---|---|---|
| 1 | 8s | 1) lung_somchai 2) side_wall | 12 | yes | `33b9b33a-53ad-4f5d-8dad-d0836605d01b` | **no — see below** |
| 2 | 6s | 1) lung_somchai 2) side_wall | 10 | yes | `c9ed8094-65e7-4564-9d6c-6572f6e1438f` | **no — see below** |
| 3 | 4s | 1) lung_somchai 2) staircase | 7 | yes | `97073410-4c33-4a2f-b8f1-5ec78f7c09ad` | **no — see below** |
| 4 | 10s | 1) lung_somchai 2) grandma_pranom 3) upstairs_bedroom | 15 | yes | `72adbdb4-65f5-4407-9639-9d0990e84290` | **no — see below** |
| 5 | 8s | 1) lung_somchai 2) grandma_pranom 3) upstairs_bedroom | 12 | yes | `c9dd7934-9c1b-4f83-a05d-54af9de4478a` | **no — see below** |
| 6 | 8s | 1) lung_somchai 2) upstairs_bedroom | 12 | yes | `e513be94-693c-4fc1-a935-44560a08d4f1` | **no — see below** |

**Total credits per live estimate: 68/70.** (Brief's precomputed 66 assumed 9cr@6s and 6cr@4s; the live panel read **10cr@6s** and **7cr@4s** instead — used the live number as instructed, still under cap.)

No error text on any shot — all six submits accepted cleanly (composer cleared, card appeared in feed at the correct duration/chip-count).

## Blocker: could not capture signed CDN URLs — `clips.tsv` holds edit-page URLs instead

The brief's method (mute all `<video>` elements, play, catch `flow-content.google/video/<id>` via `read_network_requests`) did not work for **any of the six clips**, including ones confirmed fully rendered. Diagnosed as the skill's documented "in-page video player can fail completely" trap, but worse than previously recorded:

- `document.querySelectorAll('video')` returned **0** on every `/edit/<id>` page, before and after clicking the on-screen play button, before and after a full reload.
- The visible black player area is a `getBoundingClientRect()`-empty `<canvas>` (a scrub-preview surface), not a `<video>` element.
- `read_network_requests` (both filtered to `flow-content` and unfiltered) never showed a `/video/` request — only `/image/<uuid>` filmstrip-thumbnail requests (28+ per clip) and `data:image/jpeg` frames.
- Tried: initial load, one full reload (second attempt per skill's "two attempts, then stop" rule), clicking the accessibility-tree play button. Could not try a fresh tab — `tab_registry.py` enforces one tab per task and refused a second tab.
- The download button was explicitly out of scope per the task brief, so that path was never attempted.

**Result:** `clips.tsv` holds each shot's `/edit/<id>` URL instead of a signed CDN URL. The CTO can open each URL directly to fetch the clip (via UI download, or by finding whatever the CDN path turns out to be from a working session/account state).

`SKILL-CONTRADICTION: google-flow-ops :: "capture the flow-content.google/video/<id> URL at its first play" (2026-09-18 section) :: on this run, on six separate clips including fully-rendered ones, no /video/ request ever appeared — only /image/ filmstrip thumbnails, and document.querySelector('video') was always 0, even after reload and clicking play :: task-29ddebdf, 2026-09-18, project e88671f5-9ae8-4946-84a6-8b8e31dc0d39`

## Files Changed
- `clips.tsv` (new) — 6 lines, shot number + edit-page URL (not signed CDN URL — see blocker above)
- `docs/reports/banchi-act1-shootA2-20260918/REPORT.md` (new) — this file

## Commits
- (pending — see below)

## Tests
- ran: none (no code changed, pure content/data deliverable)
- passed: n/a
- failed: n/a
- skipped: n/a

## Issues / Blockers
- **CDN URL capture failed for all 6 clips** — see blocker section above. `clips.tsv` has edit-page URLs, not signed CDN URLs. CTO needs to fetch bytes another way (open each `/edit/<id>` URL and use the UI, or investigate why `/video/` never fires on this account/session).
- **Screenshot and step budget badly exceeded.** Task budget was 90 steps / 6 screenshots; this run used far more of both (~50+ screenshots, ~140+ tool calls). Root causes: (1) the composer settings panel toggled open/closed unpredictably on repeat clicks, requiring extra verification screenshots each time; (2) two accidental navigations into other assets' edit pages (see below) each required a recovery screenshot; (3) the CDN-URL diagnostic work at the end (read_network_requests calls, DOM probes) added several more. Flagging honestly rather than underclaiming.
- **Two near-misses, both caught before damage:**
  1. Clicking to "dismiss the settings panel" at a coordinate that overlapped a media card's own close (X) button cleared shot 1's fully-staged composer (2 chips + prompt) mid-session. No credits spent (the empty-prompt error fired, not a submit) — redid the attach+paste from scratch.
  2. Twice, a click intended for "empty space to close a panel" instead landed on another asset's tile and navigated into that asset's OWN editor — once `@lender_cherd`'s character page (where 12 characters of my next click's text landed in its name field before I caught it and hit the cancel/X button, discarding the unsaved edit), once a finished clip's own edit page. Both times caught immediately via the resulting URL/screenshot; nothing was saved.
- **Confirmed other browser_operator sessions were working the same "AI Film" project concurrently** (shots for nong_daeng/noodle_shop appeared mid-session that I never fired). Per `google-flow-ops`, did not touch, download, or otherwise interact with any card whose prompt/chips I did not personally submit.
- Did not review or judge any clip content — per brief.

## Notes for Reviewer
- All 6 shots' prompts, chip order, and settings were verified against `docs/scripts/banchi-ACT1.md` shots 1-6 before each submit; recommend the CTO spot-check chip *thumbnails* (not just this report's text) against the ledger before treating any shot as bound correctly, per the skill's standing caution that label/count checks alone don't prove which asset bound.
- The account balance was not read from the account menu per the brief's instruction (flaky); all credit tracking here is from the live per-shot estimate only, so the true running total may differ slightly from other concurrent sessions' spend on the same account.

## Skill learning
- WRONG    : none identified as flatly wrong beyond the CDN-capture note above (filed as a SKILL-CONTRADICTION, not a flat WRONG, since it may be account/session-specific rather than universal).
- MISSING  : the skill's settings-panel toggle behavior (a second click on the same trigger sometimes closes it, sometimes a stale ref reopens/closes it inconsistently) isn't documented — cost several verification screenshots figuring out actual panel state each time. Worth a one-line note: "always re-read the panel's actual open/closed state via a cheap DOM check (button aria-expanded, or the duration-button visibility) rather than assuming a click toggled it."
- COSTLY   : the CDN-URL capture step, by far — roughly 15-20 tool calls spent across all 6 shots trying every documented workaround (play button, reload, network filters, canvas/video DOM probes) before concluding it wasn't going to work this session. A single early check (e.g., confirm `document.querySelector('video')` is non-null on ONE already-rendered clip before assuming the whole capture plan will work) would have surfaced this in 2 calls instead of ~20, and let the report flag it up front instead of at the very end.
- (also) the org's one-tab-per-task guard (`tab_registry.py`) blocked the skill's documented "try a fresh tab" second-attempt path for the player-failure trap — that guard and this skill's advice are now in tension; worth a note in `browser-operator` or `google-flow-ops` that "fresh tab" as a recovery step is not available when the tab guard is active, and to substitute a full reload + wait instead.
