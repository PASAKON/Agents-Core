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

## Phase 3 — S0b

Not started. Lint pre-checked clean, `--chips` expects 3:
`loc_hall_big_e`, `project_absence_char_cleaner_c`, `project_absence_prop_cart_a`.

## THE ONE SLOT

S20 (`7a1c376d-…`) holds the Unlimited slot as of this report. S2PT take 3
will not fire until S20 leaves `queued`/`Processing`/`Generating`.
