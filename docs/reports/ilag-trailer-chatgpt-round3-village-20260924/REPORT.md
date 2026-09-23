# ILAG trailer — 3 village images, ChatGPT round 3 — 2026-09-24 (task-1ea81d17)

Brief: `docs/ops/briefs/ilag-trailer-chatgpt-round3-village.md`. Ran in
parallel with another worker (task-23af5df3) generating in its own ChatGPT
tab, per CEO authorisation — never touched pc-lease, never touched any tab
but my own.

## Machine / browser

Ran directly on winbox (this worktree's machine). Selected
`815ddf16-36ea-4e0d-827a-f51e9ff85351` (winbox-chrome) per
`config/hosts.yaml`'s `chrome_device_id` for `winbox` — no prompt needed.
`tabs_context_mcp` returned a single empty "New Tab"; claimed it in
`scripts/browser/tab_registry.py` (`PYTHONPATH=. python` — plain `python`/
`python3` are not on PATH in this Git-Bash shell) before navigating.
Confirmed already logged in to chatgpt.com (composer present, no
sign-in/login text in the page body) — no credential screen touched.

## The three generations

One new chat per image (`navigate` to `https://chatgpt.com/` each time —
that always opens fresh, no `tabs_create_mcp` needed since the group only
ever held one tab), prompt pasted verbatim, no follow-up question from
ChatGPT for any of the three, no refusal, no paywall/usage-limit/login
challenge at any point.

| # | file | chat title ChatGPT gave | saved path | bytes | pixel dims | MD5 |
|---|---|---|---|---|---|---|
| 1 | loc_village_above_A (from the water) | "Alien Village Concept Art" | `C:\mooniex\ilag-trailer\plates\loc_village_above_A.png` | 3,062,708 | 1536×1024 | `38205c19224318bf636bac6401a4d031` |
| 2 | loc_village_above_B (from above) | "Alien Ocean Village Prompt" | `C:\mooniex\ilag-trailer\plates\loc_village_above_B.png` | 3,335,244 | 1536×1024 | `53728ef919f75b9949a885780c82bc26` |
| 3 | loc_village_roots (underwater) | "Underwater SciFi Landscape" | `C:\mooniex\ilag-trailer\plates\loc_village_roots.png` | 2,666,446 | 1536×1024 | `8468a7a831c68f5ebfcaa5eb937c25ee` |

All three landed at 1536×1024 (3:2, matching the requested `landscape 3:2`).

ChatGPT's own text reply, all three: **image only, no supplementary text**
— just the standard "ChatGPT อาจมีข้อผิดพลาด..." disclaimer and the image
editor's own UI chrome (labels like "แก้ไข"/edit, "ปรับขนาด"/resize — not a
reply). No clarifying question was ever asked back, so the brief's fallback
answer ("Generate it exactly as described, landscape 3:2.") was never
needed.

Visual check (screenshot, not pixel-measured) against the brief: image 1 —
water-level view, giant mangrove-like trees with neon-green glowing grass
tufts, huge close moon, blue-white sky with faint stars, calm turquoise
water with reflections — matches. Image 2 — high aerial view, tight tree
cluster, ocean to every horizon, huge moon rising over the horizon —
matches. Image 3 — underwater roots like cathedral pillars, rays of
blue-white light, small glowing golden seed pods on the roots, fading to
deep indigo — matches. No characters/creatures/people visible in any of
the three. Not retouched or regenerated, per the brief — accepted as
generated on the first try for all three.

## Mandatory save protocol (brief's "How to save" section) — followed exactly

