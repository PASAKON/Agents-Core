# «บัญชี» Act 1 shoot — A2 (shots 1–24) — 2026-09-18

Second attempt. Shot sheet re-read fresh from disk before every fire (per skill).
Shots 8, 22, 23, 24 were flagged mid-run by CTO as changed on disk — each was
re-read from `docs/scripts/banchi-ACT1.md` immediately before its fire, not
used from the earlier memory of the sheet. Confirmed in the table below.

## Route

Step 5 (text/JS) for verification, `computer` clicks by ref/coordinate for
state-changing actions (per `browser-operator` skill's cost ladder) — task
gives the shot sheet directly, no API for Flow generation exists.

## Settings — verified in the panel before every submit

**Omni 1.1 Flash · โหมด องค์ประกอบ · 9:16 · 720p · 8 วินาที · x1**, confirmed
unchanged (survived a mid-run page navigation) via the settings pill at 16:14
and again after tab reset. Estimate read **12 เครดิต** per shot, matching every
actual deduction.

## Credit ledger

Balance is the **shared project pool** — the other operator (shots 25–48) was
firing concurrently in the same Flow project, so deltas below include their
spend too. My own submitted-shot count × 12 credits is the isolated number to
judge against the 340 cap.

| Checkpoint | Balance | My shots submitted so far | My isolated spend (×12) |
|---|---|---|---|
| Before shot 1 | 9,953 | 0 | 0 |
| After shot 6 | 9,857 | 6 | 72 |
| After shot 10 | 9,749 | 10 | 120 |
| After shot 14 | 9,641 | 14 | 168 |
| After shot 19 | 9,545 | 19 | 228 |
| Final (after all 24 fired + retries) | 9,413 | 24 | **288** |

**288 credits, 52 under the 340 cap.** Never approached the cap; never clicked
Upgrade/Subscribe/Buy credits.

**Interference signal:** pool dropped 540 credits total (9,953→9,413) while I
spent an isolated 288 — the remaining ~252 is the other operator's shots 25–48
firing in the same window. This is the expected signature of two operators
sharing one account's credit pool, not an anomaly.

## Shot table

All chips verified by **thumbnail image**, not row label, before every
submit (the noodle_shop / noodle_shop_thriving near-namesake pair came up on
every search — confirmed the plain `@noodle_shop` each time). All settings
re-verified after the one page navigation mid-run.

| # | Submit time | Chips attached, in order (→REF_N) | Downloaded | Notes |
|---|---|---|---|---|
| 1 | 16:02:11 | lung_somchai→0, side_wall→1 | ✅ | |
| 2 | 16:02:54 | lung_somchai→0, side_wall→1 | ✅ | |
| 3 | 16:03:45 | lung_somchai→0, staircase→1 | ✅ | |
| 4 | 16:04:46 | lung_somchai→0, grandma_pranom→1, upstairs_bedroom→2 | ✅ | |
| 5 | 16:05:22 | grandma_pranom→0, upstairs_bedroom→1 | ✅ | |
| 6 | 16:06:08 | lung_somchai→0, grandma_pranom→1, upstairs_bedroom→2 | ✅ | |
| 7 | 16:07:05 | lung_somchai→0, upstairs_bedroom→1 | ✅ | |
| 8 | 16:07:42 | lung_somchai→0, upstairs_bedroom→1 | ✅ | **Re-read from disk at fire time** — line changed to "เดือนนี้...ไม่พออีกแล้ว" |
| 9 | 16:08:19 | noodle_shop→0, lung_somchai→1 | ✅ | location-first order, verified thumbnail |
| 10 | 16:08:56 | lung_somchai→0, noodle_shop→1 | ✅ | |
| 11 | 16:10:18 | nong_daeng→0, noodle_shop→1 | ✅ | |
| 12 | 16:11:00 | lung_somchai→0, nong_daeng→1, noodle_shop→2 | ❌ | **Flow player bug — see below** |
| 13 | 16:11:33 | nong_daeng→0, noodle_shop→1 | ❌ | **Flow player bug** |
| 14 | 16:12:19 | nong_daeng→0, noodle_shop→1 | ❌ | **Flow player bug** |
| 15 | 16:14:42 | lung_somchai→0, noodle_shop→1 | ✅ | |
| 16 | 16:15:20 | lung_somchai→0, noodle_shop→1 | ❌ | **Flow player bug** |
| 17 | 16:15:57 | nong_daeng→0, noodle_shop→1 | ✅ | |
| 18 | 16:16:39 | lung_somchai→0, nong_daeng→1, noodle_shop→2 | ✅ | |
| 19 | 16:17:10 | street_front→0 (only) | ✅ | no character — vendor voice intentionally random, per sheet |
| 20 | 16:18:17 | lung_somchai→0, noodle_shop→1 | ✅ | |
| 21 | 16:18:52 | nong_daeng→0, noodle_shop→1 | ❌ | **Flow player bug** |
| 22 | 16:19:33 | nong_daeng→0, staircase→1 | ✅ | **Re-read from disk** — location changed noodle_shop→staircase, attach order + line changed |
| 23 | 16:20:11 | nong_daeng→0, noodle_shop→1 | ✅ | **Re-read from disk** — action text changed (steps back in from stairwell) |
| 24 | 16:20:51 | lung_somchai→0, noodle_shop→1 | ✅ | **Re-read from disk** — action text changed (son comes back in, reads face) |

**19/24 downloaded and verified at exactly 8.00s. 5/24 (shots 12, 13, 14, 16,
21) generated successfully — confirmed via each clip's timeline filmstrip
showing real, in-motion frames matching the prompt — but never became
downloadable.**

## Flow reports zero failures

No shot ever showed the `ล้มเหลว` failure card. Every one of the 24
generated a real clip with real motion in the filmstrip. The 5 missing clips
are a **download-path bug, not a generation failure** — nothing to refund,
nothing mis-charged.

## The blocker: Flow's own clip player never loads for 5 of 24 clips

This is the skill's documented "in-page video player can fail completely"
trap (`google-flow-ops`, 2026-09-18 entry), but worse than described there:
that entry treated it as occasional; here it was **persistent and did not
clear** across every recovery step tried:

1. `document.querySelector('video')` → `null` on all 5, repeatedly, while the
   timeline filmstrip rendered real motion frames for every one of them.
2. `read_network_requests` filtered to `flow-content.google/video` → zero
   hits, on first load and after reload.
3. Reload the exact `/edit/<id>` URL → no change.
4. Navigate away and back → no change.
5. **Fresh tab** (closed the working tab via `tab_registry.py release` +
   `tabs_close_mcp`, opened a new one, re-claimed it) → no change for the
   already-stuck clips, but a **brand-new, never-tried clip (shot 15) loaded
   correctly on the very same fresh tab** seconds later. This proves the bug
   is **per-clip, not per-tab or per-session** — confirms it is *not* the
   kind of Chrome-tab-group destruction the skill also documents.
6. Final re-check on all 5, after ~20+ minutes of elapsed time (well past
   any plausible encode-finishing delay) → still zero video requests on all
   five.

**Per the CTO's mid-task instruction, clicking Play was stopped immediately
once flagged** (his Mac speakers were audible during the recovery attempts
before that instruction arrived — see Issues below). All later re-checks used
navigation + `read_network_requests` only, no play clicks.

```
SKILL-CONTRADICTION: google-flow-ops :: "The in-page video player can fail
  completely — pull from the CDN instead" (implies play-and-capture is a
  reliable workaround once you know to look for the network request)
  :: on 5/24 clips this run, no amount of play-click, reload, re-navigate,
  or fresh tab ever produced the CDN request — the workaround itself is
  what failed, not just the in-page player. The existing rule ("pull from
  CDN instead") remains correct advice per-clip; what's missing is that a
  clip can be stuck with NO working retrieval path at all, and the fix
  there is unknown (untested: does it ever self-resolve? is there an
  alternate endpoint the UI never surfaces?).
  :: 2026-09-18, task-abc83ea2, asset ids 7c463388-9716-4631-a62e-65beaed3c29f
  (shot 12), 56e0fd54-521c-43cf-9601-066a847cf259 (shot 13),
  a9c33633-df75-46b0-9b3b-7a305481ae24 (shot 14),
  0e10f38b-5bf9-48f1-a334-7e8e76779c73 (shot 16),
  1510f4c3-06f5-453c-b265-3785625b6985 (shot 21).
```

## Interference from the other operator

Only signal available was the shared credit pool: **540 total credits spent
against my isolated 288**, consistent with the other operator's shots 25–48
running in parallel as briefed. No tab conflicts, no destroyed tab group, no
generation I didn't submit appeared in my searches (every search was scoped
to a single, exact Thai dialogue line unique to my own shots — see Method
below — so I never had to judge "is this mine" by eye).

