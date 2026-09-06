# Absence wave 2026-09-06 — S2K-Fix1, S2M-Fix1-take2 (STOPPED), plate C take2

Project: https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3 (The Valder Collection No.7)
Task: task-f7ac7a01

STOPPED MID-RUN by CTO 10:40 ICT: "sheet in worktree is superseded (main is now
dd6e0de, crack canon rewritten). Do NOT fire S2M." Composer left untouched at
the point of the stop — no navigate, no further clicks, nothing closed.

---

## 0 · S2K-Fix1 (Unlimited, 12s) — FIRED, COMPLETED, FILED

**Six-field readback before fire:** Seedance 2.5 · 16:9 · 720p · 12s · High · Sound On.
**Chip gate:** 8/8 unique (`@project_absence_char_critic_b`, `_student_c`, `_woman`,
`_visitor_b`, `_visitor_a`, `_cleaner_c`, `@project_absence_loc_wall_pov_e`,
`@project_absence_prop_cart_a_painted`) — matches `prompt-lint.py --chips` exactly.
**Previz attached:** `docs/S2K-Render.MP4`, uploaded fresh, byte-verified before
attaching — CloudFront asset `d928986a-7d89-420e-bd05-bd9313fd595e.mp4`,
content-length 2,859,627 == local file's exact size. (First two attach attempts
grabbed the WRONG asset — see §5 below — this one was verified correct before
click.)
**Price at click:** zoomed screenshot confirmed `UNLIMITED` · struck `84` · `0`.
**Fire time:** 2026-09-06 01:28:42 UTC (08:28:42 ICT).
**Fire verification:** "Generation started" toast + All-assets count 659→660 +
card showed `Processing`.
**Completion:** confirmed via reload at 02:09:41 UTC — card showed finished
thumbnail, Details panel: Model Seedance 2.5, Quality 720p, Bitrate High, Size
1280x720, Created "September 6, 2026 at 8:28 AM" (matches fire time exactly).
Render took ~41 min (slower end of normal range).
**Info-icon check:** no Rights-verification banner, no flag.
**THE CRACK VERDICT:** torn/star shape, solid dark arrowhead centre, four
beaded arms — matches canon description, NOT a square/uniform-bar defect. **PASS.**
**REVIEW ORDER verdict:** the four front-row women read right-to-left exactly
per the position map (magenta CRITIC hard right, yellow-green STUDENT nearer
camera, blue COLLECTOR_A centre, rust VISITOR_B beside her) — matches. Did not
verify every beat (crying/hand-on-back/fold-arms timing) frame-by-frame beyond
the single reviewed frame; recommend CTO's own frame-by-frame pass per the
review-loop rule.
**Drive filename:** `S2K-Fix1.MP4` — https://drive.google.com/file/d/14wj-MsFJUtINSczKp-h2nh3A6_uKqYjt/view
(uploaded via `scripts/gdrive-bridge/upload_fix1.py`, logged to Sorry, Sir/logs.txt).

**S2K-Fix1-take1 (the accidental 5s take from the reload probe): NOT located
or filed this session.** Ran out of time before searching the grid for it.
Flag for successor: task brief says "when it lands, file it as
S2K-Fix1-take1.MP4 whatever it looks like" — unclear if it already landed in
an earlier session or is still pending. Needs a grid search by the successor.

---

## C · Projector plate take 2 (PAID image, GPT Image 2) — FIRED, ACCEPTED, DOWNLOADED

**Reference slot:** existed. GPT Image 2 composer (Image mode, switched from
default Higgsfield Soul Cinema — Soul does not accept reference images, per
existing skill finding) has an "Upload media" tile in the same "+" reference
picker used for video refs. Uploaded `ELEMENT-dupe-interview-house.png`
(1,080,709 bytes local) directly, attached via real click after visual
confirmation (thumbnail showed the reference man).
**Prompt used** (written per task instructions — describes only the CHANGE
from the reference, defers man/house/pose to the image ref):

> Using the reference image exactly for the man's face, his dark blue suit,
> his pose, and the room itself — his enormous 1960s retrofuturist house with
> warm wood panelling in wide vertical slats, the tall window throwing warm
> daylight from the right, deep plum sunken seating, polished stone floor —
> keep all of that unchanged.
>
> CHANGE ONLY THIS: pull the frame wider than the reference. IN THE NEAR
> FOREGROUND ON THE LEFT, large and close to the lens and slightly out of
> focus, add an old grey-and-white film projector on a stand, a big black
> feed reel on top, its lens barrel pointing across the frame toward him.
> Behind him against the panelling, add his cleaning cart at rest: orange
> bucket, a red-handled mop and a broom standing up out of it, labelled
> bottles, a small gold V on the front panel.
>
> Warm shadow, cold white, fine film grain, photographed not rendered. No
> text, no logos, no other people.

