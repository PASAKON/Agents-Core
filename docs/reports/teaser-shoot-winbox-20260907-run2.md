# Teaser shoot — winbox — run 2 — 2026-09-07 — task-5d0bd2fa

**Status: COMPLETE.** All three assigned shots (56, 57, 58) fired, downloaded,
and ffprobe-verified. The optional bonus (a true 9:16 re-fire of shot 1) was
also completed, since 56–58 finished with well over 35 minutes of the
90-minute budget remaining.

This is the second run on winbox, resuming after task-ef3995a1 delivered
shots 1, 2, 54, 55 and left 56–58 unfired. Read first:
`docs/reports/teaser-shoot-winbox-20260907.md` §8, and the "winbox findings
2026-09-07" section of `.claude/skills/google-flow-ops/SKILL.md` — both
hazard lists from the first run were applied from the start here.

## 0. Browser selection

Per the task, `config/hosts.yaml` already carried winbox's `chrome_device_id`
(`815ddf16-36ea-4e0d-827a-f51e9ff85351`). Called
`mcp__claude-in-chrome__select_browser` with it directly — no
`list_connected_browsers`, no `switch_browser`, per the task's explicit
instruction. Connected successfully ("Browser 1").

Chrome tab count at start (`tabs_context_mcp`): 1 tab ("New Tab").

## 1. Sign-in test

`google.com` top-right corner, read via `aria-label`: "Google Account: กอล์ฟ
พัสกร. (pass.gob1@gmail.com), Google membership". No "Sign in" button.
**Signed in, proceeded.**

## 2. Cost table

| Event | Balance before | Balance after | Delta |
|---|---|---|---|
| Session start (project loaded, balance read via account menu) | – | 130 | – |
| Shot 56 fired (องค์ประกอบ, @lung_somchai + @noodle_shop) | 130 | 110 | -20 |
| Shot 57 fired (องค์ประกอบ, @nong_daeng + @noodle_shop) | 110 | 90 | -20 |
| Shot 58 fired (องค์ประกอบ, @lung_somchai + @noodle_shop, w/ dialogue) | 90 | 70 | -20 |
| Image gen: "Man standing in alley 9x16" (Nano Banana Pro, 9:16) | 70 | 70 | 0 (confirmed free) |
| Shot 1 re-fired (เฟรม, เริ่ม = new 9:16 plate) — **optional bonus** | 70 | 50 | -20 |
| **Final balance** | | **50** | |
| **Total spend, this run** | | | **80 / 100 raised cap** (60/80 for the required 56–58, +20 for the optional re-fire which the task said raises the cap to 100) |

No re-fires were needed on any of the four generations — every fire succeeded
on the first submit (after the client-side composer rebuilds described in
§4). No paid control other than Veo 3.1 Fast / Nano Banana Pro was ever
clicked. No Quality, no Upgrade, no Subscribe — the "credits running low"
banner that appeared partway through was read and dismissed, never acted on.
Well above the 30-credit floor throughout.

## 3. Timing table (wall-clock, `date -u +%Y-%m-%dT%H:%M:%SZ`)