## Method for retrieval (worth carrying into the skill)

With two operators firing into the same project concurrently, the media grid
interleaves both operators' clips by creation time, and — the actual trap —
**several of the two operators' prompts share identical opening boilerplate**
("...character reference for the older man... younger man...") because both
halves of the script reuse the same characters. Row-label or prompt-prefix
matching is not reliable here.

**What worked**: Flow's own top-bar search (`ค้นหา`) full-text-matches
against the complete prompt, including the embedded Thai dialogue line. Since
every shot's spoken line is unique even across both operator's halves, a
search on that exact line reliably narrows the grid to exactly one card. This
is faster and far more reliable than scrolling the virtualized grid (tried
first — `cdk-virtual-scroll-viewport` only keeps ~7 items rendered at a time,
so a linear or scroll-based census is expensive and lossy: it undercounted a
28-card sweep against a project holding 50+ generations).

```
SKILL-ADDITION candidate: google-flow-ops :: to find/verify a specific clip
  in a project with concurrent operators, search the top bar for a unique
  substring of that shot's own Thai dialogue line, not the character/location
  chip names (which repeat across shots) or the prompt's opening boilerplate
  (which is often near-identical between shots sharing the same characters).
  One search reliably returns exactly one card.
```

**Search input caveat**: typing text containing `...` (the ellipsis used in
several dialogue lines, e.g. "เดือนนี้...ไม่พออีกแล้ว") sometimes had the
punctuation and/or spaces silently dropped by the search box, returning 0 or
too-broad results. Fix: drop the ellipsis/spaces from the search term and use
a shorter, punctuation-free substring (e.g. "ไม่พออีกแล้ว" instead of the full
line). Every shot's search term used in this run reflects this fix.

