# Teaser shoot — winbox — 2026-09-07 — task-ef3995a1

**Status: PARTIAL.** 4 of 7 shots completed and downloaded (1, 2, 54, 55).
Shots 56, 57, 58 were **not fired** — blocked by a severe run of chip-attach
failures on shot 56 (7 consecutive no-ops binding `@lung_somchai` /
`@noodle_shop` in องค์ประกอบ mode) combined with the 90-minute wall-clock
budget running out. This is the first real-generation run on winbox; a lot
of the time went to discovering Windows-specific UI quirks not in the skill
(see SKILL-CONTRADICTION section).

## 0. Browser selection

`list_connected_browsers` returned 3 entries:

| deviceId | name | osPlatform | isLocal |
|---|---|---|---|
| 35a05d33-19a5-4d2e-bab0-08503bad0a9b | Browser 1 | macOS | false |
| 815ddf16-36ea-4e0d-827a-f51e9ff85351 | Browser 2 | Windows | true |
| 70bf3142-ded3-4b66-8cb7-22351065a084 | Browser 3 | Windows | true |

Two Windows entries were local (Chrome + Edge per the task brief).
`switch_browser` timed out after 2 minutes (no one clicked Connect). Per the
skill's fallback, selected `815ddf16-36ea-4e0d-827a-f51e9ff85351` and
confirmed it was real Chrome (not Edge) via `navigator.userAgent` — no
`Edg/` token present: `Mozilla/5.0 (Windows NT 10.0; Win64; x64)
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36`.
**This deviceId should be recorded in `config/hosts.yaml` as winbox's
`chrome_device_id`** so future workers skip this step.

## 1. Sign-in test

`google.com` top-right corner: avatar present, `aria-label` = "Google
Account: กอล์ฟ พัสกร. (pass.gob1@gmail.com), Google membership". No "Sign
in" button. **Signed in, proceeded.**

Chrome tab count at start (`tabs_context_mcp`): 1 tab ("New Tab").

## 2. Cost table