| # | Action | Time (UTC) | Notes |
|---|---|---|---|
| 1 | First tool call / session start | 10:43:05 | |
| 2 | Browser selected, sign-in test passed, project loaded, balance read (130) | ~10:43–10:45 | |
| 3 | Shot 56: chips bound, prompt typed, **1st fire attempt lost to a focus-race navigation** (typing landed in an unrelated plate's `/edit/` page instead of the composer — same bug documented in the first run) | ~10:45–10:56 | full rebuild required; switched to `document.execCommand('insertText')` for all subsequent prompt entry, including prompts with no `@handle` |
| 4 | Shot 56 rebuilt (2/2 chips), submitted with a real click | 10:49:59 | |
| 5 | Shot 56 balance confirmed (110); wrong clip opened once by clicking a stale grid position ("Father giving envelope to son", a **pre-existing** clip) before locating the correct new card via `find()` on its auto-generated title | ~10:50–10:55 | |
| 6 | Shot 56 downloaded, verified, committed, pushed | 10:55:11 | |
| 7 | Shot 57: chips bound (2/2, clean on first attempt), prompt typed and verified, submitted | 10:56:54 | |
| 8 | Shot 57 balance confirmed (90) | ~10:57 | low-balance banner appeared here for the first time; dismissed, not acted on |
| 9 | Shot 57 download: preview **autoplayed and the built-in carousel auto-advanced to an unrelated pre-existing clip** ("Man holding son's hands") mid-export — new hazard, not in the skill | ~10:58–10:59 | re-navigated to the correct `/edit/<id>` URL by hand |
| 10 | Shot 57 downloaded (after 1 export-hang + reload cycle), verified, committed, pushed | 11:00:17 | |
| 11 | Shot 58: chips bound (2/2, clean), prompt typed **with the inline `@lung_somchai` dialogue line**, verified byte-for-byte via `innerHTML` before firing (no truncation), submitted | 11:01:57 | |
| 12 | Shot 58 balance confirmed (70) | ~11:02 | |
| 13 | Shot 58 downloaded (1 export-hang + reload cycle), verified, committed, pushed | 11:04:57 | |
| 14 | **Optional bonus** started: opened Plate A ("Man standing in alley") in รูปภาพ tab, copied its full prompt | ~11:05–11:07 | |
| 15 | New image "Man standing in alley 9x16" generated (Nano Banana Pro, 9:16), balance confirmed unchanged (70) | ~11:07–11:08 | |
| 16 | Image renamed to "Man standing in alley 9x16" via the title-edit control | ~11:08 | |
| 17 | Shot 1 rebuilt in เฟรม mode with the new plate as เริ่ม, prompt typed and verified, submitted | 11:09:29 | |
| 18 | Shot 1 balance confirmed (50) | ~11:09 | |
| 19 | Shot 1 downloaded (2 export-hang + reload cycles this time — the longest of the run), verified, frame-0 extracted, committed, pushed | 11:16:07 | |
| 20 | Final balance re-confirmed (50), grid screenshot saved, report written | ~11:17 onward | **~34 minutes elapsed for the full run**, well inside the 90-min budget |

## 4. Per-shot table

| Shot | Mode | Attached | Chip count verified | Dialogue verified byte-for-byte | Result | File |
|---|---|---|---|---|---|---|
| 56 | องค์ประกอบ | @lung_somchai, @noodle_shop | 2/2, `.ingredient-bar-container button.chip-container` | N/A (SILENT — ambient noise only) | Success on the fire that actually reached Google (1st attempt was a client-side navigation bug, not a real submission — no credits at risk) | `shot56.mp4` |
| 57 | องค์ประกอบ | @nong_daeng, @noodle_shop | 2/2 | N/A (SILENT) | Success, first clean fire of the run | `shot57.mp4` |
| 58 | องค์ประกอบ | @lung_somchai, @noodle_shop | 2/2 | Yes — "กินก่อนไปสมัครงานนะ" | Success | `shot58.mp4` |
| 1 (re-fire, optional) | เฟรม | เริ่ม = "Man standing in alley 9x16" (new plain 9:16 image, generated this run) | N/A (frame slot) | N/A (SILENT) | Success — output is native 720x1280 with **no grey padding**, unlike the original `shot01.mp4` on main | `shot01-refire.mp4` |

**Note on prompt text sent to Flow:** consistent with the first run's
interpretation (flagged there, not corrected by the CTO since), the script
file's `INGREDIENTS: @handle, ...` bookkeeping line was **not typed** into
the Flow prompt box — only the descriptive prose, in-line dialogue, and
ambient-noise lines were typed, exactly as written.

## 5. ffprobe output

```
shot56.mp4:          Duration 00:00:08.00, Video: h264, 720x1280, 24fps; Audio: aac, 48000Hz, stereo
shot57.mp4:          Duration 00:00:08.00, Video: h264, 720x1280, 24fps; Audio: aac, 48000Hz, stereo
shot58.mp4:          Duration 00:00:08.00, Video: h264, 720x1280, 24fps; Audio: aac, 48000Hz, stereo
shot01-refire.mp4:   Duration 00:00:08.00, Video: h264, 720x1280, 24fps; Audio: aac, 48000Hz, stereo
```

All four: 8.00s exactly, 720x1280 (9:16), audio present. ffprobe was
available via `C:\Users\UsEr\AppData\Local\Microsoft\WinGet\Links\` on PATH
in Git Bash, same as the first run.

## 6. Frame-0 verdict (shot 1 re-fire only — the only เฟรม-mode shot this run)

Extracted via `ffmpeg -y -i shot01-refire.mp4 -frames:v 1 -update 1
shot01-refire-frame0.png` (the `-update 1` flag needed again, same
Windows-build quirk as the first run).

**shot01-refire-frame0.png IS the new plate**, and critically **carries no
grey padding** — full-bleed 720x1280. Same man in a stained apron, same
concrete wall, same alley geometry and streetlamp position as "Man standing
in alley 9x16". This confirms the fix: the original `shot01.mp4` (on `main`,
from task-ef3995a1) had grey bars because Plate A was generated landscape;
regenerating the identical prompt in Image mode with 9:16 explicitly selected
produced a true portrait plate, and เฟรม-mode binding carried that aspect
through into the video with no letterboxing.

## 7. What failed, and re-fire decisions

- **Shot 56, attempt 1: not an outright failure, a client-side navigation
  bug.** Typing the prompt via the `computer` type action, right after
  binding both chips, caused the page to navigate into an unrelated plate's
  own `/edit/<id>` page instead of landing text in the composer — the same
  "focus-race variant" the first run's report flagged as a
  SKILL-CONTRADICTION. No card was created and no credit was spent; the
  composer was rebuilt from scratch (chips + prompt) using
  `document.execCommand('insertText', ...)` for all text entry from that
  point on, which did not reproduce the bug. This does not count against the
  one-re-fire allowance since nothing was ever submitted to Google on the
  failed attempt.
- **Shots 57 and 58: no failures.** Both fired clean on the first real
  submit attempt.
- **Shot 1 (optional bonus): no failure.** Fired clean on the first attempt.
- **No shot in this run was re-fired for taste or on any judgment call** —
  every re-attempt was because a prior attempt had provably not reached
  Google (confirmed via unchanged balance and no new card), consistent with
  the task's "re-fire only on outright failure" rule.

## 8. Skill contradictions / additions

```
SKILL-CONTRADICTION: google-flow-ops :: (new hazard, winbox-specific) ::
  Clicking the download icon on a rendered clip's own /edit/ page can trigger
  the video preview to autoplay, and while it plays, Flow's own built-in
  next/prev carousel control can auto-advance the page to a DIFFERENT,
  unrelated pre-existing clip mid-export -- the "Exporting your scene..."
  toast then applies to whichever clip is now open, not the one the operator
  intended. Observed once on shot 57's download (auto-advanced from "Young
  man holding envelope" to a pre-existing "Man holding son's hands" clip).
  No credits are at risk (download is free) but it silently wastes an export
  cycle and can mislead an operator into downloading the wrong file if they
  don't re-check the page title before trusting the download. Fix: after
  clicking download, immediately re-verify the page title/prompt match the
  intended shot before waiting on the export; if it has drifted,
  re-navigate directly to the correct /edit/<id> URL (which does not cost
  anything and does not require rebuilding the composer, since download is a
  read-only action). :: 2026-09-07, task-5d0bd2fa
```

```
SKILL-CONTRADICTION: google-flow-ops :: "resize_window is late: applies only
  after a navigation" :: Confirmed further this run: window.innerWidth /
  innerHeight on winbox measured 1920x911 throughout the session (never
  1024x768), and a getBoundingClientRect() read on the composer's own
  "Agent" toggle button returned CSS coordinates (e.g. y=840) that were
  clearly OUTSIDE the 1568x744 screenshot's pixel space -- confirming the
  screenshot is scaled down from the real viewport by a non-trivial,
  non-obvious ratio (~0.82 here, differing from the ~0.688 ratio the first
  run measured on a different tab state). NEVER click at raw
  getBoundingClientRect() coordinates on this host; only click at the pixel
  coordinates visible in the actual screenshot, or use a `find()`/`read_page`
  ref. :: 2026-09-07, task-5d0bd2fa
```

```
SKILL-CONTRADICTION: google-flow-ops :: (new hazard, winbox-specific) ::
  A synthetic JS `.click()` on the composer's own "Agent" toggle button
  (`document.querySelectorAll('button')` match, `.click()` called directly)
  did NOT change its `aria-pressed` state at all -- not even the "opens
  pickers/menus but not money buttons" behaviour documented in the existing
  winbox findings. A `computer` tool click via an element `ref` (from
  `find()`) ALSO failed to toggle it. Only a `computer` tool click at the
  toggle's actual on-screen pixel coordinates (read from a fresh screenshot,
  not from any DOM rect) succeeded. This suggests the coordinate-vs-CSS-pixel
  scale mismatch above is the root cause of the ref-click failure too, not a
  general "needs a trusted click" rule -- refs may resolve to a stale or
  mis-scaled coordinate on this host. :: 2026-09-07, task-5d0bd2fa