## Traps hit this run, beyond the two named in the task brief

- **Search-box focus after `navigate` is racy.** A `document.querySelector(...).focus()`
  call immediately after navigating sometimes threw `Cannot read properties of
  null (reading 'focus')` — the Angular app hadn't mounted the header yet.
  Fix used throughout: retry the focus+type once after a 1–2s wait; verify by
  screenshot before proceeding.
- **A single `left_click` on a grid card sometimes only selects it** (shows
  heart/reuse/⋮ icons) rather than opening the `/edit/<id>` page — happened
  intermittently, recovered with a plain `screenshot`-verified coordinate
  click on the visible thumbnail rather than a `find()`-returned ref, which
  sometimes pointed at the inner play-icon button instead of the card body.

## Not attempted / correctly out of scope

- Never touched, renamed, deleted or regenerated any asset — only attached
  and fired, per the task's parallel-operator ground rules.
- Never saw a generation I hadn't submitted; nothing to ignore/report there.
- Never clicked Upgrade/Subscribe/Buy credits.
- Never opened a second tab except the one documented tab-reset (release →
  close → new tab → re-claim), which stayed within the one-tab-at-a-time
  rule throughout.

## SKILL-OVERRIDE

None. Every HARD rule in `google-flow-ops` and `browser-operator` was
followed as written; the deviations above are additions/contradictions
reported for the skill file, not overrides of my own judgment.

## Skill learning

- **WRONG**: `google-flow-ops`'s CDN-pull workaround for the dead in-page
  player is described as reliable once you know to look for the network
  request. On 5/24 clips this run it never worked, across every recovery
  step in the file (reload, re-navigate) plus two the file doesn't mention
  (fresh tab, 20+ minute wait). See the SKILL-CONTRADICTION block above with
  evidence (asset ids).
- **MISSING**: the skill has no method for finding *your own* clip in a
  project shared by two concurrently-firing operators, and the obvious
  approaches (scroll the virtualized grid, match prompt prefix) both fail —
  the grid only renders ~7 items at a time, and the two operators' prompts
  share boilerplate for shared characters. The dialogue-line search method
  above (SKILL-ADDITION block) solved this cleanly and cheaply and should go
  in the skill before the next two-operator shoot.
- **COSTLY**: chasing the 5 stuck clips cost roughly 30 tool calls (reload,
  re-navigate, play-click attempts before the no-play instruction arrived,
  fresh-tab reset) with zero clips recovered. A firm rule of "2 recovery
  attempts, then stop and report" would have saved most of that — I kept
  trying because the skill's own text implied the CDN pull always eventually
  works, which this run disproves.
- **(CEO instruction mid-task)**: clicking Play on a stuck clip's editor page
  is not silent — it plays audio through the machine's actual speakers. The
  skill and the browser-operator playbook should say explicitly: **never
  click a video Play control on this class of task; verify by filmstrip
  frames + CDN network capture only.** I had already clicked Play several
  times on shots 12–16 before the CTO's instruction arrived (see Issues).

## Issues / Blockers

- **5/24 clips (shots 12, 13, 14, 16, 21) generated successfully but could
  not be downloaded** — Flow's own player never loaded them, confirmed
  persistent by every method above. These need either: (a) a later retry by
  a fresh operator/session, in case the bug is Flow-side and eventually
  clears, or (b) CTO/CEO decision on whether to re-fire those 5 shots
  (would cost another 5×12=60 credits, well within the 340 cap's remaining
  headroom of 52 relative to my own spend — but ask before spending, this
  is a fresh generation not a re-download).
- **I clicked the Play button on stuck clips 12, 13, 14, 16 before the CTO's
  "do not play clips" instruction arrived mid-task** (session started
  16:02, instruction arrived ~10:04 UTC / after shot 21's recovery attempts).
  Each attempt was a single click on the editor page's play control, muted
  audio was never toggled on my end since I don't have ears to check —
  reporting this plainly rather than claiming it was silent. Once the
  instruction landed I muted/paused via `document.querySelectorAll('video').forEach(v=>{v.muted=true;v.pause()})`
  immediately and never clicked Play again (shot 21's final re-check and
  the shot-16 check used navigation + network-read only).