**Settings:** 1K / Medium / 16:9 (default) / 1-per-gen.
**Price at click:** zoomed, struck `4.5` → live `1` credit — an ordinary
single-image charge (task's precedent was 1.5 credits; close enough, same
class).

**⚠️ INCIDENT — 4 generations fired instead of 1, ~4 credits (~$0.16) instead
of ~1.** The first Generate click (via `find()`-ref) showed no toast and no
asset-count change after ~5s; treated as a no-op per the documented "wait
4-6s" guidance and re-clicked at the exact coordinate. The second click showed
"Generation started" and the count moved by one. Minutes later the grid showed
**4 new images total**: 3 standing-pose variants that do not match the brief
(the model did not obey "seated ... hands together in his lap" every time)
plus 1 correct seated variant matching the brief exactly. Conclusion: the
first "silent" click was NOT a no-op — it fired for real, delayed, and
possibly further variants queued from repeated interaction with the same
composer state before the desync resolved. **Disclosed here rather than
hidden.** Documented as a new finding in the replay script (4-6s wasn't long
enough this session; wait 15-20s before ever re-clicking a silent Generate).
No further Generate clicks were made near this composer once the pattern was
noticed.

**Accepted image:** the seated variant, verified against every review point
(projector large/soft/near-left ✓, three depth planes ✓, man matches
reference face/suit/pose ✓, cart visible behind him ✓, no text/logos/other
people ✓).
**Downloaded and saved to:** `docs/prompts/absence/generated/project_absence_char_dupe_interview_projector_take2.png`
(local, in this worktree — not yet uploaded to Drive or re-pointed to the
Element per task instruction: "CEO approves the image first, then the Element
gets re-pointed").
**The 3 rejected standing variants were left in the Higgsfield project
untouched** (no delete authority, no need — they cost nothing further to
leave).

---

## A · S2M-Fix1-take2 — **NOT FIRED.** Stopped by CTO order mid-setup.

Sequence of what was actually done, for the successor picking this up on the
corrected sheet:

1. Prompt pasted from **the worktree's copy** of
   `docs/prompts/absence/s2m-fix1-registrar-welcome.txt` — 9/9 chips confirmed
   twice (`@char_registrar`, `@project_absence_char_woman`, `_student_c`,
   `_visitor_b`, `_visitor_a`, `_critic_b`, `_cleaner_c`,
   `@project_absence_prop_cart_a_painted`, `@project_absence_loc_wall_pov_e`).
   **The CTO's stop message says main is now `dd6e0de` with the crack canon
   rewritten — this worktree's sheet is stale relative to that.** Whatever was
   pasted in this session should be treated as superseded; the successor
   should re-pull the sheet fresh.
2. Resolution set to 720p, duration set to 20s (via the ARIA-slider
   focus+ArrowRight technique), Unlimited toggled on — all confirmed via DOM
   read before the reference-attach step.
3. `S2M-Render.MP4` uploaded fresh (1,796,645 bytes local). First attach
   attempt via direct grid click hit the "Last used" trap (see §5) and opened
   a Trim-video dialog showing the correct new asset
   (`7e8aad4b-a8ca-43c8-9b38-75df157ae83d.mp4`, content-length 1,796,645 —
   byte-verified match) rather than attaching directly. Clicked "Save" in
   that dialog — worked, no error.
4. **Immediately after, the browser window silently shrank below the 1280px
   threshold** (see §4 for the full innerWidth log) and collapsed into
   Higgsfield's "Mobile Access Coming Soon" lockup screen — a documented
   client-side bug, not caused by any click on my part. `resize_window`
   reported success repeatedly without changing anything (matches the
   skill's own documented finding). Recovered via the documented fix: close
   tab, open a fresh one (not by dismissing the "Got it" button + resize,
   which did not work this time).
5. On the fresh tab: prompt/chips/model/resolution/duration all had to be
   rebuilt from scratch (partial autosave — settings persisted once, prompt
   did not). Re-pasted prompt, 9/9 chips confirmed again.
6. **Unlimited toggle click did not flip `data-state` from "off" to "on"** on
   the fresh tab — one clean `find()`-ref click attempt, confirmed no flip
   after 1s. Per hard rule 5, did NOT try a second click technique. Did one
   non-click diagnostic (a full page reload) since the toggle had worked
   correctly twice earlier in this same session (on two other tabs) —
   this is a reload, not "a second click technique near the priced button."
7. **The reload reset everything again** (Cinema Studio 4.0 / 1080p / 5s
   default, prompt cleared). Reselected Seedance 2.5 successfully (needed a
   synthetic PointerEvent sequence on the model chip — plain clicks did not
   open its dropdown).
8. **Attempting to set resolution back to 720p, the resolution dropdown
   stopped responding entirely** — 2 real coordinate clicks + 1 synthetic
   PointerEvent sequence on the "1080p" pill, all confirmed via
   `document.querySelector('[role="listbox"]')` showing 0 children (closed)
   after every attempt. This is where the CTO's stop message arrived.

**Composer was left exactly as-is at the stop** (no further clicks): Video
mode, Seedance 2.5, 1080p (stuck), duration 5s (default, never reset to 20s
in this final instance), Sound On, **no prompt text, 0 chips** (cleared by
the last reload and never re-pasted), Unlimited **off**. **Nothing was fired.**
The task's own outage ladder ("fire anyway without the ref, flag it") was
never invoked because the CTO's stop order arrived before the composer was
even ready to fire, and firing on a stale sheet was explicitly the wrong move
anyway.

---

## B · S2N-Fix1-take2 — not started. Never reached; the video slot was never
free of the S2M setup work before the stop order arrived, and S2M needed to
go first per the task's own ordering.

---

## 4 · Every innerWidth reading this session (chronological, per the HARD
PRE-FIRE STEP added 2026-09-06)

| # | Context | innerWidth | innerHeight | Verdict |
|---|---|---|---|---|
| 1 | First tab, after navigate + `resize_window(1600,1000)` | 1440 | 754 | OK (≥1280) |
| 2 | Same tab, re-verified before S2K composer setup | 1440 | 754 | OK |
| 3 | Fresh tab (after first mobile-lockup recovery), post-resize | 1600 | 823 | OK |
| 4 | Same tab, before S2M reference-panel work | 1600 | 823 | OK |
| 5 | **During S2M video-ref troubleshooting — window shrank on its own** | **784** | **342** | **BELOW THRESHOLD** |
| 6 | Immediately after — full "Mobile Access Coming Soon" lockup | 764 | 392 | Locked mobile view |
| 7 | After `resize_window(1600,1000)` retry — reported success, no change | 764 | 392 | **resize_window lied** |
| 8 | New tab (escalation), post-navigate + resize | 1600 | 823 | OK, fixed |
| 9 | Same tab, after a full page reload | 1600 | 823 | OK |
| 10 | Final read at the moment of the STOP order | 1600 | 698 | OK (≥1280) |

**No Generate click was ever made while width was below 1280.** Every fire
(S2K, plate C) was preceded by a fresh, immediate width check per the hard
pre-fire rule. The narrow/lockup episode (#5-7) happened during reference-
panel work, not at a fire moment, and was fully resolved before any further
attach or fire attempt.

---

## 5 · Everything odd observed — for the replay script and the next operator

- **The reference-picker grid defaults to "Last used" sort, not "Last
  created."** If a stale/rejected asset was clicked earlier in the session
  (even accidentally), it becomes "last used" and sorts to the front of every
  later Videos-tab view, regardless of upload recency. Caused two wrong-asset
  attach attempts on S2K before this was diagnosed. Fixed by byte-exact
  `content-length` HEAD verification before every click, not by trusting
  visual position or "last used" sort order.
- **A dead/rejected asset (`ab8ec0e1-...`) surfaced repeatedly across
  multiple fresh tabs and even a fresh browser tab group** — its h2
  "Rejected due to copyright restrictions." text kept appearing in
  `document.querySelector('h2')` checks even when it had nothing to do with
  the click just made, because it's simply the first `<h2>` anywhere in the
  large "All assets" DOM behind the composer. **Lesson: never trust a bare
  `document.querySelector('h2')` as evidence of what a click did — scope the
  query to a confirmed dialog/modal container, or check for the specific
  toast text instead.**
- **A Trim-video dialog's Save button worked reliably** once the dialog's
  video preview loaded (readyState > 0) — this is a legitimate, non-buggy
  path for attaching a video reference whose length differs from (or equals)
  the composer's set duration, distinct from the direct-attach path.
- **A full page reload resets model/resolution/duration/prompt/chips
  sometimes and not other times** — inconsistent within this single session.
  Always re-verify all six fields fresh after any reload, never assume
  autosave carried anything over.
- **Model dropdown and resolution dropdown both intermittently required a
  synthetic PointerEvent sequence instead of a real click** to even open —
  consistent with existing documented findings for the Image/Video mode
  toggle, now also true for these two dropdowns in this session.
- Full technique writeup with code committed to
  `scripts/browser/higgsfield-video-ref-attach-fix.js`.

---

## Money summary

| Item | Type | Credits | Notes |
|---|---|---|---|
| S2K-Fix1 | Unlimited video | 0 | struck 84→0, verified |
| Plate C take2 (accepted) | Paid image | 1 | struck 4.5→1 |
| Plate C take2 (3 unintended extra) | Paid image | ~3 | disclosed incident, see §C |
| S2M-Fix1-take2 | — | 0 | never fired |

**Total unplanned spend: ~3 credits (~$0.12), from the Generate-click
duplicate-fire incident on the image plate.** No video credits spent (all
Unlimited, correctly zero). Not authorized in advance, disclosed here in
full per org rule on never hiding an overspend.
