## Summary

Shot the teaser in Google Flow, using winbox's own Chrome (deviceId
`815ddf16-36ea-4e0d-827a-f51e9ff85351`, verified via `navigator.userAgent`
to be real Chrome, not Edge). **4 of 7 shots completed: 1, 2, 54, 55.**
Shots 56, 57, 58 were not fired — the 90-minute wall-clock budget ran out
while stuck on a severe run of chip-attach failures for shot 56 (7
consecutive no-ops binding character Elements in องค์ประกอบ mode, all
independently coordinate-verified, matching the skill's documented ~1/15
flakiness for this exact interaction but landing on an unusually bad
streak). Full detail, timing table, cost table, and 6 skill contradictions
(one Windows-specific display bug, a submit-button-needs-trusted-click
finding, an Agent-mode-hides-settings finding, an inline-`@`-truncation
finding, an export-hang duration finding, and a resize_window-never-works
finding) are in `docs/reports/teaser-shoot-winbox-20260907.md`.

Balance: 210 → 130 (80 credits spent, well under the 180 cap and 30-credit
floor). One outright failure (shot 54, audio generation error) was
auto-refunded and successfully re-fired per the task's re-fire rule; no
re-fire was done on taste.

## Files Changed

- `docs/reports/teaser-shoot-winbox-20260907.md` (new — full report)
- `docs/reports/teaser-shoot-winbox-20260907/shot01.mp4` + `shot01-frame0.png`
- `docs/reports/teaser-shoot-winbox-20260907/shot02.mp4` + `shot02-frame0.png`
- `docs/reports/teaser-shoot-winbox-20260907/shot54.mp4`
- `docs/reports/teaser-shoot-winbox-20260907/shot55.mp4`
- `docs/reports/teaser-shoot-winbox-20260907/screenshot-final-balance-media-grid.jpg`
- `REPORT.md` (this file)

## Commits

- `teaser: shot01 fired and downloaded (frame mode, Plate A)`
- `teaser: shot02 fired and downloaded (frame mode, Plate B)`
- `teaser: shot54 fired (retry after audio-gen failure), downloaded`
- `teaser: shot55 fired and downloaded`

## Tests

No test suite applies to this task (browser-driven content generation, not
code). Verification performed instead:
- `ffprobe` on all 4 clips: confirmed 8.00s duration, 720x1280 h264 video,
  aac stereo audio present on every file.
- `ffmpeg` frame-0 extraction + visual comparison for shots 1 and 2 (the
  only two with a supplied start frame to check against): both frame-0
  images match their supplied plate.
- Chip-count / frame-bind state verified via scoped DOM queries
  (`.ingredient-bar-container button.chip-container`, `.frame-trigger
  button.empty-chip`) before every submit, not assumed.
- Thai dialogue verified byte-for-byte via `innerText` before every submit
  that included dialogue (shots 54, 55).

## Issues / Blockers

**Not a hard blocker — partial completion, reported per the task's own
"whichever runs out first ends the task" rule (wall-clock budget).**

- Shots 56, 57, 58 not fired. 130 credits remain, well above the floor, so
  the constraint was time/reliability, not money.
- Root blocker: the Elements picker's confirm-button click (open picker →
  search handle → click "เพิ่มไปยังพรอมต์") failed to bind a chip 7 times in
  a row for shot 56, including after a full page reload, despite the
  confirm button's coordinates being freshly re-verified via
  `getBoundingClientRect` immediately before every click. This is the exact
  flakiness `google-flow-ops` already documents (~1/15 success rate) — this
  run just landed on a long losing streak of it, and there was no budget
  left to keep retrying.
- Six `SKILL-CONTRADICTION` entries logged for the CTO to fold into
  `google-flow-ops` — see the report's §8. Highlights: `resize_window`
  never took effect at all on this Windows box (unlike the Mac, where it's
  merely late); a synthetic JS `.click()` silently no-ops on the
  money-spending submit button specifically (works fine for pickers/menus);
  Agent mode being ON by default hides the real per-shot settings panel
  behind an unrelated Agent-defaults panel; and one MCP tab's viewport
  collapsed to 98x74 with screenshots intermittently timing out, fixed by
  opening a fresh tab (per the skill's own frozen-tab ladder) rather than
  fighting the stuck one.

## Notes for Reviewer

- Balance and per-shot chip/frame verification are in the report's cost
  table and per-shot table — every number was read from the live page, not
  estimated.
- The task script's `INGREDIENTS: @handle` header line in each prompt block
  was treated as operator bookkeeping and **not typed into Flow's prompt
  box**, only the prose/dialogue below it. This is an interpretation call
  (the task didn't say explicitly either way) — flagging it for a
  correction if wrong, since it would affect how shots 56-58 should be
  typed too.
- Recommend the next operator start shots 56-58 with Agent mode already
  confirmed off and try the picker fresh before assuming another bad streak
  — 56/57/58 only need 1-2 chips each versus 54/55's three, so total retry
  surface is smaller.
