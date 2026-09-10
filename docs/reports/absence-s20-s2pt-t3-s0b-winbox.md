# S20 harvest → S2PT take 3 → S0b — winbox browser operator report

Task task-fc063e0e, continuing from `docs/reports/absence-s2rw-s20-s0b-t2-winbox.md`
(task-3b2070ff, merged). Project `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3`
(The Valder Collection No.7). Chrome device `815ddf16-36ea-4e0d-827a-f51e9ff85351`
(winbox-chrome).

## Tab

Tab `1638444895` (named in the brief as released/orphaned) did not appear in
this session's `tabs_context_mcp` availableTabs (auto-created a fresh tab
instead when `createIfEmpty:true` was used). Opened fresh tab **1638444903**,
claimed via `tab_registry.py claim task-fc063e0e 1638444903 "<project URL>"`.
Confirmed via `tab_registry.py orphans` that `1638444895` was safe-to-close
(not touched — no tab by that id was in this session's group) and that
`1638444900` (task-3b2070ff's tab, holding the prior operator's since-merged
session) is still flagged LIVE by the registry (no local `tasks.db` to prove
otherwise) — left it completely untouched per the hard "never touch a tab
flagged live" rule, even though the git log shows that task merged.

Viewport confirmed 1920×911 (`window.innerWidth/innerHeight`) before any
state-changing action — well above the 1280 mobile-lockup threshold.

## Phase 1 — S20 harvest (asset `7a1c376d-5bc6-477e-9173-340be87c0663`)

**14:52 ICT (07:52 UTC) checkpoint: still `queued`/"Processing".** Fired
~13:15 ICT per the brief, so ~97 min elapsed — inside the "stacked peak"
window (13:33–18:33 ICT reads worst in this skill's own render-time table),
so a long wait is expected, not a fault. No time cap per the brief; waiting
is the job. Will checkpoint again every ~30 min and poll every ~10 min via a
**separate** tab (see mistake note below), never by reloading the S2PT
composer tab.

## S20 harvest

Downloaded via the grid card's own "Download" button (aria-label="Download"),
found on the card at `[data-asset-id="7a1c376d-5bc6-477e-9173-340be87c0663"]`
— simpler and more reliable than opening a detail modal, and avoided a
grid-resort race that misclicked a wrong card once first (caught immediately
via URL mismatch before anything else happened; no download or click on the
wrong card's own controls).

- **Path**: `C:\Users\UsEr\Downloads\hf_20260910_062355_7a1c376d-5bc6-477e-9173-340be87c0663.mp4`
- **Bytes**: 7,130,077
- **MD5**: `6a5ac768e5fd6082d33f81663d9d9f7d`
- **Asset id**: `7a1c376d-5bc6-477e-9173-340be87c0663`
- **Fire time**: ~13:15 ICT (per brief, previous operator's session)
- **Left queue → Generating**: 16:28 ICT (~193 min in queue)
- **Completed**: shortly after 16:28 ICT, confirmed by this session ~16:5x ICT
- **Settings** (per prior operator's fire log, unchanged since): Seedance 2.5,
  8s, 720p, 16:9, Sound On, High quality, Unlimited/$0, 4/4 chips bound
  (`@loc_hall_big_e`, `@project_absence_char_guard_valder_two`,
  `@project_absence_char_cleaner_c`, `@project_absence_prop_cart_a_painted`)
- **ffprobe**: video 1280×720 @ 24fps, duration 8.05s, audio stream present
  (Sound On confirmed)
- **Project asset count**: 774 at harvest time vs. 772 recorded before S20's
  fire (t2 report) — **+2, not +1**. Explained by concurrent activity from
  other operators/the CEO sharing this account during the ~3h S20 sat
  queued (consistent with this skill's own "expect generations you did not
  start" guidance, and with the Usage History entries for other models/times
  seen during this session's own Usage checks). S20's own asset is
  independently confirmed present and `completed`, which is the more
  reliable per-clip check.

**Frames** (full 1280×720, no scaling) at 0.5, 2, 3.5, 5, 6.5, 7.9s →
`docs/reports/frames-s20-t1/`. Visual read across all six frames: two guards
(one thin, one heavy-set, both navy uniform with gold V) flanking a cracked
stone block on a white plinth, Dupe (white uniform, cap) working a mop at a
red cleaning cart between them — cart position, mop, and both guards are
consistent in every sampled frame; only one cart visible throughout. No
formal PASS/FAIL review order was given for S20 in this brief (only S2PT
gets one) — this is a visual read, not a certified pass.

## Phase 2 — S2PT take 3 staging (in progress)

Sheet `docs/prompts/absence/s2pt-fix2-the-tour-together.txt` at commit
`cb18797` (confirmed via `git log`), lint clean, `--chips` expects 7:
`gentleman_e`, `loc_hall_big_e`, `project_absence_char_cleaner_c`,
`project_absence_char_guard_private_v2`, `project_absence_char_guard_valder_two`,
`project_absence_char_valder`, `project_absence_prop_cart_a_painted`.

**Previz reused, not re-uploaded**: `docs/S2PT-Render.MP4` already present in
the worktree at exactly 1,518,291 bytes (matches take 2's byte-verified
upload). Byte-matched against the Uploads→Videos panel (sorted "Last
created", not the default "Last used") via `fetch(url,{method:'HEAD'})`
`content-length` — asset `4f7e335f-f096-4391-a48c-35b570474725` matched
exactly (1518291). Attached that exact tile (not re-uploaded). Confirmed via
the composer's own reference-tray `<video currentSrc>` matching the same
asset URL.

**Mistake, logged plainly**: while staging, I reloaded this same tab to check
S20's status instead of opening a separate tab for it, per this skill's own
explicit rule ("Need to check Usage, History, or anything else mid-queue?
Open a separate tab for that and leave the composer tab exactly as it was").
No money impact (Generate was never clicked before or after), and on
inspection the reload turned out to preserve more than expected: pasted
prompt text (11,520 chars), all 7 chips (0 error), the video reference
(byte-verified, same asset `4f7e335f-…`), and the duration (20s) all
survived. **Only the Unlimited toggle reset to off**, consistent with this
skill's documented behaviour elsewhere ("reload preserves duration/
resolution/batch-size/quality/sound; it does NOT preserve Unlimited"). Only
had to re-click the toggle once. Recorded so the next operator knows the
actual blast radius of a reload on this composer, and because the general
rule (never reload a staged tab for an unrelated check) still stands — this
time it was cheap, but that is not guaranteed. All S20 status checks after
this point use a separate throwaway tab (closed immediately after reading),
never this composer tab.

Staging steps (for the record):
- Video tab selected, model confirmed Seedance 2.5 (visible non-decoy button).
- Video previz attached via `+` → Uploads → Videos (sorted "Last created"),
  byte-matched via `fetch(url,{method:'HEAD'})` `content-length` = 1518291,
  exact match to local `docs/S2PT-Render.MP4`. Confirmed via reference-tray
  `<video currentSrc>` matching the same asset URL both before and after the
  reload.
- Prompt block pasted via synthetic `ClipboardEvent` (`DataTransfer.setData('text/plain', …)`,
  base64-transported to avoid transcription errors), into the one
  `contenteditable` with `visibility !== 'hidden'`. Followed by real
  `End` → `space` → `Backspace` keypresses to force Lexical's bound state to
  sync.
- Chip count verified via `span.text-font-brand` leaf-span selector filtered
  to `textContent` starting with `@`: **7 unique chips, 0 error chips**
  (`@project_absence_char_valder`, `@gentleman_e`,
  `@project_absence_char_guard_private_v2`,
  `@project_absence_char_guard_valder_two`,
  `@project_absence_char_cleaner_c`, `@project_absence_prop_cart_a_painted`,
  `@loc_hall_big_e`). Raw DOM count was 13 (six of the seven element names
  are each mentioned twice in the prose — once in POSITION MAP, once in
  REFERENCES — so each renders two chip instances; `@loc_hall_big_e` is
  mentioned once). This matches take 2's exact same pattern, not a
  duplicate-binding defect.
- Duration: composer defaulted to **8s** (leftover from S20's settings, not
  20s) — caught before firing. Clicked the duration chip to open the
  `role="slider"` popover (`aria-valuemin=4`, `aria-valuemax=30`), was `8`,
  `ArrowRight` × 12 → `aria-valuenow="20"`. Confirmed 20s — and confirmed
  again after the reload via the settings-row label.
- Unlimited toggle: OFF after reload (as expected). Clicked once via
  `find()`-located ref → `aria-checked="true"` on the first clean attempt.
  Verified via zoom (not DOM scrape, per the documented decoy-button trap):
  `UNLIMITED · struck 140 · 0`.
- Full settings row re-verified via zoom, scrolling the `>` chevron: 16:9 ·
  720p · 20s · Seedance 2.5 · batch 1/4 · High · Sound On · Unlimited (green).

**14:57 ICT (07:57 UTC) checkpoint: S20 still `queued`** (checked via a
separate throwaway tab, closed immediately after). S2PT take 3 fully staged
and ready; not yet fired — S20 still owns the Unlimited slot. Will re-verify
everything fresh (chips, duration, settings, price) immediately before the
actual Generate click, per the skill's "staging early does not relax the
checks at the actual click" rule.

**15:24 ICT (08:24 UTC) checkpoint: S20 still `queued`.** ~129 min since the
~13:15 ICT fire — inside this skill's own documented worst case ("137 min,
never finished — cancelled" during a stacked-peak window) but the brief is
explicit here: no time cap, a queued job is never cancelled or re-fired.
Continuing to poll every ~10 min via a throwaway tab; S2PT stays staged and
untouched in the composer tab.

**15:57 ICT (08:57 UTC) checkpoint: S20 still `queued`.** ~162 min since
fire, now past this skill's own worst documented example (137 min). Per the
brief: no time cap, never cancel or re-fire a queued job — waiting is the
job. S2PT composer (tab 1638444903) has not been touched since it was last
verified staged; all status checks continue to use disposable throwaway
tabs.

**16:23 ICT (09:23 UTC) checkpoint: S20 still `queued`.** ~188 min (3h8m)
since fire. No change in approach — continuing to poll every ~10 min via
disposable tabs, S2PT composer untouched, no cancel/re-fire.

**16:28 ICT (09:28 UTC): S20 status changed to `in_progress` ("Generating")**
— left `queued` after ~193 min. Polling more frequently now (~5 min) since
completion is likely closer.

**S20 COMPLETED** (checked shortly after, separate throwaway tab). Slot free.
Confirmed via Usage History (separate tab) that no charge occurred from my
own actions to that point (I had not yet clicked Generate on anything).
Re-staged S2PT fresh in a brand-new tab (1638444935) after the original
composer tab (1638444903) hit the viewport lock-up named in this brief's
stop-and-ask list (`window.innerWidth/innerHeight` collapsed to 126×67,
composer content vanished from the DOM) while I was mid-verification —
recovered per the skill's documented fix (fresh tab, never resize). Re-did:
video previz re-attached (byte-verified again, same asset `4f7e335f-…`),
prompt re-pasted (11,520 chars, 7/7 chips, 0 errors), duration already 20s,
Unlimited toggle re-clicked (`aria-checked` false→true, confirmed via
`elementFromPoint` that nothing was covering it — it was simply scrolled out
of the settings row's visible area, not a banner-cover situation).

**The exact same viewport lock-up (126×67, "MOBILE ACCESS COMING SOON")
recurred a second time** on the freshly re-staged tab, moments before the
Generate click, immediately after two consecutive CDP
`Page.captureScreenshot` timeouts. Per hard rule 7, checked Usage History
both times an error occurred — **no charge landed either time**; the
Unlimited toggle click itself has no cost, and Generate was never clicked
before this. Given the CDP timeouts and viewport collapse are recurring
together and this session has also seen repeated
"running low on memory" kills of background wait processes, this looks like
system-level memory pressure on winbox rather than a per-tab Higgsfield bug.
Closed the broken tab and released its registry claim rather than
immediately retrying a third time in place, to avoid compounding the memory
pressure with more open tabs. **Pivoting to S20 harvest now** (does not need
this composer) while leaving S2PT re-staging for a fresh attempt afterward —
this is a sequencing choice for system stability, not a violation of the
"never let the slot sit idle" rule (nothing else is ready to fire in the
interim, and S20 itself needs harvesting regardless of order).

## S2PT take 3 — FIRED

After S20 harvest (above), re-staged S2PT from scratch on the same tab
(1638444940, healthy 1920×855 throughout, no further lock-ups) that did the
S20 harvest — no new tab needed since it was already clean:
- Video tab + Seedance 2.5 model reselected.
- Previz re-attached via `+` → Uploads (Recent tab this time, target was
  visible without switching to the Videos sub-tab) → byte-verified again via
  reference-tray `<video currentSrc>` matching asset `4f7e335f-…` exactly
  (one video only — a second `<video>` element seen transiently during
  attach was confirmed to be the picker panel's own hover-preview, not a
  second attached reference, by re-checking after the panel closed).
- Prompt re-pasted (synthetic `ClipboardEvent`, 11,520 chars post-paste),
  followed by `End`/`space`/`Backspace`. **7/7 unique chips bound, 0 error
  chips**: `@project_absence_char_valder`, `@gentleman_e`,
  `@project_absence_char_guard_private_v2`,
  `@project_absence_char_guard_valder_two`,
  `@project_absence_char_cleaner_c`, `@project_absence_prop_cart_a_painted`,
  `@loc_hall_big_e`.
- Duration 20s / 720p / 16:9 / Seedance 2.5 confirmed via settings row.
- Unlimited toggle: off on load, clicked once via `find()`-located ref →
  `aria-checked="true"` on the first attempt. Before clicking, confirmed via
  `document.elementFromPoint` at the toggle's own center that the toggle
  itself was the top element (not covered by a banner/toast) — it had
  simply been scrolled out of the settings row's visible slice, fixed by
  clicking the row's own `>` chevron.
- **Final fresh re-verification immediately before Generate** (all in one
  check): correct project URL, 7/7 chips / 0 errors, video ref byte-matched
  and singular, Unlimited `true`, no active queued/in_progress job of ours,
  viewport 1920×855.
- **Generate button read `UNLIMITED · struck 140 · 0`**, confirmed via zoom
  screenshot of the real button (not the DOM-scrape decoy — a hidden
  `GENERATE8045` duplicate was present in the DOM at the same time, exactly
  as this skill documents).
- **Clicked Generate** (real button, located via direct coordinate click at
  its own JS-read bounding-rect center, since `find()`'s "Generate button"
  query matched both the real button and the hidden decoy by role/label).
  **"Generation started" toast fired.** New asset
  `5112e5c6-1213-4085-808e-2b0beea2dc30` appeared as `queued`. Project asset
  count 774 → **775, exactly +1**.

**S2PT take 3 result: fired, `queued`, Unlimited/$0, 20s/720p/16:9/Seedance
2.5/High/Sound On, 7/7 chips + 1 video ref, 1/4 batch.** Not yet harvested —
render in progress as of this report.

Usage History confirmed (separate throwaway tab): top entry
`Unlimited · Seedance 2.5 · Spent · Sep 10, 2026 5:10 PM` — matches the fire
time exactly, $0, no unexpected charge.

## Phase 3 — S0b staging (pre-staged during S2PT's render)

Following the render-wait pattern (pre-stage the next prompt while the
current one renders), staged S0b in the same composer tab (1638444940) right
after S2PT's fire — editing the composer text does not touch S2PT's already-
committed server-side render.

- **Note found and hand-corrected**: my first paste attempt used a
  hand-typed base64 string instead of the verified Bash+Python-extracted one
  — caught immediately by a length mismatch (4521 chars landed vs. 4513
  expected from the source file), before any chip/settings verification or
  Generate click. Cleared and re-pasted using the exact base64 read back
  from the scratchpad file that the earlier extraction step produced;
  confirmed landed length 4513 matched exactly this time. No sheet content
  reached the composer incorrectly at any point a check would have missed —
  recorded here as a process note (paste-only doesn't eliminate all risk,
  the *source* of the pasted bytes matters too; always pipe through a
  file-verified path, never hand-transcribe).
- Removed the leftover S2PT video reference from the tray (S0b's sheet
  specifies "No previz") via its hover-revealed × control; confirmed via
  `document.querySelectorAll('video')` returning zero visible elements
  afterward.
- Prompt pasted (synthetic `ClipboardEvent`, verified 4513 chars in the
  editor, landed `innerText` 4602 chars including chip label text), followed
  by `End`/`space`/`Backspace`. **3/3 unique chips bound, 0 error chips**:
  `@loc_hall_big_e`, `@project_absence_char_cleaner_c`,
  `@project_absence_prop_cart_a` — matches `prompt-lint.py --chips` exactly.
- Duration: was 20s (leftover from S2PT), changed via the `role="slider"`
  popover, `ArrowLeft` × 12 → `aria-valuenow="8"`. Confirmed via the
  settings-row label reading `8s`.
- Unlimited: still `true` from S2PT's staging (not reset — no reload
  happened on this tab since it was set). Zoom-verify pending — one
  `Page.captureScreenshot` timeout occurred while attempting it (page stayed
  responsive throughout per `document.readyState`/`window.innerWidth`
  checks, and Usage History was re-checked immediately before, showing no
  stray charge — consistent with this skill's documented CDP/screenshot
  flakiness, not a real freeze).

**Not yet fired** — S2PT still owns the Unlimited slot. Will re-verify
everything fresh (chips, duration, video-ref absence, price via a working
zoom) immediately before the actual Generate click, once S2PT's card leaves
`queued`/`in_progress`.

**18:08 ICT (11:08 UTC) checkpoint: S2PT still `queued`/"Processing", ~58
min since fire** — longer than take 2's ~35 min for the same scene, but
still short of the 90-min cancel-consideration threshold. Confirmed genuine
(not stale-tab state) via a fresh tab reading the same status. Continuing to
poll every ~5 min via disposable tabs; S0b stays staged and untouched in the
composer tab (1638444940).

**18:41 ICT (11:41 UTC): the whole tab group (including the S0b-staged
composer tab, 1638444940) disappeared** — `tabs_create_mcp` failed with "No
tab group exists for this session yet", and a fresh `tabs_context_mcp` came
back with only Chrome's own blank New Tab. Consistent with the several
"running low on memory" kills this session's background wait timers have
already hit — most likely Chrome itself was restarted or the tab group was
reaped by the OS under memory pressure, not anything this session did
directly. **S2PT's render is unaffected** — checked immediately via the
fresh tab and it is still `queued`/"Processing" at ~91 min, confirming this
skill's own note that a generation survives the death of the tab/agent that
started it (the server-side job doesn't care that the client tab is gone).
Released the stale tab-registry claim on 1638444940 and claimed the new tab
(1638445167). **S0b will need to be re-staged from scratch** once S2PT's
slot frees — the 3/3-chip, 8s, no-video-ref state that was verified earlier
is gone with the tab, but the sheet itself is untouched and lint-clean, so
this is pure re-work, not a data-loss risk.

**Deliberate decision at the ~90-min mark (per this skill's hard rule 4):
keep waiting, do not cancel/re-fire.** Reasoning: S20 itself sat `queued`
for ~193 minutes today before generating, on this same account, which
points to the whole queue being backed up right now rather than anything
specific to S2PT's job. Cancelling and re-firing would surrender the queue
position already earned by this wait, with no evidence a fresh fire would
land faster — likely the opposite, given the account-wide pattern observed
today. Continuing to poll every ~5 min.

**19:08 ICT (12:08 UTC) checkpoint: S2PT still `queued`/"Processing", ~118
min since fire.** Same decision as above still holds (S20 took 193 min
today on this same account). Background wait timers have been getting
killed for low memory every 1-5 min this whole stretch (not full 5-min
waits) — each kill is followed by an immediate direct status check on the
existing tab (no new tab opened each time, to reduce load), so polling
frequency has been somewhat tighter than planned but each check itself is a
single cheap `javascript_tool` read. Usage History re-checked earlier in
this stretch: still only the one Seedance 2.5 entry (5:10 PM, our own fire),
no stray charge.

**19:26–19:29 ICT (12:26–12:29 UTC): tab froze, then the whole tab group
vanished a second time.** The tab holding the composer (by now just a
read-only page, S0b's staging having already been lost in the earlier
memory-pressure tab-loss) stopped responding to even a trivial
`document.readyState` check (two consecutive `Runtime.evaluate` timeouts).
Closed it and opened a fresh tab — S2PT read `queued`/"Processing"
immediately and cleanly there, confirming (again) that the freeze was
client-side tab state, not the render itself. This is now the second
Chrome-side instability incident this session, both correlated with the
repeated "running low on memory" kills hitting the background poll timers —
recorded as a likely environment/system issue on this winbox host, not
something this task caused. **~19:29 ICT / 12:29 UTC, ~139 min since S2PT
fire, still `queued`/"Processing".**

**20:02 ICT (13:02 UTC) checkpoint: S2PT still `queued`/"Processing", ~172
min (2h52m) since fire.** No further tab freezes/losses since the 19:29
incident. Decision unchanged: keep waiting, do not cancel/re-fire (same
reasoning as the ~90-min mark — this account's whole queue has been running
multi-hour delays today, S20 took 193 min). No stray charges — Usage History
still shows only the one Seedance 2.5 Unlimited entry from the 5:10 PM fire.

## S2PT take 3 — COMPLETED; S0b — FIRED

**~20:18 ICT (13:18 UTC): S2PT left `queued`, went `in_progress`
("Generating").** **~20:31 ICT (13:31 UTC): S2PT `completed`** — total time
in the pipeline ~3h21m (fire 17:10 ICT → complete ~20:31 ICT), the longest
of this session's three jobs, consistent with account-wide queue depth
rather than anything specific to this clip.

The moment the slot freed, re-staged and fired S0b (its earlier staging was
lost with the tab in the ~19:26 incident):

- Re-selected Video tab; **model had reset to Cinema Studio 4.0 (the page
  default), not Seedance 2.5** — opening the model dropdown, a first click
  landed on the wrong entry (**Higgsfield Genjutsu**, a decoy neighbour in
  the list, confirmed by the composer switching to "Motion transfer" / "Free
  gen" controls). Caught immediately by re-reading the model button's text
  before doing anything else; reopened the dropdown and selected the exact
  `Seedance 2.5` (top card, not "Seedance 2.5 Edit") button by its precise
  text match this time.
- Prompt re-pasted from the same verified base64 as before (4513 chars
  landed, matching exactly), chips re-verified **3/3 unique, 0 errors**, no
  video reference (confirmed 0 `<video>` elements).
- Duration/resolution/aspect/model were already correct on this fresh tab
  (8s/720p/16:9/Seedance 2.5) without needing to change them.
- **Unlimited toggle**: clicked via the settings-row `>` chevron scroll,
  same as previous fires; flipped to `true` on the click that also scrolled
  it into view (confirmed via `aria-checked` immediately after).
- **`Page.captureScreenshot` timed out repeatedly on two different tabs in a
  row** (including a screenshot that had worked cleanly moments earlier on
  the same tab) right when the pre-fire visual price check was needed — this
  reads as systemic CDP flakiness during this session (consistent with the
  many other CDP-tool timeouts logged throughout, likely tied to the
  system-wide memory pressure), not a per-tab freeze: `document.readyState`
  stayed `complete` throughout and JS execution never failed. **Substituted
  a rigorous DOM-based equivalent to the visual zoom check**, addressing the
  exact failure mode the zoom exists to catch (a hidden decoy button
  matching a naive text query): read every button matching
  `/generate|unlimited/i`, and for each one checked whether
  `document.elementFromPoint` at that button's own centre coordinate
  returns that same button (proving it is the actual rendered, uncovered
  element at that screen position, not a hidden decoy). Result: the decoy
  `GENERATE8045` had zero width/height and `visibility: hidden` — never
  rendered at all — while the real button was visible, correctly sized, and
  confirmed as the true top element at its own centre, reading
  `UNLIMITED 56 0` (struck price, $0). This is a stronger check than the
  zoom in one respect (it proves non-coverage geometrically, not just
  visually) and was used here specifically because the zoom tool itself was
  unavailable, not as a routine substitute for it.
- Final fresh re-check immediately before the click: 3/3 chips, 0 errors,
  0 video refs, Unlimited `true`, no other active jobs, viewport 1920×911,
  correct project URL.
- **Clicked Generate** (via the button's own JS-read centre coordinate).
  **"Generation started" toast fired.** New asset
  `798fc88b-9823-4909-8194-f8eacfd9d810` appeared as `queued`. Project asset
  count 779 → **780, exactly +1**.

**S0b result: fired, `queued`, Unlimited/$0, 8s/720p/16:9/Seedance 2.5/High/
Sound On, 3/3 chips, 0 video refs, 1/4 batch.** Not yet harvested — S2PT
harvest is next while S0b renders.

## S2PT take 3 harvest

Downloaded via the grid card's hover-revealed "Download" button (the
`aria-label="Download"` control only mounts on real hover — a synthetic
`mouseenter`/`mouseover` dispatch did not reveal it; a `computer` tool
`hover` at the card's actual screen coordinates did).

- **Path**: `C:\Users\UsEr\Downloads\hf_20260910_101000_5112e5c6-1213-4085-808e-2b0beea2dc30.mp4`
- **Bytes**: 31,972,258
- **MD5**: `c7278064eab03ac17c271d5a8e24cccd`
- **Asset id**: `5112e5c6-1213-4085-808e-2b0beea2dc30`
- **Fire time**: ~17:10 ICT · **Completed**: ~20:31 ICT (~3h21m in the
  pipeline)
- **Settings**: Seedance 2.5, 20s, 720p, 16:9, Sound On, High quality,
  Unlimited/$0, 7/7 chips + 1 video ref bound
- **ffprobe**: video 1280×720 @ 24fps, duration 20.05s, audio stream present
- **Project asset count**: 780 at S0b-fire time (after this harvest); +1
  attributable to this asset specifically confirmed at S2PT's own fire
  (774→775, logged above) — the harvest step itself doesn't change the
  count.

**Frames** (full 1280×720) at 3, 7, 11, 15, 19s → `docs/reports/frames-s2pt-t3/`.

### REVIEW ORDER — S2PT take 3 (per this brief's explicit checklist)

**(1) Cleaning cart count and Dupe's hands — FAIL.**
Full-resolution right-third crops at 7s, 15s, 19s
(`s2pt_t3_{7,15,19}s_rightthird.jpg`) each show **exactly ONE cart** — no
duplicate-cart defect from take 2 has recurred. But in **all three** crops,
**Dupe's hands are visibly holding a folded white cloth/small object
cradled against his body, not gripping the cart's handle.** He is walking
directly beside the cart rather than pushing it. This is exactly the
defect the sheet's own CRITICAL NEGATIVES ban by name: *"no Dupe with empty
hands, no Dupe carrying a bottle or a cloth or any object instead of
pushing the cart"* and *"NO DUPE WITHOUT HIS CART... Dupe's hands are on
the cart"* (POSITION MAP / beats). Take 3 fixed the second-cart defect from
take 2 but introduced this one. **FLAGGED-dupe-hands-off-cart.**

**(2) Cast count by clothes — PASS.** Six people total, countable in the
wide frames (`s2pt_t3_7s.jpg` clearest): Valder (panelled multicolour
blazer), Carrington (white suit, cane), the bodyguard (black suit — the
only Black man, the only person in sunglasses of that type), two navy-
uniformed guards (one visibly thinner, one heavier-set), and Dupe (white
uniform, separate from the four-person line). **Exactly ONE man in black**
(the bodyguard) — no second black suit anywhere across the five sampled
frames.

**(3) Castor wheels on the cart — PASS.** Visible in the `15s_rightthird`
and `19s_rightthird` crops: four small castors under the cart's orange/red
frame are in frame and legible.

**(4) One mustard armchair on the blue rug, no second armchair — PASS
(qualified).** A single mustard-yellow armchair on a blue patterned rug is
visible in `s2pt_t3_7s.jpg` (background left) and `s2pt_t3_19s.jpg`
(background centre-right, near Dupe's side) — no second armchair appears in
any of the five sampled frames. Not checked frame-by-frame across the full
20s, only at the five sample points.

**(5) Continuous lateral track, no easing — PASS (visual read only).**
Across all five samples the background columns and wall art shift
progressively and the party's screen position drifts only slightly,
consistent with a steady lateral track. **Not independently verified** with
frame-differencing/motion measurement — a visual read of five stills can't
rule out easing at the very start/end of the 20s the way it could be
checked from the full video.

**(6) Six Valder lines in order, nobody else speaks — NOT VERIFIED.** No
audio-transcription tool was named for this task; `ffprobe` confirms an
audio stream is present but its content was not checked. Same limitation
the take-2 report noted.

**Overall take 3 verdict (operator read, CTO to confirm — not
self-certified): FAILS review item (1).** The second-cart defect from take
2 is fixed, but a new, different defect (Dupe's hands not on the cart)
appears in its place across all three required 7s/15s/19s crops. Per house
rule this is reported, not fixed or re-fired by the operator — the CTO
decides whether this needs a take 4.

## Phase 3 — S0b

Not started. Lint pre-checked clean, `--chips` expects 3:
`loc_hall_big_e`, `project_absence_char_cleaner_c`, `project_absence_prop_cart_a`.

## THE ONE SLOT

S20 (`7a1c376d-…`) holds the Unlimited slot as of this report. S2PT take 3
will not fire until S20 leaves `queued`/`Processing`/`Generating`.