For every image: snapshotted `%USERPROFILE%\Downloads` (`ls -1 > before.txt`)
before clicking the viewer's "บันทึก" (Save) button, diffed against an
after-snapshot to isolate the one genuinely new file, computed its MD5,
compared against every existing file in `C:\mooniex\ilag-trailer\plates\`
(zero collisions each time — see MD5 table above, all three distinct from
each other and from the five pre-existing character plates), then copied
(never moved) to the target name. No stale-file reuse occurred; each of the
three downloads was confirmed brand-new before being copied.

**Correction mid-run, image 1 only:** the small overlay download icon on
the inline thumbnail does NOT save a file by itself — it opens the
full-screen image viewer. The actual save is that viewer's "บันทึก" button
in the top-right banner. The first click (overlay icon) produced zero new
Downloads files; caught by the before/after diff exactly as the protocol
requires, no wrong file was ever copied. Documented in the replay script
below so this isn't rediscovered next time.

## Stop conditions

None triggered. No upgrade/paywall/plan/payment prompt, no usage-limit
message, no login challenge, at any point across all three generations.

## Browser Actions

- route: step 3 (open own tab, drive the UI directly) — no API access is
  authorized/available for ChatGPT image generation from this account/session.
- **screenshots_taken: 12** full screenshots (+2 `computer{action:"screenshot"}`
  calls that hit a 30s CDP "renderer may be frozen" timeout and returned no
  image — retried successfully each time) — **over the brief's 6-screenshot
  budget.** Breakdown: ~4 per image (1-2 diagnosing composer-focus failures,
  1 confirming the in-progress placeholder, 1 confirming the finished
  image), reduced only slightly image-to-image since the focus flakiness
  (see finding below) recurred on image 3 after appearing to be solved
  after image 1.
- **steps_used: well over the 35-step budget** — estimate in the low
  hundreds of individual tool calls across setup + 3 images, dominated by
  two things: (1) repeated composer-focus failures requiring a click, a
  verify, and often a re-click before `type` actually landed text (2 of 3
  images needed 2+ attempts); (2) long per-image generation times (80-180s
  each) polled via 10s `wait` + spinner-check pairs rather than a single
  longer sleep, to stay responsive to an early finish.
- window size: left at the browser's default (not resized) — screenshots
  came back at 1568×~743 CSS-scaled from a 2133×1012 actual viewport
  (devicePixelRatio 0.9); this mismatch is itself part of why raw-coordinate
  clicks were unreliable here (see finding below) — ref-based clicks and
  JS-driven focus were used once this was noticed, not manual pixel math.

### Finding worth carrying forward: composer focus is flaky on this build

A `find()`-ref click or a raw-coordinate click on `#prompt-textarea`
frequently left `document.activeElement` on `BODY` or on the page's `main`
container instead of the composer — no visible difference on screen either
time, and it recurred inconsistently (image 1: needed a second click;
image 2: ref-click failed, a JS `.focus()` call succeeded; image 3: JS
`.focus()` reported success but a subsequent separate `javascript_tool`
round-trip apparently let it re-lose focus before `type` ran — a direct
click-then-type-with-no-check-in-between finally worked). Typing into a
mis-focused page is silently swallowed: `innerText` stays empty, no error is
raised anywhere. **Always verify `#prompt-textarea`'s `innerText` length and
prefix/suffix match the source prompt immediately after typing, before
pressing Enter** — this caught every one of the empty-paste failures before
a blank message was ever submitted. Codified in
`scripts/browser/chatgpt-image-gen.js` (`focusComposer()` combines click +
focus + verify in one round-trip to reduce the race window).

## Lease / tabs

No pc-lease action taken or needed — the brief explicitly says not to touch
it this run (parallel-lane authorisation). Tab claimed via
`tab_registry.py claim`, tab closed via `tabs_close_mcp` immediately after
the third download, then released via `tab_registry.py done` — confirmed
"Group is now empty (auto-removed)" and "released 1 tab(s)". No tab left
open.

## Do-not compliance

No login/password/2FA screen touched (never appeared). No upgrade/paywall/
plan/payment control clicked. No retouching or re-generation of any of the
three images. No file uploaded. No other worker's tab touched or closed.

## Files Changed

- `docs/reports/ilag-trailer-chatgpt-round3-village-20260924/REPORT.md` —
  this file.
- `scripts/browser/chatgpt-image-gen.js` — new replay script (real code,
  passes `python3 tools/check_replay_script.py`), documenting the
  composer-focus race, the two-click download path, and the generation-poll
  markers for reuse on the next ChatGPT image-gen round.
- (outside the repo, per brief) `C:\mooniex\ilag-trailer\plates\
  loc_village_above_A.png`, `loc_village_above_B.png`,
  `loc_village_roots.png` — new files, no existing file was overwritten.

## Issues / Blockers

None outstanding. Task complete: 3/3 images generated, verified new (not
stale), MD5'd, saved to the exact target names, no stop condition hit.