| Event | Balance before | Balance after | Delta |
|---|---|---|---|
| Session start (account menu read) | – | 210 | – |
| Shot 1 fired (เฟรม, Plate A) | 210 | 190 | -20 |
| Shot 2 fired (เฟรม, Plate B) | 190 | 170 | -20 |
| Shot 54 attempt 1 (องค์ประกอบ, 3 chips) — **failed, audio gen unsuccessful** | 170 | 170 | 0 (auto-refunded) |
| Shot 54 retry (via card's own retry button) | 170 | 150 | -20 |
| Shot 55 fired (องค์ประกอบ, 3 chips) | 150 | 130 | -20 |
| Shots 56/57/58 | 130 | 130 | 0 (never fired — chip-attach could not be gotten reliably bound within budget) |
| **Final balance** | | **130** | |
| **Total spent** | | | **80 / 180 cap** |

Well under the cap; well above the 30-credit floor. No paid control other
than Veo 3.1 Fast was ever clicked. No Quality, no Upgrade, no Subscribe.

## 3. Timing table (wall-clock, `date -u +%Y-%m-%dT%H:%M:%SZ`)

| # | Action | Time (UTC) | Notes |
|---|---|---|---|
| 1 | Session start / ffprobe check | 09:16:06 | |
| 2 | Browser selected, sign-in test passed | ~09:17 | |
| 3 | Balance read: 210 | ~09:20 | includes recovering from an early misclick that opened Agent-default settings instead of the per-shot panel |
| 4 | Plates confirmed present (รูปภาพ tab + เลือกรูปภาพเฟรม picker) | ~09:25 | both plates appear correctly |
| 5 | Shot 1 composer built (เฟรม, Plate A, Veo Fast, 9:16, x1) | ~09:20–09:30 | **First attempt lost ~10 min**: typing the prompt navigated into the source plate's own edit page (`/edit/...`) instead of landing in the composer — a focus-race variant, not the documented one (see SKILL-CONTRADICTION). Full navigate-back-and-rebuild required. |
| 6 | Shot 1 submitted | 09:30:37 | |
| 7 | Shot 1 balance confirmed (190), downloaded | ~09:31–09:34 | render was already complete by the time balance was checked (~1 min) |
| 8 | Shot 2 composer rebuilt, submitted | 09:45:25 | frame-slot binding is genuinely racy: two full open→select→confirm cycles needed even with a correctly-scoped DOM check |
| 9 | Shot 2 balance confirmed (170), downloaded | ~09:46–09:47 | |
| 10 | Mode switched to องค์ประกอบ, 3 chips bound (lung_somchai, nong_daeng, noodle_shop) for shot 54 | ~09:48–09:57 | required discovering the composer's real Agent-mode toggle (Agent was ON by default, hiding the per-shot settings panel behind an Agent-Defaults panel instead) |
| 11 | Shot 54 submitted (attempt 1) | 09:57:55 | |
| 12 | Shot 54 attempt 1 result: **ล้มเหลว — สร้างเสียงไม่สำเร็จ** (failed, audio generation unsuccessful) | ~09:59 | balance re-checked: auto-refunded to 170 |
| 13 | Shot 54 retried via card's own retry button | 10:00:08 | |
| 14 | Shot 54 retry succeeded, balance 150, downloaded | ~10:02–10:03 | |
| 15 | Shot 55: 3 chips rebound, prompt typed via `execCommand('insertText')` | ~10:05–10:07 | switched off `computer.type` for prompts containing an inline `@handle` after it truncated shot 54's prompt (see SKILL-CONTRADICTION) |
| 16 | Shot 55 submit attempt 1 (JS `.click()` on the submit button) | 10:07:04 | **Silently did not fire** — no card appeared, balance unchanged. JS `.click()` works for opening pickers/menus but NOT for the money-spending submit button, which needs a real trusted `computer` click. |
| 17 | Shot 55 rebuilt (3 chips, prompt), submitted with a real click | 10:14:58 | |
| 18 | Shot 55 balance confirmed (130) | ~10:15 | |
| 19 | Shot 55 download: toolbar "ดาวน์โหลดฉาก" hung on "Exporting your scene…" twice, needed 2 reload cycles | ~10:16–10:25 | Third attempt (after the export state had cleared on its own) succeeded. This is the documented export-hang trap, but it hung far longer here (~9 min total) than the skill's "reload, ~15s" guidance. |
| 20 | Attempted shot 56 chip binding | 10:26–10:32 | **7 consecutive failures** to bind either `@lung_somchai` or `@noodle_shop` via the picker's confirm-button flow, including after a full page reload. Coordinates were re-verified correct via `getBoundingClientRect` immediately before each click (not stale). This is the documented ~1/15 flakiness, but landing 7-for-7 failures used up the remaining time budget. |
| 21 | Stopped, wrote report | 10:32:43 | **76 minutes elapsed**, inside the 90-min budget, but too little left to safely fire 3 more clips and download/verify them |

## 4. Per-shot table

| Shot | Mode | Attached | Chip count verified | Dialogue verified byte-for-byte | Result | File |
|---|---|---|---|---|---|---|
| 1 | เฟรม | เริ่ม = Plate A ("Man standing in alley") | N/A (frame slot, not chips) | N/A (SILENT) | Success, first try | `shot01.mp4` |
| 2 | เฟรม | เริ่ม = Plate B ("Envelope in puddle on pavement") | N/A | N/A (SILENT) | Success, second composer rebuild (frame binding dropped on nav) | `shot02.mp4` |
| 54 | องค์ประกอบ | @lung_somchai, @nong_daeng, @noodle_shop | 3/3, verified via `.ingredient-bar-container button.chip-container` | Yes — "เงินนี้พ่อตั้งใจหามาให้ลูก" | **Attempt 1 failed** (audio gen error, refunded). **Retry succeeded.** | `shot54.mp4` |
| 55 | องค์ประกอบ | @lung_somchai, @nong_daeng, @noodle_shop | 3/3 | Yes — "ไม่ต้องรู้ว่ามันมาจากไหน แค่ใช้มันให้คุ้ม" | Success (2nd submit attempt — 1st was a JS-click no-op, no credit spent) | `shot55.mp4` |
| 56 | องค์ประกอบ | @lung_somchai, @noodle_shop | **Never reached 2/2** — 7 straight chip-attach failures | N/A (SILENT) | **Not fired.** No credits spent. | — |
| 57 | องค์ประกอบ | @nong_daeng, @noodle_shop | Not attempted | N/A (SILENT) | **Not fired.** | — |
| 58 | องค์ประกอบ | @lung_somchai, @noodle_shop | Not attempted | Yes needed — "กินก่อนไปสมัครงานนะ" (never reached) | **Not fired.** | — |

**Note on prompt text sent to Flow:** the task's script file prefixes each
block with an `INGREDIENTS: @handle, ...` line. That line was treated as
operator bookkeeping (matching which characters to attach) and **not typed
into the Flow prompt box** — only the descriptive prose + dialogue lines
below it were typed. This is an interpretation call, not stated explicitly
in the task; flagging it so the CTO can correct if wrong.

## 5. ffprobe output

```
shot01.mp4: Duration 00:00:08.00, Video: h264, 720x1280, 24fps; Audio: aac, 48000Hz, stereo
shot02.mp4: Duration 00:00:08.00, Video: h264, 720x1280, 24fps; Audio: aac, 48000Hz, stereo
shot54.mp4: Duration 00:00:08.00, Video: h264, 720x1280, 24fps; Audio: aac, 48000Hz, stereo
shot55.mp4: Duration 00:00:08.00, Video: h264, 720x1280, 24fps; Audio: aac, 48000Hz, stereo
```

ffprobe and ffmpeg were both available on this box via
`C:\Users\UsEr\AppData\Local\Microsoft\WinGet\Links\` (on PATH in Git Bash).

## 6. Frame-0 verdict (shots 1 and 2 only)

Both extracted via `ffmpeg -y -i <file> -frames:v 1 -update 1
<file>-frame0.png` (the `-update 1` flag was needed — ffmpeg's default
`image2` muxer warns/fails without it on a single-frame extraction, a
Windows-build quirk not seen on the Mac runs).

- **shot01-frame0.png IS the supplied plate.** Same man in a stained apron
  against the same concrete wall, same alley geometry, same streetlamp
  position and colour grade as "Man standing in alley". Frame-mode binding
  worked correctly.
- **shot02-frame0.png IS the supplied plate.** Same envelope-in-puddle
  composition, same sandalled feet, same low-angle framing as "Envelope in
  puddle on pavement". Frame-mode binding worked correctly.

## 7. What failed, and re-fire decisions

- **Shot 54, attempt 1: outright failure** — Flow returned "ล้มเหลว สร้างเสียงไม่สำเร็จ" (failed, audio generation unsuccessful), with an
  on-screen note that the account was not charged for it. Balance confirmed
  unchanged (170→170) before the retry. Re-fired via the failed card's own
  `refresh` button per the task's "re-fire only on outright failure" rule —
  this is exactly that case, not a taste judgment. Retry succeeded and
  charged normally (170→150).
- **Shot 55, attempt 1: not an outright failure, a no-op.** The submit
  button was clicked via `element.click()` in JavaScript rather than a real
  input event; nothing happened (no card created, no balance change). This
  was caught before any credit was at risk and does not count against the
  2-refire allowance since nothing was ever submitted to Google. Re-attempted
  with a real trusted click and it fired correctly.
- **Shots 56–58: not fired at all**, so no re-fire question applies to them.
  The blocker was the composer's Elements picker refusing to bind a
  character chip on 7 consecutive attempts (open picker → search → click
  confirm), including after a full page reload, with coordinates
  independently re-verified correct via `getBoundingClientRect` before each
  click. This matches the skill's documented "~1/15 success rate" for this
  exact interaction, just an unusually bad run of it. No credits were spent
  on any of the 7 attempts — the picker either no-oped or the composer
  simply had no ingredient-bar chip afterward.

## 8. Skill contradictions / additions

```
SKILL-CONTRADICTION: google-flow-ops :: "resize_window is late: applies only
  after a navigation" :: On winbox, resize_window to 1024x768 never took
  effect at all, before OR after navigation — window.innerWidth stayed at
  1920 (later 1920x855) through repeated resize+navigate cycles. This is a
  Windows-specific gap: the skill's guidance was written and measured on
  macOS. Screenshots this session cost ~1568x698-1568x744 (roughly 1500-2300
  tokens each) instead of the ~814 tokens the skill's cost table assumes,
  which meaningfully changed the cost-benefit of screenshotting vs. reading
  via JS on this host. :: 2026-09-07, task-ef3995a1
```

```
SKILL-CONTRADICTION: google-flow-ops :: (new hazard, not in the skill) ::
  Typing a prompt that contains an inline "@handle speaks in Thai..." phrase
  via the `computer` type action can silently truncate the rest of the
  prompt right after the "@" — observed once on shot 54's first prompt entry
  (everything after "muted colour." vanished, verified via innerText before
  and after). No error, no visible state change; the composer's own
  @-mention autocomplete for the ProseMirror editor appears to be the
  trigger. Fix that worked reliably: place the cursor at the end via
  Selection/Range APIs and insert the remaining text with
  `document.execCommand('insertText', false, text)` instead of the
  character-by-character `computer` type action — this bypasses the
  keydown-level autocomplete listener entirely and was used successfully for
  shots 54 and 55. :: 2026-09-07, task-ef3995a1
```

```
SKILL-CONTRADICTION: google-flow-ops :: (new hazard) :: The composer's
  "Agent" mode toggle can be ON by default on project load (aria-pressed
  true), and while it's on, clicking the settings/tune icon opens a
  DIFFERENT panel ("การตั้งค่า Agent" — global Agent generation defaults for
  image/video) instead of the per-shot composer settings panel (model /
  aspect / เฟรม-องค์ประกอบ toggle / quantity) that this whole workflow
  depends on. The fix is to click the "Agent" chip itself first
  (aria-pressed toggles to false) before touching the settings icon.
  :: 2026-09-07, task-ef3995a1
```

```
SKILL-CONTRADICTION: google-flow-ops :: (new hazard) :: A synthetic
  `element.click()` call in JavaScript reliably opens the Elements/frame
  picker and reliably opens/closes the account menu, but did NOT fire the
  "เริ่มสร้าง" (start creating / submit) button — the click registered
  (no error) but no generation was queued and the balance did not move.
  Only a real `computer` tool click (a trusted OS-level input event) fired
  the submission. Money-spending controls on this app appear to require a
  trusted click; navigation/UI-toggle controls do not. :: 2026-09-07,
  task-ef3995a1
```

```
SKILL-CONTRADICTION: google-flow-ops :: "Export hangs: 'Exporting your
  scene…' can sit forever. Full page reload, then click download again.
  Costs nothing but time." :: Confirmed the behaviour, but on this run it
  took two full reload-and-retry cycles and roughly 9 minutes total before a
  third attempt succeeded, not the implied "reload once, ~15s" from the
  skill's timing table (which measured this on the Mac). Also: the
  single-clip download from inside the Scenebuilder editor ("ดาวน์โหลดฉาก")
  saves a **direct .mp4 file**, not the .zip the grid card's bulk-download
  button produces — an operator grepping only for `*.zip` in Downloads will
  wrongly conclude the download never landed. :: 2026-09-07, task-ef3995a1
```

```
SKILL-CONTRADICTION: google-flow-ops :: (new hazard, Windows-specific) ::
  Mid-session, one MCP-controlled tab's `window.innerWidth`/`innerHeight`
  collapsed to 98x74 with `document.hasFocus()` false and
  `visibilityState` "hidden", and `computer` screenshot/zoom calls on it
  began timing out (30s CDP timeout) roughly half the time. `resize_window`
  reported success but did not change the reported dimensions. A brand-new
  tab in the same session immediately reported the correct 1920x855 and
  worked normally, so the fix was: open a fresh tab, close the broken one,
  continue there (per the skill's own frozen-tab ladder) rather than trying
  to recover the stuck tab in place. Root cause not identified — possibly a
  Windows-specific Chrome-extension/CDP interaction, not reproduced on the
  fresh tab. :: 2026-09-07, task-ef3995a1
```

## 9. Deliverables

- This report: `docs/reports/teaser-shoot-winbox-20260907.md`
- Clips: `docs/reports/teaser-shoot-winbox-20260907/shot01.mp4`,
  `shot02.mp4`, `shot54.mp4`, `shot55.mp4`
- Frame-0 extracts: `shot01-frame0.png`, `shot02-frame0.png`
- 1 screenshot: `screenshot-final-balance-media-grid.jpg` (final credit
  balance + media grid; not saved at 1024x768 — see the resize
  SKILL-CONTRADICTION above for why)
- `REPORT.md` at worktree root

## 10. Recommendation for whoever resumes this task

1. Shots 56, 57, 58 are the only remaining work. All three use องค์ประกอบ
   mode with 1-2 chips each (@lung_somchai/@noodle_shop for 56 and 58,
   @nong_daeng/@noodle_shop for 57) — much simpler attachments than shots
   54/55's three-chip binds, so they may go faster on a fresh attempt.
2. Before retrying the chip picker, confirm Agent mode is off
   (`aria-pressed="false"` on the button whose text is exactly `"Agent"`)
   and use `document.execCommand('insertText', ...)` for any prompt
   containing an inline `@handle`.
3. Budget: 130 credits remain (well above the 30 floor), 3 shots × 20 = 60
   planned, leaving headroom for at least one more re-fire.