```

```
SKILL-CONTRADICTION: google-flow-ops :: (confirmation, not new) :: The
  export-hang trap recurred on every one of the four downloads this run,
  needing 1-2 reload-and-retry cycles each (worst case: shot 1 re-fire,
  ~7 minutes and 2 reload cycles). This matches the first run's finding that
  the skill's "reload once, ~15s" guidance (measured on the Mac) does not
  hold on winbox -- budget several minutes and up to 2 reload cycles per
  download on this host, not one. :: 2026-09-07, task-5d0bd2fa
```

## 9. Deliverables

- This report: `docs/reports/teaser-shoot-winbox-20260907-run2.md`
- Clips: `docs/reports/teaser-shoot-winbox-20260907-run2/shot56.mp4`,
  `shot57.mp4`, `shot58.mp4`, `shot01-refire.mp4`
- Frame-0 extract (for the เฟรม-mode shot): `shot01-refire-frame0.png`
- 1 screenshot: `screenshot-final-media-grid.jpg` (final media grid state;
  full 1568x698 viewport, not 1024x768 — see the resize
  SKILL-CONTRADICTION above)
- `REPORT.md` at worktree root

## 10. Recommendation for whoever reviews this

1. All 7 shots of the 56-second teaser (1, 2, 54, 55, 56, 57, 58) are now
   shot and downloaded across the two runs. Shot 1 exists in two versions:
   the original `shot01.mp4` on `main` (landscape-padded, from
   task-ef3995a1) and this run's `shot01-refire.mp4` (true 9:16, no
   padding) — **the CTO/CEO should decide which one is canonical** and, if
   the re-fire wins, update the assembly manifest / delete the padded
   original.
2. The new plate "Man standing in alley 9x16" now exists in the project's
   รูปภาพ tab for any future re-generation of shot 1 needing the same start
   frame.
3. Final balance 50/200 monthly credits. The account is genuinely low —
   whoever schedules the next shoot (retakes, or the next episode) should
   confirm the monthly credit reset date before planning further spend.

---

## CTO review, 2026-09-08

Shots 56, 57 and 58 pass: full-frame 9:16, characters continuous with shots 54
and 55, audio present.

**`shot01-refire.mp4` does not pass and must not replace `shot01.mp4`.** It
fixes the letterboxing, but the clip is black-and-white while every other shot
in the teaser is colour, so it cannot be cut against them. The mechanical checks
in this report (duration, resolution, audio, no padding) were all correct and
all blind to it. The canonical shot 1 stays the padded original until a re-fire
comes back in colour; the new "Man standing in alley 9x16" plate should be
regenerated with the grade pinned in its prompt first. Folded into the
`google-flow-ops` skill as "verify grade, not just geometry".
